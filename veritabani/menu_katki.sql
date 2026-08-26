-- ============================================================
-- Cebimde — menü ve ürün paylaşımı (fotoğraflı)
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir. sema.sql'den SONRA.
--
-- NEDEN VAR: menü fiyatları işletmelerin KENDİ sitelerinden derleniyor.
-- Ölçüldü: 35.852 mekanın 30.393'ünde (%84,8) ne site ne sosyal medya
-- var. O mekanların menüsüne uzaktan ulaşmanın yolu yok -- ama menüyü
-- gören biri var: o an orada oturan kullanıcı.
--
-- ÜÇ TABLONUN ÜÇÜ AYRI ŞEY, ve ayrı kalıyorlar:
--   paylasimlar  -> "3 kişi gittik, 850 verdik"   (HESAP, ödenen tutar)
--   menu_katkilari -> "Latte 95 ₺"                (LİSTE FİYATI, bir kalem)
--   yorumlar     -> "sessiz, bahçesi güzel"       (KANI)
-- Aynı tabloda toplamak, üç ayrı sorunun cevabını birbirine karıştırırdı.
--
-- FİYAT HESABINA GİRMİYOR -- şimdilik ve bilerek. Mekanın gösterilen
-- ortalaması fiyat_analiz.py'de, Python'da hesaplanıyor (kategori ayrımı,
-- ana ürün oranı, alt sınırlar). Tarayıcıda ikinci bir hesap yazmak, aynı
-- kuralı iki dilde tutmak ve ikisinin ayrışmasını beklemek olurdu -- bu
-- depoda en pahalı hatalar tam olarak öyle çıktı. Kullanıcı kalemleri
-- AYRI bir bölümde, "kullanıcıdan" etiketiyle gösteriliyor; onaylananlar
-- sonraki veri üretiminde boru hattına dışarıdan besleniyor.
--
-- ONAY ŞART. İki ayrı sebep var, ikisi de tek başına yeterli:
--   (1) yanlış fiyat, fiyatsızlıktan kötüdür (projenin ilk kuralı);
--   (2) fotoğraf yüklenebiliyor ve fotoğrafın ne olduğunu ancak bakan bilir.
-- ============================================================

create table if not exists public.menu_katkilari (
  id           bigint generated always as identity primary key,
  -- Kullanıcı silinirse kayıt kalır ama sahipsizleşir: yayımlanmış fiyat
  -- kişiye değil mekana bağlı. (paylasimlar ve katkilar ile aynı kural.)
  kullanici    uuid references auth.users(id) on delete set null,
  mekan_id     text not null check (char_length(mekan_id) between 1 and 80),
  il           text check (char_length(il) = 2),
  mekan_ad     text not null check (char_length(mekan_ad) between 2 and 200),

  -- Ürün adı ve fiyatı. İKİSİ DE BOŞ OLABİLİR: menünün tamamını
  -- fotoğraflayan biri 20 kalemi elle yazmak zorunda kalmasın.
  urun         text    check (urun is null or char_length(urun) between 2 and 80),
  -- Üst sınır 100.000: bir menü kaleminin fiyatı. paylasimlar'daki
  -- 1.000.000 bir HESABIN tavanı; kalem fiyatı o kadar olmaz.
  fiyat        numeric(10,2) check (fiyat is null or (fiyat > 0 and fiyat <= 100000)),

  -- Depolama kovasındaki YOL, resmin kendisi değil.
  foto         text    check (foto is null or char_length(foto) between 3 and 300),

  durum        text not null default 'bekliyor'
               check (durum in ('bekliyor','onaylandi','reddedildi')),
  olusturuldu  timestamptz not null default now(),

  -- Ya kalem (ad + fiyat birlikte), ya fotoğraf. Hiçbiri yoksa kayıt bir
  -- şey söylemiyor; adı olup fiyatı olmayan kalem de öyle.
  constraint menu_katkilari_dolu_check check (
    (urun is not null and fiyat is not null) or foto is not null
  )
);

comment on table public.menu_katkilari is
  'Kullanicidan gelen menu kalemi ve/veya menu fotografi. Onaydan gecmeden yayina girmez. Fiyat ORTALAMASINA girmez.';

create index if not exists menu_katkilari_durum_idx
  on public.menu_katkilari (durum, olusturuldu desc);
