/* ============================================================
   Tarayici kontrollerini tarayicisiz kosturur.

   ortak.js "?test=1", kesfet.js "?test=1" ve isletme.html "#kontrol"
   kontrolleri sayfayi acmadan calismiyordu; yani her degisiklikten sonra
   birinin elle uc sayfayi acmasi gerekiyordu ve pratikte kimse acmiyor.
   Burada sayfa betikleri sahte bir DOM'un icinde calistiriliyor, kontroller
   BASARISIZ basarsa yakalaniyor.

   Betikler sonuna kadar hatasiz akip hicbir sey basmadiysa kontroller
   gecmis demektir; sandiga yazan tek sey basarisizlik.

       node test_tarayici.mjs
   ============================================================ */
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import os from "node:os";

const yok = () => {};

/* Sahte eleman: okunmayan her ozellik bos dize, yazilan her ozellik
   sessizce kabul. Amaci sayfa kodunun akmasini saglamak, DOM'u taklit
   etmek degil. */
function sahteEleman(){
  return new Proxy({
    style: {}, dataset: {},
    classList: { add: yok, remove: yok, toggle: yok, contains: () => false },
    addEventListener: yok, removeEventListener: yok,
    querySelectorAll: () => [], querySelector: () => null,
    setAttribute: yok, getAttribute: () => null, removeAttribute: yok,
    appendChild: yok, insertAdjacentHTML: yok, focus: yok, remove: yok,
    closest: () => null, getBoundingClientRect: () => ({ width: 0, height: 0, top: 0, left: 0 }),
    showModal: yok, close: yok, scrollTop: 0, disabled: false, hidden: false
  }, {
    get: (t, p) => (p in t ? t[p] : ""),
    set: (t, p, v) => { t[p] = v; return true; }
  });
}

function ortamKur({ hash = "", search = "" } = {}){
  const basilan = [];
  /* DOMContentLoaded dinleyicileri TOPLANIYOR, yutulmuyor.
     kesfet.js bir IIFE icinde ve kontrolunu (paylasimKontrol) yalniz bu
     olayin icinden cagiriyor; olayi tetiklemeyen bir kosum takimi hicbir
     sey calistirmadan "gecti" der. Bir kez basimiza geldi. */
  const dinleyiciler = [];
  const ctx = {
    document: {
      addEventListener: (olay, f) => { if (olay === "DOMContentLoaded") dinleyiciler.push(f); },
      removeEventListener: yok,
      documentElement: { dataset: {}, classList: { add: yok, remove: yok },
        style: { setProperty: yok, getPropertyValue: () => "" } },
      getElementById: sahteEleman, querySelector: sahteEleman,
      querySelectorAll: () => [], createElement: sahteEleman,
      body: { insertAdjacentHTML: (_, h) => basilan.push(h), classList: { add: yok } },
      title: "", head: sahteEleman()
    },
    location: { search, hash, href: "http://yerel/x" + search + hash, replace: yok },
    history: { replaceState: yok, pushState: yok },
    localStorage: { getItem: () => null, setItem: yok, removeItem: yok },
    sessionStorage: { getItem: () => null, setItem: yok },
    matchMedia: () => ({ matches: false, addEventListener: yok }),
    navigator: { geolocation: { getCurrentPosition: yok } },
    crypto: { randomUUID: () => "00000000-0000-4000-8000-000000000000" },
    /* Cozulmeyen fetch: veri gelmesin, cizim tetiklenmesin. Kontroller
       veriye bagli degil, saf fonksiyonlara bakiyor. */
    fetch: () => new Promise(() => {}),
    setTimeout, clearTimeout, setInterval: () => 0, clearInterval: yok,
    /* Sayfanin kullandigi tarayici API'leri: is yapmalari gerekmiyor,
       var olmalari yetiyor -- kontroller saf fonksiyonlara bakiyor. */
    MutationObserver: class { observe(){} disconnect(){} },
    IntersectionObserver: class { observe(){} unobserve(){} disconnect(){} },
    ResizeObserver: class { observe(){} disconnect(){} },
    requestAnimationFrame: yok, addEventListener: yok, removeEventListener: yok,
    URLSearchParams, URL, console,
    /* Leaflet: kesfet.js harita kuruyor. Zincirlenebilir sahte nesne. */
    L: new Proxy(function(){ return ctx.L; }, {
      get: () => ctx.L, apply: () => ctx.L, construct: () => ctx.L
    }),
    Kimlik: {
      acik: false, hazir: Promise.resolve(false), girisli: false, yonetici: false,
      profil: null, kullanici: null, izle: yok, istemci: () => null,
      onaylanmisKatkilar: async () => [], onaylanmisPaylasimlar: async () => [],
      favoriler: async () => []
    }
  };
  ctx.window = ctx;
  ctx.self = ctx;
  vm.createContext(ctx);
  /* Sayfa yuklendi: kayitli dinleyicileri sirasiyla calistir. Icinden
     firlayan hata yutulmuyor -- acilista patlayan sayfa da bir hatadir. */
  const yukle = () => { for (const f of dinleyiciler) f(); };
  return { ctx, basilan, yukle, dinleyiciSayisi: () => dinleyiciler.length };
}

