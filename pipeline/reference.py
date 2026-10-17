"""Referans görsel analizi (plan B1: image-to-text köprüsü).

Vision LLM referans görseli çözümler: stil özeti, kompozisyon, ışık, renk
paleti, ton ve kamera açısı. Bu tarif üretilen prompt'lara dahil edilir —
referans kopyalanmaz, yalnızca stili aktarılır (bkz. plan: Referans Görsel).

`mock=True` iken LLM yerine PIL tabanlı deterministik analiz yapılır
(baskın renkler + parlaklık + oran); böylece akış API anahtarı olmadan da
uçtan uca test edilir. B2 (doğrudan edit) için görselin kendisi
`images.generate_image(..., reference_image=...)` ile API'ye verilir.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from PIL import Image

from pipeline.config import get_api_key
from pipeline.llm import DEFAULT_ANTHROPIC_MODEL, DEFAULT_TEXT_MODEL
from pipeline.retry import call_with_retry

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_REFERENCE_BYTES = 10 * 1024 * 1024  # plan: maks. 10 MB

_MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

ANALYSIS_SCHEMA = {
    "name": "reference_style_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["style_summary", "composition", "lighting", "color_palette", "mood", "camera"],
        "properties": {
            "style_summary": {"type": "string"},
            "composition": {"type": "string"},
            "lighting": {"type": "string"},
            "color_palette": {"type": "array", "items": {"type": "string"}},
            "mood": {"type": "string"},
            "camera": {"type": "string"},
        },
    },
}

ANALYSIS_PROMPT = (
    "Analyze this image as a style guide. I will write prompts to generate new "
    "images on a DIFFERENT subject that share this style. Extract: overall style "
    "summary, composition, lighting, color palette (3-6 named or hex colors), "
    "mood/atmosphere, and camera angle. Short English phrases. Do not describe "
    "the specific subject, only transferable style traits."
)


def validate_reference_image(path_like) -> Path:
    """Referans dosyasını doğrular (varlık, uzantı, boyut); yoksa anlaşılır hata."""
    path = Path(path_like)
    if not path.is_file():
        raise ValueError(f"Referans görsel bulunamadı: {path}")
    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Referans görsel formatı desteklenmiyor: {ext!r} "
            f"(izin verilenler: {', '.join(sorted(ALLOWED_EXTENSIONS))})"
        )
    size = path.stat().st_size
    if size > MAX_REFERENCE_BYTES:
        raise ValueError(
            f"Referans görsel çok büyük: {size / 1024 / 1024:.1f} MB "
            f"(maks. {MAX_REFERENCE_BYTES // 1024 // 1024} MB)"
        )
    return path


def _mock_analyze(img: Image.Image) -> dict:
    """PIL tabanlı deterministik analiz: baskın renkler + parlaklık + boyut."""
    small = img.convert("RGB").resize((64, 64))
    quantized = small.quantize(colors=5).convert("RGB")
    counts = quantized.getcolors(64 * 64) or []
    hexes = ["#%02X%02X%02X" % rgb for _, rgb in sorted(counts, reverse=True)]

    gray = small.convert("L")
    hist = gray.histogram()
    total = sum(hist) or 1
    mean = sum(i * c for i, c in enumerate(hist)) / total
    brightness = "bright" if mean > 170 else "dark" if mean < 85 else "medium-bright"

    return {
        "style_summary": (
            f"Mock style analysis: dominant colors {', '.join(hexes[:3])}, "
            f"{brightness} overall exposure"
        ),
        "composition": f"center-weighted composition ({img.width}x{img.height} frame)",
        "lighting": f"even {brightness} lighting",
        "color_palette": hexes[:5],
        "mood": "neutral",
        "camera": "front-facing",
    }


def analyze_reference(
    path_like,
    *,
    mock: bool = False,
    provider: str = "openai",
) -> tuple[dict, dict]:
    """Referans görseli çözümler; `(analysis, usage)` döner.

    `analysis`: style_summary/composition/lighting/color_palette/mood/camera
    `usage`: maliyet kaydı için {"provider", "model", "input_tokens", "output_tokens"}
    """
    path = validate_reference_image(path_like)
    img = Image.open(path)

    if mock:
        analysis = _mock_analyze(img)
        text = json.dumps(analysis, ensure_ascii=False)
        tokens = max(1, (len(text) + 512) // 4)  # görsel tahmini + metin (~4 karakter/token)
        usage = {
            "provider": "mock",
            "model": "mock-vision",
            "input_tokens": tokens,
            "output_tokens": tokens // 4,
        }
        return analysis, usage

    provider = provider.lower()
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = _MIME_BY_EXT[path.suffix.lower()]

    if provider == "anthropic":
        get_api_key("anthropic")
        import anthropic

        client = anthropic.Anthropic()
        prompt_with_schema = (
            ANALYSIS_PROMPT
            + "\n\nRESPONSE FORMAT: Output ONLY a single JSON object matching this schema:\n"
            + json.dumps(ANALYSIS_SCHEMA["schema"])
        )

        def _call_anthropic():
            return client.messages.create(
                model=DEFAULT_ANTHROPIC_MODEL,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_with_schema},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime,
                                    "data": b64,
                                },
                            },
                        ],
                    }
                ],
                temperature=0.3,
            )

        resp = call_with_retry(_call_anthropic)
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:].strip()
        analysis = json.loads(raw)
        usage = {
            "provider": "anthropic",
            "model": DEFAULT_ANTHROPIC_MODEL,
            "input_tokens": getattr(resp.usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(resp.usage, "output_tokens", 0) or 0,
        }
        return analysis, usage

    if provider == "openai":
        get_api_key("openai")
        from openai import OpenAI

        client = OpenAI()

        def _call_openai():
            return client.chat.completions.create(
                model=DEFAULT_TEXT_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": ANALYSIS_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ],
                    }
                ],
                response_format={"type": "json_schema", "json_schema": ANALYSIS_SCHEMA},
                temperature=0.3,
            )

        resp = call_with_retry(_call_openai)
        analysis = json.loads(resp.choices[0].message.content)
        usage_obj = resp.usage
        usage = {
            "provider": "openai",
            "model": DEFAULT_TEXT_MODEL,
            "input_tokens": getattr(usage_obj, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(usage_obj, "completion_tokens", 0) or 0,
        }
        return analysis, usage

    raise ValueError(f"Desteklenmeyen Vision sağlayıcısı: {provider!r}. 'openai' veya 'anthropic' seçin.")
