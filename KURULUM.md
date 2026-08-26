# Cebimde — giriş sistemi kurulumu

Site şu an giriş sistemi **olmadan da tam çalışıyor**. Aşağıdaki adımları
yapana kadar giriş, favori ve paylaşım özellikleri kapalı görünür; mekan
arama, harita ve filtreler etkilenmez.

Toplam süre: ~15 dakika. Ücret yok, kart istenmiyor.

---

## 1. Supabase projesi aç

1. [supabase.com](https://supabase.com) → **Start your project** → GitHub ile giriş yap.
2. **New project**:
   - **Name:** `cebimde`
   - **Database password:** güçlü bir parola üret ve bir yere kaydet
     (bunu bir daha göremezsin; site için gerekmiyor ama veritabanına
     doğrudan bağlanmak istersen lazım olur)
   - **Region:** `Frankfurt (eu-central-1)` — Türkiye'ye en yakın olanı
3. Proje hazırlanana kadar bekle (1-2 dakika).

## 2. Veritabanını kur

1. Sol menüden **SQL Editor** → **New query**.
2. `veritabani/sema.sql` dosyasının **tamamını** kopyalayıp yapıştır.
3. **Run**.
4. Alt panelde şuna benzer bir satır görmelisin:
   `Sema kuruldu: 3 tablo, RLS acik, 11 politika`
   Hata verirse dosyayı baştan yapıştırıp tekrar çalıştır — dosya
   tekrar çalıştırılabilir yazıldı, bozulmaz.
5. Aynı yöntemle şu dosyaları da **bu sırayla** çalıştır (hepsi
   `sema.sql`'e bağlı, `sahiplenme.sql` ayrıca `katki.sql`'e bağlı):

   | Dosya | Ne açar | Çalıştırmazsan |
   |---|---|---|
   | `veritabani/sayac.sql` | Görüntülenme sayacı **ve bütçe talebi** | Sayaç satırı ve işletme panelindeki "bakanlar hangi bütçeyle arıyordu" hiç görünmez |
   | `veritabani/katki.sql` | Eksik bilgi katkı formu | Form hiç görünmez |
   | `veritabani/sahiplenme.sql` | İşletme sahiplenme kodu (saha kartları) | Kod alanı hiç görünmez |
   | `veritabani/profil.sql` | Genişletilmiş profil (fotoğraf, yaş, meslek) | Ayarlarda yalnız ad ve parola görünür |
   | `veritabani/yorum.sql` | Mekan yorumları ve puanlar | Yorum bölümü hiç görünmez |
   | `veritabani/menu_katki.sql` | Menü/ürün paylaşımı (fotoğraflı) | Menü ekleme bölümü hiç görünmez |
   | `veritabani/mekan_foto.sql` | Mekan fotoğrafları | Fotoğraf şeridi hiç görünmez |
   | `veritabani/akran.sql` | Bütçe akranları ve civar özeti | Keşfette akran şeridi, işletme sayfasında civar fişi görünmez |
   | `veritabani/fiyat_oyu.sql` | "Bu fiyat hâlâ geçerli mi?" oylaması | Doğrulama düğmesi hiç görünmez, güven skoru yalnız menüye bakar |
   | `veritabani/topluluk.sql` | Topluluk akışı (`topluluk.html`) | Sayfa açılır ama "Akış şu an yüklenemedi" der |

   Hiçbiri kurulmadığında sayfa normal çalışır; yalnız o bölümler
   sessizce gizli kalır. Beklenen çıktılar:

   ```
   Sayac kuruldu: dogrudan yazma kapali, kimlik sunucuda uretiliyor
   Katki tablosu kuruldu: RLS acik, 6 politika
   Sahiplenme kuruldu: kod tablosu kapali, sahiplik 3 politika
   Profil kuruldu: 6 alan, kullanici adi uretiliyor, tablo kapali
   Yorum kuruldu: RLS acik, 5 politika, kimlik sutunu kapali
   Menu katkisi kuruldu: RLS acik, 5 politika, kimlik sutunu kapali
   Mekan fotografi kuruldu: RLS acik, 5 politika, atif zorunlu
   Akran kuruldu: iki fonksiyon, 10 arguman adi tarandi
   Fiyat oylari kuruldu: tablo, RLS, tek-oy kurali ve fiyat_oy_ozeti().
   Topluluk akisi kuruldu: yorum yazariyla, menu katkisi ADSIZ, fis ve fiyat oyu yok.
   ```

   > `profil.sql` **`yorum.sql`'den önce** çalıştırılmalı: yorumlar yazarın
   > profil alanlarını okuyor. Sıra yanlışsa `yorum.sql` anlaşılır bir
   > cümleyle duruyor, bozuk bir kurulum bırakmıyor.

   > `topluluk.sql` **en sonda**: akış `yorum.sql` ve `menu_katki.sql`
   > tablolarından besleniyor. Sıra yanlışsa dosya eksik olanları
   > **adıyla** sayıyor:
   >
   > ```
   > ERROR: topluluk.sql once sunlari istiyor:
   >   - veritabani/yorum.sql (yorumlar tablosu)
   >   - veritabani/menu_katki.sql (menu_katkilari tablosu)
   > ```
   >
   > Bu kapı yaşanmış bir hatadan sonra eklendi: dosya ilk çalıştırıldığında
   > `ERROR: 42P01: relation "public.yorumlar" does not exist` diyordu ve o
   > satır ne yapılacağını söylemiyordu.

   > **Fotoğraflar için ek adım yok.** `profil.sql` ve `menu_katki.sql`
   > depolama kovalarını (`avatar`, `menu`) ve yetkilerini kendileri
   > kuruyor. Yüklenen fotoğrafın **konum ve cihaz bilgisi (EXIF)
   > tarayıcıda siliniyor** — sunucu bunu doğrulayamaz, o yüzden kural
   > istemcide ve `test_sayfa.py` gerçek bir EXIF bloğuyla ölçüyor.

   > **Profil fotoğrafı için ek adım yok.** `profil.sql` depolama kovasını
   > ve yetkilerini kendisi kuruyor. Supabase panelinde
   > **Storage → avatar** kovasını görüyorsan hazır demektir.

   > Üçünü de istediğin sırada, istediğin kadar tekrar çalıştırabilirsin.
   > `katki.sql` ile `sahiplenme.sql` aynı politikaya dokunuyor; ilk
   > yazımda `katki.sql`'i sonradan tekrar çalıştırmak işletme sahiplerinin
   > yetkisini sessizce geri alıyordu. Ölçüldü ve kapatıldı — artık iki
   > dosyanın sırası sonucu değiştirmiyor.

   > **Üç dosyayı da (`sema.sql`, `katki.sql`, `sahiplenme.sql`) yeniden
   > çalıştırman gerekiyor.** Önceki sürümlerinde `kullanici` sütunu
   > tarayıcıya açıktı: RLS **satır** düzeyinde çalışır, "onaylanmış
   > paylaşımlar herkese açık" politikası satırı açtığında satırın içindeki
   > kullanıcı kimliği de açılıyordu. Herkese açık `anon` anahtarıyla bir
   > kişinin nereye, hangi gün, kaç kişiyle gittiği ve ne ödediği tek
   > sorguyla çıkıyordu — gerçek Postgres'te ölçüldü. Yeni sürüm o sütunun
   > okunmasını kapatıyor; veri silinmiyor, uygulamanın hiçbir özelliği de
   > kaybolmuyor.

   > `sayac.sql`'i daha önceki bir sürümüyle çalıştırdıysan tekrar çalıştır:
   > eski sürüm tarayıcının gönderdiği kimliğe güveniyordu ve sayı
   > şişirilebiliyordu. Yeni sürüm o yolu kapatıyor, birikmiş veriyi silmiyor.

## 3. Anahtarları siteye yapıştır

1. Sol menüden **Project Settings** → **API**.
2. Şu iki değeri kopyala:
   - **Project URL** — `https://xxxxx.supabase.co` biçiminde
   - **Project API keys → `anon` `public`** — uzun bir jeton
3. `app/yapilandirma.js` dosyasını aç ve doldur:

```js
window.CEBIMDE = {
  supabaseUrl: "https://xxxxx.supabase.co",
  supabaseAnahtar: "eyJhbGciOi..."
};
```

> **`service_role` anahtarını buraya asla yazma.** O anahtar bütün güvenlik
> politikalarını atlar ve tarayıcıya indiği anda veritabanın savunmasız kalır.
> `anon` anahtarın herkese açık olması normaldir — koruma anahtarda değil,
> veritabanındaki RLS politikalarında.

## 4. E-posta ayarları

**Authentication** → **Providers** → **Email** açık olmalı (varsayılan açık).

- **Confirm email** açıksa kullanıcı doğrulama bağlantısına tıklamadan
  giriş yapamaz. Güvenli olan bu; açık bırak.
- **URL Configuration** → **Site URL** alanına sitenin adresini yaz
  (yerelde `http://localhost:8123`, yayında Vercel adresin).
  Bunu yazmazsan doğrulama ve parola sıfırlama bağlantıları yanlış yere gider.
- Ücretsiz katmanda Supabase'in kendi e-posta göndericisi **saatte 3-4 posta**
  ile sınırlıdır. Gerçek kullanıcı gelmeye başlayınca **Settings → Auth → SMTP**
  bölümünden kendi göndericini bağla (Resend, Brevo gibi servislerin ücretsiz
  katmanları yeter).

## 5. Kendini yönetici yap

1. Siteden normal bir kullanıcı gibi **kayıt ol** ve e-postanı doğrula.
2. Supabase → **SQL Editor** → şunu çalıştır (e-postayı kendi adresinle değiştir):

```sql
update public.profiller set yonetici = true
where id = (select id from auth.users where email = 'senin@adresin.com');
```

3. Siteyi yenile — üst menüde **Yönetim** bağlantısı görünecek.

## 6. Doğrula

Yerelde çalıştır:

```bash
python -m http.server 8123 --directory app
```

Sırayla dene:

- [ ] `giris.html` → hesap aç → doğrulama postası geldi mi
- [ ] Giriş yap → `hesabim.html` açılıyor mu
- [ ] `kesfet.html` → bir mekan aç → **Favorilere ekle** → `hesabim.html`
      → Favorilerim'de görünüyor mu
- [ ] `paylas.html` → fiyat gönder → Paylaşımlarım'da "onay bekliyor" mu
- [ ] `yonetim.html` → paylaşımı **Onayla** → durum "yayımlandı" oldu mu
- [ ] `kesfet.html` → bir mekan aç → **Sayfasını aç** → eksik listesinin altında
      katkı formu görünüyor mu (bilgileri tam olan mekanda görünmemeli)
- [ ] Katkı gönder → `yonetim.html` → **Eksik bilgi katkıları** bölümünde
      göründü mü → **Onayla** → işletme sayfasında "kullanıcıdan" işaretiyle
      çıktı mı ve o satır eksik listesinden düştü mü
- [ ] Çıkış yap → `hesabim.html` adresine git → girişe yönlendiriyor mu

---

## Yayın öncesi kalan tek ayar

E-posta adresleri **yapıldı** — `uzaygokcek941@gmail.com` üç dosyada da yerinde
(`gizlilik.html`, `hesabim.html`, `paylas.html`). Yer tutucu kalmadı.

Kalan tek boş alan `app/yapilandirma.js` içindeki **`sahiplenmeWhatsapp`**:

```js
sahiplenmeWhatsapp: "905XXXXXXXXX",   // faturasız, ayrı bir hat
```

Boş kaldığı sürece işletme sayfası normal çalışır, yalnız **"Bu işletme benim"**
düğmesi gizli kalır. Kişisel hattını yazma — numara işletmelere görünüyor.

## supabase-js'i yerele al (bir kez, 1 dakika)

```bash
python kutuphane_al.py
python csp_uret.py          # esm.sh CSP'den düşüyor
git add app/lib/supabase-js.js vercel.json && git commit -m "chore: supabase-js yerele alindi"
```

Şu an `app/lib/supabase-js.js` bir **yer tutucu**: CDN'e yönlendiriyor.
Betik esm.sh'ten paketlenmiş (tek dosya) sürümü indirip üzerine yazıyor.

**Neden gerekli.** Leaflet `integrity` ile geliyor, supabase-js gelemiyor —
dinamik `import()` bunu desteklemiyor. Yani şu an esm.sh ne gönderirse
doğrulanmadan çalışıyor. İkincisi daha somut: CDN gelmezse giriş, favori,
paylaşım, yorum ve fotoğraf **hep birden** kapanır. Bu bir varsayım değil,
bu projede Leaflet ile yaşandı — keşfet ekranının tamamı ölmüştü.

**İndirilen şey körü körüne yazılmıyor:** boyut, HTML olmadığı,
`createClient` verdiği ve **içinde dış ithalat kalmadığı** doğrulanıyor.
Biri tutmazsa dosya yazılmıyor ve var olan dosyaya dokunulmuyor.

Çalıştırmazsan site normal çalışır — yalnız kütüphane CDN'den gelmeye
devam eder.

## Site haritası — YAPILDI (cebimde.vercel.app)

`sitemap.xml` mutlak adres istiyor, o yüzden depoda hazır durmuyor —
uydurulmuş alan adıyla üretilmiş bir site haritası, üretilmemiş olandan
kötüdür. Üretildi ve depoda: `app/sitemap.xml` (12.287 URL) + `app/robots.txt`.
Veri büyüdükçe yeniden çalıştır — `Sitemap:` satırı çoğalmıyor, ölçüldü:

```bash
python site_haritasi.py cebimde.vercel.app --isletmeler
```

Bu iki dosyayı yazar ve **ikisi de depoya girmeli** (derleme adımı yok,
Vercel `app/` klasörünü olduğu gibi servis ediyor):

- `app/sitemap.xml` — ana sayfalar + içeriği olan işletme sayfaları
- `app/robots.txt` — `Sitemap:` satırı eklenir (tekrar çalıştırınca çoğalmaz)

`--isletmeler` olmadan yalnız ana sayfalar girer. Girdiğinde bile her mekan
alınmıyor: 35.852 mekanın **23.519'unda** ad ve harita noktasından başka
bilgi yok; o sayfaları indekse itmek ince içerik üretmek olur. Şu an
**12.387 işletme sayfası** (%34,3) eşiği geçiyor — kullanıcı katkısı geldikçe
bu sayı büyüyor, o yüzden ara ara yeniden çalıştırmak mantıklı.

## Mekan fotoğrafları nereden geliyor

Üç kaynak var, üçü de yayımlama hakkı olan kaynaklar:

1. **Doğrulanmış işletme sahibi** — saha kartıyla sahiplenen kişi yüklerse
   fotoğraf kuyruğa girmez, doğrudan yayına çıkar. En temiz kaynak.
2. **Kullanıcılar** — mekan sayfasından yükleniyor, onaydan geçiyor.
3. **Wikimedia Commons** — `python foto_cek.py` serbest lisanslı fotoğrafları
   toplayıp `mekan_foto.sql` üretiyor; SQL Editor'e yapıştırıyorsun.
   Atıf (yazar + lisans) zorunlu ve satırlarda taşınıyor.

> **İki ayrı dosya, karıştırma:**
> `veritabani/mekan_foto.sql` **tabloyu kurar** (bir kez çalıştırılır, depoda).
> `foto_ekle.sql` ise `foto_cek.py`'nin ürettiği **veri** dosyasıdır (senin
> makinende oluşur, depoya girmez). Başta ikisinin de adı `mekan_foto.sql`'di
> ve `.gitignore` şema dosyasını da yutmuştu — adlar bu yüzden ayrıldı.