function modulCikar(html){
  const m = html.match(/<script type="module">([\s\S]*?)<\/script>/);
  if (!m) throw new Error("modul betigi bulunamadi");
  return m[1].replace(/^import .*$/m, "/* import elendi */");
}

/* Kontrolun GERCEKTEN kostugunu, kendi imzasini basmasindan anliyoruz.
   "sayfaya bir sey basildi mi" yetmiyor: kesfet baglaminda ortak.js de
   kendi raporunu ayni yere basiyor ve kesfet kontrolu tamamen silinse bile
   dizi dolu gorunuyordu -- yani silinen kontrol "gecti" diye raporlaniyordu.
   Imza, ilgili betigin kendi rapor cumlesinden aliniyor. */
function imzaAra(basilan, imzalar){
  return basilan.some(h => imzalar.some(i => h.includes(i)));
}

const sonuclar = [];
/* Kontrol ya bir dizi ya da dizi donduren bir SOZ verebilir. Sozler
   bekleniyor -- yoksa asenkron bir kontrol hicbir sey dogrulamadan
   "gecti" derdi (dizi degil Promise geliyor, .length undefined,
   !undefined true). */
function kosu(ad, calistir){
  try {
    const kotu = calistir();
    if (kotu && typeof kotu.then === "function"){
      sonuclar.push(kotu.then(k => ({ ad, gecti: !k.length, ayrinti: k }))
                        .catch(e => ({ ad, gecti: false, ayrinti: [String(e)] })));
      return;
    }
    if (!Array.isArray(kotu)){
      sonuclar.push({ ad, gecti: false,
                      ayrinti: ["kontrol dizi dondurmedi: " + typeof kotu] });
      return;
    }
    sonuclar.push({ ad, gecti: !kotu.length, ayrinti: kotu });
  } catch (e) {
    sonuclar.push({ ad, gecti: false, ayrinti: [e.message] });
  }
}

/* ---------- ortak.js: ?test=1 ---------- */
kosu("ortak.js (tema, acilis saati, yemek fiyati, katki dogrulama)", () => {
  const { ctx, basilan, yukle, dinleyiciSayisi } = ortamKur({ search: "?test=1" });
  vm.runInContext(fs.readFileSync("app/ortak.js", "utf8"), ctx);
  if (!dinleyiciSayisi()) return ["ortak.js hic DOMContentLoaded dinleyicisi kurmadi"];
  yukle();
  if (!imzaAra(basilan, ["kontrolun hepsi gecti", "BASARISIZ ("]))
    return ["kontrol hic calismadi: ortak.js raporunu basmadi"];
  return basilan.filter(h => h.includes("BASARISIZ"));
});

