/* ============================================================
   Oturalım — Supabase bağlantı ayarları

   Buraya kendi projenin iki değerini yapıştır:
     Supabase paneli → Project Settings → API
       Project URL      -> supabaseUrl
       anon public key  -> supabaseAnahtar

   İkisi de boş kaldığı sürece site normal çalışır; yalnızca giriş,
   favori ve paylaşım özellikleri kapalı görünür. Kimlik altyapısı
   kurulmadan ürünün geri kalanı bozulmasın diye böyle.

   GÜVENLİK: buradaki "anon" anahtar tasarım gereği herkese açıktır,
   tarayıcıya inmesi normaldir. Yetkiyi anahtar değil, veritabanındaki
   RLS politikaları belirler (veritabani/sema.sql).
   "service_role" anahtarını BURAYA ASLA YAZMA — o anahtar RLS'i
   tamamen atlar; tarayıcıya inerse bütün veri savunmasız kalır.
   ============================================================ */

window.OTURALIM = {
  supabaseUrl: "https://zlhlstfnayoaytoqmmcw.supabase.co",
  supabaseAnahtar: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpsaGxzdGZuYXlvYXl0b3FtbWN3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcxOTU1MjUsImV4cCI6MjEwMjc3MTUyNX0.FAkfmMRjh3GiKZUkrWrV_fG1vZpobIp3EiStB0KEW7w"
};
