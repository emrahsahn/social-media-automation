"""Marka ayarları: `brand.json` tek kaynak noktasıdır.

Dosya yoksa ya da bazı alanlar eksikse DEFAULTS ile birleştirilir; böylece
config yarım kalsa bile akış çalışır. Renkler #RRGGBB yazılır ve okunurken
RGB tuple'a çevrilir.
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.config import PROJECT_ROOT

BRAND_PATH = PROJECT_ROOT / "brand.json"

DEFAULTS: dict = {
    "font": {
        "file": None,
        "fallbacks": ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        "size_base": 68,
        "size_min": 34,
        "size_reference_width": 1080,
    },
    "text": {
        "color": "#FFFFFF",
        "max_chars": 60,
        "max_lines": 3,
        "align": "center",
        "bottom_margin_ratio": 0.16,
        "side_padding_ratio": 0.055,
        "line_spacing": 1.18,
    },
    "strip": {"color": "#000000", "max_alpha": 165, "height_ratio": 0.34},
}


def _deep_merge(base: dict, extra: dict) -> dict:
    """`extra`yı `base` üzerine derinlemesine yazar (iç içe sözlükler korunur)."""
    out = dict(base)
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    """'#RRGGBB' → (r, g, b); geçersiz değerde anlaşılır hata."""
    text = str(value).strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"Geçersiz renk değeri: {value!r} (#RRGGBB beklenir)")
    try:
        return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"Geçersiz renk değeri: {value!r} (#RRGGBB beklenir)") from exc


def load_brand(path: Path = BRAND_PATH) -> dict:
    """brand.json'u okur, varsayılanlarla birleştirir, renkleri tuple yapar."""
    data: dict = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    brand = _deep_merge(DEFAULTS, data)
    brand["text"]["color"] = hex_to_rgb(brand["text"]["color"]) + (255,)
    brand["strip"]["color"] = hex_to_rgb(brand["strip"]["color"])
    return brand
