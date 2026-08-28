-- ============================================================
-- Cebimde — bayilik davranış testi (gerçek Postgres'te)
--
-- Bu dosya kurulum SQL'i DEĞİL. Supabase'e yapıştırma.
-- Koşturmak için: sh veritabani/kos.sh
--
-- NE SINIYOR. Bayilikte iki şey yanlış giderse zarar somut: (a) bir
-- bayinin başka bir bayinin ya da işletmecinin verisini görmesi,
-- (b) hakedişin koddan değil başka bir yerden doğması. Aşağıdaki
-- adımlar tam olarak bu ikisini ölçüyor.
--
-- Her adım ya "gecti" der ya da BASARISIZ diye patlar. Sessizce geçmez.
-- ============================================================
\set ON_ERROR_STOP on
\pset pager off

truncate public.bayi_kazanim, public.bayi_odeme, public.bayi_bolge,
         public.bayi, public.sahiplik, public.sahiplenme_kodu,
         public.katkilar restart identity cascade;

-- Üç kişi: iki bayi + bir işletmeci.
insert into auth.users (id) values
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),   -- bayi A
  ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'),   -- bayi B
  ('cccccccc-cccc-4ccc-8ccc-cccccccccccc')    -- isletmeci
  on conflict do nothing;
insert into public.profiller (id) values
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'),
  ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'),
  ('cccccccc-cccc-4ccc-8ccc-cccccccccccc')
  on conflict do nothing;

-- Ücret: sahiplenme 25 TL, alan 75 TL (kuruş).
insert into public.bayi (kullanici, ad, durum, sahiplenme_ucreti, alan_ucreti)
values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','Bayi A','aktif',2500,7500),
       ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','Bayi B','aktif',2500,7500);

insert into public.bayi_bolge (bayi, il, ilce) values (1,'06','Çankaya');

-- A'nın iki kartı, B'nin bir kartı, bir de bayisiz kart.
insert into public.sahiplenme_kodu (kod_ozeti, mekan_id, il, mekan_ad, bayi, parti) values
  (encode(digest('AAAA2345','sha256'),'hex'),'node/1','06','A Kafe',   1,'ankara-51'),
  (encode(digest('AAAA2346','sha256'),'hex'),'node/2','06','A Bar',    1,'ankara-51'),
  (encode(digest('AAAA2347','sha256'),'hex'),'node/4','06','A Lokanta',1,'ankara-51'),
  (encode(digest('BBBB2345','sha256'),'hex'),'node/3','34','B Kafe',   2,'kadikoy-1'),
  (encode(digest('CCCC2345','sha256'),'hex'),'node/9','06','Sahipsiz', null,null);

\echo '--- 1. anon bayi tablosunu okuyamaz'
set role anon;
do $$ begin
  perform 1 from public.bayi limit 1;
  raise exception 'BASARISIZ: anon bayi tablosunu okudu';
exception when insufficient_privilege then raise notice 'gecti: anon okuyamiyor';
end $$;
reset role;

\echo '--- 2. bayi kendi satirini gorur, digerininkini gormez'
set role authenticated;
set request.jwt.claim.sub = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
do $$
declare n int;
begin
  select count(*) into n from public.bayi;
  if n <> 1 then raise exception 'BASARISIZ: bayi % satir gordu, 1 olmali', n; end if;
  raise notice 'gecti: yalniz kendi satiri';
end $$;

\echo '--- 3. kimlik sutunu tarayiciya kapali'
do $$ begin
  perform kullanici from public.bayi limit 1;
  raise exception 'BASARISIZ: bayi.kullanici okundu';
exception when insufficient_privilege then raise notice 'gecti: kullanici sutunu kapali';
end $$;

\echo '--- 4. kimse kendini bayi yapamaz'
do $$ begin
  insert into public.bayi (kullanici, ad, durum)
  values ('cccccccc-cccc-4ccc-8ccc-cccccccccccc','Kendi kendine','aktif');
  raise exception 'BASARISIZ: kullanici kendini bayi yapti';
