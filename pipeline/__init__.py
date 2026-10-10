"""Sosyal medya içerik üretim pipeline'ı.

Modüller:
- config: .env / API anahtarı yönetimi
- retry : 429/5xx hatalarında exponential backoff ile yeniden deneme
- costs : üretim başına maliyet hesabı ve meta.json kaydı
"""
