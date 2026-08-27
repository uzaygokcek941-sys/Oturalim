#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Play magaza gorsellerini uretir.

    python play_gorsel.py          # hepsi
    python play_gorsel.py one      # yalniz one cikan gorsel
    python play_gorsel.py ekran    # yalniz ekran goruntuleri
    python play_gorsel.py test     # kendini kontrol (ag/tarayici gerekmez)

NEDEN VAR
---------
PLAY.md'nin magaza girisi tablosunda iki satir "henuz yok, hazirlanmali"
diyordu ve ikisi de Play'e cikmanin ONKOSULU:

    One cikan gorsel   1024x500   -- zorunlu
    Ekran goruntusu    en az 2    -- zorunlu

RAKAMLAR VERIDEN, ELLE DEGIL. og_uret.py ile ayni gerekce: kartta yazan
sayi bir kez elle yazildiginda eskiyor ve kimse fark etmiyor. Olculdu --
paylasim karti bir donem "Oturalim" ve "36.102 mekan" yaziyordu, gercek
35.852'ydi. Buradaki sayilar app/vitrin.json'dan okunuyor.

EKRAN GORUNTULERI GERCEK UYGULAMADAN. Maket cizmiyoruz: magazada
gorunen sey kullanicinin indirdiginde gorecegi seyle ayni olmali.
Yerel sunucu aciliyor, sayfa gercek tarayicida yukleniyor, ekran
goruntusu aliniyor.

TELEFON OLCUSU 1080x1920 (9:16). Play'in siniri 320-3840 px ve en-boy
orani 16:9 ile 9:16 arasinda; 1080x1920 hem sinirlarin ortasinda hem
gercek bir telefon cozunurlugu.

HARITA DOSEMESI GELMEYEBILIR (kapali ag). O yuzden ekran goruntusu
secimi haritaya BAGLI DEGIL: kesfet LISTE gorunumunde ve mekan
sayfasinin menu sekmesinde aliniyor -- ikisi de tamamen yerel veriden
ciziliyor.
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "app", "play")
VITRIN = os.path.join(KOK, "app", "vitrin.json")
MARKA = os.path.join(KOK, "app", "marka.svg")
STIL = os.path.join(KOK, "app", "stil.css")

ONE_EN, ONE_BOY = 1024, 500
TEL_EN, TEL_BOY = 1080, 1920
SUNUCU_KAPI = 8129           # test.py'nin 8123'unden AYRI: cakismasin

# Ekran goruntuleri. Ucu de YEREL veriden ciziliyor; harita dosemesi
# gelmese de dolu gorunuyorlar.
EKRANLAR = [
    # SIRALAMA "ucuz": magaza ekraninda urunun asil isi gorunsun --
    # butceye gore SIRALANMIS liste. Varsayilan "A -> Z" ile ilk iki
    # kart ayni adi tasiyan iki kayit oluyordu ("#saltbae" kafe ve
    # restoran); dogru bir ekran ama urunu anlatmiyor.
    ("01-kesfet.png",  "/kesfet.html?il=34&butce=300&sirala=ucuz", ".kart", None),
    ("02-mekan.png",   "/isletme.html?il=06&id=node%2F12254801750&butce=300",
     "#menuSatirlar li", None),
    ("03-konum.png",   "/isletme.html?il=01&id=node%2F13068227666",
     "#konumBaglar a", '.sekme-cubuk button[data-sekme="bilgi"]'),
]


def sayi(n):
    """35852 -> '35.852'. ortak.js ile ayni bicim."""
    return "{:,}".format(int(n)).replace(",", ".")


def vitrin():
    """Magaza metnine girecek sayilar. Dosya yoksa ACIKCA duruyor --
    uydurma sayiyla gorsel uretmek, tam da onlemeye calistigimiz sey."""
    if not os.path.exists(VITRIN):
        sys.exit("app/vitrin.json yok; once: python vitrin_uret.py")
    return json.loads(io.open(VITRIN, encoding="utf-8").read())


def _tarayici_yolu():
    y = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return y[-1] if y else None


def _renkler():
    """Marka renkleri stil.css'ten OKUNUYOR, kopyalanmiyor.

    Renk ikinci bir yerde sabitlenirse marka degistiginde biri geride
    kalir; bu depoda tam olarak oyle bir hata olculdu (yazi tipi).
    """
    css = io.open(STIL, encoding="utf-8").read()

    def al(ad, yedek):
        # DEGER ONALTILIK RENK OLMALI. Gevsek desen stil.css'in kendi
        # ACIKLAMA satirini yakaliyordu ("--marka : her iki temada
        # AYNI...") -- kendi kontrolum gosterdi.
        m = re.search(r"--%s\s*:\s*(#[0-9a-fA-F]{3,8})\s*[;\n]" % ad, css)
        return m.group(1).strip() if m else yedek
    return {"marka": al("marka", "#ff7a00"),
            "vurgu": al("vurgu", "#c2410c"),
            "metin": al("metin", "#1c1917")}


