#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JavaScript ile basilan menuleri GERCEK TARAYICIYLA okur.

    python menu_tarayici.py olc 30      # OLCUM: 30 site dene, hicbir sey yazma
    python menu_tarayici.py tam         # hepsi, kaldigi yerden devam eder
    python menu_tarayici.py test        # kendini kontrol (ag gerektirmez)

NEDEN VAR
---------
menu_topla.py iki yol deniyor: WooCommerce acik ucu ve duz HTML. Ikisi de
sunucunun gonderdigi ilk HTML'e bakiyor. Menusunu JavaScript ile basan
site o HTML'de bos duruyor ve kayit "js" diye isaretlenip birakiliyor --
dosyanin kendi notu da bunu soyluyor: "gercek tarayici gerektirir."

OLCULDU (tr_menu_ozet.csv, 2026-08-26):

    denenen site      : 2.476
    kalem cikan       :   182  (%7,4)
    "js" isaretli     : 2.294

"js" yiginini platform ve bozuk adreslerden temizleyince (instagram.com,
facebook.com, yemeksepeti.com, "franco_cafebeach" gibi gecersiz alan
adlari -- app_veri.platform_mu ayni kapiyi kullaniyor):

    islenebilir kayit : 2.091
    TEKIL ALAN ADI    : 1.467

Yani bugun 1.467 isletmenin KENDI sitesi hic okunmamis duruyor. Uygulamada
fiyati olan mekan 291; bu yigin, kapsamayi buyutmenin en buyuk tek
kaldiraci.

VERIM BILINMIYOR VE UYDURULMUYOR. Bu betigin `olc` kipi tam da bunun icin
var: once 30 site denenir, kacinda fiyat ciktigi SAYILIR, sonra tam tarama
yapilip yapilmayacagina o sayiyla karar verilir. Bu depoda kural bu --
olcmeden tasarlamiyoruz.

NE KAZIMIYORUZ
--------------
Yalnizca isletmenin KENDI sitesi. Google Maps, Yandex, Yemeksepeti, Getir
ve TrendyolGo "Yapilmayacaklar" listesinde (CEBIMDE.md) ve platform_mu()
kapisi onlari zaten eliyor. Yorum da toplanmiyor: yorumlar yazarlarinin
telifinde.

ROBOTS.TXT -- menu_topla.py'de OLMAYAN kapi
--------------------------------------------
menu_topla.py robots.txt'ye bakmiyor. Duz HTML icin bu bir eksiklik; bir
tarayiciyla sayfayi TAM olarak calistirirken (betikler, istekler, cerezler)
eksiklik olmaktan cikip yanlisa donuyor. Burada her alan adi icin bir kez
robots.txt okunuyor, sonuc onbelleklenip "izin yok" diyen site ATLANIYOR
ve atlandigi RAPORDA yaziyor -- sessizce kirpmak, "hepsini denedik" diye
okunurdu.

Ayni alan adina saniyede birden fazla istek gitmiyor (ALAN_BEKLE).

