/* ============================================================
   Cebimde — keşfet ekranı
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

const TR_SADE = { "ç":"c","ğ":"g","ı":"i","ö":"o","ş":"s","ü":"u",
                  "â":"a","î":"i","û":"u",
                  "Ç":"c","Ğ":"g","İ":"i","I":"i","Ö":"o","Ş":"s","Ü":"u",
                  "Â":"a","Î":"i","Û":"u" };
/* Turkce harfleri ASCII'ye indirip kucultur. Ada gore ARAMA da bunu
   kullaniyor: kullanicilarin cogu Turkce harfsiz yaziyor ve eslesme
   olmayinca sonuc yok saniyorlar. Olculdu (Istanbul):
     "köfte" 574 mekan  ama  "kofte"  33
     "çiğ"   343        ama  "cig"    12
     "şişli"   4        ama  "sisli"   1
   Yani harfsiz yazan kullanici sonuclarin %94'unu hic gormuyordu.
   Once degistirip SONRA kucultmek onemli: "İ".toLowerCase() birlesen
   bir ust nokta birakiyor ve hicbir seye eslesmiyor. */
const sade = s => (s || "").replace(/[çğıöşüâîûÇĞİIÖŞÜÂÎÛ]/g, c => TR_SADE[c]).toLowerCase();

/* ---------- durum ---------- */
let zincir = null;
let mekanlar = [],
    turler   = new Set(P.getAll("tur").filter(Boolean)),
    bayraklar= new Set(P.getAll("bayrak").filter(Boolean)),
    arama    = sade(P.get("q") || ""),
    sirala   = P.get("sirala") || "ad",
    butce    = +(P.get("butce") || 0),
    konum    = null,
    limit    = SAYFA,
    secili   = null,
    acilistaAcilacak = P.get("mekan") || null;

let ilkCizimOldu = false;
let cetvelTavan = 0;   // gorunen listedeki en uzak mesafe (km)

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
    if (turler.size && !turUyar(turler, m.tur)) return false;
    if (bayraklar.has("bahce") && !m.bahce) return false;
    if (bayraklar.has("wifi")  && !m.wifi)  return false;
    /* "Fiyati olan" cipi yemekFiyati'na bakiyor, m.menu varligina DEGIL.
       Onceden 367 mekan donuyordu ama 203'unun kartinda fiyat yazmiyordu:
       cip fiyat vaat edip fiyatsiz kart veriyordu. Siralama ("once ucuz"),
       butce bandi ve haritadaki nokta zaten yemekFiyati kullaniyor; olcut
       dort yerde ayni olsun. Menuyu gormek isteyen mekan sayfasindan
       kalem listesine bakabiliyor. */
    if (bayraklar.has("menu")  && yemekFiyati(m) == null) return false;
    /* "Fisi olan": ESIGI GECEN fis. Cip fis vaat edip esik yuzunden
       rakamsiz kart vermesin -- "Fiyati olan" cipinde tam bu hata
       yasandi (367 mekan donuyordu, 203'unun kartinda fiyat yoktu).
       Olcut cip, rozet ve detay panelinde AYNI: fisGoster(). */
    if (bayraklar.has("fis") && !fisGoster(paylasimOzet(m.id))) return false;
    if (bayraklar.has("acik")  && acikMi(m.saat) !== true) return false;
    /* Bütçe süzgeci yalnız BÜTÇE ÜSTÜ OLDUĞU ÖLÇÜLMÜŞ mekanı eler.
       Fiyatı olmayanı elemiyoruz: "bilinmiyor" ile "pahalı" aynı şey
       değil, listeden düşürmek kullanıcıyı yanıltır. Tahmine ("üst
       segment") dayanarak da elemiyoruz -- pahalı SANMAK ile pahalı
       BİLMEK ayrı şeyler.

       Kural butceDurumu()'nda ve ana ekran da aynı yerden geçiyor:
       önceden karşılaştırma iki ekranda ayrı ayrı yazılıydı ve birini
       değiştiren ötekini sessizce ayrıştırabiliyordu. */
    const bd = butceDurumu(m, butce);
    if (bd && bd.sinif === "asiyor") return false;
    /* Aranan metin de aranan yer de AYNI sadelestirmeden geciyor:
       "kofte" yazan da "köfte" yazan da ayni sonucu gormeli. */
    if (arama && !sade(m.ad + " " + (m.mutfak || "") + " " + (m.adres || ""))
        .includes(arama)) return false;
    return true;
  });

  if (sirala === "ucuz")
    l.sort((a,b) => ((yemekFiyati(a) == null) ? Infinity : yemekFiyati(a)) -
                    ((yemekFiyati(b) == null) ? Infinity : yemekFiyati(b))
                    || a.ad.localeCompare(b.ad, "tr"));
  else if (sirala === "yakin" && konum)
    l.sort((a,b) => uzaklik(a) - uzaklik(b));
  else
    l.sort((a,b) => a.ad.localeCompare(b.ad, "tr"));
  return l;
}

/* 1 km altında metre yazmak "0.3 km"den okunur. */
function mesafeYaz(km){
  return km < 1 ? Math.round(km * 1000) + " m" : km.toFixed(1) + " km";
}

let cizimIl = "";

/* Secili ilin ekrandaki adi. Olcutun il kirilimi buna gore araniyor. */
function ilAdi(){
  const s = el("#il");
  return s && s.selectedOptions[0] ? s.selectedOptions[0].textContent.trim() : "";
}

