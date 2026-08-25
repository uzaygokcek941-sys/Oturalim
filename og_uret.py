# -*- coding: utf-8 -*-
"""Paylasim karti (app/og.png) uretir.

NEDEN VAR: bu dosya ELLE yapilmisti ve iki kez birden eskidi.

  1) ESKI MARKA ADI. Kart hala "Oturalim" yaziyordu. Marka 2026-08-25'te
     Cebimde oldu (CEBIMDE.md), 12 sayfanin hepsi degisti, kart
     degismedi -- yani her paylasilan baglantinin onizlemesinde eski ad
     duruyordu.

  2) ESKI SAYI. Kartta "36.102 mekan" yaziyor; veri 35.852. Kimse
     duzeltemedi cunku sayiyi kartin icine kim yazdiysa o da elle yazdi.

Ikisi de ayni sebepten: kartin kaynagi yoktu. Artik var ve sayi VERIDEN
okunuyor (app/veri/index.json), elle yazilmiyor.

TASARIM UYGULAMANIN KENDI TOKENLARINDAN GELIYOR. Kart bir tarayicida,
app/stil.css yuklu halde ciziliyor -- renkler, yaricaplar ve yazi
tipleri ikinci bir yerde tanimlanmiyor. Marka maketleriyle ayni acik
tema: beyaz zemin, turuncu vurgu, lacivert yazi.

SAYI PNG'NIN ICINE DAMGALANIYOR (tEXt "cebimde-mekan"). test.py o
damgayi veriyle karsilastiriyor; kart eskirse SESSIZ kalmiyor.

    python og_uret.py          -> app/og.png
    python og_uret.py test     -> kendi kontrolleri
"""
import base64
import glob
import io
import json
import os
import re
import ssl
import sys
import urllib.request

KOK = os.path.dirname(os.path.abspath(__file__))
UYGULAMA = os.path.join(KOK, "app")
CIKTI = os.path.join(UYGULAMA, "og.png")
DAMGA = "cebimde-mekan"

# Facebook/Twitter/WhatsApp onizlemesinin bekledigi olcu.
EN, BOY = 1200, 630

# Marka yazi tipleri. Uygulamanin kendi kullandigi ikisi (stil.css).
# Aile adi SAYFALARLA AYNI olmali. Uygulama Montserrat kullaniyor;
# kart baska bir yazi tipiyle cikarsa paylasim onizlemesi uygulamaya
# benzemez. test.py ikisini karsilastiriyor.
YAZI = ("https://fonts.googleapis.com/css2"
        "?family=Montserrat:wght@400;500;600;700&display=block")

# Tarayici gorseli GOMULU aliyor, agdan degil.
#
# NEDEN: kart <link> ile Google Fonts'tan cekilerek cizildiginde
# tarayicinin agi kapali oldugu ortamlarda SESSIZCE yedek yazi tipine
# dusuyor -- kart cikiyor, "calisti" gorunuyor, ama uygulamadan bambaska
# bir yazi tipiyle. Ilk denemede tam bu oldu: kart uretildi ve Fraunces
# yerine sistemin varsayilan sans'i ile ciziltdi.
#
# Yazi tipleri PYTHON'da indirilip base64 olarak isaretlemeye gomuluyor;
# cizim aninda ag'a hic gidilmiyor, yani ya dogru yazi tipiyle cikiyor ya
# da hic cikmiyor.
_ORNEK = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
_CA = "/root/.ccr/ca-bundle.crt"


def _indir(adres):
    istek = urllib.request.Request(adres, headers={"User-Agent": _ORNEK})
    baglam = ssl.create_default_context(cafile=_CA) if os.path.exists(_CA) else None
    return urllib.request.urlopen(istek, timeout=30, context=baglam).read()


