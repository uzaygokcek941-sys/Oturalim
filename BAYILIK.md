# Cebimde bayilik — saha temsilciliği

## Neden var

Uygulamanın tek gerçek darboğazı yazılım değil, veri.

| Ölçüm | Sayı |
|---|---|
| Toplam mekan | 35.852 |
| Ne web, ne sosyal medya, ne telefon | 30.393 (%84,8) |
| Menü fiyatı ölçülmüş mekan | 293 (%0,82) |
| Kadıköy 500 m'de mekan / menüsü olan | 484 / **4** |

Bu bilgiyi uzaktan toplamanın yolu yok. Google Maps, Yandex, Yemeksepeti,
Getir ve TrendyolGo kazımak projenin **Yapılmayacaklar** listesinde;
geriye kapıya gitmek kalıyor. Kapıya gitmek de ölçeklenmeyen tek iş: bir
kişiyle 81 il olmuyor.

**Bayi, o işi bölge bölge devralan kişi.**

---

## Bayi ne yapıyor

1. Bir ilçe alıyor (`bayi_bolge`). Bir ilçenin aynı anda tek bayisi olur.
2. O bölge için bir **kart partisi** basılıyor (`saha.py --bayi`).
3. Kartları kapıya bırakıyor, `saha_liste.csv`'de işaretliyor.
4. İşletme QR'ı okutup ya da 8 haneli kodu yazıp sayfasını sahipleniyor.
5. Hakediş **kendiliğinden** düşüyor.

```
sahiplen.py  ->  saha.py --bayi 3  ->  kart + SQL  ->  kapı
                                                        │
                          işletme kodu girer  ─────────►│
                                                        ▼
                        sahiplenme_kodu.kullanildi = now()
                                                        │
                            tetikleyici ────────────────┘
                                                        ▼
                                              bayi_kazanim ('sahiplenme')
                        işletme bilgi ekler, onaylanır
                                                        ▼
                                              bayi_kazanim ('alan')
```

---

## Hakediş: koda bağlı, beyana değil

Bu sistemin tek önemli tasarım kararı bu.

Bayi "40 yere uğradım" **demiyor**. Bastığı partideki kodlar zaten mekan
mekan tekil ve `sahiplenme_kodu` satırında hangi bayiye ait olduğu yazılı.
İşletme kodu kullandığında hakediş kendiliğinden doğuyor.

Beyan olsaydı ölçtüğümüz şey ziyaret değil, **ziyaret iddiası** olurdu.

### İki aşama, çünkü tek aşama yanlış teşvik

| Tür | Ne demek | Ne zaman doğar |
|---|---|---|
| `sahiplenme` | Kart **çalıştı** | işletme kodu girip sayfasını sahiplendi |
| `alan` | Kart **işe yaradı** | işletme saat/telefon/adres/site ekledi ve yayına çıktı |

Yalnız birincisini ödeseydik bayinin işi kartı kime olursa okutmak olurdu.
İkincisi parayı projenin ihtiyacı olan şeye — veriye — bağlıyor.

**Mekan başına her türden bir kez.** İşletmenin on alan doldurması on
hakediş değil; ölçtüğümüz şey "kart işe yaradı mı", "kaç tuşa basıldı"
değil.

---

## Ücret

Şema ücreti **kendiliğinden koymuyor**: `sahiplenme_ucreti` ve
`alan_ucreti` varsayılan olarak **0**. Bayiye ne ödeneceği ticari bir
karar ve yazılım onu senin adına veremez.

Ücret **hakediş anında donduruluyor** (`bayi_kazanim.tutar`). Oranı
sonradan değiştirmek geçmiş kazanımları yeniden yazmıyor.

### Önerilen başlangıç

Kuruş cinsinden. Yönetici olarak Supabase SQL Editor'de:

```sql
update public.bayi
   set sahiplenme_ucreti = 2500,   -- 25 ₺  kart çalıştı
       alan_ucreti       = 7500    -- 75 ₺  kart işe yaradı
 where id = 1;
```

Bu sayılarla 32 mekanlık bir küme, %20 sahiplenme ve sahiplenenlerin
yarısının bilgi eklemesi varsayımıyla: 6 × 25 + 3 × 75 = **375 ₺**.
Varsayımlar ölçülmedi — ilk parti bittiğinde `python saha.py olc` gerçek
oranı verecek ve rakam ona göre düzeltilecek.

### Ödeme

Para transferi bu sistemin **dışında** (havale/EFT). `bayi_odeme` yalnız
"ne kadar ödendi" kaydını tutuyor; panelde görünen **bakiye** = hakediş −
ödenen. Ödeme satırını yalnız yönetici yazabiliyor.

---

## Giriş bedeli YOK ve bu bilerek

Klasik bayilikte bayi bölge hakkı için peşin para öder. Burada öyle bir
şey yok ve olmayacak:

- Cebimde'nin bugün **geliri yok** (`VERI_VE_GELIR.md`). Geliri olmayan
  bir uygulamanın bölge hakkı satması, arkasını doldurabileceği bir söz
  vermeden para toplamak olur.
- Daha kötüsü, teşviki tersine çevirir: bayinin parası **kaydolmaktan**
  gelir, çalışmaktan değil. Bütün sistemin amacı tam tersi.

Bayilik veriliyor, satılmıyor.

---

## Ne vermiyor

Sahiplikte olduğu gibi, bayilik de sınırlı bir yetki:

