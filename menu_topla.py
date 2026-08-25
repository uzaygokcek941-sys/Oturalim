#!/usr/bin/env python3
"""Mekan CSV'sindeki websitelerinden menu kalemi + fiyat toplar.

Kullanim:
    python menu_topla.py                          # cankaya_mekanlar.csv
    python menu_topla.py turkiye_mekanlar.csv tr  # baska kaynak / cikti oneki

Iki kaynak denenir, sirayla:
  1) WooCommerce Store API  -- sitenin KENDI resmi acik ucu, yapilandirilmis veri
  2) HTML ayristirma        -- menu_cikar.py

Not: JavaScript ile basilan menuler ikisiyle de gelmez; bunlar "js" olarak
isaretlenir ve gercek tarayici gerektirir.
"""
import csv
import datetime
import html
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

from menu_cikar import menu_cikar

ISCI = 16              # es zamanli alan adi; her alan adina yine tek istek gidiyor
ZAMAN_ASIMI = "25"     # paralel calistigi icin uzun zaman asimi duvar saatine
                       # neredeyse hic mal olmuyor; 12sn'de yavas siteler dusuyordu
UA = "Mozilla/5.0 (compatible; CebimdeBot/0.1)"

WOO_UCLARI = ("/wp-json/wc/store/v1/products?per_page=100",
              "/wp-json/wc/store/products?per_page=100")

# tarih: fiyatin DERLENDIGI gun. Enflasyonda tarihsiz fiyat bir iddia
# degil, bir tahmindir; kullanici kac aylik bir sayiya baktigini bilmeli.
BUGUN = datetime.date.today().isoformat()

ALANLAR = ["mekan", "il", "tur", "website", "kaynak", "kategori", "kalem",
           "fiyat", "tarih"]


def getir(url):
    r = subprocess.run(["curl", "-sL", "--max-time", ZAMAN_ASIMI, "-A", UA, url],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout or ""


def kok(url):
    if not url.startswith("http"):
        url = "https://" + url
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}"


def woo_dene(taban):
    """WooCommerce Store API: fiyat tam sayi + minor_unit ile gelir."""
    for uc in WOO_UCLARI:
        ham = getir(taban + uc)
        if not ham.lstrip().startswith("["):
            continue
        try:
            urunler = json.loads(ham)
        except Exception:
            continue
        cikti = []
        for u in urunler:
            fiyatlar = u.get("prices") or {}
            f = fiyatlar.get("price")
            if f in (None, "", "0"):
                continue
            birim = fiyatlar.get("currency_minor_unit", 2)
            try:
                fiyat = int(f) / (10 ** int(birim))
            except (TypeError, ValueError):
                continue
            if fiyat <= 0:
                continue
            # WooCommerce adlari HTML VARLIGIYLA donuyor: "6&#8217;li
            # Macaron". Cozulmezse kullaniciya oldugu gibi gorunuyor.
            kat = ", ".join(html.unescape(c.get("name", ""))
                            for c in (u.get("categories") or [])[:2])
            cikti.append((kat, html.unescape(u.get("name") or "").strip(), fiyat))
        if cikti:
            return cikti
    return []


def html_dene(taban):
    # "0 TL", "0,00 TL" gibi yer tutucular menu kalemi degil -- ele.
    return [("", ad, f) for ad, f in menu_cikar(getir(taban)) if f > 0]


def tara(taban):
    """Tek alan adi: once Woo API, sonra HTML. Hicbir site butun taramayi
    oldurmemeli -- beklenmedik veri gelirse 'hata' isaretlenip devam edilir."""
    try:
        kalemler = woo_dene(taban)
        if kalemler:
            return kalemler, "woo"
        kalemler = html_dene(taban)
        if kalemler:
            return kalemler, "html"
        return [], "js"          # muhtemelen JS ile basiliyor
    except Exception as e:
        print(f"    ! {taban}: {type(e).__name__}: {e}", flush=True)
        return [], "hata"


def main(kaynak="cankaya_mekanlar.csv", onek="cankaya"):
    mekanlar = [r for r in csv.DictReader(open(kaynak, encoding="utf-8-sig")) if r["website"]]
    print(f"Websitesi olan mekan: {len(mekanlar)}\n", flush=True)

    # Zincirler ayni alan adini paylasiyor -> once benzersiz alan adlarina in.
    alan_adlari = sorted({kok(m["website"]) for m in mekanlar})
    print(f"Benzersiz alan adi  : {len(alan_adlari)}\n", flush=True)

    # Farkli alan adlari paralel taranabilir; ayni alan adina zaten tek istek
    # gittigi icin hicbir sunucu ust uste vurulmuyor.
    onbellek, sayac = {}, 0
    with ThreadPoolExecutor(max_workers=ISCI) as havuz:
        for taban, sonuc in zip(alan_adlari, havuz.map(tara, alan_adlari)):
            onbellek[taban] = sonuc
            sayac += 1
            if sonuc[0] or sayac % 100 == 0:
                print(f"[{sayac}/{len(alan_adlari)}] {taban[:44]:<46} "
                      f"{sonuc[1]:<5} {len(sonuc[0]):>4} kalem", flush=True)

    satirlar, ozet = [], []
    for m in mekanlar:
        taban = kok(m["website"])
        kalemler, kaynak_ad = onbellek[taban]
        for kat, ad, fiyat in kalemler:
            satirlar.append({"mekan": m["ad"], "il": m.get("il", ""), "tur": m["tur"],
                             "website": taban, "kaynak": kaynak_ad, "kategori": kat,
                             "kalem": ad, "fiyat": f"{fiyat:.2f}", "tarih": BUGUN})
        fiyatlar = sorted(f for _, _, f in kalemler)
        medyan = fiyatlar[len(fiyatlar) // 2] if fiyatlar else 0
        ozet.append({"mekan": m["ad"], "tur": m["tur"], "website": taban,
                     "kaynak": kaynak_ad, "kalem_sayisi": len(kalemler),
                     "medyan_fiyat": f"{medyan:.2f}" if medyan else ""})

    with open(f"{onek}_menu.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR)
        w.writeheader()
        w.writerows(satirlar)

    with open(f"{onek}_menu_ozet.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["mekan", "tur", "website", "kaynak",
                                          "kalem_sayisi", "medyan_fiyat"])
        w.writeheader()
        w.writerows(ozet)

    basarili = [o for o in ozet if o["kalem_sayisi"]]
    assert all(float(s["fiyat"]) > 0 for s in satirlar), "sifir/negatif fiyat sizmis"
    print(f"\nSite denendi      : {len(mekanlar)}")
    print(f"Fiyat cikan site  : {len(basarili)} (%{100*len(basarili)//max(len(mekanlar),1)})")
    print(f"Toplam kalem      : {len(satirlar)}")
    for k in ("woo", "html", "js", "hata"):
        print(f"  {k:<5}: {sum(1 for o in ozet if o['kaynak'] == k)} site")


if __name__ == "__main__":
    main(*(sys.argv[1:] or []))
