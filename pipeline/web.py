"""Sosyal Medya İçerik Üretim Aracı — Yerel Web Sunucusu (FastAPI).

Kullanım:
    python -m pipeline.web
    veya
    uvicorn pipeline.web:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline.brand import load_brand
from pipeline.config import (
    PROJECT_ROOT,
    MissingApiKeyError,
    get_session_secret,
    has_api_key,
    is_auth_required,
    verify_app_password,
    create_session_token,
    verify_session_token,
)
from pipeline.formats import FORMATS, QUALITIES, STYLES
from pipeline.generate import run_pipeline
from pipeline.images import generate_image
from pipeline.canvas import to_canvas, image_to_data_url, data_url_to_image
from pipeline.overlay import overlay_text, overlay_logo
from pipeline.costs import image_cost
from pipeline.llm import DEFAULT_SYSTEM_PROMPT
from PIL import Image

app = FastAPI(title="Sosyal Medya Otomasyon", version="1.1.0")

logger = logging.getLogger("pipeline.web")

# Üretimde (Vercel) oturum imza anahtarı zorunlu: eksikse deploy anında net hata
if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    get_session_secret()

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()] or [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
try:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # referans görsel / logo yükleme sınırı

STATIC_DIR = Path(__file__).resolve().parent / "web_static"
try:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

# Çıktı görsellerini web üzerinden sun
if OUTPUTS_DIR.exists():
    app.mount("/outputs-media", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs-media")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _safe_post_dir(post_dir_input: str) -> Path:
    """Doğrulanmış ve OUTPUTS_DIR altında olduğunu garanti eden klasör çözücü."""
    raw = Path(post_dir_input)
    target = raw if raw.is_absolute() else (OUTPUTS_DIR / raw)
    resolved = target.resolve()
    outputs_resolved = OUTPUTS_DIR.resolve()
    try:
        resolved.relative_to(outputs_resolved)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz veya yetkisiz gönderi yolu.")
    if not resolved.is_dir():
        raise HTTPException(status_code=404, detail="Gönderi klasörü bulunamadı.")
    return resolved


# Rate limiting takip listesi (IP -> [timestamp, ...])
_login_failures: dict[str, list[float]] = {}


def _save_upload_to_temp(upload: UploadFile, *, suffix: str) -> Path:
    """Yüklenen dosyayı boyut sınırıyla geçici dosyaya yazar.

    Sınır (MAX_UPLOAD_BYTES) aşılırsa geçici dosya silinir ve 413 döner;
    böylece sınırsız yüklemeyle diski doldurma (DoS) engellenir.
    """
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = Path(tmp.name)
            copied = 0
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                copied += len(chunk)
                if copied > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Dosya çok büyük (maks. {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
                    )
                tmp.write(chunk)
        return tmp_path
    except Exception:
        if tmp_path and tmp_path.is_file():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def _check_login_rate_limit(ip: str) -> None:
    now = datetime.now().timestamp()
    recent = [t for t in _login_failures.get(ip, []) if now - t < 60]
    _login_failures[ip] = recent
    if len(recent) >= 5:
        raise HTTPException(
            status_code=429,
            detail="Çok fazla hatalı giriş denemesi. Lütfen 1 dakika sonra tekrar deneyin.",
        )


def require_auth(request: Request) -> None:
    """Korumalı endpoint'ler için oturum kontrolü."""
    if not is_auth_required():
        return
    token = request.cookies.get("session_token", "")
    if not verify_session_token(token):
        raise HTTPException(
            status_code=401,
            detail="Yetkilendirme gerekli. Lütfen giriş yapın.",
        )


class LoginRequest(BaseModel):
    password: str


@app.post("/api/auth/login")
def login_endpoint(req: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
    """Uygulama giriş doğrulaması."""
    ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(ip)

    if not verify_app_password(req.password):
        _login_failures.setdefault(ip, []).append(datetime.now().timestamp())
        raise HTTPException(status_code=401, detail="Hatalı şifre.")

    if ip in _login_failures:
        _login_failures.pop(ip, None)

    token = create_session_token()
    is_secure = bool(
        os.environ.get("VERCEL")
        or os.environ.get("VERCEL_ENV")
        or (request and request.url.scheme == "https")
    )
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=86400 * 7,
        path="/",
    )
    return {"success": True, "message": "Giriş başarılı."}


