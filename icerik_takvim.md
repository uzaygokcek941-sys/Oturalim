# 8 haftalık içerik takvimi — 26 Ağustos → 21 Ekim

`PAZARLAMA.md` Faz A'da bir satır var: **"Günde 1 içerik, 40+ içerik."**
`icerik_ilk3.md` ilk üçün çekim notunu veriyor; bu belge kalan 37'yi ve
**hangi sistemle** üretileceğini veriyor.

Fikir listesi değil bir **düzen**: yedi tekrarlanabilir format, haftalık
sabit ritim, her içeriğin arkasında depodan sayılmış bir rakam ve bir de
susma kuralı. 40 ayrı senaryo yazmak boşa emek olurdu — ikinci hafta
biterken hiçbiri plandaki gibi çekilmemiş olur. Düzen ayakta kalır.

---

## Rakamlar (26 Ağustos 2026, `app/veri/`'den sayıldı)

| Ne | Kaç |
|---|---|
| Mekan | **35.852** (81 il) |
| Menü fiyatı bilinen mekan | **293** — yüzde birin altı |
| **Hiç fiyatı olmayan il** | **62/81** |
| Uygulamada gösterilen menü kalemi | **7.406** |
| Kampanya satırı | 672 (96 mekanda) |
| Restoran / Kafe / Fast food | 14.587 / 10.815 / 6.091 |
| Bar / Pub / Müze / Tiyatro | 1.029 / 414 / 761 / 304 |
| Bahçeli / wi-fi | 2.124 / 1.705 |
| Adresi olan | 9.397 (%26,2) |
| Telefon / çalışma saati | 3.884 / 3.693 |
| En kalabalık ilçeler | Fatih 1.780 · Bandırma 644 · Kadıköy 450 |
| En az mekan | Bayburt 3 · Iğdır 3 · Kilis 3 · Bingöl 5 |
| Fiyatın olduğu iller | İstanbul 191 · Kocaeli 19 · Antalya 17 · İzmir 16 · Eskişehir 9 |

Yeniden saymak için:

```bash
python - <<'PY'
import json, io
i = json.load(io.open("app/veri/index.json", encoding="utf-8"))["iller"]
print("mekan", sum(x["n"] for x in i))
print("fiyatli", sum(x["fiyatli"] for x in i))
print("fiyatsiz il", sum(1 for x in i if x["fiyatli"] == 0))
PY
```

Bu tablonun iki satırı manşete çıkacak kadar somut: uygulamada
**7.406 menü kalemi** gösteriliyor ve bunların hepsi **293 mekandan**
geliyor. İkisi birlikte söylenmeli — biri iddia, öteki sınırı.

**Çekimden önce say.** Videoda söylediğin rakam ekranda gösterdiğinle
tutmalı; tutmazsa ilk yorum onu yakalar ve o yorum videodan uzun yaşar.

---

## İki numaralı gerçek: 62 il

Bu takvimin en önemli sayısı 35.852 değil, **62**. Seksen bir ilin
altmış ikisinde tek bir menü fiyatı yok. Bunun içerik için üç sonucu var
ve üçü de bağlayıcı:

1. **"Fiyatları görürsün" diye manşet atılmaz.** Sivas'tan gelen kullanıcı
   ilk on mekanında fiyat görmez ve bir daha açmaz. Bu depodaki kural
   veride olduğu gibi vaatte de geçerli: *yanlış fiyat, fiyat
   olmamasından kötüdür.*
2. **Fiyat gösteren çekimler İstanbul/Kocaeli/Antalya/İzmir/Eskişehir'de
   yapılır.** Fiyatın gerçekten olduğu yer burası.
3. **62 rakamının kendisi içeriktir.** "Boş" demek değil, *"bu boşluğu
   sen dolduruyorsun"* demek — ürünün motoru zaten bu. Kapatılacak bir
   utanç değil, çağrının ta kendisi.

---

## Yedi format

Her format tekrarlanabilir, her birinin arkasında bir kayıt var.

