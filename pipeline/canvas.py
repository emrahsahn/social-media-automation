"""Görseli hedef tuvale getirme: oranı bozmadan doldur, fazlalığı merkezden kırp.

Kompozisyonun merkezde kalması prompt'larda zaten istenir; buradaki kırpma
böylece kritik içerik kaybı yaratmadan hedef boyutu garanti eder.
"""

from __future__ import annotations

from PIL import Image


def to_canvas(img: Image.Image, width: int, height: int) -> Image.Image:
    """`img`yi hedef `width x height` tuvale getirir (cover-resize + merkez kırpma)."""
    if img.width == width and img.height == height:
        return img.copy()
    src_ratio = img.width / img.height
    dst_ratio = width / height
    if src_ratio > dst_ratio:
        # Kaynak daha geniş: yüksekliğe göre ölçekle, kenarlardan kırp
        new_h = height
        new_w = round(img.width * height / img.height)
    else:
        # Kaynak daha uzun: genişliğe göre ölçekle, üst/alttan kırp
        new_w = width
        new_h = round(img.height * width / img.width)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return resized.crop((left, top, left + width, top + height))


def image_to_data_url(img: Image.Image, format: str = "JPEG", quality: int = 95) -> str:
    """PIL görselini yüksek kaliteli, optimize edilmiş Data URL'e (JPEG/PNG) dönüştürür."""
    import base64
    from io import BytesIO

    buf = BytesIO()
    fmt_upper = format.upper()
    if fmt_upper in ("JPEG", "JPG"):
        if img.mode in ("RGBA", "LA", "P"):
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                rgb_img.paste(img, mask=img.split()[3])
            else:
                rgb_img.paste(img.convert("RGB"))
            rgb_img.save(buf, format="JPEG", quality=quality, optimize=True)
        else:
            img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:
        img.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def data_url_to_image(data_url: str) -> Image.Image:
    """data:image/...;base64,... dizesini PIL Image nesnesine dönüştürür."""
    import base64
    from io import BytesIO

    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    raw = base64.b64decode(data_url)
    return Image.open(BytesIO(raw))