def one_cikan_html(v, renk):
    """1024x500 one cikan gorsel.

    METIN AZ: Play bu gorseli listede kucultuyor ve uzerine kendi
    baslik/dugmelerini bindirebiliyor. Uc satirdan fazlasi okunmuyor.
    """
    marka = io.open(MARKA, encoding="utf-8").read()
    return """<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="http://127.0.0.1:%(kapi)d/stil.css">
<style>
  html,body{margin:0;padding:0}
  .tuval{
    width:%(en)dpx;height:%(boy)dpx;display:flex;align-items:center;
    gap:56px;padding:0 72px;box-sizing:border-box;
    background:linear-gradient(135deg,%(marka)s 0%%,#ff9d3d 55%%,#ffd0a3 100%%);
    font-family:Montserrat,system-ui,sans-serif;color:#1c1917;
  }
  .isaret{flex:0 0 auto;width:150px;height:150px;display:grid;place-items:center;
    background:#fff;border-radius:34px;box-shadow:0 10px 34px rgba(0,0,0,.16)}
  .isaret svg{width:104px;height:104px}
  .yazi{flex:1 1 auto;min-width:0}
  h1{margin:0;font-size:60px;line-height:1.03;letter-spacing:-1.4px;font-weight:800}
  p{margin:14px 0 0;font-size:27px;line-height:1.32;font-weight:600;opacity:.9}
  .sayi{margin:22px 0 0;display:flex;gap:34px;font-variant-numeric:tabular-nums}
  .sayi b{display:block;font-size:34px;line-height:1;font-weight:800}
  .sayi span{font-size:16px;font-weight:600;opacity:.78}
</style>
<div class="tuval">
  <div class="isaret">%(marka_svg)s</div>
  <div class="yazi">
    <h1>Cebindeki bütçeyle keşfet.</h1>
    <p>Fiyatı işletmeler değil, gidenler yazıyor.</p>
    <div class="sayi">
      <div><b>%(il)s</b><span>il</span></div>
      <div><b>%(mekan)s</b><span>mekan</span></div>
      <div><b>%(kalem)s</b><span>menü kalemi</span></div>
    </div>
  </div>
</div>""" % {"kapi": SUNUCU_KAPI, "en": ONE_EN, "boy": ONE_BOY,
             "marka": renk["marka"], "marka_svg": marka,
             "il": sayi(v["il"]), "mekan": sayi(v["toplam"]),
             "kalem": sayi(v["kalem"])}