/* ---------- kesfet.js: ?test=1 ---------- */
kosu("kesfet.js (paylasim medyani, olcut kiyasi)", () => {
  const { ctx, basilan, yukle } = ortamKur({ search: "?test=1" });
  vm.runInContext(fs.readFileSync("app/ortak.js", "utf8"), ctx);
  vm.runInContext(fs.readFileSync("app/kesfet.js", "utf8"), ctx);
  yukle();
  /* kesfet.js IIFE: disaridan hicbir adina erisilemiyor, bu yuzden
     "kontrol calisti mi" sorusu ancak KENDI imzasindan anlasilir. */
  if (!imzaAra(basilan, ["medyan + olcut kiyasi", "KONTROL BASARISIZ"]))
    return ["kontrol hic calismadi: kesfet.js raporunu basmadi"];
  return basilan.filter(h => h.includes("BASARISIZ"));
});

/* ---------- isletme.html: #kontrol ---------- */
kosu("isletme.html (eksik bulucu, fis esigi, katki birlestirme)", () => {
  const { ctx, basilan } = ortamKur({ hash: "#kontrol" });
  vm.runInContext(fs.readFileSync("app/ortak.js", "utf8"), ctx);
  vm.runInContext(modulCikar(fs.readFileSync("app/isletme.html", "utf8")), ctx);
  if (!imzaAra(basilan, ["eksik bulucu + fis + katki", "BASARISIZ:"]))
    return ["kontrol hic calismadi: isletme.html raporunu basmadi"];
  return basilan.filter(h => h.includes("BASARISIZ"));
});

/* ---------- vitrin, kesfet ile ayni fiyati soylemeli ----------
   Anasayfa vitrin.json'dan, kesfet app/veri/<il>.json'dan besleniyor ama
   FIYATI ikisi de ayni fonksiyonla (ortak.js yemekFiyati) hesapliyor.
   vitrin_uret.py o fonksiyonun okudugu HAM ALANLARI tasimak zorunda.

   Bir kez kacti: "tarih" alani veriye eklendi, vitrine eklenmedi. Sonuc
   sessizdi -- bugun hicbir fiyat bir yillik degil, yani iki taraf da ayni
   sayiyi veriyordu. Veri yaslandigi gun kesfet fiyati geri cekecek,
   anasayfa gostermeye devam edecekti.

   Bu kontrol alan LISTESI tutmuyor: iki tarafi da hesaplatip sonuclari
   kiyasliyor. Yarin yemekFiyati yeni bir alan okursa bu da yakalar. */
kosu("vitrin ile veri ayni fiyati veriyor", () => {
  const { ctx } = ortamKur();
  vm.runInContext(fs.readFileSync("app/ortak.js", "utf8"), ctx);
  const vitrin = JSON.parse(fs.readFileSync("app/vitrin.json", "utf8")).vitrin || [];
  if (!vitrin.length) return ["vitrin.json bos - vitrin_uret.py calistir"];

  /* Kaynak kaydi il dosyasindan id ile bul. */
  const kaynak = new Map();
  for (const y of fs.readdirSync("app/veri")){
    if (!/^\d\d\.json$/.test(y)) continue;
    /* Dosya sikistirilmis bicimde (veri_bicim.py). Cozucu TARAYICININ
       kendi cozucusu -- ayni ctx'e yuklu ortak.js'ten cagriliyor. Yan
       kazanc: ilCoz() boylece 81 ilin GERCEK dosyasinda kosuyor, elle
       yazilmis bir ornekte degil. */
    ctx.__d = JSON.parse(fs.readFileSync("app/veri/" + y, "utf8"));
    for (const m of vm.runInContext("ilCoz(__d)", ctx).mekanlar)
      kaynak.set(m.id, m);
  }
  const hesapla = m => {
    ctx.__m = m;
    return vm.runInContext("yemekFiyati(__m)", ctx);
  };
  const kotu = [];
  for (const v of vitrin){
    const k = kaynak.get(v.id);
    if (!k){ kotu.push(v.ad + ": vitrindeki mekan veride yok (" + v.id + ")"); continue; }
    const a = hesapla(v), b = hesapla(k);
    if (a !== b)
      kotu.push(v.ad + ": vitrin " + a + " diyor, veri " + b +
                " -- vitrin_uret.py bir alani tasimiyor");
  }
  return kotu;
});

