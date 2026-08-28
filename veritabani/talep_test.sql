-- ============================================================
-- Cebimde — talep açığı ve fiyat endeksi davranış testi
--
-- Bu dosya kurulum SQL'i DEĞİL. Supabase'e yapıştırma.
-- Koşturmak için: sh veritabani/kos.sh
--
-- NE SINIYOR. İki fonksiyon da bir MEKAN LİSTESİ alıp toplu sayı
-- döndürüyor; yanlış giderse iki şey oluyor ve ikisi de sessiz:
--   (a) eşiğin altında sayı dönüyor -> tek kişinin bütçesi ya da tek
--       fişin tutarı "bölge ortalaması" diye yayınlanıyor
--   (b) liste sessizce kırpılıyor -> kullanıcının gördüğü haritayla
--       ayrışan bir sayı çıkıyor ve kimse fark etmiyor
--
-- Her adım ya "gecti" der ya da BASARISIZ diye patlar.
-- ============================================================
\set ON_ERROR_STOP on
\pset pager off

truncate public.goruntulenme, public.paylasimlar restart identity cascade;

insert into auth.users (id) values
  ('11111111-1111-4111-8111-111111111111'),
  ('22222222-2222-4222-8222-222222222222'),
  ('33333333-3333-4333-8333-333333333333')
  on conflict do nothing;

\echo '--- 1. ESIK ALTINDA hicbir sey donmuyor (4 bakis)'
insert into public.goruntulenme (mekan_id, gun, cihaz, butce_bandi) values
  ('node/1', current_date, gen_random_uuid(), 2),
  ('node/1', current_date, gen_random_uuid(), 2),
  ('node/2', current_date, gen_random_uuid(), 3),
  ('node/2', current_date, gen_random_uuid(), 1);
do $$
declare n int;
begin
  select count(*) into n from public.civar_talep_ozeti(array['node/1','node/2']);
  if n <> 0 then raise exception 'BASARISIZ: 4 bakista % satir dondu', n; end if;
  raise notice 'gecti: esik altinda dagilim yok';
end $$;

\echo '--- 2. ESIK ASILINCA dagilim geliyor (esik fazla yukseltilmedi)'
insert into public.goruntulenme (mekan_id, gun, cihaz, butce_bandi)
values ('node/2', current_date, gen_random_uuid(), 2);
do $$
declare n int; t int;
begin
  select count(*), sum(kisi) into n, t
    from public.civar_talep_ozeti(array['node/1','node/2']);
  -- Bant 2: 3 kisi (node/1'de 2, node/2'de 1). Bant 1 ve 3: birer.
  if n <> 3 or t <> 5 then
    raise exception 'BASARISIZ: % bant / % kisi (3 ve 5 olmali)', n, t;
  end if;
  raise notice 'gecti: 5 bakista dagilim aciliyor';
end $$;

\echo '--- 3. BASKA mekan listeye girmiyor'
insert into public.goruntulenme (mekan_id, gun, cihaz, butce_bandi) values
  ('node/9', current_date, gen_random_uuid(), 5),
  ('node/9', current_date, gen_random_uuid(), 5);
do $$
declare t int;
begin
  select coalesce(sum(kisi),0) into t
    from public.civar_talep_ozeti(array['node/1','node/2']);
  if t <> 5 then raise exception 'BASARISIZ: liste disi mekan sayildi (%)', t; end if;
  raise notice 'gecti: yalniz verilen mekanlar';
end $$;

\echo '--- 4. BAYAT bakis sayilmiyor (30 gun)'
insert into public.goruntulenme (mekan_id, gun, cihaz, butce_bandi) values
  ('node/1', current_date - 40, gen_random_uuid(), 5),
  ('node/1', current_date - 40, gen_random_uuid(), 5);
do $$
declare t int;
begin
  select coalesce(sum(kisi),0) into t
    from public.civar_talep_ozeti(array['node/1','node/2']);
  if t <> 5 then raise exception 'BASARISIZ: bayat bakis sayildi (%)', t; end if;
  raise notice 'gecti: 30 gunden eski bakis disarida';
end $$;

\echo '--- 5. UZUN liste SESSIZCE kirpilmiyor, hata veriyor'
do $$
declare k text[];
begin
  select array_agg('node/' || g) into k from generate_series(1, 501) g;
  perform * from public.civar_talep_ozeti(k);
  raise exception 'BASARISIZ: 501 elemanli liste kabul edildi';
exception when program_limit_exceeded then
  raise notice 'gecti: sinir asilinca hata';
end $$;

\echo '--- 6. sinirin ALTI calisiyor (sinir fazla kisilmadi)'
do $$
declare k text[]; n int;
begin
  select array_agg('node/' || g) into k from generate_series(1, 500) g;
  select count(*) into n from public.civar_talep_ozeti(k);
  raise notice 'gecti: 500 eleman kabul ediliyor (% satir)', n;
end $$;

\echo '--- 7. bos liste bos donuyor, uydurma yok'
do $$
declare n int;
begin
  select count(*) into n from public.civar_talep_ozeti(null);
  if n <> 0 then raise exception 'BASARISIZ: null listede % satir', n; end if;
  select count(*) into n from public.civar_talep_ozeti(array[]::text[]);
  if n <> 0 then raise exception 'BASARISIZ: bos listede % satir', n; end if;
  raise notice 'gecti: bos girdi bos cikti';
end $$;

\echo '--- 8. anon HAM bakis satirlarini hala goremiyor'
set role anon;
do $$ begin
  perform 1 from public.goruntulenme limit 1;
  raise exception 'BASARISIZ: anon ham satirlari okudu';