def yazi_tipleri():
    """@font-face bloklari, woff2 dosyalari GOMULU halde.

    Latin disi alt kumeler ATILIYOR: kart Turkce ve latin-ext yetiyor.
    Hepsini gommek dosyayi gereksiz buyuturdu."""
    css = _indir(YAZI).decode("utf-8")
    bloklar = []
    for blok in re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{.*?\})",
                           css, re.S):
        alt, govde = blok
        if alt not in ("latin", "latin-ext"):
            continue
        m = re.search(r"url\((https://[^)]+\.woff2)\)", govde)
        if not m:
            continue
        ham = _indir(m.group(1))
        gomulu = "url(data:font/woff2;base64,%s)" % base64.b64encode(ham).decode()
        bloklar.append(govde.replace("url(%s)" % m.group(1), gomulu))
    if not bloklar:
        raise SystemExit("yazi tipleri indirilemedi: kart uretilmedi")
    return "\n".join(bloklar)


def veri_ozeti():
    """Kartta yazacak sayilar VERIDEN. Elle yazilan sayi eskiyor."""
    y = os.path.join(UYGULAMA, "veri", "index.json")
    d = json.load(io.open(y, encoding="utf-8"))
    iller = d["iller"]
    return sum(i["n"] for i in iller), len(iller)


def _sayi(n):
    return "{:,}".format(int(n)).replace(",", ".")


def kart_html(mekan, il, yazi=""):
    """Kartin isaretlemesi. stil.css YUKLENIYOR: renkler ve yaricaplar
    uygulamanin kendi tokenlarindan geliyor, burada tekrar tanimlanmiyor."""
    logo = io.open(os.path.join(UYGULAMA, "marka.svg"), encoding="utf-8").read()
    # <?xml ...?> ve yorumlar satir ici kullanimda gereksiz.
    logo = logo[logo.index("<svg"):]
    return """<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<link rel="stylesheet" href="stil.css">
<style>
%(yazi)s
  /* Tema SABIT ACIK: onizleme resmi okuyucunun temasina gore
     degismiyor, tek bir dosya. Marka maketlerinin hepsi acik. */
  html{ color-scheme:light }
  body{
    margin:0; width:%(en)spx; height:%(boy)spx; background:var(--zemin);
    color:var(--metin); display:flex; flex-direction:column;
    justify-content:center; gap:34px; padding:0 88px; box-sizing:border-box;
    position:relative; overflow:hidden;
  }
  /* Marka lekesi: sag alttan giren turuncu daire. Metnin arkasina
     gecmiyor -- kontrast olcusu bozulmasin. */
  .leke{
    position:absolute; right:-140px; bottom:-190px; width:560px; height:560px;
    border-radius:50%%; background:var(--vurgu-los);
  }
  .bas{ display:flex; align-items:center; gap:20px; position:relative }
  .bas svg{ width:78px; height:78px }
  .bas .ad{
    font-family:var(--font-baslik); font-size:62px; font-weight:700;
    letter-spacing:-.02em;
  }
  .bas .ad em{ font-style:normal; color:var(--vurgu) }
  h1{
    font-family:var(--font-baslik); font-size:78px; line-height:1.06;
    font-weight:700; letter-spacing:-.025em; margin:0; max-width:16ch;
    position:relative;
  }
  h1 em{ font-style:normal; color:var(--vurgu) }
  .alt{
    display:flex; align-items:center; gap:18px; font-size:27px;
    color:var(--metin-2); position:relative;
  }
  .alt b{ color:var(--metin); font-variant-numeric:tabular-nums }
  .nokta{ width:7px; height:7px; border-radius:50%%; background:var(--cizgi-2) }
</style></head>
<body>
  <div class="leke"></div>
  <div class="bas">%(logo)s<span class="ad">Ceb<em>imde</em></span></div>
  <h1>Cebindeki bütçeyle <em>keşfet</em>.</h1>
  <div class="alt">
    <span><b>%(mekan)s</b> mekan</span><span class="nokta"></span>
    <span><b>%(il)s</b> il</span><span class="nokta"></span>
    <span>ücretsiz · üyeliksiz · reklamsız</span>
  </div>
</body></html>""" % {"en": EN, "boy": BOY, "logo": logo, "yazi": yazi,
                     "mekan": _sayi(mekan), "il": _sayi(il)}


def _krom():
    for y in sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")):
        return y
    return None