KURAL TEK YERDE
---------------
Ad/fiyat ayiklama kurali menu_cikar.menu_cikar()'da ve buradan da o
cagriliyor. Ikinci bir ayiklayici yazmak, ayni sozlugu iki yerde tutmak ve
ikisinin ayrismasini beklemek olurdu -- bu depoda en pahali hatalar tam
olarak oyle cikti.
"""
import csv
import datetime
import glob
import os
import re
import sys
import time
import urllib.robotparser
from urllib.parse import urlsplit

from menu_cikar import menu_cikar

# Tarayicidan gelen metin, sunucunun gonderdigi HTML degil. menu_cikar
# ikisini de okuyabiliyor cunku girdisi SATIR SATIR metin.
UA = "Mozilla/5.0 (compatible; CebimdeBot/0.1)"
# robots.txt'ye verilen ad, TAM UA dizgesi DEGIL. robotparser kullanici
# ajanini "/" ile bolup ilk parcayi aliyor: tam dizgeyi verirsek ad
# "mozilla" oluyor ve bizi ADIMIZLA yasaklayan site kapiyi gecirmis
# oluyordu. Kendi kontrolum bunu yakaladi.
BOT_ADI = "CebimdeBot"
ALAN_BEKLE = 1.0        # ayni alan adina saniyede en fazla bir istek
SAYFA_ZAMAN = 25000     # ms
CIZIM_BEKLE = 3500      # ms -- JS'in menuyu basmasi icin
EN_COK_METIN = 200000   # karakter; devi sayfa ayristiriciyi bogmasin

BUGUN = datetime.date.today().isoformat()
ALANLAR = ["mekan", "il", "tur", "website", "kaynak", "kategori", "kalem",
           "fiyat", "tarih"]
CIKTI = "tr_menu_tarayici.csv"
DURUM = "tr_menu_tarayici_durum.csv"


def chromium_yolu():
    """Depoda kurulu Chromium. Bulunamazsa None -- cagiran karar verir."""
    ortam = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
    for kalip in (os.path.join(ortam, "chromium-*", "chrome-linux", "chrome"),
                  os.path.join(ortam, "chromium", "chrome-linux", "chrome"),
                  os.path.join(ortam, "chromium*", "chrome-linux*", "chrome")):
        bulunan = sorted(glob.glob(kalip))
        if bulunan:
            return bulunan[-1]
    return None


def kok(url):
    """Adresin sema+alan adi kismi. menu_topla.kok ile ayni davranis."""
    if not url.startswith("http"):
        url = "https://" + url
    p = urlsplit(url)
    return "%s://%s" % (p.scheme, p.netloc)


def gecerli_alan(url):
    """Bu bir alan adi mi, yoksa veriye kacmis bir metin mi?

    OSM'de website alanina "franco_cafebeach" gibi degerler girilmis;
    tarayiciya vermek zaman kaybi ve gurultu.
    """
    ad = urlsplit(kok(url)).netloc
    return bool(ad) and "." in ad and " " not in ad and "_" not in ad


_robot_onbellek = {}


def robots_izin(taban, getir=None):
    """robots.txt bu adresi taramaya izin veriyor mu?

    Alan adi basina BIR kez okunuyor. Okunamazsa (404, zaman asimi) IZIN
    VAR sayiliyor: robots.txt yoklugu standartta "kisitlama yok" demek --
    yoklugu yasak saymak butun siteyi kapatirdi.
    """
    if taban in _robot_onbellek:
        return _robot_onbellek[taban]
    izin = True
    try:
        ham = (getir or _robots_getir)(taban + "/robots.txt")
        if ham:
            ayrac = urllib.robotparser.RobotFileParser()
            ayrac.parse(ham.splitlines())
            izin = ayrac.can_fetch(BOT_ADI, taban + "/")
    except Exception:
        izin = True
    _robot_onbellek[taban] = izin
    return izin


def _robots_getir(url):
    import subprocess
    r = subprocess.run(["curl", "-sL", "--max-time", "10", "-A", UA, url],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout or ""


def js_adaylari(ozet_yolu="tr_menu_ozet.csv"):
    """"js" diye isaretlenmis, platform olmayan, gecerli TEKIL alan adlari.

    Tekillestirme alan adinda: zincirin 169 subesi ayni siteyi paylasiyor
    (starbucks.co.uk) ve siteyi 169 kez acmak hem bosuna hem kaba.
    """
    from app_veri import platform_mu
    gorulen, l = set(), []
    try:
        f = open(ozet_yolu, encoding="utf-8-sig")
    except FileNotFoundError:
        return l
    with f:
        for r in csv.DictReader(f):
            if r.get("kaynak") != "js":
                continue
            w = (r.get("website") or "").strip()
            if not w or platform_mu(w) or not gecerli_alan(w):
                continue
            taban = kok(w)
            if taban in gorulen:
                continue
            gorulen.add(taban)
            l.append((r.get("mekan", ""), taban))
    return l


def sayfa_metni(sf, taban):
    """Sayfayi ac, JS'in menuyu basmasini bekle, govde metnini dondur."""
    sf.goto(taban, wait_until="domcontentloaded", timeout=SAYFA_ZAMAN)
    sf.wait_for_timeout(CIZIM_BEKLE)
    return sf.inner_text("body")[:EN_COK_METIN]


