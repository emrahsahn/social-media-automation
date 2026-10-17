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
    align = text_cfg.get("align", "center")
    side_pad = round(width * text_cfg["side_padding_ratio"])
    for line in lines:
        line_w = drawer.textlength(line, font=font)
        if align == "left":
            x = float(side_pad)
        elif align == "right":
            x = float(width - side_pad - line_w)
        else:  # center
            x = (width - line_w) / 2
        drawer.text((x, y), line, font=font, fill=fill)
        y += line_h

    return Image.alpha_composite(base, layer).convert("RGB")


def overlay_logo(
    img: Image.Image,
    logo: Image.Image,
    position: str = "top-right",
    scale: float = 0.16,
    opacity: float = 1.0,
    margin_ratio: float = 0.04,
) -> Image.Image:
    """`img` üzerine `logo` görselini belirtilen konum ve boyutta şeffaf olarak bindirir.

    Parametreler:
        img: Ana görsel (RGB veya RGBA)
        logo: Firma logosu (PNG, şeffaflık desteklenir)
        position: 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'top-center', 'center', 'bottom-center'
        scale: Logonun ana görsel genişliğine oranı (varsayılan 0.16 = %16)
        opacity: 0.0 - 1.0 arası saydamlık
        margin_ratio: Kenarlardan bırakılacak güvenli boşluk oranı
    """
    if logo is None:
        return img.convert("RGB").copy()

    width, height = img.size
    base = img.convert("RGBA")

    # 1. Logo boyutlandırma (en-boy oranını koruyarak)
    max_logo_w = max(round(width * scale), 30)
    logo_rgba = logo.convert("RGBA")
    orig_w, orig_h = logo_rgba.size
    if orig_w == 0 or orig_h == 0:
        return img.convert("RGB").copy()

    aspect = orig_h / orig_w
    target_w = max_logo_w
    target_h = max(round(target_w * aspect), 20)

    # Çok yüksek veya dikey logolarda boyu sınırla (en fazla görselin %18'i)
    max_logo_h = round(height * 0.18)
    if target_h > max_logo_h:
        target_h = max_logo_h
        target_w = max(round(target_h / aspect), 20)

    resample_filter = getattr(Image, "Resampling", Image).LANCZOS
    logo_resized = logo_rgba.resize((target_w, target_h), resample=resample_filter)

    # 2. Saydamlık uygulama
    if opacity < 1.0:
        r, g, b, a = logo_resized.split()
        a = a.point(lambda p: int(p * max(0.0, min(opacity, 1.0))))
        logo_resized = Image.merge("RGBA", (r, g, b, a))

    # 3. Konum koordinatları hesaplama
    margin = round(width * margin_ratio)
    pos = (position or "top-right").lower().strip()

    if pos in ("top-left", "sol-ust"):
        x = margin
        y = margin
    elif pos in ("top-center", "ust-orta"):
        x = round((width - target_w) / 2)
        y = margin
    elif pos in ("bottom-left", "sol-alt"):
        x = margin
        y = height - target_h - margin
    elif pos in ("bottom-right", "sag-alt"):
        x = width - target_w - margin
        y = height - target_h - margin
    elif pos in ("bottom-center", "alt-orta"):
        x = round((width - target_w) / 2)
        y = height - target_h - margin
    elif pos in ("center", "orta"):
        x = round((width - target_w) / 2)
        y = round((height - target_h) / 2)
    else:  # "top-right" / "sag-ust" (varsayılan)
        x = width - target_w - margin
        y = margin

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    layer.paste(logo_resized, (x, y), mask=logo_resized)

    return Image.alpha_composite(base, layer).convert("RGB")

