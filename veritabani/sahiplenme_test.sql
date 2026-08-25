-- ============================================================
-- Cebimde — sahiplenme davranış testi (gerçek Postgres'te)
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
do $$
declare a text; i text;
begin
  select mekan_ad, mekan_id into a, i
    from public.sahiplenme_kodu_kullan(' abcd-2345 ');
  if a is distinct from 'Test Kafe' or i is distinct from 'node/1' then
    raise exception 'BASARISIZ: yanlis isletme dondu (% / %)', i, a;
  end if;
  raise notice 'gecti: % (%)', a, i;
end $$;

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
do $$
declare d text;
begin
  insert into public.katkilar (kullanici, mekan_id, il, mekan_ad, alan, deger)
  values (auth.uid(), 'node/1', '06', 'Test Kafe', 'tel', '0312 000 00 00');
  select durum into d from public.katkilar where mekan_id = 'node/1';
  if d is distinct from 'onaylandi' then
    raise exception 'BASARISIZ: sahibinin katkisi "%" oldu, "onaylandi" olmaliydi', d;
  end if;
  raise notice 'gecti: dogrudan onaylandi';
end $$;

\echo '--- 7. sahibi olmadigi mekanda katki KUYRUKTA bekliyor'
do $$
declare d text;
begin
  insert into public.katkilar (kullanici, mekan_id, il, mekan_ad, alan, deger)
  values (auth.uid(), 'node/7', '06', 'Baska Kafe', 'tel', '0312 111 11 11');
  select durum into d from public.katkilar where mekan_id = 'node/7';
  if d is distinct from 'bekliyor' then
    raise exception 'BASARISIZ: yabanci katki "%" oldu, "bekliyor" olmaliydi', d;
  end if;
  raise notice 'gecti: kuyrukta bekliyor';
end $$;

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
do $$
declare n int; k int;
begin
  select count(*) into n from public.sahiplik where durum = 'aktif';
  if n <> 1 then
    raise exception 'BASARISIZ: anon % aktif sahiplik goruyor, 1 olmaliydi', n;
  end if;
  -- Gorunen sey "dogrulanmis", "kim dogruladi" DEGIL: anon sahibin
  -- kimligini okuyamamali. Onceden yalniz sayiya bakiliyordu, yani sutun
  -- sizsa bile kontrol yesil kalirdi.
  begin
    select count(*) into k from public.sahiplik where kullanici is not null;
    raise exception 'BASARISIZ: anon sahibin kimligini okuyabiliyor (% satir)', k;
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: rozet gorunuyor, sahibin kimligi gorunmuyor';
end $$;
reset role;

\echo '--- 12. anon kimseyi tanimiyor: kullanici sutunu uc tabloda da kapali'
-- RLS SATIR duzeyinde calisir. "Onaylanmis ... herkese acik" politikalari
-- satiri aciyor ve satirin icinde `kullanici` da vardi. Olculdu: herkese
-- acik anon anahtariyla bir kisinin nereye/hangi gun/kac kisiyle gittigi ve
-- ne odedigi tek sorguyla cikiyordu; ayni uuid uc tabloda birden gorundugu
-- icin izler birlestirilebiliyordu. Sutun yetkisi sema.sql, katki.sql ve
-- sahiplenme.sql'de aliniyor.
set role anon;
do $$
declare t text;
begin
  foreach t in array array['paylasimlar','katkilar','sahiplik'] loop
    begin
      execute format('select kullanici from public.%I limit 1', t);
      raise exception 'BASARISIZ: anon %.kullanici sutununu okuyabiliyor', t;
    exception when insufficient_privilege then null;
    end;
  end loop;
  raise notice 'gecti: uc tabloda da kimlik gorunmuyor';
end $$;

\echo '--- 13. giris yapmis kullanici da baskasinin kimligini goremiyor'
-- Hesap acmak bu veriyi acmamali: onaylanmis kayitlari authenticated de
-- goruyor, yani yetki yalniz anon'dan alinsaydi kayit olan herkes ayni
-- izi cikarabilirdi.
set role authenticated;
set request.jwt.claim.sub = '11111111-1111-4111-8111-111111111111';
do $$
declare t text;
begin
  foreach t in array array['paylasimlar','katkilar','sahiplik'] loop
    begin
      execute format('select kullanici from public.%I limit 1', t);
      raise exception 'BASARISIZ: authenticated %.kullanici sutununu okuyabiliyor', t;
    exception when insufficient_privilege then null;
    end;
  end loop;
  raise notice 'gecti: kayit olmak kimlikleri acmiyor';
end $$;

\echo '--- 14. kendi kayitlari yine calisiyor (yetki fazla kisilmadi)'
-- Sutun yetkisini kismak KOLAY; fazla kismak sessizce ozellik goturur.
-- "Sahipliklerim" listesi kullanici sutununa gore SUZUYORDU ve Postgres'te
-- WHERE de sutun yetkisi ister -- filtre kalsaydi liste bos donerdi.
-- SORGULAR ISTEMCININ KENDI SELECT LISTELERI. "count(*)" ile bakmak
-- yetmiyordu: sutun yetkisini FAZLA kismak da sessizce ozellik goturur ve
-- count(*) hicbir sutuna dokunmadigi icin yesil kalirdi (sabotajla olculdu
-- -- sahiplik.id kapatildiginda isletme sayfasindaki sahiplik rozeti
-- tamamen kaybolur ve kontrol bunu gormuyordu). Listeler kimlik.js ve
-- isletme.html'deki .select() cagrilariyla birebir ayni.
do $$
declare n int;
begin
  -- kimlik.js sahipliklerim()
  select count(*) into n from (
    select id, mekan_id, mekan_ad, il, dogrulandi, durum from public.sahiplik) t;
  if n < 1 then raise exception 'BASARISIZ: kendi sahipligini goremiyor'; end if;
  -- kimlik.js mekanSahiplenilmis()  (anon da bunu cagiriyor, bkz. 11)
  perform id from public.sahiplik limit 1;
  -- kimlik.js sahiplikYonetimListesi()
  perform id, mekan_id, mekan_ad, il, dogrulandi, durum, iptal_notu
    from public.sahiplik limit 1;

  -- kimlik.js katkilarim() / katkiYonetimListesi()
  select count(*) into n from (
    select id, mekan_id, mekan_ad, il, alan, deger, durum, olusturuldu
      from public.katkilar) t;
  if n < 1 then raise exception 'BASARISIZ: kendi katkisini goremiyor'; end if;
  -- kimlik.js onaylanmisKatkilar()
  perform alan, deger, olusturuldu from public.katkilar limit 1;

  insert into public.paylasimlar (kullanici, mekan_id, mekan_ad, il, tutar, kisi, tarih)
  values (auth.uid(), 'node/1', 'Test Kafe', '06', 900, 3, current_date);
  -- kimlik.js paylasimlarim()
  select count(*) into n from (
    select id, mekan_ad, il, tutar, kisi, tarih, durum, olusturuldu
      from public.paylasimlar where mekan_id = 'node/1') t;
  if n < 1 then raise exception 'BASARISIZ: kendi paylasimini goremiyor'; end if;
  -- kimlik.js onaylanmisPaylasimlar()  (kesfet ekrani)
  perform mekan_id, mekan_ad, tutar, kisi, tarih from public.paylasimlar limit 1;
  -- kimlik.js yonetimListesi()
  perform id, mekan_id, mekan_ad, il, tutar, kisi, tarih, aciklama, durum, olusturuldu
    from public.paylasimlar limit 1;

  raise notice 'gecti: istemcinin butun select listeleri calisiyor';
end $$;

\echo '--- 15. fis ozeti kimlik sizdirmadan sayiyor'
-- "3 kisinin 5 fisinden" cumlesi FARKLI kullanici sayisini istiyor. Bu sayi
-- eskiden satirlar cekilip tarayicida hesaplaniyordu, yani sizintinin
-- sebebi de oydu. Artik sunucuda.
reset role;
update public.paylasimlar set durum = 'onaylandi' where mekan_id = 'node/1';
insert into public.paylasimlar (kullanici, mekan_id, mekan_ad, il, tutar, kisi, tarih, durum)
values ('22222222-2222-4222-8222-222222222222','node/1','Test Kafe','06',600,2,
        current_date - 1,'onaylandi'),
       -- UCUNCU fis, ILK kullanicidan. Sart: boyle olmazsa fis sayisi ile
       -- FARKLI KISI sayisi esit olur ve "count(distinct kullanici)" yerine
       -- "count(kullanici)" yazmak kontrolu yine gecerdi. Sabotajla olculdu.
       ('11111111-1111-4111-8111-111111111111','node/1','Test Kafe','06',1200,4,
        current_date - 2,'onaylandi');
set role anon;
do $$
declare o record;
begin
  select * into o from public.mekan_fis_ozeti('node/1');
  if o.fis <> 3 then raise exception 'BASARISIZ: fis sayisi % , 3 olmaliydi', o.fis; end if;
  if o.kisi <> 2 then raise exception 'BASARISIZ: kisi sayisi % , 2 olmaliydi', o.kisi; end if;
  -- kisi basi: 900/3=300, 600/2=300, 1200/4=300 -> medyan 300
  if o.medyan <> 300 then raise exception 'BASARISIZ: medyan % , 300 olmaliydi', o.medyan; end if;
  raise notice 'gecti: % fis / % kisi / medyan %', o.fis, o.kisi, o.medyan;
end $$;
do $$
declare o record;
begin
  select * into o from public.mekan_fis_ozeti('hic/yok');
  if o.fis <> 0 or o.kisi <> 0 or o.medyan is not null then
    raise exception 'BASARISIZ: bos mekan icin % / % / %', o.fis, o.kisi, o.medyan;
  end if;
  raise notice 'gecti: fisi olmayan mekan sifir donuyor';
end $$;
reset role;

\echo '--- 16. sahipligi birakmak SILMIYOR, kayit kaliyor'
-- Yonetici iptali kaydi koruyordu, kullanicinin birakmasi SILIYORDU.
-- Ayni gerekce ikisinde de gecerli ve onemi somut: sahibin katkisi
-- INCELENMEDEN onaylaniyor. Silme kalsaydi biri mekani sahiplenip
-- incelenmemis bilgi yazar, sonra birakir ve sahip OLDUGUNA dair hicbir
-- kayit kalmazdi.
reset role;
truncate public.sahiplik restart identity cascade;
insert into public.sahiplik (kullanici, mekan_id, il, mekan_ad) values
  ('11111111-1111-4111-8111-111111111111', 'node/50', '06', 'Birakilacak Kafe');
set role authenticated;
set request.jwt.claim.sub = '11111111-1111-4111-8111-111111111111';
do $$
declare d text; n int;
begin
  perform public.sahipligi_birak(
    (select id from public.sahiplik where mekan_id = 'node/50'));
  select count(*) into n from public.sahiplik where mekan_id = 'node/50';
  if n <> 1 then raise exception 'BASARISIZ: kayit silinmis (% satir)', n; end if;
  select durum into d from public.sahiplik where mekan_id = 'node/50';
  if d <> 'birakildi' then raise exception 'BASARISIZ: durum %', d; end if;
  raise notice 'gecti: kayit duruyor, durum birakildi';
end $$;

\echo '--- 17. birakilan mekan yeniden sahiplenilebiliyor'
-- Tekil kisit yalniz "aktif" satirlari kapsiyor. Kapsamasaydi bir mekani
-- yanlislikla sahiplenip birakan kisi orayi KALICI olarak kilitlerdi.
reset role;
insert into public.sahiplenme_kodu (kod_ozeti, mekan_id, il, mekan_ad) values
  (encode(digest('THIRD001','sha256'),'hex'), 'node/50', '06', 'Birakilacak Kafe')
  on conflict do nothing;
set role authenticated;
set request.jwt.claim.sub = '22222222-2222-4222-8222-222222222222';
do $$
declare a text;
begin
  select mekan_ad into a from public.sahiplenme_kodu_kullan('THIRD001');
  if a is distinct from 'Birakilacak Kafe' then
    raise exception 'BASARISIZ: yeniden sahiplenilemedi (%)', a;
  end if;
  raise notice 'gecti: birakilan mekan yeniden sahiplenildi';
end $$;

\echo '--- 18. BASKASININ sahipligi birakilamiyor'
do $$
declare hedef bigint; d text;
begin
  select id into hedef from public.sahiplik
   where mekan_id = 'node/50' and durum = 'aktif';   -- 2. kullanicinin
  set local request.jwt.claim.sub = '11111111-1111-4111-8111-111111111111';
  begin
    perform public.sahipligi_birak(hedef);
    raise exception 'BASARISIZ: baskasinin sahipligi birakildi';
  exception when check_violation then null;          -- beklenen
  end;
  select durum into d from public.sahiplik where id = hedef;
  if d <> 'aktif' then raise exception 'BASARISIZ: durum degismis (%)', d; end if;
  raise notice 'gecti: yalniz kendi sahipligini birakabiliyor';
end $$;

\echo '--- 19. kullanici sahiplik satirini SILEMIYOR ve GUNCELLEYEMIYOR'
-- Silme politikasi kaldirildi; birakma tek sutuna dokunan fonksiyondan
-- geciyor. Bir UPDATE politikasi olsaydi kullanici ayni istekte mekan_id'yi
-- de degistirip tutmak istedigimiz kaydi bozabilirdi.
set request.jwt.claim.sub = '22222222-2222-4222-8222-222222222222';
do $$
declare n int; hedef bigint;
begin
  -- `kullanici` sutunu okunamiyor (bkz. 12-13), o yuzden WHERE'de
  -- kullanilamaz. Kendi satirini id ile hedefliyoruz; RLS zaten yalniz
  -- gorebildigi satirlara dokunmasina izin verir.
  select id into hedef from public.sahiplik where durum = 'aktif' and mekan_id = 'node/50';

  delete from public.sahiplik where id = hedef;
  get diagnostics n = row_count;
  if n > 0 then raise exception 'BASARISIZ: kullanici % satir sildi', n; end if;

  update public.sahiplik set mekan_id = 'node/999' where id = hedef;
  get diagnostics n = row_count;
  if n > 0 then raise exception 'BASARISIZ: kullanici % satir guncelledi', n; end if;

  if not exists (select 1 from public.sahiplik where durum = 'aktif'
                 and mekan_id = 'node/50') then
    raise exception 'BASARISIZ: kayit bozulmus';
  end if;
  raise notice 'gecti: dogrudan silme ve guncelleme kapali';
exception when insufficient_privilege then
  -- Yetki katmani daha once kesiyorsa da sonuc ayni: yol kapali.
  raise notice 'gecti: dogrudan silme/guncelleme yetkide kesiliyor';
end $$;

\echo '--- 20. birakilan sahiplik anon icin GORUNMUYOR'
-- Isletme sayfasindaki rozet yalniz aktif sahipligi gostermeli; birakilan
-- bir kayit "bu isletme dogrulandi" demeye devam ederse rozet yalan olur.
reset role; set role anon;
do $$
declare n int;
begin
  select count(*) into n from public.sahiplik where durum <> 'aktif';
  if n > 0 then raise exception 'BASARISIZ: anon % aktif olmayan satir goruyor', n; end if;
  raise notice 'gecti: yalniz aktif sahiplik gorunuyor';
end $$;
reset role;

\echo '=== 20 kontrolun hepsi gecti ==='
