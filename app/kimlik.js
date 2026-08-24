/* ============================================================
   Oturalım — kimlik ve hesap katmanı  (ES modülü)

   Supabase ile kayıt / giriş / oturum, favoriler, fiyat paylaşımı
   ve yönetici kararları. Tüm yetki kontrolü veritabanındaki RLS
   politikalarında; buradaki kod yalnızca arayüzü sürer.

   Yapılandırma boşsa "kapalı mod": hata fırlatmaz, Kimlik.acik = false
   döner ve sayfalar giriş özelliklerini gizler.
   ============================================================ */

const AYAR = (window.OTURALIM || {});
const ACIK = Boolean(AYAR.supabaseUrl && AYAR.supabaseAnahtar);

let sb = null;
let oturum = null;
let profil = null;
const dinleyiciler = new Set();

/* ---------- kurulum ---------- */
async function kur(){
  if (!ACIK) return false;
  const { createClient } = await import("https://esm.sh/@supabase/supabase-js@2.45.4");
  sb = createClient(AYAR.supabaseUrl, AYAR.supabaseAnahtar, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
  });
  const { data } = await sb.auth.getSession();
  oturum = data.session;
  if (oturum) profil = await profilGetir();
  sb.auth.onAuthStateChange(async (_olay, yeni) => {
    oturum = yeni;
    profil = yeni ? await profilGetir() : null;
    duyur();
  });
  return true;
}

function duyur(){
  const durum = { girisli: !!oturum, kullanici: oturum?.user || null, profil };
  dinleyiciler.forEach(f => { try { f(durum); } catch (e) { console.error(e); } });
}

/* Türkçe hata metinleri: Supabase İngilizce ve teknik konuşuyor,
   kullanıcıya ne yapacağını söylemiyor. */
function hataMetni(e){
  const m = ((e && (e.message || e.error_description)) || "").toLowerCase();
  if (m.includes("invalid login credentials"))   return "E-posta veya parola hatalı.";
  if (m.includes("email not confirmed"))         return "Önce e-postandaki doğrulama bağlantısına tıkla.";
  if (m.includes("already registered") ||
      m.includes("already been registered"))     return "Bu e-posta zaten kayıtlı. Giriş yapmayı dene.";
  if (m.includes("password should be at least")) return "Parola en az 8 karakter olmalı.";
  if (m.includes("rate limit") || m.includes("too many"))
    return "Çok fazla deneme oldu. Birkaç dakika sonra tekrar dene.";
  /* Veritabanindaki gunluk gonderim siniri (sema.sql). Ham SQL cumlesi
     kullaniciya bir sey anlatmiyor; ne oldugunu ve ne zaman gececegini
     soyleyen bir metin veriliyor. */
  if (m.includes("gunluk gonderim siniri"))
    return "Bugünlük gönderim sınırına ulaştın. Yarın devam edebilirsin.";
  if (m.includes("unique") || m.includes("duplicate"))
    return "Bu mekan için bugün zaten bir paylaşım göndermişsin.";
  if (m.includes("failed to fetch") || m.includes("networkerror"))
    return "Sunucuya ulaşılamadı. İnternet bağlantını kontrol et.";
  /* Veritabani kisiti: istemci ayni sinirlari zaten kontrol ediyor, yani
     buraya ancak istemci atlanirsa ya da iki taraf ayrisirsa gelinir.
     Ikisinde de kullaniciya ham SQL cumlesi gostermenin anlami yok. */
  if (m.includes("violates check constraint") || m.includes("check constraint"))
    return "Girdiğin değerlerden biri kabul edilmedi. Alanları gözden geçir.";
  if (m.includes("value too long"))
    return "Girdiğin metin çok uzun.";
  return (e && e.message) ? e.message : "Beklenmeyen bir hata oldu.";
}

