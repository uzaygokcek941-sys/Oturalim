#!/usr/bin/env python3
"""Turkiye geneli mekan verisini OpenStreetMap'ten il il ceker.

Kullanim:
    python turkiye_cek.py                # 81 il
    python turkiye_cek.py TR-06 TR-34    # sadece belirtilen iller

Cikti:
    ham/<il-kodu>.json   her ilin ham yaniti (yeniden calistirmada atlanir)
    turkiye_mekanlar.csv

Not: Overpass ucretsiz ve paylasimli bir kaynak. Iller arasi bekleme
suresi bilerek konuldu; kaldirma.
"""
import csv, json, os, subprocess, sys, time

ENDPOINT = "https://overpass-api.de/api/interpreter"
HAM_DIZIN = "ham"
BEKLEME = 4          # saniye, iller arasi
DENEME = 3

AMENITY = "^(cafe|restaurant|bar|pub|fast_food|ice_cream)$"

# ISO 3166-2 il kodu -> il adi (plaka sirasi)
ILLER = {
    "TR-01": "Adana", "TR-02": "Adiyaman", "TR-03": "Afyonkarahisar", "TR-04": "Agri",
    "TR-05": "Amasya", "TR-06": "Ankara", "TR-07": "Antalya", "TR-08": "Artvin",
    "TR-09": "Aydin", "TR-10": "Balikesir", "TR-11": "Bilecik", "TR-12": "Bingol",
    "TR-13": "Bitlis", "TR-14": "Bolu", "TR-15": "Burdur", "TR-16": "Bursa",
    "TR-17": "Canakkale", "TR-18": "Cankiri", "TR-19": "Corum", "TR-20": "Denizli",
    "TR-21": "Diyarbakir", "TR-22": "Edirne", "TR-23": "Elazig", "TR-24": "Erzincan",
    "TR-25": "Erzurum", "TR-26": "Eskisehir", "TR-27": "Gaziantep", "TR-28": "Giresun",
    "TR-29": "Gumushane", "TR-30": "Hakkari", "TR-31": "Hatay", "TR-32": "Isparta",
    "TR-33": "Mersin", "TR-34": "Istanbul", "TR-35": "Izmir", "TR-36": "Kars",
    "TR-37": "Kastamonu", "TR-38": "Kayseri", "TR-39": "Kirklareli", "TR-40": "Kirsehir",
    "TR-41": "Kocaeli", "TR-42": "Konya", "TR-43": "Kutahya", "TR-44": "Malatya",
    "TR-45": "Manisa", "TR-46": "Kahramanmaras", "TR-47": "Mardin", "TR-48": "Mugla",
    "TR-49": "Mus", "TR-50": "Nevsehir", "TR-51": "Nigde", "TR-52": "Ordu",
    "TR-53": "Rize", "TR-54": "Sakarya", "TR-55": "Samsun", "TR-56": "Siirt",
    "TR-57": "Sinop", "TR-58": "Sivas", "TR-59": "Tekirdag", "TR-60": "Tokat",
    "TR-61": "Trabzon", "TR-62": "Tunceli", "TR-63": "Sanliurfa", "TR-64": "Usak",
    "TR-65": "Van", "TR-66": "Yozgat", "TR-67": "Zonguldak", "TR-68": "Aksaray",
    "TR-69": "Bayburt", "TR-70": "Karaman", "TR-71": "Kirikkale", "TR-72": "Batman",
    "TR-73": "Sirnak", "TR-74": "Bartin", "TR-75": "Ardahan", "TR-76": "Igdir",
    "TR-77": "Yalova", "TR-78": "Karabuk", "TR-79": "Kilis", "TR-80": "Osmaniye",
    "TR-81": "Duzce",
}

# Sosyal medya: OSM'de her platformun kendi etiketi var ve iki bicimde
# yaziliyor -- "contact:instagram" ile duz "instagram". Ikisi de okunuyor;
# yalniz birine bakmak, veriyi dogru girmis mekanlari atlamak olurdu.
SOSYAL_ETIKET = {
    "instagram": ("contact:instagram", "instagram"),
    "facebook":  ("contact:facebook", "facebook"),
    "x":         ("contact:x", "contact:twitter", "twitter"),
    "tiktok":    ("contact:tiktok", "tiktok"),
    "youtube":   ("contact:youtube", "youtube"),
}

ALANLAR = ["il", "ad", "tur", "mutfak", "telefon", "website", "instagram",
           "facebook", "x", "tiktok", "youtube",
           "saatler", "bahce", "wifi", "adres", "ilce", "mahalle",
           "lat", "lon", "harita", "osm_id"]


def sorgu(kod):
    return (f'[out:json][timeout:300];area["ISO3166-2"="{kod}"]->.a;'
            f'(node["amenity"~"{AMENITY}"](area.a);'
            f'way["amenity"~"{AMENITY}"](area.a););out center tags;')