```bash
python foto_cek.py        # foto_ekle.sql üretir
```

> **`ham/` klasörüne gerek yok.** İlk sürüm `turkiye_cek.py`'nin ürettiği dev
> dökümü okuyordu; o döküm 81 il için saatler sürüyor ve depoda durmuyor.
> Oysa gereken şey menünün tamamı değil, yalnız **fotoğraf etiketi taşıyan**
> mekanlar — Overpass'a onu soran sorgu küçük. `ham/` varsa yine de oradan
> okunuyor, ağa hiç çıkmadan.

> Betik yalnız **uygulamada gerçekten olan** mekanlara fotoğraf yazıyor
> (35.852 kimlik `app/veri/` içinden okunuyor). Hiçbir il çekilemezse
> **dosya yazmıyor ve hata veriyor** — ağ arızasını "%0,00 fotoğraf bulundu"
> diye ölçüm gibi raporlamak, kaynağı haksız yere eletirdi.

> **Kapsamı düşük olacak, bunu baştan söylüyorum.** Commons'ta anıt, cami ve
> müze bol; mahalle kafesi yok denecek kadar az. Betik sonunda kaç mekanın
> kapsandığını **sayarak** yazıyor. Sayfaları asıl dolduracak olan işletme
> sahipleri ve kullanıcılar.

