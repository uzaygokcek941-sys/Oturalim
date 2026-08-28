-- ============================================================
-- Cebimde — bayilik (saha temsilciliği)
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir. ÖNCE sema.sql, katki.sql ve sahiplenme.sql
-- çalıştırılmış olmalı.
--
-- NEDEN VAR. Uygulamanın tek gerçek darboğazı veri: 35.852 mekanın
-- 30.393'ünde (%84,8) ne web, ne sosyal medya, ne telefon var; menüsü
-- olan 293 mekan (%0,82). Bu bilgiyi uzaktan toplamanın yolu yok --
-- işletmenin kapısına gidip kart bırakmak gerekiyor (sahiplenme.sql).
-- Kapıya gitmek ölçeklenmeyen tek iş ve bir kişiyle 81 il olmuyor.
-- Bayi, o işi bölge bölge devralan kişi.
--
-- KREDİ KODA BAĞLI, BEYANA DEĞİL. Bayi "40 yere uğradım" demiyor;
-- bastığı kart partisindeki kodlar zaten mekan mekan tekil ve
-- sahiplenme_kodu satırında hangi bayiye ait olduğu yazılı. İşletme kodu
-- kullandığında hakediş KENDİLİĞİNDEN düşüyor. Beyan olsaydı ölçtüğümüz
-- şey ziyaret değil, ziyaret iddiası olurdu.
--
-- İKİ AŞAMA, ÇÜNKÜ TEK AŞAMA YANLIŞ TEŞVİK. 'sahiplenme' = işletme
-- sayfasını sahiplendi (kart çalıştı). 'alan' = işletme gerçekten bilgi
-- ekledi (kart işe yaradı). Yalnız birinciyi ödeseydik bayinin işi kartı
-- kime olursa okutmak olurdu; ikincisi parayı projenin ihtiyacı olan
-- şeye -- veriye -- bağlıyor.
--
-- ÜCRET VARSAYILANI SIFIR VE BU BİLEREK. Bayiye ne ödeneceği ticari bir
-- karar; şema onu kendiliğinden koymuyor. Ücret bayi satırında ve
-- HAKEDİŞ ANINDA DONDURULUYOR (bayi_kazanim.tutar), yani oranın sonradan
-- değişmesi geçmişi yeniden yazmıyor. Önerilen başlangıç değerleri
-- BAYILIK.md'de.
--
-- NE VERMİYOR: sıralama, rozet, öne çıkarma, mekan silme, başka bayinin
-- verisi, kullanıcı kimliği. Bayi bölgesindeki mekanların SAYILARINI
-- görüyor; o mekanı kimin sahiplendiğini görmüyor. "Para karşılığı
-- sıralama bu projede yok" kuralı bayilikle de delinmiyor.
-- ============================================================

-- ---------- 1. Bayi ----------
create table if not exists public.bayi (
  id            bigint generated always as identity primary key,
  -- Kullanıcı silinirse bayilik de düşer: yetki kişiye bağlı.
  kullanici     uuid not null unique references auth.users(id) on delete cascade,
  ad            text not null check (char_length(ad) between 2 and 120),
  telefon       text check (char_length(telefon) <= 30),
  -- 'aday' = başvurdu, henüz bölge yok. 'aktif' = kart basılabilir.
  -- 'askida' = geçici durdurma. 'ayrildi' = bitti. Hiçbiri SİLMİYOR:
  -- dağıtılmış kartlar ortada duruyor ve kimin bastığı kaybolmamalı.
  durum         text not null default 'aday'
                check (durum in ('aday','aktif','askida','ayrildi')),
  -- Kuruş. Ondalık para tipini bilerek kullanmıyoruz: bir bayinin
  -- hakedişi tam sayıların toplamı olsun, yuvarlama tartışması olmasın.
  sahiplenme_ucreti integer not null default 0 check (sahiplenme_ucreti between 0 and 1000000),
  alan_ucreti       integer not null default 0 check (alan_ucreti between 0 and 1000000),
  baslangic     date not null default current_date,
  notu          text check (char_length(notu) <= 500),
  olusturuldu   timestamptz not null default now()
);

