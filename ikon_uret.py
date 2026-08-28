#!/usr/bin/env python3
"""Uygulama ikonlarini app/marka-ikon.svg'den uretir (PWA / Play Store).

    python ikon_uret.py          # app/ikon/*.png yazar
    python ikon_uret.py test     # kaynak ve ciktilar tutarli mi

NEDEN SVG'DEN, NEDEN PILLOW'DA YENIDEN CIZEREK DEGIL
====================================================
Onceki surumu sekli Pillow ile ELDE CIZIYORDU. Yani ayni marka iki yerde
tanimliydi: sayfalarin <link rel="icon"> SVG'sinde bir kez, bu betikte bir
kez. Ikisi ayrisirsa uygulama ikonu ile sekme ikonu farkli olur ve bunu
kimse fark etmez -- ikona kimse iki kez bakmiyor.

Artik marka TEK dosyada (app/marka-ikon.svg) ve PNG'ler ondan turetiliyor.
Sekme ikonu da ayni dosyayi kullaniyor (app/marka.svg).

NEDEN TARAYICI ILE
==================
Marka gradyan ve dondurulmus dikdortgen tasiyor; ikisini de Pillow'da
elle uretmek, SVG'yi ikinci kez yazmak demekti. Chromium zaten depoda
(test_sayfa.py). Uretim NADIR yapiliyor -- her itmede degil.

IKI AYRI SVG, IKI AYRI IS
=========================
  marka.svg       acik/koyu zemine oturan LOGO isareti (turuncu igne).
  marka-ikon.svg  UYGULAMA ikonu: turuncu zemin, beyaz igne. Android ve
                  iOS ikonu kendi zeminini istiyor; logoyu saydam
                  zeminle vermek, ana ekranda renksiz bir leke birakirdi.

MASKELENEBILIR SURUM AYRI
=========================
Android ikonu daire, damla ya da kare olarak KIRPIYOR. Guvenli bolge
ortadaki %80'lik daire. Maskelenebilir surumde isaret %78'e kuculuyor;
kucultmeseydik igne'nin ucu ve kartlar daire maskede kesilirdi.
"""
import glob
import io
import os
import re
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
UYGULAMA = os.path.join(KOK, "app")
CIKTI = os.path.join(UYGULAMA, "ikon")
KAYNAK = os.path.join(UYGULAMA, "marka-ikon.svg")
LOGO = os.path.join(UYGULAMA, "marka.svg")

# stil.css ile AYNI olmali; asagidaki kontrol karsilastiriyor.
MARKA = "#ff7a00"
LACIVERT = "#0f172a"

# 192 ve 512 PWA'nin istedigi asgari cift; maskelenebilir 512 Android
# adaptive icon icin; 1024 Play magaza girisi icin.
OLCULER = [("ikon-192.png", 192, False),
           ("ikon-512.png", 512, False),
           ("ikon-maske-512.png", 512, True),
           ("ikon-1024.png", 1024, False)]

MASKE_ORAN = 0.78          # guvenli bolge


def _tarayici():
    y = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
    return y[0] if y else None


def uret():
    from playwright.sync_api import sync_playwright
    svg = io.open(KAYNAK, encoding="utf-8").read()
    os.makedirs(CIKTI, exist_ok=True)
    yol = _tarayici()
    with sync_playwright() as p:
        t = (p.chromium.launch(executable_path=yol, args=["--no-sandbox"])
             if yol else p.chromium.launch(args=["--no-sandbox"]))
        for ad, boyut, maske in OLCULER:
            if maske:
                # Zemin TUVALIN TAMAMI, isaret ortada kucultulmus.
                ic = ('<div style="position:absolute;inset:0;background:'
                      '#f4690a"></div>'
                      '<div style="position:absolute;inset:%d%%">%s</div>'
                      % (round((1 - MASKE_ORAN) * 50),
                         svg.replace("<svg", '<svg width="100%" height="100%"', 1)))
            else:
                ic = svg.replace("<svg", '<svg width="%d" height="%d"' % (boyut, boyut), 1)
            sf = t.new_page(viewport={"width": boyut, "height": boyut},
                            device_scale_factor=1)
            sf.set_content('<body style="margin:0;position:relative;width:%dpx;'
                           'height:%dpx;overflow:hidden">%s</body>'
                           % (boyut, boyut, ic))
            sf.wait_for_timeout(250)
            sf.screenshot(path=os.path.join(CIKTI, ad), omit_background=False)
            sf.close()
            print("  %-22s %4dx%-4d %s" % (ad, boyut, boyut,
                                           "maskelenebilir" if maske else ""))
        t.close()
    print("%d ikon yazildi: app/ikon/" % len(OLCULER))


