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
from pipeline.canvas import to_canvas
from pipeline.config import PROJECT_ROOT
from pipeline.costs import CostTracker
from pipeline.formats import get_format
from pipeline.images import generate_image
from pipeline.llm import generate_content
from pipeline.overlay import overlay_text


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
    quality = payload.get("quality", "medium")

    # 1) İçerik: prompt'lar + caption + hashtag
    content, llm_usage = generate_content(payload, mock=mock)
    tracker = CostTracker()
    tracker.add_text(
        llm_usage["provider"],
        llm_usage["model"],
        input_tokens=llm_usage["input_tokens"],
        output_tokens=llm_usage["output_tokens"],
    )

    # 2) Klasör planı: outputs/YYYY-MM-DD/post-N
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
        post_dir.mkdir(parents=True, exist_ok=True)
        warnings: list[str] = []

        # 3) Görsel üretimi + hedef tuvale getirme
        png_bytes, img_meta = generate_image(
            spec["prompt"], size=fmt.api_size, quality=quality, mock=mock
        )
        tracker.add_image(
            img_meta["provider"], img_meta["model"], size=fmt.api_size, quality=quality
        )
        canvas = to_canvas(Image.open(BytesIO(png_bytes)).convert("RGB"), *fmt.canvas)
        canvas.save(post_dir / "background.png")

        # 4) Metin bindirme (istendiyse); sığmazsa uyarıyla metinsiz devam
        final = canvas
        if overlay_text_value:
            try:
                final = overlay_text(canvas, overlay_text_value, brand=brand)
            except (ValueError, FileNotFoundError) as exc:
                warnings.append(f"Metin bindirilemedi, metinsiz kaydedildi: {exc}")
        final.save(post_dir / "final.png")

        # 5) Caption + meta kaydı
        caption_file = content["caption"] + "\n\n" + " ".join(content["hashtags"])
        (post_dir / "caption.txt").write_text(caption_file, encoding="utf-8")

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
            "cost": tracker.to_meta(),
        }
        if warnings:
            meta["warnings"] = warnings
        (post_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        posts.append({"dir": str(post_dir), "prompt_id": spec["id"]})

    return {
        "posts": posts,
        "caption": content["caption"],
        "hashtags": content["hashtags"],
        "cost": tracker.to_meta(),
        "mock": mock,
    }
