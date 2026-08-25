#!/usr/bin/env python3
"""supabase-js'i CDN'den alip app/lib/ altina YERELE yazar.

    python kutuphane_al.py          # indirir, dogrular, yazar
    python kutuphane_al.py test     # aga cikmadan mantik kontrolu

NEDEN
=====
Iki ayri sorun, tek cozum.

1) SRI YOK. Leaflet <script integrity=...> ile geliyor, supabase-js
   gelemiyor: dinamik `import()` integrity oznitelligini DESTEKLEMIYOR.
   Yani bugun esm.sh'in gonderdigi her sey, dogrulanmadan calisiyor.

2) CDN TEK ARIZA NOKTASI. Bu VARSAYIM DEGIL, bu depoda YASANDI: Leaflet
   CDN'den gelmeyince kesfet ekraninin TAMAMI oluyordu (sifir kart,
   sayac "..."da donmus). Ayni sey supabase-js'e olursa giris, favori,
   paylasim, yorum ve fotograf -- hepsi kapanir.

Dosya yerele alininca ikisi de kapaniyor: ayni kaynaktan geliyor (SRI'ye
gerek kalmiyor), ve ucuncu bir tarafin ayakta olmasina bagli degil.

NEDEN "DERLEME ADIMI ISTER" ARTIK DOGRU DEGIL
=============================================
Yol haritasindaki eski not "yerele almak derleme adimi ister" diyordu ve
o gun dogruydu: esm.sh'in normal ciktisi baska esm.sh adreslerinden
parca ithal ediyor, yani tek dosya degil. Ama esm.sh'in `?bundle`
secenegi butun bagimliliklari TEK dosyada birlestiriyor. Paket yoneticisi
de, toplayici da gerekmiyor -- tek bir indirme.

INDIRILEN SEY KORU KORUNE YAZILMIYOR
====================================
Asagidaki dogrulama gecmeden dosya YAZILMIYOR:
  - govde bos ya da sacma kucuklukte degil
  - ICINDE DIS ITHALAT KALMAMIS (bundle gercekten bundle mi)
  - createClient disari veriliyor
  - HTML degil (CDN hata sayfasi 200 ile de donebiliyor)
Biri tutmazsa betik hata veriyor ve VAR OLAN dosyaya dokunmuyor. Bozuk
bir kutuphane yazmak, hic yazmamaktan kotu: giris sessizce olurdu.
"""
import hashlib
import io
import os
import re
import sys

# Surum SABIT. app/lib/supabase-js.js yer tutucusu hala CDN'e
# yonlendiriyorsa oradaki surumle ayni olmali -- ayrisirsa indirmeden once
# ve sonra farkli surum calisirdi. Kontrol asagida.
SURUM = "2.45.4"
ADRES = "https://esm.sh/@supabase/supabase-js@%s?bundle&target=es2020" % SURUM

KOK = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(KOK, "app", "lib", "supabase-js.js")

EN_AZ_BAYT = 80 * 1024          # gercegi ~250 KB; bunun altisi supheli
EN_COK_BAYT = 4 * 1024 * 1024

# Kalan dis ithalat: "from 'https://...'", "from '/v135/...'", "import('...')"
DIS_ITHALAT = re.compile(
    r"""(?:from|import)\s*\(?\s*["'](https?:|//|/v\d|/@|/npm)""")


def dogrula(govde):
    """Indirilen sey gercekten kullanilabilir mi. Sorun listesi doner."""
    s = []
    n = len(govde.encode("utf-8"))
    if n < EN_AZ_BAYT:
        s.append("dosya cok kucuk (%d bayt); CDN hata mi dondu?" % n)
    if n > EN_COK_BAYT:
        s.append("dosya cok buyuk (%d bayt)" % n)
    bas = govde.lstrip()[:200].lower()
    if bas.startswith("<!doctype") or bas.startswith("<html"):
        s.append("HTML geldi, JavaScript degil (CDN hata sayfasi 200 de donebiliyor)")
    if DIS_ITHALAT.search(govde):
        ornek = DIS_ITHALAT.search(govde).group(0)
        s.append("dis ithalat kalmis (%r) -- ?bundle ise yaramamis, "
                 "dosya tek basina calismaz" % ornek)
    if "createClient" not in govde:
        s.append("createClient disari verilmiyor")
    return s