> **Google Maps, TripAdvisor ve benzeri kaynaklar buraya girmiyor** ve
> giremez: oradaki fotoğraflar ve yorumlar yazarlarının telifinde, platforma
> lisanslı. Kendi sitende yayımlama hakkın yok — Places API'nin kendi
> şartları bile yorumu 30 günden fazla saklamayı ve harita dışında
> göstermeyi yasaklıyor. `kaynak` sütunu bu yüzden serbest metin değil,
> kısıtlı bir liste.

## SQL'i değiştirirsen

Politikaların metnini okumak yetmiyor. Davranışı gerçek bir Postgres'te
sınayan 26 kontrol var (sahiplenme 15, sayaç 11):

```bash
sh veritabani/kos.sh        # kendi geçici Postgres'ini kurar, sonra siler
```

Bu, `python test.py` içinde de koşuyor (Postgres yoksa **atlanır**, geçtiği
söylenmez). Elle koşan bir kontrolün ne olduğunu bu dosya kendisi gösterdi:
`supabase_taklit.sql`'de eksik bir `grant` yüzünden test 6. adımda patlıyordu,
yani 11 kontrolün **altısı** hiç koşmuyordu — ve 2. adım yanlış sebepten
geçiyordu (yazmayı engelleyen şey politika değil, eksik yetkiydi).

