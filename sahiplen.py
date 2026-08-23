# -*- coding: utf-8 -*-
"""Sahiplenme hedef motoru.

Uygulamadaki her isletme icin "bizde ne EKSIK" hesaplar ve bunu isletmeye
gosterilecek somut bir cumleye cevirir. Cikti: sahiplenme_hedef.csv

Mantik: eksik veri hem BIZIM zayifligimiz (oneremiyoruz) hem de ONUN kaybi
(musteri goremiyor). Ayni cumle iki tarafi da tarif ediyor -- satis dili degil,
olculen gercek.

UYARI: OSM'de "web yok" gorunmesi sitesi olmadigi anlamina GELMEZ. Mesaj
atmadan once elle dogrula (CLAUDE.md, lead disiplini).
"""
import csv, glob, io, json, math, os, collections

VERI = "app/veri"
CIKTI = "sahiplenme_hedef.csv"

# Kullaniciya en cok lazim olan alan en agir. Sirasi olculmedi, gerekce:
# "acik mi" sorusu her oneride soruluyor, menu yalniz fiyat filtresinde.
AGIRLIK = {"saat": 40, "tel": 25, "menu": 20, "adres": 10, "web": 5}

EKSIK_CUMLE = {
    "saat":  "acilis-kapanis saatiniz yazmiyor, sistem 'acik mi' diye soruldugunda sizi eleyip geciyor",
    "tel":   "telefonunuz yok, sayfayi goren kisi sizi arayamiyor",
    "menu":  "fiyat bilgisi yok, 'hesapli yer' arayan kullaniciya cikmiyorsunuz",
    "adres": "acik adres yok, yalniz haritada nokta olarak gorunuyorsunuz",
    "web":   "site veya sosyal medya bagi yok",
}

# Menu/fiyat sayfasi bu turler icin anlamli; muze icin degil.
YEME_ICME = {"Restoran", "Kafe", "Fast food", "Bar", "Pub", "Dondurma", "Pastane"}


# Turkce casefold tuzagi: "Istanbul".casefold() -> "i̇stanbul" (i + birlesen
# nokta), "istanbul" onun alt dizisi DEGIL. Klavyeden "Istanbul" yazan kullanici
# hicbir sey bulamiyordu. Karsilastirma icin harfleri ASCII'ye indiriyoruz --
# yalniz eslestirmede, gosterilen ad hep orijinal kaliyor.
_SADE = str.maketrans("çğıİöşüÇĞÖŞÜ", "cgiiosucgosu")


def sade(x):
    return (x or "").translate(_SADE).lower()


def ilce_haritasi():
    """osm_id -> ilce. Ilce bilgisi app/veri'de yok, ham CSV'de var (%20,1).

    CSV'de ayni ilce iki yazimla geciyor (Sariyer/sariyer, Merkez/merkez...):
    69 cift olcuLdu. Ilce bazli her rapor bundan bolunuyordu. Kanonik ad
    UYDURULMUYOR -- harf duzeltmesi Turkce'de tuzakli (istanbul -> Istanbul
    olur, Istanbul olmaz). Bunun yerine ayni yazimlarin EN SIK olani secilir:
    veriye dayali, tahmin yok."""
    import collections
    sayim = collections.Counter()
    ham = {}
    for dosya in ("turkiye_mekanlar.csv", "turkiye_eglence.csv"):
        if not os.path.exists(dosya):
            continue
        with io.open(dosya, encoding="utf-8-sig") as f:
            for x in csv.DictReader(f):
                ad = (x.get("ilce") or "").strip()
                if not ad:
                    continue
                sayim[ad] += 1
                ham[x["osm_id"]] = ad

    kanonik = {}
    for ad, n in sayim.items():
        k = ad.casefold()
        if k not in kanonik or n > sayim[kanonik[k]]:
            kanonik[k] = ad
    return {oid: kanonik[ad.casefold()] for oid, ad in ham.items()}


def yukle():
    ilce = ilce_haritasi()
    mekanlar = []
    for yol in sorted(glob.glob(os.path.join(VERI, "*.json"))):
        ad = os.path.basename(yol)
        if not ad[0].isdigit():
            continue
        d = json.load(io.open(yol, encoding="utf-8"))
        il = d.get("il", "")
        for m in d.get("mekanlar", []):
            m["il"] = il
            m["kod"] = ad[:2]
            m["ilce"] = ilce.get(m["id"], "")
            mekanlar.append(m)
    return mekanlar


