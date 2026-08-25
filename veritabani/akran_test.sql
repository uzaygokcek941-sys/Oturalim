-- ============================================================
-- Cebimde — bütçe akranları / civar fişi davranış testi
--
-- Bu dosya kurulum SQL'i DEGIL. Supabase'e yapistirma.
-- Kosumu: sh veritabani/kos.sh  (test.py ve CI onu cagiriyor)
--
-- NE SINANIYOR: sayilarin DOGRU CIKTIGI degil yalnizca -- kimligin disari
-- SIZMADIGI da. Iki fonksiyon da security definer, yani RLS'i atlayarak
-- calisiyor; yanlis yazilmis bir tanesi butun paylasimlari acardi.
-- ============================================================
\set ON_ERROR_STOP on
\pset pager off
truncate public.paylasimlar restart identity cascade;

reset role;
insert into auth.users (id) values
  ('a1111111-1111-4111-8111-111111111111'),
  ('a2222222-2222-4222-8222-222222222222'),
  ('a3333333-3333-4333-8333-333333333333')
  on conflict do nothing;

-- Yonetici olarak dogrudan onayli veri yaziyoruz: sinanan sey kuyruk degil,
-- toplamin kendisi. (durum='onaylandi' ile insert yapmayi politika
-- engelliyor -- o zaten menu_katki_test.sql 2. adimda sinaniyor.)
insert into public.paylasimlar (kullanici, mekan_id, mekan_ad, il, tutar, kisi, tarih, durum) values
  -- Ucuz civar: node/1 uc fis, IKI kisiden (biri iki kez gitmis)
  ('a1111111-1111-4111-8111-111111111111','node/1','Ucuz Kafe','06', 200,2,current_date - 5,'onaylandi'),
  ('a1111111-1111-4111-8111-111111111111','node/1','Ucuz Kafe','06', 240,2,current_date - 3,'onaylandi'),
  ('a2222222-2222-4222-8222-222222222222','node/1','Ucuz Kafe','06', 300,3,current_date - 1,'onaylandi'),
  -- node/2 tek fis
  ('a3333333-3333-4333-8333-333333333333','node/2','Orta Kafe','06', 600,2,current_date - 2,'onaylandi'),
  -- Pahali: kisi basi 900
  ('a1111111-1111-4111-8111-111111111111','node/3','Pahali Balik','06',1800,2,current_date - 4,'onaylandi'),
  -- Baska il
  ('a2222222-2222-4222-8222-222222222222','node/9','Izmir Kafe','35', 150,1,current_date - 2,'onaylandi'),
  -- BAYAT: 200 gun once. Sayilmamali.
  ('a3333333-3333-4333-8333-333333333333','node/1','Ucuz Kafe','06',  50,1,current_date - 200,'onaylandi'),
  -- ONAYSIZ. Sayilmamali.
  ('a3333333-3333-4333-8333-333333333333','node/4','Bekleyen','06',  100,1,current_date - 1,'bekliyor');

\echo '--- 1. butce akrani: tavan altindaki KISI sayisi, fis sayisi degil'
-- node/1'de kisi basi 100, 120, 100 -> ucu de 150 tavaninin altinda.
-- Bunlar IKI kisiden geliyor (a1 iki kez). Yani 3 fis ama 2 akran.
-- "Kac kisi" ile "kac fis" ayrimi bu ozelligin butun anlami: uc fisi olan
-- tek kisi bir akran toplulugu degil.
set role anon;
do $$
declare r record;
begin
  select * into r from public.butce_akranlari('06', 150);
  if r.akran <> 2 then raise exception 'BASARISIZ: akran % (2 bekleniyor)', r.akran; end if;
  if r.fis   <> 3 then raise exception 'BASARISIZ: fis % (3 bekleniyor)', r.fis; end if;
  if r.mekan <> 1 then raise exception 'BASARISIZ: mekan % (1 bekleniyor)', r.mekan; end if;
  raise notice 'gecti: 2 akran / 3 fis / 1 mekan';
end $$;