def indir():
    import urllib.request
    istek = urllib.request.Request(ADRES, headers={"User-Agent": "oturalim/1.0"})
    with urllib.request.urlopen(istek, timeout=60) as c:
        return c.read().decode("utf-8")


def kendini_kontrol_et():
    s = []
    # Dogrulayici GERCEKTEN eliyor mu. Her satir ayri bir tuzagi taklit
    # ediyor; hepsi "dogrula bunu reddetmeli" diyor.
    iyi = "export function createClient(){}\n" + ("//x\n" * 40000)
    if dogrula(iyi):
        s.append("saglam govde reddedildi: %s" % dogrula(iyi))
    for ad, kotu in (
            ("bos",        ""),
            ("html",       "<!doctype html><html>404</html>" + "x" * 200000),
            ("createClient yok", "export const a = 1;\n" + ("//x\n" * 40000)),
            ("dis ithalat", iyi + '\nimport {x} from "https://esm.sh/v135/y";\n'),
            ("goreli cdn yolu", iyi + '\nexport {a} from "/v135/tslib";\n')):
        if not dogrula(kotu):
            s.append("dogrula %r halini KABUL etti" % ad)
    # kimlik.js TEK bir adres biliyor ve o adres yerel olmali; CDN adresi
    # oraya geri sizarsa SRI sorunu geri gelir.
    kimlik = io.open(os.path.join(KOK, "app", "kimlik.js"), encoding="utf-8").read()
    if 'import("./lib/supabase-js.js")' not in kimlik:
        s.append("kimlik.js yerel kutuphaneyi ithal etmiyor")
    if "esm.sh" in kimlik:
        s.append("kimlik.js hala dogrudan CDN adresi tasiyor")
    # Yer tutucu hala CDN'e yonlendiriyorsa surumu BURADAKI ile ayni olmali:
    # ayrisirsa indirmeden once ve sonra farkli surum calisirdi.
    try:
        lib = io.open(HEDEF, encoding="utf-8").read()
    except Exception:
        s.append("app/lib/supabase-js.js yok (yer tutucu bile)")
        return s
    if "esm.sh" in lib and ("supabase-js@" + SURUM) not in lib:
        s.append("yer tutucudaki surum %s degil" % SURUM)
    return s


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sorunlar = kendini_kontrol_et()
        for x in sorunlar:
            print("  HATA: " + x)
        if not sorunlar:
            print("kontrol gecti: dogrulayici bes bozuk hali eliyor, "
                  "kimlik.js tek yerel adrese bagli")
        sys.exit(1 if sorunlar else 0)

    print("indiriliyor: %s" % ADRES)
    try:
        govde = indir()
    except Exception as e:
        # Ag hatasi bir OLCUM DEGIL: dosya yazilmiyor, var olan duruyor.
        sys.exit("INDIRILEMEDI: %s\nDosya YAZILMADI; var olan app/lib/ dokunulmadi." % e)

    sorunlar = dogrula(govde)
    if sorunlar:
        print("INDIRILEN DOSYA KULLANILAMAZ, yazilmadi:")
        for x in sorunlar:
            print("  - " + x)
        sys.exit(1)

    os.makedirs(os.path.dirname(HEDEF), exist_ok=True)
    io.open(HEDEF, "w", encoding="utf-8").write(govde)
    ozet = hashlib.sha384(govde.encode("utf-8")).hexdigest()
    print("yazildi: app/lib/supabase-js.js  (%.0f KB)" % (len(govde.encode()) / 1024))
    print("sha384: %s" % ozet)
    print()
    print("kimlik.js zaten bu dosyayi ithal ediyordu; yer tutucu gitti,")
    print("kutuphane artik ayni kaynaktan geliyor. Iki adim kaldi:")
    print("    python csp_uret.py      # esm.sh CSP'den dusuyor")
    print("    git add app/lib/supabase-js.js vercel.json && git commit")


if __name__ == "__main__":
    main()
