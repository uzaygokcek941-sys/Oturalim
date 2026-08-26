# Kalan işletmelerin verisini nasıl çekeriz, ve bundan nasıl para kazanılır

**Bağlam:** `PAZARLAMA.md`'nin B2 kararı — *genişlik değil derinlik*. Bu
belge o kararın veri tarafı: 35.852 mekanın **293'ünde** fiyat var (%0,82)
ve kalan 35.559'un fiyatı, adresi, menüsü, hesabı nereden gelecek.

> **CLAUDE.md yok.** Depoda ve bu makinede arandı, bulunamadı (ikinci kez).
> Yöntem yine deponun kendi kurallarından alındı: *ölçmeden tasarlama* ·
> *yanlış fiyat fiyatsızlıktan kötüdür* · *aynı kural tek yerde dursun* ·
> *başarısızlığı ölçüme çevirme*. Elinde bir `CLAUDE.md` varsa ver, planı
> onun üzerine yeniden kurayım.

---

## 0 — Bugünkü doluluk (81 il dosyasından sayıldı)

| Alan | Dolu | Oran |
|---|---|---|
| Koordinat | 35.852 | %100 |
| Mutfak | 10.075 | %28,1 |
| **Adres** | 9.397 | **%26,2** |
| Telefon | 3.884 | %10,8 |
| Saat | 3.693 | %10,3 |
| Site | 2.812 | %7,8 |
| **Sosyal hesap** | 304 | **%0,8** |
| **Menü fiyatı** | 293 | **%0,82** |

---

## 1 — Fiyat ve menü

### 1.1 Bekleyen OCR kuyruğu — en hazır kaldıraç

`menu_pdf_bulgu.csv` içinde **422 satır**, **283 tekil mekan**, **233
tekil kaynak** şu iki etiketi taşıyor ve **hiç işlenmemiş**:

```
pdf-ocr-gerekli      224
gorsel-ocr-gerekli   198
```

Bunları okuyacak araç **var ve doğruluğu ölçülmüş**: `menu_ocr.py`, kendi
başlığında *"Güney Yıldızı'nın menu.jpeg'i 8/8 doğru okundu, fiyatlar
görselle elle karşılaştırıldı"* diyor. `tam` kipi de var. Bugüne kadar
yalnız `pilot` koşulmuş: `menu_ocr_kalem.csv` **8 satır, 1 mekan**.

**Yani doğrulanmış bir okuyucu, 283 mekanlık bir kuyruğun başında bekliyor.**

    python menu_ocr.py tam

**`tam`'ın kendi süzgeçlerinden sonra ne işleyeceği ölçüldü:**

    ham OCR işaretli satır      422
    şablon sayılıp atlanan       18   (aynı görsel 8 mekana atanmıştı)
    menu_ocr.py'nin adayı       363   (236 tekil mekan)
    işlenmiş                      1
    `tam` bu turda işleyecek    362   (235 tekil mekan)

Tavan: 293 → ~528 mekan (%0,82 → ~%1,5). Gerçek verim OCR'ın kaç menüyü
okuyabildiğine bağlı ve **ölçülecek**, uydurulmayacak.

Betik ölçek için hazır: aynı görseli birden çok mekana atanmışsa şablon
sayıp atlıyor, işlenmiş kaynakları atlayıp kaldığı yerden devam ediyor.
**Eksik olan tek şey `NVIDIA_API_KEY`** — bu makinede ne ortam
değişkeninde ne `.env`'de var.

**İnsan doğrulaması kalkmıyor.** OCR çıktısı doğrudan yayına girmiyor;
5 uydurma vakası ölçülmüştü (bir mekanda sıra numaraları fiyat sanılmıştı).
Kural yerinde kalıyor.

### 1.2 JavaScript ile basılan siteler — ❌ **ÖLÇÜLDÜ, HİPOTEZ ÇÜRÜDÜ**

Hipotez şuydu: `tr_menu_ozet.csv`'de 2.476 site denenmiş, 182'sinde kalem
çıkmış (%7,4); kalanların **2.294'ü `js`** ve `menu_topla.py` sunucunun
ilk HTML'ine baktığı için onları göremiyor. Gerçek tarayıcı açsa
okunurdu.

**GitHub koşucusunda 40 alan adıyla denendi:**

```
Aday alan adi     : 40
robots.txt atladi : 0
Denenen           : 40
Kalem cikan       : 0 (%0,0)
Hata              : 7
Toplam kalem      : 0
```

**Sıfır.** Planın kendi kuralı "verim %10'un altındaysa tam tarama zaman
kaybı" diyordu; 0% çok altında. Tam tarama **yapılmayacak**.

