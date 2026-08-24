# -*- coding: utf-8 -*-
"""Sayfalari GERCEK tarayicida acan kontroller.

    python test_sayfa.py            # hepsi
    python test_sayfa.py test       # ayni sey (test.py boyle cagiriyor)

NEDEN AYRI BIR KOSUM TAKIMI: test_tarayici.mjs betikleri bir vm kutusunda
calistiriyor, yani DOM yok, yukleme sirasi yok, CDN yok. Gercek bir hatayi
o yuzden goremedi:

  Leaflet CDN'den gelmediginde ("L is not defined") kesfet ekraninin
  TAMAMI oluyordu -- sifir kart, sayac "…"da donmus, bos sayfa. Oysa
  liste, filtreler ve butce kaydiricisi haritaya hic ihtiyac duymuyor.

DIS BAGLANTILAR BILEREK ENGELLENIYOR. Iki sebep: (1) kontrol ag'a
bagimli olmasin, aksi halde CDN yavaslayinca kirmizi yanar; (2) asil
sinanmak istenen sey ZOR hal -- CDN'siz kullanici. Kurumsal ag, okul agi
ve ulke capinda engel gercek; uygulama o kosulda da calismali.

Tarayici yoksa kontrol ATLANIR, gectigi soylenmez.
"""
import os
import subprocess
import sys
import time

TABAN = "http://localhost:8199"
KOK = os.path.dirname(os.path.abspath(__file__))

# Leaflet taklidi: gercek Leaflet'e ulasamiyoruz ama kodun NORMAL yolu
# izledigini dogrulamamiz gerekiyor -- haritaKur erken donmemeli,
# isaretciler cizilmeli. Taklit yalniz kullanilan arayuzu sunuyor.
LEAFLET_TAKLIT = """
window.__cagri = [];
const kat = { addTo(){ window.__cagri.push("addTo"); return this; },
              clearLayers(){ window.__cagri.push("clearLayers"); },
              removeLayer(){} };
const isaretci = { addTo(){ return this; }, bindPopup(){ return this; },
                   on(){ return this; }, openPopup(){} };
window.L = {
  map(){ window.__cagri.push("map");
    const h = { setView(){ return h; }, removeLayer(){},
                fitBounds(){ window.__cagri.push("fitBounds"); },
                getZoom: () => 12, invalidateSize(){} };
    return h; },
  tileLayer(){ window.__cagri.push("tileLayer"); return kat; },
  layerGroup(){ window.__cagri.push("layerGroup"); return kat; },
  circleMarker(){ window.__cagri.push("circleMarker"); return isaretci; }
};
"""

SAYFALAR = ["/index.html", "/kesfet.html", "/kesfet.html?il=34&tur=Kafe&butce=300",
            "/isletme.html?il=34&id=node/8223784325", "/isletme.html?il=34&id=yok",
            "/paylas.html", "/giris.html", "/hesabim.html", "/yonetim.html",
            "/hakkinda.html", "/gizlilik.html"]


def _tarayici_yolu():
    """Playwright'in indirdigi tarayici ya da ortamda hazir duran."""
    kok = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if kok and os.path.isdir(kok):
        import glob
        for d in sorted(glob.glob(os.path.join(kok, "chromium-*", "chrome-linux", "chrome"))):
            return d
    return None


