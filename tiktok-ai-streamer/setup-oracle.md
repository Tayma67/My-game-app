# Ücretsiz Sunucu Kurulumu — Oracle Cloud Always Free (telefondan yapılır)

Amaç: 7/24 açık kalacak ücretsiz bir Ubuntu sunucusu. Telefonun tarayıcısından
yapılır. (Oracle kayıtta kart doğrulaması ister — para çekmez, "Always Free"de
kalırsan ücret yok.)

## 1. Hesap
1. cloud.oracle.com → "Start for free" → kayıt ol (kimlik + kart doğrulaması).
2. Bölge seçerken sana yakın birini seç (ör. Frankfurt).

## 2. Ücretsiz sunucu (VM) oluştur
1. Menu → Compute → Instances → "Create Instance".
2. Image: **Ubuntu 22.04**. Shape: **VM.Standard.A1.Flex** (Always Free —
   2 OCPU / 12 GB). 
3. SSH anahtarı: "Generate a key pair for me" → **private key'i indir/sakla**.
4. Create. Birkaç dakikada hazır; bir **Public IP** verir.

## 3. Bağlan (telefondan)
- Telefona bir SSH uygulaması kur (ör. Termius — ücretsiz).
- Host: VM'in public IP'si · User: `ubuntu` · indirdiğin private key ile bağlan.

## 4. Gereken yazılımlar
```
sudo apt-get update
sudo apt-get install -y python3-pip ffmpeg git
git clone <bu repo>            # ya da dosyaları kopyala
cd tiktok-ai-streamer
pip3 install -r requirements.txt
cp config.example.env .env     # nano .env ile doldur
```
> Güvenlik duvarı: Oracle'da giden (egress) bağlantı açıktır; RTMP yayını için
> ekstra port açmana gerek yok (biz dışarı yayın yapıyoruz).

## 5. Stream key
- 1.000 takipçin varsa: TikTok → LIVE → "Go LIVE via 3rd party / Stream Key"
  → Server URL + Stream Key'i `.env`'e koy. (Her yayında yenilenir.)
- Yoksa: bir TikTok **Creator Network/ajans**ına katıl (stream key'i ücretsiz
  açabilir; karşılığında hediyelerden komisyon alır — şartları oku).

## 6. Çalıştır
```
# Önce TikTok'tan canlı yayını başlat (sohbet + yayın hedefi oluşsun)
python3 main.py
```
Avatar döngüye girer, gelen yorumlara sesli cevap verir.

## Notlar / sorun giderme
- Avatar olarak kısa bir `avatar.mp4` koy (döngüye girer). Yoksa basit bir
  görselden video üretiriz.
- İlk denemede ses/görüntü senkronu veya ffmpeg ayarı tutmazsa, hata çıktısını
  bana getir — birlikte düzeltiriz (bu v1, gerçek sunucuda ince ayar ister).
- Bu sistem TikTok ToS açısından risklidir; hesap banlanabilir. Bilerek kullan.
