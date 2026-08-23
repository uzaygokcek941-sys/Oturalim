-- ============================================================
-- Oturalım — eksik bilgi katkıları
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir: her şey "if not exists" / "or replace".
--
-- NEDEN VAR: 36.102 mekanın 30.728'inde (%85,1) ne web ne telefon var.
-- Bu işletmelere uzaktan ulaşmanın yolu yok, ama bilgiyi bilen biri var:
-- o an orada oturan kullanıcı. paylasimlar tablosu FİYATI topluyordu;
-- bu tablo kalan dört alanı topluyor (saat, telefon, adres, site).
--
-- Menü/fiyat BİLEREK burada değil: onun hattı paylasimlar + fiş katmanı.
-- Aynı veriyi iki tablodan toplamak, iki ayrı doğruya yol açar.
--
-- ONAY ŞART: katkı doğrudan yayına girmez. Kullanıcıdan gelen saat bilgisi
-- yanlışsa "şu an açık" filtresi kullanıcıyı kapalı mekana yollar; bu,
-- bilgiyi hiç göstermemekten kötüdür.
-- ============================================================

create table if not exists public.katkilar (
  id           bigint generated always as identity primary key,
  -- Kullanıcı silinirse katkı kalır ama sahipsizleşir: yayımlanmış bilgi
  -- kişiye değil mekana bağlı. (paylasimlar ile aynı kural.)
  kullanici    uuid references auth.users(id) on delete set null,
  mekan_id     text not null check (char_length(mekan_id) between 1 and 80),
  il           text check (char_length(il) = 2),
  mekan_ad     text not null check (char_length(mekan_ad) between 1 and 200),
  -- Serbest alan adı YOK: istemci ne gönderirse göndersin, veritabanı
  -- yalnız bu dördünü kabul eder. isletme.html'deki EKSIK anahtarlarıyla
  -- birebir aynı; ayrışırsa sayfa toplayamadığı bir alanı ister.
  alan         text not null check (alan in ('saat','tel','adres','web')),
  deger        text not null check (char_length(deger) between 2 and 200),
  durum        text not null default 'bekliyor'
               check (durum in ('bekliyor','onaylandi','reddedildi')),
  olusturuldu  timestamptz not null default now()
);

comment on table public.katkilar is
  'Kullanicidan gelen eksik alan bilgisi. Onaydan gecmeden yayina girmez.';

create index if not exists katkilar_durum_idx     on public.katkilar (durum, olusturuldu desc);
create index if not exists katkilar_kullanici_idx on public.katkilar (kullanici, olusturuldu desc);
create index if not exists katkilar_mekan_idx     on public.katkilar (mekan_id) where durum = 'onaylandi';

-- Aynı kişi aynı mekanın aynı alanı için sırada bekleyen ikinci bir kayıt
-- açamaz. Reddedildikten sonra tekrar gönderebilir (bilgi düzelmiş olabilir),
-- onaylandıktan sonra da gönderebilir (saat değişir). Kısıt yalnız KUYRUĞU
-- korur: tek yönetici, aynı işin iki kopyasını görmesin.
create unique index if not exists katkilar_tek_bekleyen_idx
  on public.katkilar (kullanici, mekan_id, alan)
  where durum = 'bekliyor' and kullanici is not null;

-- ============================================================
-- RLS — yetki burada, istemcide değil
-- ============================================================
alter table public.katkilar enable row level security;

-- Onaylanmış katkı herkese açık (giriş yapmamış ziyaretçi dahil): işletme
-- sayfası bunu sayfayı açan herkese gösteriyor.
drop policy if exists "katki onaylanmis herkese acik" on public.katkilar;
create policy "katki onaylanmis herkese acik" on public.katkilar
  for select using (durum = 'onaylandi' or kullanici = auth.uid() or public.yonetici_mi());

-- Giriş şartı KASTEN var. Anonim yazmaya açmak katkıyı kolaylaştırırdı ama
-- kuyruğu tek kişinin temizlediği bir sistemde, kimliksiz çöp gönderimini
-- durduracak hiçbir şey kalmazdı. (goruntulenme tablosu anonim yazıyor;
-- oradaki hata payı bir sayı, buradaki hata payı yanlış bilgi.)
drop policy if exists "katki kendi ekler" on public.katkilar;
create policy "katki kendi ekler" on public.katkilar
  for insert with check (kullanici = auth.uid() and durum = 'bekliyor');

drop policy if exists "katki kendi duzeltir" on public.katkilar;
create policy "katki kendi duzeltir" on public.katkilar
  for update using (kullanici = auth.uid() and durum = 'bekliyor')
  with check (kullanici = auth.uid() and durum = 'bekliyor');

drop policy if exists "katki kendi siler" on public.katkilar;
create policy "katki kendi siler" on public.katkilar
  for delete using (kullanici = auth.uid() and durum = 'bekliyor');

drop policy if exists "katki yonetici karar verir" on public.katkilar;
create policy "katki yonetici karar verir" on public.katkilar
  for update using (public.yonetici_mi()) with check (public.yonetici_mi());

drop policy if exists "katki yonetici siler" on public.katkilar;
create policy "katki yonetici siler" on public.katkilar
  for delete using (public.yonetici_mi());

-- ============================================================
-- Kendini kontrol — bu blok hata vermeden geçmeli
-- ============================================================
do $$
declare
  politika_sayisi int;
begin
  if not exists (select 1 from pg_proc where proname = 'yonetici_mi'
                 and pronamespace = 'public'::regnamespace) then
    raise exception 'Once sema.sql calistirilmali: yonetici_mi() yok';
  end if;

  if not exists (select 1 from pg_tables
                 where schemaname = 'public' and tablename = 'katkilar'
                   and rowsecurity = true) then
    raise exception 'RLS acik degil: katkilar';
  end if;

  select count(*) into politika_sayisi
  from pg_policies where schemaname = 'public' and tablename = 'katkilar';

  if politika_sayisi < 6 then
    raise exception 'Beklenen politika sayisi olusmadi: % (en az 6 olmali)', politika_sayisi;
  end if;

  raise notice 'Katki tablosu kuruldu: RLS acik, % politika', politika_sayisi;
end;
$$;
