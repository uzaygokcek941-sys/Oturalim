# Google Play — Oturalım

Uygulama **TWA** (Trusted Web Activity) olarak paketleniyor: Android
paketinin içinde adres çubuğu olmayan bir Chrome, o da bu siteyi açıyor.
Yeniden yazılan bir şey yok — Play'e giden şey aynı site.

**Neden TWA, neden React Native / Flutter değil:** ürün zaten çalışan bir
web uygulaması ve tek kişilik bir yapıda ikinci bir kod tabanı bakmak,
üçüncü ayda iki ürünün de yarım kalması demek. TWA'da web'e yaptığın her
güncelleme uygulamaya da **yeni sürüm yüklemeden** gidiyor. Sınırı da
açık: cihaza özel bir şey (bildirim, arka planda konum, widget) gerekirse
TWA yetmez.

---

## Depoda hazır olanlar

| Dosya | Ne |
|---|---|
| `app/manifest.webmanifest` | Uygulama adı, ikonlar, `start_url`, tema rengi |
| `app/ikon/*.png` | 192, 512, maskelenebilir 512, 1024 — `python ikon_uret.py` |
| `app/sw.js` | Service worker; sürümü `python sw_uret.py` damgalıyor |
| `app/cevrimdisi.html` | Bağlantı yokken gösterilen sayfa |
| `twa-manifest.json` | Bubblewrap yapılandırması |
| `assetlinks_uret.py` | `app/.well-known/assetlinks.json` üretici |

`test.py` bunların hepsini denetliyor: manifest geçerli mi, ikonlar doğru
ölçüde mi, service worker damgası güncel mi, çevrimdışı sayfası gerçekten
açılıyor mu.

---

## Sırayla

### 0. Önce site yayında olmalı

TWA bir adrese bağlanıyor. `twa-manifest.json` içindeki `host` şu an
`oturalim.vercel.app`. **Kendi alan adını alacaksan Play'e çıkmadan önce
al** — host'u sonradan değiştirmek yeni bir paket demek.

### 1. Paket adına karar ver — bu geri alınamaz

`twa-manifest.json` ve `assetlinks_uret.py` içinde `com.oturalim.app`.
**Play'de yayımlandıktan sonra paket adı değiştirilemez;** değiştirmek
yeni bir uygulama yayımlamak, indirmelerin ve yorumların sıfırlanması
demek. Değiştireceksen şimdi, iki dosyada birden (`test.py` ikisinin
ayrışmasını hata sayıyor).

### 2. Bubblewrap

```bash
npm install -g @bubblewrap/cli
bubblewrap init --manifest=https://oturalim.vercel.app/manifest.webmanifest
```

İlk çalıştırmada JDK ve Android SDK'yı kendisi indiriyor (~1 GB, bir
kerelik). Depodaki `twa-manifest.json` cevapların çoğunu içeriyor —
Bubblewrap onu okuyup doğruluyor.

```bash
bubblewrap build
```

