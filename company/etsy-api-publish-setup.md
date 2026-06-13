# Etsy API ile Otomatik Listeleme — "Gerisini Ben Yaparım" Kurulumu

Bu, "sen hesabı aç, gerisini ben yap" isteğinin gerçek olduğu tek yol. Sen bir
kerelik API kimliği kurarsın; **ben 12 ürünü programatik olarak oluştururum**
(görsel + dosya + başlık + etiket + açıklama). Motor hazır: `tools/etsy_publish.py`.

## Neden bu adımlar indirgenemez?
Etsy API'si kimlik doğrulama ister (x-api-key + OAuth). Senin hesabın adına
işlem yaptığı için yetkiyi yalnızca sen verebilirsin. Ama yetkiden **sonraki
her şeyi** (listeleri oluşturmak) kod yapar — yani ben.

## Senin yapacakların (bir kerelik)
1. **Etsy mağazanı aç** (kimlik doğrulama — KYC).
2. **Etsy Developer'a app kaydı aç:** etsy.com/developers/register → app
   oluştur → **Keystring (API key)** al. (Etsy onayı gerekebilir, açıklamayı
   net yaz: "kendi dijital ürünlerimi listelemek için.")
3. **OAuth ile yetki ver** (`listings_w listings_r` scope) → bir **access
   token** üret. (Rehber: developer.etsy.com → Authentication. Takılırsan
   OAuth akışını senin için adım adım çıkarırım.)
4. **Shop ID'ni** öğren (API'den getShop ile ya da mağaza ayarlarından).

## Sonra ben çalıştırırım
Token'ları **ortam değişkeni** olarak ver (sohbete düz yazma — aşağıdaki
güvenlik notu). Ben şunu çalıştırırım:
```
ETSY_API_KEY=... ETSY_OAUTH_TOKEN=... ETSY_SHOP_ID=... \
  python3 tools/etsy_publish.py --manifest tools/etsy_manifest.json --live
```
Bu, `tools/etsy_manifest.json`'daki 12 ürünü taslak olarak oluşturur, her birine
Etsy-optimize kapağı + PDF dosyasını + 13 etiketi + açıklamayı ekler. Sen
Etsy'de taslakları görüp "publish" dersin (ya da istersen onu da API ile aktif
ederim).

## 🔐 Güvenlik (önemli)
- API token'ı **hassas bir parola gibidir.** Sohbete düz yazma; mümkünse kısa
  ömürlü token üret, ben kullanınca **iptal et (revoke)**.
- Token'ı repoya **commit etmem**; `.gitignore` koruması ekledim.
- Bu ortam geçici (ephemeral); token kalıcı saklanmaz.

## Dürüst beklenti
- Etsy app onayı + OAuth biraz uğraştırır (yarım saat-birkaç gün). 12 ürün için
  elle listeleme (~her biri 3 dk = ~40 dk) bazen daha hızlı olabilir. İkisi de
  hazır: elle istersen `company/marketing/etsy-listings.md`; otomatik istersen
  bu motor. Sen karar ver.
- Gumroad'da bu mümkün değil (resmi API ürün oluşturmuyor) — orada listeleme
  elle, ama asset'lerle ~3 dk/ürün.

## Durum
- [x] Listeleme motoru yazıldı + 12 ürünle kuru-çalıştırma doğrulandı.
- [x] Bu ortamın Etsy API'sine erişimi var (test edildi).
- [ ] Senin Etsy app + OAuth token kurulumun (yalnızca sen).
- [ ] `--live` çalıştır (token gelince ben).