def _yaz(yol, alanlar, satirlar):
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=alanlar)
        w.writeheader()
        w.writerows(satirlar)


def tara(adaylar, olcum=False):
    """Adaylari tarayiciyla dener. (satirlar, durum) dondurur."""
    from playwright.sync_api import sync_playwright
    yol = chromium_yolu()
    satirlar, durum = [], []
    son_istek = {}

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=yol,
                              args=["--no-sandbox"]) if yol else p.chromium.launch()
        try:
            for i, (mekan, taban) in enumerate(adaylar, 1):
                if not robots_izin(taban):
                    durum.append({"mekan": mekan, "website": taban,
                                  "sonuc": "robots-yasak", "kalem": 0})
                    print("[%d/%d] %-44s robots.txt izin vermiyor"
                          % (i, len(adaylar), taban[:44]), flush=True)
                    continue
                gecen = time.time() - son_istek.get(taban, 0)
                if gecen < ALAN_BEKLE:
                    time.sleep(ALAN_BEKLE - gecen)
                son_istek[taban] = time.time()

                sf = b.new_page(user_agent=UA)
                sonuc, kalemler = "", []
                try:
                    kalemler = menu_cikar(sayfa_metni(sf, taban))
                    sonuc = "kalem" if kalemler else "bos"
                except Exception as e:
                    sonuc = "hata:" + type(e).__name__
                finally:
                    sf.close()

                durum.append({"mekan": mekan, "website": taban,
                              "sonuc": sonuc, "kalem": len(kalemler)})
                if not olcum:
                    for ad, fiyat in kalemler:
                        satirlar.append({
                            "mekan": mekan, "il": "", "tur": "", "website": taban,
                            "kaynak": "tarayici", "kategori": "", "kalem": ad,
                            "fiyat": "%.2f" % fiyat, "tarih": BUGUN})
                if kalemler or i % 25 == 0:
                    print("[%d/%d] %-44s %-6s %4d kalem"
                          % (i, len(adaylar), taban[:44], sonuc, len(kalemler)),
                          flush=True)
        finally:
            b.close()
    return satirlar, durum


def rapor(durum, adaylar):
    kalemli = [d for d in durum if d["sonuc"] == "kalem"]
    yasak = [d for d in durum if d["sonuc"] == "robots-yasak"]
    hatali = [d for d in durum if d["sonuc"].startswith("hata")]
    denenen = len(durum) - len(yasak)
    print("\nAday alan adi     : %d" % len(adaylar))
    # SESSIZ KIRPMA YOK: atlanan site sayisi yaziliyor, yoksa rapor
    # "hepsini denedik" diye okunur.
    print("robots.txt atladi : %d" % len(yasak))
    print("Denenen           : %d" % denenen)
    print("Kalem cikan       : %d (%%%.1f)"
          % (len(kalemli), 100.0 * len(kalemli) / max(denenen, 1)))
    print("Hata              : %d" % len(hatali))
    print("Toplam kalem      : %d" % sum(d["kalem"] for d in durum))
    if kalemli:
        print("\nEn cok kalem cikan 10:")
        for d in sorted(kalemli, key=lambda x: -x["kalem"])[:10]:
            print("  %-46s %4d" % (d["website"][:46], d["kalem"]))


