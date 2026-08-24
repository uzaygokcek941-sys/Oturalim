-- ============================================================
-- Oturalım — işletme sahiplenme (Faz 4)
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir: her şey "if not exists" / "or replace".
-- ÖNCE sema.sql ve katki.sql çalıştırılmış olmalı.
--
-- NEDEN VAR: 35.852 mekanın 30.393'ünde (%84,8) ne web, ne sosyal medya, ne telefon var.
-- Bu işletmelere uzaktan ulaşmanın yolu yok; sahiplen.py onları yürüyüş
-- kümelerine ayırıyor ve saha ziyaretinde kapıya bir kart bırakılıyor.
-- Kartın üstünde o mekana ait TEK KULLANIMLIK bir kod var. Kodu giren kişi
-- o işletmenin sayfasını sahipleniyor.
--
-- KOD NEYI KANITLAR: fiziksel olarak orada bulunmayı. Tapu değil. Kartı
-- tezgahtan alan biri de girebilir. Bu yüzden sahiplik (a) kayıtlı,
-- (b) geri alınabilir, (c) sınırlı yetki veriyor.
--
-- NE VERIYOR: sahibin KENDI mekanı için gönderdiği saat/telefon/adres/site
-- katkısı kuyruğa girmeden yayına çıkıyor. Bunlar kapıda okunabilen,
-- yanlışsa zararı sınırlı ve geri alınabilir bilgiler.
--
-- NE VERMIYOR: fiyat iddiası, sıralama, rozet, öne çıkarma. İşletmenin
-- kendi menü fiyatını yazması meşru ama o hat paylasimlar + onay; para
-- karşılığı sıralama bu projede yok ve sahiplik ona kapı açmıyor.
-- ============================================================

-- Kod özeti için sha256 gerekiyor. Supabase'de pgcrypto kurulu gelir ama
-- her projede etkin olmayabiliyor; burada açıkça isteniyor.
create extension if not exists pgcrypto;

-- ---------- 1. Tek kullanımlık kodlar ----------
-- Kodun KENDISI saklanmıyor, yalnızca sha256 özeti. Parola ile aynı gerekçe:
-- tabloyu ele geçiren biri kartları basılmamış mekanları sahiplenemesin.
-- Arama da özet üzerinden yapılıyor, o yüzden düz metne hiç ihtiyaç yok.
create table if not exists public.sahiplenme_kodu (
  kod_ozeti    text primary key check (char_length(kod_ozeti) = 64),
  mekan_id     text not null check (char_length(mekan_id) between 1 and 80),
  il           text check (char_length(il) = 2),
  mekan_ad     text not null check (char_length(mekan_ad) between 1 and 200),
  olusturuldu  timestamptz not null default now(),
  -- Kart bir yerde unutulursa süresiz geçerli kalmasın.
  gecerlilik   date not null default (current_date + 180),
  kullanan     uuid references auth.users(id) on delete set null,
  kullanildi   timestamptz
);

comment on table public.sahiplenme_kodu is
  'Sahada dagitilan tek kullanimlik kodlarin sha256 ozeti. Duz kod saklanmaz.';

create index if not exists sahiplenme_kodu_mekan_idx
  on public.sahiplenme_kodu (mekan_id) where kullanildi is null;

-- RLS acik, POLITIKA YOK: kimse bu tabloyu okuyamaz/yazamaz. Tek giris
-- noktasi asagidaki security definer fonksiyon. sayac_tuz ile ayni desen.
-- Politikasiz + RLS'siz tablo "herkes gorebilir" demek olurdu; RLS acik
-- ve politikasiz tablo "kimse goremez" demek.
alter table public.sahiplenme_kodu enable row level security;
revoke all on table public.sahiplenme_kodu from anon, authenticated;