| # | Format | Ne | Neye dayanıyor | Sıklık |
|---|---|---|---|---|
| **F1** | **Fiş** | "X lirayla bir akşam" — her durakta fiş kadrajda | Senin kâğıdın. Veriye hiç bağlı değil, o yüzden en sağlamı | Haftada 1 |
| **F2** | **Kıyas** | Aynı ürün, iki mekan, iki fiyat, ikisi de kadrajda | İki fiş / iki menü | Haftada 1 |
| **F3** | **Ekran** | Tek bir özellik: kaydırıcı, bahçe filtresi, "şu an açık", harita | Uygulamanın kendisi | Haftada 1 |
| **F4** | **Boşluk** | "Bayburt'ta 3 kafe görünüyor. Bu Bayburt'ta 3 kafe var demek değil." | 62/81, Bayburt 3 | 2 haftada 1 |
| **F5** | **Nasıl çalışıyor** | k-anonimlik, üç fiş kuralı, fiyatı kimin yazdığı | `CEBIMDE.md` kararları | 2 haftada 1 |
| **F6** | **Yapmadıklarımız** | Reklam yok, Google Maps kazımıyoruz, sahte yorum yok | `CEBIMDE.md` "Yapılmayacaklar" | 2 haftada 1 |
| **F7** | **Sokak** | Bir sokakta yürü, olduğun yerde uygulamayı aç | Konum + mesafe rozeti | Haftada 1 |

**F1 ve F2 omurga.** İkisi de bir kâğıda dayanıyor, yani veri ne kadar
seyrek olursa olsun çekilebilir ve yanlış çıkamaz. F3–F7 onların arasını
dolduruyor.

---

## Haftalık ritim

Pazartesi–Cuma, günde bir. Hafta sonu çekim, hafta içi yayın.

| Gün | Format | Neden |
|---|---|---|
| Pzt | **F3 Ekran** | Haftaya ürünle başla; en kolay çekilen, en kolay ertelenmeyen |
| Sal | **F2 Kıyas** | Haftanın en çok paylaşılanı: kıyas tartışma açar |
| Çar | **F1 Fiş** | Hafta sonu çekilmiş, ortada yayınlanır |
| Per | **F4/F5/F6 dönüşümlü** | Güven günü: nasıl çalıştığını ve neyi yapmadığını anlat |
| Cum | **F7 Sokak** | Hafta sonu planı yapan insana, gideceği yerde |

Cumartesi–Pazar çekim günü: haftanın F1 ve F2'si aynı yürüyüşte toplanır.
**Bir hafta boşsa boş geçilir, uydurma içerik konmaz.**

---

## Sekiz hafta

Her satır bir gün. Konu sütunundaki rakam yukarıdaki tablodan geliyor.

### 1. hafta — "bu ne"
| Gün | Format | Konu |
|---|---|---|
| Pzt | F3 | **`icerik_ilk3.md` #3** — 35.852, haritayı Türkiye'ye aç, filtreleri bas |
| Sal | F2 | **`icerik_ilk3.md` #2** — Ankara'da kahve 40 ₺, yüz metre ötede 85 |
| Çar | F1 | **`icerik_ilk3.md` #1** — 200 ₺ ile Çankaya'da akşam |
| Per | F5 | "Fiyatı işletme yazmıyor, giden yazıyor." Üç fiş kuralı |
| Cum | F7 | Bir sokak: telefonu aç, "bana yakın"a bas, mesafe rozetini göster |

### 2. hafta — "gerçekten çalışıyor mu"
| Gün | Format | Konu |
|---|---|---|
| Pzt | F3 | **Bütçe kaydırıcısı.** 300 ₺'de liste, 150 ₺'de liste. Tek özellik |
| Sal | F2 | Aynı zincirin iki şubesi, iki fiyat |
| Çar | F1 | 100 ₺ ile öğle yemeği |
| Per | F6 | **"Google Maps'ten fiyat çekmiyoruz."** Neden: o veri onların ve yazarlarının telifinde |
| Cum | F7 | Kadıköy'de bir sokak (450 mekan) |

### 3. hafta — "kime yarıyor"
| Gün | Format | Konu |
|---|---|---|
| Pzt | F3 | **Bahçe filtresi** — 2.124 mekan. Yaz sonu, hâlâ dışarıda oturuluyor |
| Sal | F2 | Kahvaltı: iki mekan, kişi başı fark |
| Çar | F1 | Öğrenci bütçesi: bir günün tamamı, tek fişte topla |
| Per | F4 | **"62 il."** Neden boş, nasıl dolar — çağrı bu videoda |
| Cum | F7 | Üniversite çevresi bir cadde |

### 4. hafta — "ilk 100 kullanıcı"
| Gün | Format | Konu |
|---|---|---|
| Pzt | F3 | **"Şu an açık"** filtresi — 3.693 mekanda çalışma saati var |
| Sal | F2 | Zincir kahve vs. semt kahvecisi |
| Çar | F1 | Bir hafta sonu, üç durak |
| Per | F5 | **k-anonimlik:** "üç fiş gelmeden ortalama göstermiyorum." Neden |
| Cum | F7 | Sahil / meydan yürüyüşü |