exception
  when insufficient_privilege or check_violation then
    raise notice 'gecti: yazma politikasi yok';
end $$;

\echo '--- 5. kart kullanilinca hakedis KENDILIGINDEN dogar'
reset role;
reset request.jwt.claim.sub;
set role authenticated;
set request.jwt.claim.sub = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
select public.sahiplenme_kodu_kullan('aaaa-2345');
reset role;
do $$
declare t int;
begin
  select tutar into t from public.bayi_kazanim
   where bayi = 1 and mekan_id = 'node/1' and tur = 'sahiplenme';
  if t is null then raise exception 'BASARISIZ: sahiplenme kazanimi yazilmadi'; end if;
  if t <> 2500 then raise exception 'BASARISIZ: tutar % , 2500 olmali', t; end if;
  raise notice 'gecti: 2500 kurus yazildi';
end $$;

\echo '--- 6. oran degisince GECMIS kazanim degismez'
update public.bayi set sahiplenme_ucreti = 9900 where id = 1;
do $$
declare t int;
begin
  select tutar into t from public.bayi_kazanim
   where bayi = 1 and mekan_id = 'node/1' and tur = 'sahiplenme';
  if t <> 2500 then raise exception 'BASARISIZ: gecmis tutar % oldu', t; end if;
  raise notice 'gecti: hakedis aninda donduruldu';
end $$;
update public.bayi set sahiplenme_ucreti = 2500 where id = 1;

\echo '--- 7. onaylanan katki -> alan kazanimi, ikinci katki IKI KEZ yazmaz'
insert into public.katkilar (kullanici, mekan_id, il, mekan_ad, alan, deger, durum)
values ('cccccccc-cccc-4ccc-8ccc-cccccccccccc','node/1','06','A Kafe','tel','0312 000 00 00','onaylandi'),
       ('cccccccc-cccc-4ccc-8ccc-cccccccccccc','node/1','06','A Kafe','web','https://ornek.test','onaylandi');
do $$
declare n int; t int;
begin
  select count(*), max(tutar) into n, t from public.bayi_kazanim
   where bayi = 1 and mekan_id = 'node/1' and tur = 'alan';
  if n <> 1 then raise exception 'BASARISIZ: alan kazanimi % satir, 1 olmali', n; end if;
  if t <> 7500 then raise exception 'BASARISIZ: alan tutari %', t; end if;
  raise notice 'gecti: mekan basina tek alan kazanimi';
end $$;

\echo '--- 8. bekleyen katki hakedis dogurmaz'
-- KART KULLANILMIS BIR MEKANDA sinaniyor ve bu sart. Ilk yazimda kart
-- kullanilmamis bir mekan secilmisti; o mekanda zaten hicbir bayi
-- bulunamadigi icin adim, onay kontrolu SILINSE DE geciyordu. Sabotajla
-- olculdu: kontrolu kaldirdim, test yesil kaldi. Yani adim bir sey
-- sinamiyordu.
set role authenticated;
set request.jwt.claim.sub = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
select public.sahiplenme_kodu_kullan('aaaa-2347');
reset role;
reset request.jwt.claim.sub;
insert into public.katkilar (kullanici, mekan_id, il, mekan_ad, alan, deger)
values ('cccccccc-cccc-4ccc-8ccc-cccccccccccc','node/4','06','A Lokanta','tel','0312 111 11 11');
do $$
declare n int;
begin
  select count(*) into n from public.bayi_kazanim
   where mekan_id = 'node/4' and tur = 'alan';
  if n <> 0 then raise exception 'BASARISIZ: bekleyen katki % kazanim yazdi', n; end if;
  raise notice 'gecti: yalniz onaylanan sayiliyor';
end $$;

