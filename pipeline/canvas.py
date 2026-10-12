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
