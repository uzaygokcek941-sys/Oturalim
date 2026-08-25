/* ============================================================
   Cebimde — service worker

   BU DOSYA ELLE SURUMLENMIYOR. Asagidaki SURUM satirini `sw_uret.py`
   yaziyor ve degeri kabuk dosyalarinin ICERIGINDEN turetiliyor. Gerekce,
   bu depoda CSP karmalarindakiyle ayni: elle tutulan bir surum numarasi
   ilk duzenlemede eskir ve eskimesi SESSIZDIR -- kullanicilar aylarca
   eski bir surumu kullanmaya devam eder ve kimse fark etmez. En kotu
   yazilim hatasi turu: hicbir yerde patlamayan.

   NEDEN VAR
   =========
   1) Google Play. Uygulama TWA olarak paketleniyor (bkz. PLAY.md).
      Cevrimdisiyken tarayicinin kendi hata ekranini gostermek Play'in
      "bozuk islevsellik" kurallarina takiliyor. Burasi onun yerine
      cevrimdisi.html'i veriyor.
   2) Telefonda ikinci acilis. Il dosyalari 60-1325 KB; onbellekten
      gelince ekran aninda doluyor.

   TASARIM KARARLARI VE SEBEPLERI
   ==============================
   GEZINME ISTEGI: once ag, sonra onbellek. Tersi (once onbellek) daha
   hizli acilirdi ama bu uygulama FIYAT gosteriyor -- eski bir sayfayi
   sessizce vermek, bu depodaki "bayat fiyat" kuralinin cignenmesi olurdu.

   IL VERISI (veri/*.json): once ag, sonra onbellek. Ayni gerekce, arti
   kullanici cevrimdisiyken bos ekran yerine dun geceki listeyi goruyor.

   VARLIKLAR (css/js/ikon/font): surumlu onbellekten. Surum kabuk
   dosyalarinin karmasindan geliyor, yani dosya degisince onbellek adi
   degisiyor ve eskisi silinip yenisi kuruluyor. "Ayni ad, yeni icerik"
   hali hic olusmuyor.

   SUPABASE VE HARITA DOSEMESI ONBELLEGE ALINMIYOR. Ilki oturuma bagli ve
   kisisel; onbellege dusmesi baska birinin cihazinda kalmasi riskini
   tasir. Ikincisi cok sayida kucuk resim, onbellegi sisirir.

   GET DISINDA HICBIR SEY. POST/PATCH gecici olarak bile saklanmiyor.

   ARIZA HALINDE ACIK DUSUYOR: fetch isleyicisi icindeki her hata
   yakalanip istek AGA birakiliyor. Bozuk bir service worker'in siteyi
   kalici olarak kirmasi, service worker'in olmamasindan cok daha kotu.
   ============================================================ */

const SURUM = "vb9de0045ea8f";      /* sw_uret.py YAZIYOR — elle degistirme */

const KABUK = SURUM + "-kabuk";
const VERI  = SURUM + "-veri";

/* Kurulumda alinanlar. Cevrimdisi sayfasi ve stil BURADA olmak zorunda:
   ikisi de "her sey basarisiz olursa" halinde kullaniliyor. */
const ON_YUKLE = [
  /* index.html BURADA olmali: manifest'in start_url'i bu ve TWA her
     acilista onu istiyor. Ilk kurulumda service worker HENUZ etkin
     olmadigi icin o ilk gezinme yakalanmiyor -- yani onbellege
     KOYMASAYDIK, uygulamayi kurup ucak moduna alan biri ilk acilista
     "baglanti yok" gorurdu. Play'in bakabilecegi tam hal budur.
     Gezinme yine ONCE AGA gidiyor; bu kopya sadece yedek. */
  "./index.html",
  "./cevrimdisi.html",
  "./stil.css",
  "./ikon/ikon-192.png",
  "./manifest.webmanifest"
];

self.addEventListener("install", olay => {
  olay.waitUntil((async () => {
    const kova = await caches.open(KABUK);
    /* addAll TEK BIR dosya bile gelmezse hepsini birden atiyor; tek tek
       ekleniyor ki bir ikon eksikse cevrimdisi sayfasi yine de kurulsun. */
    await Promise.all(ON_YUKLE.map(y =>
      kova.add(new Request(y, { cache: "reload" })).catch(() => {})));
  })());
  /* skipWaiting CAGRILMIYOR. Cagrilsaydi yeni surum, ESKI surumun
     calistigi bir sayfanin altindan varliklari degistirebilirdi: acik
     duran kesfet ekrani yeni bir ortak.js ile eski bir kesfet.js'i
     karistirabilirdi. Yeni surum bir sonraki tam gezinmede devraliyor. */
});