comment on table public.bayi is
  'Saha temsilcisi. Kart partileri buna baglanir, hakedis koddan dogar.';

-- ---------- 2. Bölge ----------
-- Bir ilçenin aynı anda tek bayisi olur. Kısıt 'aktif' ile sınırlı:
-- bırakılmış bölge kaydı duruyor, yeni bayinin önünü tıkamıyor
-- (sahiplik tablosundaki tek-aktif deseninin aynısı).
create table if not exists public.bayi_bolge (
  id           bigint generated always as identity primary key,
  bayi         bigint not null references public.bayi(id) on delete cascade,
  il           text not null check (char_length(il) = 2),
  -- İlçe adı serbest metin: il dosyalarında ilçe alanı çoğu mekanda boş
  -- (Kadıköy kümesinde 112 mekanın 5'inde dolu). Kod tarafında bölge bir
  -- ETİKET; kısıtı veriye değil anlaşmaya dayandırıyoruz.
  ilce         text not null check (char_length(ilce) between 1 and 80),
  durum        text not null default 'aktif' check (durum in ('aktif','birakildi')),
  olusturuldu  timestamptz not null default now()
);

create unique index if not exists bayi_bolge_tek_aktif_idx
  on public.bayi_bolge (il, ilce) where durum = 'aktif';
create index if not exists bayi_bolge_bayi_idx on public.bayi_bolge (bayi);

-- ---------- 3. Kart partisi: koda bayi eklendi ----------
-- sahiplenme_kodu ZATEN VAR (sahiplenme.sql). Burada iki sütun ekleniyor;
-- ikisi de null olabilir, yani bayisiz basılmış eski kartlar aynen
-- çalışmaya devam ediyor. Bu dosyanın sahiplenme.sql'i değiştirmemesi
-- bilerek: kurulum sırası ikisini birbirine bağımlı kılmasın.
alter table public.sahiplenme_kodu
  add column if not exists bayi bigint references public.bayi(id) on delete set null;
alter table public.sahiplenme_kodu
  add column if not exists parti text;

do $$ begin
  alter table public.sahiplenme_kodu
    add constraint sahiplenme_kodu_parti_check check (char_length(parti) <= 60);
exception when duplicate_object then null;
end $$;

create index if not exists sahiplenme_kodu_bayi_idx
  on public.sahiplenme_kodu (bayi) where bayi is not null;

-- ---------- 4. Kazanım ----------
-- Bir mekan bir bayiye her türden BİR KEZ kazandırır. Tekil kısıt bunu
-- söylüyor: işletmenin on alan doldurması on hakediş değil. Ölçtüğümüz
-- şey "kart işe yaradı mı", "kaç tuşa basıldı" değil.
create table if not exists public.bayi_kazanim (
  id           bigint generated always as identity primary key,
  bayi         bigint not null references public.bayi(id) on delete cascade,
  mekan_id     text not null check (char_length(mekan_id) between 1 and 80),
  mekan_ad     text not null check (char_length(mekan_ad) between 1 and 200),
  il           text check (char_length(il) = 2),
  tur          text not null check (tur in ('sahiplenme','alan')),
  -- Hakediş anındaki ücret, kuruş. Bayi satırındaki oran sonradan
  -- değişirse geçmiş kazanımlar DEĞİŞMEZ.
  tutar        integer not null check (tutar >= 0),
  olusturuldu  timestamptz not null default now()
);

create unique index if not exists bayi_kazanim_tekil_idx
  on public.bayi_kazanim (bayi, mekan_id, tur);
create index if not exists bayi_kazanim_bayi_idx
  on public.bayi_kazanim (bayi, olusturuldu desc);

-- ---------- 5. Ödeme ----------
-- Para transferi bu sistemin DIŞINDA (havale/EFT). Burada yalnız "ne
-- kadar ödendi" kaydı var; bakiye = hakediş - ödenen. Ödeme satırını
-- yalnız yönetici yazıyor.
create table if not exists public.bayi_odeme (
  id           bigint generated always as identity primary key,
  bayi         bigint not null references public.bayi(id) on delete cascade,
  tutar        integer not null check (tutar > 0),
  tarih        date not null default current_date,
  aciklama     text check (char_length(aciklama) <= 300),
  olusturuldu  timestamptz not null default now()
);
create index if not exists bayi_odeme_bayi_idx on public.bayi_odeme (bayi, tarih desc);

-- ============================================================
-- Yardımcılar
-- ============================================================
-- Politikaların içinden çağrılıyor; stable + security definer olmalı,
-- yoksa çağıranın RLS'i tekrar devreye girip döngü yapar (sahibi_mi ile
-- aynı gerekçe).
create or replace function public.bayi_kimligim()
returns bigint
language sql
security definer
stable
set search_path = public
as $$
  select id from public.bayi
   where kullanici = auth.uid() and durum in ('aktif','askida')
   limit 1;