def kendini_kontrol_et():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ATLANDI: playwright yok")
        return None

    sunucu = subprocess.Popen([sys.executable, os.path.join(KOK, "sunucu.py"), "8199"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                import urllib.request
                urllib.request.urlopen(TABAN + "/index.html", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            print("ATLANDI: yerel sunucu acilmadi")
            return None

        sorunlar = []
        with sync_playwright() as p:
            yol = _tarayici_yolu()
            try:
                t = (p.chromium.launch(executable_path=yol, args=["--no-sandbox"])
                     if yol else p.chromium.launch(args=["--no-sandbox"]))
            except Exception as e:
                print("ATLANDI: tarayici yok (%s)" % str(e).split("\n")[0][:60])
                return None

            def sayfa_ac(yolu, taklit=None):
                sf = t.new_page()
                hata = []
                sf.on("pageerror", lambda e: hata.append(str(e)[:120]))
                if taklit:
                    sf.add_init_script(taklit)
                # Dis baglantilarin hepsi kapali: kontrol ag'a bagli olmasin
                # ve ZOR hal sinansin.
                sf.route("**://*/**", lambda r: (r.continue_()
                         if r.request.url.startswith(TABAN) else r.abort()))
                sf.goto(TABAN + yolu, wait_until="domcontentloaded", timeout=20000)
                sf.wait_for_timeout(2500)
                return sf, hata

            # 1) Hicbir sayfa JS hatasi firlatmamali (CDN'siz).
            for yolu in SAYFALAR:
                sf, hata = sayfa_ac(yolu)
                if hata:
                    sorunlar.append("%s: %s" % (yolu, hata[0]))
                govde = (sf.inner_text("body") or "").strip()
                if len(govde) < 40:
                    sorunlar.append("%s: sayfa bos (%d karakter)" % (yolu, len(govde)))
                sf.close()

            # 1b) Hicbir [data-giris] bolumu KIRPILI kalmamali.
            #
            # sahne.css bu bolumleri perdeyle kapatiyor ve sahne.js
            # aciyor. Acilmazsa oge DOM'da, metni yerinde, olculebilir
            # bir kutusu var -- ama kullanici hicbir sey gormuyor.
            # checkVisibility() bile "gorunur" diyor, cunku clip-path'e
            # bakmiyor. Statik kontrol (test.py) bildigim SEKLI yakaliyor;
            # bu kontrol SONUCU olcuyor.
            for yolu in ("/index.html", "/isletme.html?il=34&id=node/8223784325",
                         "/hakkinda.html"):
                sf, _ = sayfa_ac(yolu)
                sf.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                sf.wait_for_timeout(2600)
                kirpik = sf.evaluate("""() => [...document.querySelectorAll('[data-giris]')]
                    .filter(e => { const s = getComputedStyle(e);
                        return parseFloat(s.opacity) < 0.05 ||
                               (s.clipPath || '').includes('100%'); })
                    .map(e => e.tagName.toLowerCase() + '.' +
                              String(e.className || '').split(' ')[0])""")
                if kirpik:
                    sorunlar.append("%s: perde acilmayan bolum %s" % (yolu, kirpik))
                sf.close()

            # 2) Harita YOKKEN kesfet calismali. Asil bulunan hata buydu.
            sf, hata = sayfa_ac("/kesfet.html?il=06")
            kart = sf.eval_on_selector_all(".kart", "n => n.length")
            # Kutunun VARLIGI degil METNI olculuyor: bos bir kutu
            # kullaniciya haritanin neden gitigini soylemiyor ve
            # "yerine bir sey kondu" diye gecen bir kontrol, konmadigini
            # gizler. Sabote edilerek gorüldü.
            yedek = sf.eval_on_selector_all(
                ".harita-yok", "n => n.map(x => x.innerText.trim()).join('')")
            if kart == 0:
                sorunlar.append("Leaflet yokken kesfet hic kart cizmiyor")
            if len(yedek) < 30:
                sorunlar.append("Leaflet yokken harita yerine aciklama konmuyor "
                                "(kutu metni %d karakter)" % len(yedek))
            sf.close()

            # 3) Harita VARKEN normal yol izlenmeli: erken donus olmamali.
            sf, hata = sayfa_ac("/kesfet.html?il=06", LEAFLET_TAKLIT)
            cagri = set(sf.evaluate("window.__cagri || []"))
            kart2 = sf.eval_on_selector_all(".kart", "n => n.length")
            yedek2 = sf.eval_on_selector_all(".harita-yok", "n => n.length")
            for gerekli in ("map", "tileLayer", "layerGroup", "circleMarker"):
                if gerekli not in cagri:
                    sorunlar.append("Leaflet varken L.%s hic cagrilmadi" % gerekli)
            if yedek2:
                sorunlar.append("Leaflet varken 'harita yuklenemedi' kutusu cikiyor")
            if kart2 == 0:
                sorunlar.append("Leaflet varken kesfet hic kart cizmiyor")
            sf.close()
            t.close()

        if sorunlar:
            for x in sorunlar:
                print("  HATA: " + x)
            return False
        print("kontrol gecti: %d sayfa JS hatasiz, kesfet haritali ve haritasiz calisiyor"
              % len(SAYFALAR))
        return True
    finally:
        sunucu.terminate()
        try:
            sunucu.wait(timeout=5)
        except Exception:
            sunucu.kill()


if __name__ == "__main__":
    s = kendini_kontrol_et()
    sys.exit(0 if s is not False else 1)