self.addEventListener("activate", olay => {
  olay.waitUntil((async () => {
    const adlar = await caches.keys();
    await Promise.all(adlar
      .filter(a => a !== KABUK && a !== VERI)
      .map(a => caches.delete(a)));
    /* Gezinme on yukleme: ag isteği, service worker uyanirken baslasin. */
    if (self.registration.navigationPreload)
      await self.registration.navigationPreload.enable();
    await self.clients.claim();
  })());
});

/* Kendi kaynagimiz mi. Supabase, harita dosemesi, yazi tipi ve CDN
   buranin disinda kaliyor. */
function bizim(u){
  return u.origin === self.location.origin;
}

async function agOnce(istek, kovaAdi, yedek){
  try {
    const yanit = await fetch(istek);
    /* Yalniz TAM ve BASARILI yanit saklaniyor. 206 (kismi) ve opak
       yanitlari saklamak, onbellekte yarim dosya birakirdi. */
    if (yanit && yanit.ok && yanit.type === "basic"){
      const kova = await caches.open(kovaAdi);
      kova.put(istek, yanit.clone());
    }
    return yanit;
  } catch (e) {
    const saklanan = await caches.match(istek);
    if (saklanan) return saklanan;
    if (yedek) {
      const y = await caches.match(yedek);
      if (y) return y;
    }
    throw e;
  }
}

self.addEventListener("fetch", olay => {
  const istek = olay.request;
  if (istek.method !== "GET") return;

  let u;
  try { u = new URL(istek.url); } catch (e) { return; }
  if (!bizim(u)) return;                  /* Supabase, doseme, font: dokunma */

  /* Gezinme: once ag, olmazsa onbellek, o da yoksa cevrimdisi sayfasi. */
  if (istek.mode === "navigate"){
    olay.respondWith((async () => {
      try {
        /* On yukleme yaniti da SAKLANMALI. Ilk yazimda dogrudan
           donduruluyordu ve sonucu su oldu: gezinme yanitlari HIC
           onbellege girmiyordu -- kullanici bir sayfayi acip sonra
           cevrimdisi kalinca, ZATEN ACMIS OLDUGU sayfa bile "baglanti
           yok" ekranina dusuyordu. Olculdu ve duzeltildi. */
        const on = await olay.preloadResponse;
        if (on){
          if (on.ok && on.type === "basic"){
            const kova = await caches.open(KABUK);
            kova.put(istek, on.clone());
          }
          return on;
        }
        return await agOnce(istek, KABUK, "./cevrimdisi.html");
      } catch (e) {
        const saklanan = await caches.match(istek);
        if (saklanan) return saklanan;
        const cevrimdisi = await caches.match("./cevrimdisi.html");
        /* Onbellekte o da yoksa (ilk acilis + hemen cevrimdisi) hata
           firlatmak yerine kisa bir yanit veriliyor: tarayicinin kendi
           hata ekrani Play'de sorun. */
        return cevrimdisi || new Response(
          "<!doctype html><meta charset=utf-8><title>Bağlantı yok</title>" +
          "<p style=\"font:16px system-ui;padding:2rem\">Bağlantı yok. " +
          "İnternete bağlanınca tekrar dene.</p>",
          { headers: { "content-type": "text/html; charset=utf-8" }, status: 503 });
      }
    })());
    return;
  }

  /* Il verisi: once ag (fiyat eskimesin), olmazsa onbellek. */
  if (u.pathname.includes("/veri/") && u.pathname.endsWith(".json")){
    olay.respondWith(agOnce(istek, VERI).catch(() => fetch(istek)));
    return;
  }

  /* Varliklar: surumlu onbellekten, yoksa agdan alip sakla. */
  olay.respondWith((async () => {
    try {
      const saklanan = await caches.match(istek);
      if (saklanan) return saklanan;
      return await agOnce(istek, KABUK);
    } catch (e) {
      return fetch(istek);               /* ariza halinde ACIK dus */
    }
  })());
});

/* Sayfadan gelen "hemen devral" istegi. Kullanici gorunur bir dugmeye
   bastiginda cagriliyor; kendiliginden degil (yukaridaki gerekce). */
self.addEventListener("message", olay => {
  if (olay.data === "devral") self.skipWaiting();
});
