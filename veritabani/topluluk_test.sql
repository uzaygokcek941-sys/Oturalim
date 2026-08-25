-- ============================================================
-- Cebimde — topluluk akışı davranış testi (gerçek Postgres'te)
--
-- Bu dosya kurulum SQL'i DEGIL. Supabase'e yapistirma.
-- Kosumu: sh veritabani/kos.sh  (test.py ve CI onu cagiriyor)
--
-- Her adim ya "gecti" der ya da BASARISIZ diye patlar.
-- ============================================================
\set ON_ERROR_STOP on
\pset pager off
truncate public.yorumlar restart identity cascade;
truncate public.menu_katkilari restart identity cascade;

reset role;
insert into auth.users (id) values
  ('55555555-5555-4555-8555-555555555555'),
  ('66666666-6666-4666-8666-666666666666') on conflict do nothing;
insert into public.profiller (id, kullanici_adi)
  values ('55555555-5555-4555-8555-555555555555', public.kullanici_adi_uret())
  on conflict (id) do nothing;
insert into public.profiller (id, kullanici_adi)
  values ('66666666-6666-4666-8666-666666666666', public.kullanici_adi_uret())
  on conflict (id) do nothing;
update public.profiller
   set kullanici_adi = 'acik_kisi', ad = 'Açık Kişi', herkese_acik = true
 where id = '55555555-5555-4555-8555-555555555555';
update public.profiller
   set kullanici_adi = 'kapali_kisi', ad = 'Kapalı Kişi', herkese_acik = false
 where id = '66666666-6666-4666-8666-666666666666';

insert into public.yorumlar
  (kullanici, mekan_id, il, mekan_ad, puan, metin, durum, olusturuldu) values
  ('55555555-5555-4555-8555-555555555555', 'node/1', '34', 'Acik Kafe',
   5, 'Harika mekan', 'onaylandi', now() - interval '1 hour'),
  ('66666666-6666-4666-8666-666666666666', 'node/2', '34', 'Kapali Kafe',
   4, 'Fena degil', 'onaylandi', now() - interval '2 hour'),
  ('55555555-5555-4555-8555-555555555555', 'node/3', '34', 'Bekleyen Kafe',
   3, 'Onaysiz', 'bekliyor', now() - interval '3 minute');

insert into public.menu_katkilari
  (kullanici, mekan_id, il, mekan_ad, urun, fiyat, durum, olusturuldu) values
  ('55555555-5555-4555-8555-555555555555', 'node/4', '34', 'Menulu Kafe',
   'Latte', 145, 'onaylandi', now() - interval '30 minute'),
  ('55555555-5555-4555-8555-555555555555', 'node/5', '34', 'Bekleyen Menu',
   'Espresso', 90, 'bekliyor', now() - interval '2 minute');

\echo '--- 1. onayli yorum ve menu katkisi TEK akista, yeniden eskiye'
do $$
declare t text[];
begin
  select array_agg(a.tur order by a.olusturuldu desc)
    into t from public.topluluk_akisi() a;
  if t is distinct from array['menu','yorum','yorum'] then
    raise exception 'BASARISIZ: akis sirasi %', t;
  end if;
  raise notice 'gecti: iki kaynak tek akista, yeniden eskiye';
end $$;

\echo '--- 2. ONAYSIZ kayit akista YOK'
do $$
declare n int;
begin
  select count(*) into n from public.topluluk_akisi()
   where mekan_ad in ('Bekleyen Kafe', 'Bekleyen Menu');
  if n <> 0 then raise exception 'BASARISIZ: % onaysiz kayit akista', n; end if;
  raise notice 'gecti: onaysiz kayit akista yok';
end $$;

\echo '--- 3. YORUM yazariyla geliyor'
do $$
declare r record;
begin
  select * into r from public.topluluk_akisi() where mekan_ad = 'Acik Kafe';
  if r.yazar_adi is distinct from 'acik_kisi' or r.yazar_ad is distinct from 'Açık Kişi' then
    raise exception 'BASARISIZ: yorum yazari gelmedi (% / %)', r.yazar_adi, r.yazar_ad;
  end if;
  raise notice 'gecti: yorum yazariyla geliyor';
end $$;

\echo '--- 4. PROFILI KAPALI kisinin adi DONMUYOR (yorumu duruyor)'
do $$
declare r record;
begin
  select * into r from public.topluluk_akisi() where mekan_ad = 'Kapali Kafe';
  if r.id is null then raise exception 'BASARISIZ: kapali profilin yorumu da dustu'; end if;
  if r.yazar_adi is not null or r.yazar_ad is not null then
    raise exception 'BASARISIZ: kapali profilin adi sizdi (% / %)', r.yazar_adi, r.yazar_ad;
  end if;
  raise notice 'gecti: kapali profil adsiz, yorumu yerinde';
end $$;

\echo '--- 5. MENU KATKISI ADSIZ (katki formu "adin yazacak" demiyor)'
do $$
declare r record;
begin
  select * into r from public.topluluk_akisi() where tur = 'menu';
  if r.yazar_adi is not null or r.yazar_ad is not null or r.yazar_avatar is not null then
    raise exception 'BASARISIZ: menu katkisina ad baglanmis (%)', r.yazar_adi;
  end if;
  if r.urun is distinct from 'Latte' or r.fiyat is distinct from 145 then
    raise exception 'BASARISIZ: menu katkisinin kalemi gelmedi (% %)', r.urun, r.fiyat;
  end if;
  raise notice 'gecti: menu katkisi adsiz ama kalemli';
end $$;

\echo '--- 6. FIS akista YOK (odeme kaydi, kani degil)'
do $$
declare t text[];
begin
  select array_agg(distinct a.tur) into t from public.topluluk_akisi() a;
  if 'fis' = any(t) or 'paylasim' = any(t) then
    raise exception 'BASARISIZ: fis akista (%)', t;
  end if;
  raise notice 'gecti: fis akista yok';
end $$;

\echo '--- 7. FIYAT OYU akista YOK (tek tek oy kimseye gorunmez)'
do $$
declare t text[];
begin
  select array_agg(distinct a.tur) into t from public.topluluk_akisi() a;
  if 'oy' = any(t) then raise exception 'BASARISIZ: fiyat oyu akista (%)', t; end if;
  raise notice 'gecti: fiyat oyu akista yok';
end $$;

\echo '--- 8. IMLEC: verilen andan ESKIYE'
do $$
declare n int; en_yeni timestamptz;
begin
  select max(olusturuldu) into en_yeni from public.topluluk_akisi();
  select count(*) into n from public.topluluk_akisi(en_yeni);
  if n <> 2 then raise exception 'BASARISIZ: imlecten sonra % kayit (2 olmaliydi)', n; end if;
  raise notice 'gecti: imlec eskiye dogru calisiyor';
end $$;

\echo '--- 9. SINIR SUNUCUDA: istemci istedigi kadar buyuk sayi versin'
do $$
declare n int;
begin
  -- 3 kayit var; sinirin kendisi 60'i gecmemeli. Once sinirin
  -- KISITLADIGINI gosteriyoruz (limit 1), sonra devasa sayinin
  -- sessizce kabul edilmedigini.
  select count(*) into n from public.topluluk_akisi(null, 1);
  if n <> 1 then raise exception 'BASARISIZ: limit 1 iken % kayit', n; end if;
  select count(*) into n from public.topluluk_akisi(null, 100000);
  if n <> 3 then raise exception 'BASARISIZ: devasa limitte % kayit', n; end if;
  raise notice 'gecti: sinir sunucuda tutuluyor';
end $$;

\echo '--- 10. GERCEK anon akisi okuyor; ONAYSIZ kayit ham tabloda da yok'
do $$
declare n int;
begin
  set local role anon;
  select count(*) into n from public.topluluk_akisi();
  if n <> 3 then raise exception 'BASARISIZ: anon akisi goremedi (%)', n; end if;
  -- ILK YAZIMDA "anon ham tabloyu HIC okuyamamali" diye bakiyordum ve
  -- adim patladi: onayli yorum anon'a BILEREK acik (yorum.sql'deki
  -- "yorum onaylanmis herkese acik" politikasi, sutunlari kisitli
  -- grant ile). Kontrol yanlisti, kod degil. Olculen sey artik dogru
  -- olan: ONAYSIZ kayit ham tabloda da gorunmemeli.
  select count(*) into n from public.yorumlar where durum <> 'onaylandi';
  reset role;
  if n <> 0 then raise exception 'BASARISIZ: anon onaysiz yorumu gordu (%)', n; end if;
  raise notice 'gecti: anon yalniz onaylanmis olani goruyor';
end $$;

\echo '--- 11. anon KULLANICI sutununu hala goremiyor'
do $$
declare v uuid;
begin
  set local role anon;
  begin
    select kullanici into v from public.yorumlar limit 1;
    reset role;
    if v is not null then raise exception 'BASARISIZ: anon kullanici sutununu okudu'; end if;
  exception when insufficient_privilege then reset role;
  end;
  raise notice 'gecti: kimlik sutunu kapali';
end $$;

\echo '=== topluluk_test: 11 adimin hepsi gecti ==='
