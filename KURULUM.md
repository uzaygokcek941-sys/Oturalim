# Oturalım — giriş sistemi kurulumu

Site şu an giriş sistemi **olmadan da tam çalışıyor**. Aşağıdaki adımları
yapana kadar giriş, favori ve paylaşım özellikleri kapalı görünür; mekan
arama, harita ve filtreler etkilenmez.

Toplam süre: ~15 dakika. Ücret yok, kart istenmiyor.

---

## 1. Supabase projesi aç

1. [supabase.com](https://supabase.com) → **Start your project** → GitHub ile giriş yap.
2. **New project**:
   - **Name:** `oturalim`
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
   `Sema kuruldu: 3 tablo, RLS acik, 9 politika`
   Hata verirse dosyayı baştan yapıştırıp tekrar çalıştır — dosya
   tekrar çalıştırılabilir yazıldı, bozulmaz.
5. Aynı yöntemle şu iki dosyayı da çalıştır (ikisi de `sema.sql`'e bağlı,
   ondan **sonra** gelmeli):

   | Dosya | Ne açar | Çalıştırmazsan |
   |---|---|---|
   | `veritabani/sayac.sql` | İşletme sayfası görüntülenme sayacı | Sayaç satırı hiç görünmez |
   | `veritabani/katki.sql` | Eksik bilgi katkı formu | Form hiç görünmez |

   İkisi de kurulmadığında sayfa normal çalışır; yalnız o bölümler
   sessizce gizli kalır. Beklenen çıktılar:

   ```
   Sayac kuruldu: dogrudan yazma kapali, kimlik sunucuda uretiliyor
   Katki tablosu kuruldu: RLS acik, 6 politika
   ```

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
window.OTURALIM = {
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

## Değiştirmen gereken e-posta adresleri

Kod içinde `iletisim@oturalim.app` yer tutucu olarak duruyor. Kendi adresinle
değiştir:

| Dosya | Nerede |
|---|---|
| `app/gizlilik.html` | veri sorumlusu ve KVKK başvuru adresi (2 yer) |
| `app/hesabim.html` | `EPOSTA` sabiti — hesap silme talebi |
| `app/paylas.html` | `EPOSTA` sabiti — kimlik kapalıyken yedek yol |

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

Eksik olan: **veri sorumlusu olarak gerçek bir iletişim adresi**. Yer tutucu
adresi kendi adresinle değiştirmeden yayına çıkma.
