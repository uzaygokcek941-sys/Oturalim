-- ============================================================
-- Oturalım — Supabase taklidi (yalnız TEST icin)
--
-- Supabase'in kurulum SQL'lerinin dayandigi seyleri bos bir Postgres'te
-- kurar: auth semasi, auth.uid(), anon/authenticated rolleri ve varsayilan
-- yetkiler. Boylece RLS politikalari gercek rollerle sinanabiliyor.
--
-- BUNU SUPABASE'E YAPISTIRMA -- orada hepsi zaten var.
-- Kullanimi: veritabani/sahiplenme_test.sql basligindaki adimlar.
-- ============================================================
create extension if not exists pgcrypto;
create schema if not exists auth;
create table if not exists auth.users (
  id uuid primary key default gen_random_uuid(),
  raw_user_meta_data jsonb default '{}'::jsonb
);
create or replace function auth.uid() returns uuid
  language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub', true),'')::uuid $$;
do $$ begin
  if not exists (select 1 from pg_roles where rolname='anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname='authenticated') then create role authenticated nologin; end if;
end $$;
grant usage on schema public to anon, authenticated;
-- auth semasi da erisilebilir olmali. Supabase'de oyle; burada EKSIKTI ve
-- sonucu sessizdi: auth.uid() cagiran her sey "permission denied for schema
-- auth" veriyordu. sahiplenme_test.sql 6. adimda patliyor, yani 11 davranis
-- kontrolunun ALTISI hic kosmuyordu. Daha kotusu 2. adim ("kullanici
-- sahiplik tablosuna dogrudan yazamaz") YANLIS SEBEPTEN geciyordu:
-- yazmayi engelleyen sey politika degil, eksik yetkiydi. Yetki verildikten
-- sonra tekrar olculdu -- adim yine geciyor, bu kez politika sayesinde.
grant usage on schema auth to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;
grant select on auth.users to anon, authenticated;
alter default privileges in schema public grant all on tables to anon, authenticated;
alter default privileges in schema public grant all on functions to anon, authenticated;
alter default privileges in schema public grant all on sequences to anon, authenticated;