\echo '--- 9. karti olmayan mekanin katkisi hicbir bayiye yazilmaz'
insert into public.katkilar (kullanici, mekan_id, il, mekan_ad, alan, deger, durum)
values ('cccccccc-cccc-4ccc-8ccc-cccccccccccc','node/777','06','Kartsiz','tel','0312 222 22 22','onaylandi');
do $$
declare n int;
begin
  select count(*) into n from public.bayi_kazanim where mekan_id = 'node/777';
  if n <> 0 then raise exception 'BASARISIZ: kartsiz mekan % kazanim yazdi', n; end if;
  raise notice 'gecti: saha isi yoksa hakedis yok';
end $$;

\echo '--- 10. kazanima ELLE yazilamiyor (yonetici bile)'
-- Yonetici atamasi auth.uid() NULL iken yapilmali: profil tetikleyicisi
-- (yonetici_alani_korumali) kullaniciyi kendini yonetici yapmaktan
-- aliyor ve 5. adimdan kalan jwt burada hala okunuyordu.
reset request.jwt.claim.sub;
update public.profiller set yonetici = true
 where id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
set role authenticated;
set request.jwt.claim.sub = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
do $$ begin
  insert into public.bayi_kazanim (bayi, mekan_id, mekan_ad, il, tur, tutar)
  values (2,'node/3','B Kafe','34','sahiplenme',999999);
  raise exception 'BASARISIZ: kazanima elle yazildi';
exception
  when insufficient_privilege or check_violation then
    raise notice 'gecti: tek kaynak tetikleyici';
end $$;
reset role;
reset request.jwt.claim.sub;
update public.profiller set yonetici = false
 where id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';

\echo '--- 11. bayi baskasinin kazanimini gormez'
set role authenticated;
set request.jwt.claim.sub = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
do $$
declare n int;
begin
  select count(*) into n from public.bayi_kazanim;
  if n <> 0 then raise exception 'BASARISIZ: B, A nin % kazanimini gordu', n; end if;
  raise notice 'gecti: kazanim bayiye kilitli';
end $$;

\echo '--- 12. bayi_kartlarim yalniz kendi kartlarini veriyor'
do $$
declare n int; m text;
begin
  select count(*), min(mekan_id) into n, m from public.bayi_kartlarim();
  if n <> 1 or m <> 'node/3' then
    raise exception 'BASARISIZ: B, % kart gordu (%)', n, m;
  end if;
  raise notice 'gecti: kartlar bayiye kilitli';
end $$;

\echo '--- 13. bayi olmayan panel fonksiyonlarini cagiramaz'
reset role;
reset request.jwt.claim.sub;
set role authenticated;
set request.jwt.claim.sub = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
do $$ begin
  perform public.bayi_ozetim();
  raise exception 'BASARISIZ: bayi olmayan ozet aldi';
exception when insufficient_privilege then raise notice 'gecti: ozet kapali';
end $$;

\echo '--- 14. ozet: hakedis - odenen = bakiye'
reset role;
reset request.jwt.claim.sub;
insert into public.bayi_odeme (bayi, tutar, aciklama) values (1, 5000, 'ilk odeme');
set role authenticated;
set request.jwt.claim.sub = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
do $$
declare o record;
begin
  select * into o from public.bayi_ozetim();
  -- 3 kart, 2 sahiplenme, 1 alan; hakedis 2*2500 + 7500 = 12500, odenen 5000.
  if o.kart <> 3 then raise exception 'BASARISIZ: kart %', o.kart; end if;
  if o.sahiplenilen <> 2 then raise exception 'BASARISIZ: sahiplenilen %', o.sahiplenilen; end if;
  if o.alan_eklenen <> 1 then raise exception 'BASARISIZ: alan %', o.alan_eklenen; end if;
  if o.hakedis <> 12500 then raise exception 'BASARISIZ: hakedis %', o.hakedis; end if;
  if o.odenen <> 5000 then raise exception 'BASARISIZ: odenen %', o.odenen; end if;
  if o.bakiye <> 7500 then raise exception 'BASARISIZ: bakiye %', o.bakiye; end if;
  raise notice 'gecti: 12500 - 5000 = 7500 kurus';
