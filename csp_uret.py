#!/usr/bin/env python3
"""vercel.json'daki Content-Security-Policy basligini uretir.

    python csp_uret.py          # vercel.json'u gunceller
    python csp_uret.py kontrol  # yalniz denetler, yazmaz (test.py bunu cagiriyor)

NEDEN BIR BETIK, NEDEN ELLE YAZILMIS BIR BASLIK DEGIL
=====================================================
script-src satir ici bloklari KARMA ile geciriyor (sha256). Karma, blogun
metnine bagli: bir <script> icinde tek bosluk degistiginde karma degisiyor
ve tarayici o blogu CALISTIRMIYOR. Elle tutulan bir liste, ilk duzenlemede
sessizce eskir ve sonucu yayindaki sayfanin kirilmasi olur.

Bu yuzden karmalar UYGULANMIYOR, TURETILIYOR; ve test.py her itmede
`csp_uret.py kontrol` cagirip vercel.json'un guncel olup olmadigina
bakiyor. Yani eskime derleme adimiyla degil, KONTROLLE onleniyor -- bu
depoda derleme adimi yok.

NEDEN 'unsafe-inline' YOK
=========================
Karma varken tarayici 'unsafe-inline'i zaten yok sayiyor. Ikisini birden
yazmak, CSP'yi yazmamis gibi olmak demekti: bu uygulamada satir ici script
enjeksiyonuna karsi tek gercek savunma karma.

style-src'de 'unsafe-inline' VAR ve kalmali: kartlara satir ici
`style="--uzak:0.42"` yaziliyor ve stil OZNITELIGI karma ile gecmiyor
('unsafe-hashes' gerekirdi, o da ayni kapiyi baska adla acardi). Satir ici
stilin tasidigi risk, satir ici scriptinkinin yaninda kucuk.

NEDEN SUPABASE ADRESI JOKER
===========================
app/yapilandirma.js gitignore'da: her kurulumun kendi Supabase projesi var
ve depoda sabit bir adres yok. `https://*.supabase.co` bu yuzden --
depodaki CSP baska bir Supabase projesiyle kuran kisinin girisini
sessizce kirmasin diye. (Kendi alan adinda barinan bir Supabase varsa
asagidaki EK_KAYNAK'a eklenmeli.)
"""
import base64
import hashlib
import io
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
UYGULAMA = os.path.join(KOK, "app")
AYAR = os.path.join(KOK, "vercel.json")

# Satir ici <script> bloklari. src'li olanlar DISARIDA: onlar zaten
# script-src'deki kaynak listesinden geciyor.
BLOK = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)

# Calisma aninda gercekten kullanilan dis kaynaklar. Her biri kodda
# aranabilir olsun diye yaninda nerede kullanildigi yazili.
KAYNAK = {
    "unpkg":    "https://unpkg.com",                  # Leaflet -- yerele alininca dusuyor
    "esm":      "https://esm.sh",                     # supabase-js (kimlik.js)
    "fontcss":  "https://fonts.googleapis.com",       # <link rel=stylesheet>
    "font":     "https://fonts.gstatic.com",          # woff2 dosyalari
    "supabase": "https://*.supabase.co",              # REST + Storage
    "supaws":   "wss://*.supabase.co",                # supabase-js gercek zamanli
    "dosem":    "https://*.basemaps.cartocdn.com",    # harita dosemesi (kesfet.js)
    "commons":  "https://upload.wikimedia.org",       # serbest lisansli fotograf
}
# Kendi alan adinda Supabase barindiriyorsan buraya ekle.
EK_KAYNAK = []

KUTUPHANE = os.path.join(KOK, "app", "lib", "supabase-js.js")
LEAFLET = os.path.join(KOK, "app", "lib", "leaflet.js")


def kutuphane_yerel_mi():
    """supabase-js gercekten yerelde mi, yoksa hala CDN'e yonlendiren yer
    tutucu mu (kutuphane_al.py). CSP bunu biliyor: yer tutucu oldugu surece
    esm.sh script-src ve connect-src'de KALMAK ZORUNDA -- cikarsaydik giris
    sessizce kirilirdi. Gercegi indirilince CSP kendiliginden daraliyor."""
    try:
        govde = io.open(KUTUPHANE, encoding="utf-8").read()
    except Exception:
        return False
    return "esm.sh" not in govde


