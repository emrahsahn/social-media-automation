# Sosyal Medya İçerik Üretim Aracı — Proje Planı

## Özet

LLM API'leri (OpenAI/Anthropic) kullanarak sosyal medya gönderileri için içerik (caption + görsel/video) üreten, local'de çıktı veren bir araç. Platformlara otomatik paylaşım yapılmayacak — üretim tamamen otomatik, paylaşım manuel.

## Kapsam Dışı (Bilinçli Kararlar)

- ❌ Meta Graph API / Instagram Content Publishing API entegrasyonu yok
- ❌ Otomatik paylaşım yok — token yönetimi, App Review süreci, rate limit derdi ortadan kalkıyor
- ❌ Activepieces kullanılmayacak (Tezgahçılar projesindeki deneyim ayrı kalıyor, bu proje bağımsız)

## Akış

```
Kullanıcı formu (tema + görsel sayısı + stil + opsiyonel referans + format + notlar)
    → LLM, girdiyi yapılandırılmış prompt'lara ve caption/hashtag'e çevirir (her görsel için ayrı prompt)
    → Medya üretim API'si (sadece görsel, metinsiz) — N adet, paralel/sıralı
    → Galeri: kullanıcı seçer veya "yeniden üret" der
    → Seçilen görsel hedef tuvale getirilir (crop/resize, örn. 4:5 → 1080x1350)
    → Kodla metin bindirme (sabit pozisyon, format kuralları)
    → Önizleme: final görsel + düzenlenebilir caption/hashtag
    → Local'e kaydet (organize klasör yapısı)
    → Manuel paylaşım (kullanıcı kendi yapar)
```

## Kullanıcı Girdi Formu

Arayüzde kullanıcı ne istediğini yapılandırılmış şekilde girer. Amaç: serbest bir "bana bir görsel yap" yerine, LLM'in zengin ve tutarlı bir prompt üretebileceği net girdiler toplamak.

### Form Alanları

| Alan | Tip | Zorunlu | Varsayılan | Kural / Not |
| --- | --- | --- | --- | --- |
| **Tema / konu** | Serbest metin | Evet | — | 3-200 karakter; örn. "yeni ürün tanıtımı", "indirim duyurusu" |
| **Görsel sayısı** | Seçim (1-4) | Hayır | 2 (ön seçili) | Arayüzde kullanıcıya seçenek olarak sunulur; kararı kullanıcı verir — "2" yalnızca ön seçili başlangıçtır. Her varyasyon ayrı API çağrısı = ayrı maliyet |
| **Görsel tipi / stil** | Dropdown | Hayır | Ürün fotoğrafı | Ürün fotoğrafı / Lifestyle / İllüstrasyon / Minimal-flat |
| **Referans görsel** | Dosya yükleme | Hayır | — | JPG/PNG/WebP, maks. 10 MB; yüklenirse "buna benzer olsun" (B) yolu devreye girer |
| **Format** | Dropdown | Hayır | Post (4:5) | Post (1:1) 1080x1080 / Post (4:5) 1080x1350 / Story (9:16) 1080x1920 / Reels kapağı 1080x1920 |
| **Görsel üzerindeki metin** | Serbest metin | Hayır | — | Maks. 60 karakter; satır kaydırma ve auto-shrink otomatik (bkz. Metin Bindirme Kuralları) |
| **Ek notlar** | Serbest metin | Hayır | — | Maks. 300 karakter; renk, ton, kaçınılacaklar vb. |

### Form Payload Örneği (LLM Girdisi)

Form gönderilince oluşan yapı; LLM hem görsel prompt'larını hem caption/hashtag'i bu girdiden üretir:

```json
{
  "topic": "Yeni sezon kahve çeşidi tanıtımı",
  "image_count": 2,
  "style": "lifestyle",
  "reference_image": null,
  "format": "post_4x5",
  "overlay_text": "Yeni sezon, yeni lezzet",
  "notes": "Sıcak tonlar, ahşap yüzeyler; kalabalık olmasın"
}
```

- `style` değerleri: `product_photo`, `lifestyle`, `illustration`, `minimal_flat`
- `format` değerleri: `post_1x1`, `post_4x5`, `story_9x16`, `reels_cover_9x16` — hedef tuval boyutu buradan türetilir
- `reference_image`: yüklenirse dosya yolu, yoksa `null`

### Referans Görsel ("Buna Benzer Olsun") Mantığı

İki yol desteklenir; hangisinin kullanılacağı kullanıcının girdisine göre otomatik seçilir:

- **A) Referans yok → Metinden üretim:** Sadece form alanlarından LLM bir prompt üretir, image API'ye gönderilir.
- **B) Referans var → İki alt seçenek:**
  - **B1) Image-to-text köprüsü (stil çözümleme):** Vision destekli bir LLM referans görseli analiz eder (stil, kompozisyon, renk paleti, ışık) ve bu tarif yeni prompt'a dahil edilir. Referans kopyalanmaz, stili aktarılır; daha esnektir.
  - **B2) Doğrudan image edit/variation API'si:** Referans görsel doğrudan API'ye input verilir ("bu stile benzer ama şu değişikliklerle"). Daha sadık sonuç verir, daha az esnektir.

### Form → Prompt Dönüşümü

Form alanları doğrudan image API'sine gitmez; önce LLM bir "prompt mühendisi" gibi çalışır:

1. Form girdisi JSON olarak LLM'e verilir
2. LLM, görsel sayısı kadar **birbirinden hafif farklı** prompt üretir (kompozisyon/açı/ışık varyasyonu)
3. Her prompt'a sabit kural eklenir: **"metin/yazı içermesin"** (metin sonradan kodla bindirilecek)
4. Çıktı yapılandırılmış JSON olarak alınır ve kod bu JSON ile image API'yi çağırır

Örnek yapılandırılmış çıktı:

```json
{
  "prompts": [
    { "id": 1, "prompt": "...", "aspect_ratio": "4:5" },
    { "id": 2, "prompt": "...", "aspect_ratio": "4:5" }
  ],
  "caption": "...",
  "hashtags": ["...", "..."]
}
```

### Galeri ve Yeniden Üretim

- Üretilen N görsel galeri olarak gösterilir
- Kullanıcı birini seçer → metin bindirme aşamasına geçer
- Beğenmezse **"yeniden üret"**: form tekrar doldurulmaz, aynı girdi hafif varyasyonla yeniden çalıştırılır. Not: seed desteği sağlayıcıya göre değişir (OpenAI görsel API'lerinde bildiğimiz kadarıyla yok; Flux/Ideogram'da var) — "yeniden üret" seed varsa "aynı seed + varyasyon", yoksa "prompt varyasyonu" olarak çalışır; sağlayıcı seçilirken doğrulanmalı
- İstenirse "bunu beğendim, buna benzer 3 tane daha" akışı: seçilen görsel, B yolunda referans olarak kullanılır

## Bileşenler

### 1. İçerik Üretim Katmanı (LLM)

- OpenAI veya Anthropic API ile caption + görsel açıklaması/prompt üretimi
- Sisteme özel bir system prompt ile marka tonu, hashtag stili, dil belirlenir

### 2. Medya Üretim Katmanı

- **Görsel:** OpenAI image API veya alternatif olarak Ideogram/Flux (Replicate üzerinden)
  - Prompt'ta **"metin/yazı olmasın"** şartı — metin ayrı aşamada kodla bindirilecek
- **Video:** Runway / Luma / Kling gibi servislerin API'leri (maliyet/kalite dengesi test edilmeli)

### 3. Format Standardizasyonu (Statik Postlar İçin)

AI'ya "metni alttan X cm yukarı koy" dedirtmek tutarsız sonuç verir (diffusion modelleri piksel-hassasiyetinde değil). Bunun yerine:

- Görsel AI'dan **metinsiz** üretilir
- Metin, **Pillow (Python) veya Canvas/Sharp (Node)** ile sabit koordinata bindirilir
- Örnek spesifikasyon (1080x1350, Instagram dikey post):
  - Metin bandı: alt kenardan \~%15-18 yukarıda sabit
  - Okunabilirlik için hafif gradient/overlay şeridi
  - Font, boyut, renk marka standardına göre sabit

Bu yöntem her post arasında tutarlılığı garanti eder; AI yalnızca görsel üretir, pozisyon/format %100 kod kontrolünde kalır.

#### Boyut Standardizasyonu (Crop/Resize Adımı)

Image API'lerinin native boyutları (1024x1024, 1024x1536, 1024x1792 gibi) hedef tuvallerle birebir örtüşmez. Akış:

1. LLM, istenen formata en yakın native boyutu ister (örn. 4:5 → 1024x1536)
2. Seçilen görsel hedef tuvale getirilir (crop/resize; örn. 4:5 → **1080x1350**, story → 1080x1920). Kırpma kaybını azaltmak için prompt'larda kompozisyon merkezde tutulur.
3. Metin bindirme bu hedef tuval üzerinde yapılır

Böylece her post aynı ölçüde ve metin konumu birebir tutarlı çıkar.

#### Metin Bindirme Kuralları

