# Duman testi — elle, telefonda, gerçek Supabase'e karşı

Bu liste **otomatik kontrollerin ulaşamadığı** yerleri sınıyor. `test.py`
51 kontrol grubu koşuyor ve `test_sayfa.py` 17 sayfayı gerçek tarayıcıda
açıyor — ama ikisi de Supabase'i **taklit** ediyor. Yani şunların hiçbiri
bugüne kadar bir kez bile gerçek koşulmadı:

- RLS'in kendisi (kimin hangi satırı görebildiği)
- Moderasyon (onaylanmayan katkının gerçekten görünmemesi)
- Depolama (fotoğrafın gerçekten yüklenmesi ve geri gelmesi)
- E-posta (kayıt onayı, parola sıfırlama)
- k-anonimlik eşiklerinin **gerçek veriyle** davranışı

**Süre:** ~60 dakika. **Gereken:** telefon + `oturalim.vercel.app`.

---

## Başlamadan önce

**Üç e-posta adresi gerekiyor.** Sebebi somut: yorum tablosunda
`(kullanici, mekan_id)` **tekil** — yani bir kişi bir mekana bir yorum
yazabiliyor. Yorum eşiği 3 olduğu için "ortalama puan görünüyor mu"
maddesi **üç ayrı hesap** olmadan sınanamıyor.

Fiş öyle değil: tekillik `(kullanici, mekan_ad, tarih)`, yani **aynı
hesapla üç farklı tarihe** üç fiş girilebiliyor. Fiş eşiği tek hesapla
sınanıyor.

| | Adres | Rol |
|---|---|---|
| A | senin asıl adresin | yönetici (moderasyon) |
| B | ikinci adres | normal kullanıcı |
| C | üçüncü adres | yalnız yorum eşiği için |

Not defterine şunu yaz ve doldur: **her maddenin yanına ✓ / ✗ ve ✗ ise
ne olduğu.** "Çalışıyor gibiydi" bir sonuç değil.

---

## A — Açılış ve keşif (giriş YAPMADAN)

Buradaki maddelerin hepsi giriş yapmamış bir ziyaretçinin gördüğü şey.
Uygulamayı ilk açan insan bu.

| # | Yap | Olması gereken | Ne kanıtlıyor |
|---|---|---|---|
| A1 | Ana ekranda bütçe olarak **200** yaz | Kategori önerileri çıkıyor, hiçbiri boş liste değil | Bütçe sınıflandırıcı çalışıyor |
| A2 | Keşfet'e gir, il **Ankara** | Liste geliyor, kartlarda simge var | İl dosyası yükleniyor |
| A3 | **Konumum**'a bas, izin ver | Liste **yakından uzağa** sıralanıyor, sıralama seçicisi "Bana yakın"a geçiyor, altta durum yazısı çıkıyor | Konum → sıralama bağı |
| A4 | İzni **reddet** | Kırmızı "Konum alınamadı" yazısı, uygulama donmuyor | Hata yolu |
| A5 | Fiyatı olan bir mekana gir | Ortalama fiyat **ve kaç kalemden geldiği** yazıyor | Fiyat dayanağı |
| A6 | Fiyatı **olmayan** bir mekana gir | Fiyat yerine hiçbir sayı uydurulmuyor | *Yanlış fiyat, fiyatsızlıktan kötüdür* |
| A7 | Uçak moduna al, sayfayı yenile | Çevrimdışı sayfası çıkıyor | Service worker |

---

## B — Hesap (A hesabı)

| # | Yap | Olması gereken | Ne kanıtlıyor |
|---|---|---|---|
| B1 | A ile kayıt ol | **E-posta geliyor** ve bağlantı çalışıyor | Supabase mail ayarı — hiç sınanmadı |
| B2 | Çıkış yap, tekrar gir | Giriyor | Oturum |
| B3 | Parolamı unuttum → A adresi | Sıfırlama maili geliyor, yeni parola çalışıyor | Sıfırlama akışı |
| B4 | Profilde ad ve kullanıcı adı ver, avatar yükle | Avatar görünüyor, sayfa yenilenince duruyor | Depolama (avatar kovası) |

---

## C — Katkı (B hesabı)

Bu bölüm uygulamanın **asıl işi**. Bugün fotoğraf ve yorum yok olmasının
sebebi teknik değil: kimse henüz göndermedi. Bu maddeler o hattın
gerçekten çalıştığını kanıtlıyor.