**Sebebi de ortaya çıktı, ve daha önemli:** `menu_pdf_tara.py` bu işi
**zaten yapıyor ve daha iyi yapıyor**. O betik siteyi gerçek tarayıcıda
açıyor *ve menü bağlantısını takip ediyor* (`MENU_BAGI` ile `<a>`
metinlerinde "menü/fiyat/sipariş" arıyor). Benim yazdığım betik yalnız
**ana sayfayı** okuyordu — bir restoranın ana sayfasında fiyat nadiren
yazar.

`menu_pdf_tara.py` 1.974 mekanda koşmuş ve sonucu şu:

| durum | satır |
|---|---|
| menu bulunamadi | 1.552 |
| erisilemedi | 691 |
| pdf-ocr-gerekli | 224 |
| gorsel-ocr-gerekli | 198 |
| pdf-menu-degil | 53 |
| pdf-metin | 8 |
| sayfa-metin | 2 |

Yani hipotez **zaten sınanmıştı** ve cevabı buradaydı: sitelerin
çoğunda okunabilir bir menü metni yok; olanların büyük kısmı **görsel
veya PDF** — ve o da 1.1'deki OCR kuyruğu.

**Sonuç: `menu_tarayici.py` silindi.** Gereksiz ve zayıftı; deponun
"aynı kural tek yerde dursun" kuralına da aykırıydı. Getirdiği tek
gerçek iyileştirme — **`robots.txt` kapısı** — `menu_pdf_tara.py`'ye
taşındı, çünkü asıl ağır ziyareti o yapıyor (siteyi tam çalıştırıyor,
menü sayfasına geçiyor, PDF/görsel indiriyor) ve kapısı yoktu.

> Bu, planın en büyük kalemiydi ve **yanlıştı**. Ölçüm olmasa iki saatlik
> bir tarama koşulacak ve hiçbir şey çıkmayacaktı.

### 1.3 Zincir yayılımı — sayıyı büyütür, ÖLÇÜMÜ BÜYÜTMEZ

Ölçüldü: fiyatı olmayan mekanlardan **204'ünün adı**, fiyatı olan bir
mekanın adıyla eşleşiyor (13 zincir; Domino's 74, Kahve Dünyası 51,
Yemen Kahvesi 29…). `marka()` seviyesinde eşleştirilse **226 mekan**.
Yani 293 → ~500, %0,82 → ~%1,4.

**Bu yapılmayacak, ve sebebi kodun içinde yazılı.** `app_veri.py:348`:

> *"Anahtar (il, mekan adi) — sadece ada bakmak yetmez: zincir adlari
> illerde tekrar ediyor ve Istanbul'daki subeye Ankara'nin fiyatlari
> yapisir."*

204 eşleşmenin **198'i başka bir ilde**. İl sınırını kaldırmak, tek bir
kazımayı 198 kez daha saymak olurdu — `ortak.js`'in kendi ifadesiyle
**"tek fişi mekanın fiyatı saymakla aynı hata"**. Sayı büyür, bilgi
büyümez.

**Gerçek olan tek kısım düzeltildi:** anahtar tam dizgeydi ve OSM'de aynı
mekan iki yazımla duruyordu — `Onur OcakBaşı` / `Onur Ocakbaşı`, `BELTUR`
/ `Beltur`, `karabatak` / `Karabatak`, `pizza bulls` / `Pizza Bulls`.
Anahtar `casefold`'a alındı; **291 → 293 mekan, 7.335 → 7.406 kalem**.
Türkçe harfler **düşürülmüyor** — "Çınar" ile "Cinar"ı aynı saymak iki
ayrı işletmeyi tek zincir yapardı.

### 1.4 Kullanıcı ve işletme — tek ölçeklenen yol

Kazıma tavanı belli: siteleri olan 2.812 mekan, yani %7,8. Kalan %92,2'ye
uzaktan ulaşılamıyor. Menüyü gören iki kişi var:

- **Oradaki kullanıcı** — `menu_katkilari` hattı kurulu (fotoğraf + kalem
  + fiyat → onay → yayın), seviye sistemi teşviki veriyor
- **İşletmenin kendisi** — sahiplenme kodu (`sahiplenme.sql`), 112 Kadıköy
  kartı basılmayı bekliyor

`PAZARLAMA.md` hedefi bunun üstüne kurulu: **Kadıköy 500 m'de 4/474 →
150/474**, elle, yürüyerek. Bir hafta sonu.

### 1.5 Yapılmayacaklar — sınır aynı yerde

