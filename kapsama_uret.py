# -*- coding: utf-8 -*-
"""Kapsama sayfasi icin app/kapsama.json uretir.

    python kapsama_uret.py

NEDEN VAR. Bu sektorde kimse kendi kapsamasini yayinlamiyor: Google
Maps de, Yemeksepeti de "kac mekanin fiyatini bilmiyoruz" demiyor.
Cebimde'nin kotu sayisi %0,82 ve onu KENDIMIZ yayinliyoruz.

Iki sebebi var, ikisi de somut:
  (a) PAZARLAMA.md B5 zaten "bunlari soyle" diyor -- burasi o listeyi
      pitch'ten URUNE tasiyor.
  (b) "Uygulamaniz bos" itirazini once biz soylersek, itiraz olmaktan
      cikip yontem oluyor.

HICBIR SAYI ELLE YAZILMIYOR. Sayfa bu dosyayi okuyor; dosya da
app/veri/*.json'dan sayiliyor. Ayni desen vitrin.json'da da var ve
sebebi olculdu: kesfet.html iki yerde "36.102 mekan" yaziyordu, gercek
35.852'ydi. Elle yazilan her rakam eskiyor.

FIYAT KURALI BURAYA KOPYALANMIYOR. Bir mekanin "fiyati var" sayilmasi
app/ortak.js icindeki yemekFiyati()'ne bagli (bayat fiyati eliyor,
icecegi yemekten ayiriyor, asgari kalem istiyor). Burada sayilan sey
daha basit ve adi da oyle: MENUSU OLCULMUS mekan. Ayni kurali iki dilde
tutmak, ikisinin ayrisip ayni mekana iki farkli sey demesi olurdu.
"""
import glob
import io
import json
import os

import veri_bicim   # il dosyasi bicimi tek yerde

KOK = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(KOK, "app", "veri")

# Sayfada satir satir gosterilecek alanlar. Sira ONEMLI: kullanicinin
# once sordugu sey fiyat, en sonda sordugu sey sosyal medya.
ALANLAR = [
    ("menu",    "menü / fiyat"),
    ("adres",   "açık adres"),
    ("saat",    "açılış saati"),
    ("tel",     "telefon"),
    ("web",     "web sitesi"),
    ("insta",   "Instagram"),
    ("ilce",    "ilçe"),
    ("mahalle", "mahalle"),
]


def uret():
    with io.open(os.path.join(VERI, "index.json"), encoding="utf-8") as f:
        ix = json.load(f)
    il_ad = {i["kod"]: i["ad"] for i in ix["iller"]}

    toplam = 0
    alan_say = {a: 0 for a, _ in ALANLAR}
    # ULASILAMAZ: ne telefon, ne web, ne sosyal. Bu sayi bayiligin ve
    # saha kartinin tek gerekcesi -- o mekanlara uzaktan ulasmanin yolu
    # yok (BAYILIK.md).
    ulasilamaz = 0
    markalar = set()
    iller = []

    # Klasordeki her JSON il dosyasi degil (fiyat_olcut.json gibi yan
    # ciktilar da orada). Il listesini index.json belirliyor.
    for kod in sorted(d["kod"] for d in ix["iller"]):
        yol = os.path.join(VERI, kod + ".json")
        if not os.path.exists(yol):
            continue
        with io.open(yol, encoding="utf-8") as f:
            ms = veri_bicim.coz(json.load(f))["mekanlar"]
        n_menu = 0
        for m in ms:
            toplam += 1
            for a, _ in ALANLAR:
                if m.get(a):
                    alan_say[a] += 1
            if m.get("menu"):
                n_menu += 1
                markalar.add(" ".join(m["ad"].split()).lower())
            if not (m.get("tel") or m.get("web") or m.get("insta")):
                ulasilamaz += 1
        iller.append({"kod": kod, "ad": il_ad.get(kod, kod),
                      "mekan": len(ms), "menu": n_menu})

    cikti = {
        "il": len(iller),
        "mekan": toplam,
        "menulu": alan_say["menu"],
        # MENULU MEKAN ILE ISLETME AYRI SEY ve fark buyuk. Olculdu:
        # 293 menulu mekan yalniz ~55 farkli ad; Domino's ve Kahve
        # Dunyasi ikisi tek basina yarisindan fazla. "293 mekanin
        # menusu var" cumlesi bunu saklardi.
        "menuluMarka": len(markalar),
        "ulasilamaz": ulasilamaz,
        "menusuzIl": sum(1 for i in iller if i["menu"] == 0),
        "alanlar": [{"alan": a, "ad": ad, "mekan": alan_say[a]}
                    for a, ad in ALANLAR],
        # Iller MENU ORANINA gore, en dolu once. Alfabetik olsaydi
        # sayfanin soyledigi sey kaybolurdu: en iyi ilde bile oran %2.
        "iller": sorted(iller,
                        key=lambda i: (-(i["menu"] / i["mekan"] if i["mekan"] else 0),
                                       -i["mekan"], i["ad"])),
    }
    return cikti


def yaz():
    c = uret()
    yol = os.path.join(KOK, "app", "kapsama.json")
    with io.open(yol, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, separators=(",", ":"))
    print("yazildi:", yol)
    print("%d il / %d mekan / menulu %d (%d isletme, %%%.2f)"
          % (c["il"], c["mekan"], c["menulu"], c["menuluMarka"],
             100.0 * c["menulu"] / c["mekan"]))
    print("tek menusu olmayan il: %d / %d" % (c["menusuzIl"], c["il"]))
    print("ne tel ne web ne insta: %d (%%%.1f)"
          % (c["ulasilamaz"], 100.0 * c["ulasilamaz"] / c["mekan"]))
    # Veri beklenenden kucukse dosyayi yazdik ama HABER veriyoruz:
    # sessizce kucuk bir kapsama yayinlamak, yanlis sayi yayinlamaktir.
    assert c["mekan"] > 30000 and c["il"] >= 80, "veri beklenenden kucuk"
    return c


def kendini_kontrol_et():
    c = uret()
    assert c["mekan"] > 30000, c["mekan"]
    assert 0 < c["menulu"] < c["mekan"]
    # Isletme sayisi mekan sayisindan KUCUK olmali: zincir subeleri.
    assert c["menuluMarka"] <= c["menulu"], "marka sayisi mekandan buyuk"
    # Iller menu oranina gore azalan sirada mi.
    o = [i["menu"] / i["mekan"] for i in c["iller"] if i["mekan"]]
    assert o == sorted(o, reverse=True), "iller orana gore sirali degil"
    # Alan listesi sayfanin bekledigi biçimde mi.
    assert [a["alan"] for a in c["alanlar"]] == [a for a, _ in ALANLAR]
    assert all(a["mekan"] <= c["mekan"] for a in c["alanlar"])
    print("kontrol gecti: sayim, marka deflatoru, il siralamasi, alan listesi")
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.exit(0 if kendini_kontrol_et() else 1)
    yaz()
