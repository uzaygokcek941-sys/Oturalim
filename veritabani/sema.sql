-- ============================================================
-- Oturalım — veritabanı şeması ve güvenlik politikaları
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir: her şey "if not exists" / "or replace".
--
-- Tasarım kuralı: yetki uygulamada değil VERİTABANINDA. Tarayıcıdan
-- gelen anon anahtar herkese açıktır; kimin neyi görebileceğine
-- RLS politikaları karar verir. İstemci kodu atlanabilir, RLS atlanamaz.
-- ============================================================

-- ---------- 1. Profiller ----------
-- auth.users Supabase'in kendi tablosu; ona dokunulmaz.
-- Uygulamaya ait alanlar (görünen ad, yöneticilik) burada durur.
create table if not exists public.profiller (
  id           uuid primary key references auth.users(id) on delete cascade,
  ad           text check (char_length(ad) between 1 and 60),
  yonetici     boolean not null default false,
  olusturuldu  timestamptz not null default now()
);

comment on table public.profiller is 'Kullanicinin uygulamaya ait bilgileri. Kimlik dogrulama auth.users tarafinda.';

-- Yeni kayıt olan herkese otomatik profil.
-- security definer: tetikleyici RLS'e takılmadan yazabilmeli.
create or replace function public.yeni_kullanici_profili()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiller (id, ad)
  values (new.id, nullif(new.raw_user_meta_data->>'ad', ''))
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists yeni_kullanici on auth.users;
create trigger yeni_kullanici
  after insert on auth.users
  for each row execute function public.yeni_kullanici_profili();

-- Yöneticilik kontrolü ayrı bir fonksiyonda.
-- Politikanın içinden doğrudan profiller'e bakmak sonsuz döngü yapardı
-- (profiller politikasi -> profiller sorgusu -> politika -> ...).
create or replace function public.yonetici_mi()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select coalesce((select yonetici from public.profiller where id = auth.uid()), false);
$$;

-- ---------- 2. Favoriler ----------
-- mekan_id OSM kimliği ("node/12271185542"). Mekan verisi statik JSON'da
-- durduğu için burada yabancı anahtar yok; ad ve il kopyalanıyor ki
-- favori listesi tek sorguda çizilebilsin.
create table if not exists public.favoriler (
  kullanici  uuid not null references auth.users(id) on delete cascade,
  mekan_id   text not null check (char_length(mekan_id) between 1 and 80),
  il         text not null check (char_length(il) = 2),
  mekan_ad   text not null check (char_length(mekan_ad) between 1 and 200),
  eklendi    timestamptz not null default now(),
  primary key (kullanici, mekan_id)
);

create index if not exists favoriler_kullanici_idx on public.favoriler (kullanici, eklendi desc);

-- ---------- 3. Fiyat paylaşımları ----------
-- Kullanıcı silinirse paylaşım kalır ama sahipsizleşir (set null):
-- yayımlanmış fiyat verisi kişiye değil mekana bağlı.
create table if not exists public.paylasimlar (
  id           bigint generated always as identity primary key,
  kullanici    uuid references auth.users(id) on delete set null,
  mekan_id     text,
  mekan_ad     text not null check (char_length(mekan_ad) between 2 and 200),
  il           text check (char_length(il) = 2),
  tutar        numeric(10,2) not null check (tutar > 0 and tutar <= 1000000),
  kisi         integer not null check (kisi between 1 and 30),
  tarih        date not null default current_date check (tarih <= current_date),
  aciklama     text check (char_length(aciklama) <= 500),
  durum        text not null default 'bekliyor'
               check (durum in ('bekliyor','onaylandi','reddedildi')),
  olusturuldu  timestamptz not null default now()
);

create index if not exists paylasimlar_durum_idx     on public.paylasimlar (durum, olusturuldu desc);
create index if not exists paylasimlar_kullanici_idx on public.paylasimlar (kullanici, olusturuldu desc);
create index if not exists paylasimlar_mekan_idx     on public.paylasimlar (mekan_id) where durum = 'onaylandi';

-- Aynı kişi aynı mekan için aynı gün birden fazla kayıt açamaz.
-- Spam ve yanlışlıkla çift gönderimi burada durduruyoruz; istemci
-- doğrulaması atlanabilir, bu kısıt atlanamaz.
create unique index if not exists paylasimlar_tek_kayit_idx
  on public.paylasimlar (kullanici, mekan_ad, tarih)
  where kullanici is not null;

-- ---------- Günlük gönderim sınırı ----------
-- Tekil kısıt "aynı kişi aynı mekan için aynı gün bir kayıt" diyor ama
-- FARKLI mekan adlarıyla sınırsız kayıt açmayı durdurmuyordu. Kuyruğu tek
-- kişi temizlediği için bu, sistemi çalışamaz hale getirmenin en ucuz yolu.
--
-- Sınır cömert: gerçekten katkı veren biri bir günde 50 kayıt açmaz, ama
-- 50 satır bir yöneticinin elle temizleyebileceği miktardır.
--
-- Yönetici muaf: sahadan toplu veri giren kişi aynı zamanda onaylayan kişi.
create or replace function public.gunluk_gonderim_siniri()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  adet  int;
  sinir constant int := 50;
