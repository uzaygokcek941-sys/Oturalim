# Faz 2 — Storyboard

## Site geneli sinematik dilbilgisi

**Kabuk mantığı — AÇIKLIK (aperture).** İçerik her zaman bir açıklıktan görünür:
kapı aralığı, vitrin camı, tezgâh penceresi. Kart değil, çerçeve. Çerçevenin
dışı sokaktır ve daha karanlıktır.

**Gezinti duruşu.** Üstte ince bir şerit — dükkân tentesi / neon tabela hissi.
Yüzer kutu değil, mekâna ait bir eleman.

**Çerçeveleme kuralı.** İçerik ekran kenarından içeri çekilir. Kenarda kalan
karanlık şerit "dışarısı"dır ve boş bırakılmaz — ışık izleri oradan geçer.

**Yoğunluk temposu.** Kalabalık ↔ boş. Film sürekli bunu yapar: kaotik kalabalık
çekimi, ardından tek kişilik sessizlik. Sayfada da yoğun bölümün ardından nefes.

**Tekrarlayan malzemeler.** Neon sızıntısı (renkli halo), ıslak asfalt parlaması
(dar açılı speküler geçiş), film grenı, hareket izi (smear).

**Kompozisyon ailesi: KORİDOR.**

## Kalibrasyon — ana sayfa

**Tek büyük fikir.** *Kapı aralığında duruyorsun. Sokak önünden akıp geçiyor.
Bir kapı duruyor.*

**Sahne tezi.** Ana sayfa filmin açılış sahnesi: henüz aramıyorsun, sokağa
bakıyorsun. Karar anı.

**Kahraman hâkimiyeti.** Kahraman pahalı hissettiriyor çünkü **hareket eden
şey sen değilsin, dünya**. Işık izleri sürekli akıyor; imleç birincil düğmeye
yaklaştığında akış yavaşlıyor ve netleşiyor. Gradyan değil, mekanizma.

**Kısıtlama beyanı.** Yapmayacaklarım: cam efekti (glassmorphism), mor-mavi
gradyan, ortalanmış kahraman + altında kutu, her bölümde farklı yeni fikir,
imleç takip eden top, sayı sayacı animasyonu.

**Malzeme tezi.** Yüzeyler cam değil **ıslak**. Parlaklık geniş ve yumuşak
değil, dar ve keskin — asfalttaki neon yansıması gibi. Üstünde grain var,
çünkü film 35 mm ve el kamerası.

**Tipografi tezi.** Fraunces zaten opsiyonel optik boyut taşıyor; büyük
boyutta yüksek kontrastlı kesim, küçük boyutta okunur kesim. Otoriteyi
büyüklükten değil **sıkı harf aralığı + geniş satır boşluğu** çelişkisinden
alıyor. Karla gövdede kalıyor.

**İmza kompozisyonu.** Çerçeve **merkezde değil** ve ışık izleri çerçevenin
kenarından taşıyor. Böylece ortalanmış bir kart olarak okunamaz.

**Izgara düşüş testi.** Bu sayfa 3 sütunlu karta indirgenirse kaybolan şey:
"dışarısı" kavramı. Çerçeve ancak dışarısı varsa çerçevedir. Kart ızgarasında
dışarısı yoktur, her şey eşit mesafede durur — sayfanın tek fikri ölür.

**Paylaşılan sistem beklemesi.** Buton, kart, rozet ve form stilleri ana sayfa
ve keşfet kompozisyonları kilitlenene kadar yazılmayacak.

## Palet — filmden çekilen

Araştırma sarı ve yeşilin baskın olduğunu söylüyor. Mevcut turuncu vurgu
korunuyor (marka), yanına filmin iki rengi giriyor:

| Token | Koyu | Rol |
|---|---|---|
| `--neon-sari` | `#ffd24a` | Büfe tabelası, birincil ışık |
| `--neon-yesil` | `#4ad9a0` | Karşı ışık, "açık" durumu |
| `--vurgu` | `#f08a3c` | Mevcut marka turuncusu, eylem |
| `--asfalt` | `#0d0a08` | Çerçeve dışı, sokak |