Google Maps, Yandex, Yemeksepeti, Getir, TrendyolGo kazınmıyor. Telif
gerekçesi `CEBIMDE.md`'de yazılı ve kapı kodda: `app_veri.platform_mu`.

**Bu turda o kapıda bir açık bulundu ve kapatıldı.** Kapı yalnız `m.` ve
`mobile.` öneklerini tanıyordu; platformların **dil alt alanları**
geçiyordu — ölçüldü: `tr-tr.facebook.com` ve `tr.foursquare.com`
işletmenin kendi sitesi sayılıyordu. Ayrıca **`restaurantguru.com` hiç
listede yoktu: 17 kayıt.** Bir işletme rehberinden menü almak, Google
Maps'ten almakla aynı şey.

Veri o an değişmedi (o 21 mekanın zaten menüsü yoktu). Kapı **ileride**
önemliydi: `menu_pdf_tara.py` tam da o yığını tarıyor ve
restaurantguru'yu kazıyacaktı.

---

## 2 — Adres

Adresi olan mekan **9.397 (%26,2)**. Üç kaynak, maliyet sırasına göre:

### 2.1 Bedava: okunmayan OSM etiketleri ✅ **YAPILDI**

Adres şu an **iki** etiketten kuruluyor (`turkiye_cek.py`, `mekan_isle.py`):

```python
adres = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
```

Ham OSM çıktısında (`cankaya_osm_raw.json`, adı olan 844 kayıt) **inen ama
atılan** etiketler:

| etiket | kayıt | durum |
|---|---|---|
| addr:city | 112 | atılıyor |
| addr:postcode | 106 | atılıyor |
| addr:housename | 15 | atılıyor |
| addr:country / unit / province / floor | 10 | atılıyor |

**Ölçüm düzeltildi.** İlk hesap "+5,6 puan" diyordu ve `addr:city` ile
`addr:postcode`'u da sayıyordu. İkisi de **tek başına adres değil**:
şehir zaten `il` sütununda duruyor, posta kodunu adres diye yazmak
"06450" satırını adres sanan kullanıcıya hiçbir şey söylemez. **Adres
boşluğunu kapatmış gibi görünüp kapatmamak, boş bırakmaktan kötü.**

Gerçekten eklenebilecek tek etiket **`addr:housename`** (15 kayıt):
"Armada AVM" bir adres ifadesidir ve sokak adı olmayan bir kayıtta
kullanıcının elindeki tek tarif o olabilir. Ölçüldü:

    sokak+no ile adres : 230 / 844  (%27,3)
    + bina adı         : 243 / 844  (%28,8)   → +1,5 puan

**Yapıldı:** `turkiye_cek.py` ve `mekan_isle.py` sokak+no yoksa bina
adına düşüyor. Sorgu değişmedi — `out center tags` bu etiketi zaten
indiriyordu. **Etki bir sonraki çekimde görünür.**

### 2.2 Bedava ve zaten elimizde: ilçe/mahalle sütunları

**Bu, ölçümün en şaşırtıcı bulgusu.** `turkiye_mekanlar.csv` şunları
taşıyor:

| sütun | dolu | oran |
|---|---|---|
| ilce | 7.245 | %20,1 |
| mahalle | 4.015 | %11,1 |

**İkisi de uygulamaya hiç ulaşmıyor** — `app_veri.py` ve `veri_bicim.py`
"mahalle" kelimesini hiç içermiyor (grep: 0). Mahallesi olup adresi
olmayan **392 kayıt** var: *"Cemalpaşa, Seyhan"* yazılabilecekken hiçbir
şey yazılmıyor.

⚠️ **Bu, ekrandaki bir cümleyle çelişiyor.** `ortak.js` ve `isletme.html`
şunu diyor: *"Mahalle adı yok çünkü veride yok: 35.852'nin 9.397'sinde
adres var ama içinde ayrıştırılabilir mahalle adı geçen 49 tane (%0,14)."*
O cümle **adres metninden ayrıştırma** hakkında ve doğru. Ama `mahalle`
**sütunu** 4.015 kayıt taşıyor — 80 katı. Cümle yanlış değil, artık
yanıltıcı: elimizde olan bir şeyi "yok" diye anlatıyor.

**✅ YAPILDI.** `ilce` ve `mahalle` boru hattına alındı; işletme
sayfasının başlık altı satırında ve Bilgi listesinde, keşfet detay
panelinde görünüyor. Kural tek yerde: `ortak.js → semtYaz()`.

Uygulamaya inen sayı: **ilçe 7.195 (%20,1), mahalle 3.788 (%10,6)**.
Adresi olmayan 26.455 kayıttan **883'ü (%3,3)** ilk kez bir yer adı
kazandı: *"Üniversite · Avcılar · İstanbul"* — önceden yalnız
*"İstanbul"* yazıyordu.