create index if not exists menu_katkilari_kullanici_idx
  on public.menu_katkilari (kullanici, olusturuldu desc);
create index if not exists menu_katkilari_mekan_idx
  on public.menu_katkilari (mekan_id) where durum = 'onaylandi';

-- Aynı kişi aynı mekanın aynı ürünü için sırada bekleyen ikinci bir kayıt
-- açamaz. Reddedildikten sonra düzeltip tekrar gönderebilir; onaylandıktan
-- sonra da gönderebilir (fiyat zamanla değişir). Kısıt yalnız KUYRUĞU
-- koruyor: tek yönetici aynı işin iki kopyasını görmesin.
create unique index if not exists menu_katkilari_tek_bekleyen_idx
  on public.menu_katkilari (kullanici, mekan_id, urun)
  where durum = 'bekliyor' and kullanici is not null and urun is not null;

-- Günlük gönderim sınırı: fonksiyon sema.sql'de, aynı kural dört kuyruğu
-- birden koruyor. Tekil kısıt yalnız AYNI ürünün tekrarını durduruyor;
-- farklı ürünlerle sınırsız kayıt açmayı durdurmuyordu.
drop trigger if exists menu_katki_gunluk_sinir on public.menu_katkilari;
create trigger menu_katki_gunluk_sinir
  before insert on public.menu_katkilari
  for each row execute function public.gunluk_gonderim_siniri();

-- ============================================================
-- RLS
-- ============================================================
alter table public.menu_katkilari enable row level security;

drop policy if exists "menu katki onaylanmis herkese acik" on public.menu_katkilari;
create policy "menu katki onaylanmis herkese acik" on public.menu_katkilari
  for select using (durum = 'onaylandi' or kullanici = auth.uid() or public.yonetici_mi());

-- Kullanıcı YALNIZ 'bekliyor' durumuyla yazabilir: durumu kendi
-- belirleyebilseydi onay şartı anlamsız olurdu.
drop policy if exists "menu katki kendi ekler" on public.menu_katkilari;
create policy "menu katki kendi ekler" on public.menu_katkilari
  for insert with check (kullanici = auth.uid() and durum = 'bekliyor');

drop policy if exists "menu katki kendi siler" on public.menu_katkilari;
create policy "menu katki kendi siler" on public.menu_katkilari
  for delete using (kullanici = auth.uid());

drop policy if exists "menu katki yonetici karar verir" on public.menu_katkilari;
create policy "menu katki yonetici karar verir" on public.menu_katkilari
  for update using (public.yonetici_mi()) with check (public.yonetici_mi());

drop policy if exists "menu katki yonetici siler" on public.menu_katkilari;
create policy "menu katki yonetici siler" on public.menu_katkilari
  for delete using (public.yonetici_mi());

-- ============================================================
-- Sütun yetkisi — kimin kim olduğu tarayıcıya inmiyor
--
-- Gerekçe sema.sql'in aynı başlığı altında yazılı. Burada ayrıca kritik:
-- bu tablo mekan + fiyat + FOTOĞRAF taşıyor. uuid'yi yanına koymak, bir
-- kişinin nereye gidip ne fotoğrafladığını tek sorguda toplardı.
-- ============================================================
revoke select on public.menu_katkilari from anon, authenticated;
grant  select (id, mekan_id, mekan_ad, il, urun, fiyat, foto, durum, olusturuldu)
  on public.menu_katkilari to anon, authenticated;

-- ============================================================
-- Bir mekanın onaylı menü katkıları
--
-- Yazarın ADI DÖNMÜYOR ve bu bilerek: yorumda "kim söylüyor" bilgi taşır
-- (19 yaşındaki öğrenci ile 45 yaşındaki mühendis aynı yeri farklı bulur),
-- fiyatta taşımaz -- 95 ₺, kim yazdıysa 95 ₺. Adı eklemek, hiçbir soruyu
-- cevaplamadan bir kişiyi bir mekana bağlamak olurdu.
-- ============================================================
create or replace function public.mekan_menu_katkilari(p_mekan_id text)
returns table (
  id          bigint,
  urun        text,
  fiyat       numeric,
  foto        text,
  olusturuldu timestamptz
)
language sql
stable
security definer
set search_path = public
as $$
  select k.id, k.urun, k.fiyat, k.foto, k.olusturuldu
  from public.menu_katkilari k
  where k.mekan_id = p_mekan_id and k.durum = 'onaylandi'
  order by k.olusturuldu desc
  limit 200;
