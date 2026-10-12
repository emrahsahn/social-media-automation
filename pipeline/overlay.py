"""Görselin alt kısmına sabit konumda metin bindirme.

Tüm marka ayarları (font, renk, pozisyon, gradient, taşma kuralları)
`brand.json` dosyasından okunur (bkz. pipeline/brand.py). Kurallar:
- Font Türkçe karakterleri desteklemeli; `font.file` bulunamazsa `fallbacks`
  listesi sırayla denenir.
- Uzun metin word-wrap ile bölünür; satır limiti (max_lines) aşılırsa punto
  kademeli küçültülür (auto-shrink); hâlâ sığmıyorsa ValueError fırlatılır.
- Karakter limiti (max_chars) akışa girmeden generate.py tarafından doğrulanır.
- Okunabilirlik için alt kısımda dikey gradient şerit bindirilir.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from pipeline.brand import load_brand

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_font_path(font_cfg: dict) -> Path:
    """brand.json font ayarından ilk bulunan TTF yolunu döner; yoksa hata."""
    candidates: list[str] = []
    if font_cfg.get("file"):
        candidates.append(font_cfg["file"])
    candidates.extend(font_cfg.get("fallbacks") or [])
    for candidate in candidates:
        path = Path(candidate)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Uygun font bulunamadı. brand.json `font.file` yolunu kontrol edin veya "
        "assets/fonts altına Türkçe destekli bir TTF koyun."
    )


def _wrap(
    text: str, font: ImageFont.FreeTypeFont, max_width: int, drawer: ImageDraw.ImageDraw
) -> list[str]:
    """Kelime bazlı satır kaydırma; satır genişlikleri max_width'i aşmaz."""
    lines: list[str] = []
    for paragraph in text.splitlines():
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if drawer.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def overlay_text(img: Image.Image, text: str, brand: dict | None = None) -> Image.Image:
    """`img`nin altına gradient şerit + metni bindirir; yeni RGB görüntü döner.

    Metin verilen stilde (satır limiti + genişlik) sığmıyorsa ValueError
    fırlatır — çağıran taraf kullanıcıyı uyarıp akışa devam edebilir.
    """
    cfg = brand or load_brand()
    font_cfg, text_cfg, strip_cfg = cfg["font"], cfg["text"], cfg["strip"]
    text = (text or "").strip()
    if not text:
        return img.convert("RGB").copy()

    width, height = img.size
    base = img.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    drawer = ImageDraw.Draw(layer)

    # 1) Gradient şerit: alttan yukarı doğru saydamlaşan bant
    strip_h = round(height * strip_cfg["height_ratio"])
    strip_top = height - strip_h
    r, g, b = strip_cfg["color"]
    for y in range(strip_h):
        alpha = round(strip_cfg["max_alpha"] * (y / max(strip_h - 1, 1)))
        drawer.line([(0, strip_top + y), (width, strip_top + y)], fill=(r, g, b, alpha))

    # 2) Font + auto-shrink: puntoyu kademeli küçült, satır limitine oturana dek
    font_path = resolve_font_path(font_cfg)
    scale = width / font_cfg["size_reference_width"]
    size = max(round(font_cfg["size_base"] * scale), 12)
    min_size = max(round(font_cfg["size_min"] * scale), 12)
    max_width = width - round(width * text_cfg["side_padding_ratio"] * 2)
    max_lines = text_cfg["max_lines"]
    font: ImageFont.FreeTypeFont | None = None
    lines: list[str] = []
    while size >= min_size:
        font = ImageFont.truetype(str(font_path), size)
        lines = _wrap(text, font, max_width, drawer)
        if len(lines) <= max_lines:
            break
        size = max(round(size * 0.9), min_size)
    if font is None or len(lines) > max_lines:
        raise ValueError(
            f"Metin {max_lines} satıra sığmıyor (min punto {min_size} denendi): "
            f"{text[:50]}{'…' if len(text) > 50 else ''}"
        )

    # 3) Metni çiz: bloğun alt kenarı sabit oranda yukarıda, yatayda ortalanmış
    line_h = size * text_cfg["line_spacing"]
    block_h = line_h * len(lines)
    block_bottom = height - round(height * text_cfg["bottom_margin_ratio"])
    y = block_bottom - block_h
    fill = tuple(text_cfg["color"])
    for line in lines:
        line_w = drawer.textlength(line, font=font)
        x = (width - line_w) / 2
        drawer.text((x, y), line, font=font, fill=fill)
        y += line_h

    return Image.alpha_composite(base, layer).convert("RGB")