/* ---------- çizim ---------- */
function kartHTML(m){
  const a = acikMi(m.saat), b = bant(m, butce), o = paylasimOzet(m.id),
        sv = seviye(m), mb = mekanBandi(m, cizimIl), yas = fiyatYasEtiketi(m),
        dy = fiyatDayanagi(m, zincir), gv = fiyatGuveni(m, zincir, o);
  /* Mesafe cetveli icin 0-1 arasi deger, GORUNEN listeye gore olceklenir.
     Sabit tavan (5 km) ise yaramiyor: sehir merkezinde ilk 120 mekan
     700 m icinde kaliyor, butun centikler ayni uzunlukta cikiyordu.
     Konum yoksa cetvel hic cizilmiyor (stil --uzak varligina bakiyor). */
  const u = konum ? Math.min(1, uzaklik(m) / (cetvelTavan || 1)) : null;
  return '<button class="kart" type="button" data-id="' + kacir(m.id) + '"' +
    (u != null ? ' style="--uzak:' + u.toFixed(3) + '"' : "") +
    (secili === m.id ? ' aria-current="true"' : "") + ">" +
    /* GUVEN NOKTASI adin yaninda, KISA halde: liste 2.300 karta kadar
       cikiyor ve her karta "fiyat yok" yazmak listeyi ayni cumleyle
       doldururdu. Renk tek basina bilgi tasimiyor -- aria-label ve
       title tam gerekceyi veriyor, panelde de yazili hali var. */
    '<div class="ust"><h3>' + guvenRozeti(gv, true) + kacir(m.ad) + "</h3>" +
    /* Fiyatin yasi kartta da gorunsun. Detay paneli tarihi yaziyor ama
       kart listesinde gezen kullanici oraya hic acmiyor olabilir; alti
       aylik bir sayiyi kayitsiz gostermek, kullanicinin dogrulayamadigi
       bir iddia. Rozet degil, RAKAMIN KENDISI isaretleniyor: kartta
       zaten uc rozet var ve dordunculeri asil bilgiyi bogar. */
    (yemekFiyati(m) != null
      ? '<span class="tutar' + (yas && yas.eski ? " eski" : "") + '"' +
        (yas || dy ? ' title="' + kacir(
          [yas ? yas.ad + " tarihinde derlendi" : "",
           dy && dy.sinif === "zincir" ? dy.ad : ""].filter(Boolean).join(" · ")) + '"' : "") +
        ">~" + tl(yemekFiyati(m)) +
        /* Isaret CSS ::after ile degil GERCEK METIN: ekran okuyucu
           uretilmis icerigi guvenilir bicimde okumuyor ve title
           oznitelik tek basina yeterli degil. */
        /* Bosluk GERCEK METIN olarak duruyor: margin-left gorsel ayrimi
           veriyor ama ekran okuyucu "243 ₺eski" diye tek parca okuyordu. */
        (yas && yas.eski ? ' <small class="eski-not">eski</small>' : "") +
        /* ZINCIR ISARETI. Olculdu: fiyati gosterilen 163 mekan yalniz 53
           farkli isletme; 94'u Domino's subesi ve ayni ilde cok subeli
           113 mekanin hicbirinde subeler arasi fiyat farki yok. Yani tek
           kazima 56 ayri olcum gibi listeleniyordu.

           ROZET DEGIL, RAKAMIN KENDISININ ISARETI -- "eski" ile ayni
           gerekce: kartta zaten uc rozet var ve dorduncusu asil bilgiyi
           bogar. Isaret GERCEK METIN, ::after degil: ekran okuyucu
           uretilmis icerigi guvenilir okumuyor. */
        (dy && dy.sinif === "zincir"
          ? ' <small class="zincir-not">zincir</small>' : "") +
        "</span>" : "") +
    '</div><div class="meta"><span>' + kacir(m.tur) + "</span>" +
    (a === true  ? '<span class="rozet acik">açık</span>' : "") +
    (a === false ? '<span class="rozet kapali">kapalı</span>' : "") +
    (b ? '<span class="bant ' + b.sinif + '">' + b.ad + "</span>" : "") +
    /* Sira: butce bandi > mekan bandi > tur/mutfak tahmini.
       Butce girilmisse kullanicinin sordugu soru "butceme giriyor mu";
       girilmemisse "burasi ucuz mu". Ucu birden basmak kartta uc rozet
       demek olurdu ve ucu de ayni seyi soylemeye calisiyor. */
    (!b && mb ? '<span class="bant ' + mb.sinif + '">' + mb.ad + "</span>" : "") +
    (!b && !mb && sv && !sv.olculdu
      ? '<span class="seviye ' + sv.sinif + '">' + sv.ad + "</span>" : "") +
    (m.bahce ? '<span class="rozet">bahçe</span>' : "") +
    (m.wifi  ? '<span class="rozet">wi-fi</span>' : "") +
    (konum ? '<span class="rozet mesafe">' + mesafeYaz(uzaklik(m)) + "</span>" : "") +
    /* ESIK: fisGoster() olmadan burasi TEK FISTEN tutar basiyordu --
       isletme sayfasinin k-anonimlik icin gizledigi seyi bu ekran
       yayimliyordu. Kural ortak.js'te, karar tek yerde. */
    (fisGoster(o) ? '<span class="rozet vurgulu">kişi başı ~' + tl(o.medyan) + "</span>" : "") +
    "</div></button>";
}

