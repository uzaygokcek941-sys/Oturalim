-- ============================================================
-- Oturalım — mekan yorumları
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir. sema.sql ve profil.sql'den SONRA.
--
-- NEDEN VAR: fiyat "kaça oturulur" sorusunu cevaplıyor, ama insanın
-- sorduğu ikinci soru "nasıl bir yer". Menü fiyatı bunu söylemiyor.
--
-- FİYATTAN AYRI TUTULUYOR. paylasimlar bir ÖLÇÜM taşıyor (850 TL, 3 kişi);
-- yorum bir KANI taşıyor. İkisini tek tabloda toplamak, ortalamanın içine
-- kanı karıştırmak olurdu. Yorumun puanı fiyat hesabına GİRMİYOR.
--
-- ONAY ŞART: yorum doğrudan yayına girmez. Sebep katkilar'dakiyle aynı
-- değil -- burada mesele yanlış bilgi değil, hakaret ve karalama.
-- Tek kişilik bir yapıda bunun tek savunması ön onaydır.
--
-- PUAN ZORUNLU, METİN İSTEĞE BAĞLI: puansız yorum sıralanamaz, metinsiz
-- puan yine bir bilgidir.
-- ============================================================

create table if not exists public.yorumlar (
  id           bigint generated always as identity primary key,
  -- Kullanıcı silinirse yorum kalır ama sahipsizleşir: yayımlanmış kanı
  -- mekana bağlı. (paylasimlar ve katkilar ile aynı kural.)
  kullanici    uuid references auth.users(id) on delete set null,
  mekan_id     text not null check (char_length(mekan_id) between 1 and 80),
  il           text check (char_length(il) = 2),
  mekan_ad     text not null check (char_length(mekan_ad) between 2 and 200),
  puan         smallint not null check (puan between 1 and 5),
  -- 400 karakter: yorum bir deneme değil. Sınır hem okunabilirlik hem de
  -- tek yöneticinin okuyabileceği hacim için.
  metin        text check (metin is null or char_length(metin) between 3 and 400),
  durum        text not null default 'bekliyor'
               check (durum in ('bekliyor','onaylandi','reddedildi')),
  olusturuldu  timestamptz not null default now()
);

comment on table public.yorumlar is
  'Mekan yorumu ve puani. Onaydan gecmeden yayina girmez. Fiyat hesabina GIRMEZ.';

create index if not exists yorumlar_durum_idx     on public.yorumlar (durum, olusturuldu desc);
create index if not exists yorumlar_kullanici_idx on public.yorumlar (kullanici, olusturuldu desc);
create index if not exists yorumlar_mekan_idx     on public.yorumlar (mekan_id) where durum = 'onaylandi';

-- Bir kişi bir mekana BİR yorum yazar. Reddedilen sayılmıyor: düzeltip
-- tekrar gönderebilmeli. Onaylanan da sayılıyor -- ikinci yorum yazmak
-- yerine mevcudunu silip yenisini yazsın, yoksa aynı kişi bir mekanı
-- puan ortalamasında istediği kadar tekrarlar.
create unique index if not exists yorumlar_tek_kayit_idx
  on public.yorumlar (kullanici, mekan_id)
  where durum <> 'reddedildi' and kullanici is not null;

-- Günlük gönderim sınırı: fonksiyon sema.sql'de, aynı kural üç kuyruğu
-- birden koruyor.
drop trigger if exists yorum_gunluk_sinir on public.yorumlar;
create trigger yorum_gunluk_sinir
  before insert on public.yorumlar
  for each row execute function public.gunluk_gonderim_siniri();

-- ============================================================
-- RLS
-- ============================================================
alter table public.yorumlar enable row level security;

drop policy if exists "yorum onaylanmis herkese acik" on public.yorumlar;
create policy "yorum onaylanmis herkese acik" on public.yorumlar
  for select using (durum = 'onaylandi' or kullanici = auth.uid() or public.yonetici_mi());

