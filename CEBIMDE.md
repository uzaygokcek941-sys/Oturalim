# Cebimde

> **Cebindeki bütçeyle keşfet.**

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
| Ürün adı | **Cebimde** |
| Slogan | Cebindeki bütçeyle keşfet. |
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

## Yatırım ve San Francisco yol haritası

Nevzat Aydın gibi melek yatırımcılardan yatırım almak ve Y Combinator'a
girmek için araştırma + tarihli yol haritası: **`PAZARLAMA.md`**.

Üç şey oradan buraya taşınacak kadar önemli:

0. **KARAR VERİLDİ (28 Ağustos 2026): şirket kurulmuyor.** Faz 0 olduğu
   gibi kalıyor; melek yatırımı ve YC masadan kalktı. Webrazzi de
   İstanbul'da olduğu için hedef **Ankara'ya** çekildi:
   **21 Ekim — TechAnkara Proje Pazarı** (başvuru kapandı, ziyaretçi
   olarak gidilir) ve **8 Aralık — 18. Ankara Start-Up Zirvesi**
   (başvuru açık, şirket şartı görünmüyor). Ayrıntı `PAZARLAMA.md` B3.

1. **Faz 0 iki hedefi birden bloke ediyor.** *"Şirket: gelir doğana kadar
   kurulmayacak"* kararı dururken ne melek yatırımı alınabilir (hisse için
   şirket gerekir) ne de YC'ye girilebilir (ABD/Cayman/Singapur çatısı
   isteniyor). Karar senin; üç seçenek `PAZARLAMA.md` B4'te.
2. **Asıl sorun kapsama, ve yeri belli.** Kadıköy Moda/Bahariye'de
   **500 metrede 474 mekan var, 4'ünde fiyat yazıyor (%0,8)**. Yatırımcı
   toplantıda telefonu açarsa bunu görür. 35.852 rakamı burada yardım
   etmiyor, zarar veriyor.
