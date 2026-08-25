/* ============================================================
   Cebimde — kimlik ve hesap katmanı  (ES modülü)

   Supabase ile kayıt / giriş / oturum, favoriler, fiyat paylaşımı
   ve yönetici kararları. Tüm yetki kontrolü veritabanındaki RLS
   politikalarında; buradaki kod yalnızca arayüzü sürer.

   Yapılandırma boşsa "kapalı mod": hata fırlatmaz, Kimlik.acik = false
   döner ve sayfalar giriş özelliklerini gizler.
   ============================================================ */

const AYAR = (window.CEBIMDE || {});
const ACIK = Boolean(AYAR.supabaseUrl && AYAR.supabaseAnahtar);

let sb = null;
let oturum = null;
let profil = null;
const dinleyiciler = new Set();

/* Istemci NICIN kurulamadi. Iki sebep var ve ikisi cok farkli sey:
     "yapilandirma" -> anahtarlar bos. SITE SAHIBININ yapacagi bir sey var.
     "ag"           -> anahtarlar dolu ama supabase-js CDN'den gelmedi.
                       KULLANICININ yapacagi bir sey yok, beklemesi yeter.
   Onceden ikisi de tek bir "false"a dusuyordu ve giris.html ikisine de
   "Giris sistemi henuz kurulu degil -- app/yapilandirma.js dosyasini
   doldur" diyordu. Yayindaki sitede bu YANLIS: sistem kurulu, kullanici
   da o dosyaya erisemiyor. Kurumsal ag, okul agi ve ulke capinda engel
   gercek; Leaflet'te tam olarak bu oldu. */
let sorun = ACIK ? null : "yapilandirma";

/* CDN asili kalirsa sayfa SONSUZA KADAR bekliyordu (olculdu: 8 sn asili
   birakilan bir istekte hesabim.html 8 sn bos kaldi, sonra yonlendirdi).
   Bekleme sinirli; gec gelen modul artik kullanilmiyor cunku kullaniciya
   çoktan "tekrar dene" denmis oluyor. Sure konum bekcisiyle ayni. */
const AG_BEKLEME = 12000;

