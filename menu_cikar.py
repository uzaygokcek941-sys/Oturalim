#!/usr/bin/env python3
"""Bir isletme sitesinden menu kalemi + fiyat cikarir.

Kullanim:
    python menu_cikar.py                 # kendi kendini kontrol
    python menu_cikar.py <url> [url ...]

Yontem: HTML'i blok elemanlarda satira bolup, "ad satiri" ile onu takip eden
"fiyat satiri" ciftlerini yakalar. Fiyatin ayni satirda olmasi sart degil --
cogu site adi ve fiyati ayri DOM dugumunde tutuyor.
"""
import html as htmllib
import re
import subprocess
import sys

# Sadece gercek blok elemanlari satir bolsun. span/a/bdi satir ici -- bunlarda
# bolersek "499.50<span>TL</span>" gibi fiyatlar ikiye ayrilip kaybolur.
BLOK = r"</?(?:div|p|li|tr|td|h[1-6]|br|section|article|ul|ol|dl|dd|dt)\b[^>]*>"
SAYI = r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?"
FIYAT = re.compile(rf"^\s*(?:₺|TL)?\s*({SAYI})\s*(?:₺|TL)\s*$", re.I)
# \b yalnizca "TL" icin anlamli; "₺" kelime karakteri olmadigi icin ondan
# sonra kelime siniri olusmaz ve eslesme sessizce kaybolur.
SATIR_ICI = re.compile(rf"({SAYI})\s*(?:₺|TL\b)", re.I)
# Fiyat gibi gorunen ama menu kalemi olmayan satirlari ele
COP = re.compile(r"(sipari|kargo|indirim|kupon|toplam|sepet|kdv|puan|taksit)", re.I)


def metin_satirlari(ham: str):
    ham = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", ham)
    ham = re.sub(BLOK, "\n", ham, flags=re.I)
    ham = re.sub(r"(?s)<[^>]+>", " ", ham)
    for satir in htmllib.unescape(ham).splitlines():
        s = re.sub(r"[ \t\xa0]+", " ", satir).strip()
        if s:
            yield s


def fiyata_cevir(s: str) -> float:
    """TR ve EN bicimlerini birlikte cozer.

    "1.749,50"->1749.5   "1,749.50"->1749.5   "499.50"->499.5
    "5.000.000"->5000000 "5.000"->5000        "1.234"->1234
    Tek nokta/virgulden sonra tam 3 hane varsa binlik ayiracidir; TR'de
    "5.000" bes bin demektir, bes degil.
    """
    s = s.strip()
    son_nokta, son_virgul = s.rfind("."), s.rfind(",")
    if son_nokta >= 0 and son_virgul >= 0:
        ondalik = "," if son_virgul > son_nokta else "."      # sondaki ondalik
        binlik = "." if ondalik == "," else ","
        s = s.replace(binlik, "").replace(ondalik, ".")
    elif son_nokta >= 0 or son_virgul >= 0:
        ayirac = "." if son_nokta >= 0 else ","
        if s.count(ayirac) > 1 or len(s) - s.rfind(ayirac) - 1 == 3:
            s = s.replace(ayirac, "")                          # binlik
        else:
            s = s.replace(ayirac, ".")                         # ondalik
    return float(s)


def _gecerli_ad(ad: str, max_ad_uzunluk: int) -> bool:
    return (2 < len(ad) <= max_ad_uzunluk
            and any(c.isalpha() for c in ad)
            and not COP.search(ad))


def menu_cikar(ham: str, max_ad_uzunluk: int = 60):
    """Iki yerlesim de destekleniyor:
    1) ad ve fiyat AYNI satirda  -> "Klasik Kahvalti 499,50 TL"
    2) fiyat KENDI satirinda     -> ad onceki satirlarda
    Hangi yerlesimin cikacagi sitenin HTML'ine gore degisir; ikisi de gerekli.
    """
    satirlar = list(metin_satirlari(ham))
    bulunan, gorulen = [], set()

    def ekle(ad, ham_fiyat):
        anahtar = ad.casefold()
        if anahtar in gorulen:
            return
        gorulen.add(anahtar)
        bulunan.append((ad, fiyata_cevir(ham_fiyat)))

    for i, s in enumerate(satirlar):
        m = FIYAT.match(s)
        if m:                                   # durum 2: fiyat tek basina
            for j in range(i - 1, max(i - 4, -1), -1):
                ad = satirlar[j]
                if FIYAT.match(ad):
                    continue
                if _gecerli_ad(ad, max_ad_uzunluk):
                    ekle(ad, m.group(1))
                    break
            continue

        m = SATIR_ICI.search(s)                 # durum 1: ad + fiyat ayni satirda
        if m:
            ad = s[:m.start()].strip(" .:-–—·")
            if _gecerli_ad(ad, max_ad_uzunluk):
                ekle(ad, m.group(1))
    return bulunan


def getir(url: str) -> str:
    r = subprocess.run(
        ["curl", "-sL", "--max-time", "30", "-A",
         "Mozilla/5.0 (compatible; OturalimBot/0.1)", url],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout or ""


def main(urller):
    for url in urller:
        kalemler = menu_cikar(getir(url))
        print(f"\n=== {url}")
        print(f"    kalem: {len(kalemler)}")
        for ad, f in kalemler[:10]:
            print(f"      {ad[:44]:<46} {f:>9,.2f} TL")
        if kalemler:
            fiyatlar = sorted(f for _, f in kalemler)
            print(f"    medyan kalem fiyati: {fiyatlar[len(fiyatlar) // 2]:,.2f} TL")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        ornek = """<ul><li><a>Klasik Kahvalti</a><span>499.50 &#8378;</span></li>
                   <li><a>Menemen</a><span>369,50 TL</span></li>
                   <li><a>Sepete ekle</a><span>0 TL</span></li></ul>"""
        sonuc = menu_cikar(ornek)
        assert len(sonuc) == 2, sonuc
        assert sonuc[0] == ("Klasik Kahvalti", 499.50), sonuc
        assert sonuc[1] == ("Menemen", 369.50), sonuc

        for ham, beklenen in [("1.749,50", 1749.5), ("1,749.50", 1749.5),
                              ("499.50", 499.5), ("369,50", 369.5),
                              ("5.000.000", 5000000.0), ("5.000", 5000.0),
                              ("1.234", 1234.0), ("85", 85.0)]:
            assert fiyata_cevir(ham) == beklenen, (ham, fiyata_cevir(ham), beklenen)
        print("kendi kendini kontrol: TAMAM")
    else:
        main(sys.argv[1:])