end $$;

\echo '--- 15. bolgem yalniz kendi bolgem'
do $$
declare n int;
begin
  select count(*) into n from public.bayi_bolgelerim();
  if n <> 1 then raise exception 'BASARISIZ: bolge %', n; end if;
  raise notice 'gecti: 1 bolge';
end $$;
reset role;
reset request.jwt.claim.sub;

\echo '--- 16. bir ilcenin ayni anda tek bayisi olur'
do $$ begin
  insert into public.bayi_bolge (bayi, il, ilce) values (2,'06','Çankaya');
  raise exception 'BASARISIZ: ayni ilceye ikinci bayi girdi';
exception when unique_violation then raise notice 'gecti: bolge tekil';
end $$;
-- Bırakılan bölge yeni bayinin önünü tıkamıyor.
update public.bayi_bolge set durum = 'birakildi' where bayi = 1;
insert into public.bayi_bolge (bayi, il, ilce) values (2,'06','Çankaya');

\echo '--- 17. once bayisiz yazilmis kod, sonradan bayiye baglanabiliyor'
-- YASANMIS HAL. Ankara 51 ve 52 once bayisiz basildi ve SQL'leri
-- calistirildi; bayilik sonradan kuruldu. Ayni partiyi bayiye baglayan
-- ikinci SQL'de kod_ozeti AYNI (kodlar degismedi), yani 'on conflict
-- do nothing' ikinci calistirmayi sessizce yutuyordu: kodlar yerinde,
-- bayi bos, hata yok. saha.py artik bayili SQL'de 'do update' yaziyor
-- ve bu adim onun gercekten tuttugunu olcuyor.
insert into public.sahiplenme_kodu (kod_ozeti, mekan_id, il, mekan_ad)
values (encode(digest('DDDD2345','sha256'),'hex'),'node/5','06','Sonradan');
insert into public.sahiplenme_kodu
  (kod_ozeti, mekan_id, il, mekan_ad, gecerlilik, bayi, parti)
values (encode(digest('DDDD2345','sha256'),'hex'),'node/5','06','Sonradan',
        current_date + 180, 1, 'ankara-51')
on conflict (kod_ozeti) do update
   set bayi = excluded.bayi, parti = excluded.parti
 where public.sahiplenme_kodu.kullanildi is null;
do $$
declare b bigint; p text;
begin
  select bayi, parti into b, p from public.sahiplenme_kodu
   where mekan_id = 'node/5';
  if b is distinct from 1 or p is distinct from 'ankara-51' then
    raise exception 'BASARISIZ: bayisiz kod baglanmadi (bayi=%, parti=%)', b, p;
  end if;
  raise notice 'gecti: basilmis parti yeniden basmadan baglandi';
end $$;

\echo '--- 18. KULLANILMIS kartin atfi geriye donuk degismiyor'
-- node/1'in kodu 5. adimda kullanildi ve hakedisi o an dogdu. Atfi
-- baska bir bayiye tasimak, kapanmis bir hesabi yeniden yazmak olurdu.
insert into public.sahiplenme_kodu
  (kod_ozeti, mekan_id, il, mekan_ad, gecerlilik, bayi, parti)
values (encode(digest('AAAA2345','sha256'),'hex'),'node/1','06','A Kafe',
        current_date + 180, 2, 'calinti')
on conflict (kod_ozeti) do update
   set bayi = excluded.bayi, parti = excluded.parti
 where public.sahiplenme_kodu.kullanildi is null;
do $$
declare b bigint;
begin
  select bayi into b from public.sahiplenme_kodu where mekan_id = 'node/1';
  if b is distinct from 1 then
    raise exception 'BASARISIZ: kullanilmis kartin bayisi % oldu', b;
  end if;
  raise notice 'gecti: kullanilmis kartin atfi korundu';
end $$;

\echo 'BAYILIK TESTI: 18 adim gecti'
