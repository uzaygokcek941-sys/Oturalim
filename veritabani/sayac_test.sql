-- ============================================================
-- Cebimde — sayaç davranış testi (gerçek Postgres'te)
--
-- Bu dosya kurulum SQL'i DEGIL. Supabase'e yapistirma.
-- Kosumu: sh veritabani/kos.sh  (test.py ve CI onu cagiriyor)
--
-- NEDEN AYRI: sayac.sql'in kendi kontrolu YETKILERE bakiyor -- "anon
-- yazabiliyor mu", "tuzu okuyabiliyor mu". Hepsi gerekli ama hicbiri
-- sayacin DOGRU SAYDIGINI soylemiyor. Oysa isletmeye satilan cumle bu:
-- "sayfani bu ay 47 kisi gordu". Sayi yanlissa fiyatta yanilmis olmuyoruz,
-- YALAN SOYLEMIS oluyoruz -- dosyanin kendi basligindaki kural bu.
--
-- Her adim ya "gecti" der ya da BASARISIZ diye patlar.
-- ============================================================
\set ON_ERROR_STOP on
\pset pager off
truncate public.goruntulenme;

-- İstemcinin dokunamadığı tek şey isteğin başlıkları; PostgREST onları
-- request.headers'a koyuyor. Testte de oradan besliyoruz.
\echo '--- 1. baslik varken sayiyor'
set request.headers = '{"x-forwarded-for":"1.2.3.4","user-agent":"A"}';
do $$
declare o record;
begin
  perform public.mekan_goruldu('node/1');
  select * into o from public.mekan_sayaci('node/1');
  if o.bugun <> 1 or o.toplam <> 1 then
    raise exception 'BASARISIZ: ilk bakista % / %', o.bugun, o.toplam;
  end if;
  raise notice 'gecti: ilk goruntulenme sayildi';
end $$;

\echo '--- 2. AYNI ziyaretci ayni gun tekrar sayilmiyor'
-- Sayfayi 40 kez yenilemek sayiyi artirmamali. Birincil anahtar bunu
-- durduruyor; durdurmazsa "47 kisi gordu" cumlesi bir kisinin yenilemesi
-- olabilir.
do $$
declare o record;
begin
  perform public.mekan_goruldu('node/1');
  perform public.mekan_goruldu('node/1');
  perform public.mekan_goruldu('node/1');
  select * into o from public.mekan_sayaci('node/1');
  if o.toplam <> 1 then
    raise exception 'BASARISIZ: ayni ziyaretci % kez sayildi', o.toplam;
  end if;
  raise notice 'gecti: tekrar yenileme sayiyi artirmiyor';
end $$;

\echo '--- 3. FARKLI IP ayri sayiliyor'
set request.headers = '{"x-forwarded-for":"5.6.7.8","user-agent":"A"}';
do $$
declare o record;
begin
  perform public.mekan_goruldu('node/1');
  select * into o from public.mekan_sayaci('node/1');
  if o.toplam <> 2 then
    raise exception 'BASARISIZ: iki ayri IP % sayildi, 2 olmaliydi', o.toplam;
  end if;
  raise notice 'gecti: ayri ziyaretci ayri sayiliyor';
end $$;

\echo '--- 4. ayni IP, FARKLI tarayici ayri sayiliyor (CGNAT)'
-- Turkiye'de mobil operatorler CGNAT kullaniyor: ayni IP'nin arkasinda
-- cok kisi var. Tarayici basligi bunu bir miktar ayiriyor. Ayirmasaydi
-- sayac gercegi oldugundan cok daha az gosterirdi.
set request.headers = '{"x-forwarded-for":"1.2.3.4","user-agent":"B"}';
do $$
declare o record;
begin
  perform public.mekan_goruldu('node/1');
  select * into o from public.mekan_sayaci('node/1');
  if o.toplam <> 3 then
    raise exception 'BASARISIZ: tarayici ayrimi calismiyor (%)', o.toplam;
  end if;
  raise notice 'gecti: tarayici basligi ziyaretciyi ayiriyor';
end $$;

\echo '--- 5. x-forwarded-for YOKSA sayilmiyor'
-- Uydurma bir sabite dusmek, o isteklerin hepsini tek bir hayali
-- ziyaretcide toplar ve sayiyi sessizce bozardi.
set request.headers = '{"user-agent":"A"}';
do $$
declare o record;
begin
  perform public.mekan_goruldu('node/1');
  select * into o from public.mekan_sayaci('node/1');
  if o.toplam <> 3 then
    raise exception 'BASARISIZ: IP''siz istek sayildi (%)', o.toplam;
  end if;
  raise notice 'gecti: IP okunamayinca sayilmiyor';
end $$;

\echo '--- 6. baslik hic yokken de catlamiyor'
reset request.headers;
do $$
begin
  perform public.mekan_goruldu('node/1');
  raise notice 'gecti: basliksiz cagri sessizce gecti';
end $$;

\echo '--- 7. mekanlar birbirine karismiyor'
set request.headers = '{"x-forwarded-for":"1.2.3.4","user-agent":"A"}';
do $$
declare o record;
begin
  perform public.mekan_goruldu('node/2');
  select * into o from public.mekan_sayaci('node/2');
  if o.toplam <> 1 then
    raise exception 'BASARISIZ: node/2 icin % sayildi', o.toplam;
  end if;
  select * into o from public.mekan_sayaci('node/1');
  if o.toplam <> 3 then
    raise exception 'BASARISIZ: node/1 sayisi degisti (%)', o.toplam;
  end if;
  raise notice 'gecti: mekan basina ayri sayiliyor';
end $$;

\echo '--- 8. son30 penceresi: 30 gunden eski satir toplamda var, son30''da yok'
do $$
declare o record;
begin
  insert into public.goruntulenme (mekan_id, gun, cihaz)
  values ('node/3', current_date,      gen_random_uuid()),
         ('node/3', current_date - 29, gen_random_uuid()),
         ('node/3', current_date - 30, gen_random_uuid()),   -- pencerenin DISI
         ('node/3', current_date - 90, gen_random_uuid());
  select * into o from public.mekan_sayaci('node/3');
  if o.bugun <> 1 then raise exception 'BASARISIZ: bugun %', o.bugun; end if;
  if o.son30 <> 2 then raise exception 'BASARISIZ: son30 %, 2 olmaliydi', o.son30; end if;
  if o.toplam <> 4 then raise exception 'BASARISIZ: toplam %', o.toplam; end if;
  if o.ilk_gun <> current_date - 90 then
    raise exception 'BASARISIZ: ilk_gun %', o.ilk_gun;
  end if;
  raise notice 'gecti: bugun 1 / son30 2 / toplam 4';
end $$;

\echo '--- 9. sayisi olmayan mekan sifir donuyor, satir donmuyor'
do $$
declare o record;
begin
  select * into o from public.mekan_sayaci('hic/yok');
  if o.toplam <> 0 or o.ilk_gun is not null then
    raise exception 'BASARISIZ: bos mekan % / %', o.toplam, o.ilk_gun;
  end if;
  raise notice 'gecti: bos mekan sifir';
end $$;

\echo '--- 10. gunler birbirine BAGLANAMIYOR (KVKK iddiasi)'
-- gizlilik.html "ozet her gun yenileniyor, ayni kisinin iki ayri gundeki
-- ziyareti birbirine baglanamaz" diyor. Bu bir SOZ; burada olculuyor.
-- Ayni IP + ayni tarayici + ayni tuz, yalniz gun farkli -> iz FARKLI olmali.
do $$
declare gizli uuid; dun uuid; bugun uuid;
begin
  select tuz into gizli from public.sayac_tuz limit 1;
  bugun := md5('1.2.3.4|A|' || current_date::text       || '|' || gizli::text)::uuid;
  dun   := md5('1.2.3.4|A|' || (current_date-1)::text   || '|' || gizli::text)::uuid;
  if bugun = dun then
    raise exception 'BASARISIZ: iz gunler arasi ayni, ziyaretci izlenebilir';
  end if;
  -- Ve uretilen iz gercekten bu formulden geliyor mu: 1. adimdaki satir
  -- bugunun izini tasimali. Yoksa yukaridaki karsilastirma bos bir
  -- matematik alistirmasi olurdu.
  if not exists (select 1 from public.goruntulenme
                 where mekan_id = 'node/1' and gun = current_date and cihaz = bugun) then
    raise exception 'BASARISIZ: tabloda beklenen iz yok, formul ayrismis';
  end if;
  raise notice 'gecti: iz her gun yenileniyor ve formul tabloyla ayni';
end $$;

\echo '--- 11. tuz gercekten karisiyor'
-- Tuz olmasa, satirlari ele geciren biri IP uzayini tarayip ziyaretci
-- IP'lerini geri cozebilirdi. Tuzsuz ozet tablodakiyle ESLESMEMELI.
do $$
declare tuzsuz uuid;
begin
  tuzsuz := md5('1.2.3.4|A|' || current_date::text || '|')::uuid;
  if exists (select 1 from public.goruntulenme where cihaz = tuzsuz) then
    raise exception 'BASARISIZ: ozet tuzsuz uretilmis, IP geri cozulebilir';
  end if;
  raise notice 'gecti: tuz ozete karisiyor';
end $$;

\echo '--- 12. BUTCE BANDI kaydediliyor ve dagilim donuyor'
-- Isletme sahibinin panelindeki tek OZGUN sayi bu: "bana bakanlar hangi
-- butceyle ariyordu". Goruntulenme sayisini her sayac verir, butce
-- talebini vermez.
reset role;
truncate public.goruntulenme;
insert into public.goruntulenme (mekan_id, gun, cihaz, butce_bandi) values
  ('node/b', current_date, gen_random_uuid(), 1),
  ('node/b', current_date, gen_random_uuid(), 1),
  ('node/b', current_date, gen_random_uuid(), 2),
  ('node/b', current_date, gen_random_uuid(), 5),
  -- BUTCESIZ bakis: dagilima girmiyor ama esik sayimina giriyor.
  ('node/b', current_date, gen_random_uuid(), null);
set role anon;
do $$
declare r record; n int := 0; toplam int := 0;
begin
  for r in select * from public.mekan_butce_talebi('node/b') loop
    n := n + 1; toplam := toplam + r.kisi;
    if r.bant = 1 and r.kisi <> 2 then
      raise exception 'BASARISIZ: bant 1 kisi % (2)', r.kisi;
    end if;
  end loop;
  if n <> 3 then raise exception 'BASARISIZ: % bant dondu (3)', n; end if;
  -- Butcesiz bakis dagilimda YOK: "bilinmiyor" ile "farketmez" ayri
  -- seyler ve ikisini birlestirmek dagilimi bozar.
  if toplam <> 4 then raise exception 'BASARISIZ: dagilim toplami % (4)', toplam; end if;
  raise notice 'gecti: 3 bant, 4 kisi, butcesiz bakis disarida';
end $$;

\echo '--- 13. ESIK ALTINDA dagilim HIC donmuyor (k-anonimlik)'
-- Kucuk sayilarda "bakanlarin 1'i 150 TL altiydi" demek, o tek kisinin
-- butcesini ifsa etmekle ayni sey -- hele isletmecinin tanidigi biriyse.
-- Esik fis esiginden yuksek (5) cunku burada DAGILIMIN KENDISI donuyor.
reset role;
truncate public.goruntulenme;
insert into public.goruntulenme (mekan_id, gun, cihaz, butce_bandi) values
  ('node/az', current_date, gen_random_uuid(), 1),
  ('node/az', current_date, gen_random_uuid(), 2),
  ('node/az', current_date, gen_random_uuid(), 3),
  ('node/az', current_date, gen_random_uuid(), 4);
set role anon;
do $$
declare n int;
begin
  select count(*) into n from public.mekan_butce_talebi('node/az');
  if n <> 0 then raise exception 'BASARISIZ: esik alti % bant dondu', n; end if;
  raise notice 'gecti: 4 bakista dagilim yok';
end $$;

\echo '--- 13b. ESIK ASILINCA dagilim geliyor (esik fazla yukseltilmedi)'
-- Yalniz "gizliyor mu" diye bakmak yetmez: esigi 500 yapan bir
-- degisiklik de 13. adimi gecirir ve ozelligi sessizce goturur.
reset role;
insert into public.goruntulenme (mekan_id, gun, cihaz, butce_bandi)
  values ('node/az', current_date, gen_random_uuid(), 1);
set role anon;
do $$
declare n int;
begin
  select count(*) into n from public.mekan_butce_talebi('node/az');
  if n <> 4 then raise exception 'BASARISIZ: 5 bakista % bant dondu (4)', n; end if;
  raise notice 'gecti: 5 bakista dagilim aciliyor';
end $$;

\echo '--- 14. BAYAT bakis dagilima girmiyor (30 gun)'
reset role;
truncate public.goruntulenme;
insert into public.goruntulenme (mekan_id, gun, cihaz, butce_bandi)
select 'node/eski', current_date - 40, gen_random_uuid(), 1 from generate_series(1, 9);
set role anon;
do $$
declare n int;
begin
  select count(*) into n from public.mekan_butce_talebi('node/eski');
  if n <> 0 then raise exception 'BASARISIZ: 40 gunluk bakis sayildi'; end if;
  raise notice 'gecti: bayat bakis disarida';
end $$;

\echo '--- 15. BOZUK bant goruntulenmeyi DUSURMUYOR'
-- Sayac bir olcum araci; istemciden gelen bozuk bir bant yuzunden
-- gorunmenin kendisi kaybolmamali. Bant null'a duser, satir kalir.
reset role;
truncate public.goruntulenme;
set role anon;
select public.mekan_goruldu('node/bozuk', 99::smallint);
reset role;
do $$
declare n int; b smallint;
begin
  select count(*), max(butce_bandi) into n, b
    from public.goruntulenme where mekan_id = 'node/bozuk';
  if n <> 1 then raise exception 'BASARISIZ: bozuk bant satiri dusurdu (% satir)', n; end if;
  if b is not null then raise exception 'BASARISIZ: aralik disi bant kaydedildi (%)', b; end if;
  raise notice 'gecti: bozuk bant null, gorunme kaydedildi';
end $$;

\echo '--- 16. anon HAM satirlari hala goremiyor'
set role anon;
do $$
declare n int;
begin
  begin
    select count(*) into n from public.goruntulenme;
    raise exception 'BASARISIZ: anon goruntulenme okuyabiliyor (% satir)', n;
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: ham satirlar kapali';
end $$;
reset role;

\echo '=== sayac: 16 kontrolun hepsi gecti ==='
