#!/usr/bin/env python3
"""81 ilin eglence mekanlarini OpenStreetMap'ten ceker.

turkiye_cek.py yeme-icme mekanlarini (kafe, restoran, bar, pub, fast food,
dondurma) topluyor. Bu script onun kapsamadigi eglenceyi topluyor: gece
kulubu, sinema, tiyatro, canli muzik, bowling, oyun salonu, muze, tema
parki. Bar ve pub BILEREK burada yok -- zaten diger scriptte var, iki kez
cekmek ayni mekani iki kayda bolerdi.

Kullanim:
    python eglence_cek.py                # 81 il
    python eglence_cek.py TR-06 TR-34    # sadece belirtilen iller

Cikti:
    ham_eglence/<il-kodu>.json
    turkiye_eglence.csv
"""
import csv, json, os, subprocess, sys, time

from turkiye_cek import ILLER, ENDPOINT, BEKLEME, DENEME, gecerli_json, ALANLAR

HAM_DIZIN = "ham_eglence"

# Uc ayri OSM etiket ailesi. Park bilerek disarida: sayica cok ve buyuk
# cogunlugu isimsiz, isimsiz park oneri olarak ise yaramaz.
AMENITY = "^(nightclub|cinema|theatre|arts_centre|casino|events_venue|music_venue)$"
LEISURE = ("^(bowling_alley|amusement_arcade|escape_game|water_park|ice_rink|"
           "trampoline_park|miniature_golf|dance|adult_gaming_centre)$")
TOURISM = "^(museum|theme_park|zoo|aquarium|gallery)$"

# Bir mekan birden fazla aile tasiyabilir (muze + kutuphane gibi). Tur olarak
# SUZGECE TAKILAN degeri sec; yoksa suzgecte olmayan bir etiket tur olarak
# gecer ve veriye "library" gibi kategoriler sizar.
_D = {k: __import__("re").compile(v) for k, v in
      (("amenity", AMENITY), ("leisure", LEISURE), ("tourism", TOURISM))}


def sorgu(kod):
    # nwr = node+way+relation. Muze ve tema parki cogu zaman relation olarak
    # cizili; yalniz node/way sorgulamak onlari kacirir.
    return (f'[out:json][timeout:300];area["ISO3166-2"="{kod}"]->.a;'
            f'(nwr["amenity"~"{AMENITY}"](area.a);'
            f' nwr["leisure"~"{LEISURE}"](area.a);'
            f' nwr["tourism"~"{TOURISM}"](area.a););out center tags;')


def cek(kod):
    yol = os.path.join(HAM_DIZIN, f"{kod}.json")
    if os.path.exists(yol):
        if gecerli_json(yol):
            return yol, "atlandi"
        os.remove(yol)
    kod_http = "?"
    for deneme in range(1, DENEME + 1):
        r = subprocess.run(
            ["curl", "-s", "-o", yol, "-w", "%{http_code}", "--max-time", "400",
             "-A", "Oturalim/0.1", "--data-urlencode", f"data={sorgu(kod)}", ENDPOINT],
            capture_output=True, text=True)
        kod_http = r.stdout.strip()
        if kod_http == "200" and gecerli_json(yol):
            return yol, "ok"
        time.sleep(BEKLEME * deneme * 2)
    if os.path.exists(yol) and not gecerli_json(yol):
        os.remove(yol)
    return yol, f"basarisiz({kod_http})"


def cikar(el, il):
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
    # Hangi aile eslestiyse tur o. Bir mekan hem amenity hem tourism tasiyabilir
    # (sanat merkezi + galeri gibi); sira sabit tutuluyor ki tur kararli olsun.
    tur = ""
    for alan, desen in _D.items():
        d = t.get(alan, "")
        if d and desen.match(d):
            tur = d
            break
    if not tur:
        return None
    adres = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
    return {
        "il": il,
        "ad": ad,
        "tur": tur,
        "mutfak": t.get("cuisine", ""),
        "telefon": t.get("phone") or t.get("contact:phone") or "",
        "website": t.get("website") or t.get("contact:website") or "",
        "instagram": t.get("contact:instagram") or "",
        "saatler": t.get("opening_hours", ""),
        "bahce": t.get("outdoor_seating", ""),
        "wifi": t.get("internet_access", ""),
        "adres": adres,
        "ilce": t.get("addr:district", ""),
        "mahalle": t.get("addr:suburb") or t.get("addr:neighbourhood") or "",
        "lat": f"{lat:.7f}",
        "lon": f"{lon:.7f}",
        "harita": f"https://www.google.com/maps/search/?api=1&query={lat:.7f},{lon:.7f}",
        "osm_id": f'{el["type"]}/{el["id"]}',
    }


def main(kodlar):
    os.makedirs(HAM_DIZIN, exist_ok=True)
    for i, kod in enumerate(kodlar, 1):
        _, durum = cek(kod)
        print(f"[{i}/{len(kodlar)}] {ILLER[kod]:<16} cekim: {durum}", flush=True)
        if durum == "ok":
            time.sleep(BEKLEME)

    hepsi, gorulen = [], set()
    for kod, il in ILLER.items():
        yol = os.path.join(HAM_DIZIN, f"{kod}.json")
        if not os.path.exists(yol) or not gecerli_json(yol):
            continue
        with open(yol, encoding="utf-8") as f:
            elemanlar = json.load(f)["elements"]
        n = 0
        for el in elemanlar:
            r = cikar(el, il)
            if not r or r["osm_id"] in gorulen:
                continue
            gorulen.add(r["osm_id"])
            hepsi.append(r)
            n += 1
        print(f"  {il:<16} {n:>6} mekan", flush=True)

    hepsi.sort(key=lambda r: (r["il"], r["ad"].casefold()))
    with open("turkiye_eglence.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR)
        w.writeheader()
        w.writerows(hepsi)

    assert hepsi, "hic kayit yok"
    assert all("," not in r["lat"] for r in hepsi), "koordinatta virgul"
    assert not any("Ã" in r["ad"] or "Ä" in r["ad"] for r in hepsi), "mojibake"

    import collections
    print()
    print(f"TOPLAM: {len(hepsi)} eglence mekani, "
          f"{len(set(r['il'] for r in hepsi))} il")
    for t, n in collections.Counter(r["tur"] for r in hepsi).most_common():
        print(f"  {t:<22} {n:>5}")


if __name__ == "__main__":
    main(sys.argv[1:] or list(ILLER))
