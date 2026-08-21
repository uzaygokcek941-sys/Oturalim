/* ============================================================
   Oturalım — tüm sayfaların paylaştığı davranış
   Tema, açılış saati mantığı, biçimlendirme, kohort ölçümü.
   Bağımlılık yok. Her sayfa <script src="ortak.js" defer> ile alır.
   ============================================================ */

/* ---------- tema ----------
   Seçim <head> içindeki küçük satır içi betikle uygulanıyor (FOUC olmasın).
   Buradaki iş yalnızca düğmeye davranış vermek. */
const TEMA_ANAHTAR = "oturalim.tema";

function temaUygula(t){
  if (t === "acik" || t === "koyu") document.documentElement.dataset.tema = t;
  else delete document.documentElement.dataset.tema;
  const koyuMu = t === "koyu" ||
    (!t && matchMedia("(prefers-color-scheme: dark)").matches);
  document.querySelectorAll("[data-tema-dugme]").forEach(d => {
    d.setAttribute("aria-label", koyuMu ? "Açık temaya geç" : "Koyu temaya geç");
    const ay = d.querySelector("[data-ay]"), gunes = d.querySelector("[data-gunes]");
    if (ay) ay.hidden = !koyuMu;
    if (gunes) gunes.hidden = koyuMu;
  });
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = koyuMu ? "#15110e" : "#fbf7f0";
}

function temaKur(){
  let t = null;
  try { t = localStorage.getItem(TEMA_ANAHTAR); } catch (e) {}
  temaUygula(t);
  document.querySelectorAll("[data-tema-dugme]").forEach(d =>
    d.addEventListener("click", () => {
      const suan = document.documentElement.dataset.tema ||
        (matchMedia("(prefers-color-scheme: dark)").matches ? "koyu" : "acik");
      const yeni = suan === "koyu" ? "acik" : "koyu";
      try { localStorage.setItem(TEMA_ANAHTAR, yeni); } catch (e) {}
      temaUygula(yeni);
    }));
}