-- ---------- 2. Sahiplik ----------
create table if not exists public.sahiplik (
  id           bigint generated always as identity primary key,
  -- Kullanici silinirse sahiplik de dusmeli: yetki kisiye bagli, mekana degil.
  -- (katkilar/paylasimlar'dan farkli: orada YAYIMLANMIS bilgi kaliyor.)
  kullanici    uuid not null references auth.users(id) on delete cascade,
  mekan_id     text not null check (char_length(mekan_id) between 1 and 80),
  il           text check (char_length(il) = 2),
  mekan_ad     text not null check (char_length(mekan_ad) between 1 and 200),
  dogrulandi   timestamptz not null default now(),
  durum        text not null default 'aktif' check (durum in ('aktif','iptal')),
  -- Iptal edilmisse neden: yonetici gorsun, kayit kaybolmasin.
  iptal_notu   text check (char_length(iptal_notu) <= 300),
  olusturuldu  timestamptz not null default now()
);

comment on table public.sahiplik is
  'Dogrulanmis isletme sahipligi. Kod ile kazanilir, yonetici iptal edebilir.';

-- Bir mekanin AYNI ANDA tek aktif sahibi olur. Iptal edilmis kayitlar
-- kisitin disinda: gecmis duruyor, yeni sahiplenme onunu tikamiyor.
create unique index if not exists sahiplik_tek_aktif_idx
  on public.sahiplik (mekan_id) where durum = 'aktif';
create index if not exists sahiplik_kullanici_idx
  on public.sahiplik (kullanici, dogrulandi desc);

alter table public.sahiplik enable row level security;

-- Aktif sahiplik HERKESE ACIK: isletme sayfasi "isletme dogruladi" diyor.
-- Kimin dogruladigi degil, dogrulanmis oldugu bilgisi gorunur -- kullanici
-- kimligi bu tabloda yok sayilan tek alan degil ama satirda duruyor;
-- bu yuzden asagidaki gorunum yalniz gereken kolonlari veriyor.
drop policy if exists "sahiplik aktif herkese acik" on public.sahiplik;
create policy "sahiplik aktif herkese acik" on public.sahiplik
  for select using (durum = 'aktif' or kullanici = auth.uid() or public.yonetici_mi());

-- INSERT politikasi YOK: sahiplik yalnizca kod fonksiyonuyla kazanilir.
-- Kullanici kendi sahipligini birakabilir; yonetici iptal edebilir.
drop policy if exists "sahiplik kendi birakir" on public.sahiplik;
create policy "sahiplik kendi birakir" on public.sahiplik
  for delete using (kullanici = auth.uid());

drop policy if exists "sahiplik yonetici karar verir" on public.sahiplik;
create policy "sahiplik yonetici karar verir" on public.sahiplik
  for update using (public.yonetici_mi()) with check (public.yonetici_mi());

drop policy if exists "sahiplik yonetici siler" on public.sahiplik;
create policy "sahiplik yonetici siler" on public.sahiplik
  for delete using (public.yonetici_mi());

-- Gunluk sinir: ayni kural katkilar ve paylasimlar'da da isliyor.
-- Buradaki isi kod deneme spam'ini degil (o fonksiyonun icinde), tek
-- kullanicinin bir gunde onlarca mekan sahiplenmesini sinirlamak.
drop trigger if exists sahiplik_gunluk_sinir on public.sahiplik;
create trigger sahiplik_gunluk_sinir
  before insert on public.sahiplik
  for each row execute function public.gunluk_gonderim_siniri();

-- ---------- 3. "Bu kullanici bu mekanin sahibi mi" ----------
-- Politikalarin icinden cagriliyor; stable ve security definer olmali,
-- yoksa cagiran kullanicinin RLS'i tekrar devreye girip dongu yapar.
create or replace function public.sahibi_mi(p_mekan_id text)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1 from public.sahiplik
    where mekan_id = p_mekan_id
      and kullanici = auth.uid()
      and durum = 'aktif'
  );
$$;

revoke all on function public.sahibi_mi(text) from public;
grant execute on function public.sahibi_mi(text) to anon, authenticated;

-- ---------- 4. Kodu kullan ----------
-- Tek yazma yolu. security definer: kod tablosunu kimse goremiyor,
-- bu fonksiyon gorebiliyor.
create or replace function public.sahiplenme_kodu_kullan(p_kod text)
returns table (mekan_id text, il text, mekan_ad text)
language plpgsql
security definer
set search_path = public
as $$
declare
  ozet text;
  k    public.sahiplenme_kodu%rowtype;
begin
  if auth.uid() is null then
    raise exception 'sahiplenme icin giris yapilmali'
      using errcode = 'insufficient_privilege';
  end if;

  -- Bosluk ve buyuk/kucuk harf normalize: kart elle okunup yaziliyor.
  -- Kartta yalniz A-Z ve 2-9 var (bkz. saha.py KOD_ALFABE), o yuzden
  -- once temizleyip sonra ozetliyoruz.
  ozet := encode(digest(upper(regexp_replace(coalesce(p_kod, ''), '[^A-Za-z0-9]', '', 'g')),
                        'sha256'), 'hex');

  select * into k from public.sahiplenme_kodu
   where kod_ozeti = ozet
   for update;

  -- Ayni mesaj: gecersiz kod ile kullanilmis kod ayirt edilemesin.
  -- Ayirt edilebilirse gecerli kod aramak icin bir sinyal olur.
  if not found or k.kullanildi is not null or k.gecerlilik < current_date then
    raise exception 'kod gecersiz'
      using errcode = 'check_violation';
  end if;

  if exists (select 1 from public.sahiplik
              where sahiplik.mekan_id = k.mekan_id and durum = 'aktif') then
    raise exception 'bu isletme zaten sahiplenilmis'
      using errcode = 'check_violation';
  end if;

  insert into public.sahiplik (kullanici, mekan_id, il, mekan_ad)
  values (auth.uid(), k.mekan_id, k.il, k.mekan_ad);

  update public.sahiplenme_kodu
     set kullanan = auth.uid(), kullanildi = now()
   where kod_ozeti = ozet;

  return query select k.mekan_id, k.il, k.mekan_ad;
