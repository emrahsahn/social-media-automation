"""Form girdisinden yapılandırılmış içerik üretimi: görsel prompt'ları + caption + hashtag.

LLM bir "prompt mühendisi" gibi çalışır: form payload'ını alır, görsel sayısı
kadar birbirinden hafif farklı prompt, bir caption ve hashtag listesi üretir.
Yanıt OpenAI structured outputs ile JSON şemasına zorlanır (bkz. plan:
Form → Prompt Dönüşümü). `mock=True` iken anahtar/harcama gerekmez.
"""

from __future__ import annotations

import json

from pipeline.config import get_api_key
from pipeline.formats import FORMATS
from pipeline.retry import call_with_retry

DEFAULT_TEXT_MODEL = "gpt-4o"
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

DEFAULT_SYSTEM_PROMPT = """Sen bir sosyal medya içerik üreticisi ve görsel prompt mühendisisin.
Kullanıcının form girdisinden şunları üretirsin:
1. "prompts": istenen görsel sayısı kadar, İngilizce yazılmış, detaylı görsel üretim prompt'u.
   - Prompt'lar birbirinden hafif farklı olmalı (kompozisyon, açı veya ışık varyasyonu).
   - Kompozisyon merkezde tutulmalı; görsel sonradan hafifçe kırpılabilir.
   - Her prompt MUTLAKA "no text, no letters, no words, no logos, no watermarks"
     ifadesini içermeli; metin sonradan kod ile bindirilecek.
2. "caption": Türkçe, samimi ama profesyonel tonda 1-3 cümle.
3. "hashtags": 5-10 adet, # ile başlayan Türkçe hashtag.
4. Girdide `style_analysis` alanı varsa (referans görselin stil çözümlemesi):
   her prompt bu stil özelliklerini yansıtmalı (kompozisyon, ışık, renk paleti, ton).
   Konu yine formdaki tema olmalı; referans görselin kendisi kopyalanmamalı,
   yalnızca stili aktarılmalı.
Sadece verilen JSON şemasına uygun yanıt ver."""

# Geriye dönük uyumluluk
SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT


def get_system_prompt(custom_prompt: str | None = None) -> str:
    """Kullanıcı tanımlı veya varsayılan sistem promptunu döner."""
    if not custom_prompt or not custom_prompt.strip():
        return DEFAULT_SYSTEM_PROMPT

    user_text = custom_prompt.strip()
    safety_rules = (
        "\n\n[SİSTEM TEKNİK ZORUNLULUKLARI]:\n"
        "- Prompts dizisindeki her prompt MUTLAKA 'no text, no letters, no words, no logos, no watermarks' ifadesini içermelidir (metin sonradan kod ile bindirilir).\n"
        "- Kompozisyon merkezde tutulmalıdır.\n"
        "- Sadece ve sadece belirtilen JSON şemasına uygun tek bir JSON yanıtı verilmelidir."
    )
    if "no text" not in user_text.lower():
        user_text += safety_rules
    return user_text

JSON_SCHEMA = {
    "name": "social_post_content",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["prompts", "caption", "hashtags"],
        "properties": {
            "prompts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "prompt", "aspect_ratio"],
                    "properties": {
                        "id": {"type": "integer"},
                        "prompt": {"type": "string"},
                        "aspect_ratio": {"type": "string"},
                    },
                },
            },
            "caption": {"type": "string"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
        },
    },
}

# Mock modda kullanılan sabit sahne tarifleri (kompozisyon/açı/ışık varyasyonu)
_MOCK_SCENES = (
    "Soft natural window light, front-facing composition, shallow depth of field",
    "Warm golden hour side light, slight top-down angle, airy atmosphere",
    "Clean studio lighting, straight-on centered composition, minimal shadows",
    "Moody ambient evening light, close-up macro angle, cozy tones",
)

# Kaba token tahmini (mock maliyet kaydı için): ~4 karakter = 1 token
_EST_CHARS_PER_TOKEN = 4


def _user_message(payload: dict) -> str:
    """Form payload'ını LLM'e gidecek JSON mesaja çevirir."""
    return json.dumps(payload, ensure_ascii=False)


def _validate_content(content: dict, expected_count: int) -> dict:
    """Şema dışı/eksik yanıtı erken yakalar; aksi halde hatayı API'ye kadar taşırız."""
    prompts = content.get("prompts")
    if not isinstance(prompts, list) or len(prompts) < expected_count:
        raise ValueError(
            f"LLM {expected_count} prompt yerine {len(prompts) if isinstance(prompts, list) else 0} döndürdü"
        )
    if not content.get("caption") or not isinstance(content.get("hashtags"), list):
        raise ValueError("LLM yanıtta caption veya hashtags eksik")
    return content