def gecerli_json(yol):
    """Overpass yogunken 200 disi kod veya HTML hata sayfasi donebiliyor.
    Boyuta bakmak yetmez -- bozuk dosya onbellege girip kalici hataya donusur."""
    try:
        with open(yol, encoding="utf-8") as f:
            return isinstance(json.load(f).get("elements"), list)
    except Exception:
        return False


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
             "-A", "Cebimde/0.1", "--data-urlencode", f"data={sorgu(kod)}", ENDPOINT],
            capture_output=True, text=True)
        kod_http = r.stdout.strip()
        if kod_http == "200" and gecerli_json(yol):
            return yol, "ok"
        time.sleep(BEKLEME * deneme * 2)
    if os.path.exists(yol) and not gecerli_json(yol):
        os.remove(yol)          # bozugu birakma, sonraki calistirma yeniden denesin
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
    adres = " ".join(x for x in (t.get("addr:street"), t.get("addr:housenumber")) if x)
    return {
        "il": il,
        "ad": ad,
        "tur": t.get("amenity", ""),
        "mutfak": t.get("cuisine", ""),
        "telefon": t.get("phone") or t.get("contact:phone") or "",
        "website": t.get("website") or t.get("contact:website") or "",
        # "ad" DEGIL "alan": ustteki mekan adini golgelemesin. (Sozluk
        # uretecinin kendi kapsami var, yani calisirdi; ama okuyan kisi
        # iki satir yukarida "ad" gorup duraklar.)
        **{alan: next((t[e] for e in etiketler if t.get(e)), "")
           for alan, etiketler in SOSYAL_ETIKET.items()},
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

    # 1) Yalnizca istenen illeri cek
    for i, kod in enumerate(kodlar, 1):
        _, durum = cek(kod)
        print(f"[{i}/{len(kodlar)}] {ILLER[kod]:<16} cekim: {durum}", flush=True)
        if durum == "ok":
            time.sleep(BEKLEME)

    # 2) CSV'yi HER ZAMAN onbellekteki TUM illerden kur.
    #    Yoksa tek il icin yeniden calistirmak butun dosyayi eziyor.
    hepsi, gorulen = [], set()
    for kod, il in ILLER.items():
        yol = os.path.join(HAM_DIZIN, f"{kod}.json")
        if not os.path.exists(yol) or not gecerli_json(yol):
            continue
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
        n = 0
        for el in veri.get("elements", []):
            r = cikar(el, il)
            if not r or r["osm_id"] in gorulen:
                continue
            gorulen.add(r["osm_id"])
            hepsi.append(r)
            n += 1
        print(f"  {il:<16} {n:>6} mekan", flush=True)

    hepsi.sort(key=lambda r: (r["il"], r["ad"].casefold()))
    with open("turkiye_mekanlar.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR)
        w.writeheader()
        w.writerows(hepsi)

    assert hepsi, "hic kayit yok"
    assert all("," not in r["lat"] for r in hepsi), "koordinatta virgul"
    assert not any("Ã" in r["ad"] or "Ä" in r["ad"] for r in hepsi), "mojibake"

    print(f"\nTOPLAM: {len(hepsi)} mekan, {len(set(r['il'] for r in hepsi))} il")
    print(f"Websitesi olan : {sum(1 for r in hepsi if r['website'])}")
    print(f"Telefonu olan  : {sum(1 for r in hepsi if r['telefon'])}")
    print(f"Instagram olan : {sum(1 for r in hepsi if r['instagram'])}")


def kendini_kontrol_et():
    """python turkiye_cek.py test — aga cikmadan cikarma mantigini dogrular.

    NEDEN GEREKLI: bu betikte HIC kontrol yoktu ve buradaki hatalarin
    hepsi SESSIZ. Bir alan yanlis etiketten okunursa CSV'de bos kalir,
    boru hatti bos alani "bilgi yok" diye tasir ve uygulamada eksik
    gorunur -- hicbir yerde hata yok. Instagram tam olarak boyle
    kaybolmustu: toplaniyordu ama uygulamaya hic ulasmiyordu.
    """
    dugum = {"type": "node", "id": 1, "lat": 39.9, "lon": 32.85,
             "tags": {"name": "Deneme", "amenity": "cafe",
                      "contact:instagram": "a", "facebook": "b",
                      "contact:twitter": "c", "opening_hours": "24/7"}}
    r = cikar(dugum, "Ankara")
    assert r["ad"] == "Deneme" and r["tur"] == "cafe", r
    # Sosyal etiketlerin IKI bicimi de okunmali.
    assert r["instagram"] == "a", r          # contact:instagram
    assert r["facebook"] == "b", r           # duz facebook
    assert r["x"] == "c", r                  # contact:twitter -> x
    assert r["tiktok"] == "" and r["youtube"] == "", r
    assert r["osm_id"] == "node/1", r
    # CSV basligi ile uretilen anahtarlar birebir ayni olmali; ayrisirsa
    # DictWriter ya sutunu atar ya patlar.
    assert set(r) == set(ALANLAR), set(r) ^ set(ALANLAR)

    # Oncelik: contact:* once geliyor.
    d2 = dict(dugum)
    d2["tags"] = dict(dugum["tags"], instagram="duz")
    assert cikar(d2, "Ankara")["instagram"] == "a", "contact:instagram once gelmeli"

    # Adsiz ve konumsuz dugum ATILIR: ikisi de mekan sayfasi kurulamaz.
    assert cikar({"type": "node", "id": 2, "lat": 1, "lon": 1, "tags": {}}, "X") is None
    assert cikar({"type": "node", "id": 3, "tags": {"name": "A"}}, "X") is None

    # way: koordinat "center"dan gelir.
    y = cikar({"type": "way", "id": 9, "center": {"lat": 40.1, "lon": 29.0},
               "tags": {"name": "Yol", "amenity": "bar"}}, "Bursa")
    assert y["osm_id"] == "way/9" and y["lat"] == "40.1000000", y

    # Koordinatta VIRGUL olmamali: CSV'yi bolerdi.
    assert "," not in y["lat"] and "," not in y["lon"], y

    # Sorgu il kodunu gercekten kullaniyor mu.
    assert '"ISO3166-2"="TR-06"' in sorgu("TR-06")

    assert len(ILLER) == 81, len(ILLER)
    print("kontrol gecti: alan cikarma, sosyal etiketler, 81 il")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        kendini_kontrol_et()
    else:
        main(sys.argv[1:] or list(ILLER))
