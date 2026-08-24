-- ============================================================
-- Oturalım — genişletilmiş profil
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir: her şey "if not exists" / "or replace".
-- sema.sql'den SONRA çalıştırılmalı.
--
-- NEDEN VAR: yorumlar geliyor ve bir yorum, YAZANI olmadan yarım bir
-- bilgidir. "Burası pahalı" cümlesini 19 yaşındaki öğrenci de yazar,
-- 45 yaşındaki mühendis de; okuyanın kendine yakın olanı tartabilmesi
-- lazım. profiller tablosunda yalnız "ad" vardı.
--
-- ÜÇ KURAL, üçü de kasıtlı:
--
-- 1) HEPSİ İSTEĞE BAĞLI. Yaşını yazmayan biri yorum yazamasın demek,
--    veriyi zorla toplamak olurdu. gizlilik.html'deki "veri en aza
--    indirildi" sözü bunu gerektiriyor.
--
-- 2) DOĞUM YILI saklanıyor, yaş değil. Yaş her yıl eskir; doğum yılı
--    eskimez ve daha az şey söyler (gün/ay yok). Ekranda yaşa çevriliyor.
--
-- 3) KİMLİK NUMARASI DIŞARI ÇIKMIYOR. Profil sayfası uuid ile değil
--    KULLANICI ADIYLA açılıyor. Bu bir üslup tercihi değil: sema.sql'in
--    "Sütun yetkisi" bölümü `kullanici` sütununu üç tabloda birden
--    kapattı, çünkü o uuid ile bir kişinin dışarı çıkma geçmişi
--    birleştirilebiliyordu. Profili uuid ile açılabilir yapmak, kapatılan
--    kapıyı yandan geri açardı.
-- ============================================================

-- ---------- 1. Alanlar ----------
-- Tablo sema.sql'de kuruldu; burada yalnız yeni sütunlar ekleniyor.
alter table public.profiller add column if not exists kullanici_adi text;
alter table public.profiller add column if not exists dogum_yili    integer;
alter table public.profiller add column if not exists meslek        text;
alter table public.profiller add column if not exists kisilik       text;
alter table public.profiller add column if not exists avatar        text;
alter table public.profiller add column if not exists herkese_acik  boolean not null default true;

do $$ begin
  -- Kısıtlar ayrı ekleniyor: sütunlar zaten varsa da tazelensin.
  alter table public.profiller drop constraint if exists profiller_kullanici_adi_check;
  alter table public.profiller add constraint profiller_kullanici_adi_check
    check (kullanici_adi is null or kullanici_adi ~ '^[a-z0-9_]{3,20}$');

  -- 13 yaş alt sınırı: altındaki için veli onayı gerekir ve bu yapıda
  -- alınamıyor. Üst sınır 1900 -- yazım hatasını (1090) eliyor.
  alter table public.profiller drop constraint if exists profiller_dogum_yili_check;
  alter table public.profiller add constraint profiller_dogum_yili_check
    check (dogum_yili is null or
           (dogum_yili >= 1900 and dogum_yili <= extract(year from now())::int - 13));

  alter table public.profiller drop constraint if exists profiller_meslek_check;
  alter table public.profiller add constraint profiller_meslek_check
    check (meslek is null or char_length(meslek) between 2 and 60);

  alter table public.profiller drop constraint if exists profiller_kisilik_check;
  alter table public.profiller add constraint profiller_kisilik_check
    check (kisilik is null or char_length(kisilik) between 2 and 300);

  -- Avatar YOLU saklanıyor, resmin kendisi değil. Depolama kovasındaki
  -- yol; biçimi "<uuid>/<ad>.<uzanti>". Tam adres istemcide kuruluyor.
  alter table public.profiller drop constraint if exists profiller_avatar_check;
  alter table public.profiller add constraint profiller_avatar_check
    check (avatar is null or char_length(avatar) between 3 and 300);
end $$;

-- Kullanıcı adı tekil. Büyük/küçük harf sorunu yok: kısıt zaten yalnız
-- küçük harf kabul ediyor.
create unique index if not exists profiller_kullanici_adi_idx
  on public.profiller (kullanici_adi) where kullanici_adi is not null;

comment on column public.profiller.kullanici_adi is
  'Profil adresi (profil.html?k=...). uuid DISARI CIKMIYOR; bkz. sema.sql "Sutun yetkisi".';
comment on column public.profiller.dogum_yili is
  'Yas degil DOGUM YILI: yas her yil eskir, dogum yili eskimez ve daha az sey soyler.';

-- ---------- 2. Kullanıcı adı üretimi ----------
-- Her profilin bir adresi olmalı, yoksa yorumun yazarına tıklanamaz.
-- Kullanıcı sonradan değiştirebiliyor.
create or replace function public.kullanici_adi_uret()
returns text
language plpgsql
volatile
set search_path = public
as $$
declare
  aday text;
  i    int := 0;
begin
  loop
    -- "kisi" + 8 haneli taban-36. Sırayla artan bir sayı OLMAZ: kaç
    -- kullanıcı olduğunu ve kimin ne zaman katıldığını ifşa ederdi.
    aday := 'kisi' || lpad(to_hex((random() * 4294967295)::bigint), 8, '0');
    exit when not exists (select 1 from public.profiller where kullanici_adi = aday);
    i := i + 1;
    if i > 20 then
      return null;   -- olmayacak iş; adsız profil, adresi olmayan profildir
    end if;
  end loop;
  return aday;
end;
$$;

