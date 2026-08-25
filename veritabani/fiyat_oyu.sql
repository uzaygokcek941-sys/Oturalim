-- ============================================================
-- Cebimde — sosyal fiyat doğrulama: "bu fiyat hâlâ geçerli mi?"
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir. sema.sql'den SONRA.
--
-- NEDEN VAR — ÖLÇÜLDÜ. Menü fiyatı gösterilebilen 35.852 mekandan
-- yalnız 163'ünde var ve o 163 mekan aslında 53 işletme (94'ü tek bir
-- zincirin şubesi). Kazıma yolu kapandı (CEBIMDE.md, 2026-08-20: üç
-- ayrı ölçüm, sıfır kalem). Yani fiyat verisinin büyümesinin tek yolu
-- kullanıcı.
--
-- Fiş paylaşmak ise PAHALI bir eylem: tutar, kişi sayısı, tarih.
-- Bu tablo UCUZ olanı topluyor -- tek dokunuş. Bir kullanıcı ekranda
-- gördüğü fiyata "hâlâ böyle" ya da "değişmiş" diyor.
--
-- FİŞTEN AYRI TUTULUYOR. paylasimlar bir ÖLÇÜM taşıyor (850 TL, 3 kişi);
-- burası bir DOĞRULAMA taşıyor (evet/hayır). İkisini tek tabloda
-- toplamak, ortalamanın içine oy karıştırmak olurdu. Oy, fiyat
-- ortalamasına GİRMİYOR -- yalnız güven skorunu etkiliyor.
--
-- ONAY KUYRUĞU YOK, bilerek. Yorumda ön onay var çünkü orada hakaret ve
-- karalama riski var; burada gönderilen şey bir boolean. Kötüye kullanım
-- riski farklı: işletmenin kendi fiyatını "geçerli" diye oylaması. Ona
-- karşı savunma onay değil EŞİK -- üç AYRI kullanıcı gerekiyor ve
-- sayımı sunucu yapıyor (bkz. fiyat_oy_ozeti).
--
-- OY HANGİ FİYATA VERİLDİYSE ONA AİT. Kullanıcının gördüğü rakam
-- satırda duruyor. Menü tazelenip fiyat değişirse eski oylar YENİ
-- rakamı doğrulamış sayılmıyor -- yoksa 240 TL'ye verilen "hâlâ böyle"
-- oyu, 480 TL'ye dönmüş bir menüyü doğrular hale gelirdi.
-- ============================================================

create table if not exists public.fiyat_oylari (
  id           bigint generated always as identity primary key,
  -- Kullanıcı silinirse oy kalır ama sahipsizleşir (paylasimlar,
  -- katkilar ve yorumlar ile aynı kural).
  kullanici    uuid references auth.users(id) on delete set null,
  mekan_id     text not null check (char_length(mekan_id) between 1 and 80),
  il           text check (char_length(il) = 2),
  -- Oy verilen rakam. Kişi başı değil: ekranda yazan menü ortalaması.
  fiyat        numeric(10,2) not null check (fiyat > 0 and fiyat < 100000),
  gecerli      boolean not null,
  olusturuldu  timestamptz not null default now()
);

comment on table public.fiyat_oylari is
  'Kullanicinin ekranda gordugu menu fiyatina "hala boyle / degismis" oyu. '
  'Fiyat ortalamasina GIRMEZ; yalniz guven skorunu etkiler.';

create index if not exists fiyat_oylari_mekan_idx
  on public.fiyat_oylari (mekan_id, olusturuldu desc);
create index if not exists fiyat_oylari_kullanici_idx
  on public.fiyat_oylari (kullanici, olusturuldu desc);

-- Bir kişi bir mekanın BİR fiyatına BİR oy verir. Fiyat anahtarın
-- içinde: menü tazelenip rakam değişirse aynı kişi yeni rakama yeniden
-- oy verebilmeli -- yoksa fiyat değiştiği anda doğrulama akışı o mekan
-- için kalıcı olarak kapanırdı.
create unique index if not exists fiyat_oylari_tek_oy_idx
  on public.fiyat_oylari (kullanici, mekan_id, fiyat)
  where kullanici is not null;

