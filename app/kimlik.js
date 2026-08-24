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
  /* Sahiplenme. "kod gecersiz" bilerek tek mesaj: gecersiz kod ile
     kullanilmis/suresi gecmis kodu ayirt ettirmek, gecerli kod aramak
     icin bir sinyal olurdu. Istemci de o ayrimi uydurmuyor. */
  if (m.includes("kod gecersiz"))
    return "Kod geçersiz, süresi dolmuş ya da daha önce kullanılmış.";
  if (m.includes("zaten sahiplenilmis"))
    return "Bu işletme başka bir hesap tarafından sahiplenilmiş. Sana ait olduğunu düşünüyorsan bildir.";
  if (m.includes("sahiplenme icin giris"))
    return "Sahiplenmek için önce giriş yap.";
  if (m.includes("violates check constraint") || m.includes("check constraint"))
    return "Girdiğin değerlerden biri kabul edilmedi. Alanları gözden geçir.";
  if (m.includes("value too long"))
    return "Girdiğin metin çok uzun.";
  return (e && e.message) ? e.message : "Beklenmeyen bir hata oldu.";
}

/* YEREL gun. ortak.js'te ayni islev bugunYerel() adiyla var; kimlik.js bir
   ES modulu ve ortak.js'siz de import edilebiliyor, o yuzden kopya duruyor.
   Ikisinin ayrismasini test.py denetliyor ("bugun ayni hesaplaniyor").
   toISOString() OLMAZ: UTC verir, Turkiye kalici UTC+3, gece yarisindan
   sonraki uc saatte dunun tarihini yazardi. */