def yogunluk_haritasi(mekanlar):
    """500 m'lik hucrelerde komsu sayisi. Talep vekili: kalabalik cadde =
    yoldan gecen musteri. O(n), tam mesafe degil -- hucre yeter."""
    HUCRE = 0.0055  # ~600 m enlem
    kova = collections.Counter()
    for m in mekanlar:
        kova[(int(m["lat"] / HUCRE), int(m["lon"] / HUCRE))] += 1
    for m in mekanlar:
        a, b = int(m["lat"] / HUCRE), int(m["lon"] / HUCRE)
        m["yogunluk"] = sum(kova[(a + i, b + j)]
                            for i in (-1, 0, 1) for j in (-1, 0, 1))
    return mekanlar


def bos_mu(m, k):
    """isletme.html icindeki eksikleriBul ile AYNI kurali uygular.
    Ikisi ayrisirsa isletmeye mesajda bir sey, sayfasinda baskasi soylenir --
    sistemin tek vaadi bu ikisinin ayni olmasi, o yuzden kural tek yerde."""
    if k == "menu":
        return m.get("tur") in YEME_ICME and m.get("min") is None
    return not str(m.get(k, "")).strip()


def degerlendir(m):
    eksik = [k for k in AGIRLIK if bos_mu(m, k)]
    m["eksik"] = eksik
    bosluk = sum(AGIRLIK[k] for k in eksik)
    # yogunluk log ile yumusatilir: 200 komsulu cadde 20 komsuludan 10 kat
    # degerli degil, ~2 kat degerli.
    m["puan"] = round(bosluk * math.log1p(m["yogunluk"]), 1)
    return m


def kanca(m):
    """Ilk mesajin ilk cumlesi. En agir tek eksigi soyler, liste saymaz."""
    if not m["eksik"]:
        return ""
    en = max(m["eksik"], key=lambda k: AGIRLIK[k])
    return EKSIK_CUMLE[en]


def kontrol():
    """Sessizce bozulursa filtre bos liste dondurur ve kimse fark etmez."""
    assert sade("İstanbul") == "istanbul"     # buyuk I noktali
    assert sade("Sarıyer") == "sariyer"       # tr harfleri
    assert sade("FATIH") == "fatih"
    assert sade("Istanbul") in sade("İstanbul")  # yazim farki eslesmeli
    assert sade(None) == ""


def main(secili_il=None, secili_ilce=None):
    kontrol()
    mekanlar = yogunluk_haritasi(yukle())
    for m in mekanlar:
        degerlendir(m)

    # Ulasilabilir = telefonu var. Telefonsuza mesaj atilamaz, listeye girmez.
    hedef = [m for m in mekanlar if str(m.get("tel", "")).strip() and m["eksik"]]
    if secili_il:
        hedef = [m for m in hedef if sade(secili_il) in sade(m["il"])]
    if secili_ilce:
        hedef = [m for m in hedef if sade(secili_ilce) in sade(m["ilce"])]
    hedef.sort(key=lambda m: -m["puan"])

    with io.open(CIKTI, "w", encoding="utf-8-sig", newline="") as f:
        y = csv.writer(f)
        y.writerow(["puan", "il", "ilce", "tur", "ad", "tel", "eksikler", "kanca",
                    "yogunluk", "sayfa", "dogrulandi_mi"])
        for m in hedef:
            y.writerow([m["puan"], m["il"], m["ilce"], m["tur"], m["ad"], m.get("tel", ""),
                        "+".join(m["eksik"]), kanca(m), m["yogunluk"],
                        "/isletme.html?il=" + m["kod"] + "&id=" + m["id"], ""])

    print("ulasilabilir hedef : %d  ->  %s" % (len(hedef), CIKTI))
    print("toplam mekan       : %d" % len(mekanlar))
    print()
    print("--- en agir eksik, kac isletmede ---")
    say = collections.Counter()
    for m in mekanlar:
        for k in m["eksik"]:
            say[k] += 1
    for k, n in say.most_common():
        print("  %-6s %6d  (%%%.1f)" % (k, n, 100.0 * n / len(mekanlar)))
    print()
    print("--- hedef listesi ilce bazinda ilk 10 ---")
    for (il, ilc), n in collections.Counter(
            (m["il"], m["ilce"] or "(ilce yok)") for m in hedef).most_common(10):
        print("  %-24s %4d" % (ilc + ", " + il, n))
    print()
    print("UYARI: 'web yok' OSM'de kayitli olmadigi anlamina gelir, sitesi")
    print("olmadigi anlamina GELMEZ. Mesaj oncesi elle dogrula, dogrulandi_mi")
    print("sutununu doldur. Dogrulanmamis listeye mesaj atma.")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None,
         sys.argv[2] if len(sys.argv) > 2 else None)
