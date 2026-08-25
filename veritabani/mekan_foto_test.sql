-- ============================================================
-- Cebimde — mekan fotoğrafı davranış testi (gerçek Postgres'te)
--
-- Bu dosya kurulum SQL'i DEGIL. Supabase'e yapistirma.
-- Kosumu: sh veritabani/kos.sh
-- ============================================================
\set ON_ERROR_STOP on
\pset pager off
truncate public.mekan_fotolari restart identity cascade;
truncate public.sahiplik restart identity cascade;

reset role;
insert into auth.users (id) values
  ('66666666-6666-4666-8666-666666666666') on conflict do nothing;
insert into public.profiller (id, kullanici_adi)
  values ('66666666-6666-4666-8666-666666666666', public.kullanici_adi_uret())
  on conflict (id) do nothing;

\echo '--- 1. kullanicinin fotografi ONAYSIZ yayina girmiyor'
set role authenticated;
set request.jwt.claim.sub = '66666666-6666-4666-8666-666666666666';
do $$
declare d text; n int;
begin
  insert into public.mekan_fotolari (kullanici, mekan_id, il, mekan_ad, yol, aciklama)
  values (auth.uid(), 'node/100', '06', 'Foto Kafe',
          '66666666-6666-4666-8666-666666666666/1.jpg', 'Bahce');
  select durum into d from public.mekan_fotolari where mekan_id = 'node/100';
  if d <> 'bekliyor' then raise exception 'BASARISIZ: durum %', d; end if;
  select count(*) into n from public.mekan_fotograflari('node/100');
  if n <> 0 then raise exception 'BASARISIZ: onaysiz fotograf yayinda'; end if;
  raise notice 'gecti: kuyrukta bekliyor';
end $$;

\echo '--- 2. kullanici durumu KENDI belirleyemiyor'
do $$
begin
  begin
    insert into public.mekan_fotolari (kullanici, mekan_id, il, mekan_ad, yol, durum)
    values (auth.uid(), 'node/101', '06', 'Kacak Kafe',
            '66666666-6666-4666-8666-666666666666/2.jpg', 'onaylandi');
    raise exception 'BASARISIZ: kullanici kendi fotografini onayladi';
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: politika reddetti';
end $$;

\echo '--- 3. kullanici kaynagi COMMONS diye giremiyor'
-- kaynak serbest metin olsaydi, kullanici kendi fotografini "Commons'tan
-- geldi" diye isaretleyip atif alanlarini uydurabilirdi.
do $$
begin
  begin
    insert into public.mekan_fotolari (kullanici, mekan_id, il, mekan_ad, adres,
                                       kaynak, yazar, lisans, kaynak_bag)
    values (auth.uid(), 'node/102', '06', 'Sahte Kafe',
            'https://upload.wikimedia.org/x.jpg', 'commons',
            'Uydurma', 'CC BY-SA 4.0', 'https://commons.wikimedia.org/x');
    raise exception 'BASARISIZ: kullanici commons kaynagi ile yazdi';
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: commons yalniz sunucudan girer';
end $$;

\echo '--- 4. ISLETME SAHIBININ fotografi dogrudan yayinda'
-- Sahiplik sahada, elden verilen kodla kazaniliyor; kendi mekaninin
-- fotografini yukleyen sahibi kuyrukta bekletmenin karsiligi yok.
reset role;
insert into public.sahiplik (kullanici, mekan_id, il, mekan_ad)
values ('66666666-6666-4666-8666-666666666666', 'node/103', '06', 'Sahipli Kafe');
set role authenticated;
set request.jwt.claim.sub = '66666666-6666-4666-8666-666666666666';
do $$
declare d text; k text; n int;
begin
  insert into public.mekan_fotolari (kullanici, mekan_id, il, mekan_ad, yol)
  values (auth.uid(), 'node/103', '06', 'Sahipli Kafe',
          '66666666-6666-4666-8666-666666666666/3.jpg');
  select durum, kaynak into d, k from public.mekan_fotolari where mekan_id = 'node/103';
  if d <> 'onaylandi' then raise exception 'BASARISIZ: sahibin fotografi % ', d; end if;
  if k <> 'sahip' then raise exception 'BASARISIZ: kaynak %', k; end if;
  select count(*) into n from public.mekan_fotograflari('node/103');
  if n <> 1 then raise exception 'BASARISIZ: yayinda % fotograf', n; end if;
  raise notice 'gecti: sahibin fotografi dogrudan yayinda';
end $$;

\echo '--- 5. SAHIBI OLMADIGI mekana onayli fotograf yazamiyor'
do $$
begin
  begin
    insert into public.mekan_fotolari (kullanici, mekan_id, il, mekan_ad, yol, durum)
    values (auth.uid(), 'node/104', '06', 'Yabanci Kafe',
            '66666666-6666-4666-8666-666666666666/4.jpg', 'onaylandi');
    raise exception 'BASARISIZ: sahibi olmadan onayli fotograf yazildi';
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: politika reddetti';
end $$;

\echo '--- 6. COMMONS fotografi ATIFSIZ giremez'
-- CC BY / CC BY-SA yazar adini ve lisansi gostermeyi ZORUNLU kiliyor;
-- atifsiz kullanim lisansi ihlal eder. Kisit veritabaninda, cunku bunu
-- unutmak kolay ve sonucu hukuki.
reset role;
do $$
declare eksik text;
begin
  foreach eksik in array array['yazar','lisans','bag'] loop
    begin
      insert into public.mekan_fotolari (mekan_id, il, mekan_ad, adres, kaynak,
                                         yazar, lisans, kaynak_bag, durum)
      values ('node/105', '06', 'Commons Kafe',
              'https://upload.wikimedia.org/' || eksik || '.jpg', 'commons',
              case when eksik = 'yazar'  then null else 'Bir Fotografci' end,
              case when eksik = 'lisans' then null else 'CC BY-SA 4.0' end,
              case when eksik = 'bag'    then null else 'https://commons.wikimedia.org/wiki/File:x' end,
              'onaylandi');
      raise exception 'BASARISIZ: % olmadan commons fotografi girdi', eksik;
    exception when check_violation then null;
    end;
  end loop;
  raise notice 'gecti: atif zorunlu';
end $$;

\echo '--- 7. atifi TAM commons fotografi giriyor ve atif YAYINA cikiyor'
do $$
declare o record;
begin
  insert into public.mekan_fotolari (mekan_id, il, mekan_ad, adres, kaynak,
                                     yazar, lisans, kaynak_bag, durum)
  values ('node/105', '06', 'Commons Kafe',
          'https://upload.wikimedia.org/wikipedia/commons/a/ab/Kafe.jpg', 'commons',
          'Bir Fotografci', 'CC BY-SA 4.0',
          'https://commons.wikimedia.org/wiki/File:Kafe.jpg', 'onaylandi');
  select * into o from public.mekan_fotograflari('node/105');
  if o.yazar is null or o.lisans is null or o.kaynak_bag is null then
    raise exception 'BASARISIZ: atif yayina cikmiyor';
  end if;
  raise notice 'gecti: % / %', o.yazar, o.lisans;
end $$;

\echo '--- 8. ayni adres IKINCI kez girmiyor (foto_cek.py tekrar kosabilmeli)'
do $$
begin
  begin
    insert into public.mekan_fotolari (mekan_id, il, mekan_ad, adres, kaynak,
                                       yazar, lisans, kaynak_bag, durum)
    values ('node/105', '06', 'Commons Kafe',
            'https://upload.wikimedia.org/wikipedia/commons/a/ab/Kafe.jpg', 'commons',
            'Bir Fotografci', 'CC BY-SA 4.0',
            'https://commons.wikimedia.org/wiki/File:Kafe.jpg', 'onaylandi');
    raise exception 'BASARISIZ: ayni adres iki kez girdi';
  exception when unique_violation then null;
  end;
  raise notice 'gecti: tekrar kosum kopya uretmiyor';
end $$;

\echo '--- 9. dosya YA DA adres, ikisi birden olmaz'
do $$
begin
  begin
    insert into public.mekan_fotolari (mekan_id, il, mekan_ad, yol, adres, durum)
    values ('node/106', '06', 'Ikili Kafe', 'a/b.jpg',
            'https://ornek.test/x.jpg', 'onaylandi');
    raise exception 'BASARISIZ: yol ve adres birlikte girdi';
  exception when check_violation then null;
  end;
  begin
    insert into public.mekan_fotolari (mekan_id, il, mekan_ad, durum)
    values ('node/106', '06', 'Bos Kafe', 'onaylandi');
    raise exception 'BASARISIZ: yolsuz ve adressiz kayit girdi';
  exception when check_violation then null;
  end;
  raise notice 'gecti: tam olarak biri dolu olmali';
end $$;

\echo '--- 10. SIRA: once sahip, sonra kullanici, sonra commons'
-- Sahibin fotografi mekani en iyi temsil eden ve yayimlama hakki en net
-- olandir; ilk sirada durmali.
do $$
declare ilk text;
begin
  insert into public.mekan_fotolari (kullanici, mekan_id, il, mekan_ad, yol, kaynak, durum)
  values ('66666666-6666-4666-8666-666666666666', 'node/103', '06', 'Sahipli Kafe',
          '66666666-6666-4666-8666-666666666666/9.jpg', 'kullanici', 'onaylandi');
  insert into public.mekan_fotolari (mekan_id, il, mekan_ad, adres, kaynak,
                                     yazar, lisans, kaynak_bag, durum)
  values ('node/103', '06', 'Sahipli Kafe',
          'https://upload.wikimedia.org/wikipedia/commons/c/cd/S.jpg', 'commons',
          'X', 'CC BY 4.0', 'https://commons.wikimedia.org/wiki/File:S.jpg', 'onaylandi');
  select kaynak into ilk from public.mekan_fotograflari('node/103') limit 1;
  if ilk <> 'sahip' then raise exception 'BASARISIZ: ilk sirada %', ilk; end if;
  raise notice 'gecti: sahip once';
end $$;

\echo '--- 11. anon KIMLIK sutununu okuyamiyor'
set role anon;
do $$
begin
  begin
    perform kullanici from public.mekan_fotolari limit 1;
    raise exception 'BASARISIZ: anon mekan_fotolari.kullanici okudu';
  exception when insufficient_privilege then null;
  end;
  raise notice 'gecti: kimlik sutunu kapali';
end $$;

\echo '--- 12. kaynak listesi KAPALI (Google Maps vb. giremez)'
-- Serbest metin olsaydi yayimlama hakki olmayan bir kaynak sessizce
-- eklenebilirdi. CEBIMDE.md "Yapilmayacaklar" listesindeki karar.
reset role;
do $$
begin
  begin
    insert into public.mekan_fotolari (mekan_id, il, mekan_ad, adres, kaynak, durum)
    values ('node/107', '06', 'X', 'https://ornek.test/y.jpg', 'google', 'onaylandi');
    raise exception 'BASARISIZ: bilinmeyen kaynak kabul edildi';
  exception when check_violation then null;
  end;
  raise notice 'gecti: kaynak listesi kapali';
end $$;

\echo '=== mekan fotografi: 12 kontrolun hepsi gecti ==='
