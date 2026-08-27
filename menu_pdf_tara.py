# -*- coding: utf-8 -*-
"""PDF ve gorsel menuleri bulur; PDF'lerin metin katmanindan fiyat cikarir.

Neden gerekli: tr_menu_ozet.csv'de 2.294 site "js" diye isaretli. Playwright
ile JS'i calistirip olctuk — 20 sitelik orneklemde HICBIRINDE metin fiyati
cikmadi. Fiyatlar ya hic yayinlanmiyor, ya PDF'te, ya JPEG fotografta.

Bu betik o PDF/gorselleri bulur. PDF metin katmani varsa fiyat oradan
API'siz cikar (PyMuPDF). Metin katmani yoksa veya menu bir fotografsa
"ocr gerekli" diye isaretlenir — o asama ayri bir karar.

    python menu_pdf_tara.py pilot     ilk 50 site (verimi olcmek icin)
    python menu_pdf_tara.py tam       hepsi, kaldigi yerden devam eder
    python menu_pdf_tara.py ozet      birikmis bulgunun dokumu
    python menu_pdf_tara.py test      kendini kontrol

Sertifika dogrulamasi acik gelir. Sertifikasi bozuk sitelerden de indirmek
gerekiyorsa --guvensiz eklenir; indirilen icerik fiyat verisine donustugu
icin bu bayrak sessiz degil, uyararak calisir.

Yeniden calistirilabilir: islenen siteler menu_pdf_bulgu.csv'den okunup
atlanir, uzun tarama yarida kesilse de bastan baslamaz.
"""
import asyncio
import csv
import datetime
import io
import os
import re
import sys

import fitz  # PyMuPDF
import httpx
from playwright.async_api import async_playwright

from fiyat_analiz import kategorile

KAYNAK = "tr_menu_ozet.csv"
BULGU = "menu_pdf_bulgu.csv"
KALEM = "menu_pdf_kalem.csv"
SOSYAL = "menu_site_sosyal.csv"

# ISLETMENIN KENDI SITESINDE KENDI VERDIGI SOSYAL BAG.
#
# Olculdu: 35.852 mekanin 304'unde (%0,8) sosyal hesap var ve HEPSI
# Instagram -- cunku turkiye_mekanlar.csv dort sutun eklenmeden once
# uretilmis. OSM'yi yeniden cekmek o dort sutunu dolduruyor ama OSM'de
# etiket YOKSA orada da bir sey cikmiyor.
#
# Bu betik zaten her isletme sitesini gercek tarayicida aciyor. Ayni
# geciste sayfadaki sosyal baglar da toplanabiliyor: ek istek yok, ek
# kaynak yok, ve kaynak isletmenin KENDI sitesi -- kazima degil, orada
# yayimlanmis bag.
#
# Kullanici adi AYIKLANMIYOR burada: bicim kurallari app_veri.py'de
# (sosyal_adi) tek yerde duruyor ve iki yere kopyalanmasi, birinin
# gunun birinde otekinden sapmasi demekti. Burasi ham URL yaziyor.
SOSYAL_BAG = re.compile(
    r"^https?://(?:[\w.-]+\.)?"
    r"(instagram\.com|facebook\.com|fb\.com|twitter\.com|x\.com|"
    r"tiktok\.com|youtube\.com|youtu\.be)/", re.I)

# PAYLASIM/GIRIS BAGLARI DEGIL. "facebook.com/sharer/sharer.php?u=..."
# her sitede var ve bir hesap degil; alinsa her mekana ayni sahte
# hesap yazilirdi.
#
# DESEN YALNIZ YOLA BAKIYOR, TUM URL'YE DEGIL. Once tum URL'ye
# bakiyordu ve "tr-tr.facebook.com/xkafe" REDDEDILIYORDU: alan adindaki
# "//tr" desendeki "tr" locale parcasina takiliyordu. Turkce Facebook
# alt alan adi Turkiye'deki isletmelerde en sik gorulen bicim, yani
# kapi tam da yakalamasi gerekeni eliyordu.
SOSYAL_DEGIL = re.compile(
    r"^/(sharer|share|dialog|intent|login|plugins|watch|embed|hashtag|"
    r"oauth|profile\.php)\b|[?&]u=", re.I)