\echo '--- 2. tavan yukselince akran ve mekan buyuyor'
do $$
declare r record;
begin
  select * into r from public.butce_akranlari('06', 300);
  -- node/1 (100,120,100) + node/2 (300) -> 3 kisi, 4 fis, 2 mekan
  if r.akran <> 3 or r.mekan <> 2 then
    raise exception 'BASARISIZ: akran % mekan % (3 / 2 bekleniyor)', r.akran, r.mekan;
  end if;
  raise notice 'gecti: tavan buyuyunce kapsam buyuyor';
end $$;

\echo '--- 3. BAYAT fis sayilmiyor (180 gun)'
-- 200 gun onceki 50 TL'lik fis tavanin cok altinda; sayilsaydi 1. adimda
-- akran 3 cikardi. Fiyat eskiyor: bir yil onceki fisten "butcendeki
-- insanlar buraya gidiyor" demek dogrulanamayan bir iddia.
do $$
declare r record;
begin
  select * into r from public.butce_akranlari('06', 60);
  if r.fis <> 0 then raise exception 'BASARISIZ: bayat fis sayildi (%)', r.fis; end if;
  raise notice 'gecti: 200 gunluk fis disarida';
end $$;

\echo '--- 4. ONAYSIZ fis sayilmiyor'
do $$
declare r record;
begin
  select * into r from public.butce_akranlari('06', 1000);
  -- onayli olanlar: node/1 x3, node/2 x1, node/3 x1 = 5 fis, 3 mekan
  if r.fis <> 5 or r.mekan <> 3 then
    raise exception 'BASARISIZ: fis % mekan % (5 / 3 bekleniyor)', r.fis, r.mekan;
  end if;
  raise notice 'gecti: kuyruktaki kayit toplama girmiyor';
end $$;

\echo '--- 5. il suzgeci gercekten suzuyor'
do $$
declare r record;
begin
  select * into r from public.butce_akranlari('35', 200);
  if r.mekan <> 1 or r.akran <> 1 then
    raise exception 'BASARISIZ: il suzgeci (mekan % akran %)', r.mekan, r.akran;
  end if;
  select * into r from public.butce_akranlari('06', 200);
  if r.mekan <> 1 then raise exception 'BASARISIZ: 06 sorusuna 35 karisti'; end if;
  raise notice 'gecti: il suzgeci ayiriyor';
end $$;

\echo '--- 6. tavan yoksa/gecersizse SIFIR doner, "hepsi" degil'
-- Butce girilmemis kullaniciya "butcendeki 37 kisi" demek uydurma olurdu.
-- Istemci de bu durumda hic sormuyor; iki kapi da kapali olsun.
do $$
declare r record;
begin
  select * into r from public.butce_akranlari('06', null);
  if r.fis <> 0 then raise exception 'BASARISIZ: null tavan % fis dondu', r.fis; end if;
  select * into r from public.butce_akranlari('06', 0);
  if r.fis <> 0 then raise exception 'BASARISIZ: sifir tavan % fis dondu', r.fis; end if;
  select * into r from public.butce_akranlari('06', -5);
  if r.fis <> 0 then raise exception 'BASARISIZ: negatif tavan % fis dondu', r.fis; end if;
  raise notice 'gecti: gecersiz tavan sifir';
end $$;

\echo '--- 7. civar ozeti: verilen mekan listesinin MEDYANI, kisi basi'
-- node/1 (100,120,100) + node/2 (300) -> sirali 100,100,120,300 -> medyan 110
--
-- node/4 LISTEYE BILEREK KONULDU: uzerindeki tek fis 'bekliyor' durumunda
-- ve kisi basi 100. Onay suzgeci dususe fis 5, medyan 110 -> 100 olurdu.
-- Once bu adim node/4'u hic icermiyordu; suzgeci silen bir sabotaj testten
-- SESSIZCE geciyordu -- yani kuyrukta bekleyen, hic okunmamis bir kayit
-- civar medyanina girebilirdi ve bunu hicbir sey soylemezdi.
-- Ayni gerekcelerle bayat kayit da node/1 uzerinde duruyor (3. adim).
do $$
declare r record;
begin
  select * into r from public.civar_fis_ozeti(array['node/1','node/2','node/4']);
  if r.fis <> 4 then raise exception 'BASARISIZ: civar fis % (4)', r.fis; end if;
  if r.kisi <> 3 then raise exception 'BASARISIZ: civar kisi % (3)', r.kisi; end if;
  if r.mekan <> 2 then raise exception 'BASARISIZ: civar mekan % (2)', r.mekan; end if;
  if r.medyan <> 110 then raise exception 'BASARISIZ: civar medyan % (110)', r.medyan; end if;
  raise notice 'gecti: medyan 110, kisi basi';