/* ---------- biçimlendirme ---------- */
const tl = n => n == null ? "" : Math.round(n).toLocaleString("tr-TR") + " ₺";
const sayi = n => Number(n || 0).toLocaleString("tr-TR");
const kacir = s => String(s == null ? "" : s)
  .replace(/[&<>"]/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]));

/* ---------- açılış saati ----------
   OSM opening_hours'un tamamı çok geniş; Türkiye'de fiilen görülen biçimler:
   "24/7", "09:00-23:00", "Mo-Su 09:00-23:00", "Su-Th 12:00-22:00; Fr-Sa 12:00-23:30" */
const GUNLER = ["Su","Mo","Tu","We","Th","Fr","Sa"];

function gunUyar(ifade, gun){
  if (!ifade) return true;
  for (const p of ifade.split(",")){
    const [a,b] = p.split("-");
    const i = GUNLER.indexOf(a), j = b ? GUNLER.indexOf(b) : i;
    if (i < 0) continue;
    if (j >= i ? (gun >= i && gun <= j) : (gun >= i || gun <= j)) return true;
  }
  return false;
}

function acikMi(ifade, simdi){
  simdi = simdi || new Date();
  if (!ifade) return null;
  if (/24\/7/.test(ifade)) return true;
  const gun = simdi.getDay(), dk = simdi.getHours()*60 + simdi.getMinutes();
  let sonuc = null;
  for (const parca of ifade.split(";")){
    const m = parca.trim().match(/^(?:([A-Za-z,\-]+)\s+)?(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$/);
    if (!m) continue;
    if (!gunUyar(m[1], gun)) { if (sonuc === null) sonuc = false; continue; }
    const bas = +m[2]*60 + +m[3];
    let bit = +m[4]*60 + +m[5];
    if (bit <= bas) bit += 1440;                            // gece yarısını aşıyor
    if (dk >= bas && dk < bit) return true;
    if (dk + 1440 >= bas && dk + 1440 < bit) return true;   // dünden taşan aralık
    sonuc = false;
  }
  return sonuc;
}

/* ---------- bütçe bandı ----------
   Kişi başı bütçeyi mekanın menü fiyatlarıyla karşılaştırır.
   "Bu bütçeyle bu mekanda ne alınabilir" sorusunun cevabı; ortalama hesap değil. */
function bant(m, butce){
  if (m.min == null || !butce) return null;
  if (m.min > butce)  return { sinif:"tuz",  ad:"bütçe üstü" };
  if (m.max <= butce) return { sinif:"ucuz", ad:"menü tamamen bütçende" };
  return { sinif:"orta", ad:"bütçene giren seçenek var" };
}

/* ---------- fiyat seviyesi ----------
   Mekanların %1,2'sinde gerçek menü fiyatı var. Kalanı için tür ve OSM
   mutfak etiketi kullanılıyor; ikisi de sinyal vermiyorsa null dönüp kart
   hiçbir şey iddia etmiyor. Uydurma seviye, seviye yokluğundan kötüdür. */
const MUTFAK_HESAPLI = new Set(["burger","kebab","pizza","sandwich","chicken",
  "doner","kofte","pide","lahmacun","tea","coffee_shop","ice_cream","dessert",
  "breakfast","fish_and_chips","soup","turkish","regional","local"]);
const MUTFAK_UST = new Set(["steak_house","sushi","japanese","seafood","fish",
  "italian","french","international","fine_dining"]);

function seviye(m){
  if (m.min != null)
    return { sinif:"olcum", ad:tl(m.min) + "–" + tl(m.max), olculdu:true };
  if (m.tur === "Fast food" || m.tur === "Dondurma")
    return { sinif:"hesapli", ad:"hesaplı" };
  const mut = (m.mutfak || "").toLowerCase().split(/[;,]/).map(x => x.trim());
  if (mut.some(x => MUTFAK_UST.has(x)))     return { sinif:"ust",     ad:"üst segment" };
  if (mut.some(x => MUTFAK_HESAPLI.has(x))) return { sinif:"hesapli", ad:"hesaplı" };
  if (m.tur === "Bar" || m.tur === "Pub")   return { sinif:"icki",    ad:"içki mekanı" };
  return null;
}

/* ---------- kohort ölçümü ----------
   Çerezsiz ve sunucusuz: yalnız localStorage, yalnız bu cihaz.
   Hangi günlerde açıldığı tutuluyor; D1/D7/D30 buradan hesaplanıyor. */
const KOHORT = "oturalim.kohort";
const BIRGUN = 86400000;
const bugunISO = () => new Date().toISOString().slice(0,10);
const gunFarki = (a,b) => Math.round((Date.parse(b) - Date.parse(a)) / BIRGUN);

function kohortGuncelle(){
  let k = null;
  try { k = JSON.parse(localStorage.getItem(KOHORT)); } catch (e) { k = null; }
  if (!k || !k.ilk || !Array.isArray(k.gunler)) k = { ilk: bugunISO(), gunler: [] };
  const b = bugunISO();
  if (k.gunler.indexOf(b) < 0) k.gunler.push(b);
  k.gunler = k.gunler.slice(-90);
  try { localStorage.setItem(KOHORT, JSON.stringify(k)); } catch (e) {}
  return k;
}

function kohortOzet(k){
  const g = k.gunler.map(d => gunFarki(k.ilk, d));
  const varMi = (alt, ust) => g.some(x => x >= alt && x <= ust);
  return {
    ilkZiyaret: k.ilk,
    ziyaretGunu: k.gunler.length,
    kacGunluk: g.length ? Math.max.apply(null, g) : 0,
    geriDonen: k.gunler.length > 1,
    d1: varMi(1,1), d7: varMi(7,8), d30: varMi(30,32)
  };
}

/* ---------- kendi kendini kontrol:  ?test=1  ---------- */
function kendiniKontrolEt(){
  if (!new URLSearchParams(location.search).has("test")) return;
  const g14 = new Date(2026,7,19,14,0), g03 = new Date(2026,7,19,3,0),
        g01 = new Date(2026,7,19,1,0);
  const kontroller = [
    ["acikMi 24/7",             acikMi("24/7", g14),               true],
    ["acikMi gunduz",           acikMi("Mo-Su 09:00-23:00", g14),  true],
    ["acikMi gece kapali",      acikMi("Mo-Su 09:00-23:00", g03),  false],
    ["acikMi gece yarisi asan", acikMi("11:00-02:00", g01),        true],
    ["acikMi kapanmis",         acikMi("11:00-02:00", g03),        false],
    ["acikMi gun tutmuyor",     acikMi("Fr-Sa 20:00-23:00", g14),  false],
    ["acikMi bilgi yok",        acikMi("", g14),                   null],
    ["bant butce ustu",     (bant({min:300,max:900}, 200)||{}).sinif, "tuz"],
    ["bant tamamen icinde", (bant({min:30,max:120}, 200)||{}).sinif,  "ucuz"],
    ["bant kismen",         (bant({min:100,max:900}, 200)||{}).sinif, "orta"],
    ["bant fiyatsiz",       bant({min:null,max:null}, 200),           null],
    ["tl bicim",            tl(1250),                                 "1.250 ₺"],
    ["kacir xss",           kacir('<img src=x onerror=1>'),
                            "&lt;img src=x onerror=1&gt;"]
  ];
  const hata = kontroller.filter(k => JSON.stringify(k[1]) !== JSON.stringify(k[2]));
  document.body.insertAdjacentHTML("afterbegin",
    '<pre style="margin:0;padding:12px 16px;font:13px/1.5 ui-monospace,monospace;' +
    'white-space:pre-wrap;color:#fff;background:' + (hata.length ? "#5b1a1a" : "#1d3a17") + '">' +
    (hata.length
      ? "BASARISIZ (" + hata.length + "/" + kontroller.length + "):\n" +
        hata.map(h => "  " + h[0] + " -> " + JSON.stringify(h[1]) +
                      " beklenen " + JSON.stringify(h[2])).join("\n")
      : kontroller.length + " kontrolun hepsi gecti") + "</pre>");
}

/* ---------- açılış ---------- */
document.addEventListener("DOMContentLoaded", () => {
  temaKur();
  kohortGuncelle();
  kendiniKontrolEt();
});
