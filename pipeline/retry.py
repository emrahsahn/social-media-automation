"""429 (rate limit) ve 5xx (sunucu) hatalarında exponential backoff ile yeniden deneme.

Sağlayıcıdan bağımsız çalışır: istisnanın `.status_code` / `.status` /
`.response.status_code` alanlarına ve hata adına ("connection", "timeout")
bakarak karar verir. Gerekirse `is_retryable` parametresiyle kendi kararınızı
geçebilirsiniz.
"""

from __future__ import annotations

import random
import time
from typing import Callable

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


def _status_code(exc: Exception) -> int | None:
    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int):
        return value
    return None


def _retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or getattr(exc, "headers", None)
    if not headers:
        return None
    value = headers.get("retry-after") or headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def default_is_retryable(exc: Exception) -> bool:
    """Durum kodu 408/429/5xx ise ya da hata bir ağ/timeout hatasıysa True."""
    status = _status_code(exc)
    if status is not None:
        return status in RETRYABLE_STATUS
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    name = type(exc).__name__.lower()
    return "connection" in name or "timeout" in name


def call_with_retry(
    fn: Callable,
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    is_retryable: Callable[[Exception], bool] = default_is_retryable,
    on_retry: Callable[[int, float, Exception], None] | None = None,
    **kwargs,
):
    """`fn(*args, **kwargs)` çağırır; yeniden denenebilir hatada bekleyip tekrar dener.

    Bekleme süresi her denemede ikiye katlanır (base_delay, 2x, 4x ...), üst sınır
    max_delay'dir; küçük bir rastgele sapma (jitter) eklenir ve sunucu `Retry-After`
    başlığı gönderdiyse o süreye saygı duyulur.

    Denemeler tükenirse ya da hata yeniden denenemez türdeyse hata aynen fırlatılır.
    `on_retry(deneme_no, bekleme_sn, hata)` geri çağrısıyla loglama yapılabilir.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if not is_retryable(exc) or attempt == max_attempts:
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            delay *= 1 + random.uniform(0.0, 0.25)  # jitter: eşzamanlı istekleri dağıtır
            retry_after = _retry_after_seconds(exc)
            if retry_after is not None:
                delay = max(delay, retry_after)
            if on_retry is not None:
                on_retry(attempt, delay, exc)
            time.sleep(delay)
