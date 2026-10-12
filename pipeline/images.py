"""Görsel üretim: OpenAI gpt-image-1 veya mock üretici.

Mock üretici, prompt'tan türetilen deterministik (aynı prompt → aynı görsel)
gradyan + yumuşak lekelerden oluşan metinsiz bir arka plan üretir; böylece
tam akış API harcaması olmadan test edilebilir.
"""

from __future__ import annotations

import base64
import colorsys
import io
import random

from PIL import Image, ImageDraw, ImageFilter

from pipeline.config import get_api_key
from pipeline.retry import call_with_retry

DEFAULT_IMAGE_MODEL = "gpt-image-1"


def _mock_image_bytes(size_str: str, seed_text: str) -> bytes:
    """`seed_text`e bağlı deterministik, metinsiz gradyan arka plan üretir."""
    w, h = (int(v) for v in size_str.lower().split("x"))
    rng = random.Random(seed_text)
    hue1 = rng.randrange(360)
    hue2 = (hue1 + rng.randrange(60, 180)) % 360
    top = colorsys.hsv_to_rgb(hue1 / 360, 0.45, 0.92)
    bottom = colorsys.hsv_to_rgb(hue2 / 360, 0.55, 0.75)

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        col = tuple(round((a + (b - a) * t) * 255) for a, b in zip(top, bottom))
        draw.line([(0, y), (w, y)], fill=col)

    # Yumuşak ışık lekeleri (doku hissi için; metin yok)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(layer)
    min_side = min(w, h)
    for _ in range(4):
        radius = rng.randrange(min_side // 6, min_side // 3)
        x = rng.randrange(-radius, w)
        y = rng.randrange(-radius, h)
        shade = (255, 255, 255, 38) if rng.random() < 0.5 else (25, 25, 60, 38)
        ldraw.ellipse([x, y, x + 2 * radius, y + 2 * radius], fill=shade)
    layer = layer.filter(ImageFilter.GaussianBlur(min_side // 10))
    img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_image(
    prompt: str,
    *,
    size: str,
    quality: str = "medium",
    mock: bool = False,
    model: str = DEFAULT_IMAGE_MODEL,
) -> tuple[bytes, dict]:
    """Tek görsel üretir; `(png_bytes, meta)` döner.

    `meta`: maliyet/istatistik kaydı için {"provider", "model", "size", "quality"}.
    """
    if mock:
        png = _mock_image_bytes(size, prompt)
        return png, {"provider": "mock", "model": "mock-image", "size": size, "quality": quality}

    get_api_key("openai")
    from openai import OpenAI

    client = OpenAI()

    def _call():
        return client.images.generate(model=model, prompt=prompt, size=size, quality=quality)

    resp = call_with_retry(_call)
    b64 = getattr(resp.data[0], "b64_json", None)
    if not b64:
        raise RuntimeError("OpenAI görsel yanıtında b64_json alanı yok")
    meta = {"provider": "openai", "model": model, "size": size, "quality": quality}
    return base64.b64decode(b64), meta
