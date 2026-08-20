/* ============================================================
   Oturalım — keşfet ekranı
   Liste + harita + filtreler. Durum URL'de taşınır, böylece filtreli
   bir görünüm olduğu gibi paylaşılabilir.
   ortak.js'in yüklenmiş olmasını bekler (acikMi, bant, tl, sayi, kacir).
   ============================================================ */
(() => {
"use strict";

const SAYFA = 120;        // listede bir seferde çizilen kart
const HARITA_UST = 700;   // haritaya basılan en fazla nokta (üstü donduruyor)

const el = s => document.querySelector(s);
const P  = new URLSearchParams(location.search);

/* ---------- durum ---------- */
let mekanlar = [],
    turler   = new Set(P.getAll("tur").filter(Boolean)),
    bayraklar= new Set(P.getAll("bayrak").filter(Boolean)),
    arama    = P.get("q") || "",
    sirala   = P.get("sirala") || "ad",
    butce    = +(P.get("butce") || 0),
    konum    = null,
    limit    = SAYFA,
    secili   = null,
    acilistaAcilacak = P.get("mekan") || null;

let harita, katman, isaretler = new Map();

/* ---------- yardımcılar ---------- */
function uzaklik(m){
  if (!konum) return 0;
  const dx = (m.lon - konum.lon) * 85, dy = (m.lat - konum.lat) * 111;  // km, kaba
  return Math.hypot(dx, dy);
}

/* Filtre durumunu adres çubuğuna yazar. Yeni geçmiş kaydı biriktirmemek için
   replaceState: geri tuşu keşfet ekranından çıkmalı, 40 filtreyi tek tek geri almamalı. */
function urlYaz(){
  const p = new URLSearchParams();
  p.set("il", el("#il").value);
  turler.forEach(t => p.append("tur", t));
  bayraklar.forEach(b => p.append("bayrak", b));
  if (arama) p.set("q", arama);
  if (sirala !== "ad") p.set("sirala", sirala);
  if (butce) p.set("butce", butce);
  history.replaceState(null, "", location.pathname + "?" + p);
}

function aracYuksekligiOlc(){
  const a = el("#arac");
  if (a) document.documentElement.style.setProperty("--arac-yukseklik", a.offsetHeight + "px");
}

/* ---------- süzme ---------- */
function suzulmus(){
  const l = mekanlar.filter(m => {
    if (turler.size && !turler.has(m.tur)) return false;
    if (bayraklar.has("bahce") && !m.bahce) return false;
    if (bayraklar.has("wifi")  && !m.wifi)  return false;
    if (bayraklar.has("menu")  && !m.menu)  return false;
    if (bayraklar.has("acik")  && acikMi(m.saat) !== true) return false;
    /* Bütçe süzgeci yalnız fiyatı bilinenleri eler. Fiyatı olmayan mekanı
       elemiyoruz: "bilinmiyor" ile "pahalı" aynı şey değil, listeden
       düşürmek kullanıcıyı yanıltır. */
    if (butce && m.min != null && m.min > butce) return false;
    if (arama && !((m.ad + " " + (m.mutfak || "") + " " + (m.adres || ""))
        .toLocaleLowerCase("tr").includes(arama))) return false;
    return true;
  });

  if (sirala === "ucuz")
    l.sort((a,b) => (a.min == null ? Infinity : a.min) - (b.min == null ? Infinity : b.min)
                    || a.ad.localeCompare(b.ad, "tr"));
  else if (sirala === "yakin" && konum)
    l.sort((a,b) => uzaklik(a) - uzaklik(b));
  else
    l.sort((a,b) => a.ad.localeCompare(b.ad, "tr"));
  return l;
}

/* ---------- çizim ---------- */
function kartHTML(m){
  const a = acikMi(m.saat), b = bant(m, butce), o = paylasimOzet(m.id);
  return '<button class="kart" type="button" data-id="' + kacir(m.id) + '"' +
    (secili === m.id ? ' aria-current="true"' : "") + ">" +
    '<div class="ust"><h3>' + kacir(m.ad) + "</h3>" +
    (m.min != null ? '<span class="tutar">' + tl(m.min) + "+</span>" : "") +
    '</div><div class="meta"><span>' + kacir(m.tur) + "</span>" +
    (a === true  ? '<span class="rozet acik">açık</span>' : "") +
    (a === false ? '<span class="rozet kapali">kapalı</span>' : "") +
    (b ? '<span class="bant ' + b.sinif + '">' + b.ad + "</span>" : "") +
    (m.bahce ? '<span class="rozet">bahçe</span>' : "") +
    (m.wifi  ? '<span class="rozet">wi-fi</span>' : "") +
    (konum ? '<span class="rozet">' + uzaklik(m).toFixed(1) + " km</span>" : "") +
    (o ? '<span class="rozet vurgulu">kişi başı ~' + tl(o.medyan) + "</span>" : "") +
    "</div></button>";
}

function ciz(haritayiOrtala){
  const l = suzulmus();
  const suzuluyor = turler.size || bayraklar.size || arama || butce;

  el("#sayac").textContent = sayi(l.length) + " mekan";
  el("#sayac-ek").textContent = butce ? "· bütçe " + tl(butce) : "";
  el("#sifirla").hidden = !suzuluyor;

  el("#kartlar").innerHTML = l.length
    ? l.slice(0, limit).map(kartHTML).join("") +
      (l.length > limit
        ? '<button class="daha" id="daha" type="button">' +
          sayi(l.length - limit) + " mekan daha göster</button>"
        : "")
    : '<p class="bos">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" ' +
      'stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/>' +
      '<path d="m20 20-3.5-3.5M8 11h6"/></svg>' +
      "<strong>Bu filtrelerle mekan yok</strong>" +
      "Bir iki filtreyi kaldırmayı dene.</p>";

  const d = el("#daha");
  if (d) d.addEventListener("click", () => { limit += SAYFA; ciz(false); });

  katmanCiz(l, haritayiOrtala);
  urlYaz();
}

/* ---------- harita ---------- */
function haritaKur(){
  harita = L.map("harita", { zoomControl:true, preferCanvas:true }).setView([39.92,32.85], 12);
  const koyuMu = () => (document.documentElement.dataset.tema ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "koyu" : "acik")) === "koyu";
  let dosem = null;
  const dosemKur = () => {
    if (dosem) harita.removeLayer(dosem);
    dosem = L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/" + (koyuMu() ? "dark_all" : "light_all") +
      "/{z}/{x}/{y}{r}.png",
      { maxZoom:19, attribution:"&copy; OpenStreetMap &copy; CARTO" }).addTo(harita);
  };
  dosemKur();
  katman = L.layerGroup().addTo(harita);
  /* Tema değişince harita döşemesi de dönmeli, yoksa koyu harita açık
     arayüzün ortasında yamalı duruyor. */
  new MutationObserver(dosemKur).observe(document.documentElement,
    { attributes:true, attributeFilter:["data-tema"] });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", dosemKur);
}

