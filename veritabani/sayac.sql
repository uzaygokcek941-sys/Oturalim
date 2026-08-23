-- ============================================================
-- Oturalım — işletme sayfası görüntülenme sayacı
--
-- Supabase panelinde SQL Editor'e yapıştırıp bir kez çalıştır.
-- Tekrar çalıştırılabilir: her şey "if not exists" / "or replace".
-- sema.sql'den SONRA çalıştırılmalı.
--
-- NEDEN VAR: işletmeye "sayfanı bu ay 47 kişi gördü" diyebilmek için.
-- O cümle satışın tamamını taşıyor, bu yüzden sayı ŞİŞİRİLEBİLİR OLMAMALI.
-- Şişirilebilir bir sayaç yanlış fiyattan kötüdür: fiyatta yanılırsın,
-- burada yalan söylemiş olursun.
--
-- İLK SÜRÜMÜN AÇIĞI (kapatıldı): cihaz kimliğini TARAYICI üretiyor ve
-- doğrudan insert ediyordu. Birincil anahtar yalnız masum yenilemeyi
-- durduruyordu; rastgele uuid üreten on satırlık bir betik herhangi bir
-- mekanın sayısını istediği kadar artırabilir, aynı yolla ücretsiz katman
-- veritabanını da doldurabilirdi. Yani dosyanın kendi kuralı tutmuyordu.
--
-- ŞİMDİ: istemci kimlik GÖNDERMİYOR. Kimlik sunucuda, isteğin kendi
-- başlıklarından türetiliyor (IP + tarayıcı + gün + tuz) ve tabloya
-- yalnız özeti giriyor. Doğrudan insert kapalı; tek yol mekan_goruldu().
-- Aynı IP bir mekana günde en fazla 1 sayı ekleyebiliyor.
--
-- HÂLÂ DOĞRU OLMAYAN YER, açıkça: çok sayıda IP'si olan biri (botnet,
-- vekil havuzu) sayıyı yine şişirebilir. Bu, tek kişilik ve sunucusuz bir
-- yapıda kapatılabilecek bir şey değil; kapatıldığı iddia edilmiyor.
--
-- TERS YÖNDE HATA: Türkiye'de mobil operatörler CGNAT kullanıyor, yani
-- aynı IP'nin arkasında çok kişi olabiliyor. Tarayıcı başlığı bunu bir
-- miktar ayırıyor ama tamamen değil. Sonuç: sayaç gerçeği OLDUĞUNDAN AZ
-- gösterme eğiliminde. Bilerek bu yönde: işletmeye eksik söylemek, fazla
-- söylemekten iyidir.
--
-- KVKK: ham IP HİÇBİR YERDE saklanmıyor, yalnız geri döndürülemez özeti.
-- Özet her gün yenileniyor (tarih girdiye dahil), o yüzden aynı kişinin
-- iki ayrı gündeki ziyareti birbirine bağlanamaz; kalıcı ziyaretçi
-- kimliği yok, davranış profili çıkarılamaz. Tarayıcıda da artık hiçbir
-- şey saklanmıyor (eski sürüm localStorage kullanıyordu).
-- ============================================================

-- ---------- Tuz ----------
-- Özetin girdisine karışan gizli sabit. Tablo okunamıyor (RLS açık,
-- politika yok), fonksiyon security definer olduğu için okuyabiliyor.
-- Tuz olmasa, goruntulenme satırlarını bir şekilde ele geçiren biri
-- IP uzayını tarayıp ziyaretçi IP'lerini geri çözebilirdi.
create table if not exists public.sayac_tuz (
  tek  boolean primary key default true check (tek),
  tuz  uuid not null default gen_random_uuid()
);

insert into public.sayac_tuz (tek) values (true) on conflict (tek) do nothing;

alter table public.sayac_tuz enable row level security;
revoke all on table public.sayac_tuz from anon, authenticated;
-- (politika BİLEREK yok: RLS açıkken politikasız tabloyu kimse okuyamaz)

-- ---------- Tablo ----------
-- Bir ziyaretçi izi, bir mekan, bir gün = tek satır. Sayfayı 40 kez
-- yenilemek sayıyı artırmaz; birincil anahtar buna izin vermiyor.
create table if not exists public.goruntulenme (
  mekan_id  text not null check (char_length(mekan_id) between 1 and 80),
  gun       date not null default current_date,
  cihaz     uuid not null,
  primary key (mekan_id, gun, cihaz)
);

comment on table public.goruntulenme is
  'Isletme sayfasi tekil gunluk goruntulenme. cihaz = sunucuda uretilen gunluk ziyaretci izi; ham IP saklanmaz, gunler arasi baglanamaz.';

create index if not exists goruntulenme_mekan_gun_idx
  on public.goruntulenme (mekan_id, gun desc);

