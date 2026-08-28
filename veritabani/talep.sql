-- ============================================================
-- Cebimde — talep açığı ve fiyat endeksi (FIKIRLER.md F3, F4)
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir. ÖNCE sema.sql ve sayac.sql çalıştırılmış olmalı.
--
-- NEDEN VAR. Bu iki fonksiyon, uygulamanın **kimsenin üretemediği** iki
-- sayısını mekan düzeyinden BÖLGE düzeyine çıkarıyor:
--
--   1. TALEP AÇIĞI. "Bu civara bakanların %62'si 250 ₺ altı arıyordu;
--      menüsü bilinen mekanların medyanı 340 ₺." Google ve Yemeksepeti
--      fiyatı biliyor ama ARAYANIN BÜTÇESİNİ yayınlamıyor -- o veri
--      onların reklam ürünü. Cebimde'de bütçe zaten ürünün girdisi.
--
--   2. FİYAT ENDEKSİ. Kullanıcıların paylaştığı fişlerden ay ay kişi
--      başı medyan. RESMÎ BİR ENDEKS DEĞİL ve arayüz bunu her yerde
--      yazmak zorunda; burada üretilen şey "Cebimde kullanıcılarının
--      paylaştığı fişlerin medyanı", başka bir şey değil.
--
-- COĞRAFYA İSTEMCİDE. İkisi de mekan kimliği LİSTESİ alıyor, "ilçe"
-- almıyor. Sebep: ilçe bilgisi il dosyalarında (statik JSON), veritabanı
-- hangi mekanın Çankaya'da olduğunu bilmiyor. Aynı desen
-- civar_fis_ozeti'nde de var ve orada da aynı gerekçeyle seçilmişti.
--
-- EŞİK SUNUCUDA, ikisinde de. İstemci eşiği gevşetemiyor; gevşetebilseydi
-- eşik diye bir şey olmazdı.
-- ============================================================

-- ---------- 1. Talep açığı ----------
-- Verilen mekan listesine son 30 günde bakanların bütçe bandı dağılımı.
--
-- EŞİK 5 VE mekan_butce_talebi İLE AYNI SAYI, bilerek. Buradaki küme
-- daha geniş olduğu için eşiği gevşetmek cazip görünüyor -- gevşetilmiyor,
-- çünkü korunan şey kümenin büyüklüğü değil TEK KİŞİNİN bütçesi. Tek
-- mekanlı bir "civar" ile tek mekanın kendisi arasında fark yok.
--
-- HAM SATIR DÖNMÜYOR: yalnız bant ve sayı. Hangi cihazın hangi bandı
-- aradığı bu fonksiyondan çıkmıyor.
create or replace function public.civar_talep_ozeti(p_mekan_idler text[])
returns table (bant smallint, kisi int)
language plpgsql
security definer
stable
set search_path = public
as $$
begin
  if p_mekan_idler is null or array_length(p_mekan_idler, 1) is null then
    return;
  end if;
  -- SESSIZCE KIRPMIYOR, hata veriyor. Kirpilmis bir liste, kullanicinin
  -- gordugu haritayla ayrisan bir sayi uretir ve bunu kimse fark etmez.
  -- Ayni sinir ve ayni gerekce civar_fis_ozeti'nde de var.
  if array_length(p_mekan_idler, 1) > 500 then
    raise exception 'civar listesi cok uzun (% > 500)',
      array_length(p_mekan_idler, 1)
      using errcode = 'program_limit_exceeded';
  end if;
  return query
    with son as (
      select g.butce_bandi
      from public.goruntulenme g
      where g.mekan_id = any(p_mekan_idler)
        and g.gun > current_date - 30
    )
    select s.butce_bandi, count(*)::int
    from son s
    where s.butce_bandi is not null
      and (select count(*) from son) >= 5
    group by s.butce_bandi
    order by s.butce_bandi;
end;
$$;

revoke all on function public.civar_talep_ozeti(text[]) from public;
grant execute on function public.civar_talep_ozeti(text[]) to anon, authenticated;

comment on function public.civar_talep_ozeti is
  'Verilen mekan listesine bakanlarin butce bandi dagilimi. 5 bakisin '
  'altinda hic donmez (k-anonimlik). Cografya istemcide.';

