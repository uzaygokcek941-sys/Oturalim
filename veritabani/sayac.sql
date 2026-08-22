-- ============================================================
-- Oturalım — işletme sayfası görüntülenme sayacı
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir: her şey "if not exists" / "or replace".
--
-- NEDEN VAR: işletmeye "sayfanı bu ay 47 kişi gördü" diyebilmek için.
-- O cümle satışın tamamını taşıyor, bu yüzden sayı ŞİŞİRİLEBİLİR OLMAMALI.
-- Şişirilebilir bir sayaç yanlış fiyattan kötüdür: fiyatta yanılırsın,
-- burada yalan söylemiş olursun.
--
-- KVKK: cihaz kimliği HER GÜN YENİLENİYOR (istemci tarafında). Aynı kişinin
-- iki ayrı gündeki ziyareti birbirine bağlanamaz; veritabanında kalıcı bir
-- ziyaretçi kimliği yok, davranış profili çıkarılamaz.
-- ============================================================

-- ---------- Tablo ----------
-- Bir cihaz, bir mekan, bir gün = tek satır. Sayfayı 40 kez yenilemek
-- sayıyı artırmaz; birincil anahtar buna izin vermiyor.
create table if not exists public.goruntulenme (
  mekan_id  text not null check (char_length(mekan_id) between 1 and 80),
  gun       date not null default current_date,
  cihaz     uuid not null,
  primary key (mekan_id, gun, cihaz)
);

comment on table public.goruntulenme is
  'Isletme sayfasi tekil gunluk goruntulenme. cihaz her gun yenilenir, gunler arasi baglanamaz.';

create index if not exists goruntulenme_mekan_gun_idx
  on public.goruntulenme (mekan_id, gun desc);

alter table public.goruntulenme enable row level security;

-- ---------- Politikalar ----------
-- Yazma: herkes ekleyebilir (giriş şartı yok, sayfa herkese açık) ama yalnız
-- BUGÜNÜN satırını -- geçmişe sayı basılamasın.
drop policy if exists goruntulenme_ekle on public.goruntulenme;
create policy goruntulenme_ekle on public.goruntulenme
  for insert to anon, authenticated
  with check (gun = current_date);

-- Okuma: hiç kimse ham satırı okuyamaz. Cihaz kimlikleri listelenebilseydi
-- "bugün bu mekana kimler baktı" çıkarılabilirdi. Sayı yalnız aşağıdaki
-- toplayıcı fonksiyondan okunur.
-- (select politikası BİLEREK yok: RLS açıkken politika yoksa okuma yok.)

-- ---------- Toplayıcı ----------
-- security definer: RLS'i atlayarak yalnız SAYIYI döndürür, satırı değil.
create or replace function public.mekan_sayaci(p_mekan_id text)
returns table (bugun integer, son30 integer, toplam integer, ilk_gun date)
language sql
security definer
set search_path = public
stable
as $$
  select
    count(*) filter (where gun = current_date)::int,
    count(*) filter (where gun > current_date - 30)::int,
    count(*)::int,
    min(gun)
  from public.goruntulenme
  where mekan_id = p_mekan_id;
$$;

revoke all on function public.mekan_sayaci(text) from public;
grant execute on function public.mekan_sayaci(text) to anon, authenticated;

comment on function public.mekan_sayaci is
  'Tek mekanin tekil goruntulenme sayilari. Ham satir donmez.';