$$;
revoke all on function public.mekan_menu_katkilari(text) from public;
grant execute on function public.mekan_menu_katkilari(text) to anon, authenticated;

-- ============================================================
-- Fotoğraf deposu
--
-- Yerel Postgres'te "storage" şeması yok; tamamı korumalı.
--
-- EXIF NOTU: yüklenen dosya tarayıcıda yeniden kodlanıyor (ortak.js →
-- resimHazirla) ve bu sırada EXIF tamamen düşüyor. Sebebi somut: telefon
-- fotoğrafı GPS koordinatı, çekim saati ve cihaz modeli taşır. Bu projede
-- ham IP bile saklanmıyor, günlük yenilenen bir özete çevriliyor;
-- kullanıcının evinin koordinatını bir menü fotoğrafının içinde yayımlamak
-- o özenle çelişirdi. Sunucu tarafı bunu DOĞRULAYAMIYOR (Storage dosyayı
-- ayrıştırmıyor), o yüzden burada yazılı: kural istemcide ve
-- test_tarayici.mjs onu ölçüyor.
-- ============================================================
do $$
begin
  if not exists (select 1 from information_schema.schemata where schema_name = 'storage') then
    raise notice 'storage semasi yok (yerel Postgres): menu kovasi atlandi';
    return;
  end if;

  insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
  values ('menu', 'menu', true, 3145728, array['image/jpeg','image/webp'])
  on conflict (id) do update
    set public = true,
        -- 3 MB. Istemci zaten kucultup yeniden kodluyor; bu, o adim
        -- atlanirsa diye duran ikinci siniri.
        file_size_limit = 3145728,
        -- PNG YOK: istemci JPEG/WebP uretiyor ve PNG'de metin fotografi
        -- gereksiz buyuk oluyor. Dar tutmak, kabul edilen bicim sayisini
        -- dusurdugu icin ayristirici yuzeyi de daraltiyor.
        allowed_mime_types = array['image/jpeg','image/webp'];

  execute 'drop policy if exists "menu foto herkes okur" on storage.objects';
  execute $p$create policy "menu foto herkes okur" on storage.objects
             for select using (bucket_id = 'menu')$p$;

  -- Yazma YALNIZ kendi klasörüne; klasör adı kullanıcının uuid'si.
  -- Böyle olmasa biri başkasının fotoğrafını ezebilirdi.
  execute 'drop policy if exists "menu foto kendi yazar" on storage.objects';
  execute $p$create policy "menu foto kendi yazar" on storage.objects
             for insert to authenticated
             with check (bucket_id = 'menu'
                         and (storage.foldername(name))[1] = auth.uid()::text)$p$;

  execute 'drop policy if exists "menu foto kendi siler" on storage.objects';
  execute $p$create policy "menu foto kendi siler" on storage.objects
             for delete to authenticated
             using (bucket_id = 'menu'
                    and (storage.foldername(name))[1] = auth.uid()::text)$p$;

  -- GUNCELLEME POLITIKASI BILEREK YOK. Onaylanmis bir fotografin uzerine
  -- yazilabilseydi, onaydan gecen resim ile yayindaki resim ayri seyler
  -- olabilirdi -- onayin tamami anlamsizlasirdi. Degistirmek isteyen
  -- siler ve yeniden gonderir; yeni kayit yeniden onaydan gecer.
end $$;

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

  if not exists (select 1 from pg_tables where schemaname = 'public'
                 and tablename = 'menu_katkilari' and rowsecurity = true) then
    raise exception 'RLS acik degil: menu_katkilari';
  end if;

  select count(*) into n from pg_policies
   where schemaname = 'public' and tablename = 'menu_katkilari';
  if n < 5 then
    raise exception 'menu katki politikalari eksik: % (en az 5 olmali)', n;
  end if;

  if has_column_privilege('anon', 'public.menu_katkilari', 'kullanici', 'SELECT') then
    raise exception 'anon menu_katkilari.kullanici sutununu okuyabiliyor';
  end if;

  raise notice 'Menu katkisi kuruldu: RLS acik, % politika, kimlik sutunu kapali', n;
end;
$$;