/* ---------- profil ---------- */
async function profilGetir(){
  if (!sb || !oturum) return null;
  const { data, error } = await sb.from("profiller")
    .select("id, ad, yonetici").eq("id", oturum.user.id).maybeSingle();
  if (error){ console.error("profil:", error.message); return null; }
  return data;
}

/* ============================================================
   Dışa açılan yüzey
   ============================================================ */
const Kimlik = {
  acik: ACIK,
  hazir: null,          // kur() sözü; sayfalar bunu bekler

  get girisli(){ return !!oturum; },
  get kullanici(){ return oturum?.user || null; },
  get profil(){ return profil; },
  get yonetici(){ return !!(profil && profil.yonetici); },

  /* durum değişince haber ver; abone olur olmaz bir kez çağrılır */
  izle(f){
    dinleyiciler.add(f);
    f({ girisli: !!oturum, kullanici: oturum?.user || null, profil });
    return () => dinleyiciler.delete(f);
  },

  /* ---------- kimlik ---------- */
  async kayit(eposta, parola, ad){
    if (!sb) throw new Error("Giriş sistemi kurulu değil.");
    const { data, error } = await sb.auth.signUp({
      email: eposta, password: parola,
      options: { data: { ad: (ad || "").trim() },
                 emailRedirectTo: new URL("giris.html", location.href).href }
    });
    if (error) throw new Error(hataMetni(error));
    /* E-posta doğrulaması açıksa oturum gelmez; çağıran bunu
       "posta kutunu kontrol et" ekranı için kullanıyor. */
    return { dogrulamaBekliyor: !data.session };
  },

  async giris(eposta, parola){
    if (!sb) throw new Error("Giriş sistemi kurulu değil.");
    const { error } = await sb.auth.signInWithPassword({ email: eposta, password: parola });
    if (error) throw new Error(hataMetni(error));
  },

  async cikis(){
    if (!sb) return;
    await sb.auth.signOut();
    oturum = null; profil = null; duyur();
  },

  async parolaSifirlaIste(eposta){
    if (!sb) throw new Error("Giriş sistemi kurulu değil.");
    const { error } = await sb.auth.resetPasswordForEmail(eposta,
      { redirectTo: new URL("giris.html?yenile=1", location.href).href });
    if (error) throw new Error(hataMetni(error));
  },

  async parolaDegistir(yeni){
    if (!sb) throw new Error("Giriş sistemi kurulu değil.");
    const { error } = await sb.auth.updateUser({ password: yeni });
    if (error) throw new Error(hataMetni(error));
  },

  async adDegistir(ad){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const { error } = await sb.from("profiller")
      .update({ ad: String(ad).trim() }).eq("id", oturum.user.id);
    if (error) throw new Error(hataMetni(error));
    profil = await profilGetir();
    duyur();
  },

  /* ---------- favoriler ---------- */
  async favoriler(){
    if (!sb || !oturum) return [];
    const { data, error } = await sb.from("favoriler")
      .select("mekan_id, il, mekan_ad, eklendi").order("eklendi", { ascending: false });
    if (error){ console.error("favoriler:", error.message); return []; }
    return data || [];
  },

  async favoriEkle(m, il){
    if (!sb || !oturum) throw new Error("Favori eklemek için giriş yap.");
    const { error } = await sb.from("favoriler").insert({
      kullanici: oturum.user.id, mekan_id: m.id, il, mekan_ad: m.ad
    });
    if (error && !String(error.message).toLowerCase().includes("duplicate"))
      throw new Error(hataMetni(error));
  },

  async favoriSil(mekanId){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const { error } = await sb.from("favoriler").delete().eq("mekan_id", mekanId);
    if (error) throw new Error(hataMetni(error));
  },

  /* ---------- fiyat paylaşımı ---------- */
  async paylasimGonder(p){
    if (!sb || !oturum) throw new Error("Paylaşım için giriş yap.");
    const { error } = await sb.from("paylasimlar").insert({
      kullanici: oturum.user.id,
      mekan_id: p.mekanId || null,
      mekan_ad: String(p.mekanAd).trim(),
      il: p.il || null,
      tutar: p.tutar,
      kisi: p.kisi,
      tarih: p.tarih || new Date().toISOString().slice(0, 10),
      aciklama: (p.aciklama || "").trim() || null,
      durum: "bekliyor"
    });
    if (error) throw new Error(hataMetni(error));
  },

  /* Onaylanmış paylaşımlar herkese açık — giriş gerekmiyor.
     Keşfet ekranı bunları mekan kartlarına işliyor. */
  async onaylanmisPaylasimlar(il){
    if (!sb) return [];
    let s = sb.from("paylasimlar")
      .select("mekan_id, mekan_ad, tutar, kisi, tarih")
      .eq("durum", "onaylandi")
      .order("tarih", { ascending: false })
      .limit(2000);
    if (il) s = s.eq("il", il);
    const { data, error } = await s;
    if (error){ console.error("onaylanmis:", error.message); return []; }
    return data || [];
  },

  async paylasimlarim(){
    if (!sb || !oturum) return [];
    const { data, error } = await sb.from("paylasimlar")
      .select("id, mekan_ad, il, tutar, kisi, tarih, durum, olusturuldu")
      .order("olusturuldu", { ascending: false });
    if (error){ console.error("paylasimlarim:", error.message); return []; }
    return data || [];
  },

  async paylasimSil(id){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const { error } = await sb.from("paylasimlar").delete().eq("id", id);
    if (error) throw new Error(hataMetni(error));
  },

  /* Ham Supabase istemcisi. Sayfaların kendi `createClient` çağrısını
     kurmasına gerek kalmasın diye açıldı: isletme.html üç ayrı yerde üç
     istemci kuruyordu, yani aynı CDN modülü üç kez içeri giriyordu ve sürüm
     bir yerde güncellenip diğerinde unutulabiliyordu. Tek yerden geliyor.
     `kur()` çalışmadıysa (yapılandırma boş) null döner — çağıran bunu
     "özellik kapalı" diye okur. Önce `await Kimlik.hazir`. */
  istemci(){ return sb; },

  /* ---------- eksik bilgi katkısı ----------
     Tablo kurulu değilse (katki.sql çalıştırılmamışsa) sayfa çökmesin:
     okuma boş dizi döner, yazma anlaşılır bir cümleyle hata verir. */
  async katkiGonder(k){
    if (!sb || !oturum) throw new Error("Katkı için giriş yap.");
    const { error } = await sb.from("katkilar").insert({
      kullanici: oturum.user.id,
      mekan_id: k.mekanId,
      il: k.il || null,
      mekan_ad: String(k.mekanAd).trim(),
      alan: k.alan,
      deger: String(k.deger).trim(),
      durum: "bekliyor"
    });
    if (!error) return;
    /* Tekil kısıt burada "aynı gün" değil "sırada bekleyen" demek;
       hataMetni'nin paylaşım cümlesi bu tabloda yanlış olurdu. */
    const m = String(error.message || "").toLowerCase();
    if (m.includes("unique") || m.includes("duplicate"))
      throw new Error("Bu bilgiyi zaten göndermişsin, sırada bekliyor.");
    throw new Error(hataMetni(error));
  },

  /* Onaylanmış katkılar herkese açık — giriş gerekmiyor.
     İşletme sayfası bunları OSM verisinin yanına işliyor. */
  async onaylanmisKatkilar(mekanId){
    if (!sb) return [];
    const { data, error } = await sb.from("katkilar")
      .select("alan, deger, olusturuldu")
      .eq("mekan_id", mekanId).eq("durum", "onaylandi")
      .order("olusturuldu", { ascending: false });
    if (error){ console.error("katkilar:", error.message); return []; }
    return data || [];
  },

  async katkilarim(){
    if (!sb || !oturum) return [];
    const { data, error } = await sb.from("katkilar")
      .select("id, mekan_id, mekan_ad, il, alan, deger, durum, olusturuldu")
      .order("olusturuldu", { ascending: false });
    if (error){ console.error("katkilarim:", error.message); return []; }
    return data || [];
  },

  async katkiSil(id){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const { error } = await sb.from("katkilar").delete().eq("id", id);
    if (error) throw new Error(hataMetni(error));
  },

  async katkiYonetimListesi(durum){
    if (!sb || !oturum) return [];
    let s = sb.from("katkilar")
      .select("id, mekan_id, mekan_ad, il, alan, deger, durum, olusturuldu")
      .order("olusturuldu", { ascending: false }).limit(200);
    if (durum) s = s.eq("durum", durum);
    const { data, error } = await s;
    if (error){ console.error("katki yonetim:", error.message); return []; }
    return data || [];
  },

  async katkiKarar(id, durum){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    if (!["onaylandi","reddedildi","bekliyor"].includes(durum))
      throw new Error("Geçersiz durum.");
    const { error } = await sb.from("katkilar").update({ durum }).eq("id", id);
    if (error) throw new Error(hataMetni(error));
  },

  /* ---------- yönetim ---------- */
  async yonetimListesi(durum){
    if (!sb || !oturum) return [];
    let s = sb.from("paylasimlar")
      .select("id, kullanici, mekan_id, mekan_ad, il, tutar, kisi, tarih, aciklama, durum, olusturuldu")
      .order("olusturuldu", { ascending: false }).limit(200);
    if (durum) s = s.eq("durum", durum);
    const { data, error } = await s;
    if (error){ console.error("yonetim:", error.message); return []; }
    return data || [];
  },

  async karar(id, durum){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    if (!["onaylandi","reddedildi","bekliyor"].includes(durum))
      throw new Error("Geçersiz durum.");
    const { error } = await sb.from("paylasimlar").update({ durum }).eq("id", id);
    if (error) throw new Error(hataMetni(error));
  }
};