| | |
|---|---|
| Sıralama, rozet, öne çıkarma | **yok** — para karşılığı sıralama bu projede yok, bayilik ona kapı açmıyor |
| Mekan silme / düzenleme | yok |
| Başka bayinin verisi | yok (RLS ile kilitli, testte ölçüldü) |
| İşletmecinin kimliği | **yok** — "sahiplenildi mi" görünüyor, "kim sahiplendi" görünmüyor |
| Kod özetleri | yok |

Son iki satır önemli: bayi kendi bölgesindeki işletmecilerin listesini
eline geçirebilseydi kart bir tanışma aracı değil bir **müşteri listesi**
olurdu.

---

## Kurulum

### 1. Şema (bir kez)

Supabase SQL Editor'de sırayla: `sema.sql`, `katki.sql`, `sahiplenme.sql`,
sonra `veritabani/bayilik.sql`.

Dosya kendini kontrol ediyor: sonunda `Bayilik kuruldu: 4 tablo, 2
tetikleyici, kazanim yalniz koddan` yazmalı.

### 2. Bayiyi tanımla (yönetici)

Kişi önce uygulamaya normal kullanıcı olarak kaydolur. Sonra:

```sql
insert into public.bayi (kullanici, ad, telefon, durum,
                         sahiplenme_ucreti, alan_ucreti)
select id, 'Ad Soyad', '05xx xxx xx xx', 'aktif', 2500, 7500
  from auth.users where email = 'bayi@ornek.com';

insert into public.bayi_bolge (bayi, il, ilce)
values ((select id from public.bayi where ad = 'Ad Soyad'), '06', 'Çankaya');
```

### 3. Parti bas

```bash
python sahiplen.py                       # kümeler güncel değilse
python saha.py oturalim.vercel.app --il Ankara --kume 2 --bayi 1
```

Üç çıktı: `saha_kartlar.html` (yazdır), `saha_kodlar.sql` (Supabase'e
yapıştır), `saha_liste.csv` (sahada işaretle). **Üçü de `.gitignore`'da** —
ilk ikisi düz kod taşıyor, üçüncüsü hangi kartın nereye gittiğini
gösteriyor.

> **Sıra önemli: önce SQL, sonra dağıtım.** SQL çalıştırılmadan dağıtılan
> bir parti hiçbir kodu kabul etmez. İşletme bir kez dener, olmaz, bir
> daha denemez.

### Basılmış bir partiyi sonradan bayiye bağlamak

Kartlar `--bayi` verilmeden basıldıysa **yeniden basmaya gerek yok**:

```bash
python saha.py sql saha_liste.csv --bayi 1 --parti ankara-52
```

Kodlar listede duruyor; bayi ve parti yalnız SQL'de geçen bir şey. Kartın
üstündeki kod ve QR **değişmiyor**, yalnız veritabanına yazılan sütunlar
değişiyor. (Aynı desen `foto_cek.py sql`'de de var: CSV kaynak, SQL
türetilmiş.) Supabase'de bu SQL'i çalıştırmak yeterli — `on conflict
(kod_ozeti) do nothing` yüzünden kod zaten yazılmışsa bayi sütunu
**güncellenmez**; o durumda önce o partinin satırlarını sil ya da
`update ... set bayi = 1 where parti = '...'` yaz.

`saha.py` ikinci bir partiyi basarken **üzerine yazmayı reddediyor**:
`saha_liste.csv`, hangi kodun hangi kapıya gittiğini gösteren tek kayıt
ve kod veritabanında yalnız sha256 özeti olarak duruyor.

### 4. Ölç

```bash
python saha.py olc
```

Sıfır sahiplik, kartın işe yaramadığı anlamına gelir. **Metni ya da
bırakma biçimini değiştirmeden ikinci kümeye çıkma.**

---

## Bayi ne görüyor

`app/bayi.html` — `hesabim.html` → İşletmelerim sekmesinden açılıyor ve
bağlantı **yalnız bayiye** görünüyor.

| Sayı | Ne demek |
|---|---|
| basılan kart | adına basılmış toplam kart |
| sahiplenildi | kodu kullanılan kart |
| bilgi ekledi | işletmesi gerçekten alan dolduran mekan |
| hakediş / ödenen / bakiye | kuruş hassasiyetinde |

Sıfır burada **gösteriliyor** — işletme panelinin tersi bir karar. Orada
"0 kişi baktı" cesaret kırıcıydı; burada "20 kart bıraktım, 0'ı
sahiplenildi" bayinin bilmesi gereken en önemli cümle.

---

## Ne sınandı

`sh veritabani/kos.sh` gerçek Postgres'te 16 adım koşuyor
(`bayilik_test.sql`). Ölçtüğü iki şey:

- **Kimse başkasının verisini göremiyor**: anon bayi tablosunu okuyamıyor,
  bayi B bayi A'nın kazanımını ve kartlarını göremiyor, `kullanici`
  sütunu tarayıcıya kapalı, bayi olmayan panel fonksiyonlarını
  çağıramıyor.
- **Hakediş yalnız koddan doğuyor**: kazanıma yönetici bile elle
  yazamıyor, kartı olmayan mekanın katkısı hiçbir bayiye yazılmıyor,
  bekleyen katkı hakediş doğurmuyor, oran değişince geçmiş değişmiyor.

Her adım sabotajla doğrulandı — kontrolü kaldırıp testin gerçekten
kırmızıya döndüğü görüldü. Bir tanesi bu yüzden **düzeltildi**: "bekleyen
katkı hakediş doğurmaz" adımı kartı hiç kullanılmamış bir mekanda
sınanıyordu, yani onay kontrolü silinse de yeşil kalıyordu. Adım artık
kartı kullanılmış bir mekanda koşuyor.
