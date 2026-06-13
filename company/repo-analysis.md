# Repo Analizi — İçindeki İşe Yarar Parçalar (Kalıcı Hafıza)

> Bu dosya bizim "hafızamız". Hangi açık kaynak repoda hangi parçanın hangi
> gig/ürüne yaradığını burada tutuyoruz. Yeni oturumda ben bunu okur, kaldığımız
> yerden devam ederim.

---

## 1. enescingoz/awesome-n8n-templates (280+ ücretsiz n8n şablonu)
**Bu, otomasyon teslimatlarımızın hazır envanteri.** Müşteri ne isterse,
sıfırdan yazmak yerine ilgili şablonu alıp uyarlıyoruz.

| Kategori | Bizim kullanımımız | Örnek hazır şablonlar |
|----------|--------------------|------------------------|
| **E-posta otomasyonu** | Gig #1 → "müşteri e-postalarını otomatikle" | Gmail'i AI ile otomatik etiketle · Gmail'de OpenAI ile taslak yanıt · AI cold-email yazarı (LeadPilot) |
| **Sosyal medya içeriği** | Gig #1 + Gig #2 → içerik üretim otomasyonu | Trendlerden Instagram içeriği + AI görsel · Tweet üretici · İçeriği 4 platforma yeniden uyarlama (FlowScribe) |
| **Müşteri destek / chatbot** | Gig #1 → işletmeye AI destek botu (en çok talep edilen) | Discord AI bot · Telegram AI bot (ses+metin) · WordPress AI chatbot (Supabase+OpenAI) · Basit AI destek botu (SupportFlow) |
| **Lead/satış** | Gig #1 → küçük işletmeye lead otomasyonu | Google Sheets'te lead'i GPT-4 ile niteleme · Twilio+Cal.com randevu lead'i · Pipedrive veri zenginleştirme |
| **AI agent / araştırma** | İleri seviye / premium paket | Kendi AI deep-research agent'ı · Otonom web crawler · RAG chatbot (Qdrant) |
| **Doküman / veri işleme** | Gig #1 → fatura/CV/PDF işleme otomasyonu | PDF ile sohbet (kaynak göstererek) · Fatura veri çıkarımı (LlamaParse+OpenAI) · CV/özgeçmiş PDF parse |

**En çok satış potansiyeli olanlar (öncelik sırası):**
1. AI müşteri destek botu (Telegram/WordPress) — KOBİ'ler için somut değer.
2. Fatura/CV/PDF veri çıkarımı — ofislerin manuel işini bitirir.
3. Lead niteleme + cold-email — freelancer/ajanslar ister.

## 2. Ücretsiz AI araçları (mahseema/awesome-ai-tools'tan, sıfır bütçe)
**Bunlar üretim aletlerimiz** — ürün ve içerik üretirken kullanırım.

| İhtiyaç | Ücretsiz araç | Nerede kullanırız |
|---------|---------------|-------------------|
| Metin/copywriting | ChatGPT, Gemini, Rytr, copy.ai | Ürün metni, gig açıklaması, içerik (Gig #2) |
| Görsel üretimi | Stable Diffusion, Craiyon, Playground AI, ClipDrop | Ürün kapağı, sosyal görsel, mockup |
| Video/kısa klip | Clipwing, Synthesia | Tanıtım videosu, faceless içerik |
| Ses/seslendirme | Bark, Coqui, TorToiSe | Video seslendirme (ücretsiz) |
| Yerel LLM (API ücreti yok) | Ollama, gpt4all | n8n şablonlarını ÜCRETSIZ çalıştırma (OpenAI yerine Ollama) |

> 💡 Kritik bulgu: n8n şablonlarının çoğu OpenAI ister (ücretli). Ama
> **Ollama** ile yerel/ücretsiz modele çevrilebilir — sıfır bütçe için bu
> önemli. Şablon kataloğunda zaten "Ollama" versiyonları var.

## 3. Web teslimatı araçları
- **cruip/tailwind-landing-page-template** → Gig #3 açılış sayfası için iskelet.
- **ixartz/SaaS-Boilerplate** (MIT) → daha büyük web işleri için.

## Lisans hatırlatması
- n8n: fair-code — müşteriye kurmak/şablon uyarlamak OK; n8n'i barındırıp
  satmak kısıtlı.
- Şablon koleksiyonu: serbest kullanım.
- cruip ücretsiz sürüm: atıf linki kalmalı. SaaS-Boilerplate: MIT.
- Her ticari kullanımdan önce LICENSE kontrol.

## Sıradaki analiz (yapılacak)
- [ ] activepieces parça kataloğu (n8n alternatifi olarak)
- [ ] Şablonların Ollama (ücretsiz) versiyonlarının tam listesi
- [ ] cruip şablonunun bölümlerinin gig paketlerine eşlenmesi
