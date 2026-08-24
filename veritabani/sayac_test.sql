-- ============================================================
-- Oturalım — sayaç davranış testi (gerçek Postgres'te)
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

\echo '=== sayac: 11 kontrolun hepsi gecti ==='