Çıktı: `app-release-bundle.aab` (Play'e bu yükleniyor) ve imzalı bir APK
(kendi telefonunda denemek için).

> **İmzalama anahtarı.** Bubblewrap bir `.jks` üretiyor ve parola soruyor.
> O dosya + parola, uygulamayı **senin adına güncelleyebilen tek şey**.
> `.gitignore` `*.jks` ve `*.keystore` dosyalarını kapatıyor — depoya
> girmemeli. Bir yedeğini depo dışında sakla.

### 3. Play Console

- Geliştirici hesabı: **tek seferlik 25 USD**.
- Yeni **kişisel** hesaplarda üretime çıkmadan önce **kapalı testte 12
  test kullanıcısı / 14 gün** şartı var. Kurumsal hesapta yok. Bu ürünün
  takvimini doğrudan etkiliyor — Console'da güncel halini doğrula.
- Uygulama oluştur → `app-release-bundle.aab` yükle.

### 4. Parmak izi ve assetlinks — atlanırsa adres çubuğu çıkar

Play App Signing kullanıyorsan (varsayılan) imzayı Google atıyor, yani
doğrulanacak parmak izi **Google'ın** anahtarından geliyor ve ancak ilk
yüklemeden sonra görünüyor:

```
Play Console → Test ve yayınlama → Uygulama imzalama
→ "SHA-256 sertifika parmak izi"
```

```bash
python assetlinks_uret.py AA:BB:CC:...            # Play'den gelen
python assetlinks_uret.py AA:BB:... 11:22:...     # + yerel test anahtarın
git add app/.well-known/assetlinks.json && git commit && git push
```

Betik parmak izini doğruluyor: kısa, uzun, onaltılık olmayan ya da
yapıştırılmış bir cümle **yazılmıyor**. `keytool` çıktısının küçük harfli
ve `SHA256:` önekli hali de, iki noktasız 64 haneli hal de kabul ediliyor.

Yayına aldıktan sonra iki şeye bak:

1. `https://<alan-adın>/.well-known/assetlinks.json` → **200 ve JSON**
2. Uygulamayı aç → **üstte adres çubuğu görünmemeli**

Adres çubuğu görünüyorsa doğrulama tutmuyor demektir. Bu TWA'da en sık
yaşanan sorun ve **hiçbir yerde hata vermiyor** — uygulama çalışır, sadece
tarayıcı gibi görünür.

### 5. Store girişi

| Alan | Ne yazılacak |
|---|---|
| Uygulama adı | Oturalım |
| Kısa açıklama | Bütçene göre otur. 81 ilde 35.852 mekan. |
| Tam açıklama | Aşağıda |
| Uygulama ikonu | `app/ikon/ikon-512.png` |
| Öne çıkan görsel | 1024×500 — henüz yok, hazırlanmalı |
| Ekran görüntüsü | En az 2 telefon görüntüsü; keşfet + mekan sayfası |
| Kategori | Yiyecek ve İçecek |
| Gizlilik politikası | `https://<alan-adın>/gizlilik.html` |

**Tam açıklama taslağı** (rakamlar depodan sayılarak; değişirse güncelle):

> Bütçene göre nereye gidebileceğini gösterir. 81 ilde 35.852 kafe,
> restoran, bar ve eğlence mekanı; tür, bahçe, wi-fi, şu an açık olma ve
> mesafeye göre süzebilirsin.
>
> Fiyatı işletmeler değil, giden insanlar yazıyor. Bir yere gidip
> ödediğini yazdığında bir sonraki kişi ne kadara oturulduğunu görüyor.
> Bir mekanın ortalaması ancak üç ayrı fiş geldikten sonra gösteriliyor —
> tek kişinin bir akşamı bir mekanın fiyatı değildir.
>
> Mekan verisi OpenStreetMap'ten geliyor ve açık lisanslı. Reklam yok,
> üyelik ücreti yok. Hesap açmak yalnız fiyat, yorum veya fotoğraf
> paylaşmak istersen gerekiyor.

### 6. Veri güvenliği formu

Bu form **yanlış doldurulursa uygulama kaldırılıyor.** Aşağısı kodun
gerçekte ne yaptığı — tahmin değil, `veritabani/` ve `app/` okunarak
çıkarıldı.

| Veri | Toplanıyor mu | Nasıl |
|---|---|---|
| E-posta adresi | **Evet** | Hesap açmak için. Supabase Auth. |
| Ad / kullanıcı adı | **Evet**, isteğe bağlı | Profil. Kullanıcı gizleyebiliyor. |
| Fotoğraf | **Evet**, isteğe bağlı | Menü ve mekan fotoğrafı. **EXIF siliniyor** (konum, cihaz, saat) — cihazda, yüklemeden önce. |
| Kullanıcı içeriği | **Evet** | Fiyat paylaşımı, yorum, menü kalemi. |
| **Konum** | **HAYIR** | "Yakınımdakiler" cihazda çalışıyor; koordinat hiçbir yere gönderilmiyor. |
| IP adresi | **Hayır** (saklanmıyor) | Görüntülenme sayacı IP'yi günlük değişen bir tuzla özete çeviriyor; ham IP tabloya yazılmıyor. |
| Reklam / analitik | **Yok** | Üçüncü taraf izleyici yok. |

- Veriler **aktarımda şifreleniyor** (HTTPS): evet.
- Kullanıcı **silme talep edebiliyor**: evet — hesabım ekranı ve
  `gizlilik.html`'deki adres.

### 7. İçerik derecelendirmesi

Anketi dürüst doldur. Uygulamada **kullanıcı içeriği var** (yorum,
fotoğraf) — bu soru sorulacak ve **evet**. Ön onaydan geçiyor
(`veritabani/yorum.sql`, `mekan_foto.sql`), bunu da belirt: hakaret ve
karalamaya karşı tek savunma ön onay ve bildir-kaldır kanalı.

Alkol: uygulamada **bar ve pub var** (1.029 bar, 414 pub). Alkol satmıyor,
alkol tanıtımı yapmıyor, yalnız mekanı listeliyor. Anket bunu soruyorsa
"referans var, satış yok" tarafını işaretle.

---

## Güncelleme nasıl gidiyor

Sitede bir şey değiştirdiğinde uygulama **kendiliğinden** güncelleniyor;
Play'e yeni sürüm yüklemene gerek yok. Yeni paket yalnız şunlar için
gerekli: uygulama adı, ikon, paket adı, hedef API sürümü, TWA
yapılandırması.

Service worker sürümü içerikten türetiliyor (`sw_uret.py`), yani
dosyalar değişince onbellek kendiliğinden tazeleniyor. **Bunu elle
yapma:** `python sw_uret.py` çalıştır, `test.py` güncel olup olmadığına
bakıyor.

---

## Yapılmadı, bilerek

- **Bildirim yok.** `enableNotifications: false`. Bildirim izni istemek,
  gönderilecek bir şey olmadan güven kaybettiriyor.
- **Arka planda konum yok.** Play'in en sıkı denetlediği izin bu ve bu
  uygulamanın ona ihtiyacı yok.
- **App Store (iOS) yok.** Apple, yalnız web sitesini saran uygulamaları
  4.2 "minimum işlevsellik" kuralıyla reddediyor. Android'de TWA resmî
  olarak destekleniyor, iOS'ta karşılığı yok. iOS kullanıcısı için yol
  Safari → Paylaş → "Ana Ekrana Ekle"; manifest ve `apple-touch-icon`
  bunun için duruyor.