-- Günlük gönderim sınırı: fonksiyon sema.sql'de, aynı kural bütün
-- kuyrukları koruyor. Tek dokunuşluk bir eylem olduğu için burada
-- daha da gerekli -- listeyi kaydırırken yüzlerce oy atılabilir.
drop trigger if exists fiyat_oyu_gunluk_sinir on public.fiyat_oylari;
create trigger fiyat_oyu_gunluk_sinir
  before insert on public.fiyat_oylari
  for each row execute function public.gunluk_gonderim_siniri();

-- ============================================================
-- RLS
--
-- Tablo DIŞARIYA KAPALI. Tek tek oylar okunabilseydi kim neye oy
-- verdiği görünürdü; toplamı security definer fonksiyon veriyor.
-- ============================================================
alter table public.fiyat_oylari enable row level security;

drop policy if exists "fiyat oyu kendi gorur" on public.fiyat_oylari;
create policy "fiyat oyu kendi gorur" on public.fiyat_oylari
  for select using (kullanici = auth.uid() or public.yonetici_mi());

drop policy if exists "fiyat oyu kendi ekler" on public.fiyat_oylari;
create policy "fiyat oyu kendi ekler" on public.fiyat_oylari
  for insert with check (kullanici = auth.uid());

drop policy if exists "fiyat oyu kendi siler" on public.fiyat_oylari;
create policy "fiyat oyu kendi siler" on public.fiyat_oylari
  for delete using (kullanici = auth.uid());

-- ============================================================
-- Toplam: kaç KİŞİ ne demiş
--
-- security definer, çünkü sayım `kullanici` sütununa bakıyor ve o sütun
-- anon'a kapalı (sema.sql "Sütun yetkisi"). Tarayıcı aynı kişinin iki
-- oyunu tek kişi sayamaz -- sayabilseydi zaten kişiyi izleyebiliyor
-- olurdu.
--
-- PENCERE 180 GÜN. Bir yıl önceki "hâlâ böyle" oyu bugünkü fiyatı
-- doğrulamıyor; enflasyonda o süre fiyat ayrımının kendisinden büyük.
-- Aynı pencere butce_akranlari'nda da var (AKRAN_GUN) ve ortak.js
-- "son 6 ayda" diyor.
-- ============================================================
create or replace function public.fiyat_oy_ozeti(p_mekan_idler text[])
returns table (mekan_id text, fiyat numeric, gecerli int, degisti int, kisi int)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  -- Sessiz kırpma YOK: ekranda yazan "bu civar" ifadesini yalan yapardı
  -- (civar_fis_ozeti ile aynı gerekçe ve aynı sınır).
  if array_length(p_mekan_idler, 1) > 500 then
    raise exception 'mekan listesi cok uzun (% > 500)', array_length(p_mekan_idler, 1)
      using errcode = 'program_limit_exceeded';
  end if;

  return query
  select o.mekan_id,
         o.fiyat,
         -- ESIK SUNUCUDA (3, ortak.js OY_ESIK ile ayni). Esigin altinda
         -- KISI SAYISI donuyor ama DAGILIM donmuyor: arayuz "1 kisi daha
         -- soyleyince sonucu yazacagim" cumlesini sayidan kuruyor.
         -- Dagilimi vermek, tek kisinin ne dedigini ifsa ederdi.
         case when count(distinct o.kullanici) >= 3
              then count(distinct o.kullanici) filter (where o.gecerli)::int
              else 0 end,
         case when count(distinct o.kullanici) >= 3
              then count(distinct o.kullanici) filter (where not o.gecerli)::int
              else 0 end,
         count(distinct o.kullanici)::int
    from public.fiyat_oylari o
   where p_mekan_idler is not null
     and o.mekan_id = any(p_mekan_idler)
     and o.olusturuldu >= now() - interval '180 days'
     and o.kullanici is not null
   group by o.mekan_id, o.fiyat;
end;
$$;

revoke all on function public.fiyat_oy_ozeti(text[]) from public;
grant execute on function public.fiyat_oy_ozeti(text[]) to anon, authenticated;

comment on function public.fiyat_oy_ozeti(text[]) is
  'Mekan basina "hala boyle / degismis" oyu veren KISI sayisi (fis degil). '
  'Son 180 gun. Oy verilen fiyata gore gruplu.';

\echo 'Fiyat oylari kuruldu: tablo, RLS, tek-oy kurali ve fiyat_oy_ozeti().'