### 5. hafta — "ölçek"
| Gün | Format | Konu |
|---|---|---|
| Pzt | F3 | **Tür filtreleri** — 1.029 bar, 761 müze, 304 tiyatro. Kafe uygulaması değil |
| Sal | F2 | Fatih (1.780) vs. Kadıköy (450): aynı ürün, iki yaka |
| Çar | F1 | 500 ₺ ile bir gün |
| Per | F6 | **"Reklam yok, üyelik yok."** Bugün maliyet 0 ₺/ay — nasıl |
| Cum | F7 | Bandırma (644) veya İstanbul dışı bir ilçe |

### 6. hafta — "Play Store"
| Gün | Format | Konu |
|---|---|---|
| Pzt | F3 | **Uygulama artık Play'de.** Kurulum ekranı, ilk açılış |
| Sal | F2 | Tatlı/dondurma: 395 dondurmacı içinden iki fiyat |
| Çar | F1 | İki kişilik akşam yemeği, tek fiş |
| Per | F4 | **Bayburt 3, Iğdır 3, Kilis 3.** "Bu OSM'de 3 demek" |
| Cum | F7 | Kendi mahallen |

### 7. hafta — "topluluk"
| Gün | Format | Konu |
|---|---|---|
| Pzt | F3 | **"Ödediğini ekle"** akışı baştan sona, ekran kaydı |
| Sal | F2 | Kullanıcıdan gelen ilk iki fiyat — kaynağı söyleyerek |
| Çar | F1 | Takipçi önerisiyle bir mekan |
| Per | F5 | **Fotoğraf ve lisans:** Commons'tan, atıflı. Neden Maps fotoğrafı yok |
| Cum | F7 | Takipçinin seçtiği sokak |

### 8. hafta — "Webrazzi haftası"
| Gün | Format | Konu |
|---|---|---|
| Pzt | F3 | 8 haftanın kapsama grafiği: nereden nereye |
| Sal | F2 | En çok tartışılan kıyası tekrar çek, güncel fiyatla |
| Çar | F1 | 8 haftanın fişlerini masaya diz, toplamı söyle |
| Per | F6 | **"Sahte yorum yok."** Yorum eşiği ve neden var |
| Cum | F7 | **Summit'ten** — pitch değil, birine telefonu uzat ve çek |

---

## Susma kuralları

Bunlar öneri değil; ihlali içeriği geri alınamaz yapıyor.

1. **Fiş yoksa fiyat söylenmez.** F1 ve F2'nin tamamı buna bağlı.
2. **Ekranda olmayan şey anlatılmaz.** Yakında gelecek özellik tanıtılmaz.
3. **62 il gizlenmez.** "Türkiye'nin her yerinde fiyat var" cümlesi
   kurulmaz — kurulursa 62 ilden gelen ilk kullanıcı haklı çıkar.
4. **Rakam tahmin edilmez.** Yukarıdaki komutla sayılır. Sayı değişmişse
   bu belge de değişir.
5. **Başkasının verisi gösterilmez.** Google Maps, Yandex, Yemeksepeti,
   Getir ekranı kadraja girmez — `CEBIMDE.md` "Yapılmayacaklar".
6. **İşletme kötülenmez.** Kıyas fiyat üzerinedir, mekan üzerine değil.
   Bir işletmeyi hedef alan içerik, o işletmenin sahiplenme ihtimalini de
   bitirir.

---

## Ne ölçülüyor

Haftada bir, cuma akşamı, üç sayı:

| Sayı | Nereden |
|---|---|
| Yeni kayıt | Supabase `auth.users` |
| Yeni fiş | `fis` tablosu, haftalık |
| Fiyatı bilinen mekan | Yukarıdaki komut |

**Karar kuralı:** üç hafta üst üste tek bir fiş getirmeyen format
takvimden düşer, yerine omurgadan (F1/F2) bir gün gelir. Beğeni sayısı
karar vermez — bu ürünün ölçüsü **fiş**. Çok izlenip tek fiş getirmeyen
bir video eğlencedir, büyüme değil.

**Faz A'nın başarı ölçüsü değişmedi:** telefonu birine uzattığında, o kişi
rastgele bir sokak seçip fiyat görebiliyor mu.