3. **Takvim dışarıdan geliyor.** Webrazzi Summit **21 Ekim 2026**
   (Nevzat Aydın konuşmacı) · YC Winter 2027 başvurusu **~Kasım 2026**
   (Fall 2026 son tarihi 27 Temmuz'du, geçti) · grup **Ocak–Mart 2027,
   San Francisco**.

## Kalan veri ve gelir planı

Kalan 35.559 işletmenin fiyatı, adresi, menüsü ve hesabı nereden gelecek,
ve bundan nasıl para kazanılır: **`VERI_VE_GELIR.md`**.

Bugün koşulabilecek üç şey (kod tarafında hiçbir şey beklemiyor):

1. `python menu_ocr.py tam` — **422 satır / 283 mekan** OCR kuyruğunda
   bekliyor; okuyucu var ve doğruluğu ölçülmüş (8/8), bugüne kadar yalnız
   pilot koşulmuş (1 mekan).
2. ~~Tarayıcıyla JS menüleri~~ — **ölçüldü ve çürüdü**: GitHub
   koşucusunda 40 alan adında **0 kalem**. `menu_pdf_tara.py` bu işi
   zaten yapıyor ve menü bağlantısını da takip ediyor. Yazdığım betik
   silindi, `robots.txt` kapısı ona taşındı.
3. `python turkiye_cek.py` — Facebook/X/TikTok/YouTube sütunları CSV'de
   hiç yok; kod beşini de okuyor.

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
- [ ] `@cebimde` Instagram ve TikTok handle'ını al *(hesap senin, kod tarafı yok)*
- [x] Bio yazıldı — **eski taslak iki yerinden yanlıştı** ve düzeltildi:
      ~~"Çankaya'da bütçene göre nereye gidilir. 724 mekan, gerçek fiyatlar."~~
      724 → **35.852** (uygulama Çankaya'yı aştı, 81 il), ve *"gerçek fiyatlar"*
      abartı: 35.852 mekanın **293'ünde** menü fiyatı var (%0,82). Manşete
      çıkarmak, gelen kullanıcının ilk açtığı on mekanda fiyat görmemesi
      demekti — *yanlış fiyat, fiyat olmamasından kötü* kuralı vaat için de
      geçerli. Yerine: **"Cebindeki bütçeyle keşfet. 81 ilde 35.852 mekan. Fiyatı
      gidenler yazıyor."** Son cümle katkı çağrısını bio'nun içine koyuyor.
- [x] İlk 3 içeriğin çekim notu hazır (`icerik_ilk3.md`) — hook, gövde,
      kapanış ve her rakam depodan **sayılarak**. 11 numaralı fikrin hook'u
      büyütüldü: *"Ankara'daki bütün kafeleri listeledim"* 35.852 mekan
      varken kendini küçültmekti.
- [x] **8 haftalık takvim hazır** (`icerik_takvim.md`) — Faz A "günde 1
      içerik, 40+" satırının karşılığı. 40 ayrı senaryo değil bir **düzen**:
      yedi tekrarlanabilir format, Pzt–Cum sabit ritim, altı susma kuralı ve
      haftalık ölçüm. Takvimin en önemli sayısı 35.852 değil **62** —
      81 ilin 62'sinde tek bir menü fiyatı yok, o yüzden fiyat gösteren
      çekimler İstanbul/Kocaeli/Antalya/İzmir/Eskişehir'de yapılıyor ve
      "her yerde fiyat var" cümlesi kurulmuyor
- [ ] Çekim ve yayın *(telefon senin)*

### Ürün — TAMAMLANDI (tarayıcıda doğrulandı)
- [x] 81 il çekimi — **36.102 ham kayıt** (eğlence dahil), hiçbir il eksik
      değil. Tekilleştirmeden sonra uygulamada **35.852 mekan** (aynı il +
      aynı ad + ≤25 m kuralıyla 250 kayıt birleşti, aşağıda)
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
`iletisim@cebimde.app` yer tutucusu gerçek adresle değişmeli (3 dosya).

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
- [x] `profil.sql`, `yorum.sql`, `menu_katki.sql`, `mekan_foto.sql`, `akran.sql`
      çalıştırıldı (2026-08-25)
- [x] `sayac.sql` (bütçe bandı sütunu için tekrar), `fiyat_oyu.sql`,
      `topluluk.sql` çalıştırıldı (2026-08-26) — **veritabanı tarafı bitti**
- [ ] `@cebimde` handle (Instagram + TikTok) — **bio ve ilk 3 içeriğin notu
      hazır** (`icerik_ilk3.md`); kalan tek şey hesabı açmak
- [x] Vercel yayını — **hepsi canlıda** (2026-08-26). Önce PR #1 markayı
      taşıdı, sonra 11 commit daha birleştirildi: kategoriler, çok bütçeli
      öneri, seviye adları, son doğrulanma, kampanya alanı, kalem tarihi,
      konum haritası, semt (ilçe + mahalle). Depoda `main` ile
      `claude/repo-incelemesi-wlnrwo` arasında fark yok
- [ ] `python kutuphane_al.py` — supabase-js'i yerele al (1 dk, `KURULUM.md`)
- [x] `python foto_cek.py` — GitHub koşucusunda koştu (`veri.yml`, `foto: true`).
      **241 serbest lisanslı fotoğraf / 61 il.** Kalan tek adım insanda:
      `foto_ekle.sql`'i Supabase SQL Editor'e yapıştırmak — betik
      veritabanına kendi yazamıyor, bunun için `service_role` gerekirdi
      ve o anahtar bu depoya asla girmiyor
- [ ] **`DUMAN_TESTI.md`** — 30 maddelik elle test, telefonda, gerçek
      Supabase'e karşı. Otomatik kontroller Supabase'i taklit ediyor;
      RLS, moderasyon, depolama ve e-posta bir kez bile gerçek koşulmadı
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

**Üründe — ağ mekanikleri (fiş katmanı commit'inde sayılmıştı):**
- [x] Bütçe akranları — keşfet ekranında bütçe girilince şerit:
      *"37 kişi son 6 ayda 12 mekanda kişi başı 300 ₺ altında ödedi."*
      Sayım sunucuda (`akran.sql → butce_akranlari`), çünkü **"kaç kişi" ile
      "kaç fiş" ayrı şeyler** ve fark özelliğin bütün anlamı — üç fişi olan
      tek kişi bir akran topluluğu değil. Tarayıcı bunu ayırt edemiyor:
      `kullanici` sütunu ona kapalı. Sıfır çıkarsa şerit davete dönüyor.
      Yanına `Fişi olan` süzgeci kondu; ölçütü rozet ve panelle **aynı**.
- [x] Bayat fiyat hatırlatması — veri artık tarih taşıyor, uyarı ekranda
- [x] Mahalle statüsü — işletme sayfasında **Bu civar** kutusu: 500 m'de kaç
      mekan, hangi türler, kaçının fiyatı biliniyor, civarın fiş medyanı.
      Katkı çağrısı soyut değil sayıyla: *"bu civardaki 55 mekanın fiyatı
      bilinmiyor"*.

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
      **Kod tarafı bitti**: 112 Kadıköy kartı üretilmeye hazır, basılması
      için "hazır" denmesi bekleniyor.

**Fazların durumu (2026-08-26):**

| Faz | Ne | Durum |
|---|---|---|
| 0 | Şirket kararı — *gelir doğana kadar kurulmayacak* | Karar, kod değil. Yürürlükte; md.14'ü kapatan sebep bu |
| 1 | Eksik bilgi katkı hattı | ✅ kod + SQL + onay + takip |
| 2 | Yürüyüş kümeleri | ✅ `sahiplen.py` → `sahiplenme_kume.csv` |
| 3 | Saha kartları | ✅ kod; **kart basılmadı** (sende) |
| 4 | Sahiplenme kodu ve doğrulama | ✅ gerçek Postgres 16'da 11 davranış kontrolü |

Yani **kod tarafında açık faz kalmadı.** Faz 3'ün açık ayağı fiziksel:
kartın basılıp mekana bırakılması ve `saha.py olc` ile ölçülmesi.

**Yayın yapılandırması:**
- [x] `vercel.json` yalnızca çıktı klasörünü söylüyordu, hiç güvenlik başlığı
      yoktu. Eklendi: `X-Content-Type-Options`, `Referrer-Policy`,
      `X-Frame-Options`, `Permissions-Policy` + veri/varlık/HTML için ayrı
      önbellek kuralları. `test.py` dosyanın geçerli JSON olduğunu ve
      başlıkların durduğunu denetliyor — geçersiz JSON'da Vercel
      yapılandırmayı **sessizce yok sayar**, yani başlık kaybı hiçbir yerde
      patlamaz.
- [x] **CSP kondu** (`csp_uret.py` → `vercel.json`). Eskiden bilerek yoktu;
      gerekçe "Supabase adresi kuruluma göre değişiyor" idi. Çözüm joker:
      `https://*.supabase.co`, yani depodaki başlık hiçbir kuruluma bağlı
      değil. `script-src`'de **`'unsafe-inline'` yok** — 30 satır içi
      `<script>` bloğu sha256 karmasıyla geçiyor (12 tekil karma; blokların
      çoğu tema önyükleyicisi ve sayfalar arasında ortak). Satır içi olay
      işleyici sıfır olduğu için bu mümkündü — ölçüldü.
      `style-src`'de `'unsafe-inline'` **kaldı** ve kalmalı: kartlara satır
      içi `style="--uzak:0.42"` yazılıyor, stil özniteliği karmayla geçmiyor.

      **Eskimesi sessiz olurdu:** bir `<script>` içinde tek boşluk değişince
      karma tutmaz, tarayıcı o bloğu çalıştırmaz ve sayfa *hatasız görünür*.
      İki kapı kondu, ikisi de sabote edilip denendi:
      `csp_uret.py kontrol` (dosya güncel mi) ve `sunucu.py` artık
      `vercel.json`'daki başlıkları **yerelde de gönderiyor** — yani
      `test_sayfa.py`'nin 14 sayfası gerçek CSP altında açılıyor ve konsol
      ihlalleri toplanıyor. Engellenen script hata fırlatmadığı için bu
      ikincisi şarttı.

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
- [x] Görünür veri çöpü, dördü de kullanıcıya **aynen** gösteriliyordu:
      59 menü adında çözülmemiş HTML varlığı (`6&#8217;lı Macaron` —
      WooCommerce böyle döndürüyor ve `menu_topla.py` çözmüyordu),
      120 şemasız web adresi (`www.narli.cafe` göreli bağlantı sanılıp
      kırılıyordu — `isletme.html` düzeltiyor, `kesfet.js` düzeltmiyordu),
      12 baş/son boşluklu ad, 3 telefon alanına yazılmış telefon olmayan
      şey (`"Köfteci Yusuf"` — üstelik `sahiplen.py` onu "telefonu var"
      sayıp arama listesine koyuyordu).
- [x] Mutfak etiketi Türkçe bir sitede ham OSM İngilizcesiyle duruyordu
      (`burger;coffee_shop;savory_pancakes`) ve **iki sayfada iki türlü**:
      keşfet virgülle ayırıyordu, işletme sayfası hiç dokunmuyordu.
      Kural `ortak.js`'e alındı; 80 etiketlik sözlük **etiketlerin %93,9'unu,
      mekanların %94,0'ını** karşılıyor. Sözlükte olmayan uydurulmuyor —
      alt çizgisi boşluğa çevrilip olduğu gibi yazılıyor.
- [x] **Arama Türkçe harfe duyarlıydı.** Kullanıcıların çoğu Türkçe harfsiz
      yazıyor; ölçüldü (İstanbul): "köfte" 574 mekan buluyordu ama "kofte"
      33, "çiğ" 343 ama "cig" 12, "şişli" 4 ama "sisli" 1. Yani harfsiz
      yazan kullanıcı sonuçların **%94'ünü** hiç görmüyordu. Hem sorgu hem
      aranan metin aynı sadeleştirmeden geçiyor; sonuç ayrıca **arttı**
      (574 → 607), çünkü OSM'de harfsiz yazılmış mekanlar da geliyor.
- [x] Instagram toplanıyor ama uygulamaya hiç ulaşmıyordu: **192 mekanın**
      instagramı var ve sitesi yok, onlara hem sayfada hem saha kartında
      "sosyal medya bağınız yok" diyorduk.
- [x] **`?donus=` denetimsizdi — açık yönlendirme ve `javascript:` XSS.**
      `giris.html` bu parametreyi doğrudan `location.href`'e yazıyordu. Gerçek
      Chromium'da ölçüldü: `donus=javascript:…` **çalışıyor** — hem de tam giriş
      yapıldıktan sonra, yani oturum jetonu okunabilir haldeyken.
      `donus=https://taklit.site` ise kullanıcıyı gerçek sitede giriş yaptırıp
      taklit siteye düşürüyor; adres çubuğunda doğru alan adını gördüğü için
      ikna edici bir kimlik avı zinciri. Kural artık tek yerde
      (`ortak.js` → `guvenliDonus`): yalnız **aynı kökende, uygulamanın kendi
      klasöründe bir `.html`**. Üreten yerlerin hepsi zaten öyle yazıyordu,
      yani doğru kullanımın hiçbiri kesilmedi.
- [x] **Tarih UTC'den alınıyordu.** `toISOString()` UTC verir; Türkiye kalıcı
      UTC+3, yani her gece **00:00–03:00 arası** (günün %12,5'i) hâlâ dünü
      gösteriyordu. `paylas.html` hem varsayılan tarihi hem de `<input max>`
      değerini oradan alıyordu: gece 1'de form dünün tarihiyle açılıyor ve
      **bugünü seçtirmiyordu** — tam da dışarı çıkıp fiş paylaşan insanın saati.
- [x] **supabase-js CDN'den gelmeyince katkı formu yine de açılıyordu.**
      `Kimlik.acik` yalnız yapılandırmanın dolu olduğunu söylüyor, istemcinin
      kurulduğunu değil. Kullanıcı formu dolduruyor, "Giriş yap ve ekle"
      diyor ve **ölü** bir giriş sayfasına fırlatılıyordu. Formun kendi
      yorumundaki kural buydu zaten: *çalışmayan bir kutu göstermek, hiç
      göstermemekten kötü* — Leaflet'te aynı şey olmuştu.
- [x] **`kullanici` kimliği herkese açıktı — en ağırı.** RLS **satır**
      düzeyinde çalışır, sütun düzeyinde değil. "Onaylanmış paylaşımlar
      herkese açık" politikası satırı açıyordu ve satırın içinde `kullanici`
      uuid'si de vardı. Gerçek Postgres'te ölçüldü: herkese açık `anon`
      anahtarıyla `select kullanici, mekan_ad, tarih, tutar, kisi from
      paylasimlar` çalışıyor; aynı uuid `katkilar` ve `sahiplik`
      tablolarında da göründüğü için izler birleştirilebiliyordu. Yani tek
      bir kimlikle **bir kişinin nereye, hangi gün, kaç kişiyle gittiği ve
      ne ödediği** çıkarılabiliyordu. Kimlik değil ama *sabit* bir
      tanımlayıcıya bağlı dışarı çıkma geçmişi — `gizlilik.html`'deki veri
      enazlama sözünü ve `kimlik.js`'teki "sahibin kimliği döndürülmüyor"
      yorumunu birden bozuyordu. **İstemcinin select listesine güvenmek
      koruma değil**: anahtarı olan herkes kendi sorgusunu yazar.

      Düzeltme sütun yetkisi (`revoke select ... grant select (…)`) üç
      tabloda birden. Ölçüldü: politikalar sütun yetkisi olmadan da
      çalışıyor. "Kaç kişinin fişi" sayımı sunucuya taşındı
      (`mekan_fis_ozeti`, `security definer`) — sızıntının sebebi zaten
      o sayımdı. Gösterilen sayı **değişmiyor**: 12 veri kümesinde SQL
      medyanı ile eski JS formülü birebir aynı sonucu verdi.
- [x] **Bağlantı sorununda kullanıcıya *geliştirici talimatı* gösteriliyordu.**
      `supabase-js` CDN'den geliyor ve gelmeyebiliyor (kurumsal ağ, okul ağı,
      ülke çapında engel — Leaflet'te tam olarak bu olmuştu). İki farklı sebep
      tek bir `false`'a düşüyordu, `giris.html` de ikisine birden *"Giriş
      sistemi henüz kurulu değil — `app/yapilandirma.js` dosyasını doldur"*
      diyordu. Yayındaki sitede bu **yanlış**: sistem kurulu ve kullanıcı o
      dosyaya erişemiyor bile. Artık `Kimlik.sorun` ikisini ayırıyor ve ağ
      durumunda "Giriş şu an açılamıyor · Tekrar dene" çıkıyor.
      Aynı geçişte ölçüldü: CDN **askıda** kalırsa sayfa **süresiz** boş
      kalıyordu. 12 saniyelik sınır kondu (konum bekçisiyle aynı süre);
      ölçüldü, 12,1 sn'de doğru mesajla açılıyor.
- [x] **Keşfet ekranının `h1`'i hiç yoktu.** Sitenin indekslenen ana ekranında
      başlık sıralaması doğrudan kart `h3`'lerine atlıyordu; ekran okuyucu
      kullanıcısı başlıklarla gezerken sayfanın ne olduğunu söyleyen tek bir
      başlık bulamıyordu. Görsel olarak yer kaplamayan ama seçili şehirle
      güncellenen bir `h1` kondu (sabit metin, şehir değişince yalan olurdu).
      Artık her sayfada **tam bir** görünür `h1` olduğu denetleniyor.
- [x] **Bütçe kaydırıcısı telefonda 22 piksel yüksekti** — WCAG 2.5.8'in
      24×24 asgarisinin bile altında. Kutusu 44 px olduğu için gözle fark
      edilmiyordu ama parmağın ortadaki dar bandı tutturması gerekiyordu.
      Çizgi ve topuz aynı kaldı, büyüyen tek şey dokunma alanı
      (ekran görüntüsüyle karşılaştırıldı).
- [x] **Sahipliği bırakmak kaydı siliyordu.** Yönetici iptali kaydı
      *koruyor* — dosyanın kendi gerekçesi: "kimin neyi ne zaman
      sahiplendiği ve neden geri alındığı kaybolmasın". Ama kullanıcının
      kendi bırakması satırı **siliyordu**. Aynı gerekçe ikisinde de
      geçerli ve önemi somut: sahibin katkısı **incelenmeden** onaylanıyor
      (`sahip_katkisi_onayli` tetikleyicisi). Silme kalsaydı biri mekanı
      sahiplenip incelenmemiş bilgi yazar, sonra bırakır ve o mekanın
      sahibi *olduğuna* dair hiçbir kayıt kalmazdı. Artık üçüncü bir durum
      var (`birakildi`) ve ekranda "bıraktın" / "iptal edildi" ayrı
      yazıyor — biri kullanıcının kararı, öteki yöneticinin.
      İşlem sunucuya alındı (`sahipligi_birak`): bir `UPDATE` politikası
      `with check` ile yalnız **son hali** denetler, hangi sütunun
      değiştiğini denetlemez; kullanıcı aynı istekte `mekan_id`'yi de
      değiştirip tutmak istediğimiz kaydı bozabilirdi.
- [x] **Giriş yapılmış halin hiçbir sayfası tarayıcıda hiç çalışmamış.**
      `test_sayfa.py` bütün dış bağlantıları kesiyor (bilerek); yan etkisi,
      supabase-js'in hiç gelmemesi ve kimlik katmanının hiç kurulmamasıydı.
      `hesabim.html`'in dört sekmesi, `yonetim.html`'in onay düğmeleri,
      `isletme.html`'in fiş ve sayaç katmanları yalnızca elle açılarak
      görülmüştü. Artık yerel bir taklit modülle (`test_sahte_supabase.js`)
      altı ekran çizilerek ölçülüyor. Yetki **taklit edilmiyor**: RLS'in
      doğruluğu gerçek Postgres'te sınanıyor.
- [x] **Sayacın doğru saydığını hiçbir şey doğrulamıyordu.** `sayac.sql`'in
      kendi kontrolü yetkilere bakıyor, sayıya değil — oysa işletmeye
      satılan cümle "sayfanı bu ay 47 kişi gördü" ve dosyanın kendi başlığı
      "şişirilebilir bir sayaç yanlış fiyattan kötüdür" diyor. 11 davranış
      kontrolü eklendi; ikisi doğrudan `gizlilik.html`'deki **sözleri**
      ölçüyor (günler arası izin bağlanamaması, tuzun özete karışması).
- [x] **SQL davranış kontrolleri fiilen hiç koşmuyormuş.**
      `sahiplenme_test.sql` yazıldığı gün elle çalıştırılmış, sonra bir daha
      çalışmamış. Bu arada `supabase_taklit.sql`'de eksik bir `grant` yüzünden
      dosya 6. adımda patlıyordu: **11 kontrolün altısı** hiç koşmuyordu.
      Daha kötüsü 2. adım ("kullanıcı sahiplik tablosuna doğrudan yazamaz")
      **yanlış sebepten** geçiyordu — engel politika değil, eksik yetkiydi.
      Ayrıca dört adım yalnız satır basıyordu, yani betikten koşturulunca
      hiçbir şey doğrulamıyordu. Hepsi iddiaya çevrildi, 15'e çıkarıldı ve
      `veritabani/kos.sh` ile `test.py`'ye ve CI'a bağlandı.
- [x] **Etkinlik bağlantıları üçüncü taraf RSS'ten geliyor ve şeması hiç
      denetlenmiyordu.** `kacir()` bunu yapmaz — tırnağı kaçırır, şemaya
      bakmaz — yani akışın verdiği `javascript:…` ana sayfada **tıklanabilir**
      bir bağlantı olurdu. Bugün 774 bağlantının 774'ü `https:`, yani görünür
      bir değişiklik yok; denetim hiç yoktu. Kural iki yerde birden:
      `ortak.js → guvenliBag` (gösterim) ve `etkinlik_cek.py → guvenli_bag`
      (dosyaya hiç girmesin). İkisinin ayrışmasını `test.py` denetliyor.
      Aynı geçişte veride **iki gerçek yazım hatası** çıktı
      (`htttps://selfiepark.com.tr`, `htpps://lunapark…`): eskiden bunların
      başına bir `https://` daha ekleniyor ve hiçbir yere gitmeyen bir
      *bağlantı* çıkıyordu. Artık metin duruyor, bağlantı kurulmuyor —
      kullanıcı adresi okuyup kendisi düzeltebiliyor.
- [x] **Görünmeyen sahne için 60 fps kare üretiliyordu.** Kaydırınca gözlemci
      animasyonu durduruyordu ama `visibilitychange` koşulsuz `baslat()`
      çağırıyordu: başka sekmeye geçip dönünce, sahne hâlâ ekran dışındayken
      animasyon tam hızda yeniden başlıyor ve bir daha durmuyordu (gözlemci
      ancak kesişim *değişince* tetikleniyor). Ölçüldü: kaydırdıktan sonra
      600 ms'de 0 kare, sekmeden dönünce aynı koşulda **36 kare**. Telefonda
      bu doğrudan pil. Ayrıca her fare hareketinde köke yazılan `--iz-hiz`
      özel özelliğini **hiçbir CSS kuralı okumuyordu**; kaldırıldı.

**Kodda kalan teknik borç:**
- [x] Leaflet SRI ile geliyor (özet npm tarball'ından, resmî değerlerle doğrulandı)
- [x] **supabase-js yerele alınabiliyor** (`kutuphane_al.py`). Eski gerekçe
      —"yerele almak derleme adımı ister"— o gün doğruydu: esm.sh'in normal
      çıktısı başka esm.sh adreslerinden parça ithal ediyor. Ama `?bundle`
      seçeneği hepsini **tek dosyada** birleştiriyor; paket yöneticisi de
      toplayıcı da gerekmiyor, tek bir indirme.

      İki sorunu birden kapatıyor. (1) SRI: dinamik `import()` integrity
      desteklemiyor, yani bugün esm.sh ne gönderirse doğrulanmadan çalışıyor;
      aynı kaynaktan gelen dosyada bu soru yok. (2) **CDN tek arıza noktası** —
      varsayım değil, bu depoda yaşandı: Leaflet gelmeyince keşfet ekranının
      tamamı ölüyordu. Aynısı supabase-js'e olursa giriş, favori, paylaşım,
      yorum ve fotoğraf hep birden kapanır.

      `kimlik.js` artık **tek adres** biliyor: `app/lib/supabase-js.js`. O dosya
      şu an CDN'e yönlendiren bir yer tutucu; betik gerçeğini üzerine yazıyor.
      Yedek mantığı bilerek yok — "önce yereli dene, olmazsa CDN" hali her
      yüklemede bir 404 üretir ve daha kötüsü, yerel dosya **bozukken** sessizce
      CDN'e düşerdi; yani SRI'nin çözdüğü sorunu geri getirirdi.

      İndirilen şey körü körüne yazılmıyor: boyut, HTML olmama, `createClient`
      ve **içinde dış ithalat kalmamış olması** doğrulanmadan dosya yazılmıyor.
      `csp_uret.py` de duruma bakıyor — yer tutucu durdukça `esm.sh` CSP'de
      kalmak zorunda, gerçeği indirilince CSP kendiliğinden daralıyor. İkisinin
      ayrışması `test.py`'de hata.
- [x] `isletme.html`'in mükerrer Supabase istemcileri kaldırıldı (`Kimlik.istemci()`)
- [x] Koordinatlar 5 basamağa indi — İstanbul 414 → 400 KB gzip
- [x] **İstanbul dosyası 1.733 → 1.325 KB ham, 396 → 322 KB gzip** (`veri_bicim.py`).
      Ağırlığın bir kısmı veri değil **tekrar**dı: 12.095 nesnenin her biri
      `id`/`ad`/`tur`/`lat`/`lon` anahtarlarını yeniden yazıyordu — ölçüldü,
      yalnız anahtar adları 451 KB, yani ham dosyanın **%25'i**. Yeni biçim
      yoğun alanları **sütun**, seyrek alanları **indeksli sözlük** yapıyor.
      Hepsini sütuna koymak dosyayı BÜYÜTÜYORDU (ölçüldü: 2.000 KB) çünkü
      sütunlar `null` ile doluyordu. 81 ilin toplamı 4.583 → 3.363 KB (**−%27**).

      Ham boyutun da düşmesi ayrıca önemli: gzip indirmeyi, ham boyut
      `JSON.parse` süresini belirliyor — sadece gzip'i iyileştiren bir biçim
      telefonda indirmeyi kısaltıp ayrıştırmayı uzatırdı.

      **Gerçek çözüm hâlâ coğrafi bölmeleme** ve bu onun yerine geçmiyor:
      bölmeleme kullanıcının *baktığı* bölgeyi indirir, bu biçim bütün ili
      indirmeye devam ediyor. Farkı maliyeti: bölmeleme veri düzenini ve iki
      tüketiciyi değiştiriyor, bu değişiklik tek bir çözücü fonksiyona
      bakıyor ve çözülen nesne eskisiyle **birebir aynı** — kanıt, 81 ilin
      hepsinde koşan kodla/çöz turu.
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

## 2026-08-24 — Profil, yorumlar ve sosyal medya

**Giriş sistemi zaten vardı** (Supabase auth, `giris.html` + `hesabim.html`);
eklenen şey profilin kendisi.

**Profil.** `profiller` tablosuna altı alan: kullanıcı adı, doğum yılı, meslek,
kendini anlatan kısa metin, fotoğraf, herkese açıklık. Yeni sayfa
`profil.html?k=kullanici_adi`.

Üç karar, üçü de kasıtlı:

- **Hepsi isteğe bağlı.** Yaşını yazmayan biri yorum yazamasın demek, veriyi
  zorla toplamak olurdu.
- **Doğum yılı saklanıyor, yaş değil.** Yaş her yıl eskir ve güncel kalması
  için tekrar tekrar sorulması gerekir; doğum yılı eskimez ve gün-ay
  içermediği için daha azını söyler. Ekranda yaşa çevriliyor.
- **Profil uuid ile değil KULLANICI ADIYLA açılıyor.** Bu üslup tercihi değil:
  `sema.sql`'in "Sütun yetkisi" bölümü `kullanici` sütununu üç tabloda birden
  kapattı, çünkü o uuid ile bir kişinin dışarı çıkma geçmişi
  birleştirilebiliyordu. Profili uuid ile açılabilir yapmak, kapatılan kapıyı
  yandan geri açardı. `profiller` tablosu dışarıya **kapalı kalıyor**; herkese
  açık okuma tek bir `security definer` fonksiyondan geçiyor.

**Yorumlar.** Puan (zorunlu) + metin (isteğe bağlı), ön onaylı.
**Fiyattan ayrı tutuluyor:** fiş bir *ölçüm* taşıyor (850 ₺, 3 kişi), yorum bir
*kanı*. Yorumun puanı fiyat hesabına **girmiyor**. Onay şartının sebebi de
katkılardakiyle aynı değil — orada mesele yanlış bilgi, burada hakaret ve
karalama; tek kişilik bir yapıda bunun tek savunması ön onaydır.

Ortalama ancak **3 yorumdan sonra** gösteriliyor, fiş eşiğiyle aynı kural:
tek yorum bir eğilim değil, o günkü bir kanıdır.

Profilini kapatan kullanıcının **yorumu görünür, adı görünmez** — yorum mekana
ait bir bilgi, kişiye ait olan şey ad ve fotoğraf.

**Fişler profilde listelenmiyor** ve listelenmeyecek. Onlar kanı değil ödeme
kaydı: hangi gün, hangi mekanda, ne kadar, kaç kişiyle. Kişiye göre dizilince
dışarı çıkma ve harcama geçmişi olur. Kişiye göre fiş listeleyen bir
fonksiyonun *eklenmediği* SQL testinde denetleniyor.

**Sosyal medya.** Instagram'a Facebook, X, TikTok ve YouTube eklendi. OSM'de
her platform iki biçimde yazılıyor (`contact:instagram` ve düz `instagram`);
ikisi de okunuyor. Adres kurma kuralı tek yerde (`ortak.js → sosyalBag`) ve
şeması denetleniyor — `kacir()` şemaya bakmaz ve değer kullanıcı katkısından
da gelebiliyor.

Mevcut CSV'de yeni sütunlar yok, yani **veri çıktısı değişmedi**; boru hattı
eski veriyle de çalışıyor ve yeni çekimde alanlar kendiliğinden doluyor.
`turkiye_cek.py`'nin hiç kontrolü yoktu — eklendi (Instagram tam olarak bu
boşlukta kaybolmuştu).

**Ölçülen hatalar (kendi yazdığım kodda, kontroller yakaladı):**

- `guvenliBag("//baska.site/x")` şemasız sanılıp başına `https://` ekleniyordu;
  çıkan `https:////baska.site/x` tarayıcıda `https://baska.site/x` olarak
  çözülür. Yani ekranda **"Instagram" yazan** bir bağlantı tamamen başka bir
  siteye giderdi.
- `yildiz(null)` beş boş yıldız basıyordu: `Number(null)` sıfırdır ve
  sonludur, yalnız `isFinite`'a bakan hâl puansız mekanı puanlı gösterirdi.
- `hesabim.html` hiç açılmıyordu: profil kaydetme düğmesi adı da kapsayınca
  eski "Adı kaydet" düğmesi kalktı ama dinleyicisi kaldı.
- Yorumlardaki yıldızlar soluk çiziliyordu — `.y-ust span` özgüllükte
  `.yildiz`'i yeniyordu.
- `profil.html` kimlik katmanı gelmezken **hiç başlık göstermiyordu**.

**KVKK.** `gizlilik.html` güncellendi — eski metin *"yaş… istenmiyor"* diyordu
ve artık yanlıştı. Profil, yorum ve fotoğraf için ayrı başlıklar eklendi;
profil sayfaları `noindex, noarchive`.

---

## 2026-08-24 — Menü ve ürün paylaşımı (fotoğraflı)

Fiyat paylaşımının kardeşi. Neden gerekli: menü fiyatları işletmelerin
**kendi sitelerinden** derleniyor ve 35.852 mekanın **30.393'ünde (%84,8)**
ne site ne sosyal medya var. O menüye uzaktan ulaşmanın yolu yok — ama
menüyü gören biri var: o an orada oturan kullanıcı.

**Üç tablo, üç ayrı soru, ayrı kalıyorlar:**

| tablo | ne taşıyor |
|---|---|
| `paylasimlar` | "3 kişi gittik, 850 verdik" — **hesap** |
| `menu_katkilari` | "Latte 95 ₺" — **liste fiyatı** |
| `yorumlar` | "sessiz, bahçesi güzel" — **kanı** |

**Gösterilen ortalamaya girmiyor** — şimdilik ve bilerek. O hesap
`fiyat_analiz.py`'de, Python'da yapılıyor (kategori ayrımı, ana ürün oranı,
alt sınırlar). Aynı kuralı tarayıcıda ikinci kez yazmak, iki dilde iki doğru
tutmak ve ikisinin ayrışmasını beklemek olurdu — bu depodaki en pahalı
hatalar tam olarak öyle çıktı. Kullanıcı kalemleri ayrı bir bölümde,
"işletmenin kendi menüsünden ayrı" etiketiyle duruyor.

**Ürün + fiyat ya da yalnız fotoğraf.** Menünün tamamını fotoğraflayan biri
20 kalemi elle yazmak zorunda kalmasın. Adı olup fiyatı olmayan kalem
reddediliyor — bir şey söylemiyor.

### EXIF: fotoğrafın taşıdığı ve taşımaması gereken şey

Telefon fotoğrafı **GPS koordinatı, çekim saati ve cihaz modeli** taşır.
Bu projede ham IP bile saklanmıyor — günlük yenilenen bir özete çevriliyor.
Kullanıcının bulunduğu yerin koordinatını bir menü fotoğrafının içinde
yayımlamak o özenle çelişirdi.

Dosya olduğu gibi yüklenmiyor: tarayıcıda tuvale çizilip yeniden
kodlanıyor. Üç şey birden oluyor — EXIF tamamen düşüyor, resim küçülüyor
(uzun kenar 1600 px), biçim tekleşiyor (JPEG).

**Sunucu bunu doğrulayamıyor.** Supabase Storage dosyayı ayrıştırmıyor, ne
verirsen onu saklar. Yani kural yalnızca istemcide ve tek bekçisi test:
`test_sayfa.py` **gerçek bir EXIF bloğu** (GPS + cihaz dizgisi) takılmış bir
JPEG üretip önce girdinin gerçekten EXIF taşıdığını doğruluyor, sonra
işlenmiş dosyada kalmadığını. "EXIF yok" diye bakmak, hiç EXIF'i olmayan bir
dosyayla da geçerdi.

`createImageBitmap`'e `imageOrientation: "from-image"` veriliyor — verilmezse
dik çekilmiş fotoğraflar **yan** yüklenirdi; EXIF silmenin bilinen yan
etkisi tam olarak budur.

### Ölçülen ve düzeltilen

- **Yayımlanan kalemde yazar bilgisi yok** ve bu bilerek: yorumda "kim
  söylüyor" bilgi taşır (19 yaşındaki öğrenci ile 45 yaşındaki mühendis aynı
  yeri farklı bulur), fiyatta taşımaz — 95 ₺, kim yazdıysa 95 ₺.
- Fotoğraf kovasında **güncelleme politikası yok**: onaylanmış bir fotoğrafın
  üzerine yazılabilseydi, onaydan geçen resim ile yayındaki resim ayrı şeyler
  olabilirdi.
- `hesabim.html`'de katkı listesi `#bolum-katkilar`'a `innerHTML` yazıyordu ve
  menü listesini siliyordu; `test.py` sekme/bölüm değişmezi de araya soktuğum
  iç kabı yakaladı.
- Kırık fotoğraf (silinmiş dosya, ağ kesik) alt metniyle taşıyordu. Tek yerde
  çözüldü — `error` olayı balonlamaz, yakalama evresinde dinleniyor.
- **İki testim boşa çalışıyormuş.** `information_schema.columns`'a fonksiyon
  girmiyor, yani "çıkış sütununda yazar/fiş alanı var mı" sorgusu her zaman
  sıfır dönüyordu. Sabotaj yakaladı; `pg_proc.proargnames`'e geçirildi ve
  ikisine de "kontrol gerçekten bir şey görüyor mu" adımı eklendi.

---

## 2026-08-25 — Mekan fotoğrafları

İstenen şey "Google Maps ve web'den fotoğraf ve yorum çek"ti. **Google Maps
kısmı yapılmadı ve yapılmayacak** — teknik zorluk değil, hak meselesi:
oradaki fotoğraflar ve yorumlar yazarlarının telifinde ve platforma
lisanslı; Places API'nin kendi şartları bile yorumu 30 günden fazla
saklamayı ve harita dışında göstermeyi yasaklıyor. Zaten aşağıdaki
**Yapılmayacaklar** listesinde duran bir karar.

Yerine, **yayımlama hakkı olan** üç kaynak kuruldu:

| kaynak | nasıl | onay |
|---|---|---|
| doğrulanmış işletme sahibi | mekan sayfasından yükler | **doğrudan yayında** |
| kullanıcı | mekan sayfasından yükler | kuyrukta bekler |
| Wikimedia Commons | `foto_cek.py` → `mekan_foto.sql` | atıflı, doğrudan |

`kaynak` sütunu **serbest metin değil**, kısıtlı bir liste — yayımlama
hakkı olmayan bir kaynak sessizce eklenemesin diye. Ve `'commons'`
**istemciden yazılamıyor**: yazılabilseydi kullanıcı kendi fotoğrafını
"Commons'tan geldi" diye işaretleyip atıf alanlarını uydurabilirdi.

**Atıf silinemez.** CC BY ve CC BY-SA yazar adını ve lisansı göstermeyi
zorunlu kılıyor. İki kapı da kapalı: veritabanı kısıtı atıfsız Commons
satırını kabul etmiyor, gösterim tarafı da atıfsız satırı **hiç
çizmiyor**.

**Menü fotoğrafından ayrı tablo**, çünkü onay ölçütü farklı: menü
fotoğrafında aranan şey okunabilirlik, mekan fotoğrafında **içinde
tanınabilir insan olmaması**. Bir kafenin salonunu çeken kullanıcı orada
oturanları da çeker; onlar fotoğraflanmayı kabul etmedi.

`foto_cek.py` kapsamı **sayarak** yazıyor, tahmin etmiyor. Beklenti düşük:
Commons'ta anıt ve müze bol, mahalle kafesi yok denecek kadar az.

**Sayıldı (26–27 Ağustos, GitHub koşucusu):** 35.852 mekanın 413'ünde
fotoğraf etiketi var, **241'i serbest lisanslı (%0,67)** — ve bu sayı
**61 ilin**, çünkü **20 il 429/504 ile düştü**. Overpass'a tek adrese
tek istek atılıyordu ve iller arası bekleme 0,34 sn'di; o sayı
Wikimedia'nın hız sınırı, Overpass'ın değil. Artık üç ayna sırayla
deneniyor ve bekleme/deneme sayısı `turkiye_cek.py`'den geliyor —
ikinci bir kopya yok. Ayrıntı: `VERI_VE_GELIR.md` §3b.

### Ölçülen ve düzeltilen

- **İç içe `<a>`.** Lisans bağlantısını fotoğraf bağlantısının içine
  koymuştum; HTML iç içe bağı kabul etmiyor ve tarayıcı yapıyı bölüyor —
  3 kutu yerine 4 çıktı, atıf bloğu dışarı taştı. Bağ artık yalnız resmi
  sarıyor, atıf kardeş.
- **`CC BY-NC 4.0` serbest sayılıyordu.** Lisans kalıbım öneki eşleştirip
  `-NC`'yi (ticari kullanım yasak) görmüyordu. Kalıbı akıllandırmak yerine
  **önce reddet, sonra izin ver**e geçtim: yasaklı işaretler (NC, ND) ayrı
  ve önce eleniyor. Bir lisansı yanlışlıkla serbest saymanın bedeli
  hukuki, yanlışlıkla elemenin bedeli bir eksik fotoğraf.
- **`innerText` CSS'in `text-transform`'unu uyguluyor.** Rozet kaynakta
  küçük harfle yazılı ama ekranda `İŞLETMEDEN`; test kaynağa göre yazılmıştı
  ve düşüyordu. (Noktalı İ gelmesi ayrıca `lang="tr"`nin doğru çalıştığını
  gösteriyor.)
- **Atıfsız fotoğraf kontrolüm sabotajda kaçtı**: fotoğrafın adresi `src`
  özniteliğinde duruyor ve `inner_text`'te hiç geçmiyor, yani metne bakan
  kontrol hiçbir şey görmüyordu. DOM'a bakan bir kontrole çevrildi.
- İki kova için iki ayrı yükleme fonksiyonu vardı; **tek kurala** indirildi.
  Ayrı kalsalardı birinde EXIF adımının unutulması an meselesiydi — ve o
  adımın tek bekçisi istemci.

---

## 2026-08-25 — foto_cek.py artık `ham/` istemiyor

İlk sürüm `turkiye_cek.py`'nin ürettiği dev dökümü okuyordu — 81 il için
**saatler** süren, depoda durmayan bir dosya. Oysa aranan şey menünün
tamamı değil, **üç etiketten birini taşıyan** mekanlar; Overpass'a onu
soran sorgu 12 satır ve saniyeler sürüyor. `ham/` varsa yine oradan
okunuyor (ağa hiç çıkmadan).

Seçiciler `turkiye_cek.py` ve `eglence_cek.py`'den **import ediliyor**,
kopyalanmıyor: üç yerde üç ayrı liste, birinin güncellenip ötekilerin
unutulması demekti.

Betik yalnız **uygulamada gerçekten olan** mekanlara yazıyor — 35.852
kimlik `app/veri/` içinden okunuyor. Overpass aynı seçiciyle başka gün
çekilmiş mekanlar da döndürebiliyor; onlara satır yazmak hiçbir sayfada
görünmeyecek kayıtlar biriktirmek olurdu.

**Ölçülen hata:** ağ hatası "0 fotoğraf var" diye **ölçüm gibi**
raporlanıyordu ve dosya yazılıyordu. Kullanıcı o %0,00'a bakıp kaynağı
elerdi. Artık hiçbir il çekilemezse dosya yazılmıyor, hata veriliyor
(çıkış kodu 1); kısmi koşumda da kaç ilin çekilemediği uyarı olarak
yazılıyor — eksik bir sayıya tam sayı gibi bakmak aynı hataya götürür.

### Google Maps / Yandex — istendi, yapılmadı

Fotoğrafların oradan çekilmesi istendi. Yapılmadı: o fotoğraflar onları
yükleyen kişilerin telifinde ve platforma lisanslı, alt-lisanslanamıyor.
Kendi sitede yayımlamak ToS meselesi değil, doğrudan telif ihlali — ve
aşağıdaki listede *"sermayesiz yapıda işi bitirir"* diye yazılı olan risk
tam olarak bu.

Yerine duran üç kaynak: **doğrulanmış işletme sahibi** (en temiz — hak
kendisinde), **kullanıcı**, **Wikimedia Commons** (atıflı). Kafeler için
sayfaları dolduracak olan ilk ikisi; Commons bir ek, ana kaynak değil.

---

## 2026-08-25 — Ağ mekanikleri: bütçe akranları ve civar

Fiş katmanı tek bir mekanın sorusunu cevaplıyordu ("burası kaça oturur").
Kalan iki mekanik bir üst soruyu soruyor: **"benim bütçemdeki insanlar
nereye gidiyor"** ve **"buranın etrafında ne var"**.

### Önce bulunan hata: eşik keşfet ekranında hiç yoktu

`FIS_ESIK = 3` yalnız `isletme.html`'de tanımlıydı ve keşfet ekranı ondan
habersizdi. Sonuç, **tek bir kişinin tek fişinin** mekanın fiyatı diye
yayımlanmasıydı:

- kart rozeti: `kişi başı ~240 ₺`
- detay paneli: `Gerçekten ödenen 240 ₺ · 1 kişinin paylaşımından`

İkincisi durumu açıkça yazıyordu bile. Eşiğin iki gerekçesi de çiğneniyordu:
tek fiş bir kişinin o günkü seçimidir, mekanın fiyatı değil; ve tek fiş,
tanıdığı biri tarafından kişiye bağlanabilir (k-anonimlik). Yani işletme
sayfasının gizlediği şeyi keşfet ekranı yayımlıyordu.

Kural `ortak.js`'e alındı (`FIS_ESIK`, `fisOzeti`, `fisGoster`) ve üç yerde
—kart rozeti, detay paneli, `Fişi olan` süzgeci— aynı fonksiyona soruluyor.
`test.py` artık `FIS_ESIK`'in ikinci bir tanımını **hata sayıyor**.

### Bütçe akranları

Sayım sunucuda (`akran.sql → butce_akranlari`) çünkü *"kaç kişi"* ile
*"kaç fiş"* farkı bu özelliğin bütün anlamı: üç fişi olan tek kişi bir
akran topluluğu değil. Tarayıcı ayırt edemiyor — `kullanici` sütunu ona
kapalı (`sema.sql`). Pencere 180 gün; ekranda "son 6 ayda" yazıyor ve
`test.py` ikisinin ayrışmasını denetliyor.

### Mahalle statüsü → "Bu civar"

**Mahalle adı yok, çünkü veride yok.** Ölçüldü: 35.852 mekanın 9.397'sinde
adres alanı var ama içinde ayrıştırılabilir mahalle adı geçen **49 tane
(%0,14)**. Dışarıdan bir coğrafi çözücüyle uydurmak bu depoda kapalı bir
kapı. Yerine ölçülebilir bir şey kondu: yarıçap.

**Neden 500 m** — ölçüldü, 500 m'deki komşu sayısı medyanı: Ankara 13,
İstanbul 40, İzmir 19, Aksaray 4. Hiç komşusu olmayan mekan oranı sırasıyla
%4, %1, %8, %20.

**"Çevresine göre pahalı" DEMİYORUZ, çünkü diyemeyiz.** Menü fiyatı bilinen
mekan 35.852'de **291 (%0,82)**; 500 m içinde en az üç fiyatlı komşusu olan
mekan yalnız **%4,16**. Üç örnekten çıkan bir medyana dayanıp fiyat iddiası
kurmak, uydurma seviyeden farksız olurdu. Gösterilen şey **kapsam**: kaç
mekan var, kaçının fiyatı biliniyor — ve katkı çağrısı tam oraya düşüyor.
Fiş medyanı ağ büyüdükçe kutunun içinde kendiliğinden beliriyor.

**Coğrafya istemcide, toplam sunucuda:** `paylasimlar` tablosunda koordinat
yok, `mekan_id` var; koordinatlar uygulamanın statik JSON'unda. Bu yüzden
"hangi mekanlar yakın" kararını tarayıcı, "o mekanlarda kaç fiş / kaç kişi"
toplamını sunucu veriyor (`civar_fis_ozeti`). Koordinatı veritabanına
kopyalamak aynı gerçeği iki yerde tutmak olurdu.

**Liste kırpılmıyor, yarıçap daralıyor.** Sunucu 500'den uzun mekan
listesini reddediyor (sessizce kırpmıyor — kırpsaydı ekranda yazan
"500 m çevresi" yalan olurdu). İstanbul'un yoğun caddelerinde 500 m'de 600
mekan olabiliyor; orada yarıçap 100'er metre daralıyor ve **daraltılmış
yarıçap ekranda yazıyor**.

### Ölçülen ve doğrulanan

- SQL: **11 yeni davranış kontrolü** gerçek Postgres 16'da (toplam 86).
  Altı sabotaj denendi, altısı da yakalandı. Biri **ilk yazımda kaçtı**:
  `civar_fis_ozeti`'nin onay süzgecini hiçbir adım sınamıyordu, yani
  kuyrukta bekleyen — hiç okunmamış — bir fiş civar medyanına girebilirdi.
  Test düzeltildi (7. adıma onaysız bir mekan konuldu).
- `ortak.js` öz kontrolü **148 → 177**. Altı sabotaj, altısı yakalandı.
- Tarayıcı: eşik **iki yönlü** sınanıyor — 2 fişte rozet/kutu çıkmamalı,
  3 fişte çıkmalı. Yalnız birine bakmak, özelliği tamamen silen bir
  değişiklikten de geçerdi.
- Civar kutusu gerçek bir İstanbul mekanıyla sınanıyor
  (`node/5284691026`, 500 m'de 56 mekan); sayı **veriden** geliyor, sabit
  bir metin aranmıyor.
- Kendi testimde bir hata: "Gerçekten ödenen" metnini arıyordum ama
  `.odenen-bas span` üzerinde `text-transform:uppercase` var ve
  `inner_text` onu uyguluyor — kutu tam ekrandayken bile eşleşmiyordu.
  Kontrol DOM'a bağlandı. (Aynı tuzak galeri atıfında da yaşanmıştı.)

---

## 2026-08-25 — Mobil ve Google Play (TWA)

### Mobil düzen: ölçüldü, sorun çıkmadı

Varsayımla başlamamak için önce ölçtüm — üç ekran boyutu (320×568,
360×800, 412×915), 10 sayfa: **yatay kaydırma yok, 12 px altı yazı yok**.
Düzen zaten duyarlıydı; dokunma hedefi kuralı ve `env(safe-area-inset-*)`
de yerindeydi. Yani "mobil uyumlu hale getir" işinin büyük kısmı çoktan
yapılmıştı ve yeniden yapmak yalnız risk olurdu.

Ölçüm iki gerçek kusur buldu; ikisi de düzeltildi:

**1. Android geri tuşu keşfet ekranından çıkarıyordu.** Detay paneli
açıkken geri basınca panel kapanmıyor, adres `index.html` oluyordu.
Tarayıcıda can sıkıcı; **uygulamada çok daha kötü** — TWA'da başlangıç
adresinde geri basmak *uygulamadan çıkmak* demek, yani bir mekana bakıp
geri basan kullanıcının uygulaması kapanıyordu. Panel açılırken geçmişe
bir kayıt konuyor, geri basışı orada yakalanıyor. Filtreler bilerek
`replaceState` kullanmaya devam ediyor (40 filtreyi tek tek geri almak
istemiyoruz); panel ayrı, çünkü kullanıcının zihninde ayrı bir ekran.
Üç hal de sınanıyor: geri panel kapatmalı, X ile kapatınca **artık kayıt
kalmamalı**, tekrar tekrar aç-kapa geçmişi şişirmemeli.

**2. Katkı formunun `select`'i 23 px'ti** (bir önceki commit'te). WCAG
2.5.8 en az 24 istiyor.

### PWA: manifest, ikon, service worker

Üçü de yoktu. `manifest.webmanifest`, 4 ikon (`ikon_uret.py` — şekil ve
renkler sayfaların kendi SVG'sinden ve `stil.css`'ten, iki yerde iki türlü
olmasın diye), `sw.js` ve `cevrimdisi.html`.

**Service worker sürümü elle yazılmıyor** (`sw_uret.py`), kabuk
dosyalarının içeriğinden türetiliyor. Gerekçe CSP karmalarındakiyle aynı:
elle tutulan bir sürüm ilk düzenlemede eskir ve **eskimesi sessizdir** —
kullanıcılar aylarca eski sürümü kullanır, hiçbir yerde patlamaz.

Önbellek kararları ürünün kuralına bağlı: **gezinme ve il verisi önce
ağdan** geliyor, çünkü bu uygulama fiyat gösteriyor ve eski bir sayfayı
sessizce vermek "bayat fiyat" kuralının çiğnenmesi olurdu. Onbellek yalnız
yedek. Supabase istekleri ve harita döşemesi hiç saklanmıyor; ilki
oturuma bağlı ve kişisel.

Ölçülen çevrimdışı davranış:

| Durum | Sonuç |
|---|---|
| Hiç açılmamış sayfa | `cevrimdisi.html` — tarayıcı hata ekranı değil |
| `start_url` (ilk kurulum, uçak modu) | Açılıyor — `sw.js` onu ön yüklüyor |
| Gezilmiş keşfet ekranı | **120 kartla** açılıyor, veri önbellekten |

Üçüncüsü asıl kanıt: sayfanın açılması yetmez, kart sayısı sıfırsa il
dosyası önbellekten gelmemiş demektir.

**Bir kusur kendi kodumdaydı:** `navigationPreload` yanıtı doğrudan
dönüyordu, yani gezinme yanıtları **hiç önbelleğe girmiyordu** — kullanıcı
bir sayfayı açıp sonra çevrimdışı kalınca, *zaten açmış olduğu* sayfa bile
"bağlantı yok" ekranına düşüyordu. Ölçülüp düzeltildi.

### Google Play

`PLAY.md`: TWA yolu, Bubblewrap komutları, imzalama anahtarı (`.gitignore`
`*.jks`/`*.keystore` kapatıyor), mağaza girişi ve **veri güvenliği formu**
— sonuncusu koddan okunarak dolduruldu, tahminle değil. Kritik satır:
**konum toplanmıyor** ("yakınımdakiler" cihazda çalışıyor, koordinat
hiçbir yere gitmiyor) ve **ham IP saklanmıyor** (günlük değişen tuzla
özete çevriliyor).

`assetlinks_uret.py` parmak izini doğruluyor: kısa, uzun, onaltılık
olmayan ya da yapıştırılmış bir cümle **yazılmıyor**. Doğrulama tutmazsa
uygulamanın üstünde adres çubuğu çıkıyor ve **bunun hiçbir yerde hatası
görünmüyor** — TWA'da en sık yaşanan sorun bu.

Paket adı iki dosyada (`twa-manifest.json`, `assetlinks_uret.py`) ve
`test.py` ayrışmalarını hata sayıyor: ayrışırsa doğrulama sessizce tutmaz.

**iOS yapılmadı, bilerek.** Apple yalnız web sitesini saran uygulamaları
4.2 "minimum işlevsellik" kuralıyla reddediyor. Manifest ve
`apple-touch-icon` duruyor; iOS kullanıcısının yolu "Ana Ekrana Ekle".

### Test

`test.py` 26 → **30 kontrol grubu**. Tarayıcı tarafında service worker
**ayrı bir bağlamda** sınanıyor: kayıtlı bir sw, öteki kontrollere
önbellekten yanıt verip diskteki dosya yerine eski kopyayı sınatabilirdi.

Sekiz sabotaj denendi, sekizi de yakalandı. **Biri ilk yazımda kaçtı:**
çevrimdışı kontrolü yalnız sayfa başlığına bakıyordu ve `sw.js` içindeki
çıplak son çare yanıtının başlığı da aynı — yani ön yükleme tamamen
bozulsa bile test geçiyordu. Ayırt edici konuldu ("Tekrar dene" düğmesi).

---

## 2026-08-25 — İşletme sahibi için ayrı giriş ve panel

`isletme-giris.html` (ayrı kapı) ve `isletmem.html` (panel).

### Ayrı parola sistemi YAPILMADI, bilerek

İstenen "ayrı bir login" idi. Ayrı bir **sayfa** yapıldı, ayrı bir
**kimlik deposu** yapılmadı. Gerekçe:

Sahiplik, hangi formdan girdiğinle değil **elden verilen fiziksel kodla**
kanıtlanıyor (`sahiplenme.sql`). Sahip hesabı olup kodu olmayan hiçbir şeye
sahip değil; müşteri hesabı olup kodu olan mekanın sahibi. Yani hesap türü
yetkiyi taşımıyor — kod taşıyor. İkinci bir kimlik deposu (ikinci parola,
ikinci sıfırlama akışı, ikinci oturum) kimin neyi yapabildiği konusunda
**hiçbir şeyi değiştirmez**, yalnız saldırı yüzeyini büyütürdü. Üstelik
bir kişi hem müşteri hem işletme sahibi olabiliyor.

Değişen şey **kapı ve iş masası**: sahibin sorduğu soru müşteriden
bambaşka — "sayfamı kaç kişi gördü, neyim eksik, telefonu nasıl
düzeltirim". İkisini tek ekranda toplamak ikisine de yarım cevap vermekti.

### Yeni SQL yazılmadı

Veri katmanı zaten hazırdı: `sahipliklerim`, `mekan_sayaci`, `katkiGonder`
(sahibin katkısı `sahip_katkisi_onayli` tetikleyicisiyle sıraya girmeden
yayına çıkıyor), `mekan_puani`, `mekan_fis_ozeti`. Güvenlik de kanıtlı —
`sahiplenme_test.sql` 8. adımı: *"sahibi olmadığı mekana ONAYLI katkı
yazamaz."* Panel bunun üstünde duruyor ve yalnız arayüzü sürüyor.
`kimlik.js`'e tek ekleme oldu: `mekanSayaci`, çünkü `isletme.html` o RPC'yi
doğrudan çağırıyordu ve iki yerde iki çağrı alan adlarının ayrışması
demekti.

**`mekan_goruldu` panelde çağrılmıyor** ve bu bir tercih: o fonksiyon
sayacı **artırıyor**. Sahibin kendi panelini açması, kendi sayfasının
görüntülenmesini şişirmemeli — "sayfanı 47 kişi gördü" cümlesinin bütün
değeri doğru olmasında.

### Panelde ne var

Mekan başına: görüntülenme (son 30 gün · bugün), yorum ortalaması, fiş
medyanı, eksik bilgi listesi, dört alanı düzeltme formu, sayfaya bağlantı
ve sahipliği bırakma. Altta kodla ikinci bir işletme ekleme.

Eşikler **gevşetilmedi**: fiş medyanı yine `fisGoster()`'e, yorum
ortalaması `YORUM_ESIK`'e soruyor. Sahibi olman k-anonimlik eşiğini
kaldırmıyor — fişi yazan kişi senin müşterin. Sıfır da gösterilmiyor:
"0 kişi baktı" hem cesaret kırıcı hem de "sayaç çalışmıyor" ile ayırt
edilemez.

Doğrulama `ortak.js`'ten (`katkiSorunu`, `KATKI_ALAN`): işletme sayfası,
yönetim ekranı ve panel aynı kuralı kullanıyor. Alan listesi
**türetiliyor**, kopyalanmıyor.

### Kart → hesap → mekan, tek akışta

Kod alanı giriş formunun **içinde**. "Önce üye ol, sonra mekanı bul, sonra
kodu gir" üç adım demekti ve saha kartının dönüşünü tam orada
kaybederdik. E-posta doğrulaması açıkken oturum hemen açılmıyor — o halde
kod kullanılamıyor ve kullanıcıya bu **söyleniyor**, yoksa "kodu girdim
ama olmadı" diye geri döner.

### hesabim.html kısaldı

"İşletmelerim" sekmesi aynı listeyi ikinci kez çiziyordu. Artık bir sayı
ve bir kapı veriyor; liste ve bırakma düğmesi panelde. *Aynı kural tek
yerde dursun* — bu depoda iki yerde tutulan bir kuralın ayrışması daha
önce yaşandı.

### Ölçüm

`test_sayfa.py` 14 → **16 sayfa**, 15 → **16 girişli ekran**. İki yeni
sayfa mobil dokunma hedefi ölçümüne de girdi — orada taklit modül servis
edildiği için panel **gerçekten çiziliyor**; kütüphanesiz bir ölçümde
panel giriş sayfasına yönlenir ve form hiç ölçülmezdi.

Üç sabotaj denendi, üçü de yakalandı. Kendi testimde yine aynı tuzağa
düştüm: beklenti olarak `isletmem.html` yazmıştım ama o bir `href`,
`inner_text`'te geçmiyor — görünen metne çevrildi. (Galeri atfında ve
"gerçekten ödenen" kutusunda da aynısı olmuştu.)

---

## 2026-08-25 — Marka değişti: Oturalım → Cebimde

Ad, renk, logo, yazı tipi ve slogan marka kılavuzuna göre değişti.
**Cebindeki bütçeyle keşfet.**

### Ölçüm bir marka kararını değiştirdi

Kılavuzun ekran maketlerinde turuncu düğmenin üstünde **beyaz** yazı var.
Ölçtüm: `#FF7A00` üzerinde beyaz **2,61:1** — WCAG'in 4,5 eşiğinin çok
altında. Düğme yazısı okunmayacaktı.

**Rengi değiştirmedim, mürekkebi değiştirdim:** düğme tam marka
turuncusu kalıyor, üstündeki yazı koyu (`#1A0E00`, **7,26:1**). Marka
bozulmadı, okunurluk da bozulmadı.

Bu ayrım iki token gerektirdi:

| Token | Ne | Temaya göre |
|---|---|---|
| `--marka` | Düğme zemini, logo, grafik | **Sabit** `#FF7A00` |
| `--vurgu` | **Metin** rengi | Koyuda `#FF7A00`, açıkta `#C2410C` |

Ayrım keyfi değil: kodda `--vurgu` **44 yerde `color`**, yalnız 8 yerde
`background`. Yani asıl işi metin rengi olmak ve beyaz zeminde ham
turuncu 2,61:1. Sekiz `background` kullanımı `--marka`'ya çevrildi;
çevirmeseydim açık temada düğme yazısı 3,66:1'e düşerdi.

`test.py` artık paleti **stil.css'ten okuyup hesaplıyor** (31. kontrol
grubu): her rengin zemin üzerindeki kontrastı, düğme yazısının marka
zemininde kontrastı, `--marka`'nın iki temada aynı olması, iki açık tema
bloğunun ayrışmaması ve eski paletten kalan sabit renk olmaması. Beş
sabotaj denendi, beşi de yakalandı.

### Yazı tipi: Montserrat Rounded **yok**

Kılavuz "Montserrat Rounded" diyor. **O kesim Google Fonts'ta yok** —
ticari/özel bir kesim. En yakın gerçek eşleşme Montserrat'ın kendisi:
aynı harf iskeleti, yuvarlatılmamış uçlar. Rounded kesimini satın alırsan
yerele koyup tek satır değiştiriyorsun; o zaman `fonts.googleapis.com`
CSP'den de düşebilir.

**Yazı tipi değişimi iki gerçek kusur ortaya çıkardı** — Montserrat,
önceki Karla/Fraunces çiftinden belirgin geniş:

1. **320 px'te başlık taşıyordu.** Ölçüldü (hakkinda.html): marka 106 +
   Keşfet 56 + Hakkında 77 + tema 44 = **335 px**, ekran 320. 620 px
   kırılımı yetmez oldu; 380 px altı için ayrı kırılım kondu ve
   "Hakkında" düşüyor — "Ana sayfa" gibi, ikisi de **alt bilgide** duruyor.
2. **Uzun Türkçe kelime satıra sığmıyordu.** Tek bir `h2` 288 px'lik kaba
   308 px istiyor ve sayfayı 14 px kaydırıyordu. `overflow-wrap:break-word`
   kondu — yalnız kelime başka türlü sığmıyorsa devreye giriyor.

İkisi de eski markayla **yoktu**; ölçüm olmasa ikisi de yayına çıkardı.

### Logo tek dosyada

Önceki ikon üretici şekli Pillow ile **elde çiziyordu**, yani marka iki
yerde tanımlıydı: sayfaların favicon'ında ve betikte. Artık iki SVG var
ve PNG'ler onlardan türetiliyor (Chromium ile):

- `app/marka.svg` — logo işareti (turuncu iğne, cüzdandan çıkan kartlar)
- `app/marka-ikon.svg` — uygulama ikonu (turuncu zemin, **beyaz** iğne)

İkisi ayrı çünkü işleri ayrı: Android ve iOS ikonu kendi zeminini
istiyor; logoyu saydam zeminle vermek ana ekranda renksiz bir leke
bırakırdı. Sayfalar da artık satır içi kopya değil `marka.svg`'yi
kullanıyor.

### Değişmeyen: "oturulur"

Blanket bir `otur → ceb` değiştirmesi **yapılmadı**. "oturum",
"kaça oturulur", "oturuyor" markadan bağımsız Türkçe ve **97 yerde**
geçiyor. Hedefli değiştirme listesi kullanıldı.

Bir kalıntı bu yüzden kaçtı ve ayrıca bulundu: `gizlilik.html`'de e-posta
konusu **URL-kodluydu** (`Otural%C4%B1m`), düz arama görmedi.

### Kendi testimi kırdım

EXIF sınaması sabit bir base64 bloğu kullanıyordu ve **cihaz adı onun
içine gömülüydü**. Marka değişince beklenti güncellendi, base64
güncellenemedi — ikili bir sabitin içindeki metni hiçbir arama görmüyor.
Kontrol "girdi dosyasında EXIF yok" diye patladı. Sabit yerine **üretici**
kondu; isim artık tek yerde.

### Yapılmadı, bilerek

Kılavuzdaki **bütçe girişli ana ekran** ("Bugün cebimde: ₺300 →
kategori → Yakınımda Bul") bu turda yapılmadı; ürün değişikliği, marka
değişikliği değil. Ana sayfanın alt metni bugünkü davranışı anlatıyor:
bütçe keşfet ekranında yazılıyor. Tutulmayan bir söz vermektense eksik
söylemek.

---

## 2026-08-25 — Bütçe girişli ana ekran

Marka yol haritasındaki ilk madde: **"Bugün cebimde: ₺300 → kategori →
Yakınımda Bul."** Ana ekran o hâle getirildi.

### Önce ölçüm: bütçe süzgeç olarak çalışmıyor

Ekranı yazmadan önce bütçenin listeyi ne kadar değiştirdiğini saydım. 3 km
yarıçaplı gerçek semt çemberlerinde:

| Semt | Mekan | ₺300 ile elenen | Oran |
|---|---|---|---|
| Kadıköy | 1.096 | 36 | %3,3 |
| Beyoğlu | 2.203 | 81 | %3,7 |
| Kızılay | 599 | 16 | %2,7 |
| Alsancak | 483 | 18 | %3,7 |
| Muratpaşa | 469 | 24 | %5,1 |

₺150 ile ₺700 arasındaki fark bile küçük: Kadıköy'de 37'ye karşı 28 mekan.
Sebebi tek cümlede duruyor — **35.852 mekanın 163'ünde (%0,45) ölçülmüş
menü fiyatı var.** Kalanın 17.013'ü tür/mutfak etiketinden tahmin
edilebiliyor, 18.676'sı (%52) hakkında hiçbir sinyal yok.

Not: belgelerdeki eski **291** rakamı "menüsü toplanan mekan" sayısı.
`yemekFiyati()` bunların bir kısmını **göstermiyor** — tek kaleme dayanan,
bir yıldan eski ya da tema demosu olan menüler eleniyor. Gerçekten
gösterilebilen sayı **163**. Ana sayfadaki satır bu farkı artık söylüyor.

### O yüzden bütçe süzgeç değil, sınıflandırıcı

Bütçeyi süzgeç gibi gösteren bir ekran — "₺300 ile 12 mekan" — kullanıcıya
o 12'sinin **ölçüldüğünü** düşündürürdü. Bu depodaki kural açık: *yanlış
fiyat, fiyat olmamasından kötüdür.* Aynısı vaat için de geçerli.

`butceDurumu()` her mekana beş cevaptan birini veriyor ve hangisinin
**ölçüm**, hangisinin **tahmin** olduğu cevabın içinde:

| Sınıf | Ne demek | Kesin mi |
|---|---|---|
| `girer` | ölçülmüş fiyat, bütçenin altında | evet |
| `asiyor` | ölçülmüş fiyat, bütçenin üstünde | evet |
| `muhtemel` | ölçüm yok, türü/mutfağı hesaplı gösteriyor | hayır |
| `zor` | ölçüm yok, türü/mutfağı üst segment diyor | hayır |
| `bilinmiyor` | hiçbir sinyal yok | iddia yok |

Karşılaştırmanın kendisi yeniden yazılmadı: kesin taraf `bant()`'tan,
tahmin `seviye()`'den geliyor. **Keşfet ekranı da aynı kapıdan geçiyor** —
bütçe üstü eleme orada ayrı yazılmıştı ve birini değiştiren ötekini
sessizce ayrıştırabilirdi.

Eleme yalnız `asiyor` için. Tahmine dayanarak hiçbir mekan düşmüyor:
**pahalı sanmak ile pahalı bilmek ayrı şeyler.**

### Ekrandaki en önemli cümle

```
2 mekanın menü fiyatı ölçüldü, 1 tanesi 300 ₺ altında.
Kalan 439 mekan için 300 ₺ yeter mi bilmiyorum; türünden tahmin ediyorum.
```

Gerçek çıktı (Kadıköy, ₺300, Kafe). Bu satır olmadan üç kart, arkasında
ölçülmüş fiyat varmış gibi okunur.

Dökümün **süzülmemiş** listeden alınması şart. Önce üç aday seçip sonra
saymak, %0,45'lik ölçümü üçte bir gibi gösterirdi — test.py bunu ayrı bir
hata olarak arıyor.

Ölçüm hiç yoksa cümle rakam vermiyor, davete dönüyor: *"Buradaki hiçbir
mekanın menü fiyatı ölçülmedi. ₺300 yeter mi, söyleyemem — fiyatı gidenler
yazıyor."* Fiş eşiğiyle aynı desen.

### Bütçe akranları ana ekrana geldi

Menü fiyatı yavaş büyüyor; **fiş katmanı kullanıcıdan geliyor.** Yani
bütçeye verilebilecek tek *büyüyen* cevap o. `butce_akranlari()` artık ana
ekranda da çağrılıyor — sayım sunucuda, çünkü "kaç kişi" ile "kaç fiş" ayrı
şeyler ve tarayıcı `kullanici` sütununu göremiyor (sema.sql).

### Kategori çipleri: bütçenin aksine gerçek bir süzgeç

`tur` her mekanda var (%100 kapsama). Çipler mekan sayısına göre seçildi:
Restoran 14.587, Kafe 10.815, Fast food 6.091, Bar+Pub 1.443, Dondurma 395,
eğlence grubu 2.521.

**"Tatlı" diye bir çip yok:** verideki tür "Dondurma" ve 395 tane. Çipe
"Tatlı" deyip dondurmacı listelemek olmayan bir kapsamı vaat etmek olurdu.

Kullanıcı türü kendi seçtiyse "aynı türden üç tane önerme" çeşitlendirmesi
**kapanıyor** — "Kafe" diyene iki restoran vermek onu yoksaymak olurdu.

### Bulunan ve düzeltilen kusurlar

- **Bütçe çipleri birincil yolda hiç yoktu.** Çipler yalnız *yedek* formun
  içindeydi ve o form ancak konum reddedilince açılıyor. Yani konumuna izin
  veren kullanıcıya bütçe **hiç sorulmuyordu** ve öneri sıralaması bütçeden
  habersiz çalışıyordu. Marka yol haritasının maddesi aslında bir hata
  raporuymuş.
- **`_yorumsuz()` JS'te yanlış çalışıyor.** test.py'nin yorum ayıklayıcısı
  Python için yazılmış: `#`'ten sonrasını atıyor. `el("#butce-ozet")` satırı
  ikiye bölünüyordu ve satırın geri kalanı kontrole hiç görünmüyordu. Ters
  yönü daha tehlikeli: JS yorumlarını hiç atmadığı için **silinmiş bir
  çağrı, onu anlatan yorum cümlesi sayesinde "var" sayılıyordu.** Bu depoda
  yorumlar uzun — tuzağın en büyük olduğu yer. `_js_yorumsuz()` yazıldı;
  dize, şablon dizesi ve düzenli ifade tanıyor.
  - İlk sürümü işaretlemeyi de JS gibi tarıyordu ve `</div>` içindeki `/`
    bir düzenli ifade başı sanılıp arkasındaki HTML yorumu yutuluyordu.
  - İkinci sürümü dosya türünü *"`<script` geçiyor mu"* diye anlıyordu;
    ortak.js kendi açıklamasında o kelimeyi kullanıyor, dosya HTML sanıldı
    ve **bütün ortak.js yorumları kontrole görünür kaldı.** Ayrım artık
    `<!doctype` ile.
- **320 px hiç ölçülmüyordu.** Tarayıcı takımının mobil denetimi yalnız
  390 px'te koşuyordu; marka değişiminde üst şeridin 335 px'e taştığı elle
  bakınca görülmüştü — yani kontrol değil şans yakaladı. Denetim artık
  320 ve 390 px'te koşuyor ve **yatay taşmayı** da ölçüyor (taşıran öğeyi
  adıyla söylüyor).
- **Ölü CSS.** `.sayilar` ve `.kahraman-izgara` kuralları hiçbir işaretleme
  tarafından kullanılmıyordu; silindi.

### Yapılmadı, bilerek

- **Fiyat güven skoru (🟢/🟡/🔴) yok.** Üç renkli bir rozet, arkasında
  ölçüm olmayan mekanlara da bir renk vermek demek. Bugünkü veri iki renk
  taşıyor: ölçüldü / ölçülmedi. Fiş sayısı büyüdüğünde tekrar bakılmalı.
- **Kombinler yok.** "₺300 ile kahve + tatlı" demek iki fiyatı toplamak
  demek ve bugün tek fiyat bile 163 mekanda var.
- **Bütçe hâlâ sunucuya gitmiyor.** Yalnız `localStorage`; akran sorgusu
  bir *tavan* gönderiyor, kişiyi değil.

## 2026-08-25 — Fiyat kaç ölçümden geliyor? (163 mekan = 53 işletme)

Yol haritasındaki **fiyat güven skoru** için önce hangi sinyallerin
gerçekten değiştiğine bakıldı. İki aday da çöktü, üçüncüsü ürünü
değiştirdi.

### Yaş ekseni boş, kalem ekseni yanıltıcı

**Yaş:** menüsü olan **264 mekanın 264'ü de 0-2 aylık.** Yaşa dayalı bir
skor bugün herkesi yeşile boyar ve hiçbir şey söylemez.

**Kalem sayısı:** dağılım 2-4 → 19, 5-14 → 24, 15+ → 120 görünüyordu ve
"15+ kalemden çıkan ortalama sağlamdır" demek mantıklıydı. Ama o 120
mekan yalnız **17 farklı ad** taşıyor.

### Asıl ölçüm

| | |
|---|---|
| Menü fiyatı gösterilebilen mekan | **163** |
| Bu 163 mekan kaç işletme | **53** |
| Domino's şubesi | **94** (%58) |
| Papa John's | **10** |
| Aynı ilde çok şubeli mekan | **113** (%69) |
| Bu 113'ün kaçında şubeler farklı fiyatlı | **0** |

Yani menü **bir kez** kazınmış ve **56 ayrı ölçümmüş gibi**
gösteriliyordu. Bu, tek fişi mekanın fiyatı saymakla aynı hata — depoda
o hata `FIS_ESIK` ile kapatılmıştı ("tek fiş bir kişinin o günkü
seçimidir, mekanın fiyatı değil"). Aynı gerekçe burada da geçerli.

Gerçekten **ayrışan** tek eksen buydu: fiyat bu mekanın kendi menüsünden
mi geliyor (**50 mekan, %31**) yoksa şubelerle paylaşılan bir zincir
menüsünden mi (**113 mekan, %69**).

### Ne yapıldı

Rakam **kaldırılmadı** — rakam gerçek. Neye dayandığı yazıldı:

- **Kartta** rakamın kendisi işaretleniyor (`~243 ₺ zincir`) — rozet
  değil, "eski" işaretiyle aynı gerekçe: kartta zaten üç rozet var ve
  dördüncüsü asıl bilgiyi boğar.
- **Detay panelinde ve mekan sayfasında** tam cümle: *"Bu fiyat, aynı
  ilde 3 şubesi listelenen bir zincirin menüsünden geliyor — tek bir
  menüden. Şubeler farklı fiyatlandırma yapabiliyor, o yüzden bu rakam
  şubeye özel değil."*
- **Ana sayfada** kalibrasyon satırı: *"o 291 mekan 93 işletme."*

Ölçüldü: İstanbul'da "fiyatı olan" süzgeci **102 kart** veriyor ve
bunların **76'sı (%75)** zincir menüsünden.

"Kendi menüsünden" halinde **susuluyor**: her mekan sayfasına "bu fiyat
kendi menüsünden" yazmak, hiçbir şey söylemeyen bir satırı 35.852 kez
basmak olurdu. Satır yalnız kullanıcının bilmediğinde yanılacağı hâlde
çıkıyor.

### Ad eşleştirmesinde `sade()` kullanılmadı

`kesfet.js`'teki `sade()` arama için yazıldı ve Türkçe harfleri de
düşürüyor (`Çınar` → `cinar`). Arama için doğru, burada tehlikeli: iki
**ayrı** işletmeyi aynı zincir sayıp birinin fiyatına "12 şubede aynı"
yazdırabilir. Burada az eşleştirmek çok eşleştirmekten iyi.

Anahtarda **fiyat da var**: aynı adı taşıyan ama ayrı ayrı kazınmış
(dolayısıyla farklı fiyatlı) iki yer, iki ayrı ölçümdür.

### Yol boyunca: `vitrin_uret.py` çoktan kırılmıştı

İşletme sayısını üretmek için `vitrin_uret.py` çalıştırıldığında betik
`KeyError: 'iller'` ile durdu — **benim değişikliğimden önce de.** Sebep:
`index.json` bir il dosyası değil ama `veri_bicim.coz()`'den geçiriliyordu
ve `coz()` tanımadığı biçimi **sessizce boş bir il** olarak döndürüyordu.

Yani `vitrin.json` bir süredir üretilemiyordu ve bunu hiçbir şey
söylemiyordu — üstelik `test.py` hata verdiğinde "`vitrin_uret.py`
çalıştır" diye yol gösteriyor, yani çöken bir komuta yönlendiriyordu.

`coz()` artık tanımadığı biçimde **hata veriyor** (`kodla()` zaten
bilinmeyen alanda hata veriyordu; ikisi simetrik oldu). `coz()`'ü çağıran
diğer dört betik zaten dosya adını rakamla süzüyor, etkilenmiyorlar.

### Doğrulama

`ortak.js` öz kontrolleri **229 → 243**; `test.py`'ye "fiyat kaç ölçümden
geldiğini söylüyor" grubu eklendi. Altı sabotajın altısı da yakalandı —
aralarında "zincir haritası kart başına kuruluyor" (2.300 kartlık listede
2.300 kez ili taramak) ve "anahtardan fiyat çıktı" (ayrı kazımalar
birleşir) var.

Sabotaj koşumu ilk yazımda **kendi hatası yüzünden hiç ölçmemişti**: aynı
süreçte `importlib.reload` ile denendiğinde stdlib'in kendi `test` paketi
araya girdi ve kontrol çalışmadan `AttributeError` verdi. Her tur artık
ayrı bir süreçte koşuyor.

## 2026-08-25 — Fiyat güven skoru ve bütçeye göre renklenen harita

Yol haritasının iki maddesi. Skor **daha önce yazılamıyordu**: fiyat yaşı
bütün menülerde aynı (264 menünün 264'ü de 0-2 aylık), kalem sayısı da
yanıltıcıydı. Zincir ölçümü üçüncü ekseni verdi ve skor gerçek oldu.

### Bantlar (35.852 mekan sayıldı)

| Renk | Ne demek | Mekan |
|---|---|---|
| 🟢 **yeşil** | mekanın kendi menüsünden, taze — **ya da üç fişten doğrulanmış** | **50** (%0,14) |
| 🟡 **sarı** | zincir menüsünden geliyor ya da fiyat eskimiş | **113** (%0,32) |
| 🔴 **kırmızı** | ölçülmüş fiyat yok | **35.689** (%99,55) |

Kırmızının bu kadar geniş olması skorun kusuru değil, **verinin durumu** —
ve skorun işi tam olarak bunu söylemek. İçi de boş değil: 17.013'ünde
tür/mutfak tahmini var, 18.676'sında hiçbir sinyal yok. İkisi ayrı
gerekçeyle anlatılıyor ama aynı renk: hiçbiri ölçüm değil.

Ölçüldü (İstanbul, "fiyatı olan" süzgeci, 102 kart): **26 yeşil, 76 sarı.**

### Fiş yeşile çıkarıyor — skorun büyüme yolu

Üç ayrı fiş gelmiş bir mekan, menüsü hiç olmasa da **yeşil**. Ürünün tezi
bu: fiyatı işletme değil giden insan yazıyor. Eşik `FIS_ESIK` ile aynı
(k-anonimlik) — tek fiş bir kişinin o günkü seçimidir.

Yani bugün 50 olan yeşil sayısı sahadan gelen fişlerle **büyüyor**. Skor
donmuş bir etiket değil, katkının ölçüsü.

Mekan sayfasında rozet **iki kez** çiziliyor: önce fişsiz (sayfa hemen
dolsun), sonra fiş özeti ağdan gelince yeniden. Tek çizimde bıraksak
fişle doğrulanmış bir mekan kırmızı kalırdı.

### Renk tek başına bilgi taşımıyor

Her noktanın yanında ya görünür metin ya `aria-label` var, `title` de
gerekçeyi yazıyor. Renk körü bir kullanıcı da, ekran okuyucu da aynı şeyi
öğreniyor.

Kart listesinde nokta **kısa** halde (yalnız renk + aria-label): liste
2.300 karta çıkıyor ve her karta "fiyat yok" yazmak listeyi aynı cümleyle
doldururdu. Panelde, mekan sayfasında ve ana ekran önerisinde tam hâli.

Renkler **markanın kendi paletinden**: Okyanus `#00BFA6`, Gün Batımı
`#FFB74D`, Mercan `#FF5A5F`. Yeni renk uydurulmadı.

### Harita bütçeye göre renkleniyor

Nokta rengi `butceDurumu()`'ndan geliyor — kart rozeti, süzgeç ve ana
ekranla **aynı kapı**. Ayrı bir ölçüt kullansaydı aynı mekan listede
"bütçene giriyor", haritada başka renk olurdu.

- renk = hangi bant (giriyor / bütçe üstü / hesaplı görünüyor / bilinmiyor)
- doygunluk ve yarıçap = **ne kadar eminiz** (ölçülmüş dolu ve büyük,
  tahmin soluk ve küçük)

**Bütçe girilmemişse renklendirme yapılmıyor**, eski davranış duruyor.
Sorulmamış bir soruya harita üzerinden cevap vermek, kullanıcının
girmediği bir bütçeyi varsaymak olurdu.

Renkler CSS değişkeninden okunuyor, JS'e gömülmüyor: tema değişince
(açık/koyu) palet de değişiyor ve sabit onaltılık değer açık temada
okunmaz hale gelirdi — aynı sorun kartlarda yaşandı.

### Doğrulama ve bir kaçan sabotaj

`ortak.js` öz kontrolleri **243 → 260**; `test.py`'ye "güven skoru renk
dışında da okunuyor" grubu eklendi.

Bir sabotaj **kaçtı ve kontrol düzeltildi**: rozetin görünür metnini silen
sabotaj geçiyordu, çünkü kontrol `/doğrulanmış/` diye bakıyordu ve **aynı
kelime `title` özniteliğinde de duruyor**. Kontrol artık görünür metni
arıyor (`<span>doğrulanmış</span>`). Bu depoda aynı tuzağa daha önce de
düşülmüştü — `href` ile görünen metin karıştırılmıştı.

Harita bu koşum takımında **görülemiyor** (Leaflet unpkg'den geliyor,
ağlar kapalı), o yüzden harita kontrolü kaynak üzerinden yapılıyor ve
`butceDurumu()`'nun döndürdüğü **her** sınıfın renk haritasında karşılığı
olduğunu doğruluyor. Bir sınıf unutulursa o mekanların noktası renksiz
çizilir ve haritada sessizce kaybolur.

## 2026-08-25 — Sosyal fiyat doğrulama, ve bulunan bir k-anonimlik açığı

Yol haritasının maddesi: **"bu fiyat hâlâ geçerli mi?"** — tek dokunuş.

### Neden bu, neden şimdi

Menü fiyatı gösterilebilen mekan sayısı **163** ve bu 163 mekan **53
işletme**. Kazıma yolu kapandı (2026-08-20: üç ayrı ölçüm, sıfır kalem).
Yani fiyat verisinin büyümesinin tek yolu kullanıcı.

Fiş paylaşmak **pahalı** bir eylem: tutar, kişi sayısı, tarih. Bu katman
**ucuz** olanı topluyor — kullanıcı ekranda gördüğü rakama "hâlâ böyle"
ya da "değişmiş" diyor.

### Oy, oy verilen fiyata ait

Kullanıcının gördüğü rakam satıra yazılıyor. Menü tazelenip fiyat
değişirse **eski oylar yeni rakamı doğrulamış sayılmıyor** — yoksa 240
TL'ye verilen "hâlâ böyle" oyu, 480 TL'ye dönmüş bir menüyü doğrular hale
gelirdi. Sunucu fiyata göre gruplu dönüyor, istemci gösterdiği rakamın
satırını seçiyor. Tarayıcıda doğrulandı: başka bir fiyata verilmiş 9 oy,
ekrandaki rakam için "ilk söyleyen sen ol" demeye devam ediyor.

### Onay kuyruğu yok, eşik var

Yorumda ön onay var çünkü orada hakaret riski var; burada gönderilen şey
bir boolean. Kötüye kullanım biçimi farklı: **işletmenin kendi fiyatını
"geçerli" diye oylaması.** Ona karşı savunma onay değil eşik — üç ayrı
kullanıcı, sayımı sunucu yapıyor (kişi sayıyor, oy değil).

Oy skoru değiştiriyor: eşik geçilip çoğunluk "hâlâ böyle" derse mekan
**yeşil**, "değişmiş" derse **kırmızı** ve gerekçe yazılıyor.

**Sınır bilerek burada:** "değişmiş" kararı rakamı ekrandan
*kaldırmıyor*. Kaldırmak için bütçe süzgecinin de ağdan gelen bir cevabı
beklemesi gerekirdi; süzgeç bugün saf ve eşzamanlı (statik veri üzerinde)
ve onu ağa bağlamak listeyi her açılışta bekletirdi. Kullanıcı uyarıyı
görüyor.

---

## Bulunan açık: k-anonimlik eşiği yalnız tarayıcıdaydı

Kendi fonksiyonuma aynı deseni yazarken fark ettim.

`ortak.js`'teki `fisGoster()` üç fişin altında tutarı **gizliyordu** — ama
`mekan_fis_ozeti()` ve `civar_fis_ozeti()` rakamı olduğu gibi
**döndürüyordu.** anon anahtar tasarım gereği herkese açık, yani RPC'yi
doğrudan çağıran biri ekranda gizlenen sayıyı okuyabiliyordu: tek kişinin
bir mekanda kişi başı ne ödediği.

Gizlemeyi yalnız arayüze bırakmak, k-anonimliği bir **görünüm meselesine**
indirger.

### Ne yapıldı

Eşik üç fonksiyonda da sunucuya taşındı:

| Fonksiyon | Eşik altında dönen | Dönmeyen |
|---|---|---|
| `mekan_fis_ozeti` | fiş ve kişi sayısı | **tutar** |
| `civar_fis_ozeti` | fiş, kişi, mekan sayısı | **tutar** |
| `fiyat_oy_ozeti` | kişi sayısı | **dağılım** |

Sayılar dönmeye devam ediyor çünkü arayüz *"2 tane daha gelince
görünecek"* cümlesini onlardan kuruyor ve o cümle kimseyi ifşa etmiyor.

**İstemci tarafındaki eşik silinmedi:** kullanıcı SQL'i güncellemediyse
sunucu eski sürümde kalır ve tek savunma odur. `test.py` ikisinin
ayrışmasını hata sayıyor — tarayıcıdaki sayıyı 5'e çıkarıp sunucuyu 3'te
bırakan bir değişiklik, arada kalan iki kayıt için sessizce rakam
verirdi.

### Doğrulama

Mevcut testler bu açığı **görmüyordu**: ikisi de eşiğin üstünde (üç ve
dört fişle) koşuyordu, yani eşiği kaldıran bir değişiklik ikisini de
aynen geçerdi. Her fonksiyona eşik altı bir adım eklendi ve üç sabotajın
üçü de yakalandı (medyan 225, medyan 300, dağılım 1).

`ortak.js` öz kontrolleri **262 → 279**; `test.py`'ye "k-anonimlik eşiği
sunucuda da var" grubu eklendi (dört sabotaj); SQL takımı
`fiyat_oyu_test.sql` ile 14 adım, `sahiplenme_test` 21, `akran_test` 12.

## 2026-08-25 — Cebimde kombini: "bu bütçeyle burada ne yenir?"

Ortalama fiyat *"kaça oturulur"* diyor. Kombin daha somut bir soruyu
cevaplıyor ve cevabı uydurma değil — menüde **yazan** iki kalem:

> **300 ₺ ile:** ANNE BÖREĞİ 30 ₺ + TİRAMİSU 70 ₺ = 100 ₺ — bütçene giriyor.

### Ölçüm kombinin şeklini belirledi

| Kombin türü | Kapsama |
|---|---|
| Tek mekan içinde (ana ürün + içecek/tatlı) | **148 / 163 = %91** |
| İki mekan, 400 m, farklı adlı | 22 / 163 = **%13** |

Yani *"A'da kahve, B'de tatlı"* gibi iki mekanlı bir kombin bu veriyle
kurulamıyor — ülke çapında 22 mekan. Kombin bu yüzden **tek mekanın
kendi menüsünden**.

**En ucuzu seçiliyor**, bütçeye "oturan" bir sepet aranmıyor: bütçeye
göre kalem seçmek, kullanıcının sormadığı bir tercihte bulunmak olurdu
(*"400 lira varsa en pahalısını al"*). Sorulan şey "yeter mi".

### İki veri değişikliği gerekti

**1) Kalem kategorisi.** Kombin ana ürünle içeceği ayırt etmek zorunda;
kategori yalnız `kat[]` toplamlarındaydı, tek tek kalemlerde yoktu.
`app_veri.py` artık her kaleme `k` yazıyor. Kural **Python'da kalıyor**
(`fiyat_analiz.kategorile`) — tarayıcıya kopyalamak aynı sözlüğü iki
dilde tutmak demekti. Sınıflanamayan kaleme alan hiç yazılmıyor ve o
kalem kombine girmiyor: ne olduğunu bilmediğimiz bir şeyi "yanına
içecek" diye sunmak uydurma bir sepet olurdu. Ölçüldü: İstanbul'un 4.499
kaleminin 2.036'sı (%45) sınıflanıyor.

**2) Her kategoriden en ucuz kalem listede.** Menü **en ucuz 40 kalem**
olarak kırpılıyordu ve kombin 163 mekanın yalnız **47'sinde**
kurulabiliyordu. Tıkanan 116'nın **99'u Domino's**: pizzaların hepsi
(~480 TL) en ucuz 40'ın dışında kalıyor, listede yalnız garnitür ve
içecek duruyordu — yani mekanın **ana ürünü kayda hiç girmiyordu.**

Aynı çarpıklık kullanıcıya da görünüyordu: detay paneli *"en ucuz 40
kalem, 35-165 TL"* yazıp üstünde *"yemek ~480 TL"* gösteriyordu.

Kural mekanın ana ürününe **bakmıyor** — o karar `ortak.js`'te
(`anaKategoriler`) ve onu Python'a kopyalamak aynı kuralı iki dilde
tutmak olurdu. Bunun yerine mekanik bir kural: **her kategoriden en ucuz
kalem listede.** Ana ürün de bir kategori olduğu için zorunlu olarak
giriyor.

Sonuç: **%29 → %90** (146/163). Veri boyutu değişmedi (3,8 MB).

### Alkolsüz önce

Ölçülen vaka: Amara Şile Ocakbaşı'nda kombin *"patlıcan salatası + Efes
Malt"* çıkıyordu, çünkü menüdeki en ucuz içecek biraydı. Uygulama
alkollü mekanları listeliyor ve bu doğru; ama kimsenin istemediği bir
öğüne **varsayılan olarak içki koymak** ayrı bir şey. Alkollü kalem
ancak alkolsüz hiç yoksa geliyor. Ölçüldü: **151 kombinin 0'ında** alkol
kategorisinde kalem var.

Sınır not edildi: sınıflandırma **ada** bakıyor, "Baileys Americano"
kategori olarak Americano. Düzeltmek yeni bir anahtar kelime listesi
demek ve o liste kendi başına bir ayrışma kaynağı olurdu.

### Kaçan sabotaj ve nedeni

Bir sabotaj "kaçtı" göründü: kategorisiz kalemi kabul eden sürüm kombini
`null`'a düşürüyor, kontrolüm de `kombinKur(...).kalemler` diyerek
**TypeError fırlatıyordu** — yani kontrol listesi hiç kurulmuyor ve 294
kontrolün hiçbiri raporlanmadan grup patlıyordu. Sonuç "yakalandı" gibi
değil "kaçtı" gibi görünüyordu. Kontroller artık null-güvenli ve sepetin
**tamamını** pinliyor.

Bir de kendi koşum yöntemim kusurluydu: sabotaj betiğini `| head -12`
ile borulamıştım; `head` kapanınca betik **SIGPIPE ile ortada öldü** ve
`ortak.js` sabotajlı kaldı. Bu depoda benzeri daha önce de olmuştu
(zaman aşımına uğrayan sabotaj döngüsü). Sabotaj çıktısı artık dosyaya
yazılıyor.

### Doğrulama

`ortak.js` öz kontrolleri **279 → 296**; `test.py`'ye "kombin mekanın
kendi menüsünden" grubu eklendi. Altı sabotajın altısı yakalandı —
aralarında "veri üretiminde kalem kategorisi kalktı" ve "her kategoriden
en ucuz kalem kuralı kalktı" var; ikincisi betiği değiştirip **veriyi
yeniden üretmeyi unutmayı** da yakalıyor.

## 2026-08-25 — Kullanıcı seviyesi

Yol haritasının maddesi. Seviye bir **süs** değil bir **sayım**:
kullanıcının kaç onaydan geçmiş katkı yaptığı.

| Eşik | Ad | Gerekçe |
|---|---|---|
| 0 | Yeni | — |
| 1 | Katkıcı | ilk katkı: bir mekan senin sayende daha eksiksiz |
| 3 | Doğrulayıcı | **FIS_ESIK ile aynı sayı** — tek başına bir mekanın fiyatını k-anonimlik eşiğine taşıyabilecek katkı |
| 10 | Düzenli | **yuvarlak sayı, ölçüm değil** |
| 25 | Kaşif | **yuvarlak sayı, ölçüm değil** |
| 50 | Emektar | **yuvarlak sayı, ölçüm değil** |

Son üçünün gerekçesi yok ve bu bilerek yazılıyor: uygulama daha yayında
değil, yani gerçek bir katkı dağılımı yok. Dağılım oluşunca bu üç sayı
ölçüme göre yeniden konmalı. Uydurma bir eğriye "veri" demektense
uydurma olduğunu söylemek daha dürüst. `test.py` 3. eşiğin `FIS_ESIK`
ile aynı kalmasını denetliyor — ayrışırsa "Doğrulayıcı" adı gerekçesini
kaybeder.

### Üç sessiz kusur, üçü de kapalı

**1) Gönderilen değil ONAYDAN GEÇMİŞ katkı sayılıyor.** Gönderileni
saymak, seviyeyi kuyruğa çöp atarak yükseltilebilir yapardı. Ön onay
zaten hakaret ve yanlış bilgi için var; seviye de aynı kapıdan geçiyor.

**2) Fiyat oyu seviyeye girmiyor.** Oy tek dokunuş ve onay kuyruğu yok
(oradaki savunma eşik). Onaysız ve tek dokunuşluk bir eylemi seviyeye
bağlamak, tam da oyunlaştırmanın bozulduğu yer olurdu. Oy sayısı ekranda
**ayrı** yazıyor: *"4 fiyat doğrulaman var (seviyeye girmiyor)"* —
görünmez değil, seviyeye etkisiz.

**3) Sayım satır çekmiyor.** `head:true` ile yalnız sayı dönüyor.
Hesabım ekranındaki sekmeler tembel yükleniyor; seviyeyi o listelerden
hesaplamak *"hangi sekmeye bastığına göre değişen seviye"* demekti.
`test.py` seviye çiziminin bir sekme çizicisinin içine taşınmasını da
hata sayıyor.