@app.post("/api/auth/logout")
def logout_endpoint(response: Response) -> dict[str, Any]:
    """Oturumu sonlandırır."""
    response.delete_cookie("session_token", path="/")
    return {"success": True, "message": "Çıkış yapıldı."}


@app.get("/api/auth/status")
def auth_status_endpoint(request: Request) -> dict[str, Any]:
    """Mevcut kimlik doğrulama durumunu döner."""
    auth_req = is_auth_required()
    token = request.cookies.get("session_token", "")
    logged_in = verify_session_token(token) if auth_req else True
    return {
        "auth_required": auth_req,
        "logged_in": logged_in,
    }


class UpdateOverlayRequest(BaseModel):
    post_dir: str = ""
    overlay_text: str = ""
    align: str = "center"
    logo_position: str | None = None
    logo_scale: str | None = None
    logo_opacity: float | None = None
    background_data_url: str | None = None
    logo_data_url: str | None = None


class SavePostRequest(BaseModel):
    post_dir: str
    caption: str
    hashtags: list[str]
    overlay_text: str | None = None
    align: str = "center"


class RegenerateSingleRequest(BaseModel):
    post_dir: str
    prompt: str
    format: str
    quality: str = "standard"
    mock: bool = True
    overlay_text: str | None = None
    align: str = "center"


@app.get("/api/config", dependencies=[Depends(require_auth)])
def get_config(request: Request) -> dict[str, Any]:
    """Sistem ayarları, formatlar ve API anahtarı durumunu döner."""
    brand = load_brand()
    auth_req = is_auth_required()
    token = request.cookies.get("session_token", "")
    logged_in = verify_session_token(token) if auth_req else True

    return {
        "app_name": "Sosyal Medya Otomasyon",
        "auth": {
            "required": auth_req,
            "logged_in": logged_in,
        },
        "default_system_prompt": DEFAULT_SYSTEM_PROMPT,
        "formats": {
            k: {
                "key": v.key,
                "canvas": list(v.canvas),
                "aspect_ratio": v.aspect_ratio,
            }
            for k, v in FORMATS.items()
        },
        "styles": list(STYLES),
        "qualities": list(QUALITIES),
        "providers": ["openai", "anthropic"],
        "keys": {
            "openai": has_api_key("openai"),
            "anthropic": has_api_key("anthropic"),
        },
        "brand": {
            "max_chars": brand["text"]["max_chars"],
            "max_lines": brand["text"]["max_lines"],
            "align": brand["text"].get("align", "center"),
        },
    }


def _enrich_post_info(post: dict[str, Any]) -> dict[str, Any]:
    """Bir post klasörünün web URL'lerini ve meta verilerini hazırlar."""
    p_dir_str = post.get("dir", "")
    p_dir = Path(p_dir_str) if p_dir_str else None
    meta: dict[str, Any] = post.get("meta") or {}
    if p_dir and p_dir.is_dir() and not meta:
        meta_path = p_dir / "meta.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    rel_path = ""
    if p_dir and p_dir.is_dir() and OUTPUTS_DIR.exists():
        try:
            rel_path = p_dir.relative_to(OUTPUTS_DIR).as_posix()
        except ValueError:
            rel_path = ""

    timestamp = int(datetime.now().timestamp())
    bg_data = post.get("background_data_url", "")
    fin_data = post.get("final_data_url", "")

    bg_url = (f"/outputs-media/{rel_path}/background.png?t={timestamp}" if rel_path else "") or bg_data
    fin_url = (f"/outputs-media/{rel_path}/final.png?t={timestamp}" if rel_path else "") or fin_data

    return {
        "dir": str(p_dir) if p_dir else "",
        "rel_dir": rel_path,
        "prompt_id": post.get("prompt_id", 1),
        "prompt": meta.get("prompt", ""),
        "background_url": bg_url,
        "final_url": fin_url,
        "background_data_url": bg_data,
        "final_data_url": fin_data,
        "has_final": bool(fin_data or (p_dir and (p_dir / "final.png").is_file())),
        "meta": meta,
    }


