# Sosyal Medya Otomasyon — Instagram İçerik Stüdyosu

Tek bir temadan (konu/metin) Instagram için hazır gönderi paketleri üreten uçtan uca içerik hattı: LLM destekli görsel promptu + caption + hashtag üretimi, DALL-E görsel üretimi, marka kimliğine göre metin ve logo bindirme, ve tarayıcıda çalışan tek sayfalık bir Web Stüdyo.

```
Form → LLM (prompt + caption + hashtag) → DALL-E → Tuval → Marka overlay → outputs/YYYY-MM-DD/post-N
```

## Nasıl Çalışır

1. **Form** — konu, stil, format, kaplama metni, notlar; opsiyonel referans görsel ve logo.
2. **LLM katmanı** — istenen adet kadar birbirinden varyasyonlu görsel promptu (İngilizce), Türkçe caption ve 5-10 hashtag üretir. OpenAI structured outputs ile JSON şemasına zorlanır; Anthropic de desteklenir.
3. **Görsel katmanı** — DALL-E görseli üretir; hedef tuvale cover-resize + merkez kırpma uygulanır.
4. **Marka katmanı** — `brand.json` tek kaynak: renkler, font, satır limiti, alt şerit ve hizalama kurallarıyla metin ve logo bindirilir.
5. **Çıktı** — her varyasyon için klasör: `background.png`, `final.png`, `caption.txt`, `meta.json` (model bilgisi + tahmini maliyet dahil).

## Özellikler

- **Web Stüdyo** — giriş ekranı, üretim formu, telefon mockup'ında canlı önizleme, anlık metin/logo düzenleme, tekil yeniden üretim, caption/hashtag düzenleme, geçmiş galerisi ve tek tıkla Instagram boyutunda indirme.
- **Referans görsel** — B1: vision LLM ile stil çözümlemesi (kompozisyon, ışık, palet) yeni konuya aktarılır; B2: görselin kendisi DALL-E 2 edit çağrısına girer.
- **Mock mod** — API anahtarı ve harcama olmadan, deterministik sahte üretimle uçtan uca akışı test eder.
- **Maliyet takibi** — token ve görsel başına tahmini USD, gönderi başına `meta.json`'a yazılır.
- **CLI** — tek komutla üretim, script/otomasyon dostu.
- **Oturum güvenliği** — imzalı ve süreli oturum tokenları, üretimde zorunlu `SESSION_SECRET`, 10 MB yükleme sınırı, giriş hız sınırı.
- **Test** — 36 pytest senaryosu (hat, tuval, overlay, referans, web/auth akışları).

## Desteklenen Formatlar

| Format | Tuval | Kullanım |
|---|---|---|
| `post_4x5` | 1080x1350 | Instagram gönderi |
| `post_1x1` | 1080x1080 | Kare gönderi |
| `story_9x16` | 1080x1920 | Hikaye |
| `reels_cover_9x16` | 1080x1920 | Reels kapağı |

## Kurulum

```bash
git clone https://github.com/emrahsahn/social-media-automation.git
cd social-media-automation
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

`.env` dosyasında kullanacağın sağlayıcının anahtarını doldur:

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
APP_PASSWORD=güçlü-bir-şifre        # boşsa yerelde varsayılan: admin
SESSION_SECRET=rastgele-64-hex      # python -c "import secrets; print(secrets.token_hex(32))"
```

## Kullanım

**Web Stüdyo**

```bash
run_web.bat
# veya
.venv\Scripts\python -m pipeline.web
```

Ardından `http://localhost:8000` adresini aç.

**CLI**

```bash
# Anahtar/harcama gerektirmez
.venv\Scripts\python -m pipeline.cli --topic "Yeni sezon kahve" --mock

# Gerçek üretim
.venv\Scripts\python -m pipeline.cli --topic "Yeni sezon kahve" ^
    --count 3 --format post_4x5 ^
    --overlay-text "Yeni sezon, yeni lezzet" ^
    --style product_photo --quality hd
```

## Marka Ayarları

`brand.json` tüm görsel kimliğin tek kaynağıdır: metin rengi ve hizalaması, karakter/satır limitleri, alt şerit rengi ve yüksekliği, font dosyası ve boyut ölçekleme kuralları. Dosya eksikse güvenli varsayılanlarla çalışır.

## Testler

```bash
.venv\Scripts\python -m pytest tests/
```

## Vercel'e Dağıtım

Depo Vercel hazır: `api/index.py` giriş noktası, `vercel.json` rewrite kuralları ve `.vercelignore` dahil.

Vercel panelinde şu ortam değişkenlerini tanımla:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `APP_PASSWORD` (güçlü bir şifre; üretimde zorunlu)
- `SESSION_SECRET` (rastgele 64 hex — yereldekiyle aynı olmasın)
- `ALLOWED_ORIGINS` (örn. `https://proje-adin.vercel.app`)

Not: Vercel'in serverless dosya sistemi istekler arasında kalıcı değildir; üretilen çıktıların kalıcı olması için Vercel Blob/S3 gibi bir depolama entegrasyonu gerekir.

## Proje Yapısı

```
├── api/index.py            # Vercel serverless giriş noktası
├── pipeline/
│   ├── web.py              # FastAPI stüdyo sunucusu
│   ├── web_static/         # tek sayfalık arayüz
│   ├── cli.py              # komut satırı üretimi
│   ├── generate.py         # uçtan uca üretim akışı
│   ├── llm.py              # prompt / caption / hashtag üretimi
│   ├── images.py           # DALL-E + mock görsel üretici
│   ├── reference.py        # referans görsel stil analizi
│   ├── canvas.py           # tuval, kırpma, data-url dönüşümü
│   ├── overlay.py          # metin + logo bindirme
│   ├── brand.py            # brand.json yükleyici
│   ├── config.py           # .env ve oturum yönetimi
│   ├── formats.py          # format / stil / kalite tanımları
│   ├── retry.py            # 429/5xx yeniden deneme
│   └── costs.py            # maliyet takibi
├── tests/                  # 36 pytest senaryosu
├── brand.json              # marka kimliği (tek kaynak)
└── outputs/                # üretilen gönderiler (repoya girmez)
```
