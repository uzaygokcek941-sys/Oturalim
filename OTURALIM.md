# Oturalım

> **Bütçene göre otur.**

Çankaya (Ankara) ile başlıyor, sonra tüm Türkiye.

**Kapsam kararı (bu oturumda alındı):** İnsanları tanıştırma, eşleştirme ve
buluşturma özellikleri **çıkarıldı**. Gerekçe: yabancıları bir araya getiren bir
serviste taciz/rahatsızlık riski ve doğacak hukuki sorumluluk, sermayesiz ve
şirketsiz tek kişilik bir yapının taşıyabileceğinden büyük. Ürün saf mekan ve
fiyat keşfi olarak devam ediyor.

---

## FAZ 0 — Kararlar (kilitli)

| Karar | Değer |
|---|---|
| Ürün adı | **Oturalım** |
| Slogan | Bütçene göre otur. |
| İlk semt | **Çankaya, Ankara** → sonra 81 il |
| Ürünün tek işi | *Bütçeme göre nereye gidilir* |
| Odak süresi | 3 ay, tek ürün |
| Tek kanal | Instagram + TikTok organik. Reklam yok. |
| Gelir | **v1'de yok.** Kullanıcı birikene kadar ücretsiz. |
| Şirket | Gelir doğana kadar kurulmayacak |
| Maliyet | 0 TL — API anahtarı, kart, abonelik yok |

**Tek cümle:**
> Çankaya'da sınırlı bütçeyle dışarı çıkmak isteyenler için, mekanları gerçek
> fiyat bilgisiyle gösteren bir uygulama yapıyorum.

---

## Veri katmanı

Kaynak: OpenStreetMap / Overpass API — ücretsiz, anahtarsız, yeniden yayınlanabilir.

| Dosya | İçerik |
|---|---|
| `cankaya_mekanlar.csv` | **724** mekan (297 restoran, 234 kafe, 94 fast-food, 57 bar, 39 pub) |
| `turkiye_mekanlar.csv` | 81 il — çekim sürüyor |
| `cankaya_menu.csv` | **293** gerçek menü kalemi, 5 mekandan |
| `cankaya_menu_ozet.csv` | Site başına kalem sayısı ve medyan fiyat |

| Script | İş |
|---|---|
| `turkiye_cek.py` | İl il OSM çekimi (`python turkiye_cek.py TR-06`) |
| `mekan_isle.py` | Ham JSON → CSV (bbox tabanlı) |
| `menu_cikar.py` | Tek URL'den menü kalemi + fiyat |
| `menu_topla.py` | CSV'deki tüm sitelerden toplu menü toplama |
| `pilot_sec.py` | (artık kullanılmıyor — masa modeliyle birlikte düştü) |

### Ölçülen gerçek: fiyat kazınamıyor

Bunlar tahmin değil, çalıştırılıp görülen sonuçlar:

- Çankaya'daki 724 mekanın **57'sinin (%8)** websitesi var. Ankara ilinde %7.
- O 57 sitenin **5'inden (%8)** fiyat çıktı. 52'si menüyü JavaScript ile basıyor.
- Sonuç: mekanların **binde 6'sında** fiyat var, o da gürültülü
  (Kronotrop'un "medyan 1.050 TL"si kahve değil, satılan çekirdek paketi).

Ücretsiz fiyat kaynağı da yok: Google Places kart istiyor, Foursquare API ayda
500 çağrı veriyor (Çankaya bile sığmıyor), Foursquare açık verisinde fiyat alanı
olup olmadığı doğrulanamadı.

**Karar: fiyat kullanıcıdan gelecek.** Zaten ilk tasarımda da öyleydi.
Kazınan veri haritayı ve filtreleri veriyor; fiyatı kullanıcı koyuyor.
Avantaj: adiso boş haritayla çıktı, biz **724 mekanla** çıkıyoruz.

---

## Ürün — v1

| Katman | Kaynak | Durum |
|---|---|---|
| Mekan listesi + harita | OSM | ✅ hazır |
| Filtreler: tür, bahçe, wifi, açık saat, mesafe | OSM etiketleri | ✅ veri var |
| Fiyat | kullanıcı paylaşımı (hesap fotoğrafı / tutar) | uygulamada |
| Başlangıç fiyat verisi | 293 menü kalemi + elle giriş | ✅ elde |
| Barındırma | Vercel + Supabase ücretsiz katman | 0 TL |

Native mobil uygulama yok — web. Mağaza ücreti, inceleme süresi ve güncelleme
yükü şu aşamada gereksiz.

### KVKK — ilk sürümde, sonra değil

Tanıştırma çıktığı için yük büyük ölçüde azaldı ama sıfırlanmadı:

- Konum kullanılıyorsa açık rıza; kesin konum sunucuya yazılmaz
- Aydınlatma metni + gizlilik politikası
- Kullanıcı paylaşımı varsa: hesap/üyelik verisi için rıza, silme talebi kanalı
- Hesap fotoğrafında kart numarası / isim görünmesi ihtimaline karşı uyarı
- Paylaşımlarda mekan hakkında iftira/karalama riskine karşı bildir-kaldır kanalı

---

## İçerik planı — ilk 15

Format: dikey, 45-60 sn, ilk 3 saniyede hook, tek fikir, **somut rakam**.
Günde 1. Telefonla çek, kurgu yok. Kapanış çağrısı: **"Uygulamada hepsi var."**

| # | Fikir | Hook |
|---|---|---|
| 1 | Çankaya'da 200 TL'ye akşam: 3 mekan | "200 lirayla Çankaya'da akşam geçirilir mi? Denedim." |
| 2 | Kızılay'da kahvenin 40 TL olduğu yer | "Ankara'da kahve 40 lira, hâlâ." |
| 3 | 2 saat oturdum, hesap bu geldi (fiş göster) | "Bu hesabı görünce ben de şaşırdım." |
| 4 | Tunalı'da pahalı 3 yer + 50 m ötesindeki alternatifi | "Aynı sokakta, yarı fiyatına." |
| 5 | Çankaya'nın en ucuz 3. dalga kahvecisi | "Specialty kahve 60 liraya içilir mi? İçiliyor." |
| 6 | Öğrenci indirimi yapan mekanlar | "Öğrenciysen bu 5 yerde indirim var, kimse söylemiyor." |
| 7 | Priz, wifi, sessizlik: çalışılacak 5 kafe ve fiyatları | "Laptopla oturulacak yer arıyorsan." |
| 8 | Bahçesi olan ve hesabı 300 TL'yi geçmeyen yerler | "Bahçeli mekan pahalı olmak zorunda değil." |
| 9 | Çankaya'nın kitap kafeleri, hangisi uygun | "Ankara'da 4 kitap kafe var. Biri diğerinin yarısı fiyatına." |
| 10 | Aynı sokakta iki kafe, aynı kahve, iki kat fark | "Aynı kahve. 45 lira ve 95 lira." |
| 11 | Çankaya'da 724 mekanı tek tek çıkardım | "Ankara'daki bütün kafeleri listeledim." |
| 12 | 24 saat açık olan yerler | "Gece 3'te Ankara'da nerede oturulur?" |
| 13 | Hesap paylaşımı çağrısı | "Kazık yediğin yeri paylaş, başkası yemesin." |
| 14 | Sokak röportajı: Ankara'da 100 TL'ye ne yenir | "100 lirayla ne yiyebilirsin? Sordum." |
| 15 | Kazık uyarısı | "Bu fiyatı görünce fotoğrafını çektim." |

---

## İlerleme

### Bu 48 saat
- [ ] `@oturalim` Instagram ve TikTok handle'ını al
- [ ] Bio: *"Çankaya'da bütçene göre nereye gidilir. 724 mekan, gerçek fiyatlar."*
- [ ] İlk 3 içeriği çek ve yayınla (1, 2, 11)

### Ürün — TAMAMLANDI (tarayıcıda doğrulandı)
- [x] 81 il çekimi — **36.102 mekan** (eğlence dahil), hiçbir il eksik değil
- [x] `app_veri.py` ile il il JSON (`app/veri/<kod>.json` + `index.json`)
- [x] Harita + liste ekranı (Leaflet, OSM/CARTO döşeme)
- [x] Şehir seçici, tercih localStorage'da saklanıyor
- [x] Filtreler: tür, bahçe, wi-fi, şu an açık, fiyatı olan
- [x] Sıralama: A→Z, önce ucuz, bana yakın (konum izniyle)
- [x] Sayfalama — 200'er kart, büyük illerde donmuyor
- [x] Mekan detayı: bilgiler, telefon, site, menü kalemleri, yol tarifi
- [x] KVKK aydınlatma metni + gizlilik penceresi
- [x] Hata bildir / bildir-kaldır kanalı
- [x] Favicon, OG etiketleri, tema rengi
- [x] Mobil (375×812) ve masaüstü (1280×800) doğrulandı, yatay kaydırma yok
- [x] Açılış saati mantığı için kendi kendini kontrol (`?test=1`)

### Arayüz yenilemesi — TAMAMLANDI (2026-08-19, tarayıcıda doğrulandı)

Tek dosyalık uygulama beş sayfaya bölündü, ortak bir tasarım sistemi kuruldu.

| Dosya | İş |
|---|---|
| `app/stil.css` | Tasarım sistemi: renk/ölçü/tipografi token'ları, koyu + açık tema |
| `app/ortak.js` | Tema, açılış saati, bütçe bandı, biçimlendirme, kohort, `?test=1` |
| `app/index.html` | **Anasayfa** — bütçe seçici, canlı sayılar, türler, vitrin, dürüstlük bölümü |
| `app/kesfet.html` + `kesfet.js` | Harita + liste, bütçe kaydırıcısı, URL'de durum, mobil sekme |
| `app/paylas.html` | Fiyat paylaşma akışı; form bağlanana kadar e-posta yedeği |
| `app/hakkinda.html` | Veri kaynağı, yöntem, bilinçli yapılmayanlar |
| `app/gizlilik.html` | KVKK aydınlatma metni + bildirim kanalı (`#bildir`) |
| `app/vitrin.json` | `vitrin_uret.py` üretir — anasayfadaki rakamlar veriden gelir, elle yazılmaz |

Eklenenler: **bütçe filtresi** (ürünün asıl vaadi artık arayüzde), açık/koyu tema
(harita döşemesi de birlikte dönüyor), URL'de taşınan filtre durumu (link
paylaşılabilir), mobilde liste/harita sekmesi, iskelet yükleme, boş durum ekranları.

Ölçülen sonuçlar: `?test=1` → **13/13 kontrol geçti** · dokunma hedefi 44 px altında
**0 öğe** · yatay taşma **yok** (375 px ve 1280 px) · kontrast her iki temada en düşük
**4.65** (WCAG AA) · konsol hatası **yok**.

Eski tek dosyalık sürüm `app/kesfet-eski-yedek.html` olarak duruyor.

### Giriş sistemi — KURULDU (2026-08-20), anahtarlar girildi