@app.post("/api/generate", dependencies=[Depends(require_auth)])
async def generate_endpoint(
    topic: str = Form(...),
    system_prompt: str = Form(""),
    image_count: int = Form(2),
    style: str = Form("product_photo"),
    format: str = Form("post_4x5"),
    overlay_text_val: str = Form(""),
    notes: str = Form(""),
    provider: str = Form("openai"),
    quality: str = Form("standard"),
    mock: bool = Form(True),
    reference_mode: str = Form("b1"),
    reference_file: UploadFile | None = File(None),
    logo_file: UploadFile | None = File(None),
    logo_position: str = Form("top-right"),
    logo_scale: str = Form("medium"),
    logo_opacity: float = Form(1.0),
) -> dict[str, Any]:
    """Yeni bir sosyal medya paketi üretir."""
    temp_ref_path: Path | None = None
    temp_logo_path: Path | None = None
    try:
        if reference_file and reference_file.filename:
            suffix = Path(reference_file.filename).suffix.lower()
            if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
                raise HTTPException(
                    status_code=400,
                    detail="Desteklenmeyen referans görsel formatı. Lütfen PNG, JPG veya WebP yükleyin.",
                )
            temp_ref_path = _save_upload_to_temp(reference_file, suffix=suffix)

        if logo_file and logo_file.filename:
            l_suffix = Path(logo_file.filename).suffix.lower() or ".png"
            if l_suffix == ".svg":
                raise HTTPException(
                    status_code=400,
                    detail="SVG formatı desteklenmemektedir. Lütfen PNG, JPG veya WebP formatında bir logo yükleyin.",
                )
            if l_suffix not in (".png", ".jpg", ".jpeg", ".webp"):
                raise HTTPException(
                    status_code=400,
                    detail="Desteklenmeyen logo dosya formatı. Lütfen PNG, JPG veya WebP yükleyin.",
                )
            temp_logo_path = _save_upload_to_temp(logo_file, suffix=l_suffix)

        payload = {
            "topic": topic.strip(),
            "system_prompt": system_prompt.strip() or None,
            "image_count": image_count,
            "style": style,
            "provider": provider,
            "format": format,
            "overlay_text": overlay_text_val.strip() or None,
            "notes": notes.strip() or None,
            "quality": quality,
            "reference_image": str(temp_ref_path) if temp_ref_path else None,
            "reference_mode": reference_mode,
            "logo_path": str(temp_logo_path) if temp_logo_path else None,
            "logo_position": logo_position,
            "logo_scale": logo_scale,
            "logo_opacity": logo_opacity,
        }

        result = run_pipeline(payload, mock=mock, out_root=OUTPUTS_DIR)

        # Eğer logo yüklendiyse, sonraki düzenlemeler için post klasörüne kopyala
        if temp_logo_path and temp_logo_path.is_file():
            for p in result.get("posts", []):
                p_dir = Path(p.get("dir", ""))
                if p_dir.is_dir():
                    try:
                        shutil.copy(temp_logo_path, p_dir / "logo.png")
                    except OSError:
                        pass

        enriched_posts = [_enrich_post_info(p) for p in result["posts"]]
        return {
            "success": True,
            "posts": enriched_posts,
            "caption": result["caption"],
            "hashtags": result["hashtags"],
            "cost": result["cost"],
            "mock": result["mock"],
        }
    except HTTPException:
        raise
    except (ValueError, MissingApiKeyError) as exc:
        # Uygulama düzeyi, kullanıcıya yol gösteren hatalar: mesaj güvenli
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Üretim akışı beklenmeyen hatayla durdu")
        raise HTTPException(
            status_code=500,
            detail="Üretim sırasında beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.",
        )
    finally:
        if temp_ref_path and temp_ref_path.is_file():
            try:
                temp_ref_path.unlink()
            except OSError:
                pass
        if temp_logo_path and temp_logo_path.is_file():
            try:
                temp_logo_path.unlink()
            except OSError:
                pass


