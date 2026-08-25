# Cebimde

> **Cebindeki bütçeyle keşfet.**

Türkiye'deki kafe, restoran ve barları bütçene, bahçesine ve şu an açık olup
olmadığına göre süzen web uygulaması. Üyelik zorunlu değil, reklam yok, çerez yok.

**35.852 mekan · 81 il · 7.141 menü kalemi · 774 etkinlik**

---

## Ne yapıyor

Dışarıda oturmak pahalılaştı ve fiyatlar öngörülemez hale geldi. Aynı sokakta
iki kafe, aynı kahve, iki kat fark olabiliyor. Uygulamanın tek işi:
**bütçene göre nereye gidilebileceğini göstermek.**

- Bütçeyle başlayan ana ekran: *"Bugün cebimde ₺300"* → kategori → yakınımda bul
- Bütçenin ne kadarının **ölçüm**, ne kadarının **tahmin** olduğu ekranda yazıyor
- Fiyatın kaç ölçümden geldiği yazıyor: zincir menüsünden gelen rakam "3 şubede aynı menü" diye işaretleniyor
- Fiyat güven skoru — yeşil (kendi menüsü ya da üç fiş) / sarı (zincir, eskimiş) / kırmızı (ölçüm yok)
- Harita bütçeye göre renkleniyor; renk bandı, doygunluk ne kadar emin olduğumuzu gösteriyor
- Harita + liste, 81 ilin tamamı
- Bütçe kaydırıcısı — mekanın ana ürün ortalamasına göre süzme
- Ucuz / orta / pahalı bandı — kendi türündeki mekanlara göre, kanıt varsa
- Filtreler: tür, bahçe, wi-fi, şu an açık, fiyatı bilinen
- Yeme-içmenin yanında eğlence: sinema, tiyatro, müze, konser ve festivaller
- Her mekanın kendi sayfası — eksik bilgisi, ödenen hesaplar, görüntülenme sayısı
- Eksik bilgiyi ziyaretçi tamamlayabiliyor (saat, telefon, adres, site) — onaydan geçer
- İşletme sahibi kapıya bırakılan karttaki kodla sayfasını sahipleniyor;
  eklediği saat/telefon/adres/site sıraya girmeden yayına çıkıyor
- Açık/koyu tema (harita döşemesi de birlikte döner)
- Filtre durumu URL'de — görünüm olduğu gibi paylaşılabilir
- Arama Türkçe harfe duyarsız — "kofte" ile "köfte" aynı sonucu verir
- İsteğe bağlı hesap: favori mekanlar, fiyat paylaşımı, yönetici onayı

## Veri nereden geliyor

| Katman | Kaynak | Lisans |
|---|---|---|
| Mekan adı, konum, tür, saat, bahçe, wi-fi | OpenStreetMap (Overpass API) | ODbL |
| Menü fiyatları | İşletmelerin **kendi** sitelerinde yayımladığı menüler | — |
| Ödenen tutarlar | Kullanıcı paylaşımı (onaydan geçer) | — |
| Eksik saat, telefon, adres, site | Kullanıcı katkısı (onaydan geçer) | — |
| Konser, festival, fuar | etkinlik.io RSS akışları | — |

Google Maps, Yemeksepeti, Getir gibi platformlardan **hiçbir veri alınmadı**;
kullanım şartları buna izin vermiyor.

Dürüst not, dört katmanlı: **35.852 mekanın 291'i (%0,81)** menüsünü
yayımlamış. O 7.141 kalem bağımsız değil — **%70,8'i zincir tekrarı**, yani
geriye **85 farklı menü** kalıyor (bir Domino's menüsü 96 şubeye uygulanıyor).
Ve uygulama bunların yalnız **163'ünde** bir rakam söylüyor: mekanın
**ana ürün türünün ortalaması**. En ucuz kalem değil, içecek değil, garnitür
değil — pizzacıda pizzaların, fırında böreklerin ortalaması. Hangi türden
hesaplandığı ekranda yazıyor. Tek kaleme dayanan iddia gösterilmiyor.

Dördüncü katman: bir listenin menü **olduğu** da doğrulanıyor. Kazıyıcı bazı
sitelerde menüyü değil başka bir sayfayı bulmuş; 75 mekanın "menü"sü kitap
adı, kalem pil, küpe, sinema seansı, çadır konaklama ücreti ya da sayfanın
kendi arayüz yazısıydı ("Normal fiyat", "55k kişi favoriledi!"). Hiçbiri
fiyat iddiası üretmiyordu ama **Menü** başlığı altında duruyordu; başlık
yalan söylüyordu. Listenin hiçbir kalemi 33 yiyecek/içecek türünden birine
uymuyorsa liste bütünüyle düşüyor.

Aynı işletmenin iki kaydı da birleştiriliyor. OpenStreetMap'te bir yer hem
**nokta** (POI) hem **alan** (bina sınırı) olarak etiketlenebiliyor, ya da
aynı yeri iki kişi ayrı ayrı eklemiş oluyor; ikisi de bize ayrı mekan gibi
geliyordu — haritada iki işaretçi, listede iki kart. Aynı ilde aynı adı
taşıyan ve **25 m**'den yakın 250 kayıt birleştirildi (ad
karşılaştırması Türkçe harfe duyarsız: "Balıkçı Sabahattin" ile
"Balikci Sabahattin" aynı yer). Eşik ölçümle
seçildi: 40 m'ye çıkınca "Starbucks 54 m", "Çay ocağı 53 m" gibi
gerçekten ayrı işletmeler karışmaya başlıyor. Düşen kaydın boş olmayan
alanları kalana taşınıyor, bilgi kaybı yok.