/* ---------- kimlik.js: veri katmani GERCEKTEN calisiyor ----------
   400 satirlik veri katmani bugune kadar yalniz AYRISTIRILIYORDU, hic
   calistirilmiyordu. Supabase'e cikmadan calistirmak icin dinamik
   import sahte bir modulle degistiriliyor ve sorgu zinciri taklit
   ediliyor. Amac Supabase'i sinamak degil, BIZIM kodumuzu: hata
   siniflandirmasi, uc deger donen fonksiyonlar, girdi temizligi.

   Bunlarin hepsi sessizce yanlis olabilecek turden. Ornek: mekan
   sahiplenilmis mi sorusu, tablo YOKKEN "hayir" donuyordu -- yani
   sahiplenme kurulmamis bir sistemde isletme sayfasi kod formunu
   aciyor, kullanici kodu giriyor ve anlamsiz bir hata aliyordu. */
kosu("kimlik.js (veri katmani, sahte Supabase)", () => {
  const kaynak = fs.readFileSync("app/kimlik.js", "utf8");

  /* Sonuc uretici: her sorgu zinciri ayni nesneyi donduruyor ve en
     sonunda then() ile { data, error } veriyor. */
  const zincir = (sonuc) => {
    const z = { then: (f) => Promise.resolve(sonuc).then(f) };
    for (const ad of ["select","eq","order","limit","insert","update","delete",
                      "in","neq","gte","lte","range","or"])
      z[ad] = () => z;
    /* maybeSingle/single zinciri BITIRIYOR: dizi degil tek kayit doner. */
    z.maybeSingle = () => Promise.resolve(
      { data: Array.isArray(sonuc.data) ? (sonuc.data[0] ?? null) : sonuc.data,
        error: sonuc.error });
    z.single = z.maybeSingle;
    return z;
  };
  let sonrakiSonuc = { data: [], error: null };
  const sahteIstemci = {
    from: () => zincir(sonrakiSonuc),
    rpc: () => Promise.resolve(sonrakiSonuc),
    auth: {
      /* Girisli bir oturum: sahiplikTalep ve katkiGonder giris sarti
         ariyor. Girissiz fixture ile yazmistim ve kosum takimi ilk
         calistirmada yakaladi. */
      getSession: async () => ({ data: { session: { user: { id: "k1" } } } }),
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe(){} } } })
    }
  };

  const sahteModul = "data:text/javascript," + encodeURIComponent(
    "export const createClient = () => globalThis.__sahteIstemci;");
  /* "await" ARANMIYOR: import() bir Promise.race icinde de durabiliyor
     (zaman asimi eklendiginde tam olarak bu oldu ve kalip kacti). Aranan
     sey CAGRININ KENDISI. */
  /* Adres artik YEREL: app/lib/supabase-js.js (kutuphane_al.py o dosyanin
     uzerine gercek paketlenmis surumu yaziyor). Kalip ona gore. */
  const duzenli = kaynak.replace(/import\("\.\/lib\/supabase-js\.js"\)/,
                                 'import("' + sahteModul + '")');
  if (duzenli === kaynak) return ["kimlik.js icindeki supabase-js import'u bulunamadi"];

  const yol = path.join(os.tmpdir(), "kimlik-kontrol-" + process.pid + ".mjs");
  fs.writeFileSync(yol, duzenli);
  globalThis.__sahteIstemci = sahteIstemci;
  globalThis.window = { CEBIMDE: { supabaseUrl: "https://x.test",
                                    supabaseAnahtar: "y" } };
  globalThis.document = { querySelectorAll: () => [], addEventListener(){} };
  globalThis.localStorage = { getItem: () => null, setItem(){}, removeItem(){} };

  const kotu = [];
  return import("file://" + yol).then(async (mod) => {
    const K = mod.default;
    await K.hazir;
    const esit = (ad, a, b) => { if (JSON.stringify(a) !== JSON.stringify(b))
      kotu.push(ad + ": " + JSON.stringify(a) + " != " + JSON.stringify(b)); };

    /* --- mekanSahiplenilmis UC deger donmeli --- */
    sonrakiSonuc = { data: [{ id: 1 }], error: null };
    esit("sahiplenilmis mekan", await K.mekanSahiplenilmis("node/1"), true);
    sonrakiSonuc = { data: [], error: null };
    esit("sahiplenilmemis mekan", await K.mekanSahiplenilmis("node/1"), false);
    /* Tablo yok: false DEGIL null. Yoksa kurulmamis ozellik "hayir" gibi
       gorunur ve isletme sayfasi calismayan bir form acar. */
    sonrakiSonuc = { data: null, error: { message: 'relation "public.sahiplik" does not exist', code: "42P01" } };
    esit("tablo yok -> null", await K.mekanSahiplenilmis("node/1"), null);
    sonrakiSonuc = { data: null, error: { message: "Could not find the table in the schema cache", code: "PGRST205" } };
    esit("sema onbelleginde yok -> null", await K.mekanSahiplenilmis("node/1"), null);

    /* --- sahiplikTalep: sunucuya gitmeden once temizlik --- */
    sonrakiSonuc = { data: [{ mekan_id: "node/1", il: "34", mekan_ad: "X" }], error: null };
    const t = await K.sahiplikTalep(" abcd-3456 ");
    esit("talep sonucu", t, { mekanId: "node/1", il: "34", mekanAd: "X" });
    for (const kotuKod of ["", "  ", "AB-12"]) {
      let hata = null;
      try { await K.sahiplikTalep(kotuKod); } catch (e) { hata = e.message; }
      if (!hata) kotu.push("kisa kod sunucuya gitti: " + JSON.stringify(kotuKod));
    }
    /* Sunucu hatasi kullaniciya ANLASILIR cumleyle donmeli. */
    sonrakiSonuc = { data: null, error: { message: "kod gecersiz" } };
    let mesaj = null;
    try { await K.sahiplikTalep("ABCD3456"); } catch (e) { mesaj = e.message; }
    if (!mesaj || /gecersiz$/.test(mesaj) || mesaj.length < 20)
      kotu.push("ham SQL mesaji kullaniciya gidiyor: " + mesaj);

    /* --- katkiGonder: tekil kisit "ayni gun" degil "sirada bekliyor" --- */
    sonrakiSonuc = { error: { message: 'duplicate key value violates unique constraint' } };
    let km = null;
    try { await K.katkiGonder({ mekanId: "n", mekanAd: "X", alan: "tel", deger: "1" }); }
    catch (e) { km = e.message; }
    if (!km || !/sırada bekliyor/.test(km))
      kotu.push("katki tekil kisit mesaji yanlis: " + km);

    fs.unlinkSync(yol);
    return kotu;
  }).catch(e => [String(e).slice(0, 200)]);
});