-- ---------- 2. Fiyat endeksi ----------
-- Verilen mekan listesinin AY AY kişi başı medyanı, onaylanmış fişlerden.
--
-- AYLIK EŞİK 3 VE FIS_ESIK İLE AYNI SAYI. Üç fişten az olan ay HİÇ
-- dönmüyor -- tek fişin medyanı o kişinin ödediği tutardır, yani
-- "endeks" adı altında tek bir kişinin harcamasını yayınlamak olurdu.
-- Ay atlanıyor, sıfır yazılmıyor: sıfır bir ölçüm gibi okunur.
--
-- KİŞİ SAYISI DA DÖNÜYOR ve dönmesi şart: bir ayın medyanı üç fişten mi
-- üç yüz fişten mi geldiği, sayının kendisi kadar önemli. Arayüz bunu
-- göstermek zorunda, yoksa dayanaksız bir rakam yayınlamış oluruz.
create or replace function public.civar_fiyat_endeksi(
  p_mekan_idler text[], p_ay int default 6)
returns table (ay date, fis int, kisi int, medyan numeric)
language plpgsql
security definer
stable
set search_path = public
as $$
declare
  n int := greatest(1, least(coalesce(p_ay, 6), 24));
begin
  if p_mekan_idler is null or array_length(p_mekan_idler, 1) is null then
    return;
  end if;
  if array_length(p_mekan_idler, 1) > 500 then
    raise exception 'civar listesi cok uzun (% > 500)',
      array_length(p_mekan_idler, 1)
      using errcode = 'program_limit_exceeded';
  end if;
  return query
    with son as (
      select date_trunc('month', p.tarih)::date as ay,
             -- KISI BASI. Fisin tutari masadaki herkesi kapsiyor;
             -- boluunmezse kalabalik masa pahali mekan gibi gorunur.
             -- Ayni bolme civar_fis_ozeti'nde de yapiliyor.
             (p.tutar / greatest(p.kisi, 1))::numeric as kisi_basi,
             p.kullanici
      from public.paylasimlar p
      where p.mekan_id = any(p_mekan_idler)
        and p.durum = 'onaylandi'
        and p.tarih >= (date_trunc('month', current_date)
                        - make_interval(months => n - 1))::date
    )
    select s.ay,
           count(*)::int,
           count(distinct s.kullanici)::int,
           round(percentile_cont(0.5) within group (order by s.kisi_basi)::numeric, 0)
    from son s
    group by s.ay
    having count(*) >= 3
    order by s.ay;
end;
$$;

revoke all on function public.civar_fiyat_endeksi(text[], int) from public;
grant execute on function public.civar_fiyat_endeksi(text[], int)
  to anon, authenticated;

comment on function public.civar_fiyat_endeksi is
  'Verilen mekan listesinin ay ay kisi basi medyani. Uc fisten az olan ay '
  'HIC donmez. Resmi bir endeks DEGIL: Cebimde kullanicilarinin fisleri.';

-- ============================================================
-- Kendini kontrol — bu blok hata vermeden geçmeli
-- ============================================================
do $$
declare
  n int;
begin
  if not exists (select 1 from pg_tables where schemaname = 'public'
                 and tablename = 'goruntulenme') then
    raise exception 'Once sayac.sql calistirilmali: goruntulenme tablosu yok';
  end if;
  if not exists (select 1 from information_schema.columns
                  where table_schema = 'public' and table_name = 'goruntulenme'
                    and column_name = 'butce_bandi') then
    raise exception 'goruntulenme.butce_bandi yok: sayac.sql guncel degil';
  end if;
  if not exists (select 1 from pg_tables where schemaname = 'public'
                 and tablename = 'paylasimlar') then
    raise exception 'Once sema.sql calistirilmali: paylasimlar tablosu yok';
  end if;

  -- Ham tablolar HALA kapali olmali: bu dosya iki toplayici ekliyor,
  -- bir okuma yolu acmiyor.
  select count(*) into n from pg_policies
   where schemaname = 'public' and tablename = 'goruntulenme';
  if n > 0 then
    raise exception 'goruntulenme uzerinde % politika var, olmamali', n;
  end if;
  if has_table_privilege('anon', 'public.goruntulenme', 'select') then
    raise exception 'anon goruntulenme tablosunu okuyabiliyor';
  end if;

  raise notice 'Talep ve endeks kuruldu: iki toplayici, esikler sunucuda';
end;
$$;
