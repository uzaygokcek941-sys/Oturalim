/* ============================================================
   Oturalım — sahne motoru
   Chungking Express'in step-printing tekniği: film 6 kare/sn çekilip
   her kare dörtlenmis. Netice — onde duran net kalir, arka plan
   algilanamaz hizda akar.

   Burada iki mekanizma var:
   1) Isik izi alani (canvas). Hiz yuksekken izin kuyrugu uzun ve sonuk,
      dustukce kisa ve keskin. Yani hiz bulanikligi ureten sey KARE
      TEMIZLEME ORANI -- bu, tekniğin kendi mantigi.
   2) Giris gozlemcisi. Bolumler gorunur olunca kendi giris tipiyle acilir.

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

/* ---------- 2. Isik izi alani ---------- */
function sokagiKur(){
  const tuval = document.querySelector("canvas.sokak");
  if (!tuval) return;
  const ctx = tuval.getContext("2d", { alpha:false });
  if (!ctx) return;

  const sahne = tuval.closest(".sahne");
  const dugme = document.getElementById("yakinimdakiler");
  const renkler = ["255,210,74", "74,217,160", "240,138,60"];  // sari, yesil, turuncu

  let g = 0, y = 0, dpr = 1, izler = [], calisiyor = false, kare = 0;
  let hiz = 1, hedefHiz = 1;          // 1 = akiyor/bulanik, .15 = duruyor/net

  function olcek(){
    dpr = Math.min(devicePixelRatio || 1, 2);   // 3x ekranda bedava maliyet
    g = tuval.clientWidth; y = tuval.clientHeight;
    tuval.width = Math.round(g * dpr);
    tuval.height = Math.round(y * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    kur();
  }

  function kur(){
    // Yogunluk alana gore; telefonda 40, genis ekranda ~110 iz.
    const adet = Math.round(Math.min(110, Math.max(34, (g * y) / 14000)));
    izler = Array.from({ length:adet }, () => yeniIz(true));
  }

  function yeniIz(ilk){
    const derinlik = Math.random();               // 0 uzak, 1 yakin
    return {
      x: ilk ? Math.random() * g : -40,
      o: Math.random() * y,
      // Yakin izler hizli ve kalin; uzaklar yavas ve ince. Derinlik hissi
      // parallax'tan degil, HIZ FARKINDAN geliyor -- filmdeki gibi.
      v: 0.6 + derinlik * 5.4,
      u: 18 + derinlik * 120,                     // kuyruk uzunlugu
      k: 0.6 + derinlik * 2.0,                    // kalinlik
      a: 0.10 + derinlik * 0.42,
      r: renkler[(Math.random() * renkler.length) | 0]
    };
  }

  function ciz(){
    if (!calisiyor) return;
    kare++;

    // Kare temizleme orani hiza bagli. Hizliyken az temizlenir -> onceki
    // kareler ustuste biner -> smear. Yavaslarken cok temizlenir -> netlik.
    // Step-printing'in kendi mantigi budur.
    hiz += (hedefHiz - hiz) * 0.06;
    ctx.fillStyle = "rgba(13,10,8," + (0.10 + (1 - hiz) * 0.55) + ")";
    ctx.fillRect(0, 0, g, y);

    ctx.lineCap = "round";
    for (const iz of izler){
      const v = iz.v * hiz;
      iz.x += v;
      if (iz.x - iz.u > g){ Object.assign(iz, yeniIz(false)); continue; }

      // Kuyruk hizla kisalir: durunca iz bir noktaya doner.
      const u = iz.u * (0.22 + hiz * 0.78);
      const gr = ctx.createLinearGradient(iz.x - u, iz.o, iz.x, iz.o);
      gr.addColorStop(0, "rgba(" + iz.r + ",0)");
      gr.addColorStop(1, "rgba(" + iz.r + "," + iz.a + ")");
      ctx.strokeStyle = gr;
      ctx.lineWidth = iz.k;
      ctx.beginPath();
      ctx.moveTo(iz.x - u, iz.o);
      ctx.lineTo(iz.x, iz.o);
      ctx.stroke();
    }
    requestAnimationFrame(ciz);
  }

  function baslat(){ if (!calisiyor){ calisiyor = true; requestAnimationFrame(ciz); } }
  function durdur(){ calisiyor = false; }

  function tekKare(){
    // Az-hareket modu: akis yok, tek bir durgun kare.
    ctx.fillStyle = "#0d0a08"; ctx.fillRect(0, 0, g, y);
    hiz = 0.14;
    for (const iz of izler){
      ctx.strokeStyle = "rgba(" + iz.r + "," + (iz.a * 0.8) + ")";
      ctx.lineWidth = iz.k;
      ctx.beginPath(); ctx.moveTo(iz.x - 6, iz.o); ctx.lineTo(iz.x, iz.o); ctx.stroke();
    }
  }

  olcek();
  addEventListener("resize", olcek, { passive:true });

  if (azHareket.matches){ tekKare(); return; }

  /* Secmeye yaklastikca dunya duruyor. Sayfanin tek fikri bu. */
  if (dugme){
    const yakinlik = e => {
      const r = dugme.getBoundingClientRect();
      const mx = r.left + r.width / 2, my = r.top + r.height / 2;
      const d = Math.hypot(e.clientX - mx, e.clientY - my);
      const p = Math.min(1, d / 420);            // 0 = uzerinde, 1 = uzak
      hedefHiz = 0.15 + p * 0.85;
      document.documentElement.style.setProperty("--iz-hiz", hedefHiz.toFixed(2));
    };
    sahne.addEventListener("pointermove", yakinlik, { passive:true });
    sahne.addEventListener("pointerleave", () => { hedefHiz = 1; }, { passive:true });
    // Klavye kullanicisi de gormeli: odaklaninca ayni sey olur.
    dugme.addEventListener("focus", () => { hedefHiz = 0.15; });
    dugme.addEventListener("blur",  () => { hedefHiz = 1; });
  }

  /* Gorunmeyen kahraman icin kare uretmek pil yakmaktir. */
  if ("IntersectionObserver" in window){
    new IntersectionObserver(([gi]) => gi.isIntersecting ? baslat() : durdur(),
      { threshold:0 }).observe(sahne);
  } else baslat();

  document.addEventListener("visibilitychange",
    () => document.hidden ? durdur() : baslat());
}

/* ---------- 3. Baslat ---------- */
if (document.readyState === "loading")
  document.addEventListener("DOMContentLoaded", () => { girisleriBagla(); sokagiKur(); });
else { girisleriBagla(); sokagiKur(); }

})();