/* ---------- sayfa ici modullerin sozdizimi ---------- */
kosu("modul betikleri ayristirilabiliyor", () => {
  const kotu = [];
  for (const y of ["app/hesabim.html", "app/yonetim.html", "app/paylas.html",
                   "app/giris.html", "app/isletme.html"]){
    const s = fs.readFileSync(y, "utf8");
    if (!/<script type="module">/.test(s)) continue;
    try { new vm.Script(modulCikar(s), { filename: y }); }
    catch (e) { kotu.push(y + ": " + e.message); }
  }
  for (const y of ["app/ortak.js", "app/kesfet.js", "app/sahne.js"]){
    try { new vm.Script(fs.readFileSync(y, "utf8"), { filename: y }); }
    catch (e) { kotu.push(y + ": " + e.message); }
  }
  return kotu;
});

/* ---------- rapor ---------- */
const bitmis = await Promise.all(sonuclar);
let hata = 0;
for (const s of bitmis){
  console.log("  %s %s", s.gecti ? "gecti " : "BASARISIZ", s.ad);
  if (!s.gecti){ hata++; s.ayrinti.forEach(a => console.log("      " + String(a).slice(0, 300))); }
}
console.log(hata ? `\n${hata}/${bitmis.length} tarayici kontrolu BASARISIZ`
                 : `\n${bitmis.length} tarayici kontrolunun hepsi gecti`);
process.exit(hata ? 1 : 0);
