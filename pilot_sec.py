#!/usr/bin/env python3
"""Arama listesinden pilot masa icin en uygun mekanlari puanlar.

Kriter: aksam aciklik (masa saati 19-22), bahce, wifi, kafe/restoran olmasi,
zincir/fast-food isimlerinin elenmesi.
"""
import csv, re, sys

ZINCIR = ("starbucks", "burger king", "mcdonald", "dominos", "domino's", "kfc",
          "popeyes", "subway", "simit sarayi", "simit sarayı", "espressolab",
          "kahve dunyasi", "kahve dünyası", "tchibo", "caribou", "arby")

def aksam_acik(saat: str) -> bool:
    if not saat:
        return False
    if "24/7" in saat:
        return True
    # kapanis saati 21:00 veya sonrasi mi
    return any(int(h) >= 21 or h in ("00", "01", "02", "03", "04")
               for h in re.findall(r"-(\d{2}):\d{2}", saat))

def puan(r):
    p = 0
    if aksam_acik(r["saatler"]): p += 3
    elif not r["saatler"]:       p += 1          # bilinmiyor, arayip sorulur
    if r["bahce"] == "yes":      p += 2
    if r["wifi"] in ("wlan", "yes"): p += 1
    if r["tur"] == "cafe":       p += 1          # kafe daha uygun fiyatli
    if r["adres"]:               p += 1
    return p

def main(yol="cankaya_arama_listesi.csv", n=15):
    rows = list(csv.DictReader(open(yol, encoding="utf-8-sig")))
    rows = [r for r in rows if not any(z in r["ad"].casefold() for z in ZINCIR)]
    for r in rows:
        r["puan"] = puan(r)
    rows.sort(key=lambda r: (-r["puan"], r["ad"].casefold()))
    top = rows[:n]

    alanlar = ["puan", "ad", "tur", "telefon", "saatler", "bahce", "adres", "harita", "durum", "not"]
    with open("cankaya_pilot_15.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=alanlar, extrasaction="ignore")
        w.writeheader()
        for r in top:
            w.writerow({**r, "durum": "", "not": ""})

    assert top and top[0]["puan"] >= top[-1]["puan"], "siralama bozuk"
    print(f"Aday havuzu (zincirler elendi): {len(rows)}")
    print(f"Secilen pilot mekan           : {len(top)}\n")
    for i, r in enumerate(top, 1):
        print(f"{i:>2}. [{r['puan']}] {r['ad']}  |  {r['telefon']}  |  {r['saatler'] or 'saat bilinmiyor'}")

if __name__ == "__main__":
    main(*(sys.argv[1:] or []))
