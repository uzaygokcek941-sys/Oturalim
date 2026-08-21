#!/usr/bin/env python3
"""turkiye_mekanlar.csv + menu verisi -> uygulamanin okudugu JSON dosyalari.

Kullanim:  python app_veri.py

Cikti:
    app/veri/index.json     il listesi + mekan sayilari
    app/veri/<kod>.json     o ilin mekanlari

Menu gurultusu burada elenir: sitelerin cogu perakende urun katalogu
(kavrulmus cekirdek paketi, pasta siparisi) yayinliyor; bunlar "masada ne
oderim" sorusunun cevabi degil. Bu yuzden asiri uc fiyatlar atilir ve
uygulamada ORTALAMA HESAP degil, MENU KALEMI ARALIGI gosterilir.
"""
import csv
import json
import os
import re
from collections import defaultdict

from fiyat_analiz import kategorile

IL_KODU = {
    "Adana": "01", "Adiyaman": "02", "Afyonkarahisar": "03", "Agri": "04",
    "Amasya": "05", "Ankara": "06", "Antalya": "07", "Artvin": "08",
    "Aydin": "09", "Balikesir": "10", "Bilecik": "11", "Bingol": "12",
    "Bitlis": "13", "Bolu": "14", "Burdur": "15", "Bursa": "16",
    "Canakkale": "17", "Cankiri": "18", "Corum": "19", "Denizli": "20",
    "Diyarbakir": "21", "Edirne": "22", "Elazig": "23", "Erzincan": "24",
    "Erzurum": "25", "Eskisehir": "26", "Gaziantep": "27", "Giresun": "28",
    "Gumushane": "29", "Hakkari": "30", "Hatay": "31", "Isparta": "32",
    "Mersin": "33", "Istanbul": "34", "Izmir": "35", "Kars": "36",
    "Kastamonu": "37", "Kayseri": "38", "Kirklareli": "39", "Kirsehir": "40",
    "Kocaeli": "41", "Konya": "42", "Kutahya": "43", "Malatya": "44",
    "Manisa": "45", "Kahramanmaras": "46", "Mardin": "47", "Mugla": "48",
    "Mus": "49", "Nevsehir": "50", "Nigde": "51", "Ordu": "52",
    "Rize": "53", "Sakarya": "54", "Samsun": "55", "Siirt": "56",
    "Sinop": "57", "Sivas": "58", "Tekirdag": "59", "Tokat": "60",
    "Trabzon": "61", "Tunceli": "62", "Sanliurfa": "63", "Usak": "64",
    "Van": "65", "Yozgat": "66", "Zonguldak": "67", "Aksaray": "68",
    "Bayburt": "69", "Karaman": "70", "Kirikkale": "71", "Batman": "72",
    "Sirnak": "73", "Bartin": "74", "Ardahan": "75", "Igdir": "76",
    "Yalova": "77", "Karabuk": "78", "Kilis": "79", "Osmaniye": "80",
    "Duzce": "81",
}

# Ascii il adlarini ekranda dogru yazmak icin
IL_ADI = {
    "Adiyaman": "Adıyaman", "Agri": "Ağrı", "Aydin": "Aydın",
    "Balikesir": "Balıkesir", "Bingol": "Bingöl", "Canakkale": "Çanakkale",
    "Cankiri": "Çankırı", "Corum": "Çorum", "Diyarbakir": "Diyarbakır",
    "Elazig": "Elazığ", "Eskisehir": "Eskişehir", "Gumushane": "Gümüşhane",
    "Hakkari": "Hakkâri", "Istanbul": "İstanbul", "Izmir": "İzmir",
    "Kirklareli": "Kırklareli", "Kirsehir": "Kırşehir", "Kutahya": "Kütahya",
    "Kahramanmaras": "Kahramanmaraş", "Mugla": "Muğla", "Mus": "Muş",
    "Nevsehir": "Nevşehir", "Nigde": "Niğde", "Sanliurfa": "Şanlıurfa",
    "Sirnak": "Şırnak", "Tekirdag": "Tekirdağ", "Usak": "Uşak",
    "Igdir": "Iğdır", "Karabuk": "Karabük", "Duzce": "Düzce",
    "Bartin": "Bartın", "Kirikkale": "Kırıkkale",
}