begin
  if new.kullanici is null or public.yonetici_mi() then
    return new;
  end if;
  -- tg_table_name sistemden geliyor; yine de %I ile tirnaklaniyor.
  execute format(
    'select count(*) from public.%I where kullanici = $1 and olusturuldu >= current_date',
    tg_table_name) into adet using new.kullanici;
  if adet >= sinir then
    raise exception 'gunluk gonderim siniri doldu (%)', sinir
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

drop trigger if exists paylasim_gunluk_sinir on public.paylasimlar;
create trigger paylasim_gunluk_sinir
  before insert on public.paylasimlar
  for each row execute function public.gunluk_gonderim_siniri();

-- ============================================================
-- RLS — satır seviyesi güvenlik
-- ============================================================
alter table public.profiller   enable row level security;
alter table public.favoriler   enable row level security;
alter table public.paylasimlar enable row level security;

-- ---------- profiller ----------
drop policy if exists "profil kendi okur" on public.profiller;
create policy "profil kendi okur" on public.profiller
  for select using (id = auth.uid() or public.yonetici_mi());

drop policy if exists "profil kendi gunceller" on public.profiller;
create policy "profil kendi gunceller" on public.profiller
  for update using (id = auth.uid()) with check (id = auth.uid());

-- Kullanıcı kendini yönetici yapamasın: politika satırı açıyor,
-- tetikleyici alanı kilitliyor.
create or replace function public.yonetici_alani_korumali()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  -- auth.uid() NULL ise istek SQL Editor'den veya servis rolunden geliyor:
  -- veritabani sahibi ilk yoneticiyi atayabilmeli, yoksa kimse yonetici
  -- olamaz (tavuk-yumurta). Tarayicidan gelen anonim istegi zaten RLS'in
  -- "id = auth.uid()" kosulu durduruyor; burasi ikinci savunma katmani.
  if auth.uid() is not null
     and new.yonetici is distinct from old.yonetici
     and not public.yonetici_mi() then
    raise exception 'yonetici alani degistirilemez';
  end if;
  return new;
end;
$$;

drop trigger if exists profil_yonetici_koru on public.profiller;
create trigger profil_yonetici_koru
  before update on public.profiller
  for each row execute function public.yonetici_alani_korumali();

-- ---------- favoriler ----------
drop policy if exists "favori kendi okur" on public.favoriler;
create policy "favori kendi okur" on public.favoriler
  for select using (kullanici = auth.uid());

drop policy if exists "favori kendi ekler" on public.favoriler;
create policy "favori kendi ekler" on public.favoriler
  for insert with check (kullanici = auth.uid());

drop policy if exists "favori kendi siler" on public.favoriler;
create policy "favori kendi siler" on public.favoriler
  for delete using (kullanici = auth.uid());

-- ---------- paylaşımlar ----------
-- Onaylanmış paylaşımı herkes görür (giriş yapmamış ziyaretçi dahil):
-- fiyat verisi ürünün kamuya açık kısmı.
drop policy if exists "onaylanmis herkese acik" on public.paylasimlar;
create policy "onaylanmis herkese acik" on public.paylasimlar
  for select using (durum = 'onaylandi' or kullanici = auth.uid() or public.yonetici_mi());

drop policy if exists "paylasim kendi ekler" on public.paylasimlar;
create policy "paylasim kendi ekler" on public.paylasimlar
  for insert with check (kullanici = auth.uid() and durum = 'bekliyor');

-- Kullanıcı kendi kaydını yalnızca beklemedeyken düzeltebilir;
-- onaylandıktan sonra veri yayımlanmış sayılır.
drop policy if exists "paylasim kendi duzeltir" on public.paylasimlar;
create policy "paylasim kendi duzeltir" on public.paylasimlar
  for update using (kullanici = auth.uid() and durum = 'bekliyor')
  with check (kullanici = auth.uid() and durum = 'bekliyor');

drop policy if exists "paylasim kendi siler" on public.paylasimlar;
create policy "paylasim kendi siler" on public.paylasimlar
  for delete using (kullanici = auth.uid() and durum = 'bekliyor');

drop policy if exists "yonetici karar verir" on public.paylasimlar;
create policy "yonetici karar verir" on public.paylasimlar
  for update using (public.yonetici_mi()) with check (public.yonetici_mi());

-- Yonetici hatali veya sahte kaydi silebilmeli: kullanicinin kendi silme
-- hakki yalnizca "bekliyor" durumunda, onaylanmis bir kaydi kimse temizleyemezdi.
drop policy if exists "yonetici siler" on public.paylasimlar;
create policy "yonetici siler" on public.paylasimlar
  for delete using (public.yonetici_mi());

