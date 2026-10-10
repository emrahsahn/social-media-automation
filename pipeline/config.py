""".env dosyasından ortam değişkeni / API anahtarı okuma.

Kullanım:
    from pipeline.config import get_api_key
    key = get_api_key("openai")   # yoksa anlaşılır MissingApiKeyError fırlatır
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

ENV_NAMES = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


class MissingApiKeyError(RuntimeError):
    """İstenen sağlayıcının API anahtarı ortamda/.env'de yok."""


def load_env(path: Path = ENV_PATH, *, override: bool = False) -> int:
    """`.env` dosyasını os.environ'a yükler.

    - Yorum (#) ve boş satırlar atlanır; `export KEY=...` ve tırnaklar desteklenir.
    - Varsayılan olarak mevcut ortam değişkenleri ezilmez (override=True ile ezilir).
    - Dönen değer: okunan satır sayısı. Dosya yoksa sessizce 0 döner.
    """
    loaded = 0
    if not path.exists():
        return loaded
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        # Satır içi yorumu at (" #..."), sonra tırnakları temizle
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
        loaded += 1
    return loaded


def get_api_key(provider: str) -> str:
    """Sağlayıcının API anahtarını döner; yoksa MissingApiKeyError fırlatır."""
    env_name = ENV_NAMES.get(provider.lower())
    if env_name is None:
        raise ValueError(
            f"Bilinmeyen sağlayıcı: {provider!r}. Desteklenenler: {', '.join(ENV_NAMES)}"
        )
    value = os.environ.get(env_name, "").strip()
    if not value:
        raise MissingApiKeyError(
            f"{env_name} bulunamadı. Çözüm: `.env.example` dosyasını `.env` olarak "
            f"kopyalayıp {env_name} değerini girin."
        )
    return value


def has_api_key(provider: str) -> bool:
    """Anahtar tanımlı mı? (arayüzde uyarı göstermek vb. için)"""
    try:
        get_api_key(provider)
    except (MissingApiKeyError, ValueError):
        return False
    return True


# Modül import edildiğinde .env'i bir kez yükle (dosya yoksa sessizce geçer).
load_env()
