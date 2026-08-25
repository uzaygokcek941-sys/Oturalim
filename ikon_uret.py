#!/usr/bin/env python3
"""Uygulama ikonlarini uretir (PWA / Play Store).

    python ikon_uret.py          # app/ikon/*.png yazar
    python ikon_uret.py test     # dosyalar var mi, olculeri dogru mu

NEDEN BIR BETIK
===============
Ikon zaten VAR ve tek yerde tanimli: sayfalarin <link rel="icon"> icindeki
SVG. Ayni sekli bir de PNG olarak elle cizmek, markanin iki yerde iki turlu
olmasi demekti -- birini degistirip otekini unutmak bu depoda daha once
oldu (mutfak etiketi iki sayfada iki turlu, fiyat siniri iki boru hattinda
farkli). Burasi AYNI kaynaktan uretiyor: renkler stil.css'ten, sekil
asagidaki olculerden ve ikisi de tek yerde.

MASKELENEBILIR IKON AYRI URETILIYOR
===================================
Android ikonu daire, damla ya da kare olarak KIRPIYOR (adaptive icon).
Kirpma payi 64x64'luk tuvalde her kenardan ~%10; guvenli bolge ortadaki
%80'lik daire. Normal ikonu maskelenebilir diye vermek, fincanin
kulplarinin kesilmesi demekti. Maskelenebilir surumde sekil %62'ye
kuculuyor ve arka plan tuvalin TAMAMINI dolduruyor -- kose yuvarlamasi
yok, cunku maskeyi Android koyuyor.

KENAR YUMUSATMA
===============
Pillow'un ciziciSi kenar yumusatma yapmiyor. 4 kat buyuk cizip kuculterek
(supersampling) yapiliyor; 512 px ikon once 2048 px olarak ciziliyor.
"""
import io
import os
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "app", "ikon")

# stil.css ile AYNI olmali; test.py ikisini karsilastiriyor.
ZEMIN = "#15110e"          # --zemin (koyu tema)
VURGU = "#f08a3c"          # --vurgu

# 64x64 tuvalde sekil. Sayfalarin <link rel="icon"> SVG'siyle ayni:
#   <path d="M20 16v12a12 12 0 0 0 24 0V16" stroke-width="5" linecap="round"/>
#   <path d="M32 40v10" stroke-width="5" linecap="round"/>
BIRIM = 64.0
KALINLIK = 5.0
KOSE = 14.0

# Uretilecek olculer. 192 ve 512 PWA'nin istedigi asgari ciftidir;
# 512 maskelenebilir Android adaptive icon icin; 1024 Play magaza girisi
# icin (Play 512 istiyor ama kaynagi buyuk tutmak sonradan olcek
# degistirmeyi ucuzlatiyor).
OLCULER = [("ikon-192.png", 192, False),
           ("ikon-512.png", 512, False),
           ("ikon-maske-512.png", 512, True),
           ("ikon-1024.png", 1024, False)]

BUYUTME = 4                # supersampling


def _ciz(boyut, maskelenebilir):
    from PIL import Image, ImageDraw
    B = boyut * BUYUTME
    g = Image.new("RGBA", (B, B), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)

    if maskelenebilir:
        # Arka plan TUVALIN TAMAMI: kirpmayi Android yapiyor, kose
        # yuvarlamasini da. Buraya kose koymak, daire maskede kararmis
        # bir halka birakirdi.
        d.rectangle([0, 0, B, B], fill=ZEMIN)
        olcek = B / BIRIM * 0.62          # guvenli bolge
    else:
        d.rounded_rectangle([0, 0, B - 1, B - 1],
                            radius=KOSE * B / BIRIM, fill=ZEMIN)
        olcek = B / BIRIM

    kayma = (B - BIRIM * olcek) / 2
    def n(x, y):
        return (kayma + x * olcek, kayma + y * olcek)

    kalin = int(round(KALINLIK * olcek))
    # Fincan govdesi: (20,16) -> (20,28) -> yarim daire -> (44,28) -> (44,16)
    d.line([n(20, 16), n(20, 28)], fill=VURGU, width=kalin)
    d.line([n(44, 16), n(44, 28)], fill=VURGU, width=kalin)
    # Pillow'un arc'i kalinligi ICERI dogru cizyor; SVG ise cizgiyi yolun
    # UZERINDE ortaliyor. Kutuyu yarim kalinlik genisletmezsek dikey
    # cizgilerle yay birlesim yerinde yarim kalinlik kayiyor ve iki yanda
    # gozle gorulur bir centik kaliyor -- ilk uretimde tam bu oldu.
    yari = kalin / 2.0
    sol, ust = n(20, 16)
    sag, alt = n(44, 40)
    d.arc([sol - yari, ust - yari, sag + yari, alt + yari],
          start=0, end=180, fill=VURGU, width=kalin)
    # Yuvarlak uclar: arc ile line birlesim yerinde centik birakiyor.
    for p in ((20, 16), (44, 16), (32, 40), (32, 50)):
        x, y = n(*p)
        r = kalin / 2
        d.ellipse([x - r, y - r, x + r, y + r], fill=VURGU)
    # Ayak
    d.line([n(32, 40), n(32, 50)], fill=VURGU, width=kalin)

    return g.resize((boyut, boyut), Image.LANCZOS)


