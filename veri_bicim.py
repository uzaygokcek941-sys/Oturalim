#!/usr/bin/env python3
"""Il dosyalarinin sikistirilmis bicimi. Tek kaynak: kodlayan da cozen de burada.

    python veri_bicim.py test      # kendi kontrolu
    python veri_bicim.py cevir     # app/veri/*.json dosyalarini yeni bicime cevirir

NEDEN
=====
Istanbul dosyasi 1,78 MB ham / 396 KB gzip idi ve agirligin bir kismi VERI
DEGIL, TEKRAR: 12.095 nesnenin her biri "id", "ad", "tur", "lat", "lon"
anahtarlarini yeniden yaziyordu. Olculdu: yalniz anahtar adlari 451 KB,
yani ham dosyanin %25'i.

BICIM: YOGUN ALANLAR SUTUNLU, SEYREK ALANLAR INDEKSLI
=====================================================
    {"il":"Istanbul",
     "sutun":{"id":[...], "ad":[...], "tur":[...], "lat":[...], "lon":[...]},
     "ek":{"adres":{"3":"...", "17":"..."}, "menu":{"5":[...]}}}

Bes alan her mekanda var -> sutun. Kalan on dort alan seyrek (menu 12.095'te
190) -> indeksle sozluk. Hepsini sutuna koymak, sutunlari `null` ile
doldururdu ve dosya BUYURDU: olculdu, tam demet bicimi 2,00 MB.

OLCULEN (Istanbul, 34.json):
    bugunku            ham 1733 KB   gzip 396 KB
    sutun + seyrek ek  ham 1325 KB   gzip 322 KB      -%24 / -%19

Ikisinin de dusmesi onemli: gzip indirmeyi, ham boyut JSON.parse suresini
belirliyor. Sutunlu bicimin `null` dolgulu hali gzip'te iyi, hamda kotuydu --
yani telefonda indirmeyi kisaltip ayristirmayi uzatirdi.

NEDEN GERCEK COZUM DEGIL, AMA UCUZ
==================================
Yol haritasindaki not "gercek cozum cografi bolmeleme" diyor ve dogru:
bolmeleme kullanicinin BAKTIGI bolgeyi indirir, bu bicim butun ili
indirmeye devam ediyor. Ama bolmeleme veri duzenini ve iki tuketiciyi
birden degistiriyor; bu degisiklik TEK bir cozucu fonksiyona bakiyor ve
cozulen nesne eskisiyle BAYT BAYT ayni. Kanit: `test` adimi 81 ilin
hepsinde kodla-coz turunu yapip esitlik ariyor.

ID ONEKI
========
"node/13527199437" -> "n13527199437". Onek uc degerden biri (olculdu:
node 11.352, way 737, relation 6) ve 12.095 kez tekrarliyor. Cozucu geri
aciyor: DISARIYA giden kimlik degismiyor, cunku o kimlik veritabaninda
mekan_id olarak duruyor ve adres cubugunda geziniyor.
"""
import glob
import io
import json
import os
import sys

# Her mekanda bulunan alanlar. Sirasi ONEMLI degil ama sabit olsun:
# dosyalar kosumdan kosuma ayni ciksin diye.
YOGUN = ["id", "ad", "tur", "lat", "lon"]

# Seyrek alanlar. Listede OLMAYAN bir alan sessizce DUSMEZ -- kodlayici
# hata verir (asagida). Yeni bir alan eklendiginde burasi da guncellenmeli
# ve unutulursa kosum patlar, veri kaybolmaz.
SEYREK = ["mutfak", "adres", "saat", "tel", "web", "wifi", "bahce", "insta",
          "menu", "kat", "min", "max", "tarih", "kalem_n"]

ONEK = {"node": "n", "way": "w", "relation": "r"}
ACIK = {v: k for k, v in ONEK.items()}


def _id_kisalt(kimlik):
    tur, _, kalan = str(kimlik).partition("/")
    return ONEK[tur] + kalan if (kalan and tur in ONEK) else str(kimlik)


