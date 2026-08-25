/* ============================================================
   Cebimde — sahne motoru
   Chungking Express'in step-printing tekniği: film 6 kare/sn çekilip
   her kare dörtlenmis. Netice — onde duran net kalir, arka plan
   algilanamaz hizda akar.

   ISIK IZI ALANI (canvas) KALDIRILDI. Kahramandaki koyu "gece sokagi"
   marka maketleriyle celisiyordu -- maketlerin hepsi acik temali, beyaz
   kartli -- ve acik temada buyuk butce rakamini okunmaz yapiyordu.
   Bu baslik onu hala anlatiyordu; anlatan satirlar da onunla gitti.

   Geriye TEK mekanizma kaldi:
   - Giris gozlemcisi. Bolumler gorunur olunca kendi giris tipiyle acilir.
     Surekli donen bir cizim dongusu YOK; test_sayfa.py bunu olcuyor.

   Bagimlilik yok. stil.css + sahne.css ile calisir.
   ============================================================ */
(() => {
"use strict";

const azHareket = matchMedia("(prefers-reduced-motion: reduce)");

/* ---------- 1. Giris gozlemcisi ---------- */
function girisleriBagla(){
  /* sahne.js calisti: satir ici emniyet devreye girmesin. */
  window.__sahneHazir = true;
  const hedefler = document.querySelectorAll("[data-giris]");
  if (!hedefler.length) return;

  // Gozlemci yoksa (cok eski tarayici) her sey acik gelsin -- gizli kalmasin.
  if (!("IntersectionObserver" in window) || azHareket.matches){
    hedefler.forEach(h => h.classList.add("gorunur"));
    return;
  }
  /* Emniyet: gozlemci 1,5 sn icinde tetiklenmezse her seyi ac.
     Arka plan sekmede acilan sayfada IO hic tetiklenmiyor (dogrulandi:
     document.hidden=true iken 500 ms'de 0 kare). Bu olmadan sayfa bos kalir. */
  const emniyet = setTimeout(() => {
    hedefler.forEach(h => h.classList.add("gorunur"));
  }, 1500);

  const g = new IntersectionObserver((girdiler) => {
    for (const gi of girdiler){
      if (!gi.isIntersecting) continue;
      gi.target.classList.add("gorunur");
      g.unobserve(gi.target);          // bir kez oynar, scroll'da tekrarlamaz
    }
    /* Emniyet ancak HEPSI acildiginda iptal ediliyor. Onceden ilk
       goruneni gorur gormez iptal ediliyordu; sonradan gelen ya da o
       an gizli bir kapsayicinin icinde olan bolumler emniyetsiz
       kaliyor ve hic acilmiyordu. */
    if (![...hedefler].some(h => !h.classList.contains("gorunur")))
      clearTimeout(emniyet);
  }, { threshold:.15, rootMargin:"0px 0px -8% 0px" });
  hedefler.forEach(h => g.observe(h));
}

/* ---------- 2. (kaldirildi) Isik izi alani ----------
   Kahramandaki koyu "gece sokagi" canvas'i vardi. Marka maketleri acik
   ve kartli; katman kaldirildi (bkz. sahne.css). Cagrisi da dusuruldu --
   canvas olmayinca fonksiyon sessizce donuyordu ama olu kod, sonradan
   bakan icin "burada bir sey var" demektir. */
/* ---------- 3. Baslat ---------- */
if (document.readyState === "loading")
  document.addEventListener("DOMContentLoaded", () => { girisleriBagla(); });
else { girisleriBagla(); }

})();
