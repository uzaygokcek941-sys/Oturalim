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
- [x] 81 il çekimi — **33.552 mekan**, hiçbir il eksik değil
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

### Giriş sistemi — KURULDU (2026-08-20), Supabase anahtarı bekliyor

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

### Yayın için kalan (bunlar sende)
- [ ] **Google Form oluştur** (mekan adı, ödenen tutar, kişi sayısı, tarih, fiş)
      ve linkini `app/index.html` içindeki `PAYLAS_FORM` sabitine yapıştır
- [ ] KVKK metnindeki `iletisim@oturalim.app` adresini kendi adresinle değiştir
      (iki yerde: `#kvkk` ve `#bildir` pencerelerinde)
- [ ] Vercel'e `app` klasörünü yükle
- [ ] `@oturalim` handle'ını al, ilk 3 içeriği paylaş

### Sonraki
- [ ] Günde 1 içerik, kesintisiz
- [ ] Gelen her DM'e ilk 10 dakikada cevap
- [ ] Fiyat verisi büyüdükçe "ucuz/orta/pahalı" bandını hesapla

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