/* ---------- kurulum ---------- */
async function kur(){
  if (!ACIK) return false;
  let mod;
  try {
    mod = await Promise.race([
      /* TEK ADRES: app/lib/supabase-js.js. O dosya su an CDN'e
         yonlendiren bir yer tutucu; `python kutuphane_al.py` gercek
         paketlenmis surumu onun uzerine yaziyor ve kutuphane ayni
         kaynaktan gelmeye basliyor.

         Burada yedek mantigi YOK ve olmamali: "once yereli dene,
         olmazsa CDN" hali her yuklemede bir 404 uretir ve daha kotusu,
         yerel dosya BOZUKKEN sessizce CDN'e duserdi -- yani SRI'nin
         cozdugu sorunu geri getirirdi. Hangi surumun geldigi tek bir
         dosyanin icerigine bakiyor. */
      import("./lib/supabase-js.js"),
      new Promise((_, hata) => setTimeout(
        () => hata(new Error("supabase-js zaman asimi")), AG_BEKLEME))
    ]);
  } catch (e){
    sorun = "ag";
    throw e;                 /* hazir zinciri false'a dusuyor */
  }
  const { createClient } = mod;
  sb = createClient(AYAR.supabaseUrl, AYAR.supabaseAnahtar, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
  });
  const { data } = await sb.auth.getSession();
  oturum = data.session;
  if (oturum) profil = await kendiProfilim();
  sb.auth.onAuthStateChange(async (_olay, yeni) => {
    oturum = yeni;
    profil = yeni ? await kendiProfilim() : null;
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
  if (m.includes("sahiplik bulunamadi"))
    return "Bu sahiplik bulunamadı ya da zaten bırakılmış.";
  if (m.includes("profiller_kullanici_adi_check"))
    return "Kullanıcı adı 3-20 karakter olmalı; yalnız küçük harf, rakam ve alt çizgi.";
  if (m.includes("profiller_kullanici_adi_idx"))
    return "Bu kullanıcı adı alınmış. Başka bir tane dene.";
  if (m.includes("profiller_dogum_yili_check"))
    return "Doğum yılını kontrol et. En az 13 yaşında olmalısın.";
  if (m.includes("yorumlar_tek_kayit_idx"))
    return "Bu mekan için zaten bir yorumun var. Önce onu sil.";
  if (m.includes("yorumlar_puan_check"))
    return "Puan 1 ile 5 arasında olmalı.";
  if (m.includes("yorumlar_metin_check"))
    return "Yorum en az 3, en fazla 400 karakter olmalı.";
  if (m.includes("menu_katkilari_dolu_check"))
    return "Ürün adı ve fiyatını birlikte yaz ya da bir fotoğraf ekle.";
  if (m.includes("menu_katkilari_fiyat_check"))
    return "Fiyat 0 ile 100.000 ₺ arasında olmalı.";
  if (m.includes("menu_katkilari_urun_check"))
    return "Ürün adı 2-80 karakter olmalı.";
  if (m.includes("menu_katkilari_tek_bekleyen_idx"))
    return "Bu ürünü zaten göndermişsin, sırada bekliyor.";
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
async function kendiProfilim(){
  if (!sb || !oturum) return null;
  const { data, error } = await sb.from("profiller")
    .select("id, ad, yonetici, kullanici_adi, dogum_yili, meslek, kisilik, avatar, herkese_acik")
    .eq("id", oturum.user.id).maybeSingle();
  if (error){ console.error("profil:", error.message); return null; }
  return data;
}

/* ============================================================
   Dışa açılan yüzey
   ============================================================ */
const Kimlik = {
  acik: ACIK,
  /* null (sorun yok) | "yapilandirma" (anahtar bos) | "ag" (CDN gelmedi).
     Sayfalar buna gore FARKLI sey soylemeli: birincisinde yapacak is site
     sahibinde, ikincisinde kullanicida hicbir sey yok. */
  get sorun(){ return sorun; },
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
    profil = await kendiProfilim();
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
     isletmeyi devreden kisi yoneticiyi beklemesin.

     SILMIYOR, durumu 'birakildi' yapiyor. Yonetici iptali de oyle ve
     gerekce ayni: kimin neyi ne zaman sahiplendigi kaybolmasin. Sahibin
     katkisi INCELENMEDEN onaylandigi icin bu bir hesap verebilirlik
     meselesi -- silme kalsaydi biri mekani sahiplenip incelenmemis bilgi
     yazar, sonra birakir ve sahip OLDUGUNA dair kayit kalmazdi.
     Islem sunucuda (sahipligi_birak): bir UPDATE politikasi yalniz son
     hali denetler, hangi sutunun degistigini denetlemez. */
  /* Bir mekanin goruntulenme sayilari. isletme.html bunu dogrudan RPC
     ile cagiriyordu; isletmem.html de ayni sayiya bakiyor ve iki yerde
     iki ayri cagri, alan adlarinin ayrismasi demekti. Cagri tek yerde.

     `mekan_goruldu` BURADA YOK ve olmamali: o SAYIYI ARTIRIYOR. Sahibin
     kendi panelini acmasi, kendi sayfasinin goruntulenmesini sismesin --
     "sayfani 47 kisi gordu" cumlesinin butun degeri dogru olmasinda. */
  async mekanSayaci(mekanId){
    if (!sb) return null;
    const { data, error } = await sb.rpc("mekan_sayaci", { p_mekan_id: mekanId });
    if (error){ console.error("sayac:", error.message); return null; }
    const o = Array.isArray(data) ? data[0] : data;
    return o ? { bugun: +o.bugun || 0, son30: +o.son30 || 0,
                 toplam: +o.toplam || 0, ilkGun: o.ilk_gun || null } : null;
  },

  async sahiplikBirak(id){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const { error } = await sb.rpc("sahipligi_birak", { p_id: id });
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

  /* ---------- ağ mekanikleri: bütçe akranları ve civar ----------
     İkisi de tarayıcıda hesaplanamıyor, çünkü ikisi de `kullanici`
     sütununa bakıyor ve o sütun anon'a kapalı (sema.sql "Sütun yetkisi").
     Tarayıcı aynı kişinin iki fişini tek kişi sayamaz — sayabilseydi
     zaten kişiyi izleyebiliyor olurdu. Sayım sunucuda (akran.sql).

     akran.sql çalıştırılmamışsa çağrı hata döner; sayfa çökmesin diye
     null'a düşüyor — çağıran bunu "özellik kapalı" diye okuyor. */
  async butceAkranlari(il, tavan){
    if (!sb || !(tavan > 0)) return null;
    const { data, error } = await sb.rpc("butce_akranlari",
      { p_il: il || null, p_tavan: tavan });
    if (error){ console.error("akran:", error.message); return null; }
    const o = Array.isArray(data) ? data[0] : data;
    return o ? { akran: +o.akran || 0, fis: +o.fis || 0, mekan: +o.mekan || 0 } : null;
  },

  /* Civarın fiş özeti. Hangi mekanların civar olduğuna İSTEMCİ karar
     veriyor (koordinat statik JSON'da), toplamı sunucu veriyor.
     Liste 500'ü aşarsa sunucu hata veriyor, sessizce kırpmıyor:
     ekranda yazan yarıçapın doğru olması buna bağlı. */
  async civarFisOzeti(mekanIdler){
    if (!sb || !mekanIdler || !mekanIdler.length) return null;
    const { data, error } = await sb.rpc("civar_fis_ozeti",
      { p_mekan_idler: mekanIdler });
    if (error){ console.error("civar:", error.message); return null; }
    const o = Array.isArray(data) ? data[0] : data;
    return o ? { fis: +o.fis || 0, kisi: +o.kisi || 0, mekan: +o.mekan || 0,
                 medyan: o.medyan == null ? null : +o.medyan } : null;
  },

  /* ---------- profil (genişletilmiş) ----------
     Alanların hepsi isteğe bağlı; profil.sql'in başındaki kural bu.
     Tablo dışarıya KAPALI kalıyor: herkese açık okuma tek bir
     fonksiyondan geçiyor (profil_getir), çünkü tabloyu açmak uuid ile
     profil eşlemesini de açardı. */
  async profilGuncelle(y){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const yama = {};
    /* Boş dizgi NULL'a çevriliyor: "" bir değer değil, alanın
       boşaltılması. Öyle olmasa kullanıcı yazdığını geri alamazdı. */
    const bos = v => { const t = String(v == null ? "" : v).trim(); return t || null; };
    if ("ad"           in y) yama.ad            = bos(y.ad);
    if ("kullaniciAdi" in y) yama.kullanici_adi = (bos(y.kullaniciAdi) || "").toLowerCase() || null;
    if ("meslek"       in y) yama.meslek        = bos(y.meslek);
    if ("kisilik"      in y) yama.kisilik       = bos(y.kisilik);
    if ("avatar"       in y) yama.avatar        = bos(y.avatar);
    if ("herkeseAcik"  in y) yama.herkese_acik  = !!y.herkeseAcik;
    if ("dogumYili"    in y){
      const n = parseInt(y.dogumYili, 10);
      yama.dogum_yili = Number.isFinite(n) ? n : null;
    }
    if (!Object.keys(yama).length) return;
    const { error } = await sb.from("profiller").update(yama).eq("id", oturum.user.id);
    if (error) throw new Error(hataMetni(error));
    profil = await kendiProfilim();
    duyur();
  },

  /* Herkese açık profil. Giriş GEREKMİYOR. Bulunamazsa null: kapalı
     profil ile olmayan profil AYNI cevabı veriyor -- ayırmak, "bu ad
     kayıtlı mı" diye yoklamak için bir sinyal olurdu. */
  async profilGetir(kullaniciAdi){
    if (!sb) return null;
    const { data, error } = await sb.rpc("profil_getir",
      { p_kullanici_adi: String(kullaniciAdi || "").trim().toLowerCase() });
    if (error){ console.error("profil:", error.message); return null; }
    const p = Array.isArray(data) ? data[0] : data;
    return p || null;
  },

  /* Avatar. Depolama kovasına YALNIZ kendi klasörüne yazılabiliyor
     (profil.sql); klasör adı kullanıcının kimliği. Eski dosya siliniyor,
     yoksa her yükleme kovada bir kopya bırakırdı. */
  async avatarYukle(dosya){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const t = (dosya && dosya.type) || "";
    if (!/^image\/(jpeg|png|webp)$/.test(t))
      throw new Error("Yalnız JPEG, PNG veya WebP yükleyebilirsin.");
    if (dosya.size > 2 * 1024 * 1024)
      throw new Error("Dosya 2 MB'tan büyük olmamalı.");
    const uzanti = t === "image/png" ? "png" : t === "image/webp" ? "webp" : "jpg";
    /* Ad her seferinde değişiyor: aynı adla üzerine yazsak tarayıcı
       önbelleği eski resmi göstermeye devam ederdi. */
    const yol = oturum.user.id + "/" + Date.now() + "." + uzanti;
    const { error } = await sb.storage.from("avatar")
      .upload(yol, dosya, { contentType: t, upsert: false });
    if (error) throw new Error(hataMetni(error));
    const eski = profil && profil.avatar;
    await this.profilGuncelle({ avatar: yol });
    if (eski && eski !== yol){
      try { await sb.storage.from("avatar").remove([eski]); } catch (e) {}
    }
    return yol;
  },

  async avatarSil(){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const eski = profil && profil.avatar;
    await this.profilGuncelle({ avatar: null });
    if (eski){ try { await sb.storage.from("avatar").remove([eski]); } catch (e) {} }
  },

  /* Depolamadaki yoldan görüntülenebilir adres. Kova herkese açık, yani
     imzalı adres gerekmiyor. */
  avatarAdresi(yol){
    if (!sb || !yol) return "";
    const { data } = sb.storage.from("avatar").getPublicUrl(yol);
    return (data && data.publicUrl) || "";
  },

  /* ---------- mekan fotoğrafları ----------
     Üç kaynak, üç ayrı güven seviyesi: 'sahip' (doğrulanmış işletme
     sahibi, doğrudan yayında), 'kullanici' (onaydan geçer), 'commons'
     (Wikimedia, ATIF ZORUNLU ve taşınıyor).

     Google Maps vb. BURAYA GİRMEZ ve giremez: kaynak sütunu kısıtlı ve
     'commons' istemciden yazılamıyor (veritabani/mekan_foto.sql). */
  async mekanFotograflari(mekanId){
    if (!sb) return [];
    const { data, error } = await sb.rpc("mekan_fotograflari", { p_mekan_id: mekanId });
    if (error){ console.error("mekan fotograflari:", error.message); return []; }
    return data || [];
  },

  async mekanFotoGonder(f){
    if (!sb || !oturum) throw new Error("Fotoğraf için giriş yap.");
    const { error } = await sb.from("mekan_fotolari").insert({
      kullanici: oturum.user.id,
      mekan_id: f.mekanId,
      il: f.il || null,
      mekan_ad: String(f.mekanAd).trim(),
      yol: f.yol,
      aciklama: (f.aciklama || "").trim() || null,
      durum: "bekliyor"
      /* kaynak GÖNDERİLMİYOR: varsayılan 'kullanici', sahibiyse
         tetikleyici 'sahip' yapıyor. İstemcinin söylemesi gereken
         bir şey değil. */
    });
    if (error) throw new Error(hataMetni(error));
  },

  async mekanFotoYukle(dosya){
    return this._fotoYukle("mekan", dosya);
  },

  mekanFotoAdresi(yol){
    if (!sb || !yol) return "";
    const { data } = sb.storage.from("mekan").getPublicUrl(yol);
    return (data && data.publicUrl) || "";
  },

  async mekanFotolarim(){
    if (!sb || !oturum) return [];
    const { data, error } = await sb.from("mekan_fotolari")
      .select("id, mekan_id, mekan_ad, il, yol, adres, aciklama, kaynak, durum, olusturuldu")
      .order("olusturuldu", { ascending: false });
    if (error){ console.error("mekan fotolarim:", error.message); return []; }
    return data || [];
  },

  async mekanFotoSil(id, yol){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const { error } = await sb.from("mekan_fotolari").delete().eq("id", id);
    if (error) throw new Error(hataMetni(error));
    if (yol){ try { await sb.storage.from("mekan").remove([yol]); } catch (e) {} }
  },

  async mekanFotoYonetimListesi(durum){
    if (!sb || !oturum) return [];
    let q = sb.from("mekan_fotolari")
      .select("id, mekan_id, mekan_ad, il, yol, adres, aciklama, kaynak, durum, olusturuldu")
      .order("olusturuldu", { ascending: false }).limit(200);
    if (durum) q = q.eq("durum", durum);
    const { data, error } = await q;
    if (error){ console.error("mekan foto yonetim:", error.message); return []; }
    return data || [];
  },

  async mekanFotoKarar(id, durum){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    if (!["onaylandi","reddedildi","bekliyor"].includes(durum))
      throw new Error("Geçersiz durum.");
    const { error } = await sb.from("mekan_fotolari").update({ durum }).eq("id", id);
    if (error) throw new Error(hataMetni(error));
  },

  /* ---------- menü ve ürün paylaşımı ----------
     paylasimlar bir HESAP taşıyor ("3 kişi, 850 ₺"), burası bir LİSTE
     FİYATI ("Latte 95 ₺"). Ayrı tablolar, ayrı sorular.

     Gösterilen ortalamaya GİRMİYOR: o hesap fiyat_analiz.py'de, Python'da
     yapılıyor. Aynı kuralı tarayıcıda ikinci kez yazmak, iki dilde iki
     doğru demekti. Onaylanan kalemler ayrı bir bölümde "kullanıcıdan"
     etiketiyle duruyor. */
  async menuKatkiGonder(k){
    if (!sb || !oturum) throw new Error("Menü eklemek için giriş yap.");
    const { error } = await sb.from("menu_katkilari").insert({
      kullanici: oturum.user.id,
      mekan_id: k.mekanId,
      il: k.il || null,
      mekan_ad: String(k.mekanAd).trim(),
      urun: (k.urun || "").trim() || null,
      fiyat: k.fiyat == null || k.fiyat === "" ? null : Number(k.fiyat),
      foto: k.foto || null,
      durum: "bekliyor"
    });
    if (error) throw new Error(hataMetni(error));
  },

  async mekanMenuKatkilari(mekanId){
    if (!sb) return [];
    const { data, error } = await sb.rpc("mekan_menu_katkilari", { p_mekan_id: mekanId });
    if (error){ console.error("menu katkilari:", error.message); return []; }
    return data || [];
  },

  async menuKatkilarim(){
    if (!sb || !oturum) return [];
    const { data, error } = await sb.from("menu_katkilari")
      .select("id, mekan_id, mekan_ad, il, urun, fiyat, foto, durum, olusturuldu")
      .order("olusturuldu", { ascending: false });
    if (error){ console.error("menu katkilarim:", error.message); return []; }
    return data || [];
  },

  async menuKatkiSil(id, foto){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const { error } = await sb.from("menu_katkilari").delete().eq("id", id);
    if (error) throw new Error(hataMetni(error));
    /* Kayıt gidince dosya da gitmeli, yoksa kovada sahipsiz resim birikir.
       Silinemezse sessiz geçiyoruz: kayıt zaten gitti, kullanıcıya
       yapabileceği bir şey olmayan bir hata göstermenin anlamı yok. */
    if (foto){ try { await sb.storage.from("menu").remove([foto]); } catch (e) {} }
  },

  async menuKatkiYonetimListesi(durum){
    if (!sb || !oturum) return [];
    let q = sb.from("menu_katkilari")
      .select("id, mekan_id, mekan_ad, il, urun, fiyat, foto, durum, olusturuldu")
      .order("olusturuldu", { ascending: false }).limit(200);
    if (durum) q = q.eq("durum", durum);
    const { data, error } = await q;
    if (error){ console.error("menu katki yonetim:", error.message); return []; }
    return data || [];
  },

  async menuKatkiKarar(id, durum){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    if (!["onaylandi","reddedildi","bekliyor"].includes(durum))
      throw new Error("Geçersiz durum.");
    const { error } = await sb.from("menu_katkilari").update({ durum }).eq("id", id);
    if (error) throw new Error(hataMetni(error));
  },

  /* Menü fotoğrafı. Dosya OLDUĞU GİBİ yüklenmiyor: ortak.js'teki
     resimHazirla() tuvale çizip yeniden kodluyor ve bu sırada EXIF
     tamamen düşüyor (GPS koordinatı, çekim saati, cihaz modeli).
     Sunucu bunu doğrulayamıyor -- Storage dosyayı ayrıştırmıyor -- o
     yüzden kural burada ve test_tarayici.mjs onu ölçüyor. */
  async menuFotoYukle(dosya){
    return this._fotoYukle("menu", dosya);
  },

  /* Iki kova, TEK kural. Ayri ayri yazilmis iki yukleme, ikisinden
     birinde EXIF adiminin unutulmasi demekti -- ve o adimin tek bekcisi
     istemci (sunucu dosyayi ayristirmiyor). */
  async _fotoYukle(kova, dosya){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    if (!/^image\//.test((dosya && dosya.type) || ""))
      throw new Error("Yalnız resim dosyası yükleyebilirsin.");
    /* Ham dosya için geniş bir üst sınır: küçültme SONRA yapılıyor, ama
       200 MB'lık bir dosyayı tuvale çizmeye çalışmak sekmeyi kilitler. */
    if (dosya.size > 25 * 1024 * 1024)
      throw new Error("Dosya çok büyük (en fazla 25 MB).");
    if (typeof resimHazirla !== "function")
      throw new Error("Resim işleyici yüklenmedi.");
    /* EXIF burada dusuyor: GPS koordinati, cekim saati, cihaz modeli. */
    const hazir = await resimHazirla(dosya);
    const yol = oturum.user.id + "/" + Date.now() + "-" +
                Math.random().toString(36).slice(2, 8) + ".jpg";
    const { error } = await sb.storage.from(kova)
      .upload(yol, hazir, { contentType: "image/jpeg", upsert: false });
    if (error) throw new Error(hataMetni(error));
    return yol;
  },

  menuFotoAdresi(yol){
    if (!sb || !yol) return "";
    const { data } = sb.storage.from("menu").getPublicUrl(yol);
    return (data && data.publicUrl) || "";
  },

  /* ---------- yorumlar ----------
     Fiyattan AYRI: paylasimlar bir ÖLÇÜM taşıyor, yorum bir KANI.
     Yorumun puanı fiyat hesabına girmiyor (yorum.sql başlığı). */
  async yorumGonder(y){
    if (!sb || !oturum) throw new Error("Yorum için giriş yap.");
    const { error } = await sb.from("yorumlar").insert({
      kullanici: oturum.user.id,
      mekan_id: y.mekanId,
      il: y.il || null,
      mekan_ad: String(y.mekanAd).trim(),
      puan: y.puan,
      metin: (y.metin || "").trim() || null,
      durum: "bekliyor"
    });
    if (error) throw new Error(hataMetni(error));
  },

  /* Bir mekanın onaylı yorumları, yazar bilgisiyle. Kimlik numarası
     DÖNMÜYOR: birleştirme sunucuda (mekan_yorumlari). */
  async mekanYorumlari(mekanId){
    if (!sb) return [];
    const { data, error } = await sb.rpc("mekan_yorumlari", { p_mekan_id: mekanId });
    if (error){ console.error("yorumlar:", error.message); return []; }
    return data || [];
  },

  /* Bir kullanıcının onaylı yorumları (profil sayfası).
     FİŞLERİ listeleyen karşılığı YOK ve olmayacak: onlar kanı değil
     ödeme kaydı. Gerekçe veritabani/yorum.sql'de profil_yorumlari'nın
     başında yazılı. */
  async profilYorumlari(kullaniciAdi){
    if (!sb) return [];
    const { data, error } = await sb.rpc("profil_yorumlari",
      { p_kullanici_adi: String(kullaniciAdi || "").trim().toLowerCase() });
    if (error){ console.error("profil yorumlari:", error.message); return []; }
    return data || [];
  },

  async mekanPuani(mekanId){
    if (!sb) return null;
    const { data, error } = await sb.rpc("mekan_puani", { p_mekan_id: mekanId });
    if (error){ console.error("puan:", error.message); return null; }
    const o = Array.isArray(data) ? data[0] : data;
    return o ? { adet: +o.adet || 0,
                 ortalama: o.ortalama == null ? null : +o.ortalama } : null;
  },

  /* Keşfet ekranı bir ilin TAMAMINI tek istekte istiyor: 12 bin mekan
     için 12 bin çağrı atılamaz. */
  async ilPuanlari(il){
    if (!sb || !il) return new Map();
    const { data, error } = await sb.rpc("il_puanlari", { p_il: il });
    if (error){ console.error("il puanlari:", error.message); return new Map(); }
    return new Map((data || []).map(r =>
      [r.mekan_id, { adet: +r.adet || 0, ortalama: +r.ortalama }]));
  },

  async yorumlarim(){
    if (!sb || !oturum) return [];
    const { data, error } = await sb.from("yorumlar")
      .select("id, mekan_id, mekan_ad, il, puan, metin, durum, olusturuldu")
      .order("olusturuldu", { ascending: false });
    if (error){ console.error("yorumlarim:", error.message); return []; }
    return data || [];
  },

  async yorumSil(id){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    const { error } = await sb.from("yorumlar").delete().eq("id", id);
    if (error) throw new Error(hataMetni(error));
  },

  async yorumYonetimListesi(durum){
    if (!sb || !oturum) return [];
    let q = sb.from("yorumlar")
      .select("id, mekan_id, mekan_ad, il, puan, metin, durum, olusturuldu")
      .order("olusturuldu", { ascending: false }).limit(200);
    if (durum) q = q.eq("durum", durum);
    const { data, error } = await q;
    if (error){ console.error("yorum yonetim:", error.message); return []; }
    return data || [];
  },

  async yorumKarar(id, durum){
    if (!sb || !oturum) throw new Error("Giriş yapılmamış.");
    if (!["onaylandi","reddedildi","bekliyor"].includes(durum))
      throw new Error("Geçersiz durum.");
    const { error } = await sb.from("yorumlar").update({ durum }).eq("id", id);
    if (error) throw new Error(hataMetni(error));
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
  .catch(e => {
    /* Beklenmedik bir hata da (modul geldi ama createClient patladi gibi)
       kullanici acisindan ag sorunudur: yapacagi bir sey yok. */
    if (sorun === null) sorun = "ag";
    console.error("Kimlik kurulamadı:", e);
    return false;
  });

export default Kimlik;