TUR_TR = {"cafe": "Kafe", "restaurant": "Restoran", "bar": "Bar",
          "pub": "Pub", "fast_food": "Fast food", "ice_cream": "Dondurma"}

# Menu kalemi sayilabilecek makul araliklar (TL). Disari cikan degerler
# perakende urun / hediye paketi / veri hatasidir.
ALT_SINIR, UST_SINIR = 25, 2000

# Menu kalemi olmayan satir adlari
COP_AD = re.compile(r"(kargo|teslimat|hediye|paket|abonelik|kupon|bagis|bağış|"
                    r"sepet|toplam|indirim)", re.I)

# Yiyecek/icecek olmayan fiziksel urun. Kahve dukkanlari menuyle ayni sayfada
# termos ve fincan takimi da satiyor; bunlar "masada ne oderim"in cevabi degil.
# fiyat_analiz.PERAKENDE burada KULLANILMAZ: o filtre porsiyon safligi icin
# kalibre, "4 Adet Pizzetta" gibi gercek menu kalemlerini de eler.
ESYA = re.compile(r"(alışveriş çantası|termos|makinesi|fincan takım|bardak takım|"
                  r"hediye kart|öğütücü|demlik|tişört|kupa takım|filtre kağıd)", re.I)


def menuleri_oku(yol="tr_menu.csv"):
    """Anahtar (il, mekan adi) -- sadece ada bakmak yetmez: zincir adlari
    illerde tekrar ediyor ve Istanbul'daki subeye Ankara'nin fiyatlari yapisir."""
    menu = defaultdict(list)
    try:
        f = open(yol, encoding="utf-8-sig")
    except FileNotFoundError:
        return menu
    with f:
        for r in csv.DictReader(f):
            ad = r["kalem"].strip(" =:-–—·\t")
            fiyat = float(r["fiyat"])
            if not (ALT_SINIR <= fiyat <= UST_SINIR):
                continue
            if COP_AD.search(ad) or ESYA.search(ad) or len(ad) < 3:
                continue
            menu[(r["il"], r["mekan"])].append({"a": ad, "f": fiyat})
    return menu


def _site_anahtari(u):
    """http/https, www ve sondaki / farkini yok sayan site anahtari."""
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")


def _alan_adi(u):
    """Yolu atip yalniz alan adini dondurur: a.com/menu/ -> a.com"""
    return _site_anahtari(u).split("/")[0]