Değer temizliği yapıldı (`app_veri.semt_adi`), ve ölçümle:

- **63 ilçe** yalnız büyük/küçük harf yüzünden ikiye bölünüyordu
  (`merkez`/`Merkez`). `"istanbul".title()` Python'da `"Istanbul"`
  veriyor — Türkçe tablo şart.
- **211 mahalle** farklı yazımlarla duruyordu (`Cumhuriyet` /
  `Cumhuriyet Mah.` / `Cumhuriyet Mahallesi` / `Cumhuriyet mah.`).
  1.397 ham değer → 1.133. **Sonek atılıyor, eklenmiyor**: 611 değerde
  zaten yok ve "Mahallesi" eklemek uydurmak olurdu.
- **3 kayıtta birleşen nokta** (U+0307) vardı — `"İ".lower()` Python'da
  tek harf değil ve NFC geri birleştirmiyor.
- **197 değer elendi**: biri mahalle sütununa kaçmış tam bir adresti
  (*"Büyükkumla, ARMUTLU YOLU ÜZERİ NO:220 A, 16600 Gemlik/Bursa"*).

`ortak.js`'teki "mahalle adı veride yok" cümlesi de düzeltildi: o ölçüm
**adres metninden ayrıştırma** hakkındaydı ve hâlâ doğru, ama artık
yanıltıcıydı. Civar kutusunun başlığı yine yarıçap diyor — *"Suadiye'de
55 mekan"* demek elimizde olmayan bir sınırı iddia etmek olurdu.

### 2.3 Pahalı: binanın adresi

POI'nin içinde durduğu binanın `addr:*` etiketi OSM'in kendi iddiası,
çıkarım değil. İkinci bir Overpass sorgusu gerekir:

```
nwr["building"]["addr:housenumber"](area.a); out geom;
```

**`out center` YETMEZ:** merkez koordinatıyla "en yakın bina" eşlemesi bir
çıkarımdır ve bu deponun kapattığı kapıdır. Gerçek nokta-poligon
içindelik testi için `out geom` şart, o da yükü çok büyütür (İstanbul tek
parça gelmez, ilçe ilçe bölmek gerekir).

**Ölçülemedi:** 26.455 adressiz mekanın kaçının `addr:*` taşıyan bir
binanın içinde olduğu bilinmiyor — çekim binaları hiç istememiş ve `ham/`
dizini silinmiş. Cevap ancak yeni bir çekimle gelir. **Bu yüzden 2.3, 2.1
ve 2.2'den sonra gelir.**

### 2.4 Kullanıcı ve işletme

Katkı hattı adresi zaten kabul ediyor (`KATKI_ALAN`), sahiplenmiş işletme
kendi adresini düzeltebiliyor. Ölçekleyen yol bu.

---

## 3 — Sosyal medya hesapları

**Kod hazır, veri eksik.** `turkiye_cek.py` beş platformu okuyor
(`contact:instagram`, `contact:facebook`, `contact:twitter`,
`contact:tiktok`, `contact:youtube`), `app_veri.py` beşini de arıyor
(`sosyal_adi(...)`). Ama **`turkiye_mekanlar.csv`'de yalnız `instagram`
sütunu var** — dosya, diğer dört sütun eklenmeden önceki sürümle
üretilmiş.

Sonuç: sosyal hesabı olan mekan **304 (%0,8)**, hepsi Instagram; Facebook,
X, TikTok, YouTube **sıfır**.

**Yapılacak:** `python turkiye_cek.py` yeniden koşacak. Dört sütun
kendiliğinden dolacak; kod değişikliği yok.

**İkinci kaynak, bedava:** `menu_pdf_tara.py` zaten her işletme sitesini
gerçek tarayıcıda açıyor. Aynı geçişte sayfadaki `instagram.com/…`,
`facebook.com/…` bağlantıları toplanabilir — işletmenin **kendi sitesinde
kendi yayımladığı** bağlantı. Ek istek yok, ek kaynak yok.

---

## 4 — Yorumlar

**Google Maps, Yandex ve Instagram yorumları kazınmıyor. Bu bir eksiklik
değil, karar.** Yorumlar yazarlarının telifinde ve platforma lisanslı;
kopyalayıp yayımlama hakkımız yok. Fotoğraflarda verilen kararın aynısı.

Elimizde olan iki şey:

1. **Cebimde'nin kendi yorumları** — `yorumlar` tablosu, puan + metin,
   profil bağlantılı, `topluluk.html` akışında. Ölçekleyen yol bu.