ESZAMANLI = 6          # ayni anda acik sekme
SAYFA_ZAMAN = 20000    # ms
INDIRME_ZAMAN = 25     # s
PDF_AZAMI = 15 * 1024 * 1024

# ROBOTS.TXT KAPISI. Bu betik siteyi TAM olarak calistiriyor (betikler,
# istekler, cerezler) ve menu sayfasina gecip PDF/gorsel indiriyor --
# duz bir HTML istegine gore cok daha agir bir ziyaret. Kapinin
# olmamasi bir eksiklikti.
#
# Alan adi basina BIR kez okunuyor ve sonuc onbelleklenip "izin yok"
# diyen site ATLANIYOR; atlandigi BULGUYA yaziliyor ("robots-yasak").
# Sessizce kirpmak, "menu bulunamadi" diye okunurdu -- oysa bakmadik.
#
# ADIMIZLA verilen yasak da geciyor: robotparser kullanici ajanini "/"
# ile bolup ilk parcayi aliyor, yani TAM UA dizgesi verilirse ad
# "mozilla" olur ve CebimdeBot'a konan yasak kacar.
BOT_ADI = "CebimdeBot"
_robot_onbellek = {}


def robots_izin(taban, getir=None):
    """robots.txt bu siteyi taramaya izin veriyor mu?

    Okunamazsa IZIN VAR sayiliyor: robots.txt yoklugu standartta
    "kisitlama yok" demek, yoklugu yasak saymak butun webi kapatirdi.
    """
    import urllib.robotparser
    if taban in _robot_onbellek:
        return _robot_onbellek[taban]
    izin = True
    try:
        ham = (getir or _robots_getir)(taban.rstrip("/") + "/robots.txt")
        if ham:
            ayrac = urllib.robotparser.RobotFileParser()
            ayrac.parse(ham.splitlines())
            izin = ayrac.can_fetch(BOT_ADI, taban)
    except Exception:
        izin = True
    _robot_onbellek[taban] = izin
    return izin


def _robots_getir(url):
    import subprocess
    r = subprocess.run(["curl", "-sL", "--max-time", "10", url],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout or ""


MENU_BAGI = re.compile(r"men[uü]|fiyat|sipari", re.I)
MENU_DOSYASI = re.compile(r"men[uü]|fiyat|katalog|liste", re.I)
GORSEL_UZANTI = re.compile(r"\.(jpe?g|png|webp)(\?|$)", re.I)

# "Adana Kebap ......... 450,00" / "Adana Kebap 450 TL"
#
# Sayinin fiyat oldugunun KANITI aranir: ya para birimi (TL/₺) ya da nokta
# dolgusu. Kanit sarti yokken sarap listesindeki yil fiyat sanildi —
# olculen vaka: "Suvla Reserve / Roussanne Marsanne / Gelibolu /2022"
# satirindan 2022 TL cikti, gercek fiyat (6040 tl) ayri satirdaydi.
# Sart eklenince 3 gercek menude 240 kalemin 239'u korundu, yalniz o
# uydurma kalem atildi.
KALEM_SATIRI = re.compile(
    r"^\s*(?P<ad>[^\d\n]{3,60}?)\s*"        # urun adi: rakam icermez
    # Nokta dolgusu iki bicimde geliyor: "......" ve ". . . . . ."
    # Sakhalin menusu ikincisini kullaniyor; bitisik nokta arayan desen
    # o menunun 84 kaleminin hepsini kaciriyordu.
    r"(?:(?P<dolgu>[.·…](?:[ ]?[.·…]){1,400})\s*)?"
    # Fiyat: "3 230" (bosluklu binlik), "1.190", "450,00", "140"
    r"(?P<fiyat>\d{1,3}(?:[ ]\d{3})+|\d{1,4}(?:[.,]\d{1,2})?)"
    r"\s*(?P<para>TL|₺|tl)?\s*$"
)
TABAN, TAVAN = 30.0, 5000.0
YIL_ALT, YIL_UST = 1900, 2035   # bu araliktaki kanitsiz sayi sarap yilidir


def _sayi(s):
    """Menu fiyatini sayiya cevirir.

    Uc bicim var ve karistirilirsa fiyat 100 kat sapiyor:
      "3 230"  -> 3230.0   bosluklu binlik ayraci (Sakhalin)
      "1.190"  -> 1190.0   noktali binlik ayraci
      "450,00" ->  450.0   ondalik
    """
    s = s.strip()
    if " " in s:
        return float(s.replace(" ", ""))
    if re.fullmatch(r"\d{1,3}[.,]\d{3}", s):
        return float(s.replace(".", "").replace(",", ""))
    return float(s.replace(",", "."))


def kalem_ayikla(metin):
    """PDF metninden (ad, fiyat) ciftleri. Uydurma yok: ikisi de sayfada yazar."""
    cikan = []
    for satir in metin.splitlines():
        satir = satir.replace("\xa0", " ").strip()
        e = KALEM_SATIRI.match(satir)
        if not e:
            continue
        # "=" de ayirici olarak kullaniliyor: "ADANA KEBAP = 740 TL"
        ad = e.group("ad").strip(" .·…-:=–—")
        if len(ad) < 3 or not re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]{3}", ad):
            continue
        try:
            fiyat = _sayi(e.group("fiyat"))
        except ValueError:
            continue
        # Yil mi fiyat mi? Para birimi veya nokta dolgusu varsa fiyattir.
        # Ikisi de yoksa ve deger bir yila benziyorsa alinmaz.
        kanit = e.group("para") or e.group("dolgu")
        if not kanit and YIL_ALT <= fiyat <= YIL_UST:
            continue
        if TABAN <= fiyat <= TAVAN:
            cikan.append((ad, fiyat))
    return cikan