$$;
revoke all on function public.bayi_kimligim() from public;
grant execute on function public.bayi_kimligim() to authenticated;

-- 'aday' bayi DEĞİL: başvurmuş ama bölgesi yok. 'askida' bayi kendi
-- geçmişini görebilmeli, o yüzden yukarıdaki kimlik onu kapsıyor;
-- burası "panel açılsın mı" sorusunun cevabı.
create or replace function public.bayi_mi()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (select 1 from public.bayi
                  where kullanici = auth.uid() and durum = 'aktif');
$$;
revoke all on function public.bayi_mi() from public;
grant execute on function public.bayi_mi() to anon, authenticated;

-- ============================================================
-- Kazanım tetikleyicileri
-- ============================================================
-- (a) Kod kullanıldı -> 'sahiplenme'.
--
-- Tetikleyici, sahiplenme_kodu_kullan() fonksiyonunun İÇİNE yazmak
-- yerine tabloya asıldı ve sebebi kurulum sırası: o fonksiyon
-- sahiplenme.sql'de ve bu dosya çalıştırılmamış olabilir. Fonksiyonu
-- burada yeniden tanımlasaydık iki dosya aynı fonksiyonun iki sürümünü
-- taşırdı ve hangisinin en son koştuğu sonucu değiştirirdi.
--
-- Bayinin durumuna BAKILMIYOR. Ayrılmış bir bayinin dağıttığı kart bugün
-- kullanılırsa iş yapılmıştır; hakediş doğar. Ödeyip ödememek ayrı karar
-- ve o kaydın üstünde alınır.
create or replace function public.bayi_kazanim_sahiplenme()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  u integer;
begin
  if new.bayi is null or new.kullanildi is null
     or old.kullanildi is not null then
    return new;
  end if;
  select sahiplenme_ucreti into u from public.bayi where id = new.bayi;
  if u is null then return new; end if;
  insert into public.bayi_kazanim (bayi, mekan_id, mekan_ad, il, tur, tutar)
  values (new.bayi, new.mekan_id, new.mekan_ad, new.il, 'sahiplenme', u)
  on conflict (bayi, mekan_id, tur) do nothing;
  return new;
end;
$$;

drop trigger if exists sahiplenme_kodu_bayi_kazanimi on public.sahiplenme_kodu;
create trigger sahiplenme_kodu_bayi_kazanimi
  after update on public.sahiplenme_kodu
  for each row execute function public.bayi_kazanim_sahiplenme();