Kimlik katmanı eklendi. **Anahtarlar girilene kadar site aynen önceki gibi
çalışıyor**; giriş özellikleri kapalı görünüyor.

| Dosya | İş |
|---|---|
| `veritabani/sema.sql` | 3 tablo + 9 RLS politikası + tetikleyiciler; kendini kontrol bloğuyla |
| `app/yapilandirma.js` | Supabase URL ve anon anahtar — **boş, senin doldurman gerek** |
| `app/kimlik.js` | Kayıt, giriş, oturum, parola sıfırlama, favori, paylaşım, yönetim |
| `app/giris.html` | Giriş / hesap aç / parola sıfırla / yeni parola — tek sayfa, dört kip |
| `app/hesabim.html` | Favorilerim, Paylaşımlarım, Ayarlar (ad, parola, hesap silme talebi) |
| `app/yonetim.html` | Fiyat paylaşımlarını onayla/reddet — yalnızca yönetici |
| `KURULUM.md` | 6 adımlık kurulum, ~15 dakika, kart istemiyor |

Mevcut sayfalara eklenenler: üst menüde giriş durumu, keşfet detayında
**favori düğmesi**, `paylas.html` artık girişliyken doğrudan veritabanına
gönderiyor (kimlik kapalıyken e-posta yedeği duruyor).

**Güvenlik:** yetki tarayıcıda değil veritabanında. `yonetim.html` sayfasını
gizlemek nezaket; asıl engel `yonetici_mi()` RLS politikası.

**Doğrulanan:** `?test=1` → 13/13 · kimlik doğrulayıcıları → 18/18 · kimlik
kapalıyken keşfet normal (6 mekan, detay açılıyor, favori düğmesi gizli) ·
konsol hatası yok · yatay taşma yok.
**Supabase bağlandı (2026-08-20):** proje `zlhlstfnayoaytoqmmcw`, şema kuruldu.
Doğrulanan: 3 tablo ayakta · anonim okuma boş dönüyor (RLS çalışıyor) · anonim
`INSERT` üç tabloda da **401 / 42501** ile reddediliyor (`yonetici:true` ile profil
ekleme denemesi dahil) · `yonetici_mi()` anonime `false` diyor · olmayan tablo 404
veriyor (kontrol testi) · auth ucu açık, e-posta doğrulaması zorunlu · yanlış
parolayla giriş → Türkçe hata mesajı · menüde "Giriş", detayda favori düğmesi
görünüyor · konsol temiz.

**Canlı doğrulandı (2026-08-20):** kayıt çalıştı (`enesdemirbaba06@gmail.com`) ·
profil tetikleyicisi otomatik satır açtı ve `ad` meta verisini geçirdi · yönetici
ataması tuttu (`yonetici = true`).

**RLS izolasyon testi geçti:** sahte bir authenticated kullanıcı (uydurma `sub`)
üç tabloda da **0** satır görüyor, `yonetici_mi()` **false** dönüyor.
Test SQL'i `begin/rollback` içinde, veriyi değiştirmiyor — tekrar çalıştırılabilir.

**İlk kurulumda çıkan hata ve düzeltmesi:** `yonetici_alani_korumali()` tetikleyicisi
SQL Editor'den yapılan güncellemeyi de engelliyordu (`auth.uid()` NULL →
`yonetici_mi()` false → P0001). İlk yönetici hiç atanamıyordu. Tetikleyici artık
yalnızca `auth.uid() is not null` iken devreye giriyor; anonim isteği zaten RLS'in
`id = auth.uid()` koşulu durduruyor. `sema.sql` güncellendi.

**Uçtan uca akış doğrulandı (2026-08-20):** favori ekleme · fiyat paylaşımı
gönderme · yönetici onayı — üçü de çalıştı. Onay sonrası sayaç bekleyen 0 /
onaylanan 1 oldu.

**Yol boyunca çıkan 3 hata ve düzeltmeleri:**
1. `.ust` isim çakışması — üst çubuk sınıfı liste kartlarına da uygulanıyordu
   (height 60px + border + sticky). `header.ust` yapıldı.
2. `[hidden]` eziliyordu — `.bos{display:grid}` gibi sınıflar HTML hidden
   özniteliğini geçersiz kılıyordu; gizlenen "Yükleniyor…" görünür kalıyordu,
   `#sifirla` ve `#d-favori` de kaçak görünüyordu. `[hidden]{display:none!important}`.
3. `.alt` isim çakışması — footer sınıfı liste satırının meta bölümüne
   sızıyordu (arka plan + 48px padding). `footer.alt` yapıldı.
Ders: tasarım sisteminde `ust`/`alt` gibi çok genel sınıf adları eleman tipine
bağlanmalı, yoksa bileşen içi kullanımlarla çakışıyor.

**Döngü kapatıldı (2026-08-20):** keşfet açılışta `onaylanmisPaylasimlar(il)`
ile onaylı kayıtları çekiyor, `mekan_id` üzerinden eşliyor. Kartta
"kişi başı ~X ₺" rozeti, detayda ayrı **Gerçekten ödenen** kutusu.
Menü fiyatından görsel olarak ayrı duruyor: menü işletmenin ilanı,
paylaşım fiilen ödenen tutar. Medyan kullanılıyor (tek aşırı kayıt
ortalamayı kaydırır, medyanı kaydırmaz) — `?test=1` ile 7 kontrol.
Eşleşme için `paylas.html` linkine `mekanId` eklendi.