def satir_ici_karmalar():
    """app/*.html icindeki satir ici script bloklarinin sha256 karmalari."""
    karmalar = []
    for ad in sorted(os.listdir(UYGULAMA)):
        if not ad.endswith(".html"):
            continue
        metin = io.open(os.path.join(UYGULAMA, ad), encoding="utf-8").read()
        for govde in BLOK.findall(metin):
            # Tarayici blogun BAYT BAYT icerigini karmaliyor: kirpma yok.
            ozet = hashlib.sha256(govde.encode("utf-8")).digest()
            karmalar.append("'sha256-" + base64.b64encode(ozet).decode("ascii") + "'")
    # Ayni blok birden cok sayfada (tema on yukleyicisi gibi): tekille,
    # sirala -- baslik kosumdan kosuma AYNI cikmali, yoksa "kontrol"
    # adimi dosya degismeden de hata verirdi.
    return sorted(set(karmalar))


def cdn_esm():
    return [] if kutuphane_yerel_mi() else [KAYNAK["esm"]]


def leaflet_yerel_mi():
    """Leaflet app/lib/ altinda gercekten duruyor mu (kutuphane_al.py).

    supabase-js'teki kuralin aynisi: dosya yoksa unpkg.com CSP'de KALMAK
    ZORUNDA, yoksa harita sessizce olurdu. Dosya varsa CSP kendiliginden
    daraliyor -- unpkg script-src, style-src ve img-src'nin ucunden birden
    dusuyor."""
    try:
        return os.path.getsize(LEAFLET) > 100 * 1024
    except Exception:
        return False


def cdn_unpkg():
    return [] if leaflet_yerel_mi() else [KAYNAK["unpkg"]]


def csp():
    k = KAYNAK
    ek = " ".join(EK_KAYNAK)
    yonergeler = [
        ("default-src", "'self'"),
        # base-uri: sarkan isaretlemeyle <base> enjekte edip butun goreli
        # adresleri baskasinin sunucusuna cevirmeyi kapatiyor.
        ("base-uri", "'self'"),
        ("object-src", "'none'"),
        ("frame-ancestors", "'self'"),
        # form-action: veri sizdirmanin en ucuz yolu, enjekte edilmis bir
        # <form>'u disari gondermek.
        ("form-action", "'self'"),
        ("script-src", " ".join(["'self'"] + cdn_unpkg() + cdn_esm() +
                                satir_ici_karmalar())),
        ("style-src", " ".join(["'self'", "'unsafe-inline'", k["fontcss"]] +
                               cdn_unpkg())),
        ("font-src", " ".join(["'self'", k["font"]])),
        # blob: -- resimHazirla() tuvalden uretilen onizlemeyi boyle veriyor.
        # unpkg YEREL LEAFLET'TE DUSUYOR: leaflet.css ikonlarina goreli
        # yoldan basvuruyor (marker-icon.png, layers.png) ve o yol artik
        # 'self'. Kutuphane yerele alinmadiysa liste eski haline donuyor,
        # yoksa bir katman denetimi eklendigi gun istek sessizce
        # engellenirdi.
        ("img-src", " ".join(["'self'", "data:", "blob:", k["supabase"],
                              k["commons"], k["dosem"]] + cdn_unpkg())),
        ("connect-src", " ".join(["'self'", k["supabase"], k["supaws"]] + cdn_esm())),
    ]
    metin = "; ".join(a + " " + b for a, b in yonergeler)
    return (metin + " " + ek).strip() if ek else metin


def ayari_oku():
    return json.loads(io.open(AYAR, encoding="utf-8").read())


def mevcut(d):
    for grup in d.get("headers", []):
        if grup.get("source") == "/(.*)":
            for h in grup.get("headers", []):
                if h.get("key") == "Content-Security-Policy":
                    return h.get("value")
    return None


