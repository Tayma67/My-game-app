# TikTok AI Avatar Streamer (ücretsiz yığın)

Canlı TikTok yayınında bir avatarın, gelen sohbet mesajlarını **okuyup sesli
cevap vermesini** sağlayan otonom bir sistem. Bir **ücretsiz bulut sunucusunda**
7/24 çalışır — bilgisayar gerektirmez, kurulumu telefondan yapılır.

## Mimari (hepsi ücretsiz parçalar)
```
TikTok LIVE sohbeti ──(TikTokLive lib)──▶ main.py
                                            │  yorum gelince
                                            ▼
                                       brain.py (AI cevap, ücretsiz LLM)
                                            │
                                            ▼
                                       edge-tts (ücretsiz ses) ─▶ ses kuyruğu
                                            │
TikTok LIVE  ◀──(ffmpeg RTMP, stream key)── stream.py (avatar videosu + ses)
```

## Ne ücretsiz, ne değil (DÜRÜST)
| Parça | Durum |
|------|-------|
| Sunucu (Oracle Cloud Always Free) | ✅ Ücretsiz, 7/24. Ama kayıtta **kart doğrulaması** ister (çekim yok). |
| Sohbet okuma (TikTokLive) | ✅ Ücretsiz |
| Ses (edge-tts) | ✅ Ücretsiz |
| AI beyin | ✅ Groq/Gemini ücretsiz API katmanı (anahtarı sen alırsın, bedava) |
| Yayın (ffmpeg RTMP) | ✅ Ücretsiz |
| **Stream key (yayın anahtarı)** | ⚠️ 2026'da ham stream key **yalnızca Creator Network (ajans)** ile açılıyor (ücretsiz, takipçi şartı yok). TikTok seni LIVE Studio'ya yönlendiriyorsa kilidin açık değildir. Ajans **hediyelerden komisyon** alır + **bot yayın** ajans/TikTok kurallarına aykırı olabilir (ban riski). Her yayında **yeni key** üretilir. |
| Foto-gerçekçi 3D avatar | ⚠️ GPU ister; ücretsiz sunucuda **basit avatar** (döngü video/animasyonlu görsel) yapılır, fancy değil. |

## ⚠️ Gerçek riskler (okumadan başlama)
- **TikTok kurallarına aykırı olabilir.** Otomatik/bot yayın ve resmi olmayan
  sohbet API'si TikTok ToS'unu ihlal edebilir → **hesap banlanabilir.** Bu
  gerçek bir risk; bilerek gir.
- **Gelir garantisi yok.** Hediye geliri izleyiciye bağlı; yeni/bilinmeyen bir
  AI yayınına izleyici çekmek ayrı ve zor bir iş (yine dağıtım sorunu).
- Avatar kalitesi ücretsiz sunucuda sınırlı.

## Senin yapacakların (bir kerelik)
1. **Oracle Cloud Always Free** hesabı aç (kart doğrulaması gerekir; çekim yok)
   → bir Ubuntu VM oluştur. Rehber: `setup-oracle.md`.
2. **Stream key** edin: 1.000 takipçin varsa TikTok LIVE'dan al; yoksa bir
   Creator Network'e katıl (komisyon alır).
3. Ücretsiz bir **LLM API anahtarı** al (Groq: console.groq.com, bedava).
4. `config.example.env`'i doldur, sunucuda çalıştır (ben adım adım yönlendiririm).

## Çalıştırma
```
pip install -r requirements.txt
cp config.example.env .env   # doldur
python main.py               # sohbet→AI→ses
python stream.py             # avatar+ses→TikTok RTMP
```

> Durum: v1 iskeleti. Gerçek stream key olmadan burada test edemiyorum; sen
> sunucuyu/anahtarı hazırlayınca birlikte canlı test edip hataları düzeltiriz.
