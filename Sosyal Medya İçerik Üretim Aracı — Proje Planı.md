# Sosyal Medya Otomasyon — Proje Planı

## Özet

LLM API'leri (OpenAI/Anthropic) kullanarak özellikle Instagram gönderileri (post) ve hikayeleri (story) için içerik (caption + görsel) üreten, local'de çıktı veren ve tek tıkla Instagram'a hazır indirme imkanı sunan bir araç. Platformlara otomatik paylaşım yapılmayacak — üretim tamamen otomatik, paylaşım manuel.

> **Uygulama İsmi Kararı (2026-10-16):** Uygulamanın adı web arayüzünde, sekme başlıklarında ve tüm sistemde **"Sosyal Medya Otomasyon"** olarak kullanılacaktır (SocialCraft Studio vb. yabancı isimler kaldırılacaktır).

## Kapsam Dışı (Bilinçli Kararlar)

- ❌ Meta Graph API / Instagram Content Publishing API entegrasyonu yok
- ❌ Otomatik paylaşım yok — token yönetimi, App Review süreci, rate limit derdi ortadan kalkıyor
- ❌ Activepieces kullanılmayacak (Tezgahçılar projesindeki deneyim ayrı kalıyor, bu proje bağımsız)

## Akış

```
Kullanıcı formu (tema + sistem promptu + görsel sayısı + stil + opsiyonel referans + format + notlar)
    → LLM, kullanıcının sistem promptuna göre girdiyi yapılandırılmış prompt'lara ve caption/hashtag'e çevirir
    → Medya üretim API'si (sadece görsel, metinsiz) — N adet, paralel/sıralı
    → Galeri: kullanıcı seçer veya "yeniden üret" der
    → Seçilen görsel hedef tuvale getirilir (crop/resize, örn. 4:5 → 1080x1350 veya story → 1080x1920)
    → Kodla metin bindirme (sabit pozisyon, format kuralları)
    → Önizleme: final görsel + düzenlenebilir caption/hashtag
    → Instagram'a hazır indirme (1080x1350 / 1080x1920 PNG + tek tıkla caption kopyalama)
    → Local'e kaydet (organize klasör yapısı)
    → Manuel paylaşım (kullanıcı kendi yapar)
```

## Kullanıcı Girdi Formu

Arayüzde kullanıcı ne istediğini yapılandırılmış şekilde girer. Amaç: serbest bir "bana bir görsel yap" yerine, LLM'in zengin ve tutarlı bir prompt üretebileceği net girdiler toplamak.

### Form Alanları

| Alan | Tip | Zorunlu | Varsayılan | Kural / Not |
| --- | --- | --- | --- | --- |
| **Tema / konu** | Serbest metin | Evet | — | 3-200 karakter; örn. "yeni ürün tanıtımı", "indirim duyurusu" |
| **Sistem promptu / AI Talimatı** | Serbest metin | Hayır | Instagram için optimize şablon | Kullanıcının dilediği gibi düzenleyebileceği veya değiştirebileceği yapay zeka sistem talimatı |
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
  "system_prompt": "Sen Instagram içerik üreticisisin; dikkat çekici, samimi Türkçe ve kanca odaklı çalış...",
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

### 4. Local Çıktı Yönetimi & Instagram İndirme

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

