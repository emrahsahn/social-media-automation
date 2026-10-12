"""Sosyal medya içerik üretim pipeline'ı.

Modüller:
- config  : .env / API anahtarı yönetimi
- retry   : 429/5xx hatalarında exponential backoff ile yeniden deneme
- costs   : üretim başına maliyet hesabı ve meta.json kaydı
- formats : format sabitleri (tuval boyutu, API boyutu, oran)
- canvas  : hedef tuvale getirme (cover-resize + merkez kırpma)
- overlay : sabit konumda metin bindirme (wrap + auto-shrink)
- llm     : form payload → yapılandırılmış içerik (prompt/caption/hashtag)
- images  : görsel üretimi (OpenAI gpt-image-1 / mock)
- generate: uçtan uca akış orkestratörü
- cli     : komut satırı arayüzü (python -m pipeline.cli)
"""
