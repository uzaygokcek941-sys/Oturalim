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

for yol in sorted(glob.glob(os.path.join(KOK, "*.json"))):
    if yol.endswith("index.json"):
        continue
    kod = os.path.basename(yol)[:-5]
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
        })

# Vitrin: temsili olsun diye once yeterli kalemi olanlar (tek kalemlik bir
# dondurmaci medyani yaniltici), sonra tur cesitliligi gozetilerek ucuzdan pahaliya.
aday = [x for x in ornekler if x["n"] >= 8]
aday.sort(key=lambda x: x["medyan"])
vitrin, kota = [], {}
for x in aday:                       # her turden en fazla 2, toplam 12
    if kota.get(x["tur"], 0) >= 2:
        continue
    kota[x["tur"]] = kota.get(x["tur"], 0) + 1
    vitrin.append(x)
    if len(vitrin) == 12:
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
print("vitrin medyan araligi: %d - %d TL" % (vitrin[0]["medyan"], vitrin[-1]["medyan"]))

assert toplam > 30000 and fiyatli > 0 and kalem > 0, "veri beklenenden kucuk"