function bugunYerel(d){
  d = d || new Date();
  return d.getFullYear() + "-" +
         String(d.getMonth() + 1).padStart(2, "0") + "-" +
         String(d.getDate()).padStart(2, "0");
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
      tarih: p.tarih || bugunYerel(),
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

  /* ---------- işletme sahipliği (Faz 4) ----------
     Kod sahada elden veriliyor; ne kanitladigi sahiplenme.sql'in basinda
     yazili: FIZIKSEL OLARAK ORADA BULUNMAK, tapu degil. Bu yuzden yetki
     sinirli ve sahiplik geri alinabilir.

     Tablolar kurulu degilse (sahiplenme.sql calistirilmamissa) sayfa
     cokmesin: okuma bos doner, yazma anlasilir cumle verir. */
  async sahiplikTalep(kod){
    if (!sb) throw new Error("Giriş sistemi kurulu değil.");
    if (!oturum) throw new Error("Sahiplenmek için önce giriş yap.");
    const temiz = String(kod || "").replace(/[^A-Za-z0-9]/g, "").toUpperCase();
    /* Istemci tarafi on eleme: bos ya da kisa kodu sunucuya hic gondermeyip
       kullaniciya aninda soyluyoruz. Asil karar yine sunucuda. */
    if (temiz.length < 6) throw new Error("Kod eksik görünüyor, karttaki 8 haneyi yaz.");
    const { data, error } = await sb.rpc("sahiplenme_kodu_kullan", { p_kod: temiz });
    if (error) throw new Error(hataMetni(error));
    /* Fonksiyon tablo donuyor; tek satir bekleniyor. */
    const k = Array.isArray(data) ? data[0] : data;
    if (!k) throw new Error("Kod kabul edildi ama işletme bilgisi gelmedi.");
    return { mekanId: k.mekan_id, il: k.il, mekanAd: k.mekan_ad };
  },

  async sahipliklerim(){
    if (!sb || !oturum) return [];
    /* kullanici sutununa gore SUZMUYORUZ: RLS zaten yalniz kendi
       satirlarini veriyor ve sutun artik tarayiciya kapali (sema.sql
       "Sutun yetkisi" basligi). Postgres'te WHERE de sutun yetkisi ister,
       yani filtre kalsaydi liste bos donerdi. */
    const { data, error } = await sb.from("sahiplik")
      .select("id, mekan_id, mekan_ad, il, dogrulandi, durum")
      .order("dogrulandi", { ascending: false });
    if (error){ console.error("sahipliklerim:", error.message); return []; }
    return data || [];
  },

  /* Mekan sahiplenilmis mi. Giris GEREKMIYOR: isletme sayfasi bu rozeti
     herkese gosteriyor. Sahibin KIMLIGI dondurulmuyor -- gorunur olan
     bilgi "dogrulanmis", "kim dogruladi" degil. */
  /* Uc deger doner: true (sahiplenilmis), false (sahiplenilmemis),
     null (SAHIPLENME KURULU DEGIL).

     Ucuncusu sart. Onceden hata durumunda false donuyordu, yani
     sahiplenme.sql calistirilmamis bir kurulumda mekan "sahiplenilmemis"
     gorunuyor ve isletme sayfasi kod formunu aciyordu -- kullanici kodu
     giriyor, RPC yok, anlamsiz bir hata aliyordu. Calismayan bir kutu
     gostermek, hic gostermemekten kotu (katki formunda ayni kural). */
  async mekanSahiplenilmis(mekanId){
    if (!sb) return null;
    const { data, error } = await sb.from("sahiplik")
      .select("id").eq("mekan_id", mekanId).eq("durum", "aktif").limit(1);
    if (error){
      const m = String(error.message || "").toLowerCase();
      /* Tablo yok / semada gorunmuyor: ozellik kurulu degil. */
      if (m.includes("does not exist") || m.includes("schema cache") ||
          error.code === "42P01" || error.code === "PGRST205") return null;
      console.error("sahiplik:", error.message);
      return null;
    }
    return !!(data && data.length);
  },

  /* Kullanici kendi sahipligini birakabilir: yanlis mekani sahiplenen ya da
     isletmeyi devreden kisi yoneticiyi beklemesin. */
  async sahiplikBirak(id){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const { error } = await sb.from("sahiplik").delete().eq("id", id);
    if (error) throw new Error(hataMetni(error));
  },

  async sahiplikYonetimListesi(){
    if (!sb || !oturum) return [];
    const { data, error } = await sb.from("sahiplik")
      .select("id, mekan_id, mekan_ad, il, dogrulandi, durum, iptal_notu")
      .order("dogrulandi", { ascending: false }).limit(200);
    if (error){ console.error("sahiplik yonetim:", error.message); return []; }
    return data || [];
  },

  /* Iptal SILME degil: kayit duruyor, durum 'iptal' oluyor. Kimin neyi
     ne zaman sahiplendigi ve neden geri alindigi kaybolmasin. */
  async sahiplikIptal(id, notu){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const { error } = await sb.from("sahiplik")
      .update({ durum: "iptal", iptal_notu: String(notu || "").slice(0, 300) || null })
      .eq("id", id);
    if (error) throw new Error(hataMetni(error));
  },

  /* Bir mekanin fis ozeti: kac fis, kac FARKLI kisi, kisi basi medyan.
     Onceden isletme.html satirlari cekip tarayicida sayiyordu ve bunun
     icin `kullanici` sutununu okuyordu -- yani her ziyaretci butun
     uuid'leri goruyordu. Sayim artik sunucuda (sema.sql mekan_fis_ozeti);
     kimlikler disari cikmiyor.

     Esik karari BURADA DEGIL, isletme.html'de (FIS_ESIK): fonksiyon ham
     sayilari veriyor, "gosterilsin mi" kurali tek yerde dursun. */
  async fisOzeti(mekanId){
    if (!sb) return null;
    const { data, error } = await sb.rpc("mekan_fis_ozeti", { p_mekan_id: mekanId });
    if (error){ console.error("fis ozeti:", error.message); return null; }
    const o = Array.isArray(data) ? data[0] : data;
    return o ? { fis: +o.fis || 0, kisi: +o.kisi || 0,
                 medyan: o.medyan == null ? null : +o.medyan } : null;
  },

  /* ---------- yönetim ---------- */
  async yonetimListesi(durum){
    if (!sb || !oturum) return [];
    let s = sb.from("paylasimlar")
      .select("id, mekan_id, mekan_ad, il, tutar, kisi, tarih, aciklama, durum, olusturuldu")
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