MENU_SAYILIR = 3   # bu kadar yiyecek kalemi tanimlanmazsa PDF menu degildir


def menu_mu(kalemler):
    """PDF gercekten menu mu, yoksa kurumsal belge mi?

    Pilotta bulunan PDF'lerin hepsi surdurulebilirlik raporu ve Modern
    Slavery Statement cikti; "FOR FISCAL YEAR 2025" bir menu kalemi gibi
    ayristi. Tek guvenilir sinama: cikan adlarin yiyecek/icecek olarak
    siniflanip siniflanmadigi.
    """
    yiyecek = sum(1 for ad, _ in kalemler if kategorile(ad)[0])
    return yiyecek >= MENU_SAYILIR


def pdf_metni(veri):
    with fitz.open(stream=veri, filetype="pdf") as d:
        return "\n".join(s.get_text() for s in d)


def mutlak(kok, yol):
    if not yol:
        return None
    if yol.startswith("http"):
        return yol
    if yol.startswith("//"):
        return "https:" + yol
    return kok.rstrip("/") + "/" + yol.lstrip("/")


async def site_isle(tarayici, istemci, satir, kilit):
    """Tek site: menu sayfasini bul, PDF/gorsel topla, PDF'ten fiyat cikar."""
    site = satir["website"]
    bulgu = {"mekan": satir["mekan"], "il": satir.get("il", ""), "website": site,
             "tur": "", "kaynak_url": "", "kalem_sayisi": 0, "not": ""}
    kalemler = []
    sosyal = []
    sayfa = None
    if not robots_izin(site):
        bulgu["tur"] = "robots-yasak"
        return bulgu, kalemler
    try:
        sayfa = await tarayici.new_page()
        sayfa.set_default_timeout(SAYFA_ZAMAN)
        await sayfa.goto(site, wait_until="domcontentloaded")
        await sayfa.wait_for_timeout(1500)

        # menu sayfasina gecmeyi dene
        baglar = await sayfa.eval_on_selector_all(
            "a", "els => els.slice(0,150).map(a => [a.innerText.trim(), a.getAttribute('href')])")
        menu_baglari = [h for t, h in baglar
                        if h and not h.startswith("javascript") and MENU_BAGI.search(t or "")]
        if menu_baglari:
            hedef = mutlak(site, menu_baglari[0])
            try:
                await sayfa.goto(hedef, wait_until="domcontentloaded")
                await sayfa.wait_for_timeout(1500)
            except Exception:
                pass

        # 1) Once sayfanin KENDI metni. QR menu platformlari (allzinapp,
        #    guestservice.app, cciqrmenum) menuyu HTML olarak basiyor ve eski
        #    kaziyici JS calistirmadigi icin bunlari hic okuyamamisti.
        #    Metinden gelen fiyat en guvenilir kaynak: model araya girmiyor.
        try:
            sayfa_metni = await sayfa.inner_text("body")
        except Exception:
            sayfa_metni = ""
        metin_kalemleri = kalem_ayikla(sayfa_metni)
        if metin_kalemleri and menu_mu(metin_kalemleri):
            bulgu.update(tur="sayfa-metin", kaynak_url=sayfa.url,
                         kalem_sayisi=len(metin_kalemleri))
            kalemler = metin_kalemleri

        baglar = await sayfa.eval_on_selector_all(
            "a", "els => els.map(a => a.getAttribute('href'))")
        # Sosyal baglar ayni gecisten. Mekan basina platform basina BIR
        # tane: bir sitede ayni hesaba ustte ve altta iki bag olmasi
        # kural, ve ikisini de yazmak sayiyi sisirirdi.
        gorulen = set()
        for h in baglar:
            m_bag = mutlak(site, h) if h else ""
            k = SOSYAL_BAG.match(m_bag)
            if not k or SOSYAL_DEGIL.search("/" + m_bag[k.end():]):
                continue
            alan = k.group(1).lower()
            if alan in gorulen:
                continue
            gorulen.add(alan)
            sosyal.append([satir["mekan"], satir.get("il", ""), site, alan, m_bag])

        pdfler = [mutlak(site, h) for h in baglar
                  if h and h.lower().split("?")[0].endswith(".pdf")]
        gorseller = await sayfa.eval_on_selector_all(
            "img", "els => els.map(i => i.getAttribute('src'))")
        menu_gorselleri = [mutlak(site, s) for s in gorseller
                           if s and GORSEL_UZANTI.search(s) and MENU_DOSYASI.search(s)]

        if kalemler:
            pass                      # sayfa metninden zaten cikti
        elif pdfler:
            # menu benzeri ad varsa onu tercih et
            sirali = sorted(pdfler, key=lambda u: 0 if MENU_DOSYASI.search(u) else 1)
            for url in sirali[:2]:
                try:
                    y = await istemci.get(url, timeout=INDIRME_ZAMAN, follow_redirects=True)
                    if y.status_code != 200 or len(y.content) > PDF_AZAMI:
                        continue
                    bulunan = kalem_ayikla(pdf_metni(y.content))
                except Exception as e:
                    bulgu["not"] = "pdf hata: %s" % str(e)[:40]
                    continue
                if bulunan and menu_mu(bulunan):
                    bulgu.update(tur="pdf-metin", kaynak_url=url, kalem_sayisi=len(bulunan))
                    kalemler = bulunan
                    break
                # metin cikti ama yiyecek yok -> kurumsal belge; metin hic
                # cikmadiysa taranmis PDF, OCR gerekir
                bulgu.update(tur="pdf-menu-degil" if bulunan else "pdf-ocr-gerekli",
                             kaynak_url=url)
        elif menu_gorselleri:
            bulgu.update(tur="gorsel-ocr-gerekli", kaynak_url=menu_gorselleri[0])
        else:
            bulgu["tur"] = "menu bulunamadi"
    except Exception as e:
        bulgu["tur"] = "erisilemedi"
        bulgu["not"] = str(e)[:60]
    finally:
        if sayfa:
            try:
                await sayfa.close()
            except Exception:
                pass

    async with kilit:
        yaz_bulgu(bulgu)
        if kalemler:
            yaz_kalem(satir, bulgu["kaynak_url"], kalemler)
        if sosyal:
            yaz_sosyal(sosyal)
    return bulgu