-- ============================================================
-- Sütun yetkisi — kimin kim olduğu tarayıcıya inmiyor
--
-- RLS SATIR duzeyinde calisir, SUTUN duzeyinde degil. "Onaylanmis
-- paylasimlar herkese acik" politikasi satiri aciyordu ve satirin icinde
-- `kullanici` de vardi. Yani herkese acik anon anahtariyla su sorgu
-- calisiyordu ve GERCEK POSTGRES'TE OLCULDU:
--
--   select kullanici, mekan_ad, tarih, tutar, kisi from paylasimlar
--
-- Tek bir uuid ile bir kisinin nereye, hangi gun, kac kisiyle gittigi ve
-- ne odedigi cikariliyordu; ayni uuid katkilar ve sahiplik tablolarinda da
-- gorundugu icin izler birlestirilebiliyordu. Kimlik degil ama SABIT bir
-- tanimlayiciya bagli disari cikma gecmisi -- gizlilik.html'deki veri
-- enazlama sozunun ve kimlik.js'teki "sahibin kimligi dondurulmuyor"
-- yorumunun ikisini birden bozuyordu. Istemcinin select listesine guvenmek
-- yetmez: anahtari olan herkes kendi sorgusunu yazabilir.
--
-- `kullanici` bir IC anahtar. Tarayicinin ona hicbir yerde ihtiyaci yok:
-- "kac kisinin fisi" sayisi artik sunucuda (mekan_fis_ozeti), kendi
-- kayitlarini RLS zaten suzuyor, yonetim ekrani uuid'yi hic gostermiyordu.
--
-- Olculdu: sutun yetkisi alindiktan sonra politikalar CALISMAYA DEVAM
-- EDIYOR -- politika ifadesi cagiran rolun sutun yetkisine bagli degil.
-- ============================================================
revoke select on public.paylasimlar from anon, authenticated;
grant  select (id, mekan_id, mekan_ad, il, tutar, kisi, tarih, aciklama,
               durum, olusturuldu)
  on public.paylasimlar to anon, authenticated;
-- insert/update/delete dokunulmuyor: kullanici sutununa YAZMAK gerekiyor
-- (kendi kaydini acarken), okumak gerekmiyor.

-- ============================================================
-- Fiş özeti — sayı sunucuda hesaplanıyor
--
-- Isletme sayfasi "3 kisinin 5 fisinden" diyebilmek icin FARKLI kullanici
-- sayisini biliyordu; bunu satirlari cekip tarayicida sayarak yapiyordu,
-- yani her ziyaretci butun uuid'leri goruyordu. Sayi burada uretiliyor,
-- kimlikler disari cikmiyor.
--
-- Esik kurali ISTEMCIDE kaliyor (FIS_ESIK): bu fonksiyon ham sayilari
-- veriyor, "gosterilsin mi" karari tek yerde dursun diye.
-- ============================================================
create or replace function public.mekan_fis_ozeti(p_mekan_id text)
returns table (fis int, kisi int, medyan numeric)
language sql
stable
security definer
set search_path = public
as $$
  with son as (
    select tutar, kisi, kullanici
    from public.paylasimlar
    where mekan_id = p_mekan_id and durum = 'onaylandi'
    order by tarih desc
    limit 200                      -- istemcideki sinirla ayni
  )
  select count(*)::int,
         count(distinct kullanici)::int,
         round(percentile_cont(0.5) within group
               (order by tutar / greatest(kisi, 1)))::numeric
  from son;
$$;
revoke all on function public.mekan_fis_ozeti(text) from public;
grant execute on function public.mekan_fis_ozeti(text) to anon, authenticated;

-- ============================================================
-- Kendini kontrol — bu blok hata vermeden geçmeli
-- ============================================================
do $$
declare
  eksik text;
  politika_sayisi int;
begin
  select string_agg(t, ', ') into eksik
  from (values ('profiller'),('favoriler'),('paylasimlar')) as v(t)
  where not exists (
    select 1 from pg_tables
    where schemaname = 'public' and tablename = v.t and rowsecurity = true
  );
  if eksik is not null then
    raise exception 'RLS acik degil: %', eksik;
  end if;

  select count(*) into politika_sayisi
  from pg_policies
  where schemaname = 'public' and tablename in ('profiller','favoriler','paylasimlar');

  if politika_sayisi < 9 then
    raise exception 'Beklenen politika sayisi olusmadi: % (en az 9 olmali)', politika_sayisi;
  end if;

  raise notice 'Sema kuruldu: 3 tablo, RLS acik, % politika', politika_sayisi;
end;
$$;

-- ============================================================
-- Kurulumdan sonra: kendini yönetici yap
-- Önce siteden kayıt ol, sonra e-postanı yazıp bunu çalıştır:
--
--   update public.profiller set yonetici = true
--   where id = (select id from auth.users where email = 'senin@adresin.com');
-- ============================================================