/* ---------- doğrulama yardımcıları (saf, test edilebilir) ---------- */
export function epostaGecerli(e){
  return /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(String(e || "").trim());
}

export function parolaSorunu(p){
  p = String(p || "");
  if (p.length < 8) return "Parola en az 8 karakter olmalı.";
  if (!/[a-zA-Z]/.test(p)) return "Parola en az bir harf içermeli.";
  if (!/[0-9]/.test(p))    return "Parola en az bir rakam içermeli.";
  return null;
}

export function tutarSorunu(t){
  const n = Number(t);
  if (!Number.isFinite(n) || n <= 0) return "Tutar sıfırdan büyük olmalı.";
  if (n > 1000000) return "Tutar gerçekçi görünmüyor.";
  return null;
}

export function kisiSorunu(k){
  const n = Number(k);
  if (!Number.isInteger(n) || n < 1 || n > 30) return "Kişi sayısı 1 ile 30 arasında olmalı.";
  return null;
}

/* ---------- üst çubuktaki giriş bağlantısı ----------
   Her sayfa aynı kodu tekrarlamasın diye burada. */
function menuyuGuncelle(durum){
  document.querySelectorAll("[data-kimlik-menu]").forEach(yuva => {
    if (!ACIK){ yuva.innerHTML = ""; return; }
    yuva.innerHTML = durum.girisli
      ? '<a href="hesabim.html">Hesabım</a>' +
        (durum.profil && durum.profil.yonetici ? '<a href="yonetim.html">Yönetim</a>' : "")
      : '<a href="giris.html">Giriş</a>';
  });
}

window.Kimlik = Kimlik;
Kimlik.hazir = kur()
  .then(a => { Kimlik.izle(menuyuGuncelle); return a; })
  .catch(e => { console.error("Kimlik kurulamadı:", e); return false; });

export default Kimlik;