### Seviye herkese açık değil

Kullanıcı kendi sayfasında görüyor, başka kimseye gösterilmiyor.
Başkasına göstermek için sayımın **sunucuda** yapılması gerekirdi —
tarayıcıda hesaplanan bir rozet, sahibi tarafından istediği gibi
yazılabilir ve "doğrulanmış katkıcı" gibi bir iddiayı taşıyamaz.

Katkı yoksa kutu **hiç çıkmıyor**: yeni açılmış bir hesaba *"Yeni
seviye, 0 katkı"* göstermek boş bir ilerleme çubuğundan başka bir şey
değil.

Döküm türe göre yazılıyor (*"3 fiyat paylaşımı · 2 eksik bilgi · 2
yorum"*): tek bir "7 katkı" sayısı neyin sayıldığını söylemiyor ve
kullanıcı doğrulayamıyor.

### Doğrulama

Beş durum gerçek tarayıcıda ölçüldü: katkı yok (kutu gizli), 1, 3
(eşik), 7 + 4 oy, 55 (en üst).

Taklit Supabase'e **sayım desteği** eklendi (`count`/`head`): olmasaydı
seviye her zaman sıfır çıkardı — yani ekran "çalışıyor" görünüp yanlış
sayı gösterirdi.

`ortak.js` öz kontrolleri **296 → 313**; `test.py`'ye "seviye onaylı
katkıyı sayıyor" grubu eklendi (altı sabotaj, altısı da yakalandı).

## 2026-08-25 — İşletme aboneliği ve gelir modeli

Yol haritasının son maddesi. Diğerlerinden farklı: para ve hukuk
içeriyor, o yüzden **ne yapılabildiği ile ne yapılamadığı ayrı ayrı**
yazılıyor.

### Bugün ödeme alınamıyor — ve bu bir tercih değil

Faz 0 kararı: *"Şirket: gelir doğana kadar kurulmayacak."* Türkiye'de
şirket olmadan işletmeden düzenli ödeme almak fatura ve vergi
yükümlülüğü doğuruyor; ödeme altyapısı da (iyzico, PayTR, Stripe) tüzel
kişilik istiyor.

Yani **abonelik akışı bugün kurulamaz.** Kurulsaydı, ödeme alamayan bir
"Abone ol" düğmesi olurdu — tutulmayan bir söz. Bu depodaki kural fiyat
için ne diyorsa vaat için de aynısı geçerli.

**Bu bir tavuk-yumurta ve kararı senin vermen gerekiyor:** şirketi gelir
öncesi kurmak (aylık ~10-12 bin TL Bağ-Kur), yoksa ilk müşteri
bulununca kurmak. Ben bu kararı veremem; verilene kadar altyapıyı
hazırladım.

### Satılmayacak olanlar — bu liste ürünün kendisi

| Satılmaz | Neden |
|---|---|
| **Sıralamada üst sıra** | Para ile sıra satmak, "bütçene göre nereye gidilir" sorusunun cevabını bozar. Ürünün tek işi bu. |
| **Puan, rozet, "önerilen" etiketi** | Uydurulmuş sosyal kanıt zaten Yapılmayacaklar'da. Parayla verileni koymak daha kötüsü. |
| **Olumsuz yorumu kaldırma** | Ön onay hakaret için var, memnuniyetsizlik için değil. |
| **Fiyatı gizleme / değiştirme** | Fiyat gidenden geliyor; işletmenin onu susturabilmesi katmanı bitirir. |
| **Kullanıcı verisi** | Ham IP zaten saklanmıyor, konum sunucuya hiç gitmiyor. Satılacak bir şey yok. |

Geriye kalan **tek dürüst gelir**: işletmenin **kendi sayfası** ve
**kendi verisi** üzerinde ona değer katan şeyler. Listeyi bozmayan,
listeye para karıştırmayan şeyler.

### Bugün kurulan: bütçe talebi

Bir işletmenin gerçekten merak ettiği şey "kaç kişi baktı" değil,
**"bana bakanlar ne kadar harcamayı düşünüyordu"**. Görüntülenme
sayısını her sayaç verir; bu soruyu yalnız bu uygulamanın verisi
cevaplayabilir — ve abonelik önerisini somut yapan şey bu.

Panelde:

> Bütçe yazan 14 kişinin 9'u 250 ₺ – 399 ₺ arıyordu.

**Tam tutar değil bant saklanıyor.** Sayaç satırı `(mekan, gün, cihaz)`
üçlüsü; oraya "347 TL" yazmak üçlüyü giderek daha ayırt edici yapardı.
Beş kova, eşikleri `BUTCE_SECENEK`'ten — ekranda kullanıcıya sunulan
sayılarla aynı, ikinci bir ölçek uydurulmadı. `null` = bütçe girilmemiş;
sıfır değil, çünkü "bilinmiyor" ile "farketmez" ayrı şeyler.

**k-anonimlik eşiği sunucuda (5 bakış).** Altında dağılım **hiç
dönmüyor**: küçük sayılarda *"bakanların 1'i 150 ₺ altıydı"* demek, o
tek kişinin bütçesini ifşa etmekle aynı şey — hele o kişi işletmecinin
tanıdığı biriyse. Eşik fiş eşiğinden yüksek (3 yerine 5) çünkü burada
**dağılımın kendisi** dönüyor, tek bir medyan değil.

### Ücretsiz kalacaklar

Bugünkü panelin tamamı — görüntülenme, puan, fiş medyanı, eksik bilgi
listesi, düzenleme formu, **ve bütçe talebi** — ücretsiz kalıyor.
Sebep ideolojik değil: işletme sayfasını düzeltince **veri iyileşiyor**,
yani o katkı zaten bize değer üretiyor. Onu paywall'un arkasına koymak,
para almak için veriyi kötüleştirmek olurdu.

Ücretli katman, işletmenin **kendi** sayfasına ek olarak isteyeceği
şeylerden kurulmalı: zaman içindeki değişim (bu ay geçen aya göre),
civarla kıyas, menü yayımlama aracı, yoruma cevap. Hiçbiri listeyi
etkilemiyor.

**Fiyat konmadı.** Fiyat, gerçek bir işletmeyle konuşulmadan konursa
tahmin olur. İlk kural yine aynı: ölç, sonra karar ver.

### Doğrulama

`sayac_test.sql` 11 → **16 adım**. Yeni adımlar: bant kaydediliyor mu,
eşik altında dağılım dönmüyor mu, **eşik aşılınca dönüyor mu** (yalnız
"gizliyor mu" diye bakmak yetmez — eşiği 500 yapan bir değişiklik de
gizleme adımını geçerdi), bayat bakış eleniyor mu, **bozuk bant
görüntülenmenin kendisini düşürüyor mu** (sayaç bir ölçüm aracı; bozuk
bir bant yüzünden görünme kaybolmamalı), ham satırlar hâlâ kapalı mı.

`mekan_goruldu` imzası iki argümanlı oldu ve eski tek argümanlı sürüm
düşürüldü — iki imza yan yana dururken PostgREST hangisini çağıracağını
bilemez ve sayaç sessizce çalışmaz olur. Dosyanın kendi kurulum kontrolü
eski imzayı arıyordu ve **kendi kurulumunda patlıyordu**; o da
düzeltildi.

`create table if not exists` var olan tabloya **sütun eklemez**: sayacı
daha önce kurmuş bir kurulumda `butce_bandi` sessizce oluşmaz ve özellik
"çalışıyor" görünüp hiçbir şey göstermezdi. `alter table ... add column
if not exists` eklendi.

### Yol boyunca: Türkçe sayı eki

Panel cümlesini yazarken iki yerde **yanlış ek** olduğu görüldü:
*"3 kişiden 3'i"* → doğrusu **3'ü**, *"14 kişinin 9'i"* → **9'u**. Ek
sayının **okunuşunun** son hecesine bakıyor ve son **söylenen**
kelimeden geliyor: 14 = "on dört" → `14'ü`, 47 = "kırk yedi" → `47'si`.
`sayiEki()` yazıldı; 16 kontrolle sınanıyor. Sıfır ilk yazımda bütün
modlardan geçip "milyon" dalına düşüyordu (`0'u`) — kontrol yakaladı,
doğrusu `0'ı`.

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

---

## 2026-08-25 — Marka maketleri uygulandı: açık tema, sekmeler, menü, topluluk

Marka kılavuzunun beş ekran maketi (`Bütçeni Gir`, `Haritada Keşfet`,
`Menüleri Gör`, `Topluluğa Katıl` ve açılış) uygulamaya geçirildi. Görünüm
işi olarak başladı; her adımda maketle uygulamanın **ayrıldığı yer ölçüldü**
ve ayrılan yerlerin bir kısmı gerçek kusur çıktı.

### Uygulama kendi yazı tipini hiç yüklemiyormuş

Ölçüm (gerçek tarayıcı, `index.html`):

```
istenen adres : ...family=Fraunces...&family=Karla...
h1 kullanıyor : Montserrat, ui-sans-serif, system-ui, ...
yüklenen yüz  : []              <-- HİÇBİRİ
```

`stil.css` marka kılavuzuna geçirilirken `--font-baslik` ve `--font-govde`
**Montserrat** oldu; 13 sayfanın `<link>` satırı **Fraunces + Karla**'da
kaldı. Yani uygulama iki yazı tipini ağdan çekiyor, hiçbirini kullanmıyor ve
gerçekte **sistemin varsayılan sans'ıyla** çiziliyordu. İki maliyet birden:
her sayfada boşa inen ve çizimi bekleten bir stil dosyası, ve marka yazı
tipinin hiçbir yerde görünmemesi.

Sayfa açılıyor, "çalışıyor" görünüyordu. Ancak tarayıcıda **hangi yüzün
yüklendiğine** bakınca ortaya çıktı. Yeni kontrol grubu tam bunu ölçüyor:
indirilen aile ile CSS'in istediği aile aynı mı. Tek istisna
`cevrimdisi.html` ve **adıyla** muaf: o sayfa ağ yokken açılıyor.

### Paylaşım kartı hâlâ "Oturalım" diyordu

`app/og.png` elle yapılmıştı ve iki kez birden eskimişti: eski marka adını
ve **36.102 mekan** yazısını taşıyordu (veri: 35.852). Her paylaşılan
bağlantının önizlemesinde eski ad duruyordu.

İkisi de aynı sebepten: kartın kaynağı yoktu. `og_uret.py` yazıldı — kart bir
tarayıcıda, `app/stil.css` yüklü halde çiziliyor; sayı veriden okunuyor ve
PNG'nin içine damgalanıyor (`tEXt "cebimde-mekan"`), `test.py` damgayı
veriyle karşılaştırıyor.

Yazı tipi karta **gömülü** giriyor. İlk denemede `<link>` ile çekildi ve ağı
kapalı makinede kart **sessizce** yedek yazı tipiyle çıktı — "çalıştı"
görünüyordu. Artık yüz yüklenmezse üretim duruyor.

### Mekan sayfasında menü hiç yokmuş

291 mekanın menüsünde **7.335 fiyatlı kalem** duruyor ve ekranda hiçbiri
görünmüyordu. "Menü" sekmesine basan kullanıcı menüyü göremiyordu. Liste
eklendi; her tasarım kararı bir ölçüme dayanıyor:

| Karar | Ölçüm |
|---|---|
| fotoğraf yok | 7.335 kalemin **sıfırında** fotoğraf alanı var |
| gruplama yok | kategori kapsamı mekan başına ortanca **%47** |
| fiyata göre sıralı | uygulamanın sorusu "bu parayla ne yenir" |
| ad kırpılmıyor | kalemlerin **%16**'sının adı 34 harften uzun |
| ilk 12 açık | mekan başına ortanca 34 kalem, en çok 50 |

### Rozet menüyle çelişiyordu

Menüsünde fiyat yazan 291 mekanın **128'i (%44)** "FİYAT YOK" rozeti
alıyordu — o 128 mekanın menüsünde toplam **1.340 fiyatlı kalem** var.
Rozet doğru bir şey söylüyordu (bir **öğünün** kaça geldiği çıkmıyor: 84
mekanda ana ürün kalemi ikiden az, 27'sinde hiç kategori yok, 16'sında bütün
kategoriler içecek) ama **cümlesi yanlıştı**. Renk kırmızı kaldı, cümle
"öğün fiyatı yok" oldu, gerekçe kalem sayısını yazıyor.

### Bütçe üçüncü ekranda kayboluyordu

Keşfette `?butce=300` ile gezip mekan açınca panelin bağlantısı
`isletme.html?il=34&id=...` veriyordu — bütçe yok. Kullanıcının bir kere
yazdığı rakam üçüncü ekranda düşüyordu; kombin "En ucuz öğün" diyordu, menü
listesi kaç kalemin bütçeye girdiğini susuyordu.

### Harita ekranın 4,4 katıydı

Ölçüm (390×844, harita görünümü):

```
.govde  yüksekliği :  497 px   (doğru)
#harita yüksekliği : 2194 px   <-- ekranın 4,4 katı
```

`.govde` bir grid ve satırı örtülü `auto`; çocuğun `height:100%` değeri
belirsiz bir satıra göre çözülemiyor. Kullanıcıda sonuç: harita görünümüne
geçen kişi ekranın dört katı uzunlukta bir harita içinde kayıyordu.
`grid-template-rows:minmax(0,1fr)` ile satır belirli hale geldi.

Ayrıca panel haritanın **tamamını** örtüyordu (harita alanı 295–792 px,
panel 290 px'ten başlayıp 554 px) ve arkasındaki perde `rgba(0,0,0,.66)` +
`blur(3px)` idi. Maketteki ekranda kart altta duruyor, harita net. Perde
hafifledi ve panel harita görünümünde kısaldı; modal kaldı (odak tuzağı,
Esc). İşaretçinin Leaflet balonu da panelle **birlikte** açılıyordu — üç
bilgisi panelin başlığında zaten yazıyor ve perdenin ardında kalıyordu.

### Maketteki iki şey bilerek yapılmadı

`Topluluğa Katıl` ekranının merkezindeki kart **"Ahmet R. — Latte hâlâ
₺145"** diyor. Bu bir **fiyat oyu** ve o tablonun kuralı kimsenin
**başkasının** oyunu görememesi (`fiyat_oyu_test.sql` adım 10 ve 10b).
Fiyat oyu dışarıya yalnız eşik üstü toplam olarak veriliyor (`OY_ESIK = 3`).
Bir kişinin oyunu adıyla yayımlamak ölçülmüş bir kararı kırardı. **Maket bir
çizim, kural bir karar** — akış kuralın tarafında duruyor.

Kartların altındaki **"24 beğeni, 3 yorum"** sayacı da yok: arkasında ne
tablo var ne moderasyon. Sıfır yazan bir sayaç da uydurma bir sayı da yalan
olurdu.

Menü katkıları akışta **adsız**: mekan sayfasında da yazarsız duruyorlar ve
katkı formu kullanıcıya "adın yazacak" demiyor. Fişler hiç yok — kanı değil
ödeme kaydı.

### Kontrollerin kendi kusurları

- **SQL bitiş imzası sessizce yanlıştı.** `sahiplenme_test.sql` bitiş
  satırını dosya adı olmadan yazıyordu (`=== 21 kontrolun hepsi gecti ===`)
  ve `test.py`'nin aradığı `"20 kontrolun hepsi gecti"` metni **yorum**
  dosyasının satırının içinde geçiyordu. Sahiplenme koşumu baştan sona
  patlasa bile kontrol yeşil kalırdı — 21 SQL kontrolü başkasının çıktısına
  yaslanmıştı. `sayac` (11→16) ve `akran` (11→12) imzaları eskimişti,
  `fiyat_oyu_test` (14 adım) hiç listede yoktu.
- **Kare kontrolü** artık olmayan bir katmanı ölçüyordu; silmek yerine
  **tersine** çevrildi: ana ekranda sürekli dönen bir çizim döngüsü olmamalı.
- **Sekmeler** yorumları ve galeriyi gizleyince tarayıcı kontrolleri patladı
  — sekmelerin neyi gizlediğini ilk söyleyen şey onlar oldu.
- Yeni gruplar `s or True` dönüyordu; `kayit()` **liste** bekliyor ve boş
  listede `True`'yu BAŞARISIZ sayıp bütün koşumu çatlattı.

Toplam **20 sabotaj** koşuldu; ikisi ilk yazımda kaçtı (`"sort("` gevşekti,
`"MENU_ILK"` düğme metninde de geçiyordu) ve kontroller daraltıldı.

**42 kontrol grubunun hepsi geçiyor.** Kurulum: `veritabani/topluluk.sql`
Supabase'te çalıştırılmalı.

---

## 2026-08-26 — Leaflet yerele alındı, gizlilik listesi gerçeğe getirildi

### Harita artık üçüncü bir tarafa bağlı değil

Bu **varsayım değil, yaşanmış**: Leaflet CDN'den gelmeyince keşfet
ekranının **tamamı** ölüyordu — sıfır kart, sayaç "…"da donmuş. SRI o gün
hiçbir şey yapamadı, çünkü SRI dosyanın **doğru** olup olmadığını söylüyor,
**gelip gelmediğini** değil. İki ayrı soru.

Dosya artık depoda (200 KB). `kutuphane_al.py` onu **npm kayıt
defterinden** alıyor ve kayıt defterinin resmî `sha512` özetiyle
(`dist.integrity`) doğrulamadan hiçbir şey yazmıyor — yani SRI'nin verdiği
güvence duruyor, üzerine erişilebilirlik geliyor. unpkg yerine kayıt
defteri, çünkü özet orada yayımlanıyor.

Ölçüm (bütün dış istekler kesili, gerçek tarayıcı):

```
Leaflet yüklendi : True        (önceden False)
harita kabı      : True        (.leaflet-container)
harita-yok kutusu: False       (önceden True)
```

BSD-2-Clause: atıf başlığı dosyanın içinde, lisans metni
`app/lib/leaflet-LICENSE.txt`'te. Kodu depoya kopyalayıp lisansı bırakmak
şartın yarısını atlamak olurdu.

CSP kendiliğinden daralıyor: dosya yoksa `unpkg.com` üç yönergede birden
kalmak zorunda, varsa üçünden birden düşüyor.

### Gizlilik sayfası üç ayrı şeyi yanlış söylüyormuş

Sağlayıcı tablosu CSP ile karşılaştırıldı:

| Sağlayıcı | Tabloda | Gerçekte |
|---|---|---|
| unpkg | yazıyordu | artık **hiç** çağrılmıyor |
| upload.wikimedia.org | yoktu | çağrılıyor (Commons fotoğrafları) |
| esm.sh | yoktu | çağrılıyor (supabase-js yer tutucusu) |

İlki fazla beyan; diğerleri **eksik beyan** ve daha ağır — kullanıcıya
tarayıcısının kimlerle konuştuğunu eksik söylemek. Tablo artık CSP ile
karşılaştırılıyor: CSP tarayıcının nereye gidebileceğini söyleyen tek
yetkili yer.

### Kontrollerin kendi kusurları

- **Tarayıcı kontrollerinin ikisi de anlamını kaybetmişti.** "Leaflet
  yokken" hali unpkg isteği kesilerek oluşuyordu; dosya yerele alınınca o
  hal kendiliğinden **imkânsızlaştı** ve zarif düşüş yolu sınanmamış
  kalacaktı. "Leaflet varken" hali ise taklit `window.L`i açılışta
  kuruyordu; gerçek dosya sonradan yüklenip **üzerine yazıyor** ve sayaçlar
  hiç dolmuyordu. İkisi de `sayfa_ac`'ın yeni `leafletsiz` seçeneğiyle
  kuruluyor — kütüphanenin nerede durduğundan bağımsız.
- **SRI kontrolü sayıyla ölçüyordu** ("keşfet.html'de tam iki `integrity`").
  Kurala çevrildi: dış bir kaynaktan yüklenen her `script`/`link`
  `integrity` taşımalı. Google Fonts muaf ve gerekçesi somut — yayımladıkları
  CSS'in içeriği tarayıcıya göre değişiyor, sabit bir özet tutmuyor.
- `sw_uret.py` yalnız `lib/*.js` tarıyordu; `leaflet.css` kabuğun **dışında**
  kalırdı ve çevrimdışı açılan haritada üslup hiç gelmezdi.
- Gizlilik kontrolünün ilk hali **gevşekti**: "ad sayfada geçiyor mu" diye
  bakıyordu ve üç sabotaj birden geçti — "Wikimedia Commons" ve "esm.sh"
  sayfanın metninde de açıklanıyor, "unpkg" ise tablonun üstündeki yorumda
  geçiyor. Artık tablo satırları okunuyor.
- İlk yazımda `leaflet.js`'i "Copyright" arayarak **reddettim**; Leaflet
  başlığı "(c) 2010-2023 Vladimir Agafonkin" diye yazıyor.

### topluluk.sql ne istediğini söylemiyordu

Dosya Supabase'te çalıştırıldı ve `ERROR: 42P01: relation
"public.yorumlar" does not exist` dedi. O satır kullanıcıya ne yapacağını
söylemiyor. İki kusur birden: dosya **KURULUM.md'ye hiç yazılmamıştı** ve
bağımlılığını söylemiyordu. Depoda bu iş için gelenek zaten vardı
(`yorum.sql` sırası yanlışsa "Önce profil.sql çalıştırılmalı" diyor).

Kapı **en başta**, sonda değil: fonksiyon `language sql` ve gövdesi
*oluşturulurken* doğrulanıyor. Kapının ilk hali de hatalıydı ve gerçek
Postgres'te ortaya çıktı: `text[] || 'metin'` belirsiz ("malformed array
literal").

Yeni kontrol grubu: `kos.sh`'ın kurduğu her dosya KURULUM.md'de yazıyor mu,
ve başka bir dosyanın tablosunu okuyan her dosyanın `to_regclass` kapısı
var mı. Dosya adları `kos.sh`'tan okunuyor.

**45 kontrol grubunun hepsi geçiyor.** Kalan tek CDN bağımlılığı
supabase-js; `python kutuphane_al.py` çalıştırılınca o da yerele iniyor ve
`esm.sh` hem CSP'den hem gizlilik tablosundan kendiliğinden düşüyor.

---

## 26 Ağustos 2026 — ürün tarifinin kalan dört maddesi

Ürün tarifindeki 16 maddenin 12'si zaten ekrandaydı. Kalan dördü bu
turda kapandı; ikisi (14 ve 15) bilerek kapanmadı ve sebepleri aşağıda.

### md.10 — "Bugün burada ne yenir?" fixture'ı kendi kontrolünü kaçırıyormuş

Kalem listesi çalışıyordu ama **sabotaj üçü birden kaçtı**:
tekilleştirme, tekrarda en yakın şubenin kalması, mekan başına tek
kalem. Sebep koddan değil **fixture'dan** çıktı:

```
const CIVAR_YARICAP = 500;   /* metre */
c2 "Uzak Sube"  ->  535 m
```

İkinci şube yarıçapın 35 m dışındaydı; yani aynı adlı iki kalem hiçbir
zaman birlikte menzile girmiyor, tekilleştirme hiç denenmiyordu. Şube
187 m'ye alındı ve iki yenir kalemi olan bir mekan (`Corbaci`, 55 ve 70)
eklendi. Altı sabotajın altısı yakalanıyor.

### md.5 — onayın raf ömrü: 🟢 0-7 gün, 🟡 8-30, 🔴 30+

Tarifin istediği gün eşikleri **hiç uygulanmıyordu**: üç kişi "hâlâ
böyle" dediyse oy kaç günlük olursa olsun rozet yeşildi. Menü tarihine
uygulanamıyor (kazınan sayfada gün yok, `FIYAT_TAZE_AY` orada duruyor)
ama **oyun günü var** ve eşikler tam ona ait.

- 0-7 gün → yeşil
- 8-30 gün → sarı
- 30 günden eski → **hüküm vermiyor**, karar menü kanıtına düşüyor

Eski onay **kırmızıya çevrilmiyor**: bir onayı cezaya çevirmek olurdu.
Fiyatın yanlış olduğunun kanıtı değil, doğru olduğunun kanıtı olmaktan
çıkması.

Tarihsiz onay da artık yeşil değil (sarı, "tarihi bilinmiyor"): yaşını
bilmediğimiz bir onay "son 7 gün" diyemez. `Number(null)` sıfır olduğu
için `oyYasi` bu iki değeri önce eliyor — `gunOnce`'ta yakalanan aynı
tuzak.

### md.3 — kampanya alanı: 672 satır "ürün" gibi duruyormuş

Ölçüldü (291 menülü mekan): **96 mekanda 672 satır** bir ürün değil bir
**teklif** — "1 Alana 1 Bedava İçecek · 120 ₺" sıra menüde 120 liralık
bir içecek gibi duruyordu. O mekanların menü satırlarının %17'si.

Fiyatları çarpıtmıyorlar (mekan medyanını 1,5 kat aşan tek satır bile
yok); eksik olan **etiket**. Satır silinmiyor, ayrılıyor: teklif gerçek
ve bütçesine bakan için değerli.

Kural Python'da (`fiyat_analiz.kampanya_mi`), veriye tek baytlık bir
bayrak olarak yazılıyor (`"p":1`). Kapı `PAKET`'in **dar alt kümesi**,
tamamı değil: o listenin çoğu çoklu paket ve perakende ("10'lu Caffe
Latte", "Tekirdağ 70 CL", bir kuaförün "5-6'lı Örgü"sü). Yanlış etiket,
etiketsizlikten kötü.

Bayrak üç yeri birden düzeltiyor: menü listesi, "menüde N kalemin fiyatı
var" rozeti ve "bu civarda ne yenir". Sonuncusu ölçülmüş bir zarar
değildi ama açıktı — bir teklifin fiyatı porsiyon fiyatı diye
önerilebilirdi.

### md.4 — kalem düzeyinde tarih: kazınan menüde YOK, katkıda VAR

Tarif "Latte · son doğrulanma 2 gün önce" istiyordu. Ölçüldü: **291
mekanın 293'ünde bütün kalemler aynı gün derlenmiş**. Yani kalem tarihi
mekan tarihinin birebir kopyası olurdu — 81 dosyada bilgi taşımayan bayt.
Uydurmak yerine ölçüm yazıldı.

Kalem düzeyinde tarihi **gerçekten** olan tek veri kullanıcıdan gelen
menü katkısı (`menu_katkilari.olusturuldu`). O alan sorguda zaten
çekiliyordu ve **ekrana hiç gelmiyordu**. Artık kalemin altında
"3 gün önce" yazıyor — biçim `gunOnce`'ta, oy rozetiyle aynı yerde.

`zamanYasi` adı bilerek `gunFarki` değil: o ad kohort ölçümünde başka
bir anlamla duruyor (iki gün arası fark, yuvarlanmış, negatif olabilir).
Birleştirmek ikisinden birini bozardı.

### Kapanmayan iki madde

- **md.14 (gelir modeli).** Abonelik akışı bugün kurulamaz: Faz 0
  kararı "şirket gelir doğana kadar kurulmayacak", yani ödeme
  alınamıyor. İşletme paneli hazır ve aboneliği somut yapacak sayıyı
  üretiyor. **Sponsorlu sonuç yapılmadı ve yapılmayacak**: bütçe
  dürüstlüğü satan bir uygulamada sıralamayı satmak, satılan şeyin
  kendisini bozar.
- **md.15 (teknik mimari).** Spring Boot + PostGIS + Redis + React
  Native yerine derleme adımı olmayan statik site + Supabase. Sebep Faz
  0'ın "maliyet 0 TL" kararı; bilinçli ayrışma, eksik değil.

**421 iç kontrol + 46 kontrol grubu geçiyor.** Bu turda yazılan 14
sabotajın 14'ü yakalanıyor.

### İşletme sayfasında konum: harita, yol tarifi, hesaplar

Ölçüldü: **adresi olan mekan yalnız 9.397/35.852 (%26,2)**. Kalan
**26.455'inde** koordinat, "burası nerede" sorusunun *tek* cevabı — ve
sayfada hiç görünmüyordu. Tek şey "Çevresini haritada gör" diye keşfet
ekranına giden bir bağlantıydı; yani mekanın kendi sayfası nerede
olduğunu söylemiyordu.

Bilgi sekmesine **Konum** kutusu geldi: harita (yerel Leaflet, keşfet ile
aynı dosya), altında koordinatın kendisi, sonra bağlantılar.

Harita **isteğe bağlı** — keşfetteki kuralın aynısı. Kütüphane
yüklenemezse yerine ne olduğunu söyleyen kutu kalıyor; koordinat, yol
tarifi ve hesap düğmeleri çalışmaya devam ediyor. Gerçek tarayıcıda iki
hal birden ölçülüyor.

Harita **kaydırılmıyor ve yakınlaştırılmıyor**: tek bir nokta gösteriyor
ve sayfa kaydırmasını çalması, kazandırdığından çok götürürdü. Büyütmek
isteyen dış haritaya gidiyor, düğme hemen altında.

### "Yol tarifi" ile "ara" ayrı düğmeler, ve bu bilerek

| Düğme | Neye gidiyor | Neden |
|---|---|---|
| Yol tarifi | `destination=<enlem>,<boylam>` | Koordinat elimizde, yanılma payı yok |
| Google'da ara | ad + adres + il + koordinat | Maps yer kimliği (`place_id`) **elimizde yok** |
| Yandex'te ara | aynı | aynı |
| OpenStreetMap | `mlat`/`mlon` | Verinin geldiği yer |

Arama düğmeleri "aç" demiyor, **"ara"** diyor. "Bu mekanın Maps sayfası"
demek, aynı adlı başka bir şubeye yollandığında yalan olurdu — ve bağ
görünüşte çalışmaya devam ettiği için fark edilmezdi. Aramaya koordinat
da giriyor: ad tek başına "Bambi Cafe"yi Türkiye'de onlarca yere düşürüyor.

### Yorumlar kazınmıyor — ve sayfa bunu yazıyor

Maps, Yandex ve Instagram yorumları yazarlarının telifinde ve platforma
lisanslı. Kopyalayıp burada yayımlama hakkımız yok; fotoğraflarda verilen
kararın aynısı (CEBIMDE.md "Yapılmayacaklar"). Yapılabilecek dürüst şey
kullanıcıyı **kaynağa göndermek** — yorumu orada, yazarının yayımladığı
yerde okuyor. Cebimde'nin kendi yorumları ayrı ve zaten sayfada.

Bu tercih **ekranda yazıyor**. Sessizce yapsaydık kullanıcının "yorumlar
nerede" sorusu cevapsız kalırdı.

### Sosyal hesap kapsamı: %0,8, ve sebebi bir veri boşluğu

Sosyal hesabı olan mekan **304 (%0,8)** ve hepsi Instagram. Facebook, X,
TikTok, YouTube **sıfır** — ama bu OSM'de yok demek değil:

- `turkiye_cek.py` beş platformu da okuyor (`contact:facebook`,
  `contact:twitter`, …) ve beş sütunu da yazıyor.
- `app_veri.py` beşini de arıyor (`sosyal_adi("facebook", …)`).
- **`turkiye_mekanlar.csv`'de o sütunlar yok**: dosya, kazıyıcının o
  platformlar eklenmeden önceki sürümüyle üretilmiş.

Yani eksik olan şey kod değil, veri: `python turkiye_cek.py` yeniden
çalıştırılınca dört sütun kendiliğinden doluyor.

**İkinci kaynak eklendi (2026-08-27): işletmenin kendi sitesi.**
`turkiye_cek.py` yeniden koşsa bile OSM'de **etiket yoksa** orada da bir
şey çıkmıyor. `menu_pdf_tara.py` zaten her işletme sitesini gerçek
tarayıcıda açıyordu; artık aynı geçişte sayfadaki sosyal bağları da
topluyor (`menu_site_sosyal.csv`). Ek istek yok, ek kaynak yok — ve
kazıma değil: bağ, işletmenin kendi sitesinde kendi yayımladığı bağ.

Üç sınır kodda duruyor: paylaşım bağları (`sharer`, `intent`, `plugins`)
eleniyor — alınsalardı her mekana aynı sahte hesap yazılırdı; platform
başına tek bağ alınıyor; ve biçim kuralı **tek yerde** (`sosyal_adi`)
kalıyor, tarayıcı ham URL yazıyor. Çözülemeyen bağ — gönderi adresi
`instagram.com/p/…`, kanal kimliği `youtube.com/channel/UC…` — sessizce
düşüyor. Çelişkide **OSM kazanıyor**: etiketi bir insan yazmış.

**Ve bu kaynak neredeyse hiç koşamayacaktı.** `site_isle` bağı topluyor
ama `islenmis()` aynı siteyi iki kez taramıyor; ölçüldü: 2.294 JS
sitesinin 2.372'si menü için zaten taranmış, `bu turda islenecek
site: 0`. Yazılan şey, çalıştırılması imkânsız bir kod yolu olacaktı.
Ayrı ve **hafif** bir tur eklendi (`menu_pdf_tara.py sosyal`): menü
bağını takip etmiyor, PDF indirmiyor, yalnız sayfayı açıp `<a href>`
okuyor, ve kendi günlüğüne bakarak yarıda kalırsa devam ediyor.
Kontrol artık bunu da sınıyor — "toplama çalıştırılabilir mi" sorusu,
"toplama doğru mu" sorusundan önce geliyor.

Bu iş `sosyal_adi`'da ölçülmüş bir kusur da açığa çıkardı: alt alan
adları tek tek yazılıydı (`m.`, `web.`, `mobile.`, `music.`) ve listede
olmayan **`tr-tr.facebook.com` reddediliyordu** — Türkiye'deki
işletmelerin en sık kullandığı biçim. Bugünkü veride bir kayıt, ama site
taramasında en yaygın olan o olacaktı. Artık herhangi bir alt alan
geçiyor; alan adının kendisi yine tam eşleşiyor, yani
`instagram.com.saldirgan.net/x` geçmiyor ve `facebook.com/x` hâlâ bir
Instagram kullanıcısı sayılmıyor.

Kontrol **davranışla** yazıldı: `site_isle` taklit bir sayfayla koşuluyor
ve yazdığı CSV okunuyor. Beş sabotajın beşi de yakalandı — ama üçüncüsü
**ilk denemede kaçtı**: taklit sayfadaki paylaşım bağı `facebook.com`
sayıldığı için gerçek bağla aynı platforma düşüp tekilleniyordu. Düzeltme
düzeneği değil **kurguyu** değiştirdi: paylaşım bağları artık gerçek
bağlardan önce geliyor ve Twitter yalnız paylaşım bağı olarak var.

### Kontrollerin kendi kusurları (yine ikisi sabotajla çıktı)

- **"telifinde" araması gevşekti.** Kullanıcıya görünen cümle silindiği
  hâlde kontrol geçti: aynı kelime bölümün üstündeki **HTML yorumunda**
  da geçiyor. Gizlilik tablosunda tam olarak bu olmuştu. Artık yorumlar
  silinerek aranıyor.
- **"Yol tarifi koordinata gidiyor mu" araması kendi kendini
  doğruluyordu.** Aranan dizgi (`maps/dir/?api=1&destination=`)
  `ortak.js`'in *kendi kontrol bloğunda* beklenen değer olarak da
  duruyor; tabanı aramaya çevirdiğimde kontrol yine geçti. Artık
  `DIS_HARITA`'daki `yol` kaydının kendi tabanına bakılıyor.
- **İşaret haritanın DIŞINDA çiziliyordu ve kontrol bunu göremedi.**
  Harita "Bilgi" sekmesinin ardında kuruluyor; o grup `display:none`
  olduğu için Leaflet kabı **0×0** ölçüyor ve merkezi ona göre
  hesaplıyor. Ölçüldü: kutu `16,403 358×220` iken işaret `8,395` — yani
  sol üst köşenin dışında, ekranda boş bir harita. Kontrolün ilk hali
  `path` **sayıyordu**, yerine bakmıyordu: "işaret var" diyordu, "doğru
  yerde" demiyordu. Artık işaretin merkezi kutunun merkeziyle
  karşılaştırılıyor (sapma > 4 px hata). Düzeltme sekme açılınca
  `invalidateSize()` çağırmak; sabotajla doğrulandı, sapma 557 px.
- **Haritasız hâl kontrolü olmayan bir menüyü arıyordu.** Seçtiğim mekan
  (Draft) menüsüz ve kontrol "Leaflet yokken menü de çizilmiyor" diye
  patladı — kod değil kontrol yanlıştı. Menüsü *ve* Instagram'ı olan bir
  mekana geçildi; artık "harita gitti, geri kalan duruyor" gerçekten
  ölçülüyor.
