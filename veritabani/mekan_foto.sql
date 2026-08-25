-- ============================================================
-- Cebimde — mekan fotoğrafları
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir. sema.sql ve sahiplenme.sql'den SONRA.
--
-- NEDEN AYRI BİR TABLO: menu_katkilari MENÜYÜ fotoğraflıyor (kağıt, tabela,
-- ürün). Burası MEKANI fotoğraflıyor (bahçe, iç mekan, cephe). İki ayrı
-- şey ve ölçütleri de ayrı: menü fotoğrafında aranan şey okunabilirlik,
-- mekan fotoğrafında aranan şey İÇİNDE İNSAN OLMAMASI. Bir kafenin
-- salonunu çeken kullanıcı orada oturan insanları da çeker; o insanlar
-- fotoğraflanmayı kabul etmedi. Aynı tabloda toplamak, iki farklı onay
-- ölçütünü tek listede karıştırmak olurdu.
--
-- ÜÇ KAYNAK, ÜÇ AYRI GÜVEN SEVİYESİ (kaynak sütunu):
--   'sahip'    -> doğrulanmış işletme sahibi yükledi. En temiz kaynak:
--                 mekanın kendi fotoğrafı, yayımlama hakkı kendisinde.
--   'kullanici'-> giden biri çekti. Onaydan geçer.
--   'commons'  -> Wikimedia Commons / Wikidata (foto_cek.py). Serbest
--                 lisanslı, ATIF ZORUNLU -- yazar ve lisans saklanıyor.
--
-- GOOGLE MAPS VE BENZERİ KAYNAKLAR BURAYA GİRMEZ. Teknik bir sınır değil:
-- o fotoğraflar yazarlarının telifinde ve platforma lisanslı; kendi
-- sitende yayımlama hakkın yok. CEBIMDE.md "Yapılmayacaklar" listesinde
-- yazılı bir karar. Bu yüzden kaynak sütunu SERBEST METİN DEĞİL, kısıtlı.
-- ============================================================

create table if not exists public.mekan_fotolari (
  id           bigint generated always as identity primary key,
  -- Commons'tan gelen satırın kullanıcısı yok; kullanıcı silinirse de
  -- fotoğraf kalır ama sahipsizleşir (diğer tablolarla aynı kural).
  kullanici    uuid references auth.users(id) on delete set null,
  mekan_id     text not null check (char_length(mekan_id) between 1 and 80),
  il           text check (char_length(il) = 2),
  mekan_ad     text not null check (char_length(mekan_ad) between 2 and 200),

  -- Depolama kovasındaki yol (yüklenenler) YA DA tam adres (Commons).
  -- İkisinden tam olarak biri dolu olmalı.
  yol          text check (yol is null or char_length(yol) between 3 and 300),
  adres        text check (adres is null or char_length(adres) between 10 and 500),

  aciklama     text check (aciklama is null or char_length(aciklama) between 2 and 200),

  kaynak       text not null default 'kullanici'
               check (kaynak in ('sahip','kullanici','commons')),

  -- ATIF. Commons lisansları (CC BY, CC BY-SA) yazar adını ve lisansı
  -- göstermeyi ZORUNLU kılıyor; göstermeyen kullanım lisansı ihlal eder.
  -- Bu yüzden kaynak 'commons' ise ikisi de dolu olmak zorunda.
  yazar        text check (yazar is null or char_length(yazar) between 1 and 200),
  lisans       text check (lisans is null or char_length(lisans) between 2 and 100),
  kaynak_bag   text check (kaynak_bag is null or char_length(kaynak_bag) between 10 and 500),

  durum        text not null default 'bekliyor'
               check (durum in ('bekliyor','onaylandi','reddedildi')),
  olusturuldu  timestamptz not null default now(),

  -- Ya yüklenmiş dosya, ya dış adres; ikisi birden olmaz.
  constraint mekan_fotolari_tek_kaynak_check
    check ((yol is not null) <> (adres is not null)),

  -- Commons fotoğrafı ATIFSIZ giremez. Kısıt burada, istemcide değil:
  -- atıfsız yayımlamak lisansı ihlal eder ve bunu unutmak kolaydır.
  constraint mekan_fotolari_atif_check
    check (kaynak <> 'commons' or (yazar is not null and lisans is not null
                                   and kaynak_bag is not null))
);