Beşinci katman, fiyatın **yaşı**. Enflasyonda tarihsiz fiyat bir iddia değil
bir tahmindir; veri artık her menünün derlendiği ayı taşıyor. Altı aydan
eskiyse tarih uyarı şeridiyle, bir yıldan eskiyse **rakam hiç gösterilmiyor**
— mekan ölçülmemiş mekanlar gibi davranıyor. Bu sınır tek yerde (`yemekFiyati`)
duruyor, dolayısıyla kart, bütçe kaydırıcısı ve "fiyatı bilinen" filtresi
aynı cevabı veriyor.

Denenen sitelerin yalnızca **%7'sinden** fiyat çıkarılabildi, geri kalanı
menüsünü JavaScript ile basıyor. Bu yüzden fiyat verisi bugün zayıf ve ancak
kullanıcı paylaşımıyla büyür.

İkinci ölçüm, ilkini açıklıyor: mekanların **%91,6'sının webi veya sosyal medyası**, **%89,2'sinin
telefonu** açık veride yok; **%84,8'inde ikisi birden yok**. Yani işletmelerin
büyük kısmına uzaktan sorulamıyor bile. `sahiplen.py` bu yüzden iki liste
üretiyor — telefonu olanlar için iletişim listesi, olmayanlar için yürüyerek
gezilebilecek kümeler.

## Çalıştırma

Derleme adımı yok, bağımlılık yok. Python 3 yeterli:

```bash
python sunucu.py
```

→ http://localhost:8123

Kontroller tek komutla:

```bash
python test.py
```

Betiklerin kendi kontrolleri, sayfayı **açmadan** koşan tarayıcı
kontrolleri, sayfaları **gerçek Chromium'da açan** kontroller ve dosyalar
arası değişmezler birlikte koşar. Her itmede GitHub Actions da
aynısını çalıştırıyor. `node` kurulu değilse tarayıcı grubu **atlanır** —
geçtiği söylenmez.

CI ayrıca veriyi yeniden üretip fark olup olmadığına bakıyor: `test.py`
çıktının kendi **içinde** tutarlı olduğunu doğruluyor, o adım çıktının
**kaynakla** tutarlı olduğunu. Bir betiği değiştirip veriyi yeniden
üretmeyi unutmak aksi halde sessiz kalıyor. Veri değiştiren bir düzenleme
sonrası:

```bash
python app_veri.py && python fiyat_analiz.py && python vitrin_uret.py
```

Giriş sistemi olmadan da tam çalışır; hesap özellikleri kapalı görünür.
Kurmak için: [KURULUM.md](KURULUM.md) (~15 dakika, ücretsiz, kart istemiyor).

## Yapı

```
app/                 Uygulama — statik HTML/CSS/JS, derleme yok
  index.html         Anasayfa: bütçe girişi, kategori, yakındaki üç öneri
  kesfet.html/.js    Harita + liste + filtreler
  isletme.html       Tek işletme sayfası: bilgi, eksikler, katkı, fiş, sayaç
  paylas.html        Fiyat paylaşma
  hesabim.html       Favoriler, paylaşımlar, katkılar, ayarlar
  yonetim.html       Paylaşım ve katkı onayı (yönetici)
  giris.html         Giriş / kayıt / parola sıfırlama
  kimlik.js          Supabase kimlik ve veri katmanı
  ortak.js           Tema, açılış saati, biçimlendirme, katkı doğrulama
  stil.css           Tasarım sistemi (token tabanlı, iki tema)
  sahne.css/.js      Sinematik giriş katmanı
  veri/<il>.json     Mekan verisi, il başına
  veri/etkinlik.json Konser, festival, fuar — günlük tazelenir
veritabani/sema.sql  Tablolar + RLS politikaları
veritabani/sayac.sql Görüntülenme sayacı
veritabani/katki.sql Eksik bilgi katkıları
veritabani/sahiplenme.sql  İşletme sahiplenme kodu + doğrulama
*.py                 Veri toplama ve işleme betikleri
menu_cikar.py        HTML'den fiyat çıkarma (TR/EN sayı biçimleri)
etkinlik_cek.py      etkinlik.io RSS → app/veri/etkinlik.json
sahiplen.py          İşletme hedefleri + saha yürüyüş kümeleri
saha.py              Saha kartları (QR + kod), dağıtım sonrası ölçüm
site_haritasi.py     sitemap.xml + robots.txt üretimi
test.py              Bütün kontroller (tek giriş noktası)
test_tarayici.mjs    Tarayıcı kontrollerini tarayıcısız koşturur
test_sayfa.py        Sayfaları gerçek Chromium'da açar (CDN'ler kapalı)
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