function katmanCiz(l, ortala){
  if (!katman) return;
  katman.clearLayers();
  isaretler.clear();
  const noktalar = [];
  const stil = getComputedStyle(document.documentElement);
  const vurgu = stil.getPropertyValue("--vurgu").trim() || "#f08a3c";
  const sonuk = stil.getPropertyValue("--metin-3").trim() || "#7d7264";

  l.slice(0, HARITA_UST).forEach(m => {
    const fiyatli = m.min != null;
    const i = L.circleMarker([m.lat, m.lon], {
      radius: fiyatli ? 7 : 5, weight:1.5,
      color: fiyatli ? vurgu : sonuk,
      fillColor: fiyatli ? vurgu : sonuk,
      fillOpacity: fiyatli ? .8 : .45
    }).addTo(katman);
    i.bindPopup("<b>" + kacir(m.ad) + "</b><br>" + kacir(m.tur) +
                (fiyatli ? " · " + tl(m.min) + "–" + tl(m.max) : ""));
    i.on("click", () => ac(m.id));
    isaretler.set(m.id, i);
    noktalar.push([m.lat, m.lon]);
  });

  if (ortala && noktalar.length)
    harita.fitBounds(noktalar, { padding:[36,36], maxZoom:14 });
}

/* ---------- kullanici fiyat paylasimlari ----------
   Onaylanmis paylasimlar mekan kimligine gore eslenir. Menu fiyatiyla
   karistirilmaz: menu isletmenin ilani, paylasim gercekten odenen tutar. */
let paylasimHaritasi = new Map();