@app.post("/api/overlay-preview", dependencies=[Depends(require_auth)])
def overlay_preview_endpoint(req: UpdateOverlayRequest) -> dict[str, Any]:
    """Canlı metin ve logo düzenleme: API harcamadan final görseli anında yeniden render eder."""
    base_img = None
    p_dir = None

    if req.background_data_url:
        try:
            base_img = data_url_to_image(req.background_data_url).convert("RGB")
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Geçersiz arka plan görsel verisi.") from exc
    elif req.post_dir:
        p_dir = _safe_post_dir(req.post_dir)
        bg_path = p_dir / "background.png"
        if not bg_path.is_file():
            raise HTTPException(status_code=404, detail="background.png bulunamadı.")
        base_img = Image.open(bg_path).convert("RGB")
    else:
        raise HTTPException(status_code=400, detail="Arka plan görseli veya gönderi klasörü belirtilmedi.")

    brand = load_brand()
    brand["text"]["align"] = req.align

    try:
        logo_img = None
        if req.logo_data_url:
            try:
                logo_img = data_url_to_image(req.logo_data_url)
            except Exception:
                pass
        elif p_dir:
            logo_path = p_dir / "logo.png"
            if logo_path.is_file():
                try:
                    logo_img = Image.open(logo_path)
                except Exception:
                    pass

        if logo_img:
            scale_map = {"small": 0.12, "medium": 0.18, "large": 0.25}
            scale = scale_map.get(req.logo_scale, 0.18) if isinstance(req.logo_scale, str) else 0.18
            opacity = float(req.logo_opacity if req.logo_opacity is not None else 1.0)
            base_img = overlay_logo(
                base_img,
                logo_img,
                position=req.logo_position or "top-right",
                scale=scale,
                opacity=opacity,
            )

        final_img = overlay_text(base_img, req.overlay_text.strip(), brand=brand)
        final_data_url = image_to_data_url(final_img, format="JPEG", quality=95)

        final_url = ""
        if p_dir and p_dir.is_dir():
            try:
                final_path = p_dir / "final.png"
                final_img.save(final_path)
                meta_path = p_dir / "meta.json"
                if meta_path.is_file():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    if "payload" in meta and isinstance(meta["payload"], dict):
                        meta["payload"]["overlay_text"] = req.overlay_text.strip() or None
                        if req.logo_position:
                            meta["payload"]["logo_position"] = req.logo_position
                    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                rel_path = p_dir.relative_to(OUTPUTS_DIR).as_posix()
                timestamp = int(datetime.now().timestamp())
                final_url = f"/outputs-media/{rel_path}/final.png?t={timestamp}"
            except OSError:
                pass

        return {
            "success": True,
            "final_url": final_url or final_data_url,
            "final_data_url": final_data_url,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Metin/logo bindirme beklenmeyen hatayla durdu")
        raise HTTPException(
            status_code=400,
            detail="Metin/logo bindirme başarısız oldu. Lütfen tekrar deneyin.",
        )


@app.post("/api/save-post", dependencies=[Depends(require_auth)])
def save_post_endpoint(req: SavePostRequest) -> dict[str, Any]:
    """Kullanıcının caption, hashtag ve metin düzeltmelerini dosyaya yazar."""
    p_dir = _safe_post_dir(req.post_dir)
    if not p_dir.is_dir():
        raise HTTPException(status_code=404, detail="Gönderi klasörü bulunamadı.")

    # caption.txt'yi güncelle
    full_caption = req.caption.strip() + "\n\n" + " ".join(req.hashtags)
    (p_dir / "caption.txt").write_text(full_caption, encoding="utf-8")

    # meta.json'ı güncelle
    meta_path = p_dir / "meta.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["caption"] = req.caption.strip()
            meta["hashtags"] = req.hashtags
            if req.overlay_text is not None and "payload" in meta:
                meta["payload"]["overlay_text"] = req.overlay_text.strip() or None
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    return {"success": True, "message": "Gönderi başarıyla kaydedildi."}


@app.post("/api/regenerate-single", dependencies=[Depends(require_auth)])
def regenerate_single_endpoint(req: RegenerateSingleRequest) -> dict[str, Any]:
    """Tek bir varyasyonu yeniden üretir."""
    p_dir = _safe_post_dir(req.post_dir)
    if not p_dir.is_dir():
        raise HTTPException(status_code=404, detail="Gönderi klasörü bulunamadı.")

    fmt = FORMATS.get(req.format)
    if not fmt:
        raise HTTPException(status_code=400, detail="Geçersiz format.")

    try:
        # Yeni görsel üret
        png_bytes, img_meta = generate_image(
            req.prompt,
            size=fmt.api_size,
            quality=req.quality,
            mock=req.mock,
        )
        canvas = to_canvas(Image.open(io.BytesIO(png_bytes)).convert("RGB"), *fmt.canvas)
        canvas.save(p_dir / "background.png")

        final = canvas
        brand = load_brand()
        brand["text"]["align"] = req.align
        if req.overlay_text:
            try:
                final = overlay_text(canvas, req.overlay_text.strip(), brand=brand)
            except Exception:
                pass
        final.save(p_dir / "final.png")

        # Meta maliyet güncelle
        meta_path = p_dir / "meta.json"
        meta: dict[str, Any] = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["image"] = img_meta
                meta["prompt"] = req.prompt
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

        rel_path = p_dir.relative_to(OUTPUTS_DIR).as_posix()
        timestamp = int(datetime.now().timestamp())
        return {
            "success": True,
            "background_url": f"/outputs-media/{rel_path}/background.png?t={timestamp}",
            "final_url": f"/outputs-media/{rel_path}/final.png?t={timestamp}",
            "meta": meta,
        }
    except HTTPException:
        raise
    except (ValueError, MissingApiKeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("Tekil yeniden üretim beklenmeyen hatayla durdu")
        raise HTTPException(
            status_code=500,
            detail="Yeniden üretim sırasında beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.",
        )


@app.get("/api/outputs", dependencies=[Depends(require_auth)])
def list_outputs_endpoint() -> list[dict[str, Any]]:
    """Daha önce üretilen tüm postları ters kronolojik sırayla listeler."""
    results: list[dict[str, Any]] = []
    if not OUTPUTS_DIR.exists():
        return results

    # YYYY-MM-DD klasörleri
    date_dirs = sorted([d for d in OUTPUTS_DIR.iterdir() if d.is_dir()], reverse=True)
    for d_dir in date_dirs:
        post_dirs = sorted(
            [p for p in d_dir.iterdir() if p.is_dir() and p.name.startswith("post-")],
            key=lambda p: int(p.name.replace("post-", "")) if p.name.replace("post-", "").isdigit() else 0,
            reverse=True,
        )
        for p_dir in post_dirs:
            meta_path = p_dir / "meta.json"
            meta: dict[str, Any] = {}
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            rel_path = p_dir.relative_to(OUTPUTS_DIR).as_posix()
            timestamp = int(datetime.now().timestamp())
            results.append({
                "dir": str(p_dir),
                "rel_dir": rel_path,
                "date": d_dir.name,
                "post_name": p_dir.name,
                "topic": meta.get("payload", {}).get("topic", p_dir.name),
                "caption": meta.get("caption", ""),
                "hashtags": meta.get("hashtags", []),
                "background_url": f"/outputs-media/{rel_path}/background.png?t={timestamp}",
                "final_url": f"/outputs-media/{rel_path}/final.png?t={timestamp}",
                "created_at": meta.get("created_at", ""),
                "mock": meta.get("mock", True),
                "format": meta.get("format", "post_4x5"),
            })
    return results


@app.get("/", response_class=HTMLResponse)
def index_page() -> str:
    """Tek sayfalık modern Web Studio Dashboard HTML'i sunar."""
    html_file = STATIC_DIR / "index.html"
    if html_file.is_file():
        return html_file.read_text(encoding="utf-8")
    return "<h1>Sosyal Medya Otomasyon</h1><p>index.html bulunamadı.</p>"


@app.get("/themes", response_class=HTMLResponse)
def themes_page() -> str:
    """İnteraktif Tema & Renk Paleti Seçici sayfasını sunar."""
    theme_file = STATIC_DIR / "theme_showcase.html"
    if theme_file.is_file():
        return theme_file.read_text(encoding="utf-8")
    return "<h1>Tema Seçici bulunamadı.</h1>"


def main():
    import uvicorn
    print("\n" + "=" * 60)
    print("🚀 SOSYAL MEDYA OTOMASYON (Adım 7)")
    print("🔗 Arayüz: http://localhost:8000")
    print("📂 Çıktı Klasörü:", OUTPUTS_DIR)
    print("=" * 60 + "\n")
    uvicorn.run("pipeline.web:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
