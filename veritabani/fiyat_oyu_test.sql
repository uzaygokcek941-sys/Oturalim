-- ============================================================
-- Cebimde — sosyal fiyat doğrulama davranış testi
--
-- Bu dosya kurulum SQL'i DEĞİL. Supabase'e yapıştırma.
-- Koşumu: sh veritabani/kos.sh  (test.py ve CI onu çağırıyor)
--
-- NE SINANIYOR: sayıların doğru çıktığı değil yalnızca -- kimliğin dışarı
-- SIZMADIĞI ve OYUN SATIN ALINAMADIĞI da. Bu tablonun kötüye kullanım
-- biçimi belli: işletmenin kendi fiyatını "geçerli" diye oylaması. Ona
-- karşı iki savunma var ve ikisi de burada sınanıyor -- tek-oy kuralı ve
-- KİŞİ sayan toplam.
-- ============================================================
\set ON_ERROR_STOP on
\pset pager off
truncate public.fiyat_oylari restart identity cascade;

reset role;
insert into auth.users (id) values
  ('b1111111-1111-4111-8111-111111111111'),
  ('b2222222-2222-4222-8222-222222222222'),
  ('b3333333-3333-4333-8333-333333333333')
  on conflict do nothing;

\echo '--- 1. kullanici KENDI adina oy verebiliyor'
-- ROL DEGISIMI "SET LOCAL" ILE YAPILMIYOR: islem blogu disinda SET LOCAL
-- bir sey yapmiyor, yalniz uyari basiyor. Ilk yazimda oyleydi ve rol hic
-- degismedi -- yani 1. adim superuser olarak gecti (hicbir sey
-- kanitlamadan), 2. adim da RLS devrede olmadigi icin patladi. Kalip
-- yorum_test.sql ile ayni.
set role authenticated;
set request.jwt.claim.sub = 'b1111111-1111-4111-8111-111111111111';
insert into public.fiyat_oylari (kullanici, mekan_id, il, fiyat, gecerli)
  values ('b1111111-1111-4111-8111-111111111111','node/1','34',240,true);
\echo 'gecti: kendi oyu kabul edildi'

\echo '--- 2. BASKASININ adina oy verilemiyor'
-- Bu kapı açık olsaydı tek bir hesap üç ayrı kimlikle eşiği geçebilirdi.
do $$
begin
  begin
    insert into public.fiyat_oylari (kullanici, mekan_id, il, fiyat, gecerli)
      values ('b2222222-2222-4222-8222-222222222222','node/1','34',240,true);
    raise exception 'BASARISIZ: baskasi adina oy yazilabildi';
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: baskasi adina oy engellendi';
end $$;

\echo '--- 3. AYNI kisi AYNI fiyata iki kez oy veremiyor'
-- Tek dokunuşluk bir eylem; sınır olmasa bir kişi eşiği tek başına geçerdi.
do $$
begin
  begin
    insert into public.fiyat_oylari (kullanici, mekan_id, il, fiyat, gecerli)
      values ('b1111111-1111-4111-8111-111111111111','node/1','34',240,false);
    raise exception 'BASARISIZ: ayni kisi ayni fiyata iki kez oy verdi';
  exception when unique_violation then null;
  end;
  raise notice 'gecti: tek oy kurali tutuyor';
end $$;

\echo '--- 4. FIYAT DEGISINCE ayni kisi yeniden oy verebiliyor'
-- Menü tazelenip rakam değişirse doğrulama akışı o mekan için kalıcı
-- olarak kapanmamalı.
insert into public.fiyat_oylari (kullanici, mekan_id, il, fiyat, gecerli)
  values ('b1111111-1111-4111-8111-111111111111','node/1','34',480,false);
\echo 'gecti: yeni fiyata yeni oy'

