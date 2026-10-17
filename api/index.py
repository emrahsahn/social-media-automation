"""Vercel Serverless Function Giriş Noktası (WSGI/ASGI Adapter).

Vercel Python runtime'ı `api/index.py` içerisindeki `app` nesnesini
otomatik olarak ASGI/FastAPI uygulaması olarak algılar ve çalıştırır.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Proje kök dizinini Python yoluna ekle (böylece pipeline modülü sorunsuz yüklenir)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pipeline.web import app  # noqa: E402

__all__ = ["app"]
