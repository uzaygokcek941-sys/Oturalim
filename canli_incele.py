#!/usr/bin/env python3
"""YAYINDAKI siteyi bastan sona GEZER ve NE GORDUGUNU yazar.

    python canli_incele.py https://oturalim.vercel.app

canli_test.py'DEN FARKI: o bir KAPI, bu bir RAPOR.
canli_test.py belirli sartlari siniyor ve saglanmazsa DUSUYOR; is
akisinda her sabah kosuyor. Bu betik hicbir sey hakkinda karar
vermiyor -- 14 sayfayi aciyor, olctugunu yaziyor ve YORUMU insana
birakiyor. Ikisi ayri duruyor cunku bir raporu kapiya cevirmek
raporu kisitlar, kapiyi rapora cevirmek de kapiyi ise yaramaz yapar.

TOPLANANLAR, her sayfa icin:
  - HTTP durumu ve yuklenme suresi
  - JS hatalari
  - CSP ihlalleri (ENGELLENEN SCRIPT HATA FIRLATMIYOR, ayri toplanmali)
  - BASARISIZ istekler (404 gorsel, olu baglanti)
  - baslik ve aciklama meta'si
  - alt metni olmayan gorseller
  - 44 px'ten kucuk dokunma hedefleri (WCAG 2.5.8)
  - yatay tasma (320 / 390 / 768 px)

BU BETIK HICBIR SEY YAZMIYOR. Yalniz okuyor.
"""
import os
import sys

BEKLE = 20000
GENISLIKLER = (320, 390, 768)

SAYFALAR = [
    ("/", "ana ekran"),
    ("/kesfet.html?il=34", "kesfet - Istanbul"),
    ("/kesfet.html?il=06", "kesfet - Ankara"),
    ("/kesfet.html?il=35", "kesfet - Izmir"),
    ("/giris.html", "giris"),
    ("/paylas.html", "fis paylas"),
    ("/topluluk.html", "topluluk"),
    ("/hakkinda.html", "hakkinda"),
    ("/gizlilik.html", "gizlilik"),
    ("/hesabim.html", "hesabim (giris ister)"),
    ("/profil.html", "profil"),
    ("/isletme.html", "isletme"),
    ("/isletme-giris.html", "isletme girisi"),
    ("/isletmem.html", "isletmem (giris ister)"),
    ("/yonetim.html", "yonetim (giris ister)"),
    ("/cevrimdisi.html", "cevrimdisi"),
]


def _tarayici_yolu():
    kok = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if kok and os.path.isdir(kok):
        import glob
        for d in sorted(glob.glob(os.path.join(kok, "chromium-*",
                                               "chrome-linux", "chrome"))):
            return d
    return None


