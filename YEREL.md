# Kendi bilgisayarında çalıştır

Cebimde **tek başına** çalışabiliyor: sunucu yok, hesap yok, internet
yok. 81 il, 35.852 mekan, fiyatlar, harita ve çevrimdışı sayfası
tamamen kendi diskinden geliyor.

Ölçüldü (bu ortamda, ağ kapalıyken, Supabase tamamen boşken):

| | |
|---|---|
| Sayfa | 6 / 6 → HTTP 200 |
| JS hatası | **0** |
| Keşfet İstanbul | 120 kart, **102'sinde fiyat** |
| Harita | çalışıyor |

---

## Kurulum — üç adım

### 1. Python kur (bir kereye mahsus)

**Windows:** <https://www.python.org/downloads/> → indir → kurulumda
**"Add python.exe to PATH"** kutusunu **işaretle**. Bu kutu işaretli
değilse başlatıcı Python'u bulamaz.

**macOS:** çoğu Mac'te zaten var. Yoksa: `brew install python`

**Linux:** `sudo apt install python3`

Başka hiçbir şey gerekmiyor — kurulacak paket, `npm install`, derleme
adımı yok. Projede bilerek derleme adımı yok.

### 2. Depoyu indir

Depo **özel (private)**, yani önce GitHub'a giriş yapmış olman gerekiyor.

**En kolay yol — ZIP:**
1. <https://github.com/uzaygokcek941-sys/Otural-m> adresine git
   (giriş yapmış olmalısın, yoksa 404 görürsün)
2. Yeşil **Code** düğmesi → **Download ZIP**
3. ZIP'i **aç** (Windows'ta sağ tık → Tümünü ayıkla). Açmadan
   çalıştıramazsın.

**Git kullanıyorsan:**
```
git clone https://github.com/uzaygokcek941-sys/Otural-m.git
```

### 3. Başlat

**Windows:** klasördeki **`baslat.bat`** dosyasına **çift tıkla**.

**macOS / Linux:** terminalde klasöre gir ve:
```
sh baslat.sh
```

Tarayıcı kendiliğinden açılıyor. Açılmazsa: <http://localhost:8123>

Kapatmak için açılan siyah pencerede **Ctrl+C**.

---

## Ne çalışıyor, ne çalışmıyor

Başlatıcı uygulamayı **`--yerel`** kipinde açıyor: hesap katmanı kapalı.

| Çalışıyor | Çalışmıyor (`--yerel` kipinde) |
|---|---|
| 81 il, 35.852 mekan | Giriş / kayıt |
| Fiyatlar ve menüler | Fiş paylaşma |
| Harita, konum, "bana yakın" | Yorum, fotoğraf yükleme |
| Bütçe filtresi, sıralama | İşletme paneli, bayi paneli |
| Kapsama sayfası | Talep açığı ve fiyat endeksi şeritleri |
| Çevrimdışı sayfası | |

Kapalı olanlar **kırık değil, gizli**: uygulama giriş sistemi kurulu
değilken o bölümleri hiç çizmiyor. Giriş sayfası da bunu açıkça
söylüyor ("Giriş sistemi henüz kurulu değil").

### Hesap katmanını da açmak istersen

`baslat.bat` / `baslat.sh` yerine doğrudan:

```
python sunucu.py
```

Bu, `app/yapilandirma.js` içindeki **gerçek** Supabase ayarını
kullanır — yani internet ve yayındaki veritabanı gerekir. `--yerel`
o dosyaya **dokunmuyor**; yalnız yanıtta boş bir ayar servis ediyor,
diskteki dosya olduğu gibi kalıyor.

---

## Bir şey ters giderse

| Ne görüyorsun | Ne yapacaksın |
|---|---|
| Pencere açılıp hemen kapanıyor | `baslat.bat`'ı çift tıkla, kapanmaz — hata yazar ve bekler |
| "Python bulunamadi" | Python kurulu değil ya da PATH'e eklenmemiş (adım 1) |
| "sunucu.py bulunamadi" | Yanlış klasördesin; ZIP'i açtığından emin ol |
| "app\index.html yok" | Depo eksik inmiş, ZIP'i yeniden indir |
| Tarayıcıda boş sayfa | Adres `http://localhost:8123` mü? `file://` ile açılmaz |
| Port dolu | `python sunucu.py 9000 --yerel` ve `localhost:9000` |

**`file://` ile açma.** `app/index.html`'e çift tıklamak çalışmaz:
sayfa il dosyalarını `fetch` ile okuyor ve tarayıcı `file://`
üzerinden buna izin vermiyor. Sunucu bu yüzden var.

---

## Geliştirme yapacaksan

```
python test.py          # 58 kontrol grubu (Postgres ve Chromium varsa hepsi)
python sunucu.py        # gerçek Supabase ile
sh veritabani/kos.sh    # SQL davranış testleri (Postgres gerekir)
```

`sunucu.py` yayındaki güvenlik başlıklarını `vercel.json`'dan okuyup
gönderiyor — yani yerelde de **gerçek CSP altında** geziyorsun. Satır
içi bir betiği değiştirdiysen `python csp_uret.py` çalıştırman gerekiyor,
yoksa tarayıcı o betiği reddeder ve sayfa sessizce yarım çalışır.

Ayrıntı: `KURULUM.md` (Supabase), `README.md` (proje).