# ---------------------------------------------------------------
# GIZLILIK TABLOSU: CSP'DEN URETILIYOR, ELLE YAZILMIYOR
#
# NEDEN: gizlilik sayfasi kullaniciya "tarayicin sunlarla konusuyor"
# diyor, CSP ise tarayicinin nereye gidebilecegini soyleyen TEK YETKILI
# yer. Ikisi elle tutuldugu surece ayrisirlar ve bu SESSIZCE olur.
#
# BU TAM OLARAK YASANDI, iki kez:
#   1) Sayfa unpkg'yi listeliyordu ama Leaflet yerele alinmisti; ayrica
#      Wikimedia Commons ve esm.sh cagriliyordu ama YAZMIYORDU.
#   2) supabase-js yerele alinip esm.sh CSP'den kendiliginden dusunce
#      tablo geride kaldi ve kontrol GitHub kosucusunda patladi.
#
# Ikincisinde kontrol dogru davrandi ama is durdu. Kural yerine
# URETICI koymak dogru cozum: "ayni kural tek yerde dursun".
SAGLAYICI = {
    "https://unpkg.com":               ("unpkg", "Leaflet harita kütüphanesi"),
    "https://esm.sh":                  ("esm.sh", "Supabase istemci kütüphanesi"),
    "https://fonts.googleapis.com":    ("Google Fonts", "Yazı tipleri"),
    "https://fonts.gstatic.com":       ("Google Fonts", "Yazı tipleri"),
    "https://*.basemaps.cartocdn.com": ("OpenStreetMap / CARTO", "Harita döşemeleri"),
    "https://upload.wikimedia.org":    ("Wikimedia Commons",
                                        "Serbest lisanslı mekan fotoğrafları — "
                                        "yalnızca o fotoğrafın olduğu sayfada"),
    "https://*.supabase.co":           ("Supabase",
                                        "Hesap, oturum, favori ve fiyat paylaşımı "
                                        "verisi — yalnızca hesap açarsan"),
    "wss://*.supabase.co":             ("Supabase",
                                        "Hesap, oturum, favori ve fiyat paylaşımı "
                                        "verisi — yalnızca hesap açarsan"),
}
# CSP'de GECMEYEN ama listede olmasi gereken: siteyi barindiran taraf
# 'self' oldugu icin CSP'de gorunmuyor, ama kullanici acisindan bir
# ucuncu taraf ve dosyalari onun sunucusundan geliyor.
HER_ZAMAN = [("Vercel", "Sitenin barındırılması")]

GIZLILIK = os.path.join(KOK, "app", "gizlilik.html")
TBODY = re.compile(r"(<thead><tr><th>Sağlayıcı</th>.*?<tbody>)(.*?)(</tbody>)", re.S)


def gizlilik_satirlari(csp_metni=None):
    """CSP'de GERCEKTEN gecen saglayicilarin tablo satirlari."""
    c = csp_metni if csp_metni is not None else csp()
    gorulen, satirlar = set(), []
    for konak, (ad, ne) in SAGLAYICI.items():
        if konak in c and ad not in gorulen:
            gorulen.add(ad)
            satirlar.append((ad, ne))
    satirlar.sort()
    return satirlar + HER_ZAMAN


def gizlilik_yaz(csp_metni=None):
    """Tabloyu CSP'den yeniden yazar. (degisti_mi, satir_sayisi) doner."""
    ham = io.open(GIZLILIK, encoding="utf-8").read()
    m = TBODY.search(ham)
    if not m:
        sys.exit("gizlilik.html'de saglayici tablosu bulunamadi")
    govde = "\n" + "".join(
        "            <tr><td>%s</td><td>%s</td></tr>\n" % (ad, ne)
        for ad, ne in gizlilik_satirlari(csp_metni)) + "          "
    yeni = ham[:m.start(2)] + govde + ham[m.end(2):]
    if yeni == ham:
        return False, len(gizlilik_satirlari(csp_metni))
    io.open(GIZLILIK, "w", encoding="utf-8").write(yeni)
    return True, len(gizlilik_satirlari(csp_metni))