def _ekle(yol, basliklar, satirlar):
    yeni = not os.path.exists(yol)
    with io.open(yol, "a", encoding="utf-8", newline="") as f:
        y = csv.writer(f)
        if yeni:
            y.writerow(basliklar)
        y.writerows(satirlar)


def yaz_bulgu(b):
    _ekle(BULGU, ["mekan", "il", "website", "tur", "kaynak_url", "kalem_sayisi", "not"],
          [[b["mekan"], b["il"], b["website"], b["tur"], b["kaynak_url"],
            b["kalem_sayisi"], b["not"]]])


def yaz_kalem(satir, url, kalemler):
    # tarih: fiyatin derlendigi gun. Bkz. menu_topla.ALANLAR.
    _ekle(KALEM, ["mekan", "il", "website", "kaynak_url", "kalem", "fiyat", "tarih"],
          [[satir["mekan"], satir.get("il", ""), satir["website"], url, ad, f,
            datetime.date.today().isoformat()]
           for ad, f in kalemler])


def yaz_sosyal(satirlar):
    _ekle(SOSYAL, ["mekan", "il", "website", "alan", "url"], satirlar)


def islenmis():
    if not os.path.exists(BULGU):
        return set()
    with io.open(BULGU, encoding="utf-8") as f:
        return {r["website"] for r in csv.DictReader(f)}


