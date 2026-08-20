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
            if COP_AD.search(ad) or len(ad) < 3:
                continue
            menu[(r["il"], r["mekan"])].append({"a": ad, "f": fiyat})
    return menu


def mekan_kaydi(m, menu):
    kalemler = sorted(menu.get((m["il"], m["ad"]), []), key=lambda x: x["f"])[:40]
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
    return kayit


def main():
    menu = menuleri_oku()
    iller = defaultdict(list)
    for m in csv.DictReader(open("turkiye_mekanlar.csv", encoding="utf-8-sig")):
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
        dizin.append({"kod": kod, "ad": IL_ADI.get(il, il), "n": len(kayitlar),
                      "fiyatli": sum(1 for r in kayitlar if "menu" in r),
                      "kb": round(os.path.getsize(yol) / 1024)})

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


if __name__ == "__main__":
    main()
