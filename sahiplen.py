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


def yukle():
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


def degerlendir(m):
    eksik = [k for k in AGIRLIK
             if not str(m.get(k, "")).strip()
             and not (k == "menu" and m.get("tur") not in YEME_ICME)]
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


def main(secili_il=None):
    mekanlar = yogunluk_haritasi(yukle())
    for m in mekanlar:
        degerlendir(m)

    # Ulasilabilir = telefonu var. Telefonsuza mesaj atilamaz, listeye girmez.
    hedef = [m for m in mekanlar if str(m.get("tel", "")).strip() and m["eksik"]]
    if secili_il:
        hedef = [m for m in hedef if secili_il.lower() in m["il"].lower()]
    hedef.sort(key=lambda m: -m["puan"])

    with io.open(CIKTI, "w", encoding="utf-8-sig", newline="") as f:
        y = csv.writer(f)
        y.writerow(["puan", "il", "tur", "ad", "tel", "eksikler", "kanca",
                    "yogunluk", "sayfa", "dogrulandi_mi"])
        for m in hedef:
            y.writerow([m["puan"], m["il"], m["tur"], m["ad"], m.get("tel", ""),
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
    print("--- hedef listesi il bazinda ilk 10 ---")
    for il, n in collections.Counter(m["il"] for m in hedef).most_common(10):
        print("  %-12s %4d" % (il, n))
    print()
    print("UYARI: 'web yok' OSM'de kayitli olmadigi anlamina gelir, sitesi")
    print("olmadigi anlamina GELMEZ. Mesaj oncesi elle dogrula, dogrulandi_mi")
    print("sutununu doldur. Dogrulanmamis listeye mesaj atma.")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