async def calistir(satirlar, guvensiz=False):
    kilit = asyncio.Lock()
    sinir = asyncio.Semaphore(ESZAMANLI)
    sayac = {"n": 0}

    async with async_playwright() as p:
        tarayici = await p.chromium.launch()
        # Dogrulama varsayilan olarak ACIK. Onceden verify=False sabitti:
        # buradan inen PDF ve gorseller dogrudan fiyat verisine donusuyor,
        # yani araya giren biri menuyu degistirebilirdi. Sertifikasi
        # gecmis siteler icin --guvensiz var ama sessiz degil.
        async with httpx.AsyncClient(verify=not guvensiz) as istemci:
            async def tek(s):
                async with sinir:
                    b = await site_isle(tarayici, istemci, s, kilit)
                    sayac["n"] += 1
                    print("[%4d/%d] %-28s %-20s %s"
                          % (sayac["n"], len(satirlar), s["mekan"][:28],
                             b["tur"], b["kalem_sayisi"] or ""), flush=True)
            await asyncio.gather(*(tek(s) for s in satirlar))
        await tarayici.close()


def kendini_kontrol_et():
    ornek = """MENÜMÜZ
Adana Kebap ................ 450
Kuşbaşı Kebap  520,00 TL
İçecekler
Ayran 60
Sayfa 2
Tel: 0322 233 60 60
Çay .... 25
2024
"""
    c = dict(kalem_ayikla(ornek))
    assert c.get("Adana Kebap") == 450.0, c
    assert c.get("Kuşbaşı Kebap") == 520.0, c
    assert c.get("Ayran") == 60.0, c
    # Gercek vaka: sarap listesindeki yil fiyat sanilmamali. Para birimi de
    # nokta dolgusu da yok -> kanit yok -> alinmaz.
    assert not kalem_ayikla("Suvla Reserve / Roussanne Marsanne / Gelibolu /2022"), \
        "sarap yili fiyat sayildi"
    # ayni satir "tl" ile bitiyorsa gercekten fiyattir
    assert kalem_ayikla("Suvla / Viognier / Gelibolu 3100 tl"), "gercek fiyat reddedildi"

    # Sakhalin bicimi: aralikli nokta dolgusu + bosluklu binlik ayraci
    s = dict(kalem_ayikla(
        "Somonlu tartar ve mango  . . . . . . . . . . . . . . . 970\n"
        "Sakhalin tartar cesitleri: orkinos, somon . . . . . . . 3 230\n"))
    assert s.get("Somonlu tartar ve mango") == 970.0, s
    assert s.get("Sakhalin tartar cesitleri: orkinos, somon") == 3230.0, \
        "bosluklu binlik yanlis okundu: %s" % s
    # binlik ve ondalik ayraci karistirilmamali
    assert _sayi("1.190") == 1190.0 and _sayi("450,00") == 450.0 and _sayi("3 230") == 3230.0

    # Cukuraga bicimi: "=" ayirici, urun adinda kalmamali
    e = dict(kalem_ayikla("ADANA KEBAP = 740 TL\nİÇLİ KÖFTE = 140 TL"))
    assert e == {"ADANA KEBAP": 740.0, "İÇLİ KÖFTE": 140.0}, e
    assert "Çay" not in c, "25 TL taban altinda, alinmamali"
    assert "Sayfa" not in c, c
    assert not any(a.startswith("Tel") for a in c), c
    assert mutlak("https://a.com", "/menu.pdf") == "https://a.com/menu.pdf"
    assert mutlak("https://a.com", "https://b.com/m.pdf") == "https://b.com/m.pdf"

    # menu_mu: pilotta gelen gercek cop kurumsal belge reddedilmeli
    kurumsal = [("FOR FISCAL YEAR", 2025.0), ("RCP", 45.0), ("Table", 79.0),
                ("TSRS Uygunluk Beyanı TSRS M.d", 72.0), ("Projeksiyonları,", 2020.0)]
    assert not menu_mu(kurumsal), "kurumsal belge menu sayildi"
    assert menu_mu(list(c.items())), "gercek menu reddedildi"
    # ROBOTS.TXT KAPISI. Betik siteyi tam calistirip menu sayfasina
    # geciyor; kapinin varligi kadar DOGRU calistigi da sinaniyor.
    _robot_onbellek.clear()
    assert not robots_izin("https://a.test",
                           getir=lambda u: "User-agent: *\nDisallow: /\n"), \
        "robots.txt 'Disallow: /' dedigi halde taraniyor"
    _robot_onbellek.clear()
    assert robots_izin("https://b.test", getir=lambda u: ""), \
        "robots.txt YOKKEN tarama engellendi (yokluk kisitlama degil)"
    _robot_onbellek.clear()
    # TAM UA dizgesi verilseydi robotparser adi "mozilla" diye okur ve
    # bu yasak KACARDI.
    assert not robots_izin("https://c.test",
                           getir=lambda u: "User-agent: CebimdeBot\nDisallow: /\n"), \
        "bizi ADIMIZLA yasaklayan robots.txt gecersiz sayildi"
    _robot_onbellek.clear()

    print("kontrol gecti: %d kalem ayiklandi, cop elendi, kurumsal PDF "
          "reddedildi, robots.txt kapisi calisiyor" % len(c))
    return True


