# -*- coding: utf-8 -*-
"""Anasayfa icin vitrin.json uretir: gercek sayilar + fiyati bilinen ornek mekanlar.
Kaynak app/veri/*.json; uydurma sayi yok, hepsi sayilarak bulunuyor."""
import json, glob, os, statistics

KOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "veri")

def yukle(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)

ix = yukle(os.path.join(KOK, "index.json"))
il_ad = {i["kod"]: i["ad"] for i in ix["iller"]}

toplam = fiyatli = kalem = 0
tur_say, ornekler = {}, []

# Klasordeki her JSON il dosyasi degil: fiyat_olcut.json gibi yan ciktilar
# da burada duruyor. Il listesini index.json belirler, klasor icerigi degil.
for kod in sorted(d["kod"] for d in ix["iller"]):
    yol = os.path.join(KOK, kod + ".json")
    if not os.path.exists(yol):
        continue
    for m in yukle(yol)["mekanlar"]:
        toplam += 1
        tur_say[m["tur"]] = tur_say.get(m["tur"], 0) + 1
        if not m.get("menu"):
            continue
        fiyatli += 1
        kalem += len(m["menu"])
        ornekler.append({
            "il": kod, "ilAd": il_ad.get(kod, kod), "ad": m["ad"], "tur": m["tur"],
            "min": m["min"], "max": m["max"], "n": len(m["menu"]),
            "medyan": round(statistics.median(k["f"] for k in m["menu"])),
            "id": m["id"],
            # Fiyat burada HESAPLANMIYOR. Icecegi yemekten ayiran kural
            # app/ortak.js icindeki yemekFiyati()'nde; ayni kurali iki dilde
            # tutmak, ikisinin ayrisip ayni mekana iki farkli fiyat soylemesi
            # demek. Ham alanlar tasiniyor, hesabi tarayici yapiyor.
            "kat": m.get("kat"),
            "menu": [{"a": k["a"]} for k in m["menu"]],
            # yemekFiyati() bir yildan eski fiyati gostermiyor; tarih
            # tasinmazsa anasayfa o kurali HIC uygulayamaz ve kesfet
            # ekraninin geri cektigi fiyati gostermeye devam eder.
            # Kural tek yerde diye ham alanlarin TAMAMI tasinmali.
            "tarih": m.get("tarih"),
        })

# Aday havuzu. Once yeterli kalemi olanlar (tek kalemlik bir dondurmaci
# medyani yaniltici), sonra tur cesitliligi. ESKIDEN buradan "en ucuz 12"
# secilliyordu ve o medyan icecekleri de sayiyordu: vitrin yapisal olarak
# en kotu veriyi one cikariyordu -- tema demosu menuler hep en ucuz gorunur.
# Artik havuz genis birakiliyor, eleme ve siralama tarayicida yapiliyor.
# Havuza yalniz "kat" verisi olanlar girer: onsuz tarayici icecegi yemekten
# ayiramaz, mekan zaten elenir -- bosuna tasimanin anlami yok. Ayni zincirin
# on subesi de havuzu doldurmasin diye ad tekrari burada eleniyor. Bunlar veri
# secimi; FIYAT kurali degil, o hala yalniz ortak.js'te.
aday = [x for x in ornekler if x["n"] >= 8 and x["kat"]]
aday.sort(key=lambda x: x["ad"])
vitrin, kota, gorulen = [], {}, set()
for x in aday:                       # her turden en fazla 10, toplam 30 aday
    ad = x["ad"].strip().lower()
    if ad in gorulen or kota.get(x["tur"], 0) >= 10:
        continue
    gorulen.add(ad)
    kota[x["tur"]] = kota.get(x["tur"], 0) + 1
    vitrin.append(x)
    if len(vitrin) == 30:
        break

cikti = {
    "toplam": toplam,
    "il": len(ix["iller"]),
    "fiyatliMekan": fiyatli,
    "kalem": kalem,
    "turler": sorted(tur_say.items(), key=lambda a: -a[1]),
    "vitrin": vitrin,
}
yol = os.path.join(os.path.dirname(KOK), "vitrin.json")
with open(yol, "w", encoding="utf-8") as f:
    json.dump(cikti, f, ensure_ascii=False, separators=(",", ":"))

print("yazildi:", yol)
print("toplam %d mekan / %d il / fiyatli %d / kalem %d" % (toplam, cikti["il"], fiyatli, kalem))
print("turler:", cikti["turler"])
print("vitrin aday havuzu: %d mekan (eleme ve siralama tarayicida)" % len(vitrin))

assert toplam > 30000 and fiyatli > 0 and kalem > 0, "veri beklenenden kucuk"