-- (b) Onaylanmış katkı -> 'alan'.
--
-- Bağ, mekanın KULLANILMIŞ kodu üzerinden kuruluyor: o mekana kart kim
-- bıraktıysa hakediş onun. Kart bırakılmamış bir mekana gelen katkı
-- hiçbir bayiye yazılmıyor -- doğru olan da bu, orada saha işi yok.
--
-- Hata YUTULMUYOR. Bir hata burada katkıyı da düşürür; kabul ediliyor,
-- çünkü sessizce yanlış hakediş yazan bir tetikleyici bu depoda tekrar
-- tekrar kapattığımız hatanın ta kendisi: başarısızlığı göremeyen kapı.
create or replace function public.bayi_kazanim_alan()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  b integer;
  u integer;
begin
  if new.durum <> 'onaylandi' then return new; end if;
  select k.bayi into b from public.sahiplenme_kodu k
   where k.mekan_id = new.mekan_id
     and k.bayi is not null and k.kullanildi is not null
   order by k.kullanildi
   limit 1;
  if b is null then return new; end if;
  select alan_ucreti into u from public.bayi where id = b;
  if u is null then return new; end if;
  insert into public.bayi_kazanim (bayi, mekan_id, mekan_ad, il, tur, tutar)
  values (b, new.mekan_id, new.mekan_ad, new.il, 'alan', u)
  on conflict (bayi, mekan_id, tur) do nothing;
  return new;
end;
$$;

drop trigger if exists katki_bayi_kazanimi on public.katkilar;
create trigger katki_bayi_kazanimi
  after insert or update of durum on public.katkilar
  for each row execute function public.bayi_kazanim_alan();

-- ============================================================
-- RLS — bayi yalnız kendini görür
-- ============================================================
alter table public.bayi         enable row level security;
alter table public.bayi_bolge   enable row level security;
alter table public.bayi_kazanim enable row level security;
alter table public.bayi_odeme   enable row level security;

-- INSERT/UPDATE/DELETE politikası YALNIZ yöneticide. Bayilik kendi
-- kendine alınan bir şey değil: kart basmak, bölge vermek ve ücret
-- belirlemek anlaşma gerektiriyor.
drop policy if exists "bayi kendini gorur" on public.bayi;
create policy "bayi kendini gorur" on public.bayi
  for select using (kullanici = auth.uid() or public.yonetici_mi());

drop policy if exists "bayi yonetici yazar" on public.bayi;
create policy "bayi yonetici yazar" on public.bayi
  for insert with check (public.yonetici_mi());
drop policy if exists "bayi yonetici gunceller" on public.bayi;
create policy "bayi yonetici gunceller" on public.bayi
  for update using (public.yonetici_mi()) with check (public.yonetici_mi());

drop policy if exists "bayi bolge kendini gorur" on public.bayi_bolge;
create policy "bayi bolge kendini gorur" on public.bayi_bolge
  for select using (bayi = public.bayi_kimligim() or public.yonetici_mi());
drop policy if exists "bayi bolge yonetici yazar" on public.bayi_bolge;
create policy "bayi bolge yonetici yazar" on public.bayi_bolge
  for all using (public.yonetici_mi()) with check (public.yonetici_mi());

drop policy if exists "bayi kazanim kendini gorur" on public.bayi_kazanim;
create policy "bayi kazanim kendini gorur" on public.bayi_kazanim
  for select using (bayi = public.bayi_kimligim() or public.yonetici_mi());