def _id_ac(kisa):
    k = str(kisa)
    if k and k[0] in ACIK and k[1:].isdigit():
        return ACIK[k[0]] + "/" + k[1:]
    return k


def kodla(il_adi, mekanlar):
    """mekan listesi -> sikistirilmis sozluk."""
    bilinen = set(YOGUN) | set(SEYREK)
    sutun = {k: [] for k in YOGUN}
    ek = {}
    for i, m in enumerate(mekanlar):
        yabanci = set(m) - bilinen
        if yabanci:
            # Sessizce dusurmek, bir alanin uygulamadan kaybolmasi demekti.
            raise ValueError("bilinmeyen alan: %s (veri_bicim.SEYREK'e ekle)"
                             % ", ".join(sorted(yabanci)))
        for k in YOGUN:
            if k not in m:
                raise ValueError("yogun alan eksik: %s (%s)" % (k, m.get("id")))
            sutun[k].append(_id_kisalt(m[k]) if k == "id" else m[k])
        for k in SEYREK:
            if k in m:
                ek.setdefault(k, {})[str(i)] = m[k]
    return {"il": il_adi, "sutun": sutun, "ek": ek}


def coz(d):
    """Sikistirilmis sozluk -> {"il":..., "mekanlar":[...]}.

    ESKI BICIMI DE OKUR: "mekanlar" anahtari varsa dosya donusturulmemis
    demektir ve oldugu gibi donuyor. Boylece donusum sirasinda yarim kalan
    bir depo calismaya devam ediyor."""
    if "mekanlar" in d:
        return d
    sutun = d.get("sutun") or {}
    n = len(sutun.get("id") or [])
    mekanlar = []
    for i in range(n):
        m = {}
        for k in YOGUN:
            deger = sutun[k][i]
            m[k] = _id_ac(deger) if k == "id" else deger
        mekanlar.append(m)
    for alan, kayitlar in (d.get("ek") or {}).items():
        for indeks, deger in kayitlar.items():
            mekanlar[int(indeks)][alan] = deger
    return {"il": d.get("il"), "mekanlar": mekanlar}


def il_oku(yol):
    """Bir il dosyasini okur ve HER IKI bicimde de ayni seyi dondurur."""
    return coz(json.loads(io.open(yol, encoding="utf-8").read()))


def yaz(yol, il_adi, mekanlar):
    io.open(yol, "w", encoding="utf-8").write(
        json.dumps(kodla(il_adi, mekanlar), ensure_ascii=False,
                   separators=(",", ":")))