def mock_content(payload: dict) -> tuple[dict, dict]:
    """Anahtar gerektirmeyen deterministik içerik (test amaçlı)."""
    topic = (payload.get("topic") or "test gönderisi").strip()
    count = max(1, int(payload.get("image_count") or 2))
    spec = FORMATS[payload.get("format", "post_4x5")]
    style = payload.get("style_analysis") or {}
    style_part = ""
    if style:
        style_part = (
            f" Style reference: {style.get('style_summary', '')}. "
            f"Lighting: {style.get('lighting', '')}. "
            f"Composition: {style.get('composition', '')}."
        )
    prompts = [
        {
            "id": i,
            "prompt": (
                f"{_MOCK_SCENES[(i - 1) % len(_MOCK_SCENES)]}. "
                f"Subject related to: {topic}. Aspect ratio {spec.aspect_ratio}."
                f"{style_part} "
                "No text, no letters, no words, no logos, no watermarks."
            ),
            "aspect_ratio": spec.aspect_ratio,
        }
        for i in range(1, count + 1)
    ]
    caption = f"{topic} — mock modda üretilmiş örnek gönderi metni."
    hashtags = ["#mock", "#test", "#icerikuretimi"]
    content = {"prompts": prompts, "caption": caption, "hashtags": hashtags}
    meta_text = _user_message(payload) + json.dumps(content, ensure_ascii=False)
    tokens = max(1, len(meta_text) // _EST_CHARS_PER_TOKEN)
    usage = {
        "provider": "mock",
        "model": "mock-llm",
        "input_tokens": tokens // 2,
        "output_tokens": tokens - tokens // 2,
    }
    return content, usage

def generate_content(
    payload: dict,
    *,
    mock: bool = False,
    provider: str = "openai",
    model: str | None = None,
) -> tuple[dict, dict]:
    """Payload'dan içerik üretir; `(content, usage)` döner.

    `content`: {"prompts": [...], "caption": str, "hashtags": [...]}
    `usage`: maliyet kaydı için {"provider", "model", "input_tokens", "output_tokens"}
    """
    if mock:
        return mock_content(payload)

    provider = provider.lower()
    sys_prompt = get_system_prompt(payload.get("system_prompt"))

    if provider == "anthropic":
        get_api_key("anthropic")
        import anthropic

        client = anthropic.Anthropic()
        target_model = model or DEFAULT_ANTHROPIC_MODEL
        anthropic_system = (
            sys_prompt
            + "\n\nYANIT FORMATI: Sadece ve sadece şu JSON yapısına uyan tek bir geçerli JSON nesnesi ver. "
            + 'Markdown blokları (```json) veya ekstra metin ekleme:\n'
            + '{"prompts": [{"id": 1, "prompt": "...", "aspect_ratio": "4:5"}], "caption": "...", "hashtags": ["#tag1"]}'
        )

        def _call_anthropic():
            return client.messages.create(
                model=target_model,
                max_tokens=2048,
                system=anthropic_system,
                messages=[{"role": "user", "content": _user_message(payload)}],
                temperature=0.7,
            )

        resp = call_with_retry(_call_anthropic)
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:].strip()
        content = _validate_content(json.loads(raw), int(payload.get("image_count") or 2))
        usage = {
            "provider": "anthropic",
            "model": target_model,
            "input_tokens": getattr(resp.usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(resp.usage, "output_tokens", 0) or 0,
        }
        return content, usage

    if provider == "openai":
        get_api_key("openai")  # anahtar yoksa en başta anlaşılır hata
        from openai import OpenAI

        client = OpenAI()
        target_model = model or DEFAULT_TEXT_MODEL

        def _call_openai():
            return client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": _user_message(payload)},
                ],
                response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
                temperature=0.8,
            )

        resp = call_with_retry(_call_openai)
        raw = resp.choices[0].message.content
        content = _validate_content(json.loads(raw), int(payload.get("image_count") or 2))
        usage = resp.usage
        meta = {
            "provider": "openai",
            "model": target_model,
            "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
        }
        return content, meta

    raise ValueError(f"Desteklenmeyen LLM sağlayıcısı: {provider!r}. 'openai' veya 'anthropic' seçin.")