exception when insufficient_privilege then
  raise notice 'gecti: ham tablo kapali';
end $$;
reset role;

-- ============================================================
-- FIYAT ENDEKSI
-- ============================================================
\echo '--- 9. UC FISTEN AZ olan ay HIC donmuyor'
insert into public.paylasimlar (kullanici, mekan_id, mekan_ad, il, tutar, kisi,
                                tarih, durum) values
  ('11111111-1111-4111-8111-111111111111','node/1','A Kafe','06',200,1,
   current_date, 'onaylandi'),
  ('22222222-2222-4222-8222-222222222222','node/1','A Kafe','06',400,1,
   current_date, 'onaylandi');
do $$
declare n int;
begin
  select count(*) into n from public.civar_fiyat_endeksi(array['node/1'], 6);
  if n <> 0 then raise exception 'BASARISIZ: 2 fisle % ay dondu', n; end if;
  raise notice 'gecti: uc fisten az olan ay atlaniyor';
end $$;

\echo '--- 10. UCUNCU fisle ay aciliyor ve MEDYAN kisi basi'
insert into public.paylasimlar (kullanici, mekan_id, mekan_ad, il, tutar, kisi,
                                tarih, durum) values
  ('33333333-3333-4333-8333-333333333333','node/1','A Kafe','06',900,3,
   current_date, 'onaylandi');
do $$
declare r record;
begin
  select * into r from public.civar_fiyat_endeksi(array['node/1'], 6);
  -- Kisi basi: 200, 400, 300 -> medyan 300. Bolmeseydik 200/400/900 -> 400.
  if r.medyan <> 300 then
    raise exception 'BASARISIZ: medyan % (300 olmali; kisi basi bolunmemis?)',
      r.medyan;
  end if;
  if r.fis <> 3 or r.kisi <> 3 then
    raise exception 'BASARISIZ: fis % kisi % (3 ve 3 olmali)', r.fis, r.kisi;
  end if;
  raise notice 'gecti: medyan 300, uc fis uc kisi';
end $$;

\echo '--- 11. ONAYSIZ fis endekse girmiyor'
insert into public.paylasimlar (kullanici, mekan_id, mekan_ad, il, tutar, kisi,
                                tarih, durum) values
  ('11111111-1111-4111-8111-111111111111','node/1','A Kafe','06',9000,1,
   current_date - 1, 'bekliyor');
do $$
declare r record;
begin
  select * into r from public.civar_fiyat_endeksi(array['node/1'], 6);
  if r.fis <> 3 then
    raise exception 'BASARISIZ: onaysiz fis sayildi (fis=%)', r.fis;
  end if;
  raise notice 'gecti: yalniz onaylanan sayiliyor';
end $$;

\echo '--- 12. AY PENCERESI: eski ay istenmedigi surece gelmiyor'
-- ESKI AY icin var olan uc kullanici. Tekillik (kullanici, mekan_ad,
-- tarih) uzerinde, yani ayni tarihte uc FARKLI kullanici sorun degil.
-- Ilk yazimda uuid'leri uretiyordum ve yabanci anahtar dogru davranip
-- reddetti -- olmayan kullaniciyla fis yazilamiyor.
insert into public.paylasimlar (kullanici, mekan_id, mekan_ad, il, tutar, kisi,
                                tarih, durum) values
  ('11111111-1111-4111-8111-111111111111','node/1','A Kafe','06',500,1,
   (current_date - interval '8 months')::date, 'onaylandi'),
  ('22222222-2222-4222-8222-222222222222','node/1','A Kafe','06',500,1,
   (current_date - interval '8 months')::date, 'onaylandi'),
  ('33333333-3333-4333-8333-333333333333','node/1','A Kafe','06',500,1,
   (current_date - interval '8 months')::date, 'onaylandi');
do $$
declare n int;
begin
  select count(*) into n from public.civar_fiyat_endeksi(array['node/1'], 6);
  if n <> 1 then raise exception 'BASARISIZ: 6 ayda % ay dondu, 1 olmali', n; end if;
  select count(*) into n from public.civar_fiyat_endeksi(array['node/1'], 12);
  if n <> 2 then raise exception 'BASARISIZ: 12 ayda % ay dondu, 2 olmali', n; end if;
  raise notice 'gecti: pencere istenen kadar geriye gidiyor';
end $$;

\echo '--- 13. endekste de UZUN liste hata veriyor'
do $$
declare k text[];
begin
  select array_agg('node/' || g) into k from generate_series(1, 501) g;
  perform * from public.civar_fiyat_endeksi(k, 6);
  raise exception 'BASARISIZ: 501 elemanli liste kabul edildi';
exception when program_limit_exceeded then
  raise notice 'gecti: sinir asilinca hata';
end $$;

\echo '--- 14. anon endeksi cagirabiliyor ama HAM fisi goremiyor'
set role anon;
do $$
declare n int;
begin
  select count(*) into n from public.civar_fiyat_endeksi(array['node/1'], 6);
  if n <> 1 then raise exception 'BASARISIZ: anon endeksi alamadi (%)', n; end if;
  raise notice 'gecti: anon endeksi okuyabiliyor';
end $$;
do $$ begin
  perform kullanici from public.paylasimlar limit 1;
  raise exception 'BASARISIZ: anon fis kimligini okudu';
exception when insufficient_privilege then
  raise notice 'gecti: kimlik sutunu kapali';
end $$;
reset role;

\echo 'TALEP TESTI: 14 adim gecti'