-- Kullanıcı YALNIZ 'bekliyor' durumuyla yazabilir: durumu kendi
-- belirleyebilseydi onay şartı anlamsız olurdu.
drop policy if exists "yorum kendi ekler" on public.yorumlar;
create policy "yorum kendi ekler" on public.yorumlar
  for insert with check (kullanici = auth.uid() and durum = 'bekliyor');

drop policy if exists "yorum kendi siler" on public.yorumlar;
create policy "yorum kendi siler" on public.yorumlar
  for delete using (kullanici = auth.uid());

drop policy if exists "yorum yonetici karar verir" on public.yorumlar;
create policy "yorum yonetici karar verir" on public.yorumlar
  for update using (public.yonetici_mi()) with check (public.yonetici_mi());

drop policy if exists "yorum yonetici siler" on public.yorumlar;
create policy "yorum yonetici siler" on public.yorumlar
  for delete using (public.yonetici_mi());

-- ============================================================
-- Sütun yetkisi — kimin kim olduğu tarayıcıya inmiyor
--
-- Gerekçe sema.sql'in aynı başlığı altında yazılı ve gerçek Postgres'te
-- ölçüldü. Burada ayrıca kritik: yorum METNİ ile uuid'yi aynı satırda
-- vermek, bir kişinin nereye gidip ne düşündüğünü tek sorguda toplardı.
-- Yazarın görünen bilgisi aşağıdaki fonksiyondan geliyor.
-- ============================================================
revoke select on public.yorumlar from anon, authenticated;
grant  select (id, mekan_id, mekan_ad, il, puan, metin, durum, olusturuldu)
  on public.yorumlar to anon, authenticated;

-- ============================================================
-- Bir mekanın yorumları — yazar bilgisiyle, kimlik numarasız
--
-- security definer: uuid'yi dışarı vermeden profil birleştiriyor.
-- Profilini kapatan kullanıcının yorumu GÖRÜNÜR, adı görünmez: yorum
-- mekana ait bir bilgi, kişiye ait değil.
-- ============================================================
create or replace function public.mekan_yorumlari(p_mekan_id text)
returns table (
  id             bigint,
  puan           smallint,
  metin          text,
  olusturuldu    timestamptz,
  yazar_adi      text,
  yazar_ad       text,
  yazar_avatar   text,
  yazar_dogum    integer,
  yazar_meslek   text
)
language sql
stable
security definer
set search_path = public
as $$
  select y.id, y.puan, y.metin, y.olusturuldu,
         case when p.herkese_acik then p.kullanici_adi end,
         case when p.herkese_acik then p.ad end,
         case when p.herkese_acik then p.avatar end,
         case when p.herkese_acik then p.dogum_yili end,
         case when p.herkese_acik then p.meslek end
  from public.yorumlar y
  left join public.profiller p on p.id = y.kullanici
  where y.mekan_id = p_mekan_id and y.durum = 'onaylandi'
  order by y.olusturuldu desc
  limit 100;
$$;
revoke all on function public.mekan_yorumlari(text) from public;
grant execute on function public.mekan_yorumlari(text) to anon, authenticated;

-- ============================================================
-- Bir kullanıcının yorumları — profil sayfası için
--
-- NE LISTELENIYOR, NE LISTELENMIYOR:
--
-- Yorumlar listeleniyor. Onaylı bir yorum zaten mekan sayfasında yazarın
-- adıyla duruyor; profilde toplamak yeni bir şey açmıyor, yalnız zaten
-- yayında olanı bir araya getiriyor. Kullanıcı her birini kendi yazdı.
--
-- FIŞLER (paylasimlar) LISTELENMIYOR ve listelenmeyecek. Onlar bir kanı
-- değil ÖDEME KAYDI: "şu gün, şu mekanda, şu kadar, şu kadar kişiyle".
-- Kişiye göre dizilince bir kişinin dışarı çıkma ve harcama geçmişi olur;
-- sema.sql'in "Sütun yetkisi" bölümü tam olarak bunu kapattı.
-- Fiyat kamuya AGREGAT olarak veriliyor, kişiye bağlı olarak değil.
--
-- Profilini kapatan kullanıcının yorumları burada da dönmüyor: profil
-- sayfası zaten açılmıyor.
-- ============================================================
create or replace function public.profil_yorumlari(p_kullanici_adi text)
returns table (
  id          bigint,
  mekan_id    text,
  mekan_ad    text,
  il          text,
  puan        smallint,
  metin       text,
  olusturuldu timestamptz
)
language sql
stable
security definer
set search_path = public
as $$
  select y.id, y.mekan_id, y.mekan_ad, y.il, y.puan, y.metin, y.olusturuldu
  from public.yorumlar y
  join public.profiller p on p.id = y.kullanici
  where p.kullanici_adi = lower(p_kullanici_adi)
    and p.herkese_acik = true
    and y.durum = 'onaylandi'
  order by y.olusturuldu desc
  limit 100;
