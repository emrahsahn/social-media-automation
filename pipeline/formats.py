"""Format tanımları: hedef tuval boyutu + image API'sine istenecek native boyut.

Image API'lerinin native boyutları (1024x1024, 1024x1536 ...) hedef tuvallerle
birebir örtüşmez; bu yüzden API'den en yakın boyut istenir, seçim sonrası
canvas.to_canvas() ile hedef tuvale kırpılır (bkz. plan: Boyut Standardizasyonu).
"""

from __future__ import annotations

from typing import NamedTuple


class FormatSpec(NamedTuple):
    key: str
    canvas: tuple[int, int]  # hedef tuval (metin bindirme bu boyutta yapılır)
    api_size: str            # image API'sinden istenen en yakın native boyut
    aspect_ratio: str        # LLM prompt'una eklenen oran bilgisi


FORMATS: dict[str, FormatSpec] = {
    "post_1x1": FormatSpec("post_1x1", (1080, 1080), "1024x1024", "1:1"),
    "post_4x5": FormatSpec("post_4x5", (1080, 1350), "1024x1536", "4:5"),
    "story_9x16": FormatSpec("story_9x16", (1080, 1920), "1024x1536", "9:16"),
    "reels_cover_9x16": FormatSpec("reels_cover_9x16", (1080, 1920), "1024x1536", "9:16"),
}

# Form dropdown değerleri (bkz. plan: Kullanıcı Girdi Formu)
STYLES = ("product_photo", "lifestyle", "illustration", "minimal_flat")

# gpt-image-1 kalite kademeleri; maliyeti doğrudan etkiler (bkz. costs.py)
QUALITIES = ("auto", "low", "medium", "high")


def get_format(key: str) -> FormatSpec:
    """Format anahtarını döner; bilinmeyen anahtarda anlaşılır hata fırlatır."""
    spec = FORMATS.get(key)
    if spec is None:
        raise ValueError(
            f"Bilinmeyen format: {key!r}. Desteklenenler: {', '.join(FORMATS)}"
        )
    return spec
