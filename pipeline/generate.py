"""Uçtan uca üretim akışı: payload → içerik → görseller → tuval → metin → kayıt.

Her varyasyon için plan yapısındaki klasör oluşturulur:
    outputs/YYYY-MM-DD/post-N/
        background.png  → tuvale getirilmiş metinsiz görsel
        final.png       → metin bindirilmiş hali (overlay hatası varsa metinsiz)
        caption.txt     → caption + hashtag'ler
        meta.json       → payload, prompt, model bilgisi, maliyet bloğu
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from PIL import Image

from pipeline.brand import load_brand
from pipeline.canvas import to_canvas, image_to_data_url
from pipeline.config import PROJECT_ROOT
from pipeline.costs import CostTracker, image_cost
from pipeline.formats import get_format
from pipeline.images import generate_image
from pipeline.llm import generate_content
from pipeline.overlay import overlay_text, overlay_logo
from pipeline.reference import analyze_reference, validate_reference_image


def _next_post_index(base_dir: Path) -> int:
    """Aynı gün içindeki mevcut post-N klasörlerinden sonraki sırayı bulur."""
    if not base_dir.exists():
        return 1
    numbers = [
        int(m.group(1))
        for entry in base_dir.iterdir()
        if entry.is_dir() and (m := re.fullmatch(r"post-(\d+)", entry.name))
    ]
    return max(numbers, default=0) + 1


def _validate_payload(payload: dict) -> None:
    topic = (payload.get("topic") or "").strip()
    if not topic:
        raise ValueError("`topic` zorunlu (3-200 karakter)")
    count = int(payload.get("image_count") or 2)
    if not 1 <= count <= 4:
        raise ValueError("`image_count` 1-4 arasında olmalı")


def run_pipeline(
    payload: dict, *, mock: bool = False, out_root: Path | None = None
) -> dict:
    """Form payload'ını uçtan uca çalıştırır; özet döner.

    `mock=True` iken LLM ve görsel üretimi sahte bileşenlerle yapılır
    (API anahtarı ve harcama gerekmez).
    """
    _validate_payload(payload)
    fmt = get_format(payload.get("format", "post_4x5"))
    count = int(payload.get("image_count") or 2)
    quality = payload.get("quality", "standard")
    provider = payload.get("provider", "openai")

    # 1) Referans görsel varsa önce stil çözümle (plan B1)
    tracker = CostTracker()
    style_analysis = None
    reference_meta = None
    reference_bytes = None
    reference_path = payload.get("reference_image")
    if reference_path:
        reference_mode = payload.get("reference_mode", "b1")
        style_analysis, ref_usage = analyze_reference(
            reference_path, mock=mock, provider=provider
        )
        tracker.add_text(
            ref_usage["provider"],
            ref_usage["model"],
            input_tokens=ref_usage["input_tokens"],
            output_tokens=ref_usage["output_tokens"],
        )
        reference_meta = {
            "path": str(reference_path),
            "mode": reference_mode,
            "analysis": style_analysis,
        }
        if reference_mode == "b2":
            # B2: görselin kendisi edit çağrısına girecek
            reference_bytes = validate_reference_image(reference_path).read_bytes()

    # 2) İçerik: prompt'lar + caption + hashtag (stil çözümlemesi dahil)
    payload_for_llm = (
        payload if style_analysis is None else {**payload, "style_analysis": style_analysis}
    )
    content, llm_usage = generate_content(
        payload_for_llm, mock=mock, provider=provider
    )
    tracker.add_text(
        llm_usage["provider"],
        llm_usage["model"],
        input_tokens=llm_usage["input_tokens"],
        output_tokens=llm_usage["output_tokens"],
    )

    # Toplam metin maliyeti (her gönderiye eşit paylaştırılır)
    shared_text_usd = round(tracker.total_usd / max(count, 1), 6)

    # 3) Klasör planı: outputs/YYYY-MM-DD/post-N
    base_dir = (out_root or PROJECT_ROOT / "outputs") / date.today().isoformat()
    start = _next_post_index(base_dir)

    brand = load_brand()
    overlay_text_value = (payload.get("overlay_text") or "").strip()
    max_chars = brand["text"]["max_chars"]
    if len(overlay_text_value) > max_chars:
        raise ValueError(
            f"`overlay_text` en fazla {max_chars} karakter olabilir "
            f"(girilen: {len(overlay_text_value)}). Limiti brand.json'dan değiştirebilirsiniz."
        )
    posts: list[dict] = []
    for offset, spec in enumerate(content["prompts"][:count]):
        post_dir = base_dir / f"post-{start + offset}"
        warnings: list[str] = []

        # 4) Görsel üretimi + hedef tuvale getirme
        png_bytes, img_meta = generate_image(
            spec["prompt"],
            size=fmt.api_size,
            quality=quality,
            mock=mock,
            reference_image=reference_bytes,
        )
        tracker.add_image(
            img_meta["provider"], img_meta["model"], size=fmt.api_size, quality=quality
        )
        single_img_usd = image_cost(
            img_meta["provider"], img_meta["model"], size=fmt.api_size, quality=quality, count=1
        )
        post_estimated_usd = (
            round(single_img_usd + shared_text_usd, 6)
            if single_img_usd is not None
            else None
        )

        canvas = to_canvas(Image.open(BytesIO(png_bytes)).convert("RGB"), *fmt.canvas)
        background_data_url = image_to_data_url(canvas, format="JPEG", quality=95)

        # 5) Logo & Metin bindirme (istendiyse); sığmazsa uyarıyla devam
        final = canvas
        logo_path = payload.get("logo_path")
        if logo_path and Path(logo_path).is_file():
            try:
                logo_img = Image.open(logo_path)
                scale_map = {"small": 0.12, "medium": 0.18, "large": 0.25}
                scale_val = payload.get("logo_scale")
                scale = scale_map.get(scale_val, 0.18) if isinstance(scale_val, str) else float(scale_val or 0.18)
                opacity = float(payload.get("logo_opacity", 1.0))
                final = overlay_logo(
                    final,
                    logo_img,
                    position=payload.get("logo_position", "top-right"),
                    scale=scale,
                    opacity=opacity,
                )
            except Exception as exc:
                warnings.append(f"Logo bindirilemedi: {exc}")

        if overlay_text_value:
            try:
                final = overlay_text(final, overlay_text_value, brand=brand)
            except (ValueError, FileNotFoundError) as exc:
                warnings.append(f"Metin bindirilemedi, metinsiz kaydedildi: {exc}")

        final_data_url = image_to_data_url(final, format="JPEG", quality=95)

        # 6) Caption + meta kaydı (Salt-okunur Vercel ortamında diske yazma sessizce geçilir)
        caption_file = content["caption"] + "\n\n" + " ".join(content["hashtags"])
        saved_dir = ""
        try:
            post_dir.mkdir(parents=True, exist_ok=True)
            canvas.save(post_dir / "background.png")
            final.save(post_dir / "final.png")
            (post_dir / "caption.txt").write_text(caption_file, encoding="utf-8")
            saved_dir = str(post_dir)
        except OSError:
            pass

        meta = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "mock": mock,
            "payload": payload,
            "format": fmt.key,
            "canvas": list(fmt.canvas),
            "api_size": fmt.api_size,
            "llm": llm_usage,
            "image": img_meta,
            "prompt": spec["prompt"],
            "caption": content["caption"],
            "hashtags": content["hashtags"],
            "cost": {
                "post_estimated_usd": post_estimated_usd,
                "text_share_usd": shared_text_usd,
                "image_usd": single_img_usd,
                "batch_cumulative_tracker": tracker.to_meta(),
            },
        }
        if reference_meta:
            meta["reference"] = reference_meta
        if warnings:
            meta["warnings"] = warnings

        if saved_dir:
            try:
                (post_dir / "meta.json").write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except OSError:
                pass

        posts.append({
            "dir": saved_dir,
            "prompt_id": spec["id"],
            "background_data_url": background_data_url,
            "final_data_url": final_data_url,
            "meta": meta,
        })

    return {
        "posts": posts,
        "caption": content["caption"],
        "hashtags": content["hashtags"],
        "cost": tracker.to_meta(),
        "mock": mock,
    }
