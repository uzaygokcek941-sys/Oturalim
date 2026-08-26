-- ============================================================
-- Topluluk akışı — marka maketindeki "Topluluğa Katıl" ekranı
--
-- NE OLDUĞU: son onaylanan katkıların tek akışı. Uygulamada bu katkılar
-- zaten yayında; akış yeni bir şey AÇMIYOR, dağınık duranı bir araya
-- getiriyor. Tek yeni şey görünürlük: bir mekana bakmadan da topluluğun
-- ne yaptığı görülüyor.
--
-- ------------------------------------------------------------
-- MAKETTEKİ AKIŞ KALEMİNİN BİR TANESİ BİLEREK YAPILMADI
--
-- Maketin merkezindeki kart şunu diyor:
--
--     Ahmet R. — "Latte hâlâ ₺145 ✅"
--
-- Bu, fiyat oyu (fiyat_oylari). O tablonun kuralı ise şu: kimse
-- BAŞKASININ oyunu göremiyor. veritabani/fiyat_oyu_test.sql'in 10. ve
-- 10b. adımları tam olarak bunu ölçüyor ("gecti: oy satirlari disariya
-- kapali", "gecti: herkes yalniz kendi oyunu goruyor") ve fiyat oyu
-- dışarıya YALNIZ eşik üstü toplam olarak veriliyor (fiyat_oy_ozeti,
-- OY_ESIK = 3).
--
-- "Ahmet R. şu fiyatın hâlâ geçerli olduğunu söyledi" cümlesi o kuralı
-- kırar: bir kişinin tek tek oyunu adıyla yayımlar. Maket bir çizim,
-- kural ise ölçülmüş bir karar -- akış kuralın tarafında duruyor.
--
-- ------------------------------------------------------------
-- KİM GÖRÜNÜYOR
--
-- YORUM: yazarıyla. Onaylı bir yorum zaten mekan sayfasında ve profil
-- sayfasında yazarın adıyla duruyor; akışta da öyle duruyor. Profilini
-- kapatan kullanıcının adı DÖNMÜYOR (mekan_yorumlari ile aynı kural).
--
-- MENÜ KATKISI: ADSIZ. Kalem ve fiyat mekan sayfasında zaten yayında
-- ama YAZARSIZ (mekan_menu_katkilari yazar sütunu döndürmüyor). Katkı
-- formu da kullanıcıya "adın yazacak" demiyor. Akışta ada bağlamak,
-- insanların ad görünmeden gönderdiği bir şeyi sonradan adlandırmak
-- olurdu.
--
-- FİŞ (paylasimlar) HİÇ YOK. Onlar kanı değil ÖDEME KAYDI: "şu gün, şu
-- mekanda, şu kadar, şu kadar kişiyle". Kişiye göre dizilince bir kişinin
-- dışarı çıkma ve harcama geçmişi olur. Gerekçe yorum.sql'de
-- profil_yorumlari'nın başında yazılı; burada da geçerli.
--
-- MEKAN FOTOĞRAFI YOK: kaynağı kullanıcı olmayabiliyor (commons, sahip)
-- ve lisans/atıf zinciri mekan sayfasında duruyor. Akışta atıfsız
-- göstermek lisansı ihlal ederdi, atıfla göstermek de akışı fotoğraf
-- künyesine çevirirdi.
--
-- ------------------------------------------------------------
-- SAYFALAMA: "olusturuldu"dan ESKİYE. Sayfa numarası yok çünkü akış
-- büyürken sayfa numarası kayar (yeni kayıt gelince 2. sayfa tekrar
-- eder). İmleç zaman damgası.
-- ============================================================

-- ------------------------------------------------------------
-- ONCE NE KURULMALI
--
-- Akis iki tablodan besleniyor ve ikisi de baska dosyalarda:
--     yorumlar        -> veritabani/yorum.sql   (o da profil.sql'e bagli)
--     menu_katkilari  -> veritabani/menu_katki.sql
--
-- Fonksiyon `language sql` ve govdesi OLUSTURULURKEN dogrulaniyor, yani
-- eksik tablo ham bir hatayla patliyor:
--     ERROR: 42P01: relation "public.yorumlar" does not exist
-- O satir kullaniciya ne yapacagini soylemiyor. Kapi burada, en basta.
-- ------------------------------------------------------------
do $$
-- ::text SART: text[] || 'metin' belirsiz, Postgres literali
  -- diziye cevirmeye calisiyor ("malformed array literal").
  declare eksik text[] := '{}';
begin
  if to_regclass('public.yorumlar') is null then
    eksik := eksik || 'veritabani/yorum.sql (yorumlar tablosu)'::text;
  end if;
  if to_regclass('public.menu_katkilari') is null then
    eksik := eksik || 'veritabani/menu_katki.sql (menu_katkilari tablosu)'::text;
  end if;
  -- profiller yorum.sql'in de sarti; ayri sayiliyor cunku yorumlar
  -- kurulu olsa bile profil alanlari eksik olabilir.
  if to_regclass('public.profiller') is null then
    eksik := eksik || 'veritabani/profil.sql (profiller tablosu)'::text;
  end if;
  if array_length(eksik, 1) is not null then
    raise exception E'topluluk.sql once sunlari istiyor:\n  - %\n'
      'KURULUM.md''deki sirayla calistir, sonra bu dosyayi tekrar dene.',
      array_to_string(eksik, E'\n  - ');
  end if;
end $$;

create or replace function public.topluluk_akisi(
  p_once timestamptz default null,
  p_limit integer default 30
)
returns table (
  tur         text,
  id          bigint,
  mekan_id    text,
  mekan_ad    text,
  il          text,
  puan        smallint,
  metin       text,
  urun        text,
  fiyat       numeric,
  foto        text,
  olusturuldu timestamptz,
  yazar_adi   text,
  yazar_ad    text,
  yazar_avatar text
)
language sql
stable
security definer
set search_path = public
as $$
  with
  -- Sınır SUNUCUDA. İstemciden gelen sayı ne olursa olsun 60'ı geçmiyor:
  -- p_limit = 100000 diye çağıran biri tabloyu tek istekte boşaltamasın.
  s as (select least(greatest(coalesce(p_limit, 30), 1), 60) as n),
  y as (
    select 'yorum'::text as tur, y.id, y.mekan_id, y.mekan_ad, y.il,
           y.puan, y.metin,
           null::text as urun, null::numeric as fiyat, null::text as foto,
           y.olusturuldu,
           case when p.herkese_acik then p.kullanici_adi end as yazar_adi,
           case when p.herkese_acik then p.ad end           as yazar_ad,
           case when p.herkese_acik then p.avatar end       as yazar_avatar
    from public.yorumlar y
    left join public.profiller p on p.id = y.kullanici
    where y.durum = 'onaylandi'
      and (p_once is null or y.olusturuldu < p_once)
    order by y.olusturuldu desc
    limit (select n from s)
  ),
  k as (
    -- ADSIZ: yazar sütunları bilerek null. Bkz. başlıktaki "KİM GÖRÜNÜYOR".
    select 'menu'::text as tur, k.id, k.mekan_id, k.mekan_ad, k.il,
           null::smallint as puan, null::text as metin,
           k.urun, k.fiyat, k.foto,
           k.olusturuldu,
           null::text as yazar_adi, null::text as yazar_ad,
           null::text as yazar_avatar
    from public.menu_katkilari k
    where k.durum = 'onaylandi'
      and (p_once is null or k.olusturuldu < p_once)
    order by k.olusturuldu desc
    limit (select n from s)
  )
  select * from (select * from y union all select * from k) t
  order by t.olusturuldu desc
  limit (select n from s);
$$;

revoke all on function public.topluluk_akisi(timestamptz, integer) from public;
grant execute on function public.topluluk_akisi(timestamptz, integer) to anon, authenticated;

comment on function public.topluluk_akisi is
  'Son onayli katkilar. Yorum yazariyla, menu katkisi ADSIZ. Fis ve fiyat oyu YOK.';

do $$
begin
  if to_regclass('public.topluluk_akisi'::text) is null then null; end if;
  raise notice 'Topluluk akisi kuruldu: yorum yazariyla, menu katkisi ADSIZ, fis ve fiyat oyu yok.';
end $$;
