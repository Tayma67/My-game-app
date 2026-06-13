# Fiyatlama & Dönüşüm — Araştırma-Temelli Notlar (uygulandı)

Yeni araştırmadan çıkan, satışı artıran somut taktikler. Bunlar tahmin değil,
kaynaklı bulgular.

## Fiyatlama (psikoloji)
- **Charm pricing (.99/.97):** Fiyatın .99 ile bitmesi "sol-rakam etkisi" ile
  daha ucuz algılanır. ✓ Zaten $9.99 / $11.99 / $12.99 kullanıyoruz. Doğru.
- **Bundle = "bonus" çerçevesi:** Tüketiciler bir indirimden çok, "bonus paket"
  algısına %73 daha fazla harcıyor. Bundle'ı "indirim" değil "hepsi bir arada
  bonus kütüphane" diye konumlandır. ✓ Bundle metni buna göre.
- **Decoy / "Most popular" etiketi:** Birden çok seçenek varken ortadakini
  "En popüler" diye işaretlemek onu seçtirir. Etsy/Gumroad'da bundle'ı "Best
  Value" diye işaretle. ✓ Açılış sayfasında "Best Value" var.
- **İlk satış kritik:** Hem Etsy hem Gumroad sıralaması satış + yorum + CTR'ye
  bakıyor. İlk birkaç satış + ilk 5 yıldız sıralamayı ciddi itiyor.

## Dönüşüm (listing/satış sayfası)
- **İlk görsel her şeyi belirler** (Etsy). Bu yüzden hi-res 4:3 Etsy kapakları
  ürettik. Gumroad'da da kapak tıklamayı artırır.
- **Açıklama itirazları yanıtlamalı:** "ne alıyorum, nasıl kullanırım, işe
  yarar mı, iade var mı". Satış metinlerimiz bunları kapsıyor + 30 gün iade.
- **İçindekiler önizlemesi** (`etsy-preview.png`) "ne alıyorum" itirazını
  görselle kırar — eklendi.
- **Sosyal kanıt:** İlk yorumları al (ilk müşterilere nazikçe yorum iste).

## Gumroad sıralama faktörleri (uygula)
- Ücretli müşteri **yorumları** (sahte sayılmaz), **fiyat**, **anahtar kelime**,
  **satış**. → Etiketleri doldur (Discover doc), ilk satışı + yorumu al.

## Yapılan iyileştirmeler (bu araştırma turunda)
- 10 ürüne **Etsy-optimize 4:3 2000×1500 kapak** + **içindekiler önizleme**
  görseli üretildi (`tools/make_etsy_images.py`).
- Etsy görsel slot stratejisi belgelendi (etsy-listings.md).
- Fiyat/bundle çerçevesi charm + bonus + "Best Value" decoy ile teyit edildi.

## Sıradaki test fikirleri (ilk satışlardan sonra)
- Bundle'ı $34.99 vs $39.99 test et.
- Etsy ilk görselde "12 PROMPTS" rozetini büyüt/küçült, CTR'yi izle.
- Tek üründe fiyatı $9.99 vs $12.99 A/B (Gumroad'da yorum birikince).