def uret():
    os.makedirs(CIKTI, exist_ok=True)
    for ad, boyut, maske in OLCULER:
        _ciz(boyut, maske).save(os.path.join(CIKTI, ad), "PNG", optimize=True)
        print("  %-22s %4dx%-4d %s" % (ad, boyut, boyut,
                                       "maskelenebilir" if maske else ""))
    print("%d ikon yazildi: app/ikon/" % len(OLCULER))


def kendini_kontrol_et():
    s = []
    try:
        from PIL import Image
    except ImportError:
        return ["Pillow kurulu degil: pip install pillow"]

    # Renkler stil.css ile ayni mi. Ayrisirsa ikon markadan kopar ve
    # bunu kimse fark etmez -- ikona kimse iki kez bakmiyor.
    stil = io.open(os.path.join(KOK, "app", "stil.css"), encoding="utf-8").read()
    for ad, deger in (("--zemin", ZEMIN), ("--vurgu", VURGU)):
        if (ad + ":" + deger) not in stil.replace(" ", ""):
            s.append("%s stil.css'te %s degil" % (ad, deger))

    # Sekil, sayfalardaki SVG ile ayni mi. SVG tek satir; olculeri oradan
    # okuyup buradakiyle karsilastiriyoruz.
    sayfa = io.open(os.path.join(KOK, "app", "index.html"), encoding="utf-8").read()
    for parca in ("rx='14'", "M20 16v12", "M32 40v10", "stroke-width='5'"):
        if parca not in sayfa:
            s.append("index.html'deki ikon SVG'si degismis: %r yok" % parca)

    for ad, boyut, maske in OLCULER:
        yol = os.path.join(CIKTI, ad)
        if not os.path.exists(yol):
            s.append("%s yok (python ikon_uret.py calistir)" % ad)
            continue
        g = Image.open(yol)
        if g.size != (boyut, boyut):
            s.append("%s olcusu %s, %dx%d olmali" % (ad, g.size, boyut, boyut))
        if g.mode not in ("RGBA", "RGB"):
            s.append("%s kipi %s" % (ad, g.mode))
        # Maskelenebilir ikonun KOSESI dolu olmali: saydam kose, daire
        # maskede sorun cikarmaz ama kare maskede beyaz ucgen birakir.
        if maske:
            k = g.convert("RGBA").getpixel((1, 1))
            if k[3] < 250:
                s.append("%s kosesi saydam; maskelenebilir ikon tuvali "
                         "tamamen doldurmali" % ad)
        else:
            k = g.convert("RGBA").getpixel((1, 1))
            if k[3] > 200:
                s.append("%s kosesi dolu; normal ikonda kose yuvarlamasi "
                         "gorunmeli" % ad)
        # Vurgu rengi gercekten ciziliyor mu: bos bir kare de olcu
        # kontrolunden gecerdi.
        renkler = {p[:3] for _, p in g.convert("RGBA").getcolors(boyut * boyut) or []}
        hedef = tuple(int(VURGU[i:i+2], 16) for i in (1, 3, 5))
        if not any(abs(r - hedef[0]) < 12 and abs(gg - hedef[1]) < 12
                   and abs(b - hedef[2]) < 12 for r, gg, b in renkler):
            s.append("%s icinde vurgu rengi yok; sekil cizilmemis olabilir" % ad)
    return s


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sorunlar = kendini_kontrol_et()
        for x in sorunlar:
            print("  HATA: " + x)
        if not sorunlar:
            print("kontrol gecti: %d ikon, olculer ve renkler stil.css ile ayni"
                  % len(OLCULER))
        sys.exit(1 if sorunlar else 0)
    uret()