comment on table public.mekan_fotolari is
  'Mekan fotografi. Kaynak: sahip / kullanici / commons. Commons ATIFSIZ giremez. Google Maps vb. GIRMEZ -- yayimlama hakki yok.';

create index if not exists mekan_fotolari_durum_idx
  on public.mekan_fotolari (durum, olusturuldu desc);
create index if not exists mekan_fotolari_kullanici_idx
  on public.mekan_fotolari (kullanici, olusturuldu desc);
create index if not exists mekan_fotolari_mekan_idx
  on public.mekan_fotolari (mekan_id) where durum = 'onaylandi';

-- Aynı adres iki kez girmesin: foto_cek.py tekrar çalıştırılabilir olmalı
-- ve her çalıştırmada kopya üretmemeli.
create unique index if not exists mekan_fotolari_adres_idx
  on public.mekan_fotolari (mekan_id, adres) where adres is not null;

drop trigger if exists mekan_foto_gunluk_sinir on public.mekan_fotolari;
create trigger mekan_foto_gunluk_sinir
  before insert on public.mekan_fotolari
  for each row execute function public.gunluk_gonderim_siniri();

-- ============================================================
-- İşletme sahibinin fotoğrafı doğrudan yayında
--
-- Sahiplik SAHADA, elden verilen bir kodla kazanılıyor; kanıtladığı şey
-- fiziksel olarak orada bulunmak. Kendi mekanının fotoğrafını yükleyen
-- sahibi kuyrukta bekletmenin bir karşılığı yok -- katkilar'da aynı kural
-- var (sahip_katkisi_onayli).
--
-- Sahip DEĞİLSE durum 'bekliyor'da kalıyor; kullanıcı bunu kendi
-- belirleyemiyor (aşağıdaki politika).
-- ============================================================
create or replace function public.sahip_fotosu_onayli()
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
    new.kaynak := 'sahip';
  end if;
  return new;
end;
$$;

drop trigger if exists mekan_foto_sahip_onayi on public.mekan_fotolari;
create trigger mekan_foto_sahip_onayi
  before insert on public.mekan_fotolari
  for each row execute function public.sahip_fotosu_onayli();

-- ============================================================
-- RLS
-- ============================================================
alter table public.mekan_fotolari enable row level security;

drop policy if exists "mekan foto onaylanmis herkese acik" on public.mekan_fotolari;
create policy "mekan foto onaylanmis herkese acik" on public.mekan_fotolari
  for select using (durum = 'onaylandi' or kullanici = auth.uid() or public.yonetici_mi());

-- Kullanıcı YALNIZ 'bekliyor' ile yazabilir; sahibiyse tetikleyici
-- yukarıda onaylıyor (tetikleyici WITH CHECK'ten ÖNCE çalışıyor, o yüzden
-- politika sahibin satırını da 'onaylandi' halinde görüyor).
drop policy if exists "mekan foto kendi ekler" on public.mekan_fotolari;
create policy "mekan foto kendi ekler" on public.mekan_fotolari
  for insert with check (
    kullanici = auth.uid()
    and kaynak in ('kullanici','sahip')          -- 'commons' istemciden GİRMEZ
    and (durum = 'bekliyor'
         or (durum = 'onaylandi' and public.sahibi_mi(mekan_id)))
  );

drop policy if exists "mekan foto kendi siler" on public.mekan_fotolari;
create policy "mekan foto kendi siler" on public.mekan_fotolari
  for delete using (kullanici = auth.uid());

drop policy if exists "mekan foto yonetici karar verir" on public.mekan_fotolari;
create policy "mekan foto yonetici karar verir" on public.mekan_fotolari
  for update using (public.yonetici_mi()) with check (public.yonetici_mi());

drop policy if exists "mekan foto yonetici siler" on public.mekan_fotolari;
create policy "mekan foto yonetici siler" on public.mekan_fotolari
  for delete using (public.yonetici_mi());

-- ============================================================
-- Sütun yetkisi
-- ============================================================
revoke select on public.mekan_fotolari from anon, authenticated;
grant  select (id, mekan_id, mekan_ad, il, yol, adres, aciklama, kaynak,
               yazar, lisans, kaynak_bag, durum, olusturuldu)
  on public.mekan_fotolari to anon, authenticated;

