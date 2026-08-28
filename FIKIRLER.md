# Fikirler — 28 Ağustos 2026 incelemesinden

Bu dosya `PAZARLAMA.md` ve `VERI_VE_GELIR.md`'nin devamı. Oradaki
kararları tekrarlamıyor; **yayındaki uygulamayı gezdikten sonra** ortaya
çıkan yeni fikirleri yazıyor. Her fikrin yanında ölçülmüş bir sayı var —
tahminle yazılan tek satır yok.

---

## Önce: incelemenin sonucu

**Yayın temiz.** `canli.yml` → `incele: true`, 28 Ağustos 13:56:

| | |
|---|---|
| Sayfa | 16 / 16 → HTTP 200 |
| JS hatası | 0 |
| CSP ihlali | 0 |
| 404 | 0 |
| Yatay taşma (320/390/768) | yok |
| Süre | 537–1.304 ms |

Rapordaki tek "44 px" satırı `#butce-girdi` ve o **ihlal değil** — saran
`<label>` 54×277 ve `for=` taşıyor; daha önce ölçülüp elenmişti.

**Bulunan tek gerçek kusur benimdi** ve kapatıldı: `bayi.html` girişsiz
kullanıcıyı düz `giris.html`'e yolluyordu. `?donus=` parametresi zaten
vardı ve `guvenliDonus()` ile denetleniyordu; ben yanlış adla (`?sonra=`)
aramış, bulamayınca "yok" diye yorum yazmıştım. Bayi giriş yapıp
`hesabim.html`'e düşüyordu.

Ayrıca 64 kartın QR hedefi tek tek doğrulandı: **64/64** il dosyasında
var, adlar birebir tutuyor, konumu olmayan yok.

---

## Ölçülen üç sayı — fikirlerin hepsi bunlardan çıkıyor

### 1. İstanbul keşfet, ilk sayfa: 120 kart, **0 tanesinde fiyat**

Canlı raporun kendi satırı. Oysa İstanbul'da **191 fiyatlı mekan var** —
sadece ilk sayfaya düşmüyorlar, çünkü varsayılan sıralama A → Z.

`PAZARLAMA.md` B1'in "en kritik rakam" başlığı tam da bunu anlatıyor:
*"telefonu eline alıp açarsa, hiçbir şey göremez."* Bugün bu, veri
eksikliğinden değil **sıralamadan** oluyor.

### 2. Ankara: 2.360 mekan, 6 menü (%0,25), ve %82,5'i uzaktan ulaşılamaz

| Alan | Mekan | Oran |
|---|---|---|
| adres | 497 | %21,1 |
| saat | 278 | %11,8 |
| telefon | 215 | %9,1 |
| web | 191 | %8,1 |
| instagram | 173 | %7,3 |
| **menü** | **6** | **%0,25** |

**1.948 mekanda (%82,5) ne telefon, ne web, ne Instagram var.** Bu
sayı bayiliğin ve saha kartının tek gerekçesi: o mekanlara ulaşmanın
başka yolu yok.

Menüsü olan 6 mekanın kişi başı medyanı **281 ₺**.

### 3. 62 / 81 ilde tek bir menü yok

| İl | Mekan | Menülü | Oran |
|---|---|---|---|
| İstanbul | 12.095 | 191 | %1,58 |
| Kocaeli | 1.053 | 19 | **%1,80** ← en iyi |
| İzmir | 2.309 | 16 | %0,69 |
| Antalya | 3.322 | 17 | %0,51 |
| Ankara | 2.360 | 6 | %0,25 |
| Tekirdağ | 1.314 | **0** | %0,00 |

---

## Fikirler, etki/maliyet sırasıyla

### F1 — Varsayılan sıralama: "Bilgisi olan önce" ★ en yüksek etki, en düşük maliyet

**Sorun:** İstanbul'da ilk 120 kartın 0'ında fiyat var. 191 fiyatlı mekan
listede, ama 5. sayfada.

**Fikir:** Konum yokken varsayılan sıralama A → Z değil, **bildiğimiz
kadarına göre** olsun: fiyat > menü > fotoğraf > saat > telefon.
"Önce ucuz" seçeneği zaten fiyatsızları sona atıyor (`yemekFiyati` null →
`Infinity`), yani mekanizmanın yarısı kurulu.

**Neden dürüst:** hiçbir mekan gizlenmiyor, sıra değişiyor. Deponun kendi
kuralının aynısı: *boş bir harita, küçük ama dolu bir haritadan kötüdür.*

**Neden şimdi:** 8 Aralık'ta telefonu birine uzattığında ilk ekranın dolu
olması, sekiz haftalık saha çalışmasından daha hızlı geliyor. Veri
üretmiyor ama **var olan veriyi görünür kılıyor.**

**Uyarı:** "Bana yakın" seçildiğinde bu sıralama devreye girmemeli —
orada kullanıcının istediği şey mesafedir. Karar senin, çünkü A → Z
tarafsız bir sıra; bu değil.

---

### F2 — "Kapsama" sayfası: kötü sayıyı kendin yayınla

**Fikir:** `hakkinda.html` yanına bir **Kapsama** sayfası: il il mekan
sayısı, menü sayısı, oran; ve en üstte tek cümle — *"35.852 mekanın
293'ünde fiyat var. %0,82. Bunu büyütmenin tek yolu sen."*

Veri zaten hesaplanıyor; `vitrin_uret.py` gibi bir üretici yeter.

**Neden prestij:** bu sektörde hiç kimse kendi kapsamasını yayınlamıyor.
Google Maps de, Yemeksepeti de "kaç mekanın fiyatını bilmiyoruz"
demiyor. `PAZARLAMA.md` B5 zaten "bunları söyle" diyor — bu, o listeyi
pitch'ten **ürüne** taşımak.

