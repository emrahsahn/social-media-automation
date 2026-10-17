"""Sosyal medya içerik üretim pipeline'ı.

Modüller:
- config  : .env / API anahtarı yönetimi
- retry   : 429/5xx hatalarında exponential backoff ile yeniden deneme
- costs   : üretim başına maliyet hesabı ve meta.json kaydı
- brand   : marka ayarları (brand.json: font, renk, pozisyon, taşma kuralları)
- reference: referans görsel stil çözümleme (plan B1)
- formats : format sabitleri (tuval boyutu, API boyutu, oran)
- canvas  : hedef tuvale getirme (cover-resize + merkez kırpma)
- overlay : sabit konumda metin bindirme (wrap + auto-shrink)
- llm     : form payload → yapılandırılmış içerik (prompt/caption/hashtag)
- images  : görsel üretimi (OpenAI DALL-E / mock)
- generate: uçtan uca akış orkestratörü
- cli     : komut satırı arayüzü (python -m pipeline.cli)
"""