async function paylasimlariYukle(il){
  paylasimHaritasi = new Map();
  const K = window.Kimlik;
  if (!K || !K.acik) return;
  await K.hazir;
  const liste = await K.onaylanmisPaylasimlar(il);
  liste.forEach(p => {
    if (!p.mekan_id) return;            // kimliksiz kayit eslenemiyor
    if (!paylasimHaritasi.has(p.mekan_id)) paylasimHaritasi.set(p.mekan_id, []);
    paylasimHaritasi.get(p.mekan_id).push(p);
  });
}

/* Medyan kisi basi tutar. Ortalama degil: tek bir asiri kayit
   ortalamayi kaydirir, medyan kaydirmaz. */
function paylasimOzet(mekanId){
  const l = paylasimHaritasi.get(mekanId);
  if (!l || !l.length) return null;
  const kisiBasi = l.map(p => Number(p.tutar) / Math.max(1, p.kisi)).sort((a,b) => a - b);
  const orta = Math.floor(kisiBasi.length / 2);
  const medyan = kisiBasi.length % 2 ? kisiBasi[orta] : (kisiBasi[orta-1] + kisiBasi[orta]) / 2;
  return { adet: l.length, medyan: Math.round(medyan), sonTarih: l[0].tarih };
}

/* ?test=1 ile medyan hesabini dogrula: tek asiri kayit ortalamayi kaydirir,
   medyan kaydirmamali. */
function paylasimKontrol(){
  if (!new URLSearchParams(location.search).has("test")) return;
  const yedek = paylasimHaritasi;
  const kur = kayitlar => { paylasimHaritasi = new Map([["x", kayitlar]]); return paylasimOzet("x"); };
  const T = [
    ["tek kayit",      kur([{tutar:480, kisi:2, tarih:"2026-08-20"}]).medyan, 240],
    ["cift sayida",    kur([{tutar:100,kisi:1,tarih:"1"},{tutar:300,kisi:1,tarih:"1"}]).medyan, 200],
    ["tek sayida",     kur([{tutar:100,kisi:1,tarih:"1"},{tutar:200,kisi:1,tarih:"1"},
                            {tutar:900,kisi:1,tarih:"1"}]).medyan, 200],
    ["kisi bolme",     kur([{tutar:900, kisi:3, tarih:"1"}]).medyan, 300],
    ["kisi sifir",     kur([{tutar:120, kisi:0, tarih:"1"}]).medyan, 120],
    ["adet sayimi",    kur([{tutar:100,kisi:1,tarih:"1"},{tutar:200,kisi:1,tarih:"1"}]).adet, 2],
    ["kayit yok",      (paylasimHaritasi = new Map(), paylasimOzet("yok")), null]
  ];
  paylasimHaritasi = yedek;
  const hata = T.filter(t => JSON.stringify(t[1]) !== JSON.stringify(t[2]));
  document.body.insertAdjacentHTML("afterbegin",
    '<pre style="margin:0;padding:10px 16px;font:13px ui-monospace,monospace;color:#fff;' +
    'background:' + (hata.length ? "#5b1a1a" : "#1d3a17") + '">' +
    (hata.length ? "PAYLASIM MEDYAN BASARISIZ: " + JSON.stringify(hata)
                 : T.length + " medyan kontrolu gecti") + "</pre>");
}

/* ---------- favoriler ----------
   Kimlik katmani opsiyonel: kurulu degilse dugme hic gorunmez,
   kesfet ekraninin geri kalani aynen calisir. */
let favoriKumesi = new Set();

async function favorileriYukle(){
  const K = window.Kimlik;
  if (!K || !K.acik) return;
  await K.hazir;
  if (!K.girisli){ favoriKumesi = new Set(); return; }
  const liste = await K.favoriler();
  favoriKumesi = new Set(liste.map(f => f.mekan_id));
}

function favoriDugmesiniTazele(m){
  const d = el("#d-favori");
  if (!d) return;
  const K = window.Kimlik;
  if (!K || !K.acik){ d.hidden = true; return; }
  d.hidden = false;
  d.dataset.mekan = m.id;
  const ekli = favoriKumesi.has(m.id);
  d.setAttribute("aria-pressed", String(ekli));
  el("#d-favori-metin").textContent =
    !K.girisli ? "Favorilere ekle" : ekli ? "Favorilerimde" : "Favorilere ekle";
  el("#d-favori-ikon").setAttribute("fill", ekli ? "currentColor" : "none");
  d.classList.toggle("ikincil", !ekli);
}