end;
$$;

revoke all on function public.sahiplenme_kodu_kullan(text) from public;
grant execute on function public.sahiplenme_kodu_kullan(text) to authenticated;

-- ---------- 5. Sahibinin katkisi kuyruga girmiyor ----------
-- Sahibin KENDI mekani icin gonderdigi olgusal alan dogrudan yayina cikar.
-- Gerekce: bu bilgiler kapida okunabiliyor, yanlissa zarari sinirli ve
-- geri alinabilir; isletme de en iyi kaynak. Kuyrukta bekletmek, isletmenin
-- bir daha ugramamasinin en kisa yolu.
create or replace function public.sahip_katkisi_onayli()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.kullanici is not null
     and new.durum = 'bekliyor'
     and public.sahibi_mi(new.mekan_id) then
    new.durum := 'onaylandi';
  end if;
  return new;
end;
$$;

drop trigger if exists katki_sahip_onayi on public.katkilar;
create trigger katki_sahip_onayi
  before insert on public.katkilar
  for each row execute function public.sahip_katkisi_onayli();

-- Politika tetikleyiciden SONRA degerlendiriliyor: tetikleyici durumu
-- 'onaylandi' yaptigi icin duz "durum = 'bekliyor'" politikasi insert'i
-- reddederdi. Politika, onayli girisi YALNIZ sahibine aciyor.
--
-- Ayni tanim katki.sql'de de var (orada sahibi_mi() bos govdeyle kurulup
-- false donuyor). Burada tekrar yaziliyor ki iki dosyanin hangi sirayla
-- calistirildigi sonucu degistirmesin.
drop policy if exists "katki kendi ekler" on public.katkilar;
create policy "katki kendi ekler" on public.katkilar
  for insert with check (
    kullanici = auth.uid()
    and (durum = 'bekliyor'
         or (durum = 'onaylandi' and public.sahibi_mi(mekan_id)))
  );

-- ============================================================
-- Sütun yetkisi — kimin kim olduğu tarayıcıya inmiyor
--
-- Gerekce sema.sql'in ayni basligi altinda yazili ve gercek Postgres'te
-- olculdu: RLS SATIR duzeyinde calisir, satiri actiginda icindeki
-- `kullanici` sutunu da aciliyordu. Ayni uuid ucuncu tabloda birden
-- gorundugu icin izler birlestirilebiliyordu.
--
-- Burasi ayrica sozu tutmakla ilgili: kimlik.js'te "sahibin KIMLIGI
-- dondurulmuyor -- gorunur olan bilgi 'dogrulanmis', 'kim dogruladi'
-- degil" yaziyordu, ama bunu yalniz istemcinin select listesi
-- sagliyordu. Anahtari olan herkes kendi sorgusunu yazabilir. Politikalar sutun yetkisi
-- olmadan da calisiyor (olculdu).
-- ============================================================
revoke select on public.sahiplik from anon, authenticated;
grant  select (id, mekan_id, mekan_ad, il, dogrulandi, durum, iptal_notu)
  on public.sahiplik to anon, authenticated;

-- ============================================================
-- Kendini kontrol — bu blok hata vermeden geçmeli
-- ============================================================
do $$
declare
  n int;
begin
  if not exists (select 1 from pg_proc where proname = 'yonetici_mi'
                 and pronamespace = 'public'::regnamespace) then
    raise exception 'Once sema.sql calistirilmali: yonetici_mi() yok';
  end if;
  if not exists (select 1 from pg_tables where schemaname = 'public'
                 and tablename = 'katkilar') then
    raise exception 'Once katki.sql calistirilmali: katkilar tablosu yok';
  end if;
  if not exists (select 1 from pg_proc where proname = 'digest') then
    raise exception 'pgcrypto yok: "create extension if not exists pgcrypto;" calistir';
  end if;

  -- Kod tablosu gercekten kapali mi: politika sayisi SIFIR olmali.
  select count(*) into n from pg_policies
   where schemaname = 'public' and tablename = 'sahiplenme_kodu';
  if n <> 0 then
    raise exception 'sahiplenme_kodu uzerinde % politika var, olmamali', n;
  end if;
  if not exists (select 1 from pg_tables where schemaname = 'public'
                 and tablename = 'sahiplenme_kodu' and rowsecurity = true) then
    raise exception 'RLS acik degil: sahiplenme_kodu';
  end if;
  if not exists (select 1 from pg_tables where schemaname = 'public'
                 and tablename = 'sahiplik' and rowsecurity = true) then
    raise exception 'RLS acik degil: sahiplik';
  end if;

  select count(*) into n from pg_policies
   where schemaname = 'public' and tablename = 'sahiplik';
  if n < 4 then
    raise exception 'sahiplik politikalari eksik: % (en az 4 olmali)', n;
  end if;

  raise notice 'Sahiplenme kuruldu: kod tablosu kapali, sahiplik % politika', n;
end;
$$;