-- Yeni kullanıcıya ad üret. sema.sql'deki tetikleyicinin yerini alıyor;
-- oradaki hâli yalnız (id, ad) yazıyordu.
create or replace function public.yeni_kullanici_profili()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiller (id, ad, kullanici_adi)
  values (new.id, nullif(new.raw_user_meta_data->>'ad', ''),
          public.kullanici_adi_uret())
  on conflict (id) do nothing;
  return new;
end;
$$;

-- Bu dosyadan ÖNCE kayıt olmuş kullanıcıların adı yok; doldur.
update public.profiller set kullanici_adi = public.kullanici_adi_uret()
 where kullanici_adi is null;

-- ---------- 3. Kilitli alanlar ----------
-- yonetici alanı sema.sql'de kilitli. Aynı korumaya kullanıcı adı da
-- giriyor mu? HAYIR, bilerek: kullanıcı adını değiştirebilmeli.
-- Ama BAŞKASININ adını alamamalı -- onu tekil indeks durduruyor.

-- ---------- 4. Herkese açık profil ----------
-- profiller tablosunun okuma politikası "yalnız kendi satırın" diyor ve
-- ÖYLE KALIYOR. Dışarıya açılan şey tablo değil, aşağıdaki fonksiyon:
-- yalnız gerekli sütunları, yalnız profilini açık tutan kullanıcılar için
-- döndürüyor. Politikayı gevşetmek e-posta/uuid eşlemesini de açardı.
create or replace function public.profil_getir(p_kullanici_adi text)
returns table (
  kullanici_adi text,
  ad            text,
  dogum_yili    integer,
  meslek        text,
  kisilik       text,
  avatar        text,
  katildi       timestamptz
)
language sql
stable
security definer
set search_path = public
as $$
  select p.kullanici_adi, p.ad, p.dogum_yili, p.meslek, p.kisilik,
         p.avatar, p.olusturuldu
  from public.profiller p
  where p.kullanici_adi = lower(p_kullanici_adi)
    and p.herkese_acik = true;
$$;
revoke all on function public.profil_getir(text) from public;
grant execute on function public.profil_getir(text) to anon, authenticated;

comment on function public.profil_getir is
  'Herkese acik profil. id/e-posta DONMEZ; profilini kapatan kullanici hic donmez.';

-- ---------- 5. Avatar deposu ----------
-- Supabase Storage. Yerel Postgres'te "storage" şeması yok, o yüzden
-- tamamı korumalı: test ortamında sessizce atlanıyor, Supabase'de kuruluyor.
do $$
begin
  if not exists (select 1 from information_schema.schemata where schema_name = 'storage') then
    raise notice 'storage semasi yok (yerel Postgres): avatar kovasi atlandi';
    return;
  end if;

  insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
  values ('avatar', 'avatar', true, 2097152,
          array['image/jpeg','image/png','image/webp'])
  on conflict (id) do update
    set public = true,
        file_size_limit = 2097152,       -- 2 MB; profil fotografi icin fazlasiyla yeter
        allowed_mime_types = array['image/jpeg','image/png','image/webp'];

  -- Okuma herkese açık: avatar zaten profil sayfasında görünüyor.
  execute 'drop policy if exists "avatar herkes okur" on storage.objects';
  execute $p$create policy "avatar herkes okur" on storage.objects
             for select using (bucket_id = 'avatar')$p$;

  -- Yazma YALNIZ kendi klasörüne. Klasör adı kullanıcının uuid'si:
  -- boyle olmasa biri baskasinin avatarini ezebilirdi.
  execute 'drop policy if exists "avatar kendi yazar" on storage.objects';
  execute $p$create policy "avatar kendi yazar" on storage.objects
             for insert to authenticated
             with check (bucket_id = 'avatar'
                         and (storage.foldername(name))[1] = auth.uid()::text)$p$;

  execute 'drop policy if exists "avatar kendi gunceller" on storage.objects';
  execute $p$create policy "avatar kendi gunceller" on storage.objects
             for update to authenticated
             using (bucket_id = 'avatar'
                    and (storage.foldername(name))[1] = auth.uid()::text)$p$;

  execute 'drop policy if exists "avatar kendi siler" on storage.objects';
  execute $p$create policy "avatar kendi siler" on storage.objects
             for delete to authenticated
             using (bucket_id = 'avatar'
                    and (storage.foldername(name))[1] = auth.uid()::text)$p$;
end $$;

-- ============================================================
-- Kendini kontrol — bu blok hata vermeden geçmeli
-- ============================================================
do $$
declare
  n int;
begin
  -- Sütunlar gerçekten eklendi mi
  select count(*) into n from information_schema.columns
   where table_schema = 'public' and table_name = 'profiller'
     and column_name in ('kullanici_adi','dogum_yili','meslek','kisilik',
                         'avatar','herkese_acik');
  if n <> 6 then
    raise exception 'profil alanlari eksik: % / 6', n;
  end if;

  -- Adsız profil kalmamalı: adı olmayan profilin adresi yok, yani
  -- yorumunun yazarına tıklanamaz.
  select count(*) into n from public.profiller where kullanici_adi is null;
  if n > 0 then
    raise exception 'kullanici adi olmayan % profil kaldi', n;
  end if;

  -- profiller tablosu HÂLÂ dışarıya kapalı olmalı. Açılırsa uuid ve
  -- profil eşlemesi dışarı çıkar; herkese açık yol yalnız fonksiyon.
  if exists (select 1 from pg_policies
              where schemaname = 'public' and tablename = 'profiller'
                and cmd = 'SELECT' and coalesce(qual,'') not like '%auth.uid()%') then
    raise exception 'profiller tablosuna kosulsuz okuma politikasi eklenmis';
  end if;

  raise notice 'Profil kuruldu: 6 alan, kullanici adi uretiliyor, tablo kapali';
end;
$$;
