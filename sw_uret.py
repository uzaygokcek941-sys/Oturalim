#!/usr/bin/env python3
"""app/sw.js icindeki SURUM satirini kabuk dosyalarinin karmasindan uretir.

    python sw_uret.py           # sw.js'i damgalar
    python sw_uret.py kontrol   # damga guncel mi (test.py bunu cagiriyor)
    python sw_uret.py test      # kendi kontrolu

NEDEN
=====
Service worker'in onbellek adi surume bagli. Surum degismezse tarayici
ESKI dosyalari vermeye devam eder ve bunun HICBIR BELIRTISI OLMAZ: sayfa
acilir, calisir, sadece eskidir. Kullanici "guncellendi mi" diye
bakamiyor, gelistirici de gormuyor.

Bu depoda ayni tuzak CSP karmalarinda vardi ve ayni sekilde cozuldu:
deger ELLE YAZILMIYOR, TURETILIYOR; ve test.py her itmede guncel olup
olmadigina bakiyor. Derleme adimi yok, kontrol var.

HANGI DOSYALAR SAYILIYOR
========================
Kullanicinin tarayicisinda calisan ve onbellege giren her sey: HTML, CSS,
JS ve manifest. VERI dosyalari (app/veri/*.json) HARIC -- onlar zaten
"once ag" ile geliyor ve her il degistiginde butun kabugu tazelemek
gereksiz bir indirme dalgasi olurdu.

sw.js'in KENDISI de haric: kendi karmasini iceren bir dosyanin karmasi
sabit noktaya oturmaz.
"""
import glob
import hashlib
import io
import os
import re
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
UYGULAMA = os.path.join(KOK, "app")
SW = os.path.join(UYGULAMA, "sw.js")

SATIR = re.compile(r'^const SURUM = "([^"]*)";', re.M)


def kabuk_dosyalari():
    yollar = []
    for kalip in ("*.html", "*.css", "*.js", "*.webmanifest"):
        yollar += glob.glob(os.path.join(UYGULAMA, kalip))
    # lib/ altindaki kutuphane de kabugun parcasi: surumu degisince
    # onbellek tazelenmeli.
    #
    # CSS DE SART. Ilk yazimda yalniz *.js taraniyordu; Leaflet yerele
    # alininca leaflet.css kabugun DISINDA kaldi ve cevrimdisi acilan
    # haritada uslup hic gelmezdi (kutucuklar ust uste, denetimler
    # bicimsiz). Gorseller de aliniyor: bugun kullanilmiyorlar
    # (circleMarker var, isaretci ikonu yok) ama leaflet.css onlari
    # url() ile cagiriyor ve bir gun bir isaretci eklendiginde kabukta
    # olmamalari sessiz bir bosluk olurdu. Besi toplam 6,5 KB.
    for kalip in ("lib/*.js", "lib/*.css", "lib/images/*"):
        yollar += glob.glob(os.path.join(UYGULAMA, *kalip.split("/")))
    yollar = [y for y in yollar if os.path.basename(y) != "sw.js"]
    return sorted(yollar)


def surum():
    ozet = hashlib.sha256()
    for y in kabuk_dosyalari():
        # Yol da karmaya giriyor: bir dosyanin ADI degisirse (silinip
        # baskasi eklenirse) icerik toplami ayni kalabilirdi.
        ozet.update(os.path.relpath(y, UYGULAMA).encode("utf-8"))
        ozet.update(io.open(y, "rb").read())
    return "v" + ozet.hexdigest()[:12]


def mevcut():
    m = SATIR.search(io.open(SW, encoding="utf-8").read())
    return m.group(1) if m else None


def yaz():
    metin = io.open(SW, encoding="utf-8").read()
    yeni = surum()
    if not SATIR.search(metin):
        sys.exit("sw.js icinde 'const SURUM = \"...\";' satiri yok")
    io.open(SW, "w", encoding="utf-8").write(
        SATIR.sub('const SURUM = "%s";' % yeni, metin, count=1))
    return yeni


def kontrol():
    dosyalar = kabuk_dosyalari()
    if len(dosyalar) < 5:
        # Kontrolun KENDISI bir sey goruyor mu: kaliplar bozulursa liste
        # bosalir, karma sabitlenir ve damga hep "guncel" gorunurdu.
        return ["kabuk dosyasi az bulundu (%d); kalip bozuk mu?" % len(dosyalar)]
    var = mevcut()
    if var is None:
        return ["sw.js icinde SURUM satiri yok"]
    if var != surum():
        return ["sw.js damgasi eskimis (%s != %s); `python sw_uret.py` calistir"
                % (var, surum())]
    return []


def kendini_kontrol_et():
    s = []
    dosyalar = kabuk_dosyalari()
    if any(os.path.basename(y) == "sw.js" for y in dosyalar):
        s.append("sw.js kendi karmasina giriyor; surum sabit noktaya oturmaz")
    if any("/veri/" in y.replace("\\", "/") for y in dosyalar):
        s.append("il verisi kabuga girmis; her il degisiminde onbellek tazelenirdi")
    if len(dosyalar) < 5:
        s.append("kabuk dosyasi az bulundu (%d)" % len(dosyalar))

    # Surum GERCEKTEN icerige bagli mi. Bir dosyayi gecici olarak
    # degistirip karmanin degistigini goruyoruz; degismezse damga
    # ise yaramaz ve bunu baska hicbir sey yakalamaz.
    hedef = os.path.join(UYGULAMA, "stil.css")
    once = surum()
    ham = io.open(hedef, "rb").read()
    try:
        io.open(hedef, "wb").write(ham + b"\n/* gecici */\n")
        if surum() == once:
            s.append("dosya degisti ama surum degismedi")
    finally:
        io.open(hedef, "wb").write(ham)
    if surum() != once:
        s.append("gecici degisiklik geri alinamadi")

    sw = io.open(SW, encoding="utf-8").read()
    # sw.js'te sessizce bozulabilecek uc kural.
    if 'istek.method !== "GET"' not in sw:
        s.append("sw.js GET disi istekleri elemiyor")
    if "skipWaiting()" in sw.split('self.addEventListener("install"')[1].split("});")[0]:
        s.append("install icinde skipWaiting var; acik sayfanin varliklari "
                 "altindan degisebilir")
    if "cevrimdisi.html" not in sw:
        s.append("sw.js cevrimdisi sayfasini bilmiyor")
    if not os.path.exists(os.path.join(UYGULAMA, "cevrimdisi.html")):
        s.append("app/cevrimdisi.html yok")
    return s


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "yaz"
    if komut == "test":
        sorunlar = kendini_kontrol_et()
        for x in sorunlar:
            print("  HATA: " + x)
        if not sorunlar:
            print("kontrol gecti: %d kabuk dosyasi, surum icerige bagli"
                  % len(kabuk_dosyalari()))
        sys.exit(1 if sorunlar else 0)
    if komut == "kontrol":
        sorunlar = kontrol()
        for x in sorunlar:
            print("  HATA: " + x)
        sys.exit(1 if sorunlar else 0)
    print("sw.js damgalandi: %s (%d kabuk dosyasi)"
          % (yaz(), len(kabuk_dosyalari())))