# ============================================================
# Kendini kontrol
# ============================================================
def kendini_kontrol_et():
    s = []
    ornek = [
        {"id": "node/1", "ad": "A Kafe", "tur": "Kafe", "lat": 39.9, "lon": 32.8},
        {"id": "way/2", "ad": "B Bar", "tur": "Bar", "lat": 40.0, "lon": 29.0,
         "adres": "Bagdat Caddesi 448", "wifi": 1},
        {"id": "relation/3", "ad": "C Muze", "tur": "Muze", "lat": 41.0, "lon": 28.9,
         "menu": [{"a": "Cay", "f": 20}], "kat": {"Cay": {"n": 1, "med": 20}}},
    ]
    if coz(kodla("Test", ornek))["mekanlar"] != ornek:
        s.append("kodla/coz turu ornegi bozdu")
    # Uc onek de geri acilmali: "w2" -> "way/2" olmazsa mekan sayfasi
    # acilmaz ve veritabanindaki mekan_id ile eslesmez.
    for k in ("node/9", "way/9", "relation/9"):
        if _id_ac(_id_kisalt(k)) != k:
            s.append("id turu bozuk: " + k)
    # Onek listesinde olmayan bir kimlik OLDUGU GIBI gecmeli.
    if _id_ac(_id_kisalt("garip/9")) != "garip/9":
        s.append("bilinmeyen onekli kimlik bozuluyor")
    # Rakam olmayan kuyruk ACILMAMALI: "node" ile baslayan bir ad
    # ("nazar") kazara kimlik sanilmasin.
    if _id_ac("nazar") != "nazar":
        s.append("rakamsiz deger kimlik sanildi")
    # Bilinmeyen alan SESSIZCE dusmemeli.
    try:
        kodla("Test", [{"id": "node/1", "ad": "A", "tur": "K", "lat": 1, "lon": 2,
                        "yeni_alan": 5}])
        s.append("bilinmeyen alan sessizce dustu")
    except ValueError:
        pass
    # Eski bicim oldugu gibi okunmali (yarim donusumde depo calissin).
    eski = {"il": "X", "mekanlar": ornek}
    if coz(eski) != eski:
        s.append("eski bicim okunamiyor")
    # Bos il.
    if coz(kodla("Bos", []))["mekanlar"] != []:
        s.append("bos il bozuk")

    # GERCEK VERI: 81 ilin hepsinde tur, ve BOYUT gercekten dusuyor mu.
    yollar = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "app", "veri", "*.json")))
    bakilan = 0
    for yol in yollar:
        ad = os.path.basename(yol)
        if not ad[:2].isdigit():
            continue                      # index/etkinlik/olcut dosyalari
        d = il_oku(yol)
        bakilan += 1
        if coz(kodla(d["il"], d["mekanlar"]))["mekanlar"] != d["mekanlar"]:
            s.append("%s: kodla/coz turu veriyi degistirdi" % ad)
    if bakilan == 0:
        # Kontrolun KENDISI bir sey gormeli: dosyalar bulunamazsa
        # "hepsi gecti" demek yanlis olurdu.
        s.append("hicbir il dosyasi bulunamadi (app_veri.py calisti mi?)")
    return s, bakilan


def cevir():
    """Var olan dosyalari yeni bicime cevirir. Tekrar calistirilabilir."""
    kok = os.path.dirname(os.path.abspath(__file__))
    onceki = sonraki = 0
    n = 0
    for yol in sorted(glob.glob(os.path.join(kok, "app", "veri", "*.json"))):
        ad = os.path.basename(yol)
        if not ad[:2].isdigit():
            continue
        onceki += os.path.getsize(yol)
        d = il_oku(yol)
        yaz(yol, d["il"], d["mekanlar"])
        sonraki += os.path.getsize(yol)
        n += 1
    # index.json'daki `kb` alani DOSYA BOYUTU: donusumden sonra eskiyor.
    # Tazelenmezse depoda, hicbir yerin okumadigi ama YANLIS olan bir sayi
    # kalirdi -- bu depoda "kimse bakmiyor" bir gerekce degil.
    dizin_yolu = os.path.join(kok, "app", "veri", "index.json")
    if os.path.exists(dizin_yolu):
        dz = json.loads(io.open(dizin_yolu, encoding="utf-8").read())
        for il in dz.get("iller", []):
            y = os.path.join(kok, "app", "veri", il["kod"] + ".json")
            if os.path.exists(y):
                il["kb"] = round(os.path.getsize(y) / 1024)
        io.open(dizin_yolu, "w", encoding="utf-8").write(
            json.dumps(dz, ensure_ascii=False))
    print("%d il cevrildi: %.0f KB -> %.0f KB (-%.0f%%)"
          % (n, onceki / 1024, sonraki / 1024,
             100 * (1 - sonraki / onceki) if onceki else 0))


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "test"
    if komut == "cevir":
        cevir()
        sys.exit(0)
    sorunlar, bakilan = kendini_kontrol_et()
    for x in sorunlar:
        print("  HATA: " + x)
    if not sorunlar:
        print("kontrol gecti: kodla/coz turu %d il dosyasinda veriyi degistirmiyor"
              % bakilan)
    sys.exit(1 if sorunlar else 0)