Sarı ve yeşil **yan yana kullanılmaz** — filmde de karşı karşıya durur, biri
öndeyken diğeri arkada kalır.

## Giriş haritası — ana sayfa

En az 4 farklı giriş, `fadeUp` en fazla 2 kez. Kullanılan: **0 kez**.

| # | Bölüm | Kamera | Kütüphane |
|---|---|---|---|
| 1 | Kahraman | Rack focus reveal — bulanıktan nete | `camera-shots-50 #6` |
| 2 | Sayılar şeridi | Jump cut stagger — Godard, sıralı sıçrama | `camera-shots-50 #20` |
| 3 | Tür/kategori | Curtain wipe — yatay perde | `camera-shots-50 #10` |
| 4 | Vitrin mekanlar | Crossfade overlap — **Wong Kar-wai** | `camera-shots-50 #21` |
| 5 | Kapanış çağrısı | Iris-in — daire açılması | `camera-shots-50 #1` |

Komşu bölümler aynı şekilde girmiyor.

## Etkileşim bütçesi — ana sayfa

**1 ağır (sayfa başına tavan):** Kahramandaki step-printing ışık izi alanı.
JS + `requestAnimationFrame`. İmleç birincil düğmeye yaklaştıkça izler yavaşlar
ve netleşir. Bu sayfanın tek fikrinin motorudur, süs değil.

**2 dikkat çeken açılış (tavan):** Rack focus (kahraman), Iris-in (kapanış).

Geri kalan hareket bunlara tabi: kart hover'ında yakın planı netleştirme
(`#31` tilt-shift akrabası, saf CSS), neon titremesi (`#17`), çıkışta defocus
(`#48` — Wong Kar-wai).

## Kahraman iskeleti

**#18 Framed Viewport** — kütüphanede bu yönetmen için Tier 2, gerekçe
"kapı aralığından çerçeveleme".

- Çerçeve: mimari, kalın, köşesiz — vitrin kasası
- Çerçeve içi: başlık + tek birincil eylem (Yakınımdakileri göster)
- Çerçeve dışı: sokak — akan ışık izleri, grain, ıslak zemin yansıması
- Çerçeve **merkezde değil**, sağa kaçık; izler sol kenardan içeri taşar

Yasaklananlara uyuluyor: tarayıcı/telefon maketi değil, çerçeve kenarı görünür,
çerçeve içeriği örtmüyor.

## Keşfet — ikinci tempo

Filmin iki görüntü yönetmeni var; bu sayfa Doyle değil Lau tarafı: hızlı, keskin,
araç gibi.

**Tek büyük fikir.** *Koridorda yürüyorsun, vitrinler yanından geçiyor.*

**Sahne tezi.** Ana sayfanın sakin bir kopyası değil — burada kullanıcı artık
karar vermiş, arıyor. Sayfa yardımcı olmalı, etkilememeli.

**İmza kompozisyonu.** Liste bir kart ızgarası değil, **koridor**: kartlar sola
hizalı tek sütun, sol kenarda mesafeyi gösteren dikey bir cetvel, kart üstüne
gelince o kart netleşip hafifçe öne çıkarken **komşuları bulanıklaşır**
(step-printing'in doğrudan uygulaması, `camera-shots-50 #31`).

**Izgara düşüş testi.** Kart ızgarasına indirgenirse kaybolan: mesafe hissi.
Koridorda 110 m ile 680 m arasındaki fark yürünen bir mesafedir; ızgarada
hepsi eşit uzaklıkta durur.

**Kısıtlama.** Burada ağır hareket yok. Ağır etkileşim bütçesi **0**. Neon
titremesi yok, iris yok, perde yok. Yalnız rack-focus ve mesafe cetveli.

## Diğer 7 sayfa

Aynı filmin sessiz sahneleri. Kendi imza kompozisyonlarını Faz 3'te alacaklar;
ana sayfa ve keşfet kilitlenmeden yazılmayacak (paylaşılan sistem beklemesi).
