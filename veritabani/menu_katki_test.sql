-- ============================================================
-- Cebimde — menü katkısı davranış testi (gerçek Postgres'te)
--
-- Bu dosya kurulum SQL'i DEGIL. Supabase'e yapistirma.
-- Kosumu: sh veritabani/kos.sh  (test.py ve CI onu cagiriyor)
-- ============================================================
\set ON_ERROR_STOP on
\pset pager off
truncate public.menu_katkilari restart identity cascade;

reset role;
insert into auth.users (id) values
  ('55555555-5555-4555-8555-555555555555') on conflict do nothing;
insert into public.profiller (id, kullanici_adi)
  values ('55555555-5555-4555-8555-555555555555', public.kullanici_adi_uret())
  on conflict (id) do nothing;

\echo '--- 1. kalem ONAYSIZ yayina girmiyor'
set role authenticated;
set request.jwt.claim.sub = '55555555-5555-4555-8555-555555555555';
do $$
declare d text; n int;
begin
  insert into public.menu_katkilari (kullanici, mekan_id, il, mekan_ad, urun, fiyat)
  values (auth.uid(), 'node/90', '06', 'Menu Kafe', 'Latte', 95);
  select durum into d from public.menu_katkilari where mekan_id = 'node/90';
  if d <> 'bekliyor' then raise exception 'BASARISIZ: durum %', d; end if;
  select count(*) into n from public.mekan_menu_katkilari('node/90');
  if n <> 0 then raise exception 'BASARISIZ: onaysiz kalem yayinda'; end if;
  raise notice 'gecti: kuyrukta bekliyor, yayinda yok';
end $$;

\echo '--- 2. kullanici durumu KENDI belirleyemiyor'
do $$
begin
  begin
    insert into public.menu_katkilari (kullanici, mekan_id, il, mekan_ad, urun, fiyat, durum)
    values (auth.uid(), 'node/91', '06', 'Kacak Kafe', 'Cay', 20, 'onaylandi');
    raise exception 'BASARISIZ: kullanici kendi kalemini onayladi';
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: politika reddetti';
end $$;

\echo '--- 3. YALNIZ fotograf gecerli bir kayit (menuyu tek tek yazmak sart degil)'
-- Menunun tamamini fotograflayan biri 20 kalemi elle yazmak zorunda kalmasin.
do $$
declare n int;
begin
  insert into public.menu_katkilari (kullanici, mekan_id, il, mekan_ad, foto)
  values (auth.uid(), 'node/92', '06', 'Foto Kafe',
          '55555555-5555-4555-8555-555555555555/1.jpg');
  select count(*) into n from public.menu_katkilari where mekan_id = 'node/92';
  if n <> 1 then raise exception 'BASARISIZ: fotografli kayit kabul edilmedi'; end if;
  raise notice 'gecti: fotograf tek basina yeterli';
end $$;

\echo '--- 4. BOS kayit ve YARIM kalem reddediliyor'
-- Adi olup fiyati olmayan kalem bir sey soylemiyor; ikisi de yoksa
-- kayit tamamen bos.
do $$
declare kotu text;
begin
  -- hicbiri yok
  begin
    insert into public.menu_katkilari (kullanici, mekan_id, il, mekan_ad)
    values (auth.uid(), 'node/93', '06', 'Bos Kafe');
    raise exception 'BASARISIZ: bos kayit kabul edildi';
  exception when check_violation then null;
  end;
  -- yalniz ad
  begin
    insert into public.menu_katkilari (kullanici, mekan_id, il, mekan_ad, urun)
    values (auth.uid(), 'node/93', '06', 'Bos Kafe', 'Latte');
    raise exception 'BASARISIZ: fiyatsiz kalem kabul edildi';
  exception when check_violation then null;
  end;
  -- yalniz fiyat
  begin
    insert into public.menu_katkilari (kullanici, mekan_id, il, mekan_ad, fiyat)
    values (auth.uid(), 'node/93', '06', 'Bos Kafe', 95);
    raise exception 'BASARISIZ: adsiz fiyat kabul edildi';
  exception when check_violation then null;
  end;
  raise notice 'gecti: bos ve yarim kayit reddediliyor';
end $$;

\echo '--- 5. fiyat sinirlari'
do $$
declare kotu numeric;
begin
  foreach kotu in array array[0, -5, 100001] loop
    begin
      insert into public.menu_katkilari (kullanici, mekan_id, il, mekan_ad, urun, fiyat)
      values (auth.uid(), 'node/94', '06', 'X Kafe', 'Urun' || kotu::text, kotu);
      raise exception 'BASARISIZ: fiyat % kabul edildi', kotu;
    exception when check_violation then null;
    end;
  end loop;
  raise notice 'gecti: sifir, negatif ve 100.000 ustu reddediliyor';
end $$;

\echo '--- 6. ayni urun icin IKINCI bekleyen kayit acilamiyor'
do $$
begin
  begin
    insert into public.menu_katkilari (kullanici, mekan_id, il, mekan_ad, urun, fiyat)
    values (auth.uid(), 'node/90', '06', 'Menu Kafe', 'Latte', 110);
    raise exception 'BASARISIZ: ayni urun icin iki bekleyen kayit acildi';
  exception when unique_violation then null;
  end;
  raise notice 'gecti: kuyruk tekil';
end $$;

\echo '--- 7. ama FARKLI urun icin acilabiliyor'
-- Bir menude cok kalem var; tekil kisit kuyrugu korumali, katkiyi degil.
do $$
declare n int;
begin
  insert into public.menu_katkilari (kullanici, mekan_id, il, mekan_ad, urun, fiyat)
  values (auth.uid(), 'node/90', '06', 'Menu Kafe', 'Filtre kahve', 70);
  select count(*) into n from public.menu_katkilari where mekan_id = 'node/90';
  if n <> 2 then raise exception 'BASARISIZ: % kayit, 2 olmaliydi', n; end if;
  raise notice 'gecti: ayni mekana farkli kalem eklenebiliyor';
end $$;

\echo '--- 8. onaylandiginda yayina giriyor'
reset role;
update public.menu_katkilari set durum = 'onaylandi' where mekan_id = 'node/90';
set role anon;
do $$
declare n int; o record;
begin
  select count(*) into n from public.mekan_menu_katkilari('node/90');
  if n <> 2 then raise exception 'BASARISIZ: % kalem gorunuyor', n; end if;
  select * into o from public.mekan_menu_katkilari('node/90') where urun = 'Latte';
  if o.fiyat <> 95 then raise exception 'BASARISIZ: fiyat %', o.fiyat; end if;
  raise notice 'gecti: 2 kalem yayinda';
end $$;

\echo '--- 9. anon KIMLIK sutununu okuyamiyor'
-- Bu tablo mekan + fiyat + FOTOGRAF tasiyor; uuid yanina konsa bir kisinin
-- nereye gidip ne fotografladigi tek sorguda toplanirdi.
do $$
begin
  begin
    perform kullanici from public.menu_katkilari limit 1;
    raise exception 'BASARISIZ: anon menu_katkilari.kullanici okudu';
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: kimlik sutunu kapali';
end $$;

\echo '--- 10. yayimlanan kalemde YAZAR bilgisi hic yok'
-- Yorumda "kim soyluyor" bilgi tasir; fiyatta tasimaz. 95 TL, kim
-- yazdiysa 95 TL. Ad eklemek, hicbir soruyu cevaplamadan bir kisiyi bir
-- mekana baglamak olurdu.
do $$
declare adlar text[];
begin
  select proargnames into adlar from pg_proc
   where pronamespace = 'public'::regnamespace
     and proname = 'mekan_menu_katkilari';
  if adlar is null then
    raise exception 'BASARISIZ: mekan_menu_katkilari bulunamadi';
  end if;
  -- Once kontrolun GERCEKTEN bir sey gordugunu dogrula: ilk yazim
  -- information_schema.columns'a bakiyordu, fonksiyon oraya girmedigi
  -- icin her zaman sifir donuyor ve kontrol bos calisiyordu.
  if not ('urun' = any(adlar)) then
    raise exception 'BASARISIZ: kontrol bos calisiyor, cikis sutunlari okunamadi';
  end if;
  if exists (select 1 from unnest(adlar) a where a like 'yazar%' or a = 'kullanici') then
    raise exception 'BASARISIZ: yayimlanan kalemde yazar alani var (%)', adlar;
  end if;
  raise notice 'gecti: kalem anonim yayimlaniyor (%)', array_length(adlar, 1);
end $$;

\echo '--- 11. kullanici kendi kaydini silebiliyor, baskasininkini silemiyor'
reset role;
insert into public.menu_katkilari (kullanici, mekan_id, il, mekan_ad, urun, fiyat, durum)
values ('33333333-3333-4333-8333-333333333333', 'node/95', '06', 'Baska Kafe',
        'Ayran', 30, 'onaylandi');
set role authenticated;
set request.jwt.claim.sub = '55555555-5555-4555-8555-555555555555';
do $$
declare n int; hedef bigint;
begin
  select id into hedef from public.menu_katkilari where mekan_id = 'node/92';
  delete from public.menu_katkilari where id = hedef;
  get diagnostics n = row_count;
  if n <> 1 then raise exception 'BASARISIZ: kendi kaydini silemedi'; end if;

  select id into hedef from public.menu_katkilari where mekan_id = 'node/95';
  delete from public.menu_katkilari where id = hedef;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'BASARISIZ: baskasinin kaydini sildi'; end if;
  raise notice 'gecti: yalniz kendi kaydini siliyor';
end $$;

\echo '--- 12. fotograf kovasi: guncelleme politikasi OLMAMALI'
-- Onaylanmis bir fotografin uzerine yazilabilseydi, onaydan gecen resim
-- ile yayindaki resim ayri seyler olabilirdi ve onayin tamami
-- anlamsizlasirdi. Degistirmek isteyen siler, yeniden gonderir.
reset role;
do $$
declare n int;
begin
  if not exists (select 1 from information_schema.schemata where schema_name = 'storage') then
    raise notice 'gecti: storage yok, kova kontrolu atlandi (yerel Postgres)';
    return;
  end if;
  select count(*) into n from pg_policies
   where schemaname = 'storage' and tablename = 'objects'
     and cmd = 'UPDATE' and coalesce(qual, '') like '%menu%';
  if n > 0 then
    raise exception 'BASARISIZ: menu kovasinda guncelleme politikasi var';
  end if;
  raise notice 'gecti: uzerine yazma yolu kapali';
end $$;

\echo '=== menu katkisi: 12 kontrolun hepsi gecti ==='
