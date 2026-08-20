# Oturalım

> **Bütçene göre otur.**

Türkiye'deki kafe, restoran ve barları bütçene, bahçesine ve şu an açık olup
olmadığına göre süzen web uygulaması. Üyelik zorunlu değil, reklam yok, çerez yok.

**33.552 mekan · 81 il · 9.490 menü kalemi**

---

## Ne yapıyor

Dışarıda oturmak pahalılaştı ve fiyatlar öngörülemez hale geldi. Aynı sokakta
iki kafe, aynı kahve, iki kat fark olabiliyor. Uygulamanın tek işi:
**bütçene göre nereye gidilebileceğini göstermek.**

- Harita + liste, 81 ilin tamamı
- Bütçe kaydırıcısı — kişi başı tutara göre süzme
- Filtreler: tür, bahçe, wi-fi, şu an açık, fiyatı bilinen
- Açık/koyu tema (harita döşemesi de birlikte döner)
- Filtre durumu URL'de — görünüm olduğu gibi paylaşılabilir
- İsteğe bağlı hesap: favori mekanlar, fiyat paylaşımı, yönetici onayı

## Veri nereden geliyor

| Katman | Kaynak | Lisans |
|---|---|---|
| Mekan adı, konum, tür, saat, bahçe, wi-fi | OpenStreetMap (Overpass API) | ODbL |
| Menü fiyatları | İşletmelerin kendi sitelerinde yayımladığı menüler | — |
| Ödenen tutarlar | Kullanıcı paylaşımı (onaydan geçer) | — |

Google Maps, Yemeksepeti, Getir gibi platformlardan **hiçbir veri alınmadı**;
kullanım şartları buna izin vermiyor.

Dürüst not: denenen sitelerin yalnızca **%7'sinden** fiyat çıkarılabildi, geri
kalanı menüsünü JavaScript ile basıyor. Bu yüzden fiyat verisi bugün zayıf ve
ancak kullanıcı paylaşımıyla büyür.

## Çalıştırma

Derleme adımı yok, bağımlılık yok. Python 3 yeterli:

```bash
python sunucu.py
```

→ http://localhost:8123

Giriş sistemi olmadan da tam çalışır; hesap özellikleri kapalı görünür.
Kurmak için: [KURULUM.md](KURULUM.md) (~15 dakika, ücretsiz, kart istemiyor).

## Yapı

```
app/                 Uygulama — statik HTML/CSS/JS, derleme yok
  index.html         Anasayfa: bütçe seçici, canlı sayılar, vitrin
  kesfet.html/.js    Harita + liste + filtreler
  paylas.html        Fiyat paylaşma
  hesabim.html       Favoriler, paylaşımlar, ayarlar
  yonetim.html       Paylaşım onayı (yönetici)
  giris.html         Giriş / kayıt / parola sıfırlama
  kimlik.js          Supabase kimlik ve veri katmanı
  ortak.js           Tema, açılış saati, biçimlendirme, kohort
  stil.css           Tasarım sistemi (token tabanlı, iki tema)
  veri/<il>.json     Mekan verisi, il başına
veritabani/sema.sql  Tablolar + RLS politikaları
*.py                 Veri toplama ve işleme betikleri
```

## Güvenlik

Yetki tarayıcıda değil **veritabanında**. `anon` anahtarı tasarım gereği
herkese açıktır; kimin neyi görebileceğine `sema.sql` içindeki RLS politikaları
karar verir. Doğrulanan davranışlar:

- Anonim kullanıcı üç tabloya da yazamıyor (`401 / 42501`)
- Bir kullanıcı başkasının profilini, favorilerini, bekleyen paylaşımlarını göremiyor
- Kullanıcı kendini yönetici yapamıyor (politika + tetikleyici)
- Onaylanmış paylaşımlar herkese açık, bekleyenler yalnızca sahibine ve yöneticiye

## Teknoloji

Tarayıcıda çalışan statik dosyalar (derleme adımı yok) · Leaflet (harita) ·
Supabase (kimlik + veritabanı, ücretsiz katman) · barındırma: Vercel.

## Lisans ve sorumluluk

Mekan verisi © OpenStreetMap katkıcıları, ODbL. Fiyatlar derlendiği andaki
hâliyle durur, **bağlayıcı değildir**, değişmiş olabilir. İşletmelerle ticari
ilişki veya anlaşma yoktur; para karşılığı sıralama yapılmaz.

İşletme sahibiysen ve bilginin kaldırılmasını istiyorsan, uygulamadaki
bildirim kanalından ulaşman yeterli — talep en geç 7 gün içinde karşılanır.