$$;
revoke all on function public.profil_yorumlari(text) from public;
grant execute on function public.profil_yorumlari(text) to anon, authenticated;

comment on function public.profil_yorumlari is
  'Kullanicinin onayli yorumlari. FISLER BILEREK YOK: onlar kani degil odeme kaydi.';

-- ============================================================
-- Puan özeti — kart ve liste için
--
-- Eşik ISTEMCIDE (YORUM_ESIK): fonksiyon ham sayıları veriyor,
-- "gösterilsin mi" kararı tek yerde dursun. mekan_fis_ozeti ile aynı
-- kural.
-- ============================================================
create or replace function public.mekan_puani(p_mekan_id text)
returns table (adet integer, ortalama numeric)
language sql
stable
security definer
set search_path = public
as $$
  select count(*)::int,
         round(avg(puan), 1)
  from public.yorumlar
  where mekan_id = p_mekan_id and durum = 'onaylandi';
$$;
revoke all on function public.mekan_puani(text) from public;
grant execute on function public.mekan_puani(text) to anon, authenticated;

-- Keşfet ekranı bir ilin TAMAMININ puanlarını tek istekte istiyor:
-- 12 bin mekan için 12 bin çağrı atılamaz.
create or replace function public.il_puanlari(p_il text)
returns table (mekan_id text, adet integer, ortalama numeric)
language sql
stable
security definer
set search_path = public
as $$
  select y.mekan_id, count(*)::int, round(avg(y.puan), 1)
  from public.yorumlar y
  where y.il = p_il and y.durum = 'onaylandi'
  group by y.mekan_id;
$$;
revoke all on function public.il_puanlari(text) from public;
grant execute on function public.il_puanlari(text) to anon, authenticated;

-- ============================================================
-- Kendini kontrol
-- ============================================================
do $$
declare
  n int;
begin
  if not exists (select 1 from pg_proc where proname = 'gunluk_gonderim_siniri'
                 and pronamespace = 'public'::regnamespace) then
    raise exception 'Once sema.sql calistirilmali: gunluk_gonderim_siniri() yok';
  end if;
  if not exists (select 1 from information_schema.columns
                 where table_schema = 'public' and table_name = 'profiller'
                   and column_name = 'herkese_acik') then
    raise exception 'Once profil.sql calistirilmali: profiller.herkese_acik yok';
  end if;

  if not exists (select 1 from pg_tables where schemaname = 'public'
                 and tablename = 'yorumlar' and rowsecurity = true) then
    raise exception 'RLS acik degil: yorumlar';
  end if;

  select count(*) into n from pg_policies
   where schemaname = 'public' and tablename = 'yorumlar';
  if n < 5 then
    raise exception 'yorum politikalari eksik: % (en az 5 olmali)', n;
  end if;

  -- Kimlik sütunu dışarıya kapalı olmalı: yorum metni ile uuid'yi aynı
  -- satırda vermek, bir kişinin nereye gidip ne düşündüğünü tek sorguda
  -- toplardı.
  if has_column_privilege('anon', 'public.yorumlar', 'kullanici', 'SELECT') then
    raise exception 'anon yorumlar.kullanici sutununu okuyabiliyor';
  end if;

  raise notice 'Yorum kuruldu: RLS acik, % politika, kimlik sutunu kapali', n;
end;
$$;