\echo '--- 5. toplam KISI sayiyor ve oy verilen FIYATA gore ayiriyor'
reset role;
insert into public.fiyat_oylari (kullanici, mekan_id, il, fiyat, gecerli) values
  ('b2222222-2222-4222-8222-222222222222','node/1','34',240,true),
  ('b3333333-3333-4333-8333-333333333333','node/1','34',240,false),
  -- BAYAT: 200 gun once. Sayilmamali.
  ('b2222222-2222-4222-8222-222222222222','node/9','34',100,true);
update public.fiyat_oylari set olusturuldu = now() - interval '200 days'
  where mekan_id = 'node/9';

set role anon;
do $$
declare r record; n int := 0;
begin
  for r in select * from public.fiyat_oy_ozeti(array['node/1']) loop
    n := n + 1;
    if r.fiyat = 240 then
      if r.gecerli <> 2 then raise exception 'BASARISIZ: 240 gecerli % (2)', r.gecerli; end if;
      if r.degisti <> 1 then raise exception 'BASARISIZ: 240 degisti % (1)', r.degisti; end if;
      if r.kisi    <> 3 then raise exception 'BASARISIZ: 240 kisi % (3)', r.kisi; end if;
    elsif r.fiyat = 480 then
      -- 480'e YALNIZ bir kisi oy vermis. 240'in oylari buraya
      -- karismamali: karisirsa eski rakama verilen onay yeni rakami
      -- dogrulamis olurdu. KISI SAYISI donuyor (arayuz "2 kisi daha"
      -- cumlesini ondan kuruyor) ama DAGILIM donmuyor -- esik altinda
      -- tek kisinin ne dedigi ifsa olurdu.
      if r.kisi    <> 1 then raise exception 'BASARISIZ: 480 kisi % (1)', r.kisi; end if;
      if r.gecerli <> 0 then raise exception 'BASARISIZ: 480 gecerli % (0)', r.gecerli; end if;
      if r.degisti <> 0 then
        raise exception 'BASARISIZ: esik alti dagilim sizdi (480 degisti %)', r.degisti;
      end if;
    else
      raise exception 'BASARISIZ: beklenmeyen fiyat %', r.fiyat;
    end if;
  end loop;
  if n <> 2 then raise exception 'BASARISIZ: % satir dondu (2 bekleniyor)', n; end if;
  raise notice 'gecti: 240 -> 2 gecerli / 1 degisti, 480 ayri satir';
end $$;

\echo '--- 5b. ESIK SUNUCUDA: iki kisilik dagilim disari cikmiyor'
-- BULGU. Esik once YALNIZ tarayicidaydi (ortak.js OY_ESIK / FIS_ESIK).
-- anon anahtar tasarim geregi herkese acik, yani RPC'yi dogrudan
-- cagiran biri ekranda gizlenen dagilimi okuyabilirdi. Gizlemeyi
-- yalniz arayuze birakmak, k-anonimligi bir gorunum meselesine
-- indirger. Ayni duzeltme mekan_fis_ozeti ve civar_fis_ozeti'nde de
-- yapildi.
reset role;
insert into public.fiyat_oylari (kullanici, mekan_id, il, fiyat, gecerli) values
  ('b1111111-1111-4111-8111-111111111111','node/2','34',300,true),
  ('b2222222-2222-4222-8222-222222222222','node/2','34',300,false);
set role anon;
do $$
declare r record;
begin
  select * into r from public.fiyat_oy_ozeti(array['node/2']);
  if r.kisi <> 2 then raise exception 'BASARISIZ: kisi % (2)', r.kisi; end if;
  if r.gecerli <> 0 or r.degisti <> 0 then
    raise exception 'BASARISIZ: esik alti dagilim sizdi (% / %)', r.gecerli, r.degisti;
  end if;
  raise notice 'gecti: esik alti sayi var, dagilim yok';
end $$;

\echo '--- 5c. ESIK ASILINCA dagilim geliyor'
-- Yalniz "gizliyor mu" diye bakmak yetmez: esigi 999 yapan bir
-- degisiklik de 5b'yi gecirir ve ozelligi sessizce goturur.
reset role;
insert into public.fiyat_oylari (kullanici, mekan_id, il, fiyat, gecerli)
  values ('b3333333-3333-4333-8333-333333333333','node/2','34',300,true);
