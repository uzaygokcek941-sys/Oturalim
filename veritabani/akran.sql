-- ============================================================
-- Cebimde — bütçe akranları ve civar fişi
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir. sema.sql'den SONRA.
--
-- NEDEN VAR: fiş katmanı tek bir mekanın sorusunu cevaplıyor ("burası kaça
-- oturur"). Ağ mekaniği bunun bir üstü: "benim bütçemdeki insanlar nereye
-- gidiyor" ve "bu civarda ne oluyor". İkisi de TEK KİŞİYİ değil TOPLAMI
-- gösteriyor -- fiş katmanının k-anonimlik eşiği burada da geçerli.
--
-- NEDEN SUNUCUDA: iki sayının ikisi de tarayıcıda hesaplanamıyor, çünkü
-- ikisi de `kullanici` sütununa bakıyor ve o sütun anon/authenticated'a
-- KAPALI (sema.sql "Sütun yetkisi"). Tarayıcı aynı kişinin iki mekandaki
-- iki fişini tek kişi sayamaz; sayabilseydi zaten kişiyi takip edebiliyor
-- olurdu. Sayım burada, kimlik dışarı çıkmadan.
--
-- COĞRAFYA BURADA DEĞİL: paylasimlar tablosunda koordinat yok, mekan_id
-- var. Mekanların koordinatı uygulamanın statik JSON'unda duruyor. Bu
-- yüzden "civar" kararını istemci veriyor (hangi mekanlar yakın), toplamı
-- sunucu veriyor (o mekanlarda kaç fiş, kaç kişi). Koordinatı buraya
-- kopyalamak, aynı gerçeği iki yerde tutmak olurdu.
-- ============================================================

-- ============================================================
-- Bütçe akranları
--
-- "Bütçesi seninkine benzeyen kaç kişi, kaç mekanda fiş bıraktı."
--
-- SON 180 GÜN: fiyat eskiyor. Bir yıl önceki fişten "bütçendeki insanlar
-- buraya gidiyor" demek, kullanıcının doğrulayamayacağı bir iddia olurdu.
-- (Aynı gerekçe ortak.js FIYAT_TAZE_AY'da yazılı; orada 6 ay, burada da 6.)
--
-- TAVAN KİŞİ BAŞI: paylaşım "3 kişi gittik 850 verdik" diyor, bütçe
-- kaydırıcısı ise tek kişinin cebini soruyor. tutar/kisi karşılaştırılıyor.
--
-- Eşik BURADA DEĞİL, istemcide (AKRAN_ESIK): fonksiyon ham sayıyı veriyor.
-- mekan_fis_ozeti ve mekan_puani ile aynı kural -- "gösterilsin mi" kararı
-- tek yerde dursun.
-- ============================================================
create or replace function public.butce_akranlari(p_il text, p_tavan numeric)
returns table (akran int, fis int, mekan int)
language sql
stable
security definer
set search_path = public
as $$
  with son as (
    select kullanici, mekan_id
    from public.paylasimlar
    where durum = 'onaylandi'
      and (p_il is null or il = p_il)
      and tarih >= current_date - interval '180 days'
      -- Tavan geçersizse (0, negatif, null) hiçbir satır seçilmiyor:
      -- "bütçe girilmemiş" ile "bütçesi sıfır olan akranlar" aynı şey değil.
      and p_tavan is not null and p_tavan > 0
      and tutar / greatest(kisi, 1) <= p_tavan
    limit 5000
  )
  select count(distinct kullanici)::int,
         count(*)::int,
         count(distinct mekan_id)::int
  from son;
$$;
revoke all on function public.butce_akranlari(text, numeric) from public;
grant execute on function public.butce_akranlari(text, numeric) to anon, authenticated;

comment on function public.butce_akranlari is
  'Butcesi p_tavan altinda kalan kac kisi kac mekanda fis birakti. Kimlik dismiyor.';

-- ============================================================
-- Civar fişi — bir mekan listesinin toplamı
--
-- Hangi mekanların "civar" olduğuna istemci karar veriyor (koordinat
-- orada). Burada yalnız toplam alınıyor.
--
-- DİZİ SINIRI SESSİZ DEĞİL: 500'den uzun liste kesilmiyor, HATA veriyor.
-- Sessizce kırpmak, istemcinin "500 m çevresi" dediği şeyin aslında
-- "500 m çevresinin bir kısmı" olması demekti -- ekranda yazan yarıçap
-- yalan olurdu. İstemci yarıçapı daraltıp tekrar soruyor ve DARALTILMIŞ
-- yarıçapı yazıyor (ortak.js mahalleOzeti).
-- ============================================================
create or replace function public.civar_fis_ozeti(p_mekan_idler text[])
returns table (fis int, kisi int, mekan int, medyan numeric)
language plpgsql
stable
security definer
set search_path = public
as $$
begin
  if p_mekan_idler is null or array_length(p_mekan_idler, 1) is null then
    return query select 0, 0, 0, null::numeric;
    return;
  end if;
  if array_length(p_mekan_idler, 1) > 500 then
    raise exception 'civar listesi cok uzun (% > 500)', array_length(p_mekan_idler, 1)
      using errcode = 'program_limit_exceeded';
  end if;
  return query
    with son as (
      select p.tutar, p.kisi, p.kullanici, p.mekan_id
      from public.paylasimlar p
      where p.mekan_id = any(p_mekan_idler)
        and p.durum = 'onaylandi'
        and p.tarih >= current_date - interval '180 days'
      order by p.tarih desc
      limit 2000
    )
    select count(*)::int,
           count(distinct son.kullanici)::int,
           count(distinct son.mekan_id)::int,
           -- Esik BURADA DA sunucuda. Civar daha genis bir kume oldugu
           -- icin esigi gevsetmek cazip; gevsetilmiyor, cunku tek fisli
           -- bir civar da tek kisidir (isletme.html'deki yorumla ayni
           -- gerekce, artik iki tarafta birden).
           case when count(*) >= 3
                then round(percentile_cont(0.5) within group
                           (order by son.tutar / greatest(son.kisi, 1)))::numeric
           end
    from son;
end;
$$;
revoke all on function public.civar_fis_ozeti(text[]) from public;
grant execute on function public.civar_fis_ozeti(text[]) to anon, authenticated;

comment on function public.civar_fis_ozeti is
  'Verilen mekan listesinin fis toplami. Cografya istemcide, kimlik disari cikmiyor.';

-- ============================================================
-- Kendini kontrol
-- ============================================================
do $$
declare
  n int;
begin
  if not exists (select 1 from pg_tables where schemaname = 'public'
                 and tablename = 'paylasimlar') then
    raise exception 'Once sema.sql calistirilmali: paylasimlar tablosu yok';
  end if;

  -- Fonksiyonlar gercekten cagrilabiliyor mu. "var mi" diye pg_proc'a
  -- bakmak yetmiyor: yetki verilmemis bir fonksiyon da orada gorunur.
  if not has_function_privilege('anon', 'public.butce_akranlari(text, numeric)', 'EXECUTE') then
    raise exception 'anon butce_akranlari cagiramiyor';
  end if;
  if not has_function_privilege('anon', 'public.civar_fis_ozeti(text[])', 'EXECUTE') then
    raise exception 'anon civar_fis_ozeti cagiramiyor';
  end if;

  -- Cikti sutunlarinda kimlik OLMAMALI. Bu kontrol pg_proc.proargnames'e
  -- bakiyor; information_schema.columns'a bakan bir surumu vardi ve
  -- BOSA KOSUYORDU -- orada fonksiyon yok, sorgu hep sifir donuyordu.
  select count(*) into n
    from pg_proc, unnest(coalesce(proargnames, '{}')) as ad
   where proname in ('butce_akranlari','civar_fis_ozeti')
     and pronamespace = 'public'::regnamespace
     and ad in ('kullanici','uuid','kimlik');
  if n > 0 then
    raise exception 'akran fonksiyonlari kimlik sutunu donduruyor (%)', n;
  end if;

  -- Kontrolun kendisi bir sey goruyor mu: yukaridaki sorgu hicbir satir
  -- gormeseydi de 0 donerdi ve "gecti" derdi.
  select count(*) into n
    from pg_proc, unnest(coalesce(proargnames, '{}')) as ad
   where proname in ('butce_akranlari','civar_fis_ozeti')
     and pronamespace = 'public'::regnamespace;
  if n = 0 then
    raise exception 'kimlik sutunu kontrolu hicbir argumani gormedi';
  end if;

  raise notice 'Akran kuruldu: iki fonksiyon, % arguman adi tarandi', n;
end;
$$;