2. **Kaynağa bağlantı** — işletme sayfasındaki Konum kutusu (bu oturumda
   eklendi) Google'da ara / Yandex'te ara / Instagram düğmeleri veriyor.
   Kullanıcı yorumu **yazarının yayımladığı yerde** okuyor.

Bu tercih ekranda **yazıyor** — sessiz yapılsa "yorumlar nerede" sorusu
cevapsız kalırdı.

---

## 5 — Bu veriden nasıl para kazanılır

`PAZARLAMA.md` B4'teki kilit burada da geçerli: **Faz 0 dururken hiçbiri
kurulamaz** ("şirket: gelir doğana kadar kurulmayacak" → ödeme alınamıyor).
Aşağıdakiler kilidin açılmasından **sonra**, ve zorluk sırasına göre.

### 5.1 İşletme aboneliği — hattı hazır, sayıyı üretiyor

`isletmem.html` paneli çalışıyor ve aboneliği somut yapacak iki sayıyı
üretiyor: **görüntülenme** ve **"bakanlar hangi bütçeyle arıyordu"
dağılımı**. Bir kafe sahibinin bugün hiçbir yerden alamadığı sayı ikincisi:
*"sayfana bakan 40 kişinin 28'i 200-300 ₺ arıyordu."*

Satış cümlesi buradan çıkıyor ve **ölçüme dayanıyor**, vaade değil.

Fiyat: aylık düşük bant (ör. 199-499 ₺). Ölçeği tek başına taşımaz ama
**Faz 0'ı açan ilk gelir** o olabilir.

### 5.2 Doğrulanmış işletme rozeti + menü yönetimi

Sahiplenme zaten var ve **ücretsiz kalmalı** — veriyi doğru tutan mekanizma
o. Ücretli olan üstüne binen şey: menüyü toplu güncelleme, fotoğraf
yükleme kotası, kampanya alanı (md.3'te veri yapısı var).

### 5.3 Veri hizmeti — en yüksek marj, en yüksek risk

Fiyat kapsaması anlamlı bir seviyeye çıkarsa (bir ilçede %30+), o veri
**enflasyon ölçümü** için değerli: yerel gıda fiyat endeksi, aylık sepet
karşılaştırması. Alıcı: araştırma şirketleri, basın, belediyeler.

**İki şart, ikisi de sert:**
- Veri **ODbL** (OpenStreetMap) türevi — paylaş-benzer-lisansla yükümlülüğü
  var; satılan şeyin ne olduğu hukukçuya sorulmadan yapılmamalı
- Kullanıcı katkısı satılıyorsa **kullanıcıya söylenmeli**; gizlilik
  metni bugün bunu vaat etmiyor

### 5.4 Yapılmayacak: sponsorlu sıralama

Bütçe dürüstlüğü satan bir uygulamada sıralamayı satmak, satılan şeyin
kendisini bozar. `PAZARLAMA.md`'de de yazılı.

---

## 6 — Sıra

Maliyet ve hazır olma durumuna göre:

| # | İş | Maliyet | Beklenen | Durum |
|---|---|---|---|---|
| 1 | `python menu_ocr.py tam` | koşum + API anahtarı | **362 kaynak / 235 mekan** | araç hazır; `NVIDIA_API_KEY` gerekiyor |
| ~~2~~ | ~~Tarayıcıyla JS menüleri~~ | — | **0/40 (%0,0)** | ❌ **ölçüldü, çürüdü** |
| ~~3~~ | ~~Tam tarama~~ | — | — | ❌ 2'nin sonucu |
| 4 | `python turkiye_cek.py` | koşum | 4 sosyal sütun | kod hazır |
| ~~5~~ | ~~`ilce`/`mahalle` boru hattına~~ | — | **7.460 mekan (%20,8)** | ✅ **yapıldı** |
| ~~6~~ | ~~OSM `addr:housename`~~ | — | +1,5 puan (sonraki çekimde) | ✅ **yapıldı** |
| 7 | **Kadıköy 500 m elle derinleştirme** | 1 hafta sonu | 4/474 → 150/474 | `PAZARLAMA.md` Faz A |
| 8 | Saha kartları (112 Kadıköy) | baskı | işletme sahiplenmesi | senin onayın |
| 9 | Bina adresi (Overpass `out geom`) | büyük | ölçülmedi | 6'dan sonra |
| 10 | Gelir hattı | **Faz 0 kararı** | — | senin kararın |

**1, 2 ve 4 bugün koşulabilir ve kod tarafında hiçbir şey beklemiyor.**