**İkinci faydası savunma:** "uygulamanız boş" itirazını sen önce
söylersen, itiraz olmaktan çıkıp yöntem oluyor.

---

### F3 — Talep açığı: kimsenin üretemediği tek sayı

**Elimizdeki benzersiz varlık:** `mekan_butce_talebi` — *"sayfana bakan
40 kişinin 28'i 200-300 ₺ arıyordu."* Sunucuda k-anonimlik eşiği var
(5 bakış), yani tek kişi ifşa olmuyor.

**Fikir:** bunu mekan düzeyinden **ilçe düzeyine** toplayıp yayınla:

> Çankaya'da arayanların %X'i 200-300 ₺ arıyor.
> Menüsü bilinen mekanların medyanı **281 ₺**.

**Neden kimse yapamıyor:** Google ve Yemeksepeti fiyatı biliyor ama
**arayanın bütçesini** yayınlamıyor — o veri onların reklam ürünü.
Cebimde'de bütçe zaten ürünün girdisi.

Bu, 8 Aralık'ta gösterilecek slayt. Bugün kullanıcı yok, o yüzden sayı
da yok — ama **mekanizma kurulu**, eksik olan yalnız toplama ve sayfa.

---

### F4 — Cebimde Fiyat Endeksi (aylık, ilçe bazlı)

**Fikir:** onaylanmış fişlerden aylık, ilçe bazlı bir yerel fiyat
endeksi. `VERI_VE_GELIR.md` §5.3 bunu **gelir** fikri olarak yazıyor;
buradaki öneri farklı — **gelir değil, itibar ve katkı motoru.**

**Asıl kazanç katkı tarafında.** Bugün fiş paylaşmanın gerekçesi *"bir
sonraki kişi kazık yemesin"* — özel bir iyilik. Endeks varken gerekçe
şuna dönüşüyor: *"senin fişin ilçenin fiyat endeksine giriyor."* Özel
iyilik yerine **kamusal fayda**; ikincisi çok daha güçlü bir çağrı.

**Sert şartlar, üçü de:**
- Yöntem açık yayınlanmalı (kaç fiş, kaç kişi, hangi ilçe)
- k-anonimlik eşiği fişte de geçerli (`FIS_ESIK = 3`)
- **Resmî bir endeks olduğu asla ima edilmemeli.** "Cebimde
  kullanıcılarının paylaştığı fişlerden" — bu cümle her yerde durmalı.

---

### F5 — Öğrenci bayiliği: bugün kurduğumuz sistemin doğal ilk kadrosu

**Bugün `BAYILIK.md` kuruldu** ve ilk bayi kadrosu için Ankara'da hazır
bir havuz var: ODTÜ, Hacettepe, Bilkent, Ankara Üniversitesi.

**Neden tam oturuyor:**
- Öğrenci **hedef kullanıcının kendisi** — "cebindeki bütçeyle keşfet"
  cümlesi en çok ona hitap ediyor
- Mahalleyi biliyor, yürüyor, ve hakediş küçük olsa bile anlamlı
- Bir fakülte caddesi = yürüme mesafesinde yoğunluk, yani
  `PAZARLAMA.md` B2'nin **derinlik** kararının birebir uygulaması

**Ölçü:** bir kampüs caddesinde bir hafta sonu. Hedef, Kadıköy hedefinin
aynısı: o caddede fiyat kapsaması %30+.

Hakediş zaten koda bağlı, beyana değil — yani öğrenci bayiyi denetlemek
diye bir iş yok, sistem kendi ölçüyor.

---

### F6 — Kartın metnini değiştir (bir sonraki parti için)

Bugünkü kart *"Sizde eksik görünen: açılış-kapanış, telefon, menü
fiyatı…"* diyor. Bu, işletmeciye **onun eksiğini** söylüyor.

**Fikir:** işletmecinin **kazancını** söyle. Elimizde onun hiçbir yerden
alamayacağı bir sayı var (F3):

> Sayfanı kaç kişi gördü ve **hangi bütçeyle arıyorlardı** — panelinde
> yazıyor.

Basılmış 64 kart aynen dağıtılsın; bu, 3. parti için.

---

## Bilerek listeye alınmayanlar

| | Neden |
|---|---|
| Sponsorlu sıralama | `VERI_VE_GELIR.md` §5.4 — satılan şeyin kendisini bozar |
| Maps / Yandex / YS / Getir / TrendyolGo kazıma | Yapılmayacaklar listesi |
| Zincir yayılımı | Ölçüldü: sayıyı büyütür, **ölçümü büyütmez** |
| Şirket kurma | 28 Ağustos B4 kararı |
| Tarayıcıyla JS menüleri | Ölçüldü, hipotez çürüdü (0/40) |

---

## Sıra önerisi

| # | Fikir | Maliyet | Kim yapar |
|---|---|---|---|
| 1 | F1 varsayılan sıralama | küçük | ben, senin kararınla |
| 2 | F2 Kapsama sayfası | küçük | ben |
| 3 | F5 öğrenci bayiliği | bir hafta sonu | sen |
| 4 | F3 talep açığı | orta — **kullanıcı gerekiyor** | ben, kullanıcı gelince |
| 5 | F4 fiyat endeksi | orta — **fiş gerekiyor** | ben, fiş gelince |
| 6 | F6 kart metni | 3. partide | ben |

**1 ve 2 bugün yapılabilir ve hiçbir şey beklemiyor.** 3 senin
takvimine bağlı. 4 ve 5 kullanıcı sayısı sıfırdan çıkmadan anlamsız —
ama ikisinin de mekanizması bugün kurulu, eksik olan yalnız veri.