-- ============================================================
-- Bir mekanın onaylı fotoğrafları
--
-- Sıra: önce SAHİP, sonra kullanıcı, sonra commons. Sahibin fotoğrafı
-- mekanı en iyi temsil eden ve yayımlama hakkı en net olandır.
-- ============================================================
create or replace function public.mekan_fotograflari(p_mekan_id text)
returns table (
  id          bigint,
  yol         text,
  adres       text,
  aciklama    text,
  kaynak      text,
  yazar       text,
  lisans      text,
  kaynak_bag  text,
  olusturuldu timestamptz
)
language sql
stable
security definer
set search_path = public
as $$
  select f.id, f.yol, f.adres, f.aciklama, f.kaynak,
         f.yazar, f.lisans, f.kaynak_bag, f.olusturuldu
  from public.mekan_fotolari f
  where f.mekan_id = p_mekan_id and f.durum = 'onaylandi'
  order by case f.kaynak when 'sahip' then 0 when 'kullanici' then 1 else 2 end,
           f.olusturuldu desc
  limit 24;
$$;
revoke all on function public.mekan_fotograflari(text) from public;
grant execute on function public.mekan_fotograflari(text) to anon, authenticated;

-- ============================================================
-- Fotoğraf deposu
--
-- EXIF: yüklenen dosya tarayıcıda yeniden kodlanıyor (ortak.js →
-- resimHazirla) ve GPS/cihaz bilgisi düşüyor. Mekan fotoğrafında bu
-- menüdekinden DAHA önemli: menü fotoğrafı zaten mekanın içinde çekiliyor
-- ve konumu zaten biliniyor, ama fotoğrafı çeken kişinin CİHAZ KİMLİĞİ
-- onun başka fotoğraflarıyla eşleştirilebilir.
-- ============================================================
do $$
begin
  if not exists (select 1 from information_schema.schemata where schema_name = 'storage') then
    raise notice 'storage semasi yok (yerel Postgres): mekan kovasi atlandi';
    return;
  end if;

  insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
  values ('mekan', 'mekan', true, 3145728, array['image/jpeg','image/webp'])
  on conflict (id) do update
    set public = true,
        file_size_limit = 3145728,
        allowed_mime_types = array['image/jpeg','image/webp'];

  execute 'drop policy if exists "mekan foto herkes okur" on storage.objects';
  execute $p$create policy "mekan foto herkes okur" on storage.objects
             for select using (bucket_id = 'mekan')$p$;

  execute 'drop policy if exists "mekan foto kendi yazar" on storage.objects';
  execute $p$create policy "mekan foto kendi yazar" on storage.objects
             for insert to authenticated
             with check (bucket_id = 'mekan'
                         and (storage.foldername(name))[1] = auth.uid()::text)$p$;

  execute 'drop policy if exists "mekan foto kendi siler dosya" on storage.objects';
  execute $p$create policy "mekan foto kendi siler dosya" on storage.objects
             for delete to authenticated
             using (bucket_id = 'mekan'
                    and (storage.foldername(name))[1] = auth.uid()::text)$p$;
  -- Guncelleme politikasi BILEREK yok: onaydan gecen resim ile yayindaki
  -- resim ayri seyler olabilirdi (menu kovasiyla ayni gerekce).
end $$;

-- ============================================================
-- Kendini kontrol
-- ============================================================
do $$
declare
  n int;
begin
  if not exists (select 1 from pg_proc where proname = 'sahibi_mi'
                 and pronamespace = 'public'::regnamespace) then
    raise exception 'Once sahiplenme.sql calistirilmali: sahibi_mi() yok';
  end if;

  if not exists (select 1 from pg_tables where schemaname = 'public'
                 and tablename = 'mekan_fotolari' and rowsecurity = true) then
    raise exception 'RLS acik degil: mekan_fotolari';
  end if;

  select count(*) into n from pg_policies
   where schemaname = 'public' and tablename = 'mekan_fotolari';
  if n < 5 then
    raise exception 'mekan foto politikalari eksik: % (en az 5 olmali)', n;
  end if;

  if has_column_privilege('anon', 'public.mekan_fotolari', 'kullanici', 'SELECT') then
    raise exception 'anon mekan_fotolari.kullanici sutununu okuyabiliyor';
  end if;

  raise notice 'Mekan fotografi kuruldu: RLS acik, % politika, atif zorunlu', n;
end;
$$;