- **Font:** Türkçe karakterleri (ğ, ş, İ, ı, ö, ü, ç) destekleyen bir TTF kullanılmalı (Latin Extended-A desteği; örn. Inter, Montserrat, Poppins). Karar (2026-10-11): **Poppins Bold** (OFL lisanslı, `assets/fonts/Poppins-Bold.ttf`); bulunamazsa `brand.json` fallback listesine düşer (Segoe UI Bold / Arial Bold)
- **Taşma yönetimi:**
  - Karakter limiti (örn. max ~60 karakter) — form alanında kullanıcıya gösterilir
  - Uzun metin otomatik satır kaydırma (word-wrap) ile bölünür
  - İzin verilen satır sayısı aşılırsa font boyutu kademeli küçültülür (auto-shrink); metin hâlâ sığmıyorsa kullanıcı uyarılır
- **Marka ayarları tek config dosyasından okunur** (örn. `brand.json`): font dosyası, boyut, renk, pozisyon, gradient parametreleri — marka standardı kod içine gömülmez

### 4. Local Çıktı Yönetimi

Önerilen klasör yapısı:

```
/outputs/
  2026-10-07/
    post-1/
      background.png
      final.png       ← metin bindirilmiş hali
      caption.txt
      meta.json        ← tema, prompt, üretim tarihi vb.
```

### 5. Arayüz (Form + Galeri + Önizleme)

- **Next.js** ile local arayüz (karar: 2026-10-10): form girişi, üretilen görsellerin galerisi, final önizlemesi ve **düzenlenebilir caption/hashtag alanı** (kaydetmeden önce son düzeltme yapılır)
- Arayüz ile Python pipeline arasında yerel bir köprü kurulur (örn. küçük bir FastAPI servisi); üretim ve metin bindirme Python tarafında kalır

### 6. Maliyet ve Hata Yönetimi

- **API anahtarları:** `.env` dosyasından okunur, repoya girmez (`.gitignore`); anahtar arayüzde/kodda tutulmaz
- **Retry:** Geçici hatalarda (429 rate limit, 5xx) üstel beklemeli 2-3 deneme; kalıcı hatada kullanıcıya net mesaj, akış kaldığı yerden devam edebilir
- **Maliyet kaydı:** Her üretim çağrısının tahmini maliyeti `meta.json`'a yazılır (sağlayıcı, model, boyut, adet) — bir postun ve toplam kullanımın maliyeti izlenebilir

## Teknik Yığın Önerisi

| Katman | Öneri |
| --- | --- |
| Dil/Script | Python (PIL/Pillow ile metin bindirme kolay) |
| Arayüz | Next.js (local; Python pipeline'a yerel servis köprüsü ile bağlanır) |
| LLM | OpenAI veya Anthropic API |
| Görsel üretim | OpenAI image API / Ideogram / Flux |
| Video üretim | Runway / Luma (opsiyonel, 2. faz) |
| Çıktı | Local dosya sistemi (JSON + PNG/MP4) |

## Sonraki Adımlar

1. Form şemasını (alanlar, zorunlu/opsiyonel, varsayılanlar) netleştir — tamamlandı: 2026-10-10
2. `.env` ile anahtar yönetimini, retry davranışını ve üretim başına maliyet kaydını kur — tamamlandı: 2026-10-10
3. Tek bir tema için uçtan uca akışı çalıştır: form girdisi → LLM prompt → görsel üret → hedef tuvale getir (crop/resize) → metin bindir → caption düzenle → local'e kaydet — tamamlandı: 2026-10-10 (mock modda doğrulandı: `python -m pipeline.cli --mock`; gerçek API çalıştırması `.env`'e anahtar konulunca yapılacak; sağlayıcı kararı: OpenAI tek anahtar). Caption düzenleme arayüzü 6. adımda.
4. Format spesifikasyonunu netleştir ve sabitle: Türkçe destekli font, taşma kuralları (wrap/limit/auto-shrink), renk, pozisyon; marka ayarlarını tek config dosyasında topla — tamamlandı: 2026-10-11 (`brand.json` tek kaynak: font/punto/renk/pozisyon/gradient/taşma; wrap + auto-shrink + max_chars limiti mock testlerle doğrulandı)
5. Referans görsel desteğini ekle (önce B1 stil çözümleme, sonra B2 edit API)
6. Galeri + "yeniden üret" akışını ve önizlemede caption/hashtag düzenlemeyi ekle
7. Birden fazla post'u toplu üretecek bir script/CLI'ye genişlet
8. (Opsiyonel, çok sonra) Video üretimini dahil et