-- Kazanıma KİMSE elle yazamaz, yönetici de yazamaz: tek kaynağı
-- tetikleyici (security definer, RLS'in dışında). Elle yazma yolu açık
-- olsaydı hakedişin "koddan doğar" kuralı yalan olurdu.

drop policy if exists "bayi odeme kendini gorur" on public.bayi_odeme;
create policy "bayi odeme kendini gorur" on public.bayi_odeme
  for select using (bayi = public.bayi_kimligim() or public.yonetici_mi());
drop policy if exists "bayi odeme yonetici yazar" on public.bayi_odeme;
create policy "bayi odeme yonetici yazar" on public.bayi_odeme
  for all using (public.yonetici_mi()) with check (public.yonetici_mi());

-- ============================================================
-- Sütun yetkisi — kimin kim olduğu tarayıcıya inmiyor
--
-- sema.sql ve sahiplenme.sql'deki aynı başlıkla aynı gerekçe: RLS SATIR
-- düzeyinde çalışır, satırı açtığında içindeki `kullanici` sütunu da
-- açılır. Bayi kendi satırını görüyor -- ama aynı uuid'yi profiller,
-- katkilar ve sahiplik ile birleştirebilecek biri için bu sütun bir iz.
-- Politika `kullanici` sütununa bakmaya devam ediyor; politika ifadesi
-- sütun yetkisine tabi değil, kullanıcının SELECT listesi tabi.
-- ============================================================
revoke select on public.bayi from anon, authenticated;
grant  select (id, ad, telefon, durum, sahiplenme_ucreti, alan_ucreti,
               baslangic, notu, olusturuldu)
  on public.bayi to authenticated;

-- ============================================================
-- Panelin okuduğu iki fonksiyon
-- ============================================================
-- Özet: bayinin panele bakma sebebi bu satır.
-- Tutarlar KURUŞ; TL'ye çevirmek arayüzün işi (tek yerde, ortak.js).
create or replace function public.bayi_ozetim()
returns table (kart integer, sahiplenilen integer, alan_eklenen integer,
               hakedis integer, odenen integer, bakiye integer)
language plpgsql
security definer
set search_path = public
as $$
declare
  b bigint := public.bayi_kimligim();
begin
  if b is null then
    raise exception 'bayi degilsiniz' using errcode = 'insufficient_privilege';
  end if;
  return query
  select
    (select count(*)::int from public.sahiplenme_kodu where bayi = b),
    (select count(*)::int from public.sahiplenme_kodu
      where bayi = b and kullanildi is not null),
    (select count(*)::int from public.bayi_kazanim
      where bayi = b and tur = 'alan'),
    (select coalesce(sum(tutar),0)::int from public.bayi_kazanim where bayi = b),
    (select coalesce(sum(tutar),0)::int from public.bayi_odeme where bayi = b),
    (select coalesce((select sum(tutar) from public.bayi_kazanim where bayi = b),0)
          - coalesce((select sum(tutar) from public.bayi_odeme  where bayi = b),0))::int;
end;
$$;
revoke all on function public.bayi_ozetim() from public;
grant execute on function public.bayi_ozetim() to authenticated;

-- Kart kart liste. security definer, çünkü sahiplenme_kodu tablosu
-- RLS açık ve POLİTİKASIZ -- kimse okuyamıyor, bu fonksiyon okuyabiliyor.
--
-- DÖNMEYEN İKİ SÜTUN VAR VE ÖNEMLİLER: kod_ozeti ve kullanan.
-- Birincisi kartın anahtarı, ikincisi işletmecinin kimliği. Bayi
-- "sahiplenildi mi" bilgisini görüyor, "kim sahiplendi"yi görmüyor.
create or replace function public.bayi_kartlarim(p_sinir integer default 500)
returns table (mekan_id text, mekan_ad text, il text, parti text,
               basildi timestamptz, sahiplenildi timestamptz,
               gecerlilik date, alan_eklendi boolean)
language plpgsql
security definer
set search_path = public
as $$
declare
  b bigint := public.bayi_kimligim();
begin
  if b is null then
    raise exception 'bayi degilsiniz' using errcode = 'insufficient_privilege';
  end if;
  return query
  select k.mekan_id, k.mekan_ad, k.il, k.parti,
         k.olusturuldu, k.kullanildi, k.gecerlilik,
         exists (select 1 from public.bayi_kazanim z
                  where z.bayi = b and z.mekan_id = k.mekan_id and z.tur = 'alan')
    from public.sahiplenme_kodu k
   where k.bayi = b
   order by k.kullanildi desc nulls last, k.olusturuldu desc
   limit greatest(1, least(coalesce(p_sinir, 500), 2000));
end;
$$;
revoke all on function public.bayi_kartlarim(integer) from public;
grant execute on function public.bayi_kartlarim(integer) to authenticated;

-- Bölgem. Tablodan da okunabilirdi; fonksiyon, panelin tek bir yerden
-- (ve bayi id'sini hiç görmeden) okuması için.
create or replace function public.bayi_bolgelerim()
returns table (il text, ilce text, durum text)
language sql
security definer
stable
set search_path = public
as $$
  select b.il, b.ilce, b.durum from public.bayi_bolge b
   where b.bayi = public.bayi_kimligim()
   order by b.durum, b.il, b.ilce;
$$;
revoke all on function public.bayi_bolgelerim() from public;
grant execute on function public.bayi_bolgelerim() to authenticated;

-- ============================================================
-- Kendini kontrol — bu blok hata vermeden geçmeli
-- ============================================================
do $$
declare
  n int;
begin
  if not exists (select 1 from pg_proc where proname = 'yonetici_mi'
                 and pronamespace = 'public'::regnamespace) then
    raise exception 'Once sema.sql calistirilmali: yonetici_mi() yok';
  end if;
  if not exists (select 1 from pg_tables where schemaname = 'public'
                 and tablename = 'sahiplenme_kodu') then
    raise exception 'Once sahiplenme.sql calistirilmali: sahiplenme_kodu yok';
  end if;

  -- Dört tabloda da RLS açık olmalı. Kapalı bir tablo "herkes görür"
  -- demek ve burada görülecek şey hakediş ile telefon numarası.
  select count(*) into n from pg_tables
   where schemaname='public'
     and tablename in ('bayi','bayi_bolge','bayi_kazanim','bayi_odeme')
     and rowsecurity = true;
  if n <> 4 then
    raise exception 'RLS 4 bayi tablosunun %sinde acik', n;
  end if;

  -- Kazanıma elle yazma yolu OLMAMALI: insert/update/delete politikası
  -- yok, yani tek kaynak tetikleyici.
  select count(*) into n from pg_policies
   where schemaname='public' and tablename='bayi_kazanim'
     and cmd in ('INSERT','UPDATE','DELETE','ALL');
  if n <> 0 then
    raise exception 'bayi_kazanim uzerinde % yazma politikasi var, olmamali', n;
  end if;

  -- sahiplenme_kodu'na iki sütun gerçekten eklendi mi.
  if not exists (select 1 from information_schema.columns
                  where table_schema='public' and table_name='sahiplenme_kodu'
                    and column_name='bayi') then
    raise exception 'sahiplenme_kodu.bayi sutunu eklenmemis';
  end if;

  -- Kimlik sütunu tarayıcıya kapalı mı: authenticated `kullanici`
  -- sütununu SEÇEMEMELİ.
  if has_column_privilege('authenticated', 'public.bayi', 'kullanici', 'select') then
    raise exception 'bayi.kullanici sutunu authenticated rolune acik';
  end if;
  if not has_column_privilege('authenticated', 'public.bayi', 'ad', 'select') then
    raise exception 'bayi.ad sutunu kapali, panel bos gorunur';
  end if;

  -- İki tetikleyici de asılı mı.
  if not exists (select 1 from pg_trigger
                  where tgname = 'sahiplenme_kodu_bayi_kazanimi') then
    raise exception 'sahiplenme kazanim tetikleyicisi yok';
  end if;
  if not exists (select 1 from pg_trigger where tgname = 'katki_bayi_kazanimi') then
    raise exception 'alan kazanim tetikleyicisi yok';
  end if;

  raise notice 'Bayilik kuruldu: 4 tablo, 2 tetikleyici, kazanim yalniz koddan';
end;
$$;