**Yönetici silme politikası eklendi:** onaylanmış hatalı/sahte kaydı kimse
temizleyemiyordu (kullanıcının silme hakkı yalnızca `bekliyor` durumunda).

**Önbellek sorunu kökten çözüldü:** `python -m http.server` değişen .js/.css'i
tarayıcı önbelleğinden verdiği için kod güncellenmesine rağmen eski sürüm
çalışıyordu (üç kez yanlış teşhise yol açtı). `sunucu.py` artık
`Cache-Control: no-store` gönderiyor; `.claude/launch.json` buna bağlandı.

**Canlı veriyle denenmedi:** gösterim kodu yazıldı ve mantığı test edildi, ama
gerçek bir onaylı paylaşımla ekranda görülmedi (test kaydı sahteydi, silindi).
İlk gerçek paylaşım onaylandığında doğrulanmalı.

**Açık ayar riski:** `Confirm email` kapalı (`mailer_autoconfirm = true`), yani
e-posta doğrulanmadan hesap açılıyor. Test için pratik, yayın öncesi geri açılmalı.

**AÇIK GÜVENLİK SORUNU:** `service_role` anahtarı sohbete yapıştırıldığı için
ifşa sayılır. Supabase → Project Settings → API → JWT Settings →
**Generate new JWT secret** ile yenilenmeli; bu işlem anon anahtarı da değiştirir,
yeni anon anahtar `app/yapilandirma.js` içine yazılmalı.

**KVKK:** `gizlilik.html` hesap bölümüyle güncellendi, `hakkinda.html`'deki
"üyelik yok" satırı "zorunlu üyelik yok" olarak düzeltildi. Yayın öncesi
`iletisim@oturalim.app` yer tutucusu gerçek adresle değişmeli (3 dosya).

Yerelde çalıştırmak için: `python -m http.server 8123 --directory app`

### Kalanlar — tek liste (2026-08-23'te gerçeğe göre yenilendi)

İlerleme daha önce üç ayrı yerde yazılıydı ve bir kısmı gerçeğin gerisinde
kalmıştı. Aşağısı tek kaynak; kapananlar listeden düşürüldü.

**Kapandı, listeden düştü:** Google Form (yerine `paylas.html` + `paylasimlar`
tablosu geçti, `PAYLAS_FORM` sabiti kodda yok) · KVKK yer tutucu adresi
(gerçek adres üç dosyada da yerinde) · Supabase anahtarları (girildi).

**Sende (kod değil):**
- [x] `app/yapilandirma.js` → `sahiplenmeWhatsapp` dolduruldu (2026-08-23)
- [x] `sema.sql`, `sayac.sql`, `katki.sql` Supabase'de çalıştırıldı (2026-08-23)
- [ ] `@oturalim` handle (Instagram + TikTok), bio, ilk 3 içerik
- [ ] Vercel yayını
- [ ] Günde 1 içerik, gelen DM'e ilk 10 dakikada cevap

**Fiyat verisi — 2026-08-23'te ölçülüp düzeltilenler:**
- [x] Ortalama **ana ürün türü** üzerinden alınıyor. İçecek/tatlıyı elemek
      yetmiyordu: Domino's'ta pizza 15 kalem @480 ₺ ama yanındaki 7 tavuk
      garnitürü ve tost sayılmış bir dondurma ortalamayı 428 ₺'ye çekiyordu.
      Global "şu kategoriler ana yemek" listesi tutulmuyor — aynı kategori
      mekana göre değişiyor (fırında börek ana ürün, kebapçıda yan). Mekanın
      kendi dağılımına bakılıyor: en çok kalemli tür ana ürün, hacmi onun
      yarısı ve üstündekiler de sayılıyor. Ölçüldü: 132 mekanda fiyat
      yükseldi, 15'inde düştü, ortalama kayma +67 ₺. Hangi türden hesaplandığı
      ekranda yazıyor ("ortalama 528 ₺ (pizza)").
- [x] Gösterilen rakam **ortalama** oldu. Önce kategori medyanlarının medyanı
      alınıyordu; o "tipik bir kalem kaç lira" sorusunun cevabıydı, kullanıcının
      sorusu ise "burada kaça oturulur". Ölçüldü: 164 mekanın 131'inde rakam
      düştü, 31'inde yükseldi, ortalama kayma −34 ₺. Detay başlığı da artık
      en ucuz kalemle değil ortalamayla açıyor.
- [x] Tek kaleme dayanan yemek fiyatı iddiası kaldırıldı (`YEMEK_ASGARI_KALEM=2`).
      Kahve Dünyası'nın 74 şubesinde perakende ürün katalogundan tek kalem
      ("Tatlı 1@350") "yemek ~350 ₺" diye yazıyordu. İddia 246 → 164 mekan.
- [x] Kırpılmış menü artık kırpıldığını söylüyor (`kalem_n`). 131 mekanda kart
      "yemek ~480 ₺" derken detay "40 kalem · 35 – 165 ₺" gösteriyordu.
- [x] "Fiyatı olan" çipi `yemekFiyati` ile hizalandı — 203 mekan fiyat vaat
      edip fiyatsız kart veriyordu.
- [x] Menü olmayan listeler menü diye gösteriliyordu. 367 menülü mekanın
      75'inde liste kalem pil, kitap adı, küpe, sinema seansı, çadır
      konaklama ücreti ya da sayfanın kendi arayüz yazısıydı ("Normal fiyat",
      "55k kişi favoriledi!"). İki kapı kondu: kalem düzeyinde `ARAYUZ_AD`,
      mekan düzeyinde `menu_degil_mi` (33 türden hiçbirine uymayan liste
      düşer). Menülü mekan 367 → 292, fiyat iddiası 165 → 164.