#### Instagram İndirme Standardı
Kullanıcının ürettiği içerikleri doğrudan Instagram'a yükleyebilmesi için arayüzde akıllı indirme ve kopyalama sağlanır:
- **Instagram Dikey Post (4:5):** 1080x1350 px → dosya adı: `instagram-post-1080x1350.png`
- **Instagram Kare Post (1:1):** 1080x1080 px → dosya adı: `instagram-post-1080x1080.png`
- **Instagram Hikaye / Story (9:16):** 1080x1920 px → dosya adı: `instagram-story-1080x1920.png`
- **Instagram Reels Kapağı (9:16):** 1080x1920 px → dosya adı: `instagram-reels-1080x1920.png`
- **Caption + Hashtag Kopyalama:** Tek tıkla Instagram gönderi açıklamasına yapıştırılmaya hazır panoya kopyalanır.

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
5. Referans görsel desteğini ekle (önce B1 stil çözümleme, sonra B2 edit API) — tamamlandı: 2026-10-13 (`--reference-image` + `--reference-mode b1|b2`; B1: vision çözümleme → prompt'a stil yansıması, B2: görsel edit API'ye doğrudan input; mock ile doğrulandı, gerçek vision/edit çağrısı anahtar sonrası test edilecek)
6. Galeri + "yeniden üret" akışını ve önizlemede caption/hashtag düzenlemeyi ekle — tamamlandı: 2026-10-13 (FastAPI + modern karanlık mod Web Stüdyosu: form, galeri şeridi, canlı metin bindirme önizlemesi, caption/hashtag düzenleme, tekil varyasyon yeniden üretme ve çıktı galerisi; http://localhost:8000)
7. Kullanıcı Tanımlı Sistem Promptu & Instagram İndirme Geliştirmesi — tamamlandı: 2026-10-16
   - Uygulama adının web arayüzünde (sayfa başlığı, logo, tab başlığı vb.) **"Sosyal Medya Otomasyon"** olarak güncellenmesi tamamlandı.
   - Web arayüzüne kullanıcının serbestçe düzenleyebileceği "Sistem Promptu / AI Talimatı" metin alanı eklendi (varsayılan Instagram optimizasyonlu şablon ve sıfırlama butonu ile).
   - Pipeline (`llm.py`, `generate.py`, `web.py`) katmanına dinamik sistem promptu aktarımı sağlandı.
   - İndirme butonlarının ve indirilen dosyaların Instagram gönderi/hikaye formatlarına göre akıllı adlandırılması (`instagram-story-1080x1920-v1.png`, `instagram-post-1080x1350-v1.png` vb.) ve galeri indirmeleri tamamlandı.
   - **Anahtar & Şifre Yönetimi:** OpenAI/Anthropic API anahtarları ve uygulama giriş şifresi doğrudan `.env` dosyasında (ve Vercel ortamında Environment Variables panelinde) tutulacak şekilde yapılandırıldı.
   - **Login Paneli:** `.env` dosyasındaki `APP_PASSWORD` değeri ile doğrulanan şık giriş modalı, `HttpOnly` oturum çerezi, rate limit koruması ve korumalı `/api/*` endpoint'leri tamamlandı.
8. **Firma Logosu & Kullanıcı Kontrollü Konumlandırma (Filigran)** — tamamlandı: 2026-10-17
   - **Kullanıcı Kararı & Konum Seçimi:** Logonun nereye yerleştirileceğine (Sol Üst, Üst Orta, Sağ Üst, Sol Alt, Orta/Filigran, Sağ Alt) tamamen kullanıcının karar vermesi sağlandı.
   - **Boyut & Şeffaflık:** Küçük (%13), Orta (%18), Büyük (%26) boyut ve %100, %80, %50 opaklık ayarları eklendi.
   - **İnteraktif Canlı Önizleme:** Logo yüklendiğinde ve konum butonlarına tıklandığında sağdaki Instagram telefon simülatörü üzerinde anlık olarak pozisyon ve boyut canlı güncellenir.
   - **Üretim & Düzenleme Pipeline Entegrasyonu:** `pipeline/overlay.py` içinde alfa kompozitli `overlay_logo()` geliştirildi; üretim esnasında veya üretim sonrasındaki "Görsel Metni & Logo Konumunu Düzenle" panelinden API harcamadan logo konumu tek tıkla yeniden konumlandırılabilir.
   - **Monokrom Tasarım Korundu:** Siyah-beyaz/monokrom tasarım bütünlüğü korundu; sadece Instagram logosu renkli tutuldu.
9. **Vercel'e Yayınlama Uyarlaması, Stateless Mimari & Tarayıcı Hafızası (IndexedDB)** — tamamlandı: 2026-10-17
   - **Stateless "At Çıktıyı Al Çık" Mimarisi:** Harici blob/S3 depolama maliyeti ve karmaşıklığı olmadan, in-memory base64 data URL'ler üzerinden çalışacak şekilde uyarlandı (`pipeline/canvas.py`, `pipeline/generate.py`, `pipeline/web.py`).
   - **Salt-Okunur Dosya Sistemi Uyumu:** Vercel serverless ortamında disk salt-okunur olduğunda yerel `outputs/` yazımları `OSError` yakalayarak güvenle es geçilir, API doğrudan in-memory veriyi döndürür.
   - **Instagram JPEG Standardizasyonu:** Vercel'in 4.5 MB payload limiti ve Instagram'ın yerel formatı gözetilerek çıktılar optimize JPEG (%95 kalite) formatına getirildi (~350 KB tuval).
   - **Tarayıcı Hafızası (IndexedDB - `StudioDB`):** Üretilen son 20 gönderi, caption ve hashtag'ler kullanıcının tarayıcısında IndexedDB (`SosyalMedyaStudioDB`) üzerinde saklanır. Sayfa yenilense veya sunucu kapansa bile içerikler kaybolmaz.
   - **Stüdyoya Geri Yükleme:** Çıktı Galerisi'ndeki herhangi bir gönderi "📱 Stüdyoda Aç" butonu ile canlı Instagram telefon simülatörüne anında geri yüklenebilir.
   - **Vercel Giriş Noktaları:** `api/index.py` (ASGI köprüsü), `vercel.json` (fonksiyon süresi 60s, `includeFiles` ile şablon ve fontlar, URL rewrite kuralları) ve `.vercelignore` oluşturuldu.
   - **Test Paketi:** 36/36 pytest testi (Vercel ASGI entry point, salt-okunur dosya sistemi simülasyonu, data URL overlay preview, güvenlik ve auth testleri) başarıyla geçmektedir.
10. Birden fazla post'u toplu üretecek bir script/CLI'ye genişlet — tamamlandı: 2026-10-18 (`pipeline/batch.py` ve `pipeline/cli.py --batch-file`; JSON/CSV/TXT desteği, kümülatif maliyet ve raporlama, 40/40 test başarılı)
11. (Opsiyonel, çok sonra) Video üretimini dahil et