def _sayfayi_incele(ctx, taban, yol, ad):
    """Tek sayfa. Sozluk donuyor; KARAR VERMIYOR, olcuyor."""
    sayfa = ctx.new_page()
    hata, csp, kirik = [], [], []
    sayfa.on("pageerror", lambda e: hata.append(str(e).split("\n")[0][:110]))

    def konsol(m):
        y = m.text
        if "Content Security Policy" in y or "Refused to" in y:
            csp.append(y[:150])
    sayfa.on("console", konsol)

    # BASARISIZ ISTEKLER. Bir 404 gorsel sayfayi cokertmiyor ve konsola
    # da her zaman dusmuyor; sessizce eksik kaliyor.
    def yanit(r):
        if r.status >= 400:
            kirik.append("%d %s" % (r.status, r.url[-70:]))
    sayfa.on("response", yanit)

    r = {"ad": ad, "yol": yol}
    try:
        import time as _t
        t0 = _t.monotonic()
        y = sayfa.goto(taban + yol, wait_until="domcontentloaded", timeout=BEKLE)
        r["http"] = y.status if y else "?"
        try:
            sayfa.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass                      # networkidle gelmeyebilir; sorun degil
        r["ms"] = int((_t.monotonic() - t0) * 1000)

        r["baslik"] = (sayfa.title() or "").strip()
        # SON ADRES. "giris ister" sayfalari giris yoksa yonlendiriyor;
        # ilk raporumda bunu gormedigim icin giris.html'i uc ayri sayfa
        # adiyla olcup uc kez ayni "hatayi" yazdim.
        son = sayfa.url.replace(taban, "")
        if son.split("?")[0] != yol.split("?")[0]:
            r["yonlendi"] = son
            # YONLENDIRME ISTEMCI TARAFINDA ve networkidle'dan SONRA
            # olabiliyor: hedef sayfanin <head>'i daha ayrisirken
            # olcuyordum. Belirtisi tutarsizlikti -- hesabim "meta
            # description YOK" diyordu, ayni giris.html'e yonlenen
            # yonetim ise demiyordu. Ayni sayfa iki farkli sonuc
            # veremez; demek ki olcum erkendi.
            sayfa.wait_for_timeout(800)
        r.update(sayfa.evaluate("""() => {
            if (!document.body) return {yonlendirdi: true, aciklama: 0,
                     h1: 1, gorsel: 0, altsiz: 0, kucuk_hedef: 0,
                     lang: document.documentElement.lang || '', metin: 0};
            const meta = document.querySelector('meta[name=description]');
            const gorsel = [...document.querySelectorAll('img')];
            // SATIR ICI BAGLAR SAYILMIYOR ve bu bir duzeltme: ilk
            // yazimda gizlilik sayfasinda 15 "ihlal" saydim, oysa
            // WCAG 2.5.8 metin icindeki baglari ACIKCA muaf tutuyor.
            // Olmayan bir ihlali raporlamak, gercek olanlari da
            // bakilmaz hale getirir.
            const sec = 'button, a, select, input:not([type=hidden]), [role=button]';
            let kucuk = 0;
            for (const e of document.querySelectorAll(sec)){
              const b = e.getBoundingClientRect();
              if (b.width === 0 && b.height === 0) continue;
              if (e.tagName === 'A' &&
                  getComputedStyle(e).display === 'inline') continue;
              if (b.height < 44) kucuk++;
            }
            return {
              aciklama: meta ? (meta.content || '').length : 0,
              // YALNIZ GORUNEN h1. Ilk yazimda hepsini sayiyordum ve
              // giris.html'de "3 h1" diye rapor ettim -- oysa uc panel
              // basligi var (giris / kayit / sifre sifirlama) ve ayni
              // anda YALNIZ BIRI gorunuyor. Gizli bir basligi ihlal
              // saymak, olmayan bir hatayi rapor etmektir.
              h1: [...document.querySelectorAll('h1')]
                    .filter(e => e.getClientRects().length > 0).length,
              gorsel: gorsel.length,
              // alt="" BOS DEGIL, KARARDIR: WCAG suslemeli gorseli boyle
              // isaretliyor ve ekran okuyucu onu ATLIYOR. Eksik olan
              // sey alt ozniteliginin HIC OLMAMASI.
              altsiz: gorsel.filter(i => !i.hasAttribute('alt')).length,
              alt_bos: gorsel.filter(i => i.hasAttribute('alt') &&
                                          !i.alt.trim()).length,
              // 44 px'i GECMEYEN denetimlerin ne oldugunu da yaz;
              // sayi tek basina duzeltilemez, secici duzeltilebilir.
              kucuk_ne: (() => {
                const c = [];
                for (const e of document.querySelectorAll(
                       'button, a, select, input:not([type=hidden]), [role=button]')){
                  const b = e.getBoundingClientRect();
                  if (b.width === 0 && b.height === 0) continue;
                  if (e.tagName === 'A' &&
                      getComputedStyle(e).display === 'inline') continue;
                  if (b.height < 44)
                    c.push((e.id ? '#' + e.id : e.tagName.toLowerCase()) +
                           ':' + Math.round(b.height));
                }
                return c.slice(0, 6);
              })(),
              kucuk_hedef: kucuk,
              lang: document.documentElement.lang || '',
              // document.body NULL olabiliyor: hesabim.html giris
              // yoksa yonlendiriyor ve olcum ani govdesiz yakaliyor.
              // Ilk yazimda burasi COKUYORDU ve sayfa "incelenemedi"
              // diye gecti -- oysa sayfanin kendisi saglam.
              metin: (document.body ? document.body.innerText : '').trim().length
            };
        }"""))

        # Yatay tasma her genislikte AYRI olculuyor: 390'da duran bir
        # duzen 320'de tasabiliyor.
        tasma = []
        for g in GENISLIKLER:
            sayfa.set_viewport_size({"width": g, "height": 780})
            sayfa.wait_for_timeout(350)
            if sayfa.evaluate("() => document.documentElement.scrollWidth > "
                              "document.documentElement.clientWidth + 1"):
                tasma.append(g)
        r["tasma"] = tasma
    except Exception as e:
        r["cokme"] = "%s: %s" % (type(e).__name__, str(e).split("\n")[0][:90])
    finally:
        r["hata"] = hata[:3]
        r["csp"] = csp[:2]
        # Ayni adres tekrar tekrar dusebiliyor; tekilleniyor.
        r["kirik"] = sorted(set(kirik))[:4]
        sayfa.close()
    return r