def uret():
    from playwright.sync_api import sync_playwright
    from PIL import Image, PngImagePlugin

    mekan, il = veri_ozeti()
    gecici = os.path.join(UYGULAMA, "_og_gecici.html")
    io.open(gecici, "w", encoding="utf-8").write(
        kart_html(mekan, il, yazi_tipleri()))
    ham = CIKTI + ".ham.png"
    try:
        krom = _krom()
        with sync_playwright() as pw:
            b = pw.chromium.launch(executable_path=krom, args=["--no-sandbox"])
            s = b.new_page(viewport={"width": EN, "height": BOY},
                           device_scale_factor=1)
            s.goto("file://" + gecici, wait_until="load")
            # Yazi tipleri GERCEKTEN yuklendi mi. Gomulu olduklari icin
            # gelmemeleri artik bir hata; sessizce yedege dusmesin.
            s.evaluate("() => document.fonts.ready")
            s.wait_for_timeout(300)
            yuklu = s.evaluate(
                "() => [...document.fonts].filter(f => f.status === 'loaded')"
                ".map(f => f.family)")
            for aile in ("Montserrat",):
                if aile not in yuklu:
                    raise SystemExit("%s yuklenmedi: kart yedek yazi tipiyle "
                                     "cizilecekti, uretim durduruldu" % aile)
            s.screenshot(path=ham)
            b.close()
    finally:
        os.remove(gecici)

    # SAYIYI DOSYANIN ICINE DAMGALA: kart eskirse test.py soylesin.
    im = Image.open(ham).convert("RGB")
    bilgi = PngImagePlugin.PngInfo()
    bilgi.add_text(DAMGA, "%d/%d" % (mekan, il))
    im.save(CIKTI, "PNG", optimize=True, pnginfo=bilgi)
    os.remove(ham)
    print("app/og.png uretildi: %s mekan, %s il" % (_sayi(mekan), _sayi(il)))


def damga_oku():
    """PNG'ye damgalanan sayi. Kart hic uretilmemisse None."""
    from PIL import Image
    if not os.path.exists(CIKTI):
        return None
    with Image.open(CIKTI) as im:
        return (im.info or {}).get(DAMGA)


def kendini_kontrol_et():
    s = []
    mekan, il = veri_ozeti()
    if mekan < 1000 or il != 81:
        s.append("veri ozeti sacma: %s mekan, %s il" % (mekan, il))

    h = kart_html(mekan, il, "@font-face{font-family:'Montserrat'}")
    # Sayi ELLE degil veriden. Bir daha "36.102" gibi bir sayi
    # gomulmesin diye kartin icinde uretilmis sayi ARANIYOR.
    if _sayi(mekan) not in h:
        s.append("kartta mekan sayisi yok")
    # ESKI MARKA ADI GERI GELMESIN.
    if "Otural" in h:
        s.append("kartta eski marka adi geciyor")
    if "Cebimde" not in h.replace("Ceb<em>imde</em>", "Cebimde"):
        s.append("kartta marka adi yok")
    # Tasarim uygulamanin tokenlarindan gelmeli.
    if 'href="stil.css"' not in h:
        s.append("kart stil.css yuklemiyor")
    # Yazi tipi AGDAN cekilmemeli: agi kapali bir makinede kart sessizce
    # yedek yazi tipiyle cikiyordu.
    if "fonts.googleapis.com" in h:
        s.append("kart yazi tipini agdan cekiyor (gomulu olmali)")
    if "#ff7a00" in h.lower() or "#0f172a" in h.lower():
        s.append("kartta elle yazilmis renk var (token kullan)")

    # Sayi bicimi: Turkce binlik ayraci nokta.
    if _sayi(35852) != "35.852":
        s.append("binlik ayraci yanlis: %s" % _sayi(35852))

    d = damga_oku()
    if d is None:
        s.append("app/og.png yok ya da damgasiz; `python og_uret.py` calistir")
    elif d != "%d/%d" % (mekan, il):
        s.append("app/og.png eskimis (kartta %s, veride %d/%d); "
                 "`python og_uret.py` calistir" % (d, mekan, il))

    if s:
        for x in s:
            print("  HATA: " + x)
        return False
    print("kontrol gecti: kart veriden besleniyor, damga guncel (%s mekan)"
          % _sayi(mekan))
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.exit(0 if kendini_kontrol_et() else 1)
    uret()
