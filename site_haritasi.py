# -*- coding: utf-8 -*-
"""app/sitemap.xml uretir ve robots.txt'deki Sitemap satirini yazar.

Alan adi burada SABIT DEGIL, disaridan veriliyor. Sebep: sitemap mutlak URL
istiyor ve depoda gercek alan adi yazili degil; uydurulmus bir alan adiyla
uretilmis sitemap, uretilmemis sitemap'ten kotudur.

    python site_haritasi.py oturalim.vercel.app
    python site_haritasi.py oturalim.vercel.app --isletmeler
    python site_haritasi.py test

INCE ICERIK KURALI: --isletmeler verilse bile her mekan girmiyor. 36.102
mekanin 23.742'sinde (%65,8) ad ve koordinattan baska hicbir sey yok; o
sayfalari indekse itmek arama motoru acisindan ince icerik uretmek olur ve
sitenin tamamini asagi ceker. Yalniz saat / telefon / adres / site / fiyat
alanlarindan EN AZ BIRI dolu olan mekan sitemap'e giriyor.

Cikti her calistirmada yeniden uretilir; depoya girmez (.gitignore).
"""
import glob
import io
import json
import os
import sys
from xml.sax.saxutils import escape

VERI = "app/veri"
CIKTI = "app/sitemap.xml"
ROBOTS = "app/robots.txt"

# Giris sayfalari. hesabim/yonetim/giris bilerek yok: noindex tasiyorlar.
SAYFALAR = [
    ("index.html",    "1.0",  "daily"),
    ("kesfet.html",   "0.9",  "daily"),
    ("hakkinda.html", "0.5",  "monthly"),
    ("paylas.html",   "0.5",  "monthly"),
    ("gizlilik.html", "0.3",  "yearly"),
]

# Bu alanlardan en az biri doluysa sayfanin soyleyecek bir seyi var.
DOLU_SAYILAN = ("saat", "tel", "adres", "web")


def govdeli_mi(m):
    """Sayfanin ad ve haritadaki noktadan fazlasi var mi?"""
    if m.get("min") is not None:
        return True
    return any(str(m.get(k) or "").strip() for k in DOLU_SAYILAN)


def mekanlar():
    """(il_kodu, mekan) ciftleri. index/etkinlik/olcut dosyalari veri degil."""
    for yol in sorted(glob.glob(os.path.join(VERI, "*.json"))):
        ad = os.path.basename(yol)
        if not ad[0].isdigit():
            continue
        d = json.load(io.open(yol, encoding="utf-8"))
        for m in d.get("mekanlar", []):
            yield ad[:2], m


def kok(alan):
    """Alan adini https koklu ve sondaki egik cizgisiz hale getirir."""
    a = alan.strip().rstrip("/")
    if not a.startswith(("http://", "https://")):
        a = "https://" + a
    return a


def url(tam, oncelik, siklik):
    return ("  <url><loc>%s</loc><changefreq>%s</changefreq>"
            "<priority>%s</priority></url>" % (escape(tam), siklik, oncelik))


def uret(alan, isletmeler=False):
    k = kok(alan)
    satirlar = [url(k + "/" + s, o, f) for s, o, f in SAYFALAR]

    toplam = girdi = 0
    if isletmeler:
        for kod, m in mekanlar():
            toplam += 1
            if not govdeli_mi(m):
                continue
            girdi += 1
            satirlar.append(url(
                "%s/isletme.html?il=%s&id=%s" % (k, kod, m["id"]),
                "0.4", "weekly"))

    icerik = ('<?xml version="1.0" encoding="UTF-8"?>\n'
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
              + "\n".join(satirlar) + "\n</urlset>\n")
    io.open(CIKTI, "w", encoding="utf-8").write(icerik)

    # robots.txt'deki Sitemap satirini tazele (varsa degistir, yoksa ekle).
    if os.path.exists(ROBOTS):
        r = [x for x in io.open(ROBOTS, encoding="utf-8").read().splitlines()
             if not x.startswith("Sitemap:")]
        while r and not r[-1].strip():
            r.pop()
        r.append("Sitemap: " + k + "/sitemap.xml")
        io.open(ROBOTS, "w", encoding="utf-8").write("\n".join(r) + "\n")

    print("sitemap: %d URL -> %s" % (len(satirlar), CIKTI))
    if isletmeler:
        print("  isletme sayfasi: %d/%d girdi (%%%.1f)"
              % (girdi, toplam, 100.0 * girdi / max(toplam, 1)))
        print("  ince icerik diye ELENEN: %d — yalniz ad + harita noktasi"
              % (toplam - girdi))
    else:
        print("  isletme sayfalari haric (eklemek icin: --isletmeler)")
    print("robots.txt Sitemap satiri: %s/sitemap.xml" % k)


def kendini_kontrol_et():
    """Alan adi normalizasyonu ve ince icerik kurali."""
    assert kok("a.com") == "https://a.com"
    assert kok("https://a.com/") == "https://a.com"
    assert kok(" http://a.com ") == "http://a.com"

    assert govdeli_mi({"tel": "0312"})
    assert govdeli_mi({"min": 100})
    assert govdeli_mi({"min": 0})                 # 0 da olculmus bir fiyat
    assert not govdeli_mi({"tur": "Kafe"})
    assert not govdeli_mi({"saat": "  "})         # bosluk dolu sayilmaz
    assert not govdeli_mi({"tel": None, "min": None})

    # & karakteri XML'de kacirilmali; isletme URL'lerinin hepsinde var.
    assert "&amp;" in url("https://a.com/x?il=06&id=n/1", "0.4", "weekly")
    assert "<loc>" in url("https://a.com/", "1.0", "daily")
    print("kontrol gecti: alan adi normalizasyonu, ince icerik kurali, XML kacirma")
    return True


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or args[0] == "test":
        sys.exit(0 if kendini_kontrol_et() else 1)
    uret(args[0], "--isletmeler" in sys.argv[1:])
