# Açılış Sayfası — Ücretsiz Yayınlama (GitHub Pages)

Bu, tüm ürünleri tanıtan, SEO uyumlu, tek dosyalık bir açılış sayfasıdır.
Ücretsiz yayınlanır ve zamanla Google'dan organik trafik getirebilir
(kişisel sosyal medya gerekmez).

## GitHub Pages ile yayınlama (ücretsiz, ~2 dk — SEN)
1. GitHub'da bu repoya git → **Settings → Pages**.
2. "Build and deployment" → Source: **Deploy from a branch**.
3. Branch: `main` (veya çalışma dalı), Folder: **/ (root)** seçili değilse,
   `site` klasörünü kullanmak için repo köküne `index.html` koymak gerekir;
   alternatif: branch = main, folder = `/docs` ya da root. En kolayı:
   `site/index.html`'i repo köküne kopyala ya da Pages "root" seçip
   `site/`'i `docs/`'a taşı.
4. Kaydet → birkaç dakika sonra `https://tayma67.github.io/My-game-app/`
   benzeri bir adres verir.

> Not: GitHub Pages alt klasör (`/site`) yerine `root` ya da `/docs`'tan
> yayın yapar. En pratik yol: yayın anında `site/` içeriğini `docs/`'a
> kopyalamak. İstersen bunu senin için ayarlarım.

## Alternatif: Netlify / Vercel (ücretsiz)
- Netlify'a sürükle-bırak: `site` klasörünü netlify.com/drop'a bırak → anında
  canlı URL. Hesap KYC istemez, en hızlısı budur.

## Sonra
- Açılış sayfasının linkini Gumroad profiline ve ürün açıklamalarına ekle.
- Ürün #2-4 yayınlanınca, `index.html`'deki "Get the kit" linklerini tek tek
  ürün URL'leriyle güncelle (şimdilik mağaza ana sayfasına gidiyorlar).