def kendini_kontrol_et():
    s = []
    for ad, yol in (("marka.svg", LOGO), ("marka-ikon.svg", KAYNAK)):
        if not os.path.exists(yol):
            s.append("app/%s yok" % ad)
    if s:
        return s

    ikon = io.open(KAYNAK, encoding="utf-8").read()
    logo = io.open(LOGO, encoding="utf-8").read()

    # Renkler stil.css ile ayni mi. Ayrisirsa ikon markadan kopar.
    stil = io.open(os.path.join(UYGULAMA, "stil.css"), encoding="utf-8").read().replace(" ", "")
    if ("--marka:" + MARKA) not in stil:
        s.append("stil.css'te --marka %s degil" % MARKA)
    if ("--zemin:" + LACIVERT) not in stil:
        s.append("stil.css'te --zemin %s degil" % LACIVERT)

    # Iki SVG de AYNI markayi cizmeli: igne, kart ve catal-bicak.
    # Sayilar kabaca esit olmali; biri elden gecirilip oteki unutulursa
    # sekme ikonu ile uygulama ikonu ayrisir.
    for ad, govde in (("marka.svg", logo), ("marka-ikon.svg", ikon)):
        if govde.count("<rect") < 2:
            s.append("%s: cuzdan kartlari yok (en az iki <rect>)" % ad)
        if "circle" not in govde:
            s.append("%s: catal-bicak dairesi yok" % ad)
        if govde.count("<path") < 3:
            s.append("%s: igne ya da catal-bicak eksik" % ad)
        if "linearGradient" not in govde:
            s.append("%s: gradyan yok" % ad)
    # Uygulama ikonu ZEMIN tasimali (saydam olamaz), logo TASIMAMALI.
    if '<rect width="64" height="64"' not in ikon:
        s.append("marka-ikon.svg: tam zemin yok; ana ekranda renksiz leke olur")
    if '<rect width="64" height="64"' in logo:
        s.append("marka.svg: tam zemin var; logo saydam olmali")

    # Sayfalar AYNI dosyayi kullanmali; satir ici bir kopya, markanin
    # ikinci bir tanimi demek.
    for y in sorted(glob.glob(os.path.join(UYGULAMA, "*.html"))):
        h = io.open(y, encoding="utf-8").read()
        if 'href="marka.svg"' not in h:
            s.append("%s marka.svg'yi kullanmiyor" % os.path.basename(y))
        # SATIR ICI IKON aranirken <link rel="icon"> ETIKETININ ICINE
        # bakiliyor. Ilk yazimda "sayfada data URI var mi" diye
        # bakiyordu ve <select> okunun arka planina takiliyordu --
        # yani DOGRU davranisi hata sayiyordu.
        if re.search(r'<link[^>]*rel="icon"[^>]*data:image/svg', h):
            s.append("%s hala satir ici ikon tasiyor" % os.path.basename(y))

    try:
        from PIL import Image
    except ImportError:
        return s + ["Pillow kurulu degil: pip install pillow"]

    for ad, boyut, maske in OLCULER:
        yol = os.path.join(CIKTI, ad)
        if not os.path.exists(yol):
            s.append("%s yok (python ikon_uret.py calistir)" % ad)
            continue
        g = Image.open(yol).convert("RGB")
        if g.size != (boyut, boyut):
            s.append("%s olcusu %s, %dx%d olmali" % (ad, g.size, boyut, boyut))
            continue
        # Kose DOLU olmali: saydam ya da beyaz kose, kare maskede
        # gorunur bir ucgen birakir.
        k = g.getpixel((2, 2))
        if max(k) - min(k) < 20:
            s.append("%s kosesi renksiz (%s); zemin cizilmemis olabilir" % (ad, k))
        # Beyaz igne GERCEKTEN cizilmis mi: bos bir turuncu kare de
        # olcu ve kose kontrolunden gecerdi.
        orta = g.getpixel((boyut // 2, int(boyut * 0.62)))
        if min(orta) < 200:
            s.append("%s ortasinda beyaz igne yok (%s)" % (ad, orta))
    return s


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sorunlar = kendini_kontrol_et()
        for x in sorunlar:
            print("  HATA: " + x)
        if not sorunlar:
            print("kontrol gecti: %d ikon marka-ikon.svg'den, renkler stil.css ile ayni"
                  % len(OLCULER))
        sys.exit(1 if sorunlar else 0)
    uret()