alter table public.goruntulenme enable row level security;

-- ---------- Yetkiler ----------
-- Doğrudan yazma KAPATILDI: açığın kaynağı buydu. Politikayı düşürmek tek
-- başına yetmez, tablo üzerindeki GRANT de geri alınıyor (Supabase yeni
-- tablolara anon/authenticated için varsayılan yetki verir).
drop policy if exists goruntulenme_ekle on public.goruntulenme;
revoke all on table public.goruntulenme from anon, authenticated;

-- Okuma da yok. Cihaz izleri listelenebilseydi "bugün bu mekana kimler
-- baktı" çıkarılabilirdi. Sayı yalnız aşağıdaki toplayıcıdan okunur.

-- ---------- Ziyaretçi izi ----------
-- İstemcinin dokunamadığı tek şey isteğin kendi başlıkları. PostgREST
-- bunları request.headers ayarına koyuyor; fonksiyon oradan okuyor.
-- x-forwarded-for zincirinin İLK adresi gerçek istemci, gerisi vekiller.
create or replace function public.ziyaretci_izi()
returns uuid
language plpgsql
security definer
set search_path = public
stable
as $$
declare
  basliklar json;
  ip        text;
  tarayici  text;
  gizli     uuid;
begin
  begin
    basliklar := nullif(current_setting('request.headers', true), '')::json;
  exception when others then
    basliklar := null;
  end;

  ip := btrim(split_part(coalesce(basliklar->>'x-forwarded-for', ''), ',', 1));
  -- IP okunamadıysa SAYMA. Uydurma bir sabite düşmek, o istekleri tek bir
  -- hayali ziyaretçide toplar ve sayıyı sessizce bozardı.
  if ip = '' then
    return null;
  end if;

  tarayici := coalesce(basliklar->>'user-agent', '');
  select tuz into gizli from public.sayac_tuz limit 1;

  return md5(ip || '|' || tarayici || '|' || current_date::text || '|' ||
             coalesce(gizli::text, ''))::uuid;
end;
$$;

revoke all on function public.ziyaretci_izi() from public, anon, authenticated;

-- ---------- Sayma ----------
-- Tek yazma yolu. Parametresi yalnız mekan; kimlik istemciden GELMİYOR.
create or replace function public.mekan_goruldu(p_mekan_id text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  iz uuid;
begin
  if p_mekan_id is null or char_length(p_mekan_id) not between 1 and 80 then
    return;
  end if;

  iz := public.ziyaretci_izi();
  if iz is null then
    return;
  end if;

  -- Aynı gün ikinci kez bakınca çakışır; hata değil, beklenen durum.
  insert into public.goruntulenme (mekan_id, gun, cihaz)
  values (p_mekan_id, current_date, iz)
  on conflict do nothing;
end;
$$;

revoke all on function public.mekan_goruldu(text) from public;
grant execute on function public.mekan_goruldu(text) to anon, authenticated;

comment on function public.mekan_goruldu is
  'Sayfa goruntulenmesini kaydeder. Ziyaretci kimligi sunucuda uretilir, istemci veremez.';

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

-- ============================================================
-- Kendini kontrol — bu blok hata vermeden geçmeli
-- ============================================================
do $$
declare
  n int;
begin
  -- Doğrudan yazma yolu gerçekten kapalı mı? Açık kalırsa dosyanın
  -- tamamının anlamı kalmıyor, o yüzden burada sınanıyor.
  select count(*) into n from pg_policies
  where schemaname = 'public' and tablename = 'goruntulenme';
  if n > 0 then
    raise exception 'goruntulenme uzerinde politika kalmis: % (hicbiri olmamali)', n;
  end if;

  if has_table_privilege('anon', 'public.goruntulenme', 'INSERT') then
    raise exception 'anon hala goruntulenme tablosuna yazabiliyor';
  end if;
  if has_table_privilege('anon', 'public.goruntulenme', 'SELECT') then
    raise exception 'anon hala goruntulenme tablosunu okuyabiliyor';
  end if;
  if has_table_privilege('anon', 'public.sayac_tuz', 'SELECT') then
    raise exception 'anon tuzu okuyabiliyor';
  end if;

  if not has_function_privilege('anon', 'public.mekan_goruldu(text)', 'EXECUTE') then
    raise exception 'anon mekan_goruldu cagiramiyor, sayac hic islemez';
  end if;
  if has_function_privilege('anon', 'public.ziyaretci_izi()', 'EXECUTE') then
    raise exception 'anon ziyaretci_izi cagirabiliyor';
  end if;

  raise notice 'Sayac kuruldu: dogrudan yazma kapali, kimlik sunucuda uretiliyor';
end;
$$;