def ozetle():
    import collections
    if not os.path.exists(BULGU):
        print("henuz bulgu yok")
        return
    with io.open(BULGU, encoding="utf-8") as f:
        satir = list(csv.DictReader(f))
    print("\n=== OZET (%d site) ===" % len(satir))
    for k, v in collections.Counter(s["tur"] for s in satir).most_common():
        print("  %-22s %4d  (%%%d)" % (k, v, round(100 * v / len(satir))))
    print("  toplam cikarilan kalem: %d"
          % sum(int(s["kalem_sayisi"] or 0) for s in satir))


def liste_kaynagi(yol="taranmamis.txt"):
    """OSM'de sitesi olan ama hic denenmemis mekanlar.

    tr_menu_ozet.csv 1.321 siteyi kapsiyordu; OSM'de 2.024 tekil site var.
    Aradaki 703 site hic denenmedi ve icinde QR menu platformlari cikti.
    """
    if not os.path.exists(yol):
        sys.exit("%s yok" % yol)
    with io.open(yol, encoding="utf-8") as f:
        adresler = [s.strip() for s in f if s.strip()]
    ad = {}
    with io.open("turkiye_mekanlar.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            u = r.get("website", "").strip()
            if u:
                ad[u] = (r["ad"], r["il"])
    return [{"mekan": ad.get(u, (u, ""))[0], "il": ad.get(u, (u, ""))[1],
             "website": u, "kaynak": "js"} for u in adresler]


def main(kip, guvensiz=False):
    if kip == "liste":
        hepsi = liste_kaynagi()
    else:
        with io.open(KAYNAK, encoding="utf-8-sig") as f:
            hepsi = [r for r in csv.DictReader(f) if r["kaynak"] == "js"]
    atla = islenmis()
    kalan = [r for r in hepsi if r["website"] not in atla]
    if kip == "pilot":
        kalan = kalan[:200]
    print("js site: %d · islenmis: %d · bu turda: %d" % (len(hepsi), len(atla), len(kalan)))
    if not kalan:
        print("islenecek site yok")
        return
    asyncio.run(calistir(kalan, guvensiz))
    ozetle()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--guvensiz"]
    guvensiz = "--guvensiz" in sys.argv[1:]
    kip = args[0] if args else "pilot"
    if kip == "test":
        sys.exit(0 if kendini_kontrol_et() else 1)
    elif kip == "ozet":
        ozetle()
    else:
        if guvensiz:
            print("UYARI: sertifika dogrulamasi KAPALI. Inen menu icerigi "
                  "degistirilmis olabilir; cikan fiyatlara guvenme.")
        main(kip, guvensiz)