set role anon;
do $$
declare r record;
begin
  select * into r from public.fiyat_oy_ozeti(array['node/2']);
  if r.kisi <> 3 then raise exception 'BASARISIZ: kisi % (3)', r.kisi; end if;
  if r.gecerli <> 2 then raise exception 'BASARISIZ: gecerli % (2)', r.gecerli; end if;
  if r.degisti <> 1 then raise exception 'BASARISIZ: degisti % (1)', r.degisti; end if;
  raise notice 'gecti: uc kiside dagilim aciliyor';
end $$;

\echo '--- 6. BAYAT oy sayilmiyor (180 gun)'
do $$
declare n int;
begin
  select count(*) into n from public.fiyat_oy_ozeti(array['node/9']);
  if n <> 0 then raise exception 'BASARISIZ: 200 gunluk oy sayildi'; end if;
  raise notice 'gecti: bayat oy disarida';
end $$;

\echo '--- 7. bos ve bilinmeyen girdi uydurma uretmiyor'
do $$
declare n int;
begin
  select count(*) into n from public.fiyat_oy_ozeti(array[]::text[]);
  if n <> 0 then raise exception 'BASARISIZ: bos liste % satir', n; end if;
  select count(*) into n from public.fiyat_oy_ozeti(null);
  if n <> 0 then raise exception 'BASARISIZ: null liste % satir', n; end if;
  select count(*) into n from public.fiyat_oy_ozeti(array['node/yok']);
  if n <> 0 then raise exception 'BASARISIZ: bilinmeyen mekan satir uretti'; end if;
  raise notice 'gecti: bos girdi bos cikti';
end $$;

\echo '--- 8. UZUN liste SESSIZCE kirpilmiyor'
do $$
declare uzun text[];
begin
  select array_agg('node/' || i) into uzun from generate_series(1, 501) i;
  begin
    perform * from public.fiyat_oy_ozeti(uzun);
    raise exception 'BASARISIZ: 501 elemanli liste sessizce kabul edildi';
  exception when program_limit_exceeded then null;
  end;
  raise notice 'gecti: sinir asilinca hata';
end $$;

\echo '--- 9. sinirin ALTI calisiyor (sinir fazla kisilmadi)'
-- Yalniz "reddediyor mu" diye bakmak yetmez: 500'u 50 yapan bir degisiklik
-- de 8. adimi gecirir ve ozelligi sessizce goturur.
do $$
declare uzun text[]; n int;
begin
  select array_agg('node/' || i) into uzun from generate_series(500, 998) i;
  uzun := array_append(uzun, 'node/1');      -- tam 500 eleman
  if array_length(uzun, 1) <> 500 then
    raise exception 'BASARISIZ: test kendi listesini 500 kuramadi (%)', array_length(uzun, 1);
  end if;
  select count(*) into n from public.fiyat_oy_ozeti(uzun);
  -- node/1'de iki fiyat (240, 480) var; node/2 listede degil.
  if n <> 2 then raise exception 'BASARISIZ: 500 elemanli listede % satir', n; end if;
  raise notice 'gecti: 500 eleman kabul ediliyor';
end $$;

\echo '--- 10. GERCEK anon tek tek oylari goremiyor'
-- Gorebilseydi kimin neye oy verdigi disari cikardi. Toplam security
-- definer fonksiyondan geliyor; tablonun kendisi kapali.
--
-- JWT TALEBI TEMIZLENIYOR. Ilk yazimda temizlenmiyordu ve 1. adimda
-- kurulan sub hala duruyordu: rol anon olsa bile auth.uid() bir kimlik
-- donduruyor, "kullanici = auth.uid()" politikasi da o kisinin 2 satirini
-- aciyordu. Yani adim "anon okuyabiliyor" diye patliyordu ama olculen sey
-- anonimlik degil, testin kendi kalintisiydi. Gercek Supabase'de anon
-- rolu sub tasimaz.
reset role;
set request.jwt.claim.sub = '';
set role anon;
do $$
declare n int;
begin
  select count(*) into n from public.fiyat_oylari;
  if n <> 0 then raise exception 'BASARISIZ: anon % oy satiri okuyabiliyor', n; end if;
  raise notice 'gecti: oy satirlari disariya kapali';