function ciz(haritayiOrtala){
  const l = suzulmus();
  const suzuluyor = turler.size || bayraklar.size || arama || butce;

  el("#sayac").textContent = sayi(l.length) + " mekan";
  el("#sayac-ek").textContent = butce ? "· bütçe " + tl(butce) : "";

  /* Gorunmez h1 secili sehri soyluyor. Sabit birakmak, sehir
     degistiginde sayfanin basligini yanlis yapardi. */
  const b = el("#baslik");
  if (b) b.textContent = (ilAdi() || "Türkiye") + " mekanları — Cebimde";
  el("#sifirla").hidden = !suzuluyor;

  /* Sicrama girisi YALNIZ ilk cizimde. Her filtre degisiminde tekrar
     oynarsa arac hissi bozuluyor -- burasi kesfet, gosteri degil. */
  /* Cetvel tavani: cizilecek kartlarin en uzagi. kartHTML'den ONCE
     hesaplanmali, cunku her kart bu tavana gore olcekleniyor. */
  cetvelTavan = konum
    ? l.slice(0, limit).reduce((e, m) => Math.max(e, uzaklik(m)), 0)
    : 0;
  /* Cizim basina bir kez: kartHTML her kart icin DOM'a sormasin.
     cetvelTavan ile ayni gerekce, ayni desen. */
  cizimIl = ilAdi();

  const kutu = el("#kartlar");
  kutu.classList.toggle("ilk-cizim", !ilkCizimOldu);
  ilkCizimOldu = true;

  kutu.innerHTML = l.length
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

/* ---------- harita ----------
   Leaflet bir CDN'den geliyor ve gelmeyebiliyor: kesinti, kurumsal ag,
   okul agi, ulke capinda engel. Olculdu -- unpkg erisilemedigi anda
   "L is not defined" firliyordu ve kesfet ekraninin TAMAMI oluyordu:
   sifir kart, sayac "…"da donmus, bos sayfa. Oysa liste, filtreler,
   butce kaydiricisi ve siralama haritaya hic ihtiyac duymuyor.

   Harita artik ISTEGE BAGLI. Yoksa yerine ne oldugunu soyleyen bir kutu
   konuyor ve sayfanin geri kalani calismaya devam ediyor. */
function haritaVar(){ return typeof L !== "undefined" && harita; }

function haritaYok(){
  const kutu = el("#harita");
  if (kutu) kutu.innerHTML =
    '<div class="harita-yok">' +
    "<strong>Harita yüklenemedi</strong>" +
    "<span>Bağlantı engellenmiş olabilir. Liste, filtreler ve bütçe " +
    "kaydırıcısı çalışmaya devam ediyor.</span></div>";
}

function haritaKur(){
  /* typeof: L tanimli degilse duz "if (!L)" ReferenceError firlatir --
     korumanin kendisi cokerdi. */
  if (typeof L === "undefined"){ haritaYok(); return; }
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
  const vurgu = stil.getPropertyValue("--vurgu").trim() || "#ff7a00";
  const sonuk = stil.getPropertyValue("--metin-3").trim() || "#7d7264";
  /* HARITA BUTCEYE GORE RENKLENIYOR. Renkler CSS'ten okunuyor, burada
     ikinci kez tanimlanmiyor: tema degisince (acik/koyu) palet de
     degisiyor ve sabit bir onaltilik deger acik temada okunmaz hale
     gelirdi -- ayni sorun kartlarda yasandi.

     Butce GIRILMEMISSE renklendirme yapilmiyor: eski davranis (fiyati
     bilinen vurgulu, bilinmeyen sonuk) duruyor. Sorulmamis bir soruya
     harita uzerinden cevap vermek, kullanicinin girmedigi bir butceyi
     varsaymak olurdu. */
  const bRenk = {
    girer:      stil.getPropertyValue("--bant-ucuz").trim() || "#00bfa6",
    asiyor:     stil.getPropertyValue("--bant-tuz").trim()  || "#ff5a5f",
    muhtemel:   stil.getPropertyValue("--bant-orta").trim() || "#ffb74d",
    zor:        sonuk,
    bilinmiyor: sonuk
  };

  l.slice(0, HARITA_UST).forEach(m => {
    const yf = yemekFiyati(m), fiyatli = yf != null;
    /* butceDurumu() ayni kapi: kart rozeti, suzgec ve ana ekran da
       oradan geciyor. Harita ayri bir olcut kullansaydi ayni mekan
       listede "bütçene giriyor", haritada baska renk olurdu. */
    const bd = butceDurumu(m, butce);
    const r = bd ? bRenk[bd.sinif] : (fiyatli ? vurgu : sonuk);
    /* Kesin bilinenler (olculmus) dolu ve buyuk, tahminler soluk ve
       kucuk: renk "hangi bantta", doygunluk "ne kadar eminiz" diyor. */
    const kesin = bd ? bd.kesin : fiyatli;
    const i = L.circleMarker([m.lat, m.lon], {
      radius: kesin ? 7 : 5, weight:1.5,
      color: r, fillColor: r,
      fillOpacity: kesin ? .85 : .4
    }).addTo(katman);
    i.bindPopup("<b>" + kacir(m.ad) + "</b><br>" + kacir(m.tur) +
                (fiyatli ? " · ortalama " + tl(yf) : "") +
                (bd ? "<br>" + kacir(bd.ad) : ""));
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

/* ---------- butce akranlari ----------
   "Benim butcemdeki insanlar nereye gidiyor." Fis katmani tek bir mekani
   anlatiyor; bu satir butcenin kendisini anlatiyor.

   NEDEN SUNUCUYA SORULUYOR: "kac KISI" ile "kac FIS" ayri seyler ve fark
   bu ozelligin butun anlami -- uc fisi olan tek kisi bir akran toplulugu
   degil. Tarayici bunu ayirt edemez, cunku `kullanici` sutunu ona kapali
   (sema.sql). Sayim akran.sql'de.

   ISTEK BASINA BIR CAGRI DEGIL: kaydirici surukleyince "input" saniyede
   onlarca kez tetikleniyor. Cagri yalniz "change" ile, yani parmak
   kalkinca gidiyor; ustelik son cevap disindaki cevaplar ATILIYOR --
   yavas donen eski bir istek yeni butcenin sayisini ezmesin. */
let akranSayac = 0;

async function akranYaz(){
  const kutu = el("#akran");
  if (!kutu) return;
  if (!butce){ kutu.hidden = true; kutu.textContent = ""; return; }

  const benim = ++akranSayac;
  const K = window.Kimlik;
  if (!K || !K.acik){ kutu.hidden = true; return; }

  let o = null;
  try {
    await K.hazir;
    o = await K.butceAkranlari(el("#il").value, butce);
  } catch (e) { /* akran.sql kurulu degil ya da ag yok: satir hic cikmasin */ }

  if (benim !== akranSayac) return;         /* gecikmis cevap: at */
  const c = akranCumlesi(o, butce);
  if (!c){ kutu.hidden = true; kutu.textContent = ""; return; }
  kutu.textContent = c;
  kutu.hidden = false;
}

/* Medyan kisi basi tutar. Ortalama degil: tek bir asiri kayit
   ortalamayi kaydirir, medyan kaydirmaz. */
/* Ürün kategorisi ölçütü: "Ankara'da latte kaç TL olmalı".
   Dosya yoksa kırılım yine gösterilir, sadece ucuz/pahalı işareti çıkmaz. */
let olcut = null;

function olcutYukle(){
  if (olcut) return Promise.resolve(olcut);
  return fetch("veri/fiyat_olcut.json")
    .then(r => r.ok ? r.json() : null)
    .then(d => (olcut = d || { turkiye:{}, il:{} }))
    .catch(() => (olcut = { turkiye:{}, il:{} }));
}

/* Ölçüt dosyasındaki il adları kaynak CSV'den geldiği için ASCII
   ("Istanbul"), uygulamadaki liste ise düzgün Türkçe ("İstanbul").
   Karşılaştırmadan önce ikisi de sade() ile sadeleştiriliyor (yukarıda). */

/* Ölçüt kaç markadan çıktı ve bandı ne kadar geniş — ikisi de tutmuyorsa
   rozet gösterilmez. 32 kategoriden yalnız 8'i bu eşiği geçiyor; kalanında
   "pahalı" demek 5-7 markalık bir örnekleme dayanmak olurdu. */
const OLCUT_EN_AZ_MARKA = 8;
const OLCUT_EN_GENIS_BANT = 0.8;

/* Mekanın kategori fiyatını ölçütle kıyaslar. İl ölçütü varsa o, yoksa ülke.
   Yalnız bandın DIŞINA taşan işaretlenir: bandın içi "normal" değil,
   "bir şey söyleyemiyoruz". */
/* Olcut kullanilabilir mi: yeterli marka, yeterince dar bant. */
function olcutSaglam(o){
  return !!(o && o.alt && o.ust && o.medyan &&
            o.kaynak >= OLCUT_EN_AZ_MARKA &&
            (o.ust - o.alt) / o.medyan <= OLCUT_EN_GENIS_BANT);
}

function olcutKiyas(ilAd, kategori, fiyat){
  if (!olcut) return null;
  const anahtar = Object.keys(olcut.il).find(k => sade(k) === sade(ilAd));
  /* En OZEL olcut kazanir ama yalniz olcu barini gecerse. Onceden il
     kaydi VARSA o kullaniliyordu; 4 markalik bir il olcutu, 16 markalik
     ulke olcutunu bastiriyor ve cevabi susturuyordu. Daha zayif kanit
     daha guclusunu engellememeli. */
  const ilO = anahtar ? olcut.il[anahtar][kategori] : null;
  const o = olcutSaglam(ilO) ? ilO : olcut.turkiye[kategori];
  if (!olcutSaglam(o)) return null;
  if (fiyat < o.alt) return { sinif:"ucuz", ad:"ucuz",   medyan:o.medyan, orta:false };
  if (fiyat > o.ust) return { sinif:"tuz",  ad:"pahalı", medyan:o.medyan, orta:false };
  /* Bandin ICI de bir cevap: "bu kategorideki markalarin ortadaki
     yarisinda". Kategori satirindaki rozet bunu BASMIYOR (orada amac
     goze carpani isaretlemek); mekan bandi basiyor. Karsilastirma tek
     fonksiyonda kaliyor, gosterip gostermemeye cagiran karar veriyor. */
  return { sinif:"orta", ad:"orta", medyan:o.medyan, orta:true };
}

/* ---------- mekanın ucuz / orta / pahalı bandı ----------
   Neye gore? Mekanin ANA URUN turune gore: pizzaci pizzacilarla,
   kebapci kebapcilarla kiyaslanir. Ulke ortalamasina gore soylemek
   anlamsizdi -- 900 TL'lik balikci "pahali", 480 TL'lik pizzaci "ucuz"
   cikardi ve ikisi de yanlis olurdu.

   Olcut TEK BIR kategoride guvenilir degilse band hic gosterilmiyor.
   Ornegin bugun Pizza olcutu 5 markadan cikiyor; 5 markaya dayanip
   "bu pizzaci pahali" demek, uydurma seviyeden farksiz olurdu.
   Bkz. OLCUT_EN_AZ_MARKA ve OLCUT_EN_GENIS_BANT.

   Cok ana urunlu mekanda (balikci + kahvaltici) hepsinin ayni yonu
   gostermesi araniyor: biri ucuz digeri pahali diyorsa cevap yok. */
/* Kategori satirinda hangi kiyas rozet olur. "orta" olmaz: 30 satirin
   25'ine basilir ve hicbirini ayirt ettirmez. Mekan bandi ayni kiyasi
   kullaniyor ama "orta"yi gosteriyor -- orada tek bir cevap var ve
   sessiz kalmak "bilinmiyor" demekti. Karar burada, kiyasin kendisinde
   degil: karsilastirma tek yerde kalsin. */
function kategoriRozeti(kiyas){
  return kiyas && !kiyas.orta ? kiyas : null;
}

function mekanBandi(m, ilAd, bugun){
  const fiyat = yemekFiyati(m, bugun);
  if (fiyat == null) return null;
  const ana = anaKategoriler(m);
  if (!ana || !ana.length) return null;
  let ortak = null;
  for (const k of ana){
    const kiyas = olcutKiyas(ilAd, k, fiyat);
    if (!kiyas) return null;                    /* olcut yetersiz: sus */
    if (ortak && ortak.sinif !== kiyas.sinif) return null;   /* celiski */
    ortak = kiyas;
  }
  return ortak && { sinif: ortak.sinif, ad: ortak.ad,
                    tur: ana.join(", ").toLocaleLowerCase("tr"),
                    medyan: ortak.medyan };
}

/* Cikti sekli ORTAK.JS ile ayni: {fis, medyan}. Onceden `adet` deniyordu
   ve bu ekran esikten habersiz oldugu icin sorun cikmiyordu -- esik
   uygulanir uygulanmaz iki sekil arasinda cevirmek gerekti. `kisi`
   (tekil katkici) BURADA YOK ve uydurulmuyor: `kullanici` sutunu
   tarayiciya kapali (sema.sql), yani bu ekran ayni kisinin iki fisini
   ayirt edemez. fisOzeti() kisi yoksa o kismi hic yazmiyor. */
function paylasimOzet(mekanId){
  const l = paylasimHaritasi.get(mekanId);
  if (!l || !l.length) return null;
  const kisiBasi = l.map(p => Number(p.tutar) / Math.max(1, p.kisi)).sort((a,b) => a - b);
  const orta = Math.floor(kisiBasi.length / 2);
  const medyan = kisiBasi.length % 2 ? kisiBasi[orta] : (kisiBasi[orta-1] + kisiBasi[orta]) / 2;
  return { fis: l.length, medyan: Math.round(medyan), sonTarih: l[0].tarih };
}

/* ?test=1 ile medyan hesabini dogrula: tek asiri kayit ortalamayi kaydirir,
   medyan kaydirmamali. */
/* ?test=1 ile ölçüt kıyasını doğrula: Türkçe il adı eşleşmesi ve
   "az markadan rozet basma" eşiği. İkisi de sessizce bozulabilecek türden. */
function olcutKontrol(){
  if (!new URLSearchParams(location.search).has("test")) return [];
  const yedek = olcut;
  olcut = {
    turkiye: { Kebap: { kaynak:16, medyan:748, alt:474, ust:900 },
               // Sarap: ilde zayif, ulkede saglam -> ulkeye dusmeli
               Sarap: { kaynak:12, medyan:550, alt:400, ust:700 } },
    il: { Istanbul: {
      Kebap: { kaynak:11, medyan:755, alt:470, ust:900 },
      Cay:   { kaynak:3,  medyan:45,  alt:35,  ust:250 },   // marka az VE bant geniş
      // Dar bant ama marka az: YALNIZ marka esigi reddedebilir.
      Kofte: { kaynak:3,  medyan:400, alt:350, ust:450 },
      // Kebap'ta "ucuz" olan 300, burada "pahalı" -> celiski yolu.
      Salata:{ kaynak:12, medyan:150, alt:100, ust:200 },
      Sarap: { kaynak:2,  medyan:550, alt:400, ust:700 },   // marka az, ulkede var
      Pizza: { kaynak:18, medyan:480, alt:19,  ust:547 }    // bant çok geniş
    } }
  };
  const T = [
    ["il olcutu ascii/turkce eslesmeli",
     olcutKiyas("İstanbul", "Kebap", 1250) && olcutKiyas("İstanbul","Kebap",1250).sinif, "tuz"],
    ["band altinda ucuz", olcutKiyas("İstanbul", "Kebap", 300).sinif, "ucuz"],
    ["band icinde orta doner", olcutKiyas("İstanbul", "Kebap", 600).sinif, "orta"],
    ["band icinde kategori rozeti basilmaz",
     olcutKiyas("İstanbul", "Kebap", 600).orta,                       true],
    ["az markali olcut rozet basmaz", olcutKiyas("İstanbul", "Cay", 9999), null],
    /* Dar bantli ama az markali olcut: reddi YALNIZ marka esigi verebilir.
       Cay hem az markali hem genis bantli oldugu icin marka esigi bozulsa
       bile testi gecirriyordu -- kontrol yanlis sebepten yesildi. */
    ["dar bantli ama az markali olcut da rozet basmaz",
     olcutKiyas("İstanbul", "Kofte", 9999),                           null],
    ["kategori rozeti ortayi basmaz",
     kategoriRozeti(olcutKiyas("İstanbul", "Kebap", 600)),             null],
    ["kategori rozeti pahaliyi basar",
     (kategoriRozeti(olcutKiyas("İstanbul", "Kebap", 1250)) || {}).sinif, "tuz"],
    ["genis bantli olcut rozet basmaz", olcutKiyas("İstanbul", "Pizza", 9999), null],
    ["il yoksa ulke olcutune duser", olcutKiyas("Bilinmeyen", "Kebap", 1250).sinif, "tuz"],
    /* Zayif il olcutu, guclu ulke olcutunu bastirmamali. Stub'da Istanbul
       Cay'i 3 markadan (zayif); ulke Cay olcutu 12 markadan ve dar. */
    ["zayif il olcutu ulke olcutunu susturmaz",
     olcutKiyas("İstanbul", "Sarap", 900).sinif,                      "tuz"],
    ["il olcutu saglamsa o kullanilir",
     olcutKiyas("İstanbul", "Kebap", 465).sinif,                      "ucuz"],
    ["bilinmeyen kategori", olcutKiyas("İstanbul", "Yok", 100), null],

    /* --- arama sadelestirmesi ---
       Kullanicilarin cogu Turkce harfsiz yaziyor. Olculdu: "kofte" 574
       mekanin 33'unu buluyordu, %94'u gorunmuyordu. */
    ["sade turkce harfi indirir",     sade("Köfte"),        "kofte"],
    ["sade buyuk I ile i ayni",       sade("IŞIK"),         sade("ışık")],
    /* "İ".toLowerCase() birlesen ust nokta birakiyor; once degistirip
       sonra kucultmek sart. */
    ["sade birlesen nokta birakmaz",  sade("İSKENDER"),     "iskender"],
    ["sade sapkali harf",             sade("Hakkâri"),      "hakkari"],
    ["sade bos girdi",                sade(null),           ""],
    ["sade ascii bozulmaz",           sade("Domino's 2"),   "domino's 2"],

    /* --- mekan bandi --- */
    ["mekan bandi ana urune gore ucuz",
     (mekanBandi({kat:{"Kebap":{n:4,med:300,top:1200}}}, "İstanbul") || {}).sinif,
                                                                      "ucuz"],
    ["mekan bandi ana urune gore pahali",
     (mekanBandi({kat:{"Kebap":{n:4,med:1200,top:4800}}}, "İstanbul") || {}).sinif,
                                                                      "tuz"],
    ["mekan bandi ana urune gore orta",
     (mekanBandi({kat:{"Kebap":{n:4,med:600,top:2400}}}, "İstanbul") || {}).sinif,
                                                                      "orta"],
    /* Icecek ana urun degil: kebapcinin bandi kebaptan cikmali, caydan
       degil -- Cay olcutu zaten guvenilmez ve bandi susturmamali. */
    ["mekan bandi icecege bakmaz",
     (mekanBandi({kat:{"Kebap":{n:4,med:300,top:1200},
                       "Çay":{n:9,med:45,top:405}}}, "İstanbul") || {}).sinif,
                                                                      "ucuz"],
    ["mekan bandi hangi turden hesaplandigini soyler",
     (mekanBandi({kat:{"Kebap":{n:4,med:300,top:1200}}}, "İstanbul") || {}).tur,
                                                                      "kebap"],
    /* Olcut zayifsa SUS: 5 markaya dayanip "pahali" demek uydurma seviye. */
    ["olcutu zayif ana urunde band yok",
     mekanBandi({kat:{"Pizza":{n:4,med:900,top:3600}}}, "İstanbul"),   null],
    /* Ana urunlerden BIRI olculemiyorsa mekan da olculemez: kalanlardan
       cevap uretmek, mekanin yarisina bakip hukum vermek olurdu. Tek
       kategorili fixture bu farki gostermiyordu -- zayif olcutu atlamak
       da, reddetmek de null uretiyordu. */
    ["ana urunlerden biri olculemiyorsa band yok",
     mekanBandi({kat:{"Kebap":{n:4,med:1250,top:5000},
                      "Pizza":{n:4,med:1250,top:5000}}}, "İstanbul"),  null],
    ["fiyati olmayan mekanda band yok",
     mekanBandi({min:25, max:290}, "İstanbul"),                        null],
    ["tek kalemli mekanda band yok",
     mekanBandi({kat:{"Kebap":{n:1,med:300,top:300}}}, "İstanbul"),    null],
    /* Iki ana urun ters yone isaret ediyorsa cevap yok. */
    /* Kebap olcutunde 300 "ucuz", Salata olcutunde ayni 300 "pahalı".
       Iki ana urun ters yone isaret ediyorsa cevap yok. */
    ["celiskili ana urunlerde band yok",
     mekanBandi({kat:{"Kebap":{n:4,med:300,top:1200},
                      "Salata":{n:4,med:300,top:1200}}}, "İstanbul"),  null],
    ["uyumlu ana urunlerde band var",
     (mekanBandi({kat:{"Kebap":{n:4,med:1250,top:5000},
                       "Salata":{n:4,med:1250,top:5000}}}, "İstanbul") || {}).sinif,
                                                                       "tuz"],
    /* Bir yildan eski fiyat sayi olarak gosterilmiyor; band da gosterilmez. */
    ["eskimis fiyatta band yok",
     mekanBandi({tarih:"2025-08", kat:{"Kebap":{n:4,med:300,top:1200}}},
                "İstanbul", new Date(2026, 7, 15)),                    null]
  ];
  olcut = yedek;
  return T.filter(t => JSON.stringify(t[1]) !== JSON.stringify(t[2]));
}

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
    ["fis sayimi",     kur([{tutar:100,kisi:1,tarih:"1"},{tutar:200,kisi:1,tarih:"1"}]).fis, 2],
    ["kayit yok",      (paylasimHaritasi = new Map(), paylasimOzet("yok")), null],
    /* Esik BU EKRANDA da gecerli. Ayri satir olarak duruyor cunku
       eksikligi tam olarak burada aylarca gorunmedi. */
    ["iki fis rozet basmaz",
      fisGoster(kur([{tutar:100,kisi:1,tarih:"1"},{tutar:200,kisi:1,tarih:"1"}])), false],
    ["uc fis rozet basar",
      fisGoster(kur([{tutar:100,kisi:1,tarih:"1"},{tutar:200,kisi:1,tarih:"1"},
                     {tutar:300,kisi:1,tarih:"1"}])), true]
  ];
  paylasimHaritasi = yedek;
  const hata = T.filter(t => JSON.stringify(t[1]) !== JSON.stringify(t[2]))
    .concat(olcutKontrol());
  const gecen = T.length + 7;
  document.body.insertAdjacentHTML("afterbegin",
    '<pre style="margin:0;padding:10px 16px;font:13px ui-monospace,monospace;color:#fff;' +
    'background:' + (hata.length ? "#5b1a1a" : "#1d3a17") + '">' +
    (hata.length ? "KONTROL BASARISIZ: " + JSON.stringify(hata)
                 : gecen + " kontrol gecti (medyan + olcut kiyasi)") + "</pre>");
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

/* ---------- detay ----------
   ANDROID GERI TUSU. Olculdu: panel acikken geri basinca panel
   kapanmiyordu, KESFET EKRANINDAN TAMAMEN CIKILIYORDU (adres index.html
   oluyordu). Tarayicida bu can sikici, uygulamada daha kotu: TWA'da
   baslangic adresindeyken geri basmak uygulamadan CIKMAK demek, yani
   kullanici bir mekana bakip geri basinca uygulama kapaniyordu.

   Cozum, panel acilirken gecmise bir kayit koymak ve geri basisini o
   kayitta yakalamak. Suzgecler bilerek replaceState kullaniyor (40
   filtreyi tek tek geri almak istemiyoruz); burasi ayri ve pushState
   dogru, cunku panel kullanicinin zihninde AYRI BIR EKRAN. */
let panelGecmiste = false;

function panelAc(){
  const d = el("#detay");
  if (!d) return;
  if (!d.open && !panelGecmiste){
    /* Adres DEGISMIYOR: aynı URL ile yalniz bir gecmis kaydi ekleniyor.
       Adresi degistirmek, paylasilan baglantilari bozardi. */
    history.pushState({ panel: 1 }, "", location.href);
    panelGecmiste = true;
  }
  /* Panel HANGI GORUNUMUN uzerinde aciliyor: haritada perde hafif,
     listede koyu. Bilgi dialog'un KENDI ustunde duruyor cunku modal
     bir dialog'un ::backdrop'u ust katmanda; ata elemanin durumundan
     secilemiyor. */
  const gv = el("#govde");
  d.dataset.uzerinde = (gv && gv.dataset.gorunum) || "liste";
  d.showModal();
}


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
  /* Panelde rozet TAM halde: karar burada veriliyor ve yer var. */
  el("#d-meta").innerHTML =
    guvenRozeti(fiyatGuveni(m, zincir, paylasimOzet(m.id))) +
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
    m.mutfak ? satir(IK.mutfak, kacir(mutfakYaz(m.mutfak))) : "",
    m.saat   ? satir(IK.saat,   kacir(m.saat)) : "",
    m.tel    ? satir(IK.tel, '<a href="tel:' + kacir(m.tel.replace(/\s/g,"")) + '">' +
                             kacir(m.tel) + "</a>") : "",
    m.web    ? satir(IK.web, webBagi(m.web)) : "",
    /* Sosyal medya. Instagram, sitesi olmayan 192 mekanin TEK baglantisi;
       diger platformlar da ayni yoldan geciyor. Adres kurma kurali
       ortak.js'te (sosyalBag) -- isletme sayfasi da ayni listeyi
       kuruyor, iki yerde iki turlu olmasin. */
    ...sosyalListe(m).map(x =>
        satir(IK.web, x.bag + ' <small style="color:var(--metin-3)">' +
                      kacir(x.ad) + "</small>"))
  ].filter(Boolean).join("");

  let govde = bilgi ? '<div class="d-bilgi">' + bilgi + "</div>" : "";

  /* Kullanici paylasimi menuden AYRI gosteriliyor: biri isletmenin ilan
     ettigi liste fiyati, digeri insanlarin fiilen odedigi tutar. */
  /* ESIK BURADA DA UYGULANIYOR. Onceden tek fisten "Gercekten odenen
     240 TL" kutusu ciziliyordu ve altina "1 kisinin paylasimindan" diye
     de YAZIYORDU -- yani bir kisinin o gunku hesabi mekanin fiyati diye
     yayimlaniyordu. Esigin altinda tutar yerine KAC FIS KALDIGI
     yaziliyor; cumle ortak.js'te, isletme sayfasiyla ayni. */
  const o = paylasimOzet(m.id);
  if (fisGoster(o)){
    govde +=
      '<div class="odenen">' +
      '<div class="odenen-bas"><span>Gerçekten ödenen</span>' +
      '<b>' + tl(o.medyan) + "</b></div>" +
      '<p>Kişi başı medyan tutar. ' + sayi(o.fis) +
      " paylaşımdan hesaplandı; son bilgi " +
      new Date(o.sonTarih).toLocaleDateString("tr-TR",
        { day:"numeric", month:"long", year:"numeric" }) + ".</p></div>";
  } else if (o){
    govde += '<div class="odenen az"><p>' + kacir(fisOzeti(o)) + "</p></div>";
  }

  /* Ürün kırılımı: 40 kalemlik listeyi taramak yerine "çay kaç, kebap kaç"
     tek bakışta görünsün. Fiyatlar mekanın kendi menüsünden, alt medyan. */
  if (m.kat){
    const ilAd = ilAdi();
    const sirali = Object.entries(m.kat).sort((a,b) => a[1].med - b[1].med);
    govde +=
      '<div class="d-menu-bas"><h3>Ne kaça</h3><span>' +
      sayi(sirali.length) + " kategori</span></div><div class=\"kat-liste\">" +
      sirali.map(([ad, o]) => {
        const k = kategoriRozeti(olcutKiyas(ilAd, ad, o.med));
        return '<div class="kat">' +
          "<span>" + kacir(ad) +
          (o.n > 1 ? ' <i>' + sayi(o.n) + " kalem</i>" : "") + "</span>" +
          (k ? '<em class="rozet ' + k.sinif + '">' + k.ad + "</em>" : "") +
          "<b>" + tl(o.med) + "</b></div>";
      }).join("") + "</div>";
  }

  if (m.menu){
    /* Menü ucuzdan pahalıya: bütçesi olan kullanıcı önce ne alabileceğini
       görsün, listenin dibine inmek zorunda kalmasın. */
    const sirali = m.menu.slice().sort((x,y) => x.f - y.f);
    /* Liste kirpilmis olabilir: veride en ucuz 40 kalem duruyor, kategori
       medyanlari ise tam listeden geliyor. Basligi "40 kalem · 35-165 TL"
       diye yazmak, ustteki "yemek ~480 TL" ile celisiyordu. Aralgin neyin
       araligi oldugu artik yaziyor; sayi uydurmuyoruz, kirpildigini
       soyluyoruz. */
    const kirpik = m.kalem_n && m.kalem_n > m.menu.length;
    const ort = yemekFiyati(m);
    /* Basligi ORTALAMA aciyor, en ucuz kalem degil. "35 TL'den baslar"
       demek teknik olarak dogru ama sorunun cevabi degil: kullanici
       burada kaca oturacagini soruyor. Aralik ikinci sirada ve kirpilmissa
       neyin araligi oldugunu soyluyor. */
    const aralik = (kirpik ? "en ucuz " : "") + sayi(m.menu.length) + " kalem · " +
                   tl(m.min) + " – " + tl(m.max) +
                   (kirpik ? " <i>(toplam " + sayi(m.kalem_n) + ")</i>" : "");
    /* Ortalamanin NEYIN ortalamasi oldugu yaziyor: "ortalama 480 TL (pizza)".
       Rakami aciklamayan sayi, kullanicinin dogrulayamadigi bir iddiadir --
       tur yazilinca menuye bakip kendisi kontrol edebiliyor. Uc ve ustu
       turde liste uzuyor, orada yalniz rakam kaliyor. */
    const anaTur = ort != null ? (anaKategoriler(m) || []) : [];
    const turAd = anaTur.length && anaTur.length <= 2
      ? " <i>(" + kacir(anaTur.join(", ").toLocaleLowerCase("tr")) + ")</i>" : "";
    /* Rakamin yaninda ne anlama geldigi: "ortalama 300 TL (kebap) · ucuz".
       Sayi tek basina kiyaslanamaz -- kullanici Turkiye'deki kebap
       fiyatlarini ezbere bilmiyor. */
    const mb = mekanBandi(m, ilAdi());
    /* Neye gore ucuz? Rakam title'da: "ucuz" tek basina kimin olcusune
       gore oldugunu soylemiyor, kullanici dogrulayamiyor. */
    const bandAd = mb
      ? ' <span class="bant ' + mb.sinif + '" title="' +
        kacir(mb.tur + " medyanı " + tl(mb.medyan) + " (Türkiye ölçütü)") +
        '">' + mb.ad + "</span>" : "";
    const baslik = ort != null
      ? "ortalama <b>" + tl(ort) + "</b>" + turAd + bandAd + " · " + aralik
      : aralik;
    /* Fiyatin YASI rakamin yaninda duruyor. Enflasyonda tarihsiz fiyat
       kullanicinin dogrulayamadigi bir iddia: kac aylik bir sayiya baktigini
       bilmeden "pahali" da diyemez "ucuz" da. Bir yildan eskiyse rakam zaten
       yemekFiyati() icinde dusuyor, burada yalnizca kalan menu listesinin
       tarihi yaziliyor. */
    const yas = fiyatYasEtiketi(m);
    const tarihSatiri = yas
      ? '<p class="uyari' + (yas.eski ? " eski" : "") + '">' +
        (yas.eski ? "⚠ " : "") + kacir(yas.ad) + " tarihinde derlendi" +
        (yas.eski ? " — güncelliğini yitirmiş olabilir." : ".") + "</p>"
      : "";
    /* FIYAT KAC OLCUMDEN GELIYOR. Kartta yalnizca "zincir" isareti var;
       panele acan kullanici karari burada veriyor, o yuzden tam cumle
       burada. Olculdu: 163 fiyatli mekan 53 farkli isletme, 94'u tek bir
       zincirin subesi ve subeler arasi fiyat farki YOK -- tek kazima 56
       olcum gibi duruyordu. Cumle ortak.js'te (dayanakCumlesi). */
    const dy = fiyatDayanagi(m, zincir);
    const dayanakSatiri = dy && dy.sinif === "zincir"
      ? '<p class="uyari zincir">' + kacir(dayanakCumlesi(dy)) + "</p>" : "";
    /* CEBIMDE KOMBINI: "bu butceyle burada ne yenir". Ortalama fiyat
       "kaca oturulur" diyor; kombin menude YAZAN iki kalemi gosteriyor.
       Menunun USTUNDE cunku kullanicinin sordugu somut soru bu; menu
       listesi onun dayanagi. Kurulamiyorsa satir hic cikmiyor --
       uydurma bir sepet, sepet olmamasindan kotu. */
    const kmb = kombinKur(m, butce);
    const kombinSatiri = kmb
      ? '<p class="kombin"><b>' + kacir(butce ? tl(butce) + " ile" : "En ucuz öğün") +
        ":</b> " + kombinCumlesi(kmb, butce) + "</p>"
      : "";
    govde +=
      '<div class="d-menu-bas"><h3>Menü</h3><span>' + baslik + "</span></div>" +
      kombinSatiri +
      sirali.map(k =>
        '<div class="kalem' + (butce && k.f > butce ? " disi" : "") + '">' +
        "<span>" + kacir(k.a) + "</span><b>" + tl(k.f) + "</b></div>").join("") +
      tarihSatiri + dayanakSatiri +
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
  /* BUTCE DE GIDIYOR. Mekan sayfasi butceyi ?butce= ile okuyor; buradan
     gecirilmezse kullanicinin ana ekranda yazdigi rakam ucuncu ekranda
     kayboluyordu -- kombin "En ucuz ogun" diyordu, menu listesi kac
     kalemin butceye girdigini hic yazmiyordu. */
  el("#d-sayfa").href = "isletme.html?il=" + encodeURIComponent(el("#il").value) +
                        "&id=" + encodeURIComponent(m.id) +
                        (butce > 0 ? "&butce=" + butce : "");
  favoriDugmesiniTazele(m);
  panelAc();

  const i = isaretler.get(id);
  /* Harita mekana gidiyor ama BALON ACILMIYOR: panel modal ve balonu
     bulanik perdenin arkasinda birakiyordu. Ikisi de ayni uc bilgiyi
     (ad, tur, butce durumu) yaziyor; ikinci kopya gorunmeyen bir
     kopyaydi. Balon isaretcide duruyor -- panel kapaninca haritada
     tiklayan kullanici onu goruyor. */
  if (i && haritaVar()) harita.setView([m.lat, m.lon], Math.max(harita.getZoom(), 15));
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
  }).then(ham => {
    /* ilCoz: dosya sikistirilmis bicimde (veri_bicim.py). Cozucu tek
       yerde -- ucuncu tuketici de ayni fonksiyonu cagiriyor. */
    const v = ilCoz(ham);
    mekanlar = v.mekanlar;
    /* Zincir haritasi IL BASINA bir kez. Kart basina hesaplansa 2.300
       kartlik listede 2.300 kez butun ili tarardi. Il degisince
       yenilenmesi sart: Ankara listesiyle Istanbul haritasi, "56 subede
       ayni menu" gibi yanlis bir sayi yazdirirdi. */
    zincir = zincirHaritasi(mekanlar);
    olcutYukle();
    /* Fisler ile akran satiri AYNI ile ait: il degisince ikisi birden
       yenilenmezse ekranda Ankara listesi + Izmir akrani kalirdi. */
    paylasimlariYukle(kod).then(() => { ciz(false); akranYaz(); });
    limit = SAYFA;
    secili = null;
    ciz(true);
    /* Anasayfadan "yakınımdakiler" ile gelindiyse konumu kendiliğinden iste.
       Liste önce çizilir; konum gelince yeniden sıralanır, böylece izin
       penceresi açıkken ekran boş durmaz. */
    if (sirala === "yakin" && !konum) konumIste(() => ciz(true));
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
  try { kayitli = localStorage.getItem("cebimde.il"); } catch (e) {}

  fetch("veri/index.json").then(r => r.json()).then(d => {
    secim.innerHTML = d.iller.map(i =>
      '<option value="' + i.kod + '">' + kacir(i.ad) + "</option>").join("");
    const istenen = P.get("il");
    secim.value = d.iller.some(i => i.kod === istenen) ? istenen
                : d.iller.some(i => i.kod === kayitli) ? kayitli
                : d.varsayilan;
    ilYukle(secim.value, true);
    secim.addEventListener("change", () => {
      try { localStorage.setItem("cebimde.il", secim.value); } catch (e) {}
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
    const v = sade(e.target.value);
    zaman = setTimeout(() => { arama = v; limit = SAYFA; ciz(false); }, 180);
  });

  el("#sirala").addEventListener("change", e => {
    sirala = e.target.value; limit = SAYFA;
    if (sirala === "yakin") konumIste(() => ciz(false)); else ciz(false);
  });

  el("#butce").addEventListener("input", e => { butce = +e.target.value; butceYaz(); });
  el("#butce").addEventListener("change", () => { limit = SAYFA; ciz(false); akranYaz(); });

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
    akranYaz();
    ciz(true);
  });

  /* Acik konum dugmesi. Basari durumunu yaziyla bildiriyor: sessizce hicbir
     sey olmamasi, kullanicinin "calismiyor" diye birakmasinin sebebi. */
  const konumDug = el("#konum-al");
  if (konumDug) konumDug.addEventListener("click", () => {
    if (!navigator.geolocation){ konumDug.textContent = "konum desteklenmiyor"; return; }
    konumDug.disabled = true;
    konumDug.textContent = "konum alınıyor…";
    const bitir = () => {
      konumDug.disabled = false;
      konumDug.textContent = konum ? "konumun kullanılıyor" : "konum alınamadı";
      ciz(false);
    };
    konumIste(bitir);
  });

  /* mobil sekme */
  document.querySelectorAll(".sekme button").forEach(b =>
    b.addEventListener("click", () => {
      document.querySelectorAll(".sekme button").forEach(x =>
        x.setAttribute("aria-selected", String(x === b)));
      el("#govde").dataset.gorunum = b.dataset.gorunum;
      /* Leaflet gizliyken boyut alamıyor; görünür olunca yeniden ölçtür. */
      if (b.dataset.gorunum === "harita" && harita)
        if (haritaVar()) setTimeout(() => harita.invalidateSize(), 60);
    }));

  document.querySelectorAll("[data-kapat]").forEach(b =>
    b.addEventListener("click", () => el("#detay").close()));

  /* Panel kapaninca (dugme, Esc ya da disari tiklama) BIZIM koydugumuz
     gecmis kaydi da geri alinmali; yoksa kayit orada kalir ve bir
     sonraki geri basisi "hicbir sey olmuyor" gibi gorunur. */
  el("#detay").addEventListener("close", () => {
    if (panelGecmiste){ panelGecmiste = false; history.back(); }
  });

  addEventListener("popstate", () => {
    /* Geri tusu: panel acikken ONCE paneli kapat. Bayrak burada
       dusuruluyor, yoksa close olayi bir kez daha history.back()
       cagirir ve kullanici sayfadan disari duser. */
    if (panelGecmiste){
      panelGecmiste = false;
      const d = el("#detay");
      if (d && d.open) d.close();
    }
  });

  const favDugme = el("#d-favori");
  if (favDugme) favDugme.addEventListener("click", favoriDegistir);
  favorileriYukle();
  paylasimKontrol();
});
})();