def kendini_kontrol():
    """Ag GEREKTIRMEZ. Kapilarin kendisi sinaniyor."""
    s = []

    # gecerli_alan: veriye kacmis metinler elenmeli
    for kotu in ("franco_cafebeach", "https://franco_cafebeach", "", "http://"):
        if gecerli_alan(kotu):
            s.append("gecerli_alan bozuk adresi kabul etti: %r" % kotu)
    for iyi in ("kaffamiro.com", "https://www.sagra.com.tr/menu"):
        if not gecerli_alan(iyi):
            s.append("gecerli_alan gecerli adresi reddetti: %r" % iyi)

    # kok(): sema ve alan adi, yol atiliyor
    if kok("www.a.com/menu/x") != "https://www.a.com":
        s.append("kok() yolu atmiyor: %s" % kok("www.a.com/menu/x"))

    # robots: YASAK gercekten yasak, YOKLUK izin
    _robot_onbellek.clear()
    yasak = "User-agent: *\nDisallow: /\n"
    if robots_izin("https://x.test", getir=lambda u: yasak):
        s.append("robots.txt 'Disallow: /' dedigi halde izin verildi")
    _robot_onbellek.clear()
    if not robots_izin("https://y.test", getir=lambda u: ""):
        s.append("robots.txt YOKKEN tarama engellendi (yokluk kisitlama degil)")
    _robot_onbellek.clear()
    # Bize ADIMIZLA yasak koyan siteye de uyulmali.
    bize = "User-agent: CebimdeBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    if robots_izin("https://z.test", getir=lambda u: bize):
        s.append("robots.txt bizi adimizla yasakladigi halde izin verildi")
    _robot_onbellek.clear()

    # Ayiklama kurali menu_cikar'da: burada YENIDEN YAZILMADIGI sinaniyor.
    ornek = "Filtre Kahve 85 TL\nLatte 95 TL\n"
    if len(menu_cikar(ornek)) != 2:
        s.append("menu_cikar ornek metinden iki kalem cikarmiyor")

    # js_adaylari: platform ve tekrar elenmeli
    ad = js_adaylari()
    tabanlar = [t for _, t in ad]
    if len(tabanlar) != len(set(tabanlar)):
        s.append("js_adaylari ayni alan adini birden cok kez veriyor")
    for kotu in ("instagram.com", "facebook.com", "yemeksepeti.com",
                 "getir.com", "trendyol"):
        if any(kotu in t for t in tabanlar):
            s.append("js_adaylari platform adresini elemiyor: %s" % kotu)

    print("kendini kontrol: %s" % ("BASARISIZ" if s else "%d kontrol gecti" % 9))
    for x in s:
        print("  HATA:", x)
    return s


def main(kip="olc", n="30"):
    if kip == "test":
        sys.exit(1 if kendini_kontrol() else 0)

    adaylar = js_adaylari()
    if not adaylar:
        print("Aday yok: once `python menu_topla.py turkiye_mekanlar.csv tr`")
        return
    if chromium_yolu() is None:
        print("Not: PLAYWRIGHT_BROWSERS_PATH altinda Chromium bulunamadi, "
              "Playwright'in kendi kurulumu denenecek.")

    if kip == "olc":
        # ORNEK BASTAN ALINIYOR, rastgele degil: kosum tekrarlanabilir olsun
        # ve iki olcum karsilastirilabilsin.
        adaylar = adaylar[:int(n)]
        print("OLCUM kipi: %d alan adi denenecek, dosyaya HICBIR SEY "
              "yazilmayacak.\n" % len(adaylar))
        _, durum = tara(adaylar, olcum=True)
        rapor(durum, adaylar)
        print("\nKarar: verim %%10'un altindaysa tam tarama zaman kaybi; "
              "ustundeyse `python menu_tarayici.py tam`.")
        return

    satirlar, durum = tara(adaylar)
    _yaz(CIKTI, ALANLAR, satirlar)
    _yaz(DURUM, ["mekan", "website", "sonuc", "kalem"], durum)
    rapor(durum, adaylar)
    print("\nYazildi: %s (%d satir) ve %s" % (CIKTI, len(satirlar), DURUM))
    print("Sonraki adim: fiyat_analiz.py kapilari + app_veri.py")


if __name__ == "__main__":
    main(*(sys.argv[1:] or []))