def _kesfet_derin(ctx, taban):
    """Kesfet ekraninin ICINE bakiyor: fotograf, fiyat, atif, harita."""
    sayfa = ctx.new_page()
    try:
        sayfa.goto(taban + "/kesfet.html?il=34", wait_until="domcontentloaded",
                   timeout=BEKLE)
        sayfa.wait_for_selector(".kart", timeout=BEKLE)
        sayfa.wait_for_timeout(5000)      # fotograflar Supabase'ten gelsin
        return sayfa.evaluate("""() => {
            const k = [...document.querySelectorAll('.kart')];
            const img = [...document.querySelectorAll('.kart-gorsel img')]
                          .filter(i => !i.hidden);
            return {
              kart: k.length,
              fotograf: img.length,
              yuklenmeyen: img.filter(i => i.complete && i.naturalWidth === 0).length,
              atifsiz: img.filter(i => !(i.title || '').trim()).length,
              fiyatli: k.filter(x => /\\d[\\d.]*\\s*₺/.test(x.innerText)).length,
              rozet: k.filter(x => /fiyat|ölçüm|fiş/i.test(x.innerText)).length,
              harita: !!document.querySelector('.leaflet-container'),
              ornek_atif: img.slice(0, 3).map(i => (i.title || '').slice(0, 70))
            };
        }""")
    except Exception as e:
        return {"hata": "%s: %s" % (type(e).__name__, str(e)[:80])}
    finally:
        sayfa.close()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    taban = sys.argv[1].rstrip("/")
    if not taban.startswith("http"):
        taban = "https://" + taban
    from playwright.sync_api import sync_playwright

    print("INCELEME: %s\n" % taban, flush=True)
    with sync_playwright() as p:
        yol = _tarayici_yolu()
        t = (p.chromium.launch(executable_path=yol, args=["--no-sandbox"])
             if yol else p.chromium.launch(args=["--no-sandbox"]))
        ctx = t.new_context(viewport={"width": 390, "height": 780})
        try:
            sonuc = [_sayfayi_incele(ctx, taban, y, a) for y, a in SAYFALAR]
            derin = _kesfet_derin(ctx, taban)
        finally:
            ctx.close()
            t.close()

    print("%-26s %4s %6s %5s %4s %4s %5s %s"
          % ("SAYFA", "HTTP", "ms", "metin", "JS", "CSP", "404", "tasma"))
    print("-" * 84)
    for r in sonuc:
        if "cokme" in r:
            print("%-26s  COKTU: %s" % (r["ad"], r["cokme"]))
            continue
        print("%-26s %4s %6s %5s %4d %4d %5d %s"
              % (r["ad"], r["http"], r["ms"], r["metin"], len(r["hata"]),
                 len(r["csp"]), len(r["kirik"]),
                 ",".join(str(x) for x in r["tasma"]) or "-"))

    print("\nAYRINTI (yalniz sorunu olanlar)")
    temiz = True
    for r in sonuc:
        satir = []
        if r.get("hata"):
            satir += ["JS: " + h for h in r["hata"]]
        if r.get("csp"):
            satir += ["CSP: " + c for c in r["csp"]]
        if r.get("kirik"):
            satir += ["istek: " + k for k in r["kirik"]]
        if r.get("altsiz"):
            satir.append("alt OZNITELIGI OLMAYAN gorsel: %d/%d"
                         % (r["altsiz"], r["gorsel"]))
        if r.get("kucuk_hedef"):
            satir.append("44 px'ten kisa: %d -> %s"
                         % (r["kucuk_hedef"], ", ".join(r.get("kucuk_ne", []))))
        if r.get("h1") != 1:
            satir.append("h1 sayisi: %s (1 olmali)" % r.get("h1"))
        if not r.get("aciklama"):
            satir.append("meta description YOK")
        if r.get("lang") != "tr":
            satir.append("html lang: %r" % r.get("lang"))
        if r.get("tasma"):
            satir.append("yatay tasma: %s px" % r["tasma"])
        if r.get("yonlendi"):
            satir.append("YONLENDIRDI -> %s (asagidaki olcumler O sayfanin)"
                         % r["yonlendi"])
        if satir:
            temiz = False
            print("\n  %s (%s)" % (r["ad"], r["yol"]))
            for x in satir:
                print("    - " + x)
    if temiz:
        print("  yok")

    print("\nKESFET ICI (Istanbul)")
    for a, v in derin.items():
        print("  %-14s %s" % (a, v))

    # SAYIYA CEVIRMEDEN: bu bir rapor, kapi degil. Karar insanin.
    print("\nBu bir RAPOR, kapi degil -- hicbir sey 'basarisiz' sayilmadi.")
    print("Kapi canli_test.py; her sabah canli.yml ile kosuyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