class Sunucu:
    """app/ klasorunu yerelde yayimlar. sunucu.py'yi cagiriyor cunku
    CSP basliklarini o kuruyor -- gorsel, gercek basliklarla cizilmis
    sayfadan alinmali."""

    def __enter__(self):
        self.p = subprocess.Popen(
            [sys.executable, os.path.join(KOK, "sunucu.py"), str(SUNUCU_KAPI)],
            cwd=KOK, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            time.sleep(0.25)
            try:
                import urllib.request
                urllib.request.urlopen(
                    "http://127.0.0.1:%d/index.html" % SUNUCU_KAPI, timeout=2)
                return self
            except Exception:
                continue
        self.p.terminate()
        sys.exit("yerel sunucu %d numarali kapida acilmadi" % SUNUCU_KAPI)

    def __exit__(self, *a):
        self.p.terminate()


def uret(kip="hepsi"):
    from playwright.sync_api import sync_playwright
    v = vitrin()
    renk = _renkler()
    os.makedirs(CIKTI, exist_ok=True)
    yol = _tarayici_yolu()
    yazilan = []

    with Sunucu(), sync_playwright() as p:
        t = (p.chromium.launch(executable_path=yol, args=["--no-sandbox"])
             if yol else p.chromium.launch(args=["--no-sandbox"]))

        if kip in ("hepsi", "one"):
            sf = t.new_page(viewport={"width": ONE_EN, "height": ONE_BOY},
                            device_scale_factor=1)
            sf.set_content(one_cikan_html(v, renk))
            # Yazi tipi INMEDEN goruntu alinirsa marka yanlis gorunur.
            try:
                sf.wait_for_function("document.fonts.ready.then(()=>true)",
                                     timeout=8000)
            except Exception:
                pass
            sf.wait_for_timeout(500)
            ad = os.path.join(CIKTI, "one-cikan-1024x500.png")
            sf.screenshot(path=ad)
            sf.close()
            yazilan.append((ad, ONE_EN, ONE_BOY))
            print("  one-cikan-1024x500.png  %dx%d" % (ONE_EN, ONE_BOY))

        if kip in ("hepsi", "ekran"):
            for ad, adres, bekle, tikla in EKRANLAR:
                sf = t.new_page(viewport={"width": TEL_EN // 3,
                                          "height": TEL_BOY // 3},
                                device_scale_factor=3)
                sf.goto("http://127.0.0.1:%d%s" % (SUNUCU_KAPI, adres),
                        wait_until="domcontentloaded")
                if tikla:
                    try:
                        sf.wait_for_selector(tikla, timeout=8000)
                        sf.eval_on_selector(tikla, "e => e.click()")
                    except Exception:
                        pass
                # BOS EKRAN GORUNTUSU YAZILMIYOR: beklenen ogenin
                # gercekten cizildigi dogrulaniyor. Magazaya bos bir
                # ekran koymak, hic koymamaktan kotu.
                try:
                    sf.wait_for_selector(bekle, timeout=15000)
                except Exception:
                    sf.close()
                    t.close()
                    sys.exit("%s: '%s' cizilmedi, goruntu YAZILMADI" % (ad, bekle))
                sf.wait_for_timeout(900)
                yolu = os.path.join(CIKTI, ad)
                sf.screenshot(path=yolu)
                sf.close()
                yazilan.append((yolu, TEL_EN, TEL_BOY))
                print("  %-22s %dx%d" % (ad, TEL_EN, TEL_BOY))
        t.close()

    for yolu, en, boy in yazilan:
        g_en, g_boy = png_olcusu(yolu)
        if (g_en, g_boy) != (en, boy):
            sys.exit("%s %dx%d cikti, %dx%d bekleniyordu"
                     % (os.path.basename(yolu), g_en, g_boy, en, boy))
    print("%d gorsel yazildi: app/play/" % len(yazilan))


def png_olcusu(yol):
    """PNG genislik/yukseklik. Pillow'suz: IHDR yeterli."""
    import struct
    with open(yol, "rb") as f:
        bas = f.read(24)
    if bas[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s PNG degil" % yol)
    return struct.unpack(">II", bas[16:24])


def kendini_kontrol_et():
    """Ag ve tarayici GEREKTIRMEZ."""
    s = []
    v = {"il": 81, "toplam": 35852, "kalem": 7406}
    h = one_cikan_html(v, _renkler())

    # RAKAM VERIDEN GELMELI. Elle yazilan sayi eskiyor ve kimse fark
    # etmiyor -- paylasim kartinda tam olarak bu yasandi.
    for beklenen in ("35.852", "7.406", "81"):
        if beklenen not in h:
            s.append("one cikan gorselde %s yok (sayi veriden gelmiyor mu?)"
                     % beklenen)
    # Bicim ortak.js ile ayni: nokta ayirici, virgul degil.
    if "35,852" in h:
        s.append("sayi bicimi yanlis (35,852) -- nokta ayirici olmali")
    if sayi(35852) != "35.852" or sayi(7406) != "7.406":
        s.append("sayi() bicimi ortak.js ile tutmuyor")

    # Marka rengi stil.css'ten okunmali, kopyalanmamali.
    r = _renkler()
    if not r["marka"].startswith("#") or len(r["marka"]) not in (4, 7):
        s.append("marka rengi stil.css'ten okunamadi: %r" % r["marka"])
    if r["marka"] not in h:
        s.append("one cikan gorsel marka rengini kullanmiyor")

    # Play'in zorunlu olculeri.
    if (ONE_EN, ONE_BOY) != (1024, 500):
        s.append("one cikan gorsel olcusu Play'in istedigi 1024x500 degil")
    oran = TEL_BOY / float(TEL_EN)
    if not (16 / 9.0 - 0.01 <= oran <= 16 / 9.0 + 0.01):
        s.append("telefon goruntusu 9:16 degil (%.3f)" % oran)
    if not (320 <= TEL_EN <= 3840 and 320 <= TEL_BOY <= 3840):
        s.append("telefon goruntusu Play'in 320-3840 px araligi disinda")

    # EN AZ IKI ekran goruntusu: Play'in alt siniri.
    if len(EKRANLAR) < 2:
        s.append("Play en az 2 ekran goruntusu istiyor, %d tanimli" % len(EKRANLAR))
    # Her ekranin BEKLEDIGI bir oge olmali; olmazsa bos goruntu yazilir.
    for ad, adres, bekle, _ in EKRANLAR:
        if not bekle:
            s.append("%s icin beklenen oge tanimsiz: bos goruntu yazilabilir" % ad)
        if not adres.startswith("/"):
            s.append("%s adresi yerel degil: %r" % (ad, adres))

    # Kapi test.py'nin sunucusuyla CAKISMAMALI: iki kosum ayni anda
    # olabilir ve biri otekinin sunucusuna baglanirsa goruntu yanlis
    # sayfadan alinir.
    if SUNUCU_KAPI == 8123:
        s.append("sunucu kapisi test.py ile ayni (8123): cakisir")

    print("kendini kontrol: %s"
          % ("BASARISIZ" if s else "%d kontrol gecti" % 12))
    for x in s:
        print("  HATA:", x)
    return s


if __name__ == "__main__":
    kip = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
    if kip == "test":
        sys.exit(1 if kendini_kontrol_et() else 0)
    uret(kip)