def ek_menuler_oku(mekanlar, yollar=("menu_pdf_kalem.csv", "menu_ocr_kalem.csv")):
    """PDF/sayfa metni ve gorsel OCR ile toplanan menuler.

    Birlestirme anahtari MEKAN ADI degil WEB SITESI: bu kalemler siteler
    taranarak bulundu ve zincir adlari illerde tekrar ediyor ("Domino's"
    10 ilde). Site adresi tek bir mekani gosteriyor.
    """
    # Tam adres eslesmesi ONCE. Alan adina dusmek gerekiyor cunku OSM
    # etiketi yollu olabiliyor ("dokuzondokuz.com/menu/") ama taramadaki
    # kayit kok adresi ("dokuzondokuz.com"). Alan adi eslesmesi yalnizca
    # o alan adi TEK mekana aitse kullanilir: "adilesultanevyemekleri.com"
    # iki ayri subeye ait ve hangisine ait oldugu belirsiz kalir.
    site_mekan, alan_mekan = {}, defaultdict(set)
    for m in mekanlar:
        u = (m.get("website") or "").strip()
        if u:
            site_mekan.setdefault(_site_anahtari(u), (m["il"], m["ad"]))
            alan_mekan[_alan_adi(u)].add((m["il"], m["ad"]))
    tekil_alan = {a: next(iter(v)) for a, v in alan_mekan.items() if len(v) == 1}

    ek = defaultdict(list)
    eslesmeyen = set()
    for yol in yollar:
        if not os.path.exists(yol):
            continue
        with open(yol, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                u = r.get("website", "")
                hedef = (site_mekan.get(_site_anahtari(u))
                         or tekil_alan.get(_alan_adi(u)))
                if not hedef:
                    eslesmeyen.add(r.get("mekan", "?"))
                    continue
                ad = r["kalem"].strip(" =:-–—·\t")
                try:
                    fiyat = float(r["fiyat"])
                except (ValueError, TypeError):
                    continue
                if not (ALT_SINIR <= fiyat <= UST_SINIR):
                    continue
                if COP_AD.search(ad) or ESYA.search(ad) or len(ad) < 3:
                    continue
                ek[hedef].append({"a": ad, "f": fiyat})
    if eslesmeyen:
        print("ek menu: OSM mekaniyla eslesmeyen %d kayit (%s)"
              % (len(eslesmeyen), ", ".join(sorted(eslesmeyen)[:3])))
    return ek


def kategori_dokumu(kalemler):
    """Mekanin kendi menusunden urun kategorisi kirilimi.

    Butun fiyatlar gercek: hicbir deger hesaplanmiyor, yalniz mekanin kendi
    kaleminden seciliyor. Cift sayida kalemde ust/alt ortalamasi ALINMAZ
    (o gozlenmemis bir fiyat olurdu) — alt medyan, yani gercekten menude
    yazan bir fiyat dondurulur.
    """
    kova = defaultdict(list)
    for k in kalemler:
        kat = kategorile(k["a"])[0]
        if kat:
            kova[kat].append(k["f"])
    dokum = {}
    for kat, fiyatlar in kova.items():
        fiyatlar.sort()
        dokum[kat] = {
            "n": len(fiyatlar),
            "med": fiyatlar[(len(fiyatlar) - 1) // 2],   # alt medyan = gercek kalem
            "min": fiyatlar[0],
            "max": fiyatlar[-1],
        }
    return dokum


def mekan_kaydi(m, menu):
    tum_kalemler = menu.get((m["il"], m["ad"]), [])
    # Kategori dokumu TAM listeden: kayda giren 40 kalem en ucuzlar oldugu icin
    # onlardan hesaplanan kirilim sistematik olarak asagi kayardi.
    kalemler = sorted(tum_kalemler, key=lambda x: x["f"])[:40]
    kayit = {
        "id": m["osm_id"],
        "ad": m["ad"],
        "tur": TUR_TR.get(m["tur"], m["tur"]),
        "lat": round(float(m["lat"]), 6),
        "lon": round(float(m["lon"]), 6),
    }
    for anahtar, deger in (("mutfak", m["mutfak"]), ("tel", m["telefon"]),
                           ("web", m["website"]), ("saat", m["saatler"]),
                           ("adres", m["adres"])):
        if deger:
            kayit[anahtar] = deger
    if m["bahce"] == "yes":
        kayit["bahce"] = 1
    if m["wifi"] in ("wlan", "yes"):
        kayit["wifi"] = 1
    if kalemler:
        kayit["menu"] = kalemler
        kayit["min"] = kalemler[0]["f"]
        kayit["max"] = kalemler[-1]["f"]
        dokum = kategori_dokumu(tum_kalemler)
        if dokum:
            kayit["kat"] = dokum
    return kayit


def main():
    menu = menuleri_oku()
    mekanlar = list(csv.DictReader(open("turkiye_mekanlar.csv", encoding="utf-8-sig")))

    # Ikinci kaynak: PDF metni, sayfa metni ve gorsel OCR ile toplananlar.
    # Ayni mekana iki kaynaktan kalem gelirse ikisi de kalir; tekrar eden
    # (ad, fiyat) cifti asagida tekilleniyor.
    once = sum(len(v) for v in menu.values())
    for anahtar, kalemler in ek_menuler_oku(mekanlar).items():
        menu[anahtar].extend(kalemler)
    for anahtar, kalemler in menu.items():
        gorulen, tekil = set(), []
        for k in kalemler:
            imza = (k["a"], k["f"])
            if imza not in gorulen:
                gorulen.add(imza)
                tekil.append(k)
        menu[anahtar] = tekil
    print("menu kalemi: %d -> %d (ek kaynaklar dahil, tekillenmis)"
          % (once, sum(len(v) for v in menu.values())))

    iller = defaultdict(list)
    for m in mekanlar:
        iller[m["il"]].append(mekan_kaydi(m, menu))

    os.makedirs("app/veri", exist_ok=True)
    dizin = []
    for il, kayitlar in iller.items():
        kod = IL_KODU.get(il)
        if not kod:
            print(f"  UYARI: {il} icin il kodu yok, atlandi")
            continue
        kayitlar.sort(key=lambda r: r["ad"].casefold())
        yol = f"app/veri/{kod}.json"
        with open(yol, "w", encoding="utf-8") as f:
            json.dump({"il": IL_ADI.get(il, il), "mekanlar": kayitlar},
                      f, ensure_ascii=False, separators=(",", ":"))
        # Konumdan il bulmak icin merkez. Ortalama degil medyan: tek bir
        # yanlis etiketlenmis mekan merkezi denize kaydirmasin.
        enler = sorted(r["lat"] for r in kayitlar)
        boylar = sorted(r["lon"] for r in kayitlar)
        orta = len(kayitlar) // 2
        dizin.append({"kod": kod, "ad": IL_ADI.get(il, il), "n": len(kayitlar),
                      "fiyatli": sum(1 for r in kayitlar if "menu" in r),
                      "kb": round(os.path.getsize(yol) / 1024),
                      "lat": round(enler[orta], 4), "lon": round(boylar[orta], 4)})

    dizin.sort(key=lambda d: -d["n"])
    with open("app/veri/index.json", "w", encoding="utf-8") as f:
        json.dump({"varsayilan": "06", "iller": dizin}, f, ensure_ascii=False)

    toplam = sum(d["n"] for d in dizin)
    assert len(dizin) == 81, f"81 il bekleniyordu, {len(dizin)} yazildi"
    assert toplam > 30000, f"mekan sayisi dusuk: {toplam}"
    print(f"il: {len(dizin)}  mekan: {toplam}")
    print(f"menusu olan mekan: {sum(d['fiyatli'] for d in dizin)}")
    print(f"kalan menu kalemi: {sum(len(v) for v in menu.values())} "
          f"(sinirlar {ALT_SINIR}-{UST_SINIR} TL)")
    print("\nen buyuk 6 dosya:")
    for d in sorted(dizin, key=lambda d: -d["kb"])[:6]:
        print(f"  {d['ad']:<12}{d['n']:>7} mekan  {d['kb']:>5} KB")


def kendini_kontrol_et():
    """python app_veri.py test — kategori dokumunun fiyat uydurmadigini dogrular."""
    kalemler = [{"a": "Turk Kahvesi", "f": 90.0}, {"a": "Turk kahvesi (duble)", "f": 120.0},
                {"a": "Adana Kebap", "f": 700.0}, {"a": "Ayran", "f": 60.0},
                {"a": "Guatemala Filtre Kahve 250g", "f": 350.0}]
    d = kategori_dokumu(kalemler)
    gercek = {k["f"] for k in kalemler}
    for kat, o in d.items():
        for alan in ("med", "min", "max"):
            assert o[alan] in gercek, "uydurma fiyat: %s.%s=%s" % (kat, alan, o[alan])
    # cift sayida kalemde ortalama DEGIL, gozlenen alt medyan gelmeli
    assert d["Türk kahvesi"]["med"] == 90.0, d["Türk kahvesi"]
    assert d["Türk kahvesi"]["n"] == 2
    # 250g paket porsiyon degil: hic kategoriye girmemeli
    assert "Filtre kahve" not in d, d
    assert d["Kebap"]["med"] == 700.0 and d["Ayran"]["med"] == 60.0

    # Site eslestirme: OSM etiketi yollu, tarama kaydi kok adres olabiliyor
    assert _site_anahtari("https://www.A.com/menu/") == "a.com/menu"
    assert _alan_adi("https://www.A.com/menu/") == "a.com"
    assert _alan_adi("http://a.com") == _alan_adi("https://www.a.com/x/y")

    print("kontrol gecti: %d kategori, uydurma fiyat yok" % len(d))
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.exit(0 if kendini_kontrol_et() else 1)
    main()
