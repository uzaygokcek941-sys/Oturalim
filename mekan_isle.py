#!/usr/bin/env python3
"""Overpass ham JSON -> temiz mekan CSV'leri.

Kullanim:  python mekan_isle.py <ham.json> <onek>
Ornek:     python mekan_isle.py cankaya_osm_raw.json cankaya
"""
import csv, json, sys

ALANLAR = ["ad", "tur", "mutfak", "telefon", "website", "instagram",
           "saatler", "bahce", "wifi", "adres", "lat", "lon", "harita", "osm_id"]


def cikar(el):
    t = el.get("tags", {})
    ad = t.get("name")
    if not ad:
        return None
    if el["type"] == "node":
        lat, lon = el.get("lat"), el.get("lon")
    else:
        c = el.get("center") or {}
        lat, lon = c.get("lat"), c.get("lon")
    if lat is None or lon is None:
        return None
    adres = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
    return {
        "ad": ad,
        "tur": t.get("amenity", ""),
        "mutfak": t.get("cuisine", ""),
        "telefon": t.get("phone") or t.get("contact:phone") or "",
        "website": t.get("website") or t.get("contact:website") or "",
        "instagram": t.get("contact:instagram") or "",
        "saatler": t.get("opening_hours", ""),
        "bahce": t.get("outdoor_seating", ""),
        "wifi": t.get("internet_access", ""),
        "adres": adres,
        "lat": f"{lat:.7f}",
        "lon": f"{lon:.7f}",
        "harita": f"https://www.google.com/maps/search/?api=1&query={lat:.7f},{lon:.7f}",
        "osm_id": f'{el["type"]}/{el["id"]}',
    }


def yaz(yol, satirlar, ek_kolon=()):
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR + list(ek_kolon))
        w.writeheader()
        for s in satirlar:
            w.writerow({**s, **{k: "" for k in ek_kolon}})


def main(ham, onek):
    with open(ham, encoding="utf-8") as f:
        veri = json.load(f)

    gorulen, hepsi = set(), []
    for el in veri.get("elements", []):
        r = cikar(el)
        if not r or r["ad"].casefold() in gorulen:
            continue
        gorulen.add(r["ad"].casefold())
        hepsi.append(r)
    hepsi.sort(key=lambda r: r["ad"].casefold())

    # Aranabilir liste: telefonu olan kafe ve restoranlar
    ara = [r for r in hepsi if r["telefon"] and r["tur"] in ("cafe", "restaurant")]

    yaz(f"{onek}_mekanlar.csv", hepsi)
    yaz(f"{onek}_arama_listesi.csv", ara, ek_kolon=("durum", "not"))

    # Kontroller: sessizce bozuk veri uretmektense patla
    assert hepsi, "hic mekan cikmadi"
    assert all("," not in r["lat"] and "," not in r["lon"] for r in hepsi), "koordinatta virgul var"
    assert not any("Ã" in r["ad"] or "Ä" in r["ad"] for r in hepsi), "mojibake tespit edildi"

    print(f"Isimli benzersiz mekan : {len(hepsi)}")
    print(f"Arama listesi (tel'li) : {len(ara)}")
    tur = {}
    for r in hepsi:
        tur[r["tur"]] = tur.get(r["tur"], 0) + 1
    for k, v in sorted(tur.items(), key=lambda x: -x[1]):
        print(f"  {k:<12} {v}")
    print(f"Telefonu olan : {sum(1 for r in hepsi if r['telefon'])}")
    print(f"Saati olan    : {sum(1 for r in hepsi if r['saatler'])}")
    print(f"Bahcesi olan  : {sum(1 for r in hepsi if r['bahce'] == 'yes')}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "cankaya_osm_raw.json",
         sys.argv[2] if len(sys.argv) > 2 else "cankaya")