| # | Yap | Olması gereken | Ne kanıtlıyor |
|---|---|---|---|
| C1 | Bir mekana **fiş paylaş** (tutar + tarih) | "Onay bekliyor" diyor, **listede görünmüyor** | Onaysız katkı sızmıyor |
| C2 | Aynı mekana aynı tarihle bir fiş daha | Reddediliyor (çift kayıt) | Tekillik kısıtı |
| C3 | Aynı mekana **farklı iki tarihle** iki fiş daha (toplam 3) | Onaylandıktan sonra **ortalama görünüyor** | Fiş eşiği = 3 |
| C4 | Mekana **fotoğraf** yükle | "Onay bekliyor", listede yok | Foto moderasyonu |
| C5 | Menü fotoğrafı + kalem gönder | "Onay bekliyor" | Menü katkısı |
| C6 | **Yorum** yaz (puan + metin) | "Onay bekliyor" | Yorum moderasyonu |
| C7 | Hesabım → katkılarım | Gönderdiğin her şey **durumuyla** listeleniyor | Kendi katkını görme |
| C8 | Bir katkını **sil** | Siliniyor ve geri gelmiyor | Silme yetkisi |

---

## D — Moderasyon (A hesabı, yönetim ekranı)

| # | Yap | Olması gereken | Ne kanıtlıyor |
|---|---|---|---|
| D1 | `yonetim.html`'i **B hesabıyla** aç | **Giremiyor** | RLS — en kritik madde |
| D2 | A ile aç | B'nin gönderdikleri kuyrukta | Yönetim listesi |
| D3 | Fotoğrafı **onayla** | Mekan sayfasında **atıfla** görünüyor; keşfet listesinde kartta çıkıyor | Onay → görünürlük |
| D4 | Yorumu **reddet** | Hiçbir yerde görünmüyor, B'nin kendi listesinde "reddedildi" yazıyor | Ret yolu |

---

## E — İşletme sahibi

| # | Yap | Olması gereken | Ne kanıtlıyor |
|---|---|---|---|
| E1 | Bir mekanda "Buranın sahibiyim" | Kod isteniyor | Sahiplenme kapısı |
| E2 | **Yanlış kod** gir | Reddediliyor | Kod doğrulaması (kodlar sha256 saklanıyor) |
| E3 | Doğru kodla sahiplen, `isletmem.html` | Panel açılıyor, mekan listede | Sahiplik |
| E4 | Panelden kampanya/menü güncelle | Mekan sayfasında görünüyor | Sahip yetkisi |

---

## F — Gizlilik ve eşikler

| # | Yap | Olması gereken | Ne kanıtlıyor |
|---|---|---|---|
| F1 | 3'ten az fişi olan mekan | "N tane daha gelince ortalama burada görünecek" | k-anonimlik = 3 |
| F2 | B ve C ile **iki** yorum yaz, onayla | Ortalama puan **görünmüyor** | Yorum eşiği tutuyor |
| F3 | A ile üçüncü yorumu yaz, onayla | Ortalama puan **görünüyor** | Eşik tam 3'te açılıyor |
| F4 | Topluluk akışında başkasının profiline gir | E-posta adresi **hiçbir yerde yok** | Kişisel veri sızmıyor |

---

## G — Mobil ve PWA

| # | Yap | Olması gereken | Ne kanıtlıyor |
|---|---|---|---|
| G1 | "Ana ekrana ekle" | Simge çıkıyor, tam ekran açılıyor | Manifest |
| G2 | 320 px genişlikte (küçük telefon) keşfet | Araç çubuğu kırpılmıyor, "Konumum" kendi satırında | Ölçülen 470 px eşiği |
| G3 | Tek elle, başparmakla gez | Basılacak her şey **en az 44 px** | WCAG 2.5.8 |

---

## Bittiğinde

**Her ✗ için üç şey yaz:** hangi ekran, ne yaptın, ne oldu. Ekran
görüntüsü al. Tahmin yazma — "sanırım RLS" değil, "yonetim.html B ile
açıldı ve kuyruk göründü".

Testi geçen bir madde **bir daha koşulmayacak diye bir şey yok**: bu
liste her yayın öncesi tekrar koşuluyor.

---

## Bu listenin koşamadığı tek şey

**Fotoğraf ve yorumların gerçekten var olması.** O bir test sorunu değil,
bir kullanıcı sorunu: bugün uygulamada onaylanmış tek bir kullanıcı
fotoğrafı ya da yorumu yok, çünkü henüz kimse göndermedi. Hat uçtan uca
çalışıyor ve bu liste onu kanıtlıyor — ama **hattı dolduran şey insan.**
Ayrıntı: `VERI_VE_GELIR.md` §3b ve §4.
