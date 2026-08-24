-- ============================================================
-- Oturalım — profil ve yorum davranış testi (gerçek Postgres'te)
--
-- Bu dosya kurulum SQL'i DEGIL. Supabase'e yapistirma.
-- Kosumu: sh veritabani/kos.sh  (test.py ve CI onu cagiriyor)
--
-- Her adim ya "gecti" der ya da BASARISIZ diye patlar.
-- ============================================================
\set ON_ERROR_STOP on
\pset pager off
truncate public.yorumlar restart identity cascade;

reset role;
insert into auth.users (id) values
  ('33333333-3333-4333-8333-333333333333'),
  ('44444444-4444-4444-8444-444444444444') on conflict do nothing;
-- Tetikleyici profili acmis olmali; alanlari dolduruyoruz.
insert into public.profiller (id, kullanici_adi)
  values ('33333333-3333-4333-8333-333333333333', public.kullanici_adi_uret())
  on conflict (id) do nothing;
insert into public.profiller (id, kullanici_adi)
  values ('44444444-4444-4444-8444-444444444444', public.kullanici_adi_uret())
  on conflict (id) do nothing;
update public.profiller
   set kullanici_adi = 'ayse', ad = 'Ayşe', dogum_yili = 1998,
       meslek = 'Öğretmen', kisilik = 'Sessiz köşe severim', herkese_acik = true
 where id = '33333333-3333-4333-8333-333333333333';
update public.profiller
   set kullanici_adi = 'gizli_kisi', ad = 'Mehmet', dogum_yili = 1990,
       meslek = 'Mühendis', herkese_acik = false
 where id = '44444444-4444-4444-8444-444444444444';

\echo '--- 1. her profilin bir adresi var (uuid disari cikmasin diye)'
do $$
declare n int;
begin
  select count(*) into n from public.profiller where kullanici_adi is null;
  if n > 0 then raise exception 'BASARISIZ: % profilin kullanici adi yok', n; end if;
  raise notice 'gecti: adsiz profil yok';
end $$;

\echo '--- 2. uretilen ad SIRALI DEGIL (kac kullanici oldugu sizmasin)'
do $$
declare a text; b text;
begin
  a := public.kullanici_adi_uret();
  b := public.kullanici_adi_uret();
  if a = b then raise exception 'BASARISIZ: ayni ad iki kez uretildi'; end if;
  if a !~ '^[a-z0-9_]{3,20}$' then raise exception 'BASARISIZ: bicim disi ad %', a; end if;
  raise notice 'gecti: % / %', a, b;
end $$;

\echo '--- 3. anon profiller TABLOSUNU okuyamiyor'
-- Acilirsa uuid ile profil eslesmesi disari cikar; sema.sql'de kapatilan
-- kapi yandan geri acilmis olur.
set role anon;
do $$
declare n int;
begin
  select count(*) into n from public.profiller;
  if n > 0 then raise exception 'BASARISIZ: anon % profil goruyor', n; end if;
  raise notice 'gecti: tablo kapali';
end $$;

\echo '--- 4. ama HERKESE ACIK profil fonksiyonla okunuyor'
do $$
declare o record;
begin
  select * into o from public.profil_getir('ayse');
  if o.ad is distinct from 'Ayşe' then raise exception 'BASARISIZ: ad %', o.ad; end if;
  if o.dogum_yili <> 1998 then raise exception 'BASARISIZ: dogum %', o.dogum_yili; end if;
  if o.meslek is distinct from 'Öğretmen' then raise exception 'BASARISIZ: meslek'; end if;
  raise notice 'gecti: % (%), %', o.ad, o.dogum_yili, o.meslek;
end $$;

\echo '--- 5. buyuk harfle yazilan ad da bulunuyor'
do $$
declare o record;
begin
  select * into o from public.profil_getir('AySE');
  if o.ad is null then raise exception 'BASARISIZ: buyuk harfli ad bulunamadi'; end if;
  raise notice 'gecti: buyuk/kucuk harf onemsiz';
end $$;

\echo '--- 6. profilini KAPATAN kullanici hic donmuyor'
do $$
declare n int;
begin
  select count(*) into n from public.profil_getir('gizli_kisi');
  if n <> 0 then raise exception 'BASARISIZ: kapali profil dondu'; end if;
  select count(*) into n from public.profil_getir('boyle_biri_yok');
  if n <> 0 then raise exception 'BASARISIZ: olmayan profil dondu'; end if;
  raise notice 'gecti: kapali ve olmayan profil donmuyor';
end $$;

\echo '--- 7. yorum ONAYSIZ yayina girmiyor'
set role authenticated;
set request.jwt.claim.sub = '33333333-3333-4333-8333-333333333333';
do $$
declare d text; n int;
begin
  insert into public.yorumlar (kullanici, mekan_id, il, mekan_ad, puan, metin)
  values (auth.uid(), 'node/70', '06', 'Yorum Kafe', 5, 'Sessiz ve ucuz');
  select durum into d from public.yorumlar where mekan_id = 'node/70';
  if d <> 'bekliyor' then raise exception 'BASARISIZ: durum %', d; end if;
  select count(*) into n from public.mekan_yorumlari('node/70');
  if n <> 0 then raise exception 'BASARISIZ: onaysiz yorum yayinda'; end if;
  raise notice 'gecti: kuyrukta bekliyor, yayinda yok';
end $$;

\echo '--- 8. kullanici durumu KENDI belirleyemiyor'
-- Belirleyebilseydi onay sartinin tamami anlamsiz olurdu.
do $$
begin
  begin
    insert into public.yorumlar (kullanici, mekan_id, il, mekan_ad, puan, durum)
    values (auth.uid(), 'node/71', '06', 'Kacak Kafe', 5, 'onaylandi');
    raise exception 'BASARISIZ: kullanici kendi yorumunu onayladi';
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: politika reddetti';
end $$;

\echo '--- 9. ayni mekana IKINCI yorum yazilamiyor'
-- Yazilabilseydi ayni kisi bir mekani puan ortalamasinda tekrarlardi.
do $$
begin
  begin
    insert into public.yorumlar (kullanici, mekan_id, il, mekan_ad, puan)
    values (auth.uid(), 'node/70', '06', 'Yorum Kafe', 1);
    raise exception 'BASARISIZ: ayni mekana iki yorum yazildi';
  exception when unique_violation then null;
  end;
  raise notice 'gecti: tekil kisit tuttu';
end $$;

\echo '--- 10. puan sinirlari: 0 ve 6 kabul edilmiyor'
do $$
declare kotu int;
begin
  foreach kotu in array array[0, 6, -1] loop
    begin
      insert into public.yorumlar (kullanici, mekan_id, il, mekan_ad, puan)
      values (auth.uid(), 'node/8' || kotu::text, '06', 'X Kafe', kotu);
      raise exception 'BASARISIZ: puan % kabul edildi', kotu;
    exception when check_violation then null;
    end;
  end loop;
  raise notice 'gecti: puan 1-5 disi reddediliyor';
end $$;

\echo '--- 11. onaylandiginda yayina giriyor, YAZARIYLA birlikte'
reset role;
update public.yorumlar set durum = 'onaylandi' where mekan_id = 'node/70';
set role anon;
do $$
declare o record;
begin
  select * into o from public.mekan_yorumlari('node/70');
  if o.puan <> 5 then raise exception 'BASARISIZ: puan %', o.puan; end if;
  if o.yazar_ad is distinct from 'Ayşe' then
    raise exception 'BASARISIZ: yazar adi %', o.yazar_ad;
  end if;
  if o.yazar_adi is distinct from 'ayse' then
    raise exception 'BASARISIZ: yazar adresi %', o.yazar_adi;
  end if;
  if o.yazar_dogum <> 1998 then raise exception 'BASARISIZ: yazar dogum'; end if;
  raise notice 'gecti: % puan, yazar % (%)', o.puan, o.yazar_ad, o.yazar_adi;
end $$;

\echo '--- 12. profilini kapatanin YORUMU gorunur, ADI gorunmez'
-- Yorum mekana ait bir bilgi; kisiye ait olan sey ad ve fotograf.
reset role;
insert into public.yorumlar (kullanici, mekan_id, il, mekan_ad, puan, metin, durum)
values ('44444444-4444-4444-8444-444444444444', 'node/70', '06', 'Yorum Kafe',
        3, 'Fena degil', 'onaylandi');
set role anon;
do $$
declare n int; adli int;
begin
  select count(*) into n from public.mekan_yorumlari('node/70');
  if n <> 2 then raise exception 'BASARISIZ: % yorum gorunuyor, 2 olmaliydi', n; end if;
  select count(*) into adli from public.mekan_yorumlari('node/70')
   where yazar_ad is not null;
  if adli <> 1 then
    raise exception 'BASARISIZ: % yorumda yazar adi var, 1 olmaliydi', adli;
  end if;
  raise notice 'gecti: 2 yorum gorunuyor, 1 tanesi adsiz';
end $$;

\echo '--- 13. anon yorumlarda KIMLIK sutununu okuyamiyor'
-- Yorum metni ile uuid ayni satirda verilseydi bir kisinin nereye gidip
-- ne dusundugu tek sorguda toplanirdi.
do $$
begin
  begin
    perform kullanici from public.yorumlar limit 1;
    raise exception 'BASARISIZ: anon yorumlar.kullanici okudu';
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: kimlik sutunu kapali';
end $$;

\echo '--- 14. puan ozeti dogru hesapliyor'
do $$
declare o record;
begin
  select * into o from public.mekan_puani('node/70');
  if o.adet <> 2 then raise exception 'BASARISIZ: adet %', o.adet; end if;
  if o.ortalama <> 4.0 then raise exception 'BASARISIZ: ortalama %', o.ortalama; end if;
  select * into o from public.mekan_puani('hic/yok');
  if o.adet <> 0 or o.ortalama is not null then
    raise exception 'BASARISIZ: bos mekan % / %', o.adet, o.ortalama;
  end if;
  raise notice 'gecti: 2 yorum, ortalama 4.0';
end $$;

\echo '--- 15. il puanlari tek istekte, yalniz ONAYLI olanlardan'
reset role;
insert into public.yorumlar (kullanici, mekan_id, il, mekan_ad, puan, durum)
values ('33333333-3333-4333-8333-333333333333', 'node/72', '06', 'Ikinci Kafe', 2, 'onaylandi'),
       ('44444444-4444-4444-8444-444444444444', 'node/73', '06', 'Ucuncu Kafe', 5, 'bekliyor'),
       ('33333333-3333-4333-8333-333333333333', 'node/74', '34', 'Istanbul Kafe', 4, 'onaylandi');
set role anon;
do $$
declare n int; o record;
begin
  select count(*) into n from public.il_puanlari('06');
  if n <> 2 then raise exception 'BASARISIZ: 06 icin % mekan, 2 olmaliydi', n; end if;
  select * into o from public.il_puanlari('06') where mekan_id = 'node/72';
  if o.ortalama <> 2.0 then raise exception 'BASARISIZ: node/72 ortalama %', o.ortalama; end if;
  -- Bekleyen yorum GIRMEMELI, baska il de girmemeli.
  if exists (select 1 from public.il_puanlari('06') where mekan_id = 'node/73') then
    raise exception 'BASARISIZ: onaysiz yorum il puanina girdi';
  end if;
  if exists (select 1 from public.il_puanlari('06') where mekan_id = 'node/74') then
    raise exception 'BASARISIZ: baska ilin mekani girdi';
  end if;
  raise notice 'gecti: 2 mekan, onaysiz ve baska il disarida';
end $$;

\echo '--- 16. kullanici kendi yorumunu silebiliyor, baskasininkini silemiyor'
set role authenticated;
set request.jwt.claim.sub = '33333333-3333-4333-8333-333333333333';
do $$
declare n int; hedef bigint;
begin
  select id into hedef from public.yorumlar where mekan_id = 'node/72';
  delete from public.yorumlar where id = hedef;
  get diagnostics n = row_count;
  if n <> 1 then raise exception 'BASARISIZ: kendi yorumunu silemedi'; end if;

  -- 44444444'un yorumu (node/73)
  select id into hedef from public.yorumlar where mekan_id = 'node/73';
  delete from public.yorumlar where id = hedef;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'BASARISIZ: baskasinin yorumunu sildi'; end if;
  raise notice 'gecti: yalniz kendi yorumunu siliyor';
end $$;

\echo '--- 17. dogum yili sinirlari'
-- 13 yas alt siniri: altindaki icin veli onayi gerekir ve bu yapida alinamaz.
reset role;
do $$
declare kotu int;
begin
  foreach kotu in array array[1800, 2200] loop
    begin
      update public.profiller set dogum_yili = kotu
       where id = '33333333-3333-4333-8333-333333333333';
      raise exception 'BASARISIZ: dogum yili % kabul edildi', kotu;
    exception when check_violation then null;
    end;
  end loop;
  -- 13 yasindan kucuk
  begin
    update public.profiller set dogum_yili = extract(year from now())::int - 5
     where id = '33333333-3333-4333-8333-333333333333';
    raise exception 'BASARISIZ: 5 yasindaki kullanici kabul edildi';
  exception when check_violation then null;
  end;
  raise notice 'gecti: 1900-oncesi, gelecek ve 13 alti reddediliyor';
end $$;

\echo '--- 18. kullanici adi bicimi ve tekilligi'
do $$
declare kotu text;
begin
  foreach kotu in array array['ab', 'Ayse', 'ayşe', 'cok_cok_cok_uzun_bir_ad_daha', 'a b'] loop
    begin
      update public.profiller set kullanici_adi = kotu
       where id = '44444444-4444-4444-8444-444444444444';
      raise exception 'BASARISIZ: "%" kabul edildi', kotu;
    exception when check_violation then null;
    end;
  end loop;
  -- Baskasinin adini alamaz
  begin
    update public.profiller set kullanici_adi = 'ayse'
     where id = '44444444-4444-4444-8444-444444444444';
    raise exception 'BASARISIZ: baskasinin adi alindi';
  exception when unique_violation then null;
  end;
  raise notice 'gecti: bicim ve tekillik tutuyor';
end $$;

\echo '--- 19. profil yorumlari: yalniz onayli, kapali profil hic donmuyor'
reset role; set role anon;
do $$
declare n int; o record;
begin
  -- ayse'nin ONAYLI iki yorumu var (node/70 ve node/74); node/72'yi
  -- 16. adimda kendisi sildi. Sayiyi degil, HANGILERI oldugunu da
  -- dogruluyoruz: yalniz sayiya bakmak, yanlis yorumlarin donmesini
  -- gormezdi.
  select count(*) into n from public.profil_yorumlari('ayse');
  if n <> 2 then raise exception 'BASARISIZ: ayse icin % yorum, 2 olmaliydi', n; end if;
  if exists (select 1 from public.profil_yorumlari('ayse')
              where mekan_id not in ('node/70','node/74')) then
    raise exception 'BASARISIZ: beklenmeyen mekan dondu';
  end if;
  -- En yeni once: profil sayfasi bu sirayla ciziyor.
  select * into o from public.profil_yorumlari('ayse') limit 1;
  if o.mekan_id is distinct from 'node/74' then
    raise exception 'BASARISIZ: siralama yanlis, ilk sirada %', o.mekan_id;
  end if;
  -- Profilini kapatanin yorumlari da donmuyor: profil sayfasi zaten acilmiyor.
  select count(*) into n from public.profil_yorumlari('gizli_kisi');
  if n <> 0 then raise exception 'BASARISIZ: kapali profilin yorumlari dondu'; end if;
  raise notice 'gecti: 2 onayli yorum, en yeni once, kapali profil bos';
end $$;

\echo '--- 20. profilde FIS listelenmiyor'
-- Fisler kani degil ODEME KAYDI: "su gun, su mekanda, su kadar, su kadar
-- kisiyle". Kisiye gore dizilince bir kisinin disari cikma ve harcama
-- gecmisi olur; sema.sql "Sutun yetkisi" tam olarak bunu kapatti.
do $$
declare n int;
begin
  select count(*) into n
    from information_schema.columns
   where table_schema = 'public' and table_name = 'profil_yorumlari'
     and column_name in ('tutar','kisi');
  if n > 0 then raise exception 'BASARISIZ: profil yorumlarinda fis alani var'; end if;
  -- Kisiye gore fis listeleyen bir fonksiyon HIC olmamali.
  if exists (select 1 from pg_proc pr
               join pg_namespace ns on ns.oid = pr.pronamespace
              where ns.nspname = 'public'
                and pr.proname in ('profil_paylasimlari','kullanici_paylasimlari',
                                   'profil_fisleri')) then
    raise exception 'BASARISIZ: kisiye gore fis listeleyen fonksiyon eklenmis';
  end if;
  raise notice 'gecti: fis kisiye gore listelenmiyor';
end $$;
reset role;

\echo '=== yorum: 20 kontrolun hepsi gecti ==='