end $$;

\echo '--- 10b. giris yapmis kullanici BASKASININ oyunu goremiyor'
-- Asil sinav bu: politika "kullanici = auth.uid()" diyor. Yanlis yazilmis
-- bir hali (ornegin "using (true)") 10. adimi de gecerdi -- anon'un sub'i
-- yok diye. b1 kendi 2 oyunu gormeli, b2 ve b3'un oylarini gormemeli.
reset role;
set request.jwt.claim.sub = 'b1111111-1111-4111-8111-111111111111';
set role authenticated;
do $$
declare n int;
begin
  select count(*) into n from public.fiyat_oylari;
  -- b1'in oylari: node/1@240, node/1@480, node/2@300.
  if n <> 3 then
    raise exception 'BASARISIZ: b1 % satir goruyor (kendi 3 oyu bekleniyor)', n;
  end if;
  select count(*) into n from public.fiyat_oylari
   where kullanici <> 'b1111111-1111-4111-8111-111111111111';
  if n <> 0 then raise exception 'BASARISIZ: baskasinin % oyu gorunuyor', n; end if;
  raise notice 'gecti: herkes yalniz kendi oyunu goruyor';
end $$;

reset role;
set request.jwt.claim.sub = '';
set role anon;

\echo '--- 11. anon KIMLIK sutununu hala goremiyor'
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
\echo '--- 12. SON OY YASI: esik ustunde geliyor, altinda GELMIYOR'
-- KENDI FIXTURE'I: onceki adimlar node/1'in oylarini degistiriyor
-- (bayat oy, ek kisiler). Bu adim kendi mekaniyla kosuyor ki yas
-- olcumu baska bir adimin yan etkisine bagli olmasin.
reset role;
insert into public.fiyat_oylari (kullanici, mekan_id, il, fiyat, gecerli,
                                 olusturuldu) values
  ('b1111111-1111-4111-8111-111111111111','node/yas','34',300,true,
   now() - interval '3 days'),
  ('b2222222-2222-4222-8222-222222222222','node/yas','34',300,true,
   now() - interval '9 days'),
  ('b3333333-3333-4333-8333-333333333333','node/yas','34',300,false,
   now() - interval '40 days'),
  -- Esik ALTI ayri fiyat: tek kisi.
  ('b1111111-1111-4111-8111-111111111111','node/yas','34',999,true,
   now() - interval '1 day');
do $$
declare r record; n int;
begin
  select * into r from public.fiyat_oy_ozeti(array['node/yas']) where fiyat = 300;
  if r.son_gun is null then
    raise exception 'BASARISIZ: esik ustunde son oy yasi gelmedi';
  end if;
  -- EN YENI oyun yasi donmeli (3 gun), en eskisininki degil.
  if r.son_gun <> 3 then
    raise exception 'BASARISIZ: son oy yasi % (3 olmaliydi -- en yeni oy)', r.son_gun;
  end if;
  -- Esik ALTI grup: yas donmemeli, yoksa tek kisinin ne zaman oy
  -- verdigi disari cikar.
  select count(*) into n from public.fiyat_oy_ozeti(array['node/yas'])
   where kisi < 3 and son_gun is not null;
  if n > 0 then
    raise exception 'BASARISIZ: esik altinda son oy yasi sizdi (% satir)', n;
  end if;
  raise notice 'gecti: son oy yasi esigin ardinda, en yeni oydan';
end $$;

\echo '=== fiyat_oyu_test: 15 adimin hepsi gecti ==='