- [x] Fiyatların YAŞI kondu. Toplayıcı betikler her satıra derleme gününü
      yazıyor; veri `tarih: "YYYY-AA"` taşıyor (kalemlerin **en eskisi** —
      yeni kalem eskisini tazelemez). Üç bant: 0-6 ay tarih yazılır, 6-12 ay
      "eski" işaretiyle, 12 aydan sonra **sayı gösterilmez**. Sınır
      `yemekFiyati()` içinde, yani kart, bütçe süzgeci ve "fiyatı bilinen"
      filtresi aynı cevabı alıyor.
- [x] Zincir menüsünün şubeye uygulanması **ölçüldü**. Menü anahtarı
      `(il, mekan adı)`, yani bir şube kendi sitesini bildirmemiş olsa bile
      aynı ildeki aynı adlı mekanın menüsünü alıyor: menü alan 401 mekanın
      **217'si (%54)** menüyü sadece adından alıyormuş. Kural bugüne kadar
      hiç yazılmamıştı; artık her çalıştırmada sayı basılıyor.

      Daha sıkı bir kural denendi ve **bırakıldı**: "gruptaki bütün web
      bildirimleri tek alan adında uzlaşsın". İstanbul'daki 52 Kahve Dünyası
      şubesini düşürüyordu — Atatürk Kitaplığı'ndaki şube kütüphanenin
      sitesiyle etiketlenmiş. Gerçek bir zinciri tek bir OSM etiketi yüzünden
      elemek olurdu ve yayılmanın bugün ürettiği yanlış eşleşme ölçülemedi:
      yayılan adların hepsi gerçek zincir (Domino's, Kahve Dünyası,
      Papa John's, Cajun Corner, Pizzabulls).
- [x] Platform profili menü kaynağı sayılmıyor. OSM'de **202 mekan** website
      etiketine bir sosyal medya / pazaryeri profili yazmış; üçü menü
      üretmişti. `shopier.com` Giresun'daki bir mekanla İstanbul'daki başka
      bir mekana **aynı pazaryeri katalogunu** yazmıştı, `trendyol.com` ise
      Trendyol'un arayüzünü ("55k kişi favoriledi!"). Alan adına bakılıyor,
      yola değil — `qrmenu.actdurum.com` işletmenin kendi QR menüsü, kalıyor.
- [x] Aynı işletmenin iki kaydı ayrı mekan sayılıyordu: OSM'de bir yer hem
      nokta (POI) hem alan (bina) olarak etiketlenebiliyor. Aynı il + aynı ad
      + **≤25 m** kuralıyla 250 kayıt birleştirildi (36.102 → 35.852).
      Ad karşılaştırması Türkçe harfe duyarsız: "Balıkçı Sabahattin" ile
      "Balikci Sabahattin" aynı yer. Eşik ölçümle seçildi; 40 m'de
      "Starbucks 54 m", "Çay ocağı 53 m" gibi gerçek ayrı işletmeler
      karışıyor. Düşen kaydın alanları kalana taşınıyor — 250 birleşmede
      bilgi kaybı 0. Çıktı `test.py`'de de denetleniyor.
- [x] **Ucuz / orta / pahalı bandı.** Mekanın ana ürün türüne göre: pizzacı
      pizzacılarla, kebapçı kebapçılarla kıyaslanıyor. Ülke ortalamasına göre
      söylemek anlamsızdı — 900 ₺'lik balıkçı "pahalı", 480 ₺'lik pizzacı
      "ucuz" çıkardı ve ikisi de yanlış olurdu.

      Kanıt eşiği var ve **çoğu zaman susuyor**: fiyat iddiası olan 163
      mekanın **14'ü** band alıyor (7 pahalı, 4 orta, 3 ucuz). Band
      çıkmayan 149'un **107'si pizzacı** — Türkiye pizza ölçütü yalnız 5
      markadan çıkıyor ve 5 markaya dayanıp "bu pizzacı pahalı" demek
      uydurma seviyeden farksız olurdu. Sayı, veri büyüdükçe büyür.

      Bir mekanın birden çok ana ürünü varsa hepsinin **aynı yönü**
      göstermesi aranıyor; biri ölçülemiyorsa band hiç gösterilmiyor.
- [x] İki boru hattının fiyat sınırı ayrışmıştı: ölçüt 5–3000 ₺, uygulama
      25–2000 ₺ kullanıyordu. Yani ölçüt, uygulamanın **göstermediği**
      kalemlerden hesaplanıyordu — 12,55 ₺'lik bir "Pizza margherita"
      markanın medyanı olup Türkiye pizza bandını bozuyordu. Hizalandı:
      eşiği geçen kategori 8 → 10, bant genişliği Pizza'da 1,03 → 0,19.
- [x] Zayıf il ölçütü, güçlü ülke ölçütünü bastırıyordu: il kaydı **varsa**
      kullanılıyor, eşiği geçmezse cevap susuyordu. Artık en özel ölçüt
      ancak kanıt barını geçerse kazanıyor; geçmezse ülkeye düşülüyor.

**Üründe — ağ mekanikleri (fiş katmanı commit'inde sayılmıştı, hiçbiri başlamadı):**
- [ ] Bütçe akranları
- [x] Bayat fiyat hatırlatması — veri artık tarih taşıyor, uyarı ekranda
- [ ] Mahalle statüsü

**Üründe — dijitalleşmemiş işletme planı:**
- [x] Faz 1 — eksik bilgi katkı hattı (`katki.sql`, form, onay, takip)
- [x] Faz 2 — yürüyüş kümeleri (`sahiplen.py` → `sahiplenme_kume.csv`)
- [x] Faz 3 — saha (`saha.py`). En yoğun kümeler seçiliyor, her mekana özel
      **QR + tek kullanımlık kod** taşıyan A4 kart basılıyor, Supabase'e
      yapıştırılacak SQL ve sahada işaretlenecek ziyaret listesi üretiliyor.
      Üçüncü ayak ölçüm: `python saha.py olc` kart bırakılan mekanların
      görüntülenmesini, sahiplenmesini ve onaylı katkısını sayıyor.
      Alan adı dışarıdan veriliyor (`site_haritasi.py` ile aynı gerekçe:
      uydurma alan adıyla basılmış kart, basılmamış karttan kötü).
- [x] Faz 4 — sahiplenme kodu ve doğrulama akışı (`veritabani/sahiplenme.sql`).
      Kod **orada bulunmayı** kanıtlar, tapuyu değil; bu yüzden yetki sınırlı
      (yalnız saat/telefon/adres/site) ve sahiplik geri alınabilir. Gerçek
      Postgres 16'da 11 davranış kontrolü, uçtan uca üretilmiş kartlarla
      doğrulandı.
- [ ] Kart metni ve bırakma biçimi sahada denenmedi. `saha.py olc` sıfır
      sahiplenme gösteriyorsa metin değişmeden ikinci kümeye çıkılmamalı.

**Yayın yapılandırması:**
- [x] `vercel.json` yalnızca çıktı klasörünü söylüyordu, hiç güvenlik başlığı
      yoktu. Eklendi: `X-Content-Type-Options`, `Referrer-Policy`,
      `X-Frame-Options`, `Permissions-Policy` + veri/varlık/HTML için ayrı
      önbellek kuralları. `test.py` dosyanın geçerli JSON olduğunu ve
      başlıkların durduğunu denetliyor — geçersiz JSON'da Vercel
      yapılandırmayı **sessizce yok sayar**, yani başlık kaybı hiçbir yerde
      patlamaz.
- [ ] **CSP bilerek yok.** Supabase adresi kuruluma göre değişiyor
      (`yapilandirma.js`); depoda sabit bir CSP yazmak, başka bir Supabase
      projesiyle kuran kişinin girişini sessizce kırardı. Tek bir kurulum
      sabitlendiğinde eklenmeli: `fonts.googleapis.com`, `fonts.gstatic.com`,
      `unpkg.com`, `esm.sh` ve o kurulumun `*.supabase.co` adresi.

**Gerçek tarayıcıda açınca bulunanlar (`test_sayfa.py`):**
- [x] Leaflet CDN'den gelmeyince keşfet ekranının **tamamı** ölüyordu
      (`L is not defined`): sıfır kart, sayaç "…"da donmuş. Harita artık
      isteğe bağlı; liste, filtreler ve bütçe kaydırıcısı haritasız çalışıyor.
- [x] `isletme.html` `sahne.js`'i hiç yüklemiyordu; "Bu sayfada eksik olanlar"
      bölümü — sayfanın çekirdeği — `clip-path` ile kırpılmış hâlde **her
      ziyaretçide görünmüyordu**. `checkVisibility()` bile "görünür" diyor.
- [x] Konum izni **yanıtlanmazsa** kullanıcı kilitleniyordu: `getCurrentPosition`
      timeout'u izin istemi cevaplanana kadar saymaya başlamıyor, yani hiçbir
      geri çağrı gelmiyor. Sayfanın kendi bekçisi kondu.
- [x] Instagram toplanıyor ama uygulamaya hiç ulaşmıyordu: **192 mekanın**
      instagramı var ve sitesi yok, onlara hem sayfada hem saha kartında
      "sosyal medya bağınız yok" diyorduk.

**Kodda kalan teknik borç:**
- [x] Leaflet SRI ile geliyor (özet npm tarball'ından, resmî değerlerle doğrulandı)
- [ ] **supabase-js hâlâ SRI'siz** — `import()` integrity desteklemiyor, yerele
      almak da derleme adımı ister. Üç import noktası bire indirildi; kalan tek
      yer `kimlik.js`. Gerçek çözüm: sürüm sabit, esm.sh'e güveniliyor.
- [x] `isletme.html`'in mükerrer Supabase istemcileri kaldırıldı (`Kimlik.istemci()`)
- [x] Koordinatlar 5 basamağa indi — İstanbul 414 → 400 KB gzip
- [ ] **İstanbul dosyası hâlâ 1,7 MB ham / 406 KB gzip.** Ölçüldü: geri kalan
      ağırlığın tamamı keşfet ekranının gerçekten kullandığı alanlar. Menü/kategori
      ayrı dosyaya alınamıyor (bütçe süzgeci çizimden önce onlara bakıyor);
      hafif dosya + tam dosya ayrımı ana huniyi (anasayfa → keşfet) kötüleştiriyor,
      çünkü ikisi aynı önbelleği paylaşıyor. Gerçek çözüm coğrafi bölmeleme, o da
      veri düzenini ve iki tüketiciyi birden değiştirir.
- [x] Kontroller CI'da koşuyor (`python test.py` · GitHub Actions, her itmede)
- [x] `kacir()` tek tırnağı da kaçırıyor; paylaşım/katkı günlük gönderim sınırı kondu
- [x] "Ucuz / orta / pahalı" bandı kuruldu (yukarıda). Bugün 163 mekanın
      **14'ünde** çıkıyor; kalanın çoğu pizzacı ve Türkiye pizza ölçütü
      yalnız 5 markadan geliyor. Kanıt eşiği **düşürülmeyecek** — sayı veri
      büyüdükçe kendiliğinden büyür.

      Sayı 18'den 14'e indi ve bu bir gerileme değil: `İ` sınıflandırma
      hatası düzelince İstanbul tatlı ölçütünün bandı 0,68'den 0,84'e
      **genişledi** — gerçek yayılım görünür oldu ve kanıt eşiğini
      geçmiyor. Önceki 18'in dördü, göründüğünden gevşek bir ölçüte
      dayanıyormuş. **Hata düzeltmek iddiayı azaltabilir.**

---

## Yapılmayacaklar

| Yapma | Neden |
|---|---|
| **İnsanları tanıştırma / eşleştirme** | Taciz riski ve hukuki sorumluluk; tek kişilik yapı taşıyamaz |
| Native mobil uygulama | Mağaza ücreti, inceleme, güncelleme yükü |
| Şirket kurmak | Gelir yokken aylık ~10-12 bin TL Bağ-Kur primi |
| Domain satın almak (şimdi) | Vercel alt alan adı yeterli |
| Reklam vermek | Bütçe yok |
| Google Maps kazımak | ToS ihlali, ban riski, yayınlama hakkı yok |
| Yemeksepeti / Getir / Trendyol kazımak | ToS ihlali + ihtarname riski; sermayesiz yapıda işi bitirir |
| İkinci semt (üründen önce) | Çankaya ile yayına çık, sonra genişlet |

---

## 2026-08-20 — Fiyat kazıma yolu kapandı (ölçülmüş)

Üç ayrı ölçüm yapıldı, üçü de aynı sonuca çıktı: **Türkiye'de işletmeler
fiyatlarını internete koymuyor.** Bu teknik bir engel değil, sektörün durumu.
Aşağısı, "PDF menüleri okusak / JavaScript'i çalıştırsak" sorusu tekrar
gündeme geldiğinde yeniden saat harcamamak için kaydedilmiştir.

### Ölçüm 1 — JavaScript engeli diye bilinen şey engel değilmiş

`tr_menu_ozet.csv`'de 2.294 site "js" işaretliydi ve bu, menülerin JS ile
basıldığı için okunamadığı anlamına geliyor sanılıyordu. Playwright (headless
Chromium) ile JS çalıştırılıp menü sayfasına da gidildi. **20 rastgele sitenin
20'sinde de metin fiyatı çıkmadı.**

| Durum | Adet |
|---|---|
| Menü sayfası bulunamadı | 7 (%35) |
| PDF menü | 4 (%20) |
| Menü sayfası var, fiyat yok | 4 (%20) |
| Site ölü / erişilemiyor | 4 (%20) |
| Görsel (JPEG) menü | 1 (%5) |

İki temsili örnek: **Cihangir Kebap** menü sayfasında yemek adları yazıyor,
fiyat hiç yok — işletme yayınlamıyor. **Güney Yıldızı**'nın menüsünün tamamı
tek bir `menu.jpeg` fotoğrafı.

### Ölçüm 2 — PDF metin katmanı: 200 sitede sıfır kalem

`menu_pdf_tara.py` yazıldı: menü sayfasını bulur, PDF/görsel toplar, PDF
metin katmanından PyMuPDF ile fiyat çıkarır (API'siz, ücretsiz). 200 site:

| Durum | Adet |
|---|---|
| Menü sayfası bulunamadı | 101 (%50) |
| **Site ölü / erişilemiyor** | 39 (%20) |
| PDF var ama menü değil | 36 (%18) |
| PDF taranmış, OCR gerekli | 15 (%8) |
| Görsel menü, OCR gerekli | 8 (%4) |
| **Çıkarılan gerçek menü kalemi** | **0** |

İlk turda 23 kalem çıkmıştı ve hepsi çöptü: Starbucks'ınki bir *Modern
Slavery Statement*'tan "FOR FISCAL YEAR 2025", Big Chefs'inki bir
sürdürülebilirlik raporundan iklim senaryosu tablosu. Bulunan PDF'ler menü
değil kurumsal belgeydi. `menu_mu()` eklendi: çıkan adlar
`fiyat_analiz.kategorile` ile yiyecek olarak sınıflanmıyorsa PDF reddedilir.
Filtreden sonra ücretsiz yolun verimi **tam olarak sıfır**.

Ayrıca sitelerin **%20'si ölü** — OSM'deki `website` etiketleri bayatlamış.

### Ölçüm 3 — OCR'ın tavanı

Geriye OCR gerektiren %12 kalıyor (taranmış PDF %8 + görsel menü %4).

```
2.294 js site × %12          ≈ 275 mekan   (TAVAN — OCR'ın başarması ve
                                            menünün güncel olması şartıyla)
Şu anki fiyatlı mekan        = 383
OCR sonrası en iyi hal       ≈ 658  → 33.552 içinde %2,0
```

İl kırılımı: İstanbul ~39, Antalya ~5, İzmir ~5, **Ankara ~4** mekan.
Yani hedef şehirde kazanç 6 mekandan 10 mekana çıkmak.

### Karar

Kazıma yolu kapandı. Kapsamı %1,1'den %2'ye taşımak için kurulacak bir OCR
hattı, hedef şehirde 4 mekan ekliyor. Kalan iki yol **elle veri girişi** ve
**kullanıcı paylaşımı**; ikisinin de altyapısı hazır (yönetim paneli, paylaşım
formu, onay akışı, `kat` kategori kırılımı, `fiyat_olcut.json`).

Hedef değişmiyor: **Çankaya'da 80-100 mekan.** Bir semtte %90 kapsam, 81 ilde
%1'den değerlidir.

### Ölçüm 4 — Tam tarama fiilen yapıldı (2026-08-21)

Yukarıdaki tavan hesabına rağmen tarama sonuna kadar çalıştırıldı. **2.646
kayıt** işlendi (OSM'de sitesi olan 2.024 tekil mekanın hepsi dahil). Bu
sırada iki kör nokta ortaya çıktı ve kapatıldı:

- **703 site hiç denenmemişti.** `tr_menu_ozet.csv` yalnız 1.321 siteyi
  kapsıyordu. Aradaki farkta QR menü platformları vardı (allzinapp,
  guestservice.app, cciqrmenum).
- **Sayfa metni hiç okunmuyordu.** Tarayıcı yalnız PDF ve görsel arıyordu.
  Eski kazıyıcı JS çalıştırmadığı için bu sayfaları okuyamamıştı; yeni
  tarayıcı JS çalıştırıyordu ama metne bakmıyordu. Sıralama artık
  **sayfa metni → PDF → görsel**.

| Durum | Adet |
|---|---|
| Menü sayfası bulunamadı | 1.501 (%57) |
| Site ölü / erişilemiyor | 652 (%25) |
| PDF taranmış, OCR gerekli | 220 (%8) |
| Görsel menü, OCR gerekli | 183 (%7) |
| PDF var ama menü değil | 53 (%2) |
| **PDF metni** | 7 |
| **Sayfa metni** | 1 |

### Elde edilen gerçek veri: 483 kalem / 8 mekan

| Mekan | İl | Kalem | Kaynak |
|---|---|---|---|
| Sakhalin İstanbul | İstanbul | 142 | PDF metni |
| Nezih Dokuz Ondokuz | İstanbul | 100 | PDF metni |
| Fern Cafe | İstanbul | 94 | PDF metni |
| Cozy Etiler | İstanbul | 71 | PDF metni |
| Santral Coffee House | İstanbul | 39 | PDF metni |
| Tarhun fırın | İstanbul | 15 | Sayfa metni |
| 360 Istanbul | İstanbul | 14 | PDF metni |
| Güney Yıldızı | Adana | 8 | Görsel OCR |

497 PDF kaleminin **497'sinin** kaynak dosyada birebir geçtiği programatik
olarak doğrulandı. Güney Yıldızı'nın 8 kalemi görselle gözle karşılaştırıldı,
8/8 doğru. Verim: **8 / 2.646 = %0,3**.

Veri `app_veri.py`'a ikinci kaynak olarak bağlandı (`ek_menuler_oku`,
birleştirme anahtarı web sitesi; OSM etiketi yollu olabildiği için tam adres
tutmazsa alan adına düşülüyor — ama yalnız o alan adı tek mekana aitse).
Fiyatlı mekan **383 → 391**.

### OCR kurulu ama beş denetimle sarılı

NVIDIA NIM (`nemotron-nano-12b-v2-vl`) anahtarı `.env`'de, `.gitignore`
kapsıyor. **Model ikna edici uyduruyor** — bu oturumda beş ayrı vaka çıktı ve
**hepsi ancak kaynağa elle bakılınca** görüldü. Her biri için kalıcı denetim
eklendi ve teste gömüldü:

| Vaka | Ne oldu | Denetim |
|---|---|---|
| Sagaris | Fiyatsız menüde sıra numaralarını görüp 12 kaleme 123 TL yazdı | `uydurma_mi()` + PDF metin karşılaştırması |
| 4 mekan | Platform şablon görseli 8 mekana atanmıştı | Paylaşılan-URL denetimi |
| Adanalı Kebapçı | "Menü" aslında yemek fotoğrafı, üzerinde tek harf yok | Nötr "yazı var mı" ön kapısı |
| Muhtar | Fix menü fiyatı (2.500₺) 9 ayrı yemeğe yazıldı | `FIX_MENU` denetimi |
| Bağdat Marmaris | restaurantguru filigranlı, isimler bozuk, bir fiyat yanlış | `UCUNCU_TARAF` denetimi |

Ayrıca iki ayrıştırma hatası: şarap yılı (`Gelibolu /2022`) fiyat sanılıyordu;
boşluklu binlik (`3 230`) 230 okunuyordu — ikincisi Sakhalin'in 142 kaleminin
tamamını yok etmişti.

**Kural: görsel OCR çıktısı insan doğrulaması olmadan uygulamaya girmez.**
PDF ve sayfa metni farklı — orada model araya girmiyor, sayı dosyanın içinde
birebir yazıyor, uydurma fiziksel olarak mümkün değil.

### Karar değişmedi

2.646 kayıt tarandı, 8 mekan çıktı. **Ankara'ya katkı sıfır** — 8 mekanın
7'si İstanbul, biri Adana. Ankara'da fiyatlı mekan 6'da kaldı.

Kazıma yolu bitti ve bu sefer sonuna kadar gidilerek bitti. Kalan tek yol
**elle veri girişi + kullanıcı paylaşımı**. Hedef aynı: **Çankaya'da 80-100
mekan.**

`menu_ocr.py` ileride işe yarar: Çankaya'da menü fotoğrafı çekilirse fiyatları
elle yazmak yerine fotoğrafı okutabilirsin — ama çıktı gözle doğrulanmadan
kaydedilmez.
