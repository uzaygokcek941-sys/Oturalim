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
/* Butce karsilastirmasi YEMEK fiyatiyla yapilir. m.min ile yapilinca 100 TL
   butce giren kisiye ana yemegi 400 TL olan balikci "butcende" diye
   gosteriliyordu -- cunku m.min menudeki en ucuz icecekti. */
function bant(m, butce){
  const f = yemekFiyati(m);
  if (f == null || !butce) return null;
  if (f > butce) return { sinif:"tuz",  ad:"bütçe üstü" };
  return { sinif:"ucuz", ad:"bütçene giriyor" };
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

/* Eğlence mekanlarının menüsü yok; fiyat bilgisi tür seviyesinde kalıyor.
   Müze ve galeri Türkiye'de çoğunlukla düşük ücretli ya da ücretsiz; aquapark
   ve tema parkı günlük biletle pahalı. Ortada kalanlara "biletli" deyip
   rakam iddia etmiyoruz. */
const EGLENCE_UCUZ   = new Set(["Müze","Sanat galerisi","Sanat merkezi"]);
const EGLENCE_PAHALI = new Set(["Aquapark","Tema parkı","Kumarhane"]);
const EGLENCE_BILETLI= new Set(["Sinema","Tiyatro","Canlı müzik","Bowling",
  "Oyun salonu","Kaçış oyunu","Buz pisti","Trambolin parkı","Mini golf",
  "Hayvanat bahçesi","Akvaryum","Etkinlik alanı","Oyun merkezi","Dans salonu"]);

/* Eğlence türleri tek tek çip olamayacak kadar çok. Çip "grup:eglence"
   değerini taşır; süzgeç burada üyeliğe çevirir. Böylece çip mantığı ve URL
   biçimi değişmeden kalıyor. */
const TUR_GRUP = {
  eglence: new Set(["Gece kulübü","Sinema","Tiyatro","Canlı müzik",
    "Sanat merkezi","Etkinlik alanı","Kumarhane","Bowling","Oyun salonu",
    "Kaçış oyunu","Aquapark","Buz pisti","Trambolin parkı","Mini golf",
    "Dans salonu","Oyun merkezi","Müze","Tema parkı","Hayvanat bahçesi",
    "Akvaryum","Sanat galerisi"]),
  yeme: new Set(["Kafe","Restoran","Fast food","Dondurma","Bar","Pub"])
};

function turUyar(secili, tur){
  for (const s of secili){
    if (s.slice(0, 5) === "grup:"){
      const g = TUR_GRUP[s.slice(5)];
      if (g && g.has(tur)) return true;
    } else if (s === tur) return true;
  }
  return false;
}

/* Menudeki en ucuz kalem neredeyse her zaman bir ICECEK. m.min'i fiyat diye
   gostermek pahali bir baligiyi "25 TL'den baslar" yapiyordu (Milos Balik:
   min=25 "Aci Bal", ana yemek 350-590 TL). Kullaniciya lazim olan sey
   "burada bir YEMEK kac lira" -- icecek ve tatli disi kategorilerin medyani. */
const ICECEK_KAT = new Set(["Ayran","Kola / gazlı","Meyve suyu","Su","Filtre kahve",
  "Espresso","Çay","Türk kahvesi","Latte","Americano","Rakı / içkiler","Matcha",
  "Şarap","Bira","Sıcak çikolata"]);
const TATLI_KAT = new Set(["Tatlı","Dondurma"]);

/* Tema demosu esigi. 2026-08 fiyatlariyla bir ogun bunun altinda olmaz;
   enflasyonla birlikte yukseltilmeli, yoksa gercek ucuz yerleri eler. */
const YEMEK_ALT_SINIR = 80;
const TR_HARF = /[çğıöşüÇĞİÖŞÜ]/;

function yemekFiyati(m){
  const kat = m.kat;
  if (!kat) return null;                  /* kategori yoksa icecegi ayiramayiz */
  let ana = Object.keys(kat).filter(k => !ICECEK_KAT.has(k) && !TATLI_KAT.has(k));
  if (!ana.length) ana = Object.keys(kat).filter(k => TATLI_KAT.has(k));
  if (!ana.length) return null;

  const med = [];
  for (const k of ana) for (let i = 0; i < kat[k].n; i++) med.push(kat[k].med);
  med.sort((a, b) => a - b);
  const orta = Math.round(med[med.length >> 1]);

  /* Tema demosu: WordPress sablonundan gelen menuler Ingilizce ve ucuzdur
     ("Fish Tacos" 32 TL). Ikisi birden ise guvenme -- yanlis ucuzluk bu
     uygulamada yapilabilecek en kotu hata. */
  if (orta < YEMEK_ALT_SINIR){
    const mn = m.menu || [];
    if (mn.length >= 8 && !mn.some(k => TR_HARF.test(k.a))) return null;
  }
  return orta;
}

function seviye(m){
  const yf = yemekFiyati(m);
  if (yf != null)
    return { sinif:"olcum", ad:"yemek ~" + tl(yf), olculdu:true };
  if (m.tur === "Fast food" || m.tur === "Dondurma")
    return { sinif:"hesapli", ad:"hesaplı" };
  const mut = (m.mutfak || "").toLowerCase().split(/[;,]/).map(x => x.trim());
  if (mut.some(x => MUTFAK_UST.has(x)))     return { sinif:"ust",     ad:"üst segment" };
  if (mut.some(x => MUTFAK_HESAPLI.has(x))) return { sinif:"hesapli", ad:"hesaplı" };
  if (m.tur === "Bar" || m.tur === "Pub")   return { sinif:"icki",    ad:"içki mekanı" };
  if (EGLENCE_UCUZ.has(m.tur))  return { sinif:"hesapli", ad:"hesaplı" };
  if (EGLENCE_PAHALI.has(m.tur))return { sinif:"ust",     ad:"biletli, pahalı" };
  if (EGLENCE_BILETLI.has(m.tur))return { sinif:"biletli", ad:"biletli" };
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
    /* yemekFiyati: icecek fiyatinin yemek yerine gecmedigini kanitlar */
    ["yemek icecegi saymaz",
      yemekFiyati({kat:{"Kebap":{n:3,med:980},"Su":{n:1,med:30},"Çay":{n:1,med:40}}}), 980],
    ["yemek kat yoksa null", yemekFiyati({min:25, max:290}),          null],
    ["yemek tatlicida tatli",
      yemekFiyati({kat:{"Tatlı":{n:2,med:150},"Çay":{n:1,med:30}}}),  150],
    ["yemek tema demosu elenir",
      yemekFiyati({kat:{"Tavuk":{n:4,med:36}},
        menu:[{a:"Fish Tacos",f:32},{a:"Chicken Alfredo",f:36},{a:"French Fries",f:29},
              {a:"Prawns Fry",f:31},{a:"Vegetable Roll",f:25},{a:"Americano",f:38},
              {a:"Pizza Margherita",f:51},{a:"Berry Chocolate",f:29}]}), null],
    ["yemek ucuz ama turkce kalir",
      yemekFiyati({kat:{"Çorba":{n:2,med:60}},
        menu:[{a:"Mercimek Çorbası",f:60},{a:"Ayran",f:30}]}),        60],
    ["bant butce ustu",
      (bant({kat:{"Kebap":{n:1,med:400}}}, 200)||{}).sinif,           "tuz"],
    ["bant butce icinde",
      (bant({kat:{"Çorba":{n:1,med:120}}}, 200)||{}).sinif,           "ucuz"],
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