end $$;

\echo '--- 7b. civar ozetinde de ESIK SUNUCUDA'
-- 7. adim dort fisle kosuyor (esigin ustunde) ve esigi kaldiran bir
-- degisiklik onu aynen gecerdi. Burada tek fisli bir civar
-- sorgulaniyor: sayilar donmeli, TUTAR donmemeli.
--
-- Civar daha genis bir kume oldugu icin esigi gevsetmek cazip;
-- gevsetilmiyor, cunku tek fisli bir civar da tek kisidir.
do $$
declare r record;
begin
  select * into r from public.civar_fis_ozeti(array['node/2']);
  if r.fis <> 1 then raise exception 'BASARISIZ: civar fis % (1)', r.fis; end if;
  if r.medyan is not null then
    raise exception 'BASARISIZ: esik alti civar tutari sizdi (medyan %)', r.medyan;
  end if;
  raise notice 'gecti: tek fisli civar tutar vermiyor';
end $$;

\echo '--- 8. civar ozeti bos liste ve bilinmeyen mekan'
do $$
declare r record;
begin
  select * into r from public.civar_fis_ozeti(array[]::text[]);
  if r.fis <> 0 or r.medyan is not null then
    raise exception 'BASARISIZ: bos liste % fis', r.fis;
  end if;
  select * into r from public.civar_fis_ozeti(null);
  if r.fis <> 0 then raise exception 'BASARISIZ: null liste % fis', r.fis; end if;
  select * into r from public.civar_fis_ozeti(array['node/yok']);
  if r.fis <> 0 or r.medyan is not null then
    raise exception 'BASARISIZ: bilinmeyen mekan medyan uretti';
  end if;
  raise notice 'gecti: bos girdi bos cikti, uydurma yok';
end $$;

\echo '--- 9. UZUN liste SESSIZCE kirpilmiyor, hata veriyor'
-- Sessiz kirpma, ekranda yazan "500 m cevresi" ifadesini yalan yapardi.
do $$
declare uzun text[];
begin
  select array_agg('node/' || i) into uzun from generate_series(1, 501) i;
  begin
    perform * from public.civar_fis_ozeti(uzun);
    raise exception 'BASARISIZ: 501 elemanli liste sessizce kabul edildi';
  exception when program_limit_exceeded then null;
  end;
  raise notice 'gecti: sinir asilinca hata';
end $$;

\echo '--- 10. sinirin ALTI calisiyor (sinir fazla kisilmadi)'
-- Yalniz "reddediyor mu" diye bakmak yetmez: 500'u 50 yapan bir degisiklik
-- de 9. adimi gecirir ve ozelligi sessizce goturur.
do $$
declare uzun text[]; r record;
begin
  -- 500'den baslayan doldurma kimlikleri: 1..499 arasi uretmek node/1'i
  -- zaten iceriyor ve sondaki eklemeyi anlamsiz kilardi.
  select array_agg('node/' || i) into uzun from generate_series(500, 998) i;
  uzun := array_append(uzun, 'node/1');      -- tam 500 eleman
  if array_length(uzun, 1) <> 500 then
    raise exception 'BASARISIZ: test kendi listesini 500 kuramadi (%)', array_length(uzun, 1);
  end if;
  select * into r from public.civar_fis_ozeti(uzun);
  if r.fis <> 3 then raise exception 'BASARISIZ: 500 elemanli listede % fis', r.fis; end if;
  raise notice 'gecti: 500 eleman kabul ediliyor';
end $$;

\echo '--- 11. anon KIMLIGI hala goremiyor'
-- Iki fonksiyon da security definer. Yanlis yazilmis biri, sema.sql'in
-- kapattigi sutunu geri acardi.
do $$
begin
  begin
    perform kullanici from public.paylasimlar limit 1;
    raise exception 'BASARISIZ: anon paylasimlar.kullanici okuyabiliyor';
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: kimlik sutunu hala kapali';
end $$;

reset role;
\echo '=== akran_test: 12 adimin hepsi gecti ==='
