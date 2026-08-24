-- ============================================================
-- Oturalım — sahiplenme davranış testi (gerçek Postgres'te)
--
-- Bu dosya kurulum SQL'i DEGIL. Sahiplenme akisinin guvenlik
-- ozelliklerini gercek bir Postgres'te sinar. Supabase'e yapistirma.
--
-- Calistirmak icin (Postgres 16 + pgcrypto):
--     initdb -D veri && pg_ctl -D veri -o "-k /tmp -p 5433" start
--     psql -h /tmp -p 5433 -U postgres -f veritabani/supabase_taklit.sql
--     psql -h /tmp -p 5433 -U postgres -f veritabani/sema.sql
--     psql -h /tmp -p 5433 -U postgres -f veritabani/katki.sql
--     psql -h /tmp -p 5433 -U postgres -f veritabani/sahiplenme.sql
--     psql -h /tmp -p 5433 -U postgres -f veritabani/sahiplenme_test.sql
--
-- Her adim ya "gecti" der ya da BASARISIZ diye patlar. Sessizce gecmez.
-- ============================================================
\set ON_ERROR_STOP on
\pset pager off
-- Tekrar calistirilabilir olsun: onceki kosunun izini sil.
truncate public.sahiplik, public.sahiplenme_kodu, public.katkilar restart identity cascade;

-- iki kullanici
insert into auth.users (id) values
  ('11111111-1111-4111-8111-111111111111'),
  ('22222222-2222-4222-8222-222222222222') on conflict do nothing;

-- kodlar: gecerli, suresi gecmis
insert into public.sahiplenme_kodu (kod_ozeti, mekan_id, il, mekan_ad) values
  (encode(digest('ABCD2345','sha256'),'hex'), 'node/1', '06', 'Test Kafe')
  on conflict do nothing;
insert into public.sahiplenme_kodu (kod_ozeti, mekan_id, il, mekan_ad, gecerlilik) values
  (encode(digest('EXPIRED1','sha256'),'hex'), 'node/9', '06', 'Eski Kafe', current_date - 1)
  on conflict do nothing;

\echo '--- 1. anon kod tablosunu okuyamaz'
set role anon;
do $$ begin
  perform 1 from public.sahiplenme_kodu limit 1;
  raise exception 'BASARISIZ: anon kod tablosunu okudu';
exception when insufficient_privilege then raise notice 'gecti: anon okuyamiyor';
end $$;
reset role;

\echo '--- 2. kullanici sahiplik tablosuna DOGRUDAN yazamaz'
set role authenticated;
set request.jwt.claim.sub = '11111111-1111-4111-8111-111111111111';
do $$ begin
  insert into public.sahiplik (kullanici, mekan_id, il, mekan_ad)
  values (auth.uid(), 'node/1', '06', 'Test Kafe');
  raise exception 'BASARISIZ: dogrudan sahiplik yazildi';
exception when insufficient_privilege then raise notice 'gecti: dogrudan yazilamiyor';
end $$;

\echo '--- 3. gecerli kod calisiyor (bosluk/kucuk harf toleransli)'
select mekan_ad from public.sahiplenme_kodu_kullan(' abcd-2345 ');

\echo '--- 4. ayni kod ikinci kez calismaz'
do $$ begin
  perform public.sahiplenme_kodu_kullan('ABCD2345');
  raise exception 'BASARISIZ: kod ikinci kez kullanildi';
exception when check_violation then raise notice 'gecti: % ', sqlerrm;
end $$;

\echo '--- 5. suresi gecmis kod ve uydurma kod AYNI mesaji veriyor'
do $$
declare m1 text; m2 text;
begin
  begin perform public.sahiplenme_kodu_kullan('EXPIRED1');
  exception when check_violation then m1 := sqlerrm; end;
  begin perform public.sahiplenme_kodu_kullan('ZZZZZZZZ');
  exception when check_violation then m2 := sqlerrm; end;
  if m1 is distinct from m2 then
    raise exception 'BASARISIZ: mesajlar ayirt edilebiliyor (% / %)', m1, m2;
  end if;
  raise notice 'gecti: ikisi de "%"', m1;
end $$;

\echo '--- 6. sahibinin katkisi kuyruga girmiyor'
insert into public.katkilar (kullanici, mekan_id, il, mekan_ad, alan, deger)
values (auth.uid(), 'node/1', '06', 'Test Kafe', 'tel', '0312 000 00 00');
select durum as sahip_katkisi from public.katkilar where mekan_id = 'node/1';

\echo '--- 7. sahibi olmadigi mekanda katki KUYRUKTA bekliyor'
insert into public.katkilar (kullanici, mekan_id, il, mekan_ad, alan, deger)
values (auth.uid(), 'node/7', '06', 'Baska Kafe', 'tel', '0312 111 11 11');
select durum as yabanci_katki from public.katkilar where mekan_id = 'node/7';

\echo '--- 8. sahibi olmadigi mekana ONAYLI katki yazamaz'
do $$ begin
  insert into public.katkilar (kullanici, mekan_id, il, mekan_ad, alan, deger, durum)
  values (auth.uid(), 'node/8', '06', 'Ucuncu Kafe', 'tel', '0312 222 22 22', 'onaylandi');
  raise exception 'BASARISIZ: sahibi olmadan onayli katki yazildi';
exception when insufficient_privilege then raise notice 'gecti: politika reddetti';
end $$;

\echo '--- 9. ikinci kullanici ayni mekani sahiplenemiyor'
reset role;   -- kod tablosu kullaniciya kapali (bkz. 1), kodu yonetici basar
insert into public.sahiplenme_kodu (kod_ozeti, mekan_id, il, mekan_ad) values
  (encode(digest('SECOND01','sha256'),'hex'), 'node/1', '06', 'Test Kafe') on conflict do nothing;
set role authenticated;
set request.jwt.claim.sub = '22222222-2222-4222-8222-222222222222';
do $$ begin
  perform public.sahiplenme_kodu_kullan('SECOND01');
  raise exception 'BASARISIZ: mekan iki kez sahiplenildi';
exception when check_violation then raise notice 'gecti: %', sqlerrm;
end $$;

\echo '--- 10. giris yapmamis kullanici kodu kullanamaz'
reset request.jwt.claim.sub;
set role anon;
do $$ begin
  perform public.sahiplenme_kodu_kullan('SECOND01');
  raise exception 'BASARISIZ: anon kod kullandi';
exception when insufficient_privilege then raise notice 'gecti: giris sarti isliyor';
end $$;

\echo '--- 11. aktif sahiplik anon icin gorunur (isletme rozeti)'
select count(*) as gorunen_sahiplik from public.sahiplik where durum = 'aktif';
reset role;
