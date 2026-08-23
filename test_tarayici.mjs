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
function kosu(ad, calistir){
  try {
    const kotu = calistir();
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
let hata = 0;
for (const s of sonuclar){
  console.log("  %s %s", s.gecti ? "gecti " : "BASARISIZ", s.ad);
  if (!s.gecti){ hata++; s.ayrinti.forEach(a => console.log("      " + String(a).slice(0, 300))); }
}
console.log(hata ? `\n${hata}/${sonuclar.length} tarayici kontrolu BASARISIZ`
                 : `\n${sonuclar.length} tarayici kontrolunun hepsi gecti`);
process.exit(hata ? 1 : 0);