## Güvenlik notu

Yetki kontrolü tarayıcıda değil veritabanında. `yonetim.html` sayfasını
gizlemek yalnızca nezaket; asıl engel `sema.sql` içindeki `yonetici_mi()`
politikası. Yönetici olmayan biri sayfayı elle açsa bile veritabanı ona
başkasının kaydını döndürmez.

Test etmek istersen: yönetici olmayan bir hesapla giriş yapıp tarayıcı
konsolunda başkasının paylaşımını çekmeyi dene — boş dizi dönmeli.

## KVKK

Hesap açıldığı andan itibaren kişisel veri işliyorsun. Şunlar hazır:

- Aydınlatma metni `gizlilik.html` içinde, hangi verinin niçin işlendiği yazılı
- Silme talebi kanalı `hesabim.html` → Ayarlar → Hesabı sil
- Veri en aza indirildi: e-posta ve parola özeti; ad isteğe bağlı
- Veri sorumlusu iletişim adresi yerinde (yer tutucu kalmadı)
- Görüntülenme sayacının IP işlemesi `gizlilik.html` → *İşletme sayfası
  görüntülenme sayısı* başlığı altında açıklanmış: ham IP saklanmıyor,
  özet her gün yenileniyor, hukuki sebep yazılı

Hesap açmayan ziyaretçi için işlenen tek kişisel veri, sayacın kullandığı
IP + tarayıcı bilgisidir; o da geri döndürülemez özete çevrilip saklanır.