def yaz():
    d = ayari_oku()
    hedef = None
    for grup in d.get("headers", []):
        if grup.get("source") == "/(.*)":
            hedef = grup
    if hedef is None:
        sys.exit("vercel.json'da '/(.*)' basligi yok; once o eklenmeli")
    yeni = csp()
    for h in hedef["headers"]:
        if h.get("key") == "Content-Security-Policy":
            h["value"] = yeni
            break
    else:
        hedef["headers"].append({"key": "Content-Security-Policy", "value": yeni})
    io.open(AYAR, "w", encoding="utf-8").write(
        json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    # TABLO DA AYNI KOSUMDA YAZILIYOR. Ayri bir komut olsaydi biri
    # calistirilip oteki unutulurdu -- iki listenin ayrismasi tam da
    # boyle oluyordu.
    degisti, n = gizlilik_yaz(yeni)
    if degisti:
        print("gizlilik.html saglayici tablosu yenilendi (%d satir)" % n)
    return yeni


def gizlilik_kontrol(csp_metni=None):
    """Tablo, URETICININ bugun yazacagi seyle AYNI mi.

    "CSP'de gecen her ad tabloda var mi" kontrolu ayri ve daha gevsek
    (test.py'de); bu kontrol daha siki: uretici hic kosmasa bile tablo
    dogru gorunebiliyordu ve o hal sabotajla goruldu -- yaz() icindeki
    cagriyi silmek hicbir seyi patlatmiyordu.

    Burada tablo URETILENLE karsilastiriliyor, yani uretici durursa
    veya kaynak listesi degisirse fark hemen cikiyor.
    """
    beklenen = gizlilik_satirlari(csp_metni)
    ham = io.open(GIZLILIK, encoding="utf-8").read()
    m = TBODY.search(ham)
    if not m:
        return ["gizlilik.html: saglayici tablosu bulunamadi"]
    var = [(a.strip(), b.strip()) for a, b in
           re.findall(r"<tr><td>(.*?)</td><td>(.*?)</td></tr>", m.group(2), re.S)]
    if var != beklenen:
        return ["gizlilik.html saglayici tablosu eskimis "
                "(tabloda %d satir, uretici %d satir yazardi); "
                "`python csp_uret.py` calistir" % (len(var), len(beklenen))]
    return []


def kontrol():
    """Dosya guncel mi. test.py ve CI bunu cagiriyor."""
    karmalar = satir_ici_karmalar()
    if not karmalar:
        # Kontrolun KENDISI bir sey goruyor mu: duzenli ifade bozulursa
        # karma listesi bosalir ve "guncel" diye gecerdi.
        return ["satir ici script hic bulunamadi (BLOK duzenli ifadesi bozuk mu?)"]
    var = mevcut(ayari_oku())
    if var is None:
        return ["vercel.json'da Content-Security-Policy yok; `python csp_uret.py` calistir"]
    if var != csp():
        eksik = [h for h in karmalar if h not in var]
        return ["vercel.json'daki CSP eskimis (%d karmadan %d'i eksik); "
                "`python csp_uret.py` calistir" % (len(karmalar), len(eksik))]
    # TABLO DA AYNI KONTROLDE. Ayri bir kontrol olsaydi biri kosup
    # oteki unutulurdu -- zaten sorunun kaynagi buydu.
    return gizlilik_kontrol(var)


def kendini_kontrol_et():
    sorunlar = []
    # URETICI yaz()'A BAGLI MI. gizlilik_kontrol() tablonun GUNCEL
    # oldugunu soyluyor; bu satir uretilebilir oldugunu soyluyor.
    # Ikisi ayri sey ve ikincisi olmadan sinsi bir tuzak kaliyor:
    # cagri silinirse tablo bugun dogru gorunur, ama CSP degistigi gun
    # kontrol "python csp_uret.py calistir" der ve o komut HICBIR SEYI
    # DUZELTMEZ -- kullanici dongude kalir. Sabotajla goruldu.
    kaynak = io.open(__file__, encoding="utf-8").read()
    govde = kaynak.split("def yaz():")[1].split("\ndef ")[0]
    if "gizlilik_yaz(" not in govde:
        sorunlar.append("yaz() gizlilik tablosunu URETMIYOR: CSP degisince "
                        "tablo geride kalir ve `python csp_uret.py` onu "
                        "duzeltmez")
    # Uretilen satirlarin ikisi de dolu olmali; bos bir aciklama
    # kullaniciya hicbir sey soylemez.
    for ad, ne in gizlilik_satirlari():
        if not ad.strip() or len(ne.strip()) < 8:
            sorunlar.append("gizlilik satiri eksik: %r / %r" % (ad, ne))
    k = satir_ici_karmalar()
    if len(k) < 5:
        sorunlar.append("satir ici script karmasi az bulundu (%d)" % len(k))
    # src'li script karmalanmamali: karmasi gereksiz ve YANLIS olurdu
    # (etiket govdesi bos, yani hepsi ayni karmayi verirdi).
    ornek = '<script src="ortak.js"></script><script>var a=1;</script>'
    if len(BLOK.findall(ornek)) != 1:
        sorunlar.append("src'li script blogu da karmalaniyor")
    metin = csp()
    if "'unsafe-inline'" in metin.split("script-src")[1].split(";")[0]:
        sorunlar.append("script-src'de 'unsafe-inline' var (karmalari etkisiz kilar)")
    if "'unsafe-inline'" not in metin.split("style-src")[1].split(";")[0]:
        sorunlar.append("style-src'de 'unsafe-inline' yok (satir ici stil kirilir)")
    for gerekli in ("object-src 'none'", "base-uri 'self'", "form-action 'self'",
                    "wss://*.supabase.co"):
        if gerekli not in metin:
            sorunlar.append("CSP'de eksik: " + gerekli)
    return sorunlar


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "yaz"
    if komut == "test":
        s = kendini_kontrol_et()
        for x in s:
            print("  HATA: " + x)
        if not s:
            print("kontrol gecti: %d satir ici karma, yonergeler yerinde"
                  % len(satir_ici_karmalar()))
        sys.exit(1 if s else 0)
    if komut == "kontrol":
        s = kontrol()
        for x in s:
            print("  HATA: " + x)
        sys.exit(1 if s else 0)
    yeni = yaz()
    print("vercel.json guncellendi (%d satir ici karma)" % len(satir_ici_karmalar()))
    print(yeni[:160] + ("..." if len(yeni) > 160 else ""))
