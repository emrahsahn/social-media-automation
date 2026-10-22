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


import hashlib
import hmac
import time

_SESSION_SALT = "sosyal-medya-otomasyon-secure-salt-2026"


def _is_vercel() -> bool:
    return bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))


def get_session_secret() -> str:
    """Oturum token'larını imzalayan anahtarı döner.

    Vercel veya yerel ortamda SESSION_SECRET tanımlıysa o kullanılır;
    tanımlı değilse varsayılan güvenli tuz kullanılır (böylece 500 hatasıyla çökmez).
    """
    secret = os.environ.get("SESSION_SECRET", "").strip()
    if secret:
        return secret
    return _SESSION_SALT


def get_app_password() -> str:
    """Ortam değişkeninden veya .env'den tanımlı uygulama şifresini döner.
    Ortamda tanımlı değilse varsayılan olarak 'admin' döner.
    """
    if "APP_PASSWORD" in os.environ:
        return os.environ["APP_PASSWORD"].strip()
    return "admin"


def is_auth_required() -> bool:
    """Uygulama şifresi kontrolü gerekliliği."""
    return bool(get_app_password())


def create_session_token(expires_in_seconds: int = 86400 * 7) -> str:
    """Geçerli şifre için süreli ve imzalı oturum belirteci üretir (varsayılan 7 gün)."""
    pwd = get_app_password()
    secret = get_session_secret()
    exp = int(time.time()) + expires_in_seconds
    payload = f"{pwd}:{exp}"
    sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def verify_app_password(password: str) -> bool:
    """Verilen şifre APP_PASSWORD ile eşleşiyor mu?"""
    expected = get_app_password()
    if not expected:
        return True
    return hmac.compare_digest(password.strip(), expected)


def verify_session_token(token: str) -> bool:
    """Gelen oturum belirteci geçerli mi ve süresi dolmamış mı?"""
    if not is_auth_required():
        return True
    if not token:
        return False
    pwd = get_app_password()
    secret = get_session_secret()

    # Yalnızca süreli format kabul edilir: "exp.sig"
    if "." not in token:
        return False
    parts = token.split(".", 1)
    if len(parts) != 2 or not parts[0].isdigit():
        return False
    exp = int(parts[0])
    if time.time() > exp:
        return False  # Süresi dolmuş oturum
    payload = f"{pwd}:{exp}"
    expected_sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(parts[1], expected_sig)


# Modül import edildiğinde .env'i bir kez yükle (dosya yoksa sessizce geçer).
load_env()