async function favoriDegistir(){
  const K = window.Kimlik, d = el("#d-favori");
  const id = d.dataset.mekan;
  const m = mekanlar.find(x => x.id === id);
  if (!m) return;
  if (!K.girisli){
    location.href = "giris.html?donus=" +
      encodeURIComponent("kesfet.html?il=" + el("#il").value + "&mekan=" + id);
    return;
  }
  d.disabled = true;
  try {
    if (favoriKumesi.has(id)){ await K.favoriSil(id); favoriKumesi.delete(id); }
    else { await K.favoriEkle(m, el("#il").value); favoriKumesi.add(id); }
    favoriDugmesiniTazele(m);
  } catch (e){
    alert(e.message);
  } finally {
    d.disabled = false;
  }
}

/* ---------- detay ---------- */
function ac(id){
  const m = mekanlar.find(x => x.id === id);
  if (!m) return;
  secili = id;
  document.querySelectorAll(".kart").forEach(k => {
    if (k.dataset.id === id) k.setAttribute("aria-current", "true");
    else k.removeAttribute("aria-current");
  });

  const a = acikMi(m.saat), b = bant(m, butce);
  el("#d-ad").textContent = m.ad;
  el("#d-meta").innerHTML =
    '<span class="rozet vurgulu">' + kacir(m.tur) + "</span>" +
    (a === true  ? '<span class="rozet acik">şu an açık</span>' : "") +
    (a === false ? '<span class="rozet kapali">şu an kapalı</span>' : "") +
    (b ? '<span class="bant ' + b.sinif + '">' + b.ad + "</span>" : "") +
    (m.bahce ? '<span class="rozet">bahçe</span>' : "") +
    (m.wifi  ? '<span class="rozet">wi-fi</span>' : "");

  const satir = (yol, icerik) =>
    '<div><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + yol +
    "</svg><span>" + icerik + "</span></div>";

  const IK = {
    adres: '<path d="M12 21s7-6.4 7-11a7 7 0 1 0-14 0c0 4.6 7 11 7 11Z"/><circle cx="12" cy="10" r="2.6"/>',
    saat:  '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    tel:   '<path d="M5 4h4l2 5-2.5 1.5a12 12 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/>',
    web:   '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18 15 15 0 0 1 0-18Z"/>',
    mutfak:'<path d="M3 2v7a3 3 0 0 0 3 3v10M9 2v7a3 3 0 0 1-3 3"/><path d="M17 2c-1.7 1.3-2.5 3.4-2.5 6 0 2 .8 3.4 2.5 4v10"/>'
  };

  const bilgi = [
    m.adres  ? satir(IK.adres,  kacir(m.adres)) : "",
    m.mutfak ? satir(IK.mutfak, kacir(m.mutfak.replace(/;/g, ", "))) : "",
    m.saat   ? satir(IK.saat,   kacir(m.saat)) : "",
    m.tel    ? satir(IK.tel, '<a href="tel:' + kacir(m.tel.replace(/\s/g,"")) + '">' +
                             kacir(m.tel) + "</a>") : "",
    m.web    ? satir(IK.web, '<a href="' + kacir(m.web) + '" target="_blank" rel="noopener">' +
                             kacir(m.web.replace(/^https?:\/\//,"").replace(/\/$/,"")) + "</a>") : ""
  ].filter(Boolean).join("");

  let govde = bilgi ? '<div class="d-bilgi">' + bilgi + "</div>" : "";

  /* Kullanici paylasimi menuden AYRI gosteriliyor: biri isletmenin ilan
     ettigi liste fiyati, digeri insanlarin fiilen odedigi tutar. */
  const o = paylasimOzet(m.id);
  if (o){
    govde +=
      '<div class="odenen">' +
      '<div class="odenen-bas"><span>Gerçekten ödenen</span>' +
      '<b>' + tl(o.medyan) + "</b></div>" +
      '<p>Kişi başı medyan tutar. ' + sayi(o.adet) +
      (o.adet === 1 ? " kişinin paylaşımından" : " paylaşımdan") +
      " hesaplandı; son bilgi " + new Date(o.sonTarih).toLocaleDateString("tr-TR",
        { day:"numeric", month:"long", year:"numeric" }) + ".</p></div>";
  }

  if (m.menu){
    /* Menü ucuzdan pahalıya: bütçesi olan kullanıcı önce ne alabileceğini
       görsün, listenin dibine inmek zorunda kalmasın. */
    const sirali = m.menu.slice().sort((x,y) => x.f - y.f);
    govde +=
      '<div class="d-menu-bas"><h3>Menü</h3><span>' + sayi(m.menu.length) +
      " kalem · " + tl(m.min) + " – " + tl(m.max) + "</span></div>" +
      sirali.map(k =>
        '<div class="kalem' + (butce && k.f > butce ? " disi" : "") + '">' +
        "<span>" + kacir(k.a) + "</span><b>" + tl(k.f) + "</b></div>").join("") +
      '<p class="uyari">İşletmenin kendi sitesinde yayımladığı fiyatlar. ' +
      "Ortalama hesap değildir, değişmiş olabilir.</p>";
  } else {
    govde +=
      '<p class="bos" style="padding:var(--a6) 0">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" ' +
      'stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h10M4 17h7"/></svg>' +
      "<strong>Bu mekanın fiyatı henüz yok</strong>" +
      "Gittiysen hesabını paylaş, ilk sen ekle.</p>";
  }

  el("#d-govde").innerHTML = govde;
  el("#d-govde").scrollTop = 0;
  el("#d-yol").href = "https://www.google.com/maps/dir/?api=1&destination=" + m.lat + "," + m.lon;
  el("#d-paylas").href = "paylas.html?mekan=" + encodeURIComponent(m.ad) +
                         "&il=" + encodeURIComponent(el("#il").value) +
                         "&mekanId=" + encodeURIComponent(m.id);
  favoriDugmesiniTazele(m);
  el("#detay").showModal();

  const i = isaretler.get(id);
  if (i){ harita.setView([m.lat, m.lon], Math.max(harita.getZoom(), 15)); i.openPopup(); }
}

/* ---------- veri yükleme ---------- */
function ilYukle(kod, ilkAcilis){
  el("#sayac").textContent = "yükleniyor…";
  el("#kartlar").innerHTML =
    '<div style="padding:var(--a4) var(--a5);display:grid;gap:var(--a4)">' +
    Array.from({length:7}, () =>
      '<div><div class="iskelet" style="height:17px;width:62%"></div>' +
      '<div class="iskelet" style="height:13px;width:38%;margin-top:9px"></div></div>').join("") +
    "</div>";

  fetch("veri/" + kod + ".json").then(r => {
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }).then(v => {
    mekanlar = v.mekanlar;
    paylasimlariYukle(kod).then(() => ciz(false));
    limit = SAYFA;
    secili = null;
    ciz(true);
    /* Anasayfadaki vitrin kartından gelindiyse o mekanı doğrudan aç */
    if (ilkAcilis && acilistaAcilacak){
      const hedef = acilistaAcilacak;
      acilistaAcilacak = null;
      if (mekanlar.some(m => m.id === hedef)) ac(hedef);
    }
  }).catch(e => {
    el("#sayac").textContent = "hata";
    el("#kartlar").innerHTML = '<p class="bos"><strong>Veri yüklenemedi</strong>' +
      kacir(e.message) + "</p>";
  });
}

/* ---------- konum ----------
   İzin açılışta DEĞİL, kullanıcı "bana yakın"ı seçince isteniyor:
   gerekçesiz izin kutusu ilk izlenimi yakıyor ve çoğu kullanıcı reddediyor. */
function konumIste(bitince){
  if (konum || !navigator.geolocation){ bitince(); return; }
  navigator.geolocation.getCurrentPosition(
    p => { konum = { lat:p.coords.latitude, lon:p.coords.longitude }; bitince(); },
    () => { el("#sirala").value = sirala = "ad"; bitince(); },
    { timeout:6000 });
}

/* ---------- bütçe göstergesi ---------- */
function butceYaz(){
  el("#butce-deger").textContent = butce ? tl(butce) : "kapalı";
  el("#butce-kutu").classList.toggle("etkin", !!butce);
}

/* ---------- açılış ---------- */
document.addEventListener("DOMContentLoaded", () => {
  aracYuksekligiOlc();
  addEventListener("resize", aracYuksekligiOlc);

  /* URL'den gelen filtreleri düğmelere yansıt */
  document.querySelectorAll(".cip[data-tur],.cip[data-bayrak]").forEach(b => {
    const anahtar = b.dataset.tur || b.dataset.bayrak;
    const kume = b.dataset.tur ? turler : bayraklar;
    b.setAttribute("aria-pressed", String(kume.has(anahtar)));
  });
  el("#ara").value = arama;
  el("#sirala").value = sirala;
  el("#butce").value = butce;
  butceYaz();

  haritaKur();

  /* şehir listesi */
  const secim = el("#il");
  let kayitli = null;
  try { kayitli = localStorage.getItem("oturalim.il"); } catch (e) {}

  fetch("veri/index.json").then(r => r.json()).then(d => {
    secim.innerHTML = d.iller.map(i =>
      '<option value="' + i.kod + '">' + kacir(i.ad) + "</option>").join("");
    const istenen = P.get("il");
    secim.value = d.iller.some(i => i.kod === istenen) ? istenen
                : d.iller.some(i => i.kod === kayitli) ? kayitli
                : d.varsayilan;
    ilYukle(secim.value, true);
    secim.addEventListener("change", () => {
      try { localStorage.setItem("oturalim.il", secim.value); } catch (e) {}
      ilYukle(secim.value, false);
    });
  }).catch(e => {
    el("#kartlar").innerHTML = '<p class="bos"><strong>İl listesi yüklenemedi</strong>' +
      kacir(e.message) + "</p>";
  });

  /* liste tıklaması */
  el("#kartlar").addEventListener("click", e => {
    const k = e.target.closest(".kart");
    if (k) ac(k.dataset.id);
  });

  /* arama — her tuşta değil, yazma durunca çiz (uzun listede takılıyordu) */
  let zaman;
  el("#ara").addEventListener("input", e => {
    clearTimeout(zaman);
    const v = e.target.value.toLocaleLowerCase("tr");
    zaman = setTimeout(() => { arama = v; limit = SAYFA; ciz(false); }, 180);
  });

  el("#sirala").addEventListener("change", e => {
    sirala = e.target.value; limit = SAYFA;
    if (sirala === "yakin") konumIste(() => ciz(false)); else ciz(false);
  });

  el("#butce").addEventListener("input", e => { butce = +e.target.value; butceYaz(); });
  el("#butce").addEventListener("change", () => { limit = SAYFA; ciz(false); });

  el("#cipler").addEventListener("click", e => {
    const b = e.target.closest(".cip[data-tur],.cip[data-bayrak]");
    if (!b) return;
    const acikDurum = b.getAttribute("aria-pressed") === "true";
    b.setAttribute("aria-pressed", String(!acikDurum));
    const kume = b.dataset.tur ? turler : bayraklar;
    const anahtar = b.dataset.tur || b.dataset.bayrak;
    if (acikDurum) kume.delete(anahtar); else kume.add(anahtar);
    limit = SAYFA;
    ciz(false);
  });

  el("#sifirla").addEventListener("click", () => {
    turler.clear(); bayraklar.clear();
    arama = ""; butce = 0; limit = SAYFA;
    el("#ara").value = ""; el("#butce").value = 0;
    document.querySelectorAll(".cip[data-tur],.cip[data-bayrak]")
      .forEach(b => b.setAttribute("aria-pressed", "false"));
    butceYaz();
    ciz(true);
  });

  /* mobil sekme */
  document.querySelectorAll(".sekme button").forEach(b =>
    b.addEventListener("click", () => {
      document.querySelectorAll(".sekme button").forEach(x =>
        x.setAttribute("aria-selected", String(x === b)));
      el("#govde").dataset.gorunum = b.dataset.gorunum;
      /* Leaflet gizliyken boyut alamıyor; görünür olunca yeniden ölçtür. */
      if (b.dataset.gorunum === "harita" && harita)
        setTimeout(() => harita.invalidateSize(), 60);
    }));

  document.querySelectorAll("[data-kapat]").forEach(b =>
    b.addEventListener("click", () => el("#detay").close()));

  const favDugme = el("#d-favori");
  if (favDugme) favDugme.addEventListener("click", favoriDegistir);
  favorileriYukle();
  paylasimKontrol();
});
})();
