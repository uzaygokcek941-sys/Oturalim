# -*- coding: utf-8 -*-
"""Tek komutla butun kontroller.

    python test.py

Uc grup:
  1. Betiklerin kendi kontrolleri  (her biri "python <betik>.py test")
  2. Tarayici kontrolleri          (node test_tarayici.mjs)
  3. Dosyalar arasi degismezler    (burada)

Ucuncu grup neden var: bu projenin en cok tekrar eden kurali "ayni kural
tek yerde dursun". Ama kural fiilen dort dosyada birden yaziyor -- ortak.js
etiketi, katki.sql CHECK'i, isletme.html eksik listesi, sahiplen.py
agirliklari. Biri digerinden ayrilirsa hicbir sey patlamiyor: isletmeye
mesajda bir sey, sayfasinda baska bir sey soyleniyor. Ancak boyle bir
kontrol yakalar.

node yoksa 2. grup ATLANIR ve atlandigi soylenir -- gectigi soylenmez.
"""
import csv
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys

import veri_bicim   # il dosyasi bicimi tek yerde

KOK = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(KOK, "app", "veri")

# Kendi kontrolu olan betikler. Hepsi "test" argumanini ayni sekilde anliyor.
BETIKLER = ["app_veri.py", "etkinlik_cek.py", "fiyat_analiz.py", "menu_cikar.py",
            "turkiye_cek.py", "foto_cek.py",
            "menu_ocr.py", "menu_pdf_tara.py", "saha.py", "sahiplen.py",
            "site_haritasi.py", "csp_uret.py", "veri_bicim.py", "kutuphane_al.py",
            "ikon_uret.py", "sw_uret.py", "assetlinks_uret.py", "og_uret.py"]

# Turkiye siniri, genis pay. Disina dusen koordinat cekimde bir sey
# kaymis demektir; haritada Atlantik'te bir nokta olarak gorunur.
SINIR = {"lat": (35.5, 42.5), "lon": (25.5, 45.0)}

sonuc = []      # (ad, gecti_mi, ayrinti)


def kayit(ad, sorunlar, atlandi=False):
    sonuc.append((ad, None if atlandi else not sorunlar, sorunlar))


def oku(*parca):
    return io.open(os.path.join(KOK, *parca), encoding="utf-8").read()


# ============================================================
# 1. Betiklerin kendi kontrolleri
# ============================================================
def betik_kontrolleri():
    for b in BETIKLER:
        if not os.path.exists(os.path.join(KOK, b)):
            kayit(b, ["dosya yok"])
            continue
        y = subprocess.run([sys.executable, b, "test"], cwd=KOK,
                           capture_output=True, text=True)
        if y.returncode != 0:
            kayit(b, [(y.stdout + y.stderr).strip()[-400:]])
        else:
            son = [x for x in y.stdout.strip().splitlines() if x.strip()]
            kayit(b, [] if son else ["cikti yok: kontrol calisti mi?"])


# ============================================================
# 2. Tarayici kontrolleri
# ============================================================
def tarayici_kontrolleri():
    ad = "test_tarayici.mjs (ortak, kesfet, isletme)"
    if not shutil.which("node"):
        kayit(ad + " — node yok, ATLANDI", [], atlandi=True)
        return
    y = subprocess.run(["node", "test_tarayici.mjs"], cwd=KOK,
                       capture_output=True, text=True)
    kayit(ad, [] if y.returncode == 0 else [(y.stdout + y.stderr).strip()[-800:]])


# ============================================================
# 3. Dosyalar arasi degismezler
# ============================================================
def alanlar_ayni_mi():
    """Katki alanlari dort dosyada birden yaziyor; dordu de ayni olmali."""
    s = []
    ortak = set(re.findall(r"(\w+):\"[^\"]+\"",
                re.search(r"const KATKI_ALAN = \{(.*?)\};", oku("app", "ortak.js"), re.S).group(1)))
    sql = set(re.search(r"alan\s+text not null check \(alan in \((.*?)\)\)",
                        oku("veritabani", "katki.sql"), re.S).group(1).replace("'", "").replace(" ", "").split(","))
    ipucu = set(re.findall(r"^\s*(\w+):\s*\"",
                re.search(r"const KATKI_IPUCU = \{(.*?)\};", oku("app", "isletme.html"), re.S).group(1), re.M))
    eksik = set(re.findall(r"^\s*(\w+):\s*\[",
                re.search(r"const EKSIK = \{(.*?)\n\};", oku("app", "isletme.html"), re.S).group(1), re.M))
    agirlik = set(re.findall(r"\"(\w+)\":",
                  re.search(r"AGIRLIK = \{(.*?)\}", oku("sahiplen.py"), re.S).group(1)))

    if ortak != sql:
        s.append("ortak.js KATKI_ALAN %s != katki.sql CHECK %s" % (sorted(ortak), sorted(sql)))
    if ortak != ipucu:
        s.append("ortak.js KATKI_ALAN %s != isletme.html KATKI_IPUCU %s" % (sorted(ortak), sorted(ipucu)))
    if not ortak <= eksik:
        s.append("katki alanlari isletme.html EKSIK listesinde yok: %s" % sorted(ortak - eksik))
    # sahiplen.py AGIRLIK ile isletme.html EKSIK ayni kumeyi tarif etmeli:
    # biri isletmeye mesaj yaziyor, oteki ayni isletmenin sayfasini.
    if agirlik != eksik:
        s.append("sahiplen.py AGIRLIK %s != isletme.html EKSIK %s" % (sorted(agirlik), sorted(eksik)))
    return s


def veri_tutarli_mi():
    s = []
    dizin = json.loads(oku("app", "veri", "index.json"))
    dosyalar = sorted(os.path.basename(y)[:2] for y in glob.glob(os.path.join(VERI, "*.json"))
                      if os.path.basename(y)[0].isdigit())
    kodlar = sorted(i["kod"] for i in dizin["iller"])
    if kodlar != dosyalar:
        s.append("index.json il kodlari dosyalarla ayni degil (%d vs %d)" % (len(kodlar), len(dosyalar)))
    if dizin["varsayilan"] not in kodlar:
        s.append("index.json varsayilan il listede yok: " + dizin["varsayilan"])

    try:
        from fiyat_analiz import yiyecek_mi
    except ImportError:
        yiyecek_mi = None

    toplam = kalem = fiyatli = 0
    # Menulu MEKAN sayisi ile ISLETME sayisi ayri seyler ve fark buyuk:
    # olculdu, 291 menulu mekan yalniz 93 farkli ad -- Domino's tek basina
    # 94 sube, Kahve Dunyasi 73. Ana sayfa ikisini de yaziyor; ikisi
    # ayrisirsa sayfa "291 mekan = 291 olcum" izlenimi verir.
    markalar = set()
    for kod in dosyalar:
        d = veri_bicim.coz(json.loads(oku("app", "veri", kod + ".json")))
        for m in d.get("mekanlar", []):
            toplam += 1
            kalem += len(m.get("menu") or [])
            if m.get("min") is not None:
                fiyatli += 1
            if m.get("menu"):
                markalar.add(" ".join((m.get("ad") or "").split()).lower())
            # Ciktida gorunur cop kalmasin. Ucu de kullaniciya AYNEN
            # gosteriliyordu: cozulmemis HTML varligi ("6&#8217;li
            # Macaron"), bas/son bosluklu ad, ve telefon alanina yazilmis
            # telefon olmayan sey ("Köfteci Yusuf").
            if m.get("ad") and m["ad"] != " ".join(m["ad"].split()):
                s.append("%s.json: ad bas/son bosluklu ya da cift bosluklu (%r)"
                         % (kod, m["ad"]))
            if m.get("tel") and len(re.sub(r"\D", "", m["tel"])) < 7:
                s.append("%s.json: %s telefonu telefon degil (%r)"
                         % (kod, m.get("ad", "")[:20], m["tel"]))
            for k in (m.get("menu") or []):
                if re.search(r"&[a-zA-Z]+;|&#\d+;", k["a"]):
                    s.append("%s.json: kalem adinda cozulmemis HTML varligi (%r)"
                             % (kod, k["a"][:40]))
                    break

            # "Menu" basligi altinda menu olmayan sey durmasin. app_veri.py
            # bunu uretimde eliyor; burasi ciktinin kendisini denetliyor,
            # cunku veri elle de duzenlenebiliyor ve JSON kalici.
            if yiyecek_mi and m.get("menu") and not any(
                    yiyecek_mi(k["a"]) for k in m["menu"]):
                s.append("%s.json: %s menusunde tek yiyecek/icecek yok (%r)"
                         % (kod, m.get("ad"), m["menu"][0]["a"][:40]))
            for alan in ("id", "ad", "tur", "lat", "lon"):
                if m.get(alan) in (None, ""):
                    s.append("%s.json: %s alani bos (%s)" % (kod, alan, m.get("id")))
                    break
            else:
                if not (SINIR["lat"][0] <= m["lat"] <= SINIR["lat"][1] and
                        SINIR["lon"][0] <= m["lon"] <= SINIR["lon"][1]):
                    s.append("%s.json: koordinat Turkiye disinda (%s: %s, %s)"
                             % (kod, m["id"], m["lat"], m["lon"]))
        if len(s) > 8:
            s = s[:8] + ["... (kirpildi)"]
            break

    # Ayni mekanin ikinci kaydi ciktida kalmasin. app_veri.py birlestiriyor;
    # burasi CIKTIYI denetliyor -- boru hatti degisirse ya da veri elle
    # duzenlenirse kopyalar sessizce geri gelmesin.
    from math import radians, sin, cos, asin, sqrt
    for kod in dosyalar:
        d = veri_bicim.coz(json.loads(oku("app", "veri", kod + ".json")))
        ada = {}
        for m in d.get("mekanlar", []):
            ada.setdefault(m["ad"].strip().casefold(), []).append(m)
        for ad, grup in ada.items():
            for i in range(len(grup)):
                for j in range(i + 1, len(grup)):
                    a, b = grup[i], grup[j]
                    dl, dn = radians(b["lat"] - a["lat"]), radians(b["lon"] - a["lon"])
                    h = (sin(dl / 2) ** 2 + cos(radians(a["lat"])) *
                         cos(radians(b["lat"])) * sin(dn / 2) ** 2)
                    if 6371000 * 2 * asin(sqrt(h)) <= 25:
                        s.append("%s.json: '%s' iki kez var, %s ve %s 25 m'den yakin"
                                 % (kod, m["ad"][:30], a["id"], b["id"]))
                        break
        if len(s) > 8:
            s = s[:8] + ["... (kirpildi)"]
            break

    v = json.loads(oku("app", "vitrin.json"))
    for anahtar, gercek in (("toplam", toplam), ("kalem", kalem),
                            ("fiyatliMekan", fiyatli), ("fiyatliMarka", len(markalar))):
        if v.get(anahtar) != gercek:
            s.append("vitrin.json %s=%s ama veride %s — vitrin_uret.py calistir"
                     % (anahtar, v.get(anahtar), gercek))

    # SAYFA METNINDEKI mekan sayisi. Elle yazilan her rakam eskiyor:
    # olculdu, kesfet.html iki yerde "36.102 mekan" diyordu, gercek 35.852.
    # Bu sayilar <meta description> ve og:description icinde, yani arama
    # sonucunda ve paylasilan baglantida gorunen ilk cumle. Kimse oraya
    # bakmiyor -- tam da bu yuzden kontrol gerekiyor.
    dogru = "{:,}".format(toplam).replace(",", ".")
    for ad in sorted(glob.glob(os.path.join(KOK, "app", "*.html"))):
        h = io.open(ad, encoding="utf-8").read()
        for yazan in set(re.findall(r"(\d{2}\.\d{3}) mekan", h)):
            if yazan.replace(".", "") != str(toplam):
                s.append("%s: metinde '%s mekan' yaziyor, gercek %s"
                         % (os.path.basename(ad), yazan, dogru))

    # BELGELER DE ESKIYOR, ve kimse onlara bakmiyor. Kural app/*.html
    # icin vardi; tasarim/decisions.md iki yerde "36.102 mekan" diyordu
    # ve CEBIMDE.md bir yerde -- yani kontrol yazildiktan SONRA bile
    # depoda uc yanlis rakam kalmisti. Ayni kural, daha genis kapi.
    #
    # DUZELTMEYI ANLATAN SATIR MUAF: "36.102 -> 35.852" yazan bir cumle
    # eski sayiyi HATA OLARAK aniyor, iddia olarak degil. Olcut, DOGRU
    # sayinin ayni satirda gecmesi.
    # PAZARLAMA.md ozellikle onemli: yatirimciya ve YC'ye SOYLENECEK
    # rakamlar orada. Eskimis bir sayiyi bir toplantida soylemek, bir
    # belgede birakmaktan pahali.
    #
    # IKINCI DESEN: menu kalemi. Icerik belgeleri "7.406 menü kalemi"
    # diyor ve bu rakam veri her buyudugunde degisiyor. Desen DAR
    # tutuldu (bir hane, nokta, uc hane) -- "12 kalemi" gibi cumleleri
    # yakalamasin diye; genis desen yanlis alarm uretir ve yanlis alarm
    # kontrolun kapatilmasiyla biter.
    #
    # SATIR SONU ARTIK KACIS DEGIL. Kontrol satir satir okuyordu; bir
    # belgede "81 ilde 35.852\nmekan var" yaziyordu, yani sayi ile
    # kelime AYRI SATIRLARDAYDI ve eskise kimse gormeyecekti. Sabotaj
    # bunu gosterdi: sayiyi bozdum, kontrol susmaya devam etti.
    # Artik metnin tamami taraniyor ve arada bosluk/madde imi
    # ("**35.852** mekan") olabiliyor. Satir numarasi konumdan
    # hesaplaniyor -- hata iletisi yerini gostermeye devam etsin diye.
    #
    # SIRA ONEMLI: yalniz "sayi sonra kelime". Tablolarda ("| Mekan |
    # 12.095 |") kelime once geliyor ve orada 12.095 ISTANBUL, toplam
    # degil. Ters sirayi da yakalamak yanlis alarm demekti.
    kalem_dogru = "{:,}".format(kalem).replace(",", ".")
    DESENLER = ((r"(\d{2}\.\d{3})\**\s+\**mekan", str(toplam), dogru, "mekan"),
                (r"(\d\.\d{3})\**\s+\**men\u00fc kalemi", str(kalem), kalem_dogru,
                 "menü kalemi"))
    for ad in ("CEBIMDE.md", "README.md", "KURULUM.md", "PLAY.md",
               "PAZARLAMA.md", "VERI_VE_GELIR.md",
               "icerik_ilk3.md", "icerik_takvim.md",
               os.path.join("tasarim", "decisions.md")):
        yol = os.path.join(KOK, ad)
        if not os.path.exists(yol):
            continue
        metin = io.open(yol, encoding="utf-8").read()
        satirlar = metin.split("\n")
        for desen, gercek, guzel, etiket in DESENLER:
            for m in re.finditer(desen, metin):
                if m.group(1).replace(".", "") == gercek:
                    continue
                no = metin.count("\n", 0, m.start()) + 1
                # DUZELTMEYI ANLATAN SATIR MUAF: "36.102 -> 35.852" eski
                # sayiyi HATA OLARAK aniyor, iddia olarak degil. Olcut,
                # DOGRU sayinin ayni satirda (ya da sarkmis cumlenin bir
                # onceki satirinda) gecmesi.
                yakin = "".join(satirlar[max(0, no - 2):no + 1])
                if guzel in yakin:
                    continue
                s.append("%s:%d: '%s %s' yaziyor, gercek %s"
                         % (ad, no, m.group(1), etiket, guzel))

    # Anasayfadaki SABIT yedekler: JS kapaliyken gorunen sayi bunlar.
    ana = oku("app", "index.html")
    for kimlik, gercek in (("d-toplam", toplam), ("d-kalem", kalem),
                           ("d-fiyatli", fiyatli), ("d-marka", len(markalar))):
        m = re.search(r'id="%s">([\d.]+)' % kimlik, ana)
        if m and m.group(1).replace(".", "") != str(gercek):
            s.append("index.html %s yedegi %s, gercek %s" % (kimlik, m.group(1), gercek))
    return s


def sayfalar_tutarli_mi():
    s = []
    for y in sorted(glob.glob(os.path.join(KOK, "app", "*.html"))):
        h = oku("app", os.path.basename(y))
        ad = os.path.basename(y)
        noindex = 'content="noindex"' in h
        og = "og:image" in h
        # Indekslenen sayfada paylasim karti olmali; noindex sayfada olmamali.
        if noindex == og:
            s.append("%s: noindex=%s ama og:image=%s" % (ad, noindex, og))

    # SRI ARTIK SAYIYLA OLCULMUYOR. Eskiden "kesfet.html'de tam iki
    # integrity olmali" deniyordu -- Leaflet'in css ve js'i icin. Leaflet
    # yerele alininca ikisi de dustu ve kontrol HAKLI olarak bagirdi;
    # ama artik sorulmasi gereken soru bu degil. SRI ayni kaynaktan gelen
    # dosya icin anlamsiz ('self' zaten dogrulanmis).
    #
    # Yeni soru: DIS bir kaynaktan yuklenen her script/link integrity
    # tasiyor mu. Sayi degil KURAL -- yarin baska bir CDN eklenirse de
    # gecerli.
    #
    # Google Fonts MUAF ve gerekcesi somut: yayimladiklari CSS'in ICERIGI
    # tarayiciya gore degisiyor (woff2 alt kumeleri, unicode-range), yani
    # sabit bir ozet tutmuyor. Ustelik <link> stylesheet icin SRI, dosya
    # gelmezse sayfayi yazi tipsiz birakir -- kirilma yeri gorunur.
    SRI_MUAF = ("fonts.googleapis.com", "fonts.gstatic.com")
    for y in sorted(glob.glob(os.path.join(KOK, "app", "*.html"))):
        ad = os.path.basename(y)
        h = oku("app", ad)
        for etiket in re.findall(r"<(?:script|link)\b[^>]*>", h):
            m = re.search(r'(?:src|href)="(https?://[^"]+)"', etiket)
            if not m:
                continue                      # goreli yol: ayni kaynak
            adres = m.group(1)
            if any(x in adres for x in SRI_MUAF):
                continue
            if "integrity=" not in etiket:
                s.append("%s: dis kaynak integrity'siz yukleniyor: %s"
                         % (ad, adres[:70]))

    # hesabim.html: sekme dugmeleri, bolum kimlikleri ve gizleme listesi
    # uc ayri yerde duruyor.
    h = oku("app", "hesabim.html")
    dugme = re.findall(r'data-bolum="(\w+)"', h)
    bolum = re.findall(r'id="bolum-(\w+)"', h)
    liste = re.search(r'\[((?:"\w+",?\s*)+)\]\.forEach\(ad =>', h)
    gizle = re.findall(r'"(\w+)"', liste.group(1)) if liste else []
    if not (dugme == bolum == gizle):
        s.append("hesabim.html sekme/bolum/gizleme ayrisiyor: %s / %s / %s"
                 % (dugme, bolum, gizle))
    return s


def _js_tara(kaynak):
    """JS govdesinden /* */ ve // yorumlarini atar; kodu birakir.

    Dizeler, sablon dizeleri ve duzenli ifadeler taniniyor: "//" bir dize
    olabiliyor (guvenliBag'da protokolsuz adres denetimi) ve /a\/\/b/
    icindeki "//" yorum degil."""
    n = len(kaynak)
    cikan = []
    i = 0
    onceki = ""            # son anlamli karakter: "/" regex mi bolme mi
    while i < n:
        c = kaynak[i]
        if kaynak[i:i + 2] == "/*":
            j = kaynak.find("*/", i + 2)
            i = n if j < 0 else j + 2
            cikan.append(" ")
            continue
        if kaynak[i:i + 2] == "//":
            j = kaynak.find("\n", i)
            i = n if j < 0 else j
            cikan.append(" ")
            continue
        if c in "'\"`":
            k = i + 1
            while k < n:
                if kaynak[k] == "\\":
                    k += 2
                    continue
                if kaynak[k] == c:
                    break
                k += 1
            cikan.append(kaynak[i:k + 1])
            onceki = c
            i = k + 1
            continue
        if c == "/" and onceki in ("", "(", ",", "=", ":", "[", "!", "&",
                                   "|", "?", "{", "}", ";", "+", "-", "*",
                                   "%", "~", "^", "<", ">"):
            k = i + 1                          # duzenli ifade govdesi
            sinif = False
            while k < n:
                if kaynak[k] == "\\":
                    k += 2
                    continue
                if kaynak[k] == "[":
                    sinif = True
                elif kaynak[k] == "]":
                    sinif = False
                elif kaynak[k] == "/" and not sinif:
                    break
                elif kaynak[k] == "\n":
                    break
                k += 1
            cikan.append(kaynak[i:k + 1])
            onceki = "/"
            i = k + 1
            continue
        cikan.append(c)
        if not c.isspace():
            onceki = c
        i += 1
    return "".join(cikan)


def _js_yorumsuz(kaynak):
    """JS/HTML kaynagindan YORUMLARI atar; kodu ve isaretlemeyi birakir.

    NEDEN AYRI BIR AYIRICI. _yorumsuz() Python icin yazildi: "#"den sonrasini
    atiyor. JS'te "#" bir yorum degil, SECICI -- el("#butce-ozet") satiri
    ikiye bolunuyordu ve satirin geri kalani (butceCumlesi cagrisi) kontrole
    hic gorunmuyordu. Ilk yazimda tam bunu yasadim: dogru yazilmis kod
    "eksik" diye raporlandi.

    Ters yonu daha tehlikeli: JS yorumlarini HIC atmayan bir kontrol,
    yorumda gecen bir isim yuzunden "bu fonksiyon cagriliyor" der. Yani
    silinmis bir cagri, onu anlatan aciklama cumlesi sayesinde gecerdi.
    Bu depoda yorumlar uzun; tam da bu tuzagin buyuk oldugu yer.

    ISARETLEME JS TARAYICISINDAN GECMIYOR. Ilk surum butun dosyayi tek
    tarayicidan geciriyordu ve "</div>" icindeki "/" bir duzenli ifade
    basi sanilip arkasindaki HTML yorumu yutuluyordu. Artik once HTML
    yorumlari ayikleniyor, sonra YALNIZ <script> govdeleri taraniyor.

    Dosyanin turune "<script gecıyor mu" diye BAKILMIYOR: ortak.js kendi
    aciklamasinda o kelimeyi kullaniyor ve dosya HTML sanilip hic
    taranmiyordu -- yani butun ortak.js yorumlari kontrole gorunur
    kaliyordu. Ayrim <!doctype ile yapiliyor."""
    if not re.match(r"\s*<!doctype", kaynak, re.I):
        return _js_tara(kaynak)     # duz .js dosyasi
    kaynak = re.sub(r"<!--.*?-->", " ", kaynak, flags=re.S)
    return re.sub(r"(<script\b[^>]*>)(.*?)(</script>)",
                  lambda m: m.group(1) + _js_tara(m.group(2)) + m.group(3),
                  kaynak, flags=re.S)


def _yorumsuz(kaynak):
    """Satir sonu # yorumlarini ve tam satir yorumlarini atar.

    Ilk surum ham metinde ariyordu ve KENDI UYARI YORUMLARINI yakaliyordu:
    yapilandirma.js'te "service_role anahtarini BURAYA ASLA YAZMA" uyarisi,
    menu_ocr.py'de "onceden verify=False'ti" aciklamasi. Yani dogru yazilmis
    kodu, dogru yazildigini anlatan cumle yuzunden hatali sayiyordu."""
    cikan = []
    for satir in kaynak.splitlines():
        kirik = satir.split("#", 1)[0]
        cikan.append(kirik)
    return "\n".join(cikan)


def _jwt_rolu(jeton):
    """JWT govdesinden rol. Cozulemezse None."""
    import base64
    try:
        govde = jeton.split(".")[1]
        govde += "=" * (-len(govde) % 4)
        return json.loads(base64.urlsafe_b64decode(govde)).get("role")
    except Exception:
        return None


def sema_tutarli_mi():
    """SQL tarafinda sessizce dusebilecek korumalar.

    Bunlar politika degil TETIKLEYICI oldugu icin sema.sql'in kendi politika
    sayaci onlari gormuyor: biri silinse dosya yine "kuruldu" der."""
    s = []
    sema = oku("veritabani", "sema.sql")
    katki = oku("veritabani", "katki.sql")

    if "function public.gunluk_gonderim_siniri()" not in sema:
        s.append("sema.sql: gunluk_gonderim_siniri() tanimi yok")
    for dosya, metin, tetik in (("sema.sql", sema, "paylasim_gunluk_sinir"),
                                ("katki.sql", katki, "katki_gunluk_sinir")):
        if ("create trigger " + tetik) not in metin:
            s.append("%s: '%s' tetikleyicisi yok — gunluk sinir o tabloda islemez" % (dosya, tetik))

    # katki.sql sema.sql'e bagli; bagimlilik kontrolu dosyanin icinde olmali
    # ki yanlis sirada calistiran kisi sessiz bir kurulum almasin.
    if "gunluk_gonderim_siniri" not in katki:
        s.append("katki.sql: sema.sql bagimliligi kontrol edilmiyor")

    # Yonetici alanini koruyan tetikleyici (sema.sql) da ayni sekilde
    # politika sayacinin disinda.
    if "create trigger profil_yonetici_koru" not in sema:
        s.append("sema.sql: profil_yonetici_koru tetikleyicisi yok")

    # Butce akrani: EKRANDA YAZAN SURE ile SORGUNUN BAKTIGI SURE ayni
    # olmali. ortak.js "son 6 ayda" diyor, akran.sql 180 gunden bakiyor.
    # Ayrisirlarsa kullaniciya yanlis bir zaman araligi soylenir ve
    # hicbir sey patlamaz -- tam olarak sessizce yanlis olan tur.
    akran = oku("veritabani", "akran.sql")
    ortak_js = oku("app", "ortak.js")
    gunler = set(re.findall(r"current_date - interval '(\d+) days'", akran))
    if gunler != {"180"}:
        s.append("akran.sql: pencere %s gun; ortak.js 'son 6 ayda' diyor"
                 % (", ".join(sorted(gunler)) or "yok"))
    if "AKRAN_GUN = 180" not in ortak_js:
        s.append("ortak.js: AKRAN_GUN 180 degil, akran.sql ile ayrisiyor")
    if "son 6 ayda" not in ortak_js:
        s.append("ortak.js: akran cumlesinde sure yazmiyor")
    # Fis esigi TEK YERDE olmali. isletme.html'de ikinci bir tanim vardi
    # ve kesfet ekrani ondan habersizdi: tek fisten tutar yayimlaniyordu.
    for dosya in ("isletme.html", "kesfet.js"):
        if re.search(r"^\s*const FIS_ESIK\s*=", oku("app", dosya), re.M):
            s.append("app/%s: FIS_ESIK ikinci kez tanimlaniyor "
                     "(kural ortak.js'te durmali)" % dosya)
    if "const FIS_ESIK = 3;" not in ortak_js:
        s.append("ortak.js: FIS_ESIK tanimi yok")

    # Sayac: dogrudan yazma yolunun kapali kaldigi.
    sayac = oku("veritabani", "sayac.sql")
    if "revoke all on table public.goruntulenme from anon" not in sayac:
        s.append("sayac.sql: goruntulenme uzerindeki GRANT geri alinmiyor")

    # katki.sql ile sahiplenme.sql ayni politikayi ("katki kendi ekler")
    # tanimliyor. Ayrisirlarsa hangi dosyanin en son calistigi davranisi
    # degistirir -- ilk yazimda tam bunu yapiyordu ve sessizdi.
    sahip = oku("veritabani", "sahiplenme.sql")
    def _politika(metin):
        i = metin.find('create policy "katki kendi ekler"')
        if i < 0:
            return None
        govde = metin[i:metin.index(";", i)]
        return re.sub(r"\s+|--[^\n]*", "", govde)
    a, b = _politika(katki), _politika(sahip)
    if a is None or b is None:
        s.append("'katki kendi ekler' politikasi iki dosyanin birinde yok")
    elif a != b:
        s.append("'katki kendi ekler' politikasi katki.sql ve sahiplenme.sql'de "
                 "farkli — hangi dosya son calisirsa davranis o olur")
    if "proname = 'sahibi_mi'" not in katki:
        s.append("katki.sql: sahibi_mi() bos govdesi 'not exists' ile korunmuyor — "
                 "tekrar calistirmak sahiplik yetkisini siler")

    # security definer + search_path: fonksiyon cagiranin degil SAHIBININ
    # yetkisiyle calisiyor. search_path sabitlenmezse, arama yolunda nesne
    # yaratabilen biri fonksiyonun cagirdigi adi kendi nesnesiyle
    # golgeleyebilir ve o yetkiyi devralir. Bugun dokuz fonksiyonun dokuzu
    # da sabitliyor; bu kontrol onuncusu icin var.
    for dosya in ("sema.sql", "katki.sql", "sayac.sql"):
        metin = oku("veritabani", dosya)
        for govde in re.split(r"\bcreate (?:or replace )?function\b", metin)[1:]:
            basi = govde.split("$$")[0]
            if "security definer" not in basi.lower():
                continue
            ad = re.match(r"\s*([\w.]+)", govde)
            if "set search_path" not in basi.lower():
                s.append("%s: %s() security definer ama search_path sabit degil"
                         % (dosya, ad.group(1) if ad else "?"))

    # Olusturulan her tabloda RLS acik olmali. Politikasiz tablo (sayac_tuz)
    # da RLS istiyor: RLS'siz tabloda politika yoklugu "herkes gorebilir"
    # demek, RLS'li tabloda "kimse goremez".
    for dosya in ("sema.sql", "katki.sql", "sayac.sql"):
        metin = oku("veritabani", dosya)
        for t in re.findall(r"create table if not exists public\.(\w+)", metin):
            # Bosluga duyarsiz: dosyada tablo adlari hizalanmis
            # ("public.favoriler   enable ..."), duz metin eslesmesi
            # bunlari kaciriyordu.
            if not re.search(r"alter\s+table\s+public\.%s\s+enable\s+row\s+level\s+security" % t,
                             metin):
                s.append("%s: %s tablosunda RLS acilmiyor" % (dosya, t))
    return s


def sahne_tutarli_mi():
    """js-sahne sinifini ekleyen her sayfa sahne.js'i de yuklemeli.

    sahne.css [data-giris] bolumlerini YALNIZ .js-sahne altinda gizliyor
    ve perdeyi sahne.js aciyor. Sinifi ekleyip betigi yuklemeyen sayfada
    icerik KALICI gizli kaliyor. Olculdu: isletme.html tam bunu
    yapiyordu ve "Bu sayfada eksik olanlar" bolumu -- sayfanin cekirdegi
    -- her ziyaretcide gorunmuyordu.

    Satir ici emniyet (2 sn sonra sinifi kaldiran setTimeout) da
    araniyor: asil koruma o, ve sessizce silinebilir."""
    s = []
    for yol in sorted(glob.glob(os.path.join(KOK, "app", "*.html"))):
        ad = os.path.basename(yol)
        metin = oku("app", ad)
        if 'classList.add("js-sahne")' not in metin:
            continue
        if "__sahneHazir" not in metin:
            s.append("%s: js-sahne ekliyor ama satir ici emniyet yok — "
                     "betik gelmezse icerik kalici gizli kalir" % ad)
        if "[data-giris" in metin and 'src="sahne.js"' not in metin:
            s.append("%s: [data-giris] var ama sahne.js yuklenmiyor — "
                     "perde hic acilmaz" % ad)
    if "window.__sahneHazir = true" not in oku("app", "sahne.js"):
        s.append("sahne.js: __sahneHazir bayragi yok — satir ici emniyet "
                 "her sayfada bosuna tetiklenir")
    return s


def yayin_basliklari_mi():
    """vercel.json gecerli mi ve guvenlik basliklari yerinde mi.

    Sessizce bozulabilecek turden: gecersiz JSON'da Vercel yapilandirmayi
    yok sayip yayina devam eder, yani baslik kaybi hicbir yerde patlamaz.

    CSP ARTIK VAR. Onceden bilerek yoktu ve gerekcesi suydu: Supabase
    adresi kuruluma gore degisiyor (yapilandirma.js gitignore'da), yani
    depoda sabit bir adres yazmak baska bir projeyle kuran kisinin
    girisini sessizce kirardi. Cozum joker: `https://*.supabase.co`.

    KARMALAR ESKIYEBILIR ve eskimesi SESSIZ: satir ici bir <script>
    degistiginde karma tutmaz, tarayici o blogu calistirmaz ve sayfa
    hatasiz gorunur. O yuzden burada guncellik de denetleniyor
    (csp_uret.py kontrol) ve ayrica test_sayfa.py butun sayfalari
    GERCEK CSP altinda aciyor (sunucu.py basligi vercel.json'dan okuyor).
    """
    s = []
    try:
        v = json.loads(oku("vercel.json"))
    except Exception as e:
        return ["vercel.json okunamadi (Vercel bunu sessizce yok sayar): %s" % e]
    if v.get("outputDirectory") != "app":
        s.append("vercel.json: outputDirectory 'app' degil")
    basliklar = {b.get("key") for grup in v.get("headers", [])
                 for b in grup.get("headers", [])}
    for gerekli in ("X-Content-Type-Options", "Referrer-Policy",
                    "X-Frame-Options", "Permissions-Policy",
                    "Content-Security-Policy"):
        if gerekli not in basliklar:
            s.append("vercel.json: %s basligi yok" % gerekli)
    y = subprocess.run([sys.executable, "csp_uret.py", "kontrol"], cwd=KOK,
                       capture_output=True, text=True)
    if y.returncode != 0:
        s.append((y.stdout + y.stderr).strip()[-200:])
    # Yerel sunucu ile yayin AYNI basligi vermeli; ayrisirlarsa CSP
    # tarayicida hic sinanmamis olur ve ilk kanit yayindaki kirik sayfa
    # olurdu.
    if 'json.loads(io.open(AYAR' not in oku("sunucu.py"):
        s.append("sunucu.py guvenlik basliklarini vercel.json'dan okumuyor")

    # supabase-js hala YER TUTUCU mu. Sessiz kalinmiyor ama HATA da degil:
    # bu bir kurulum adimi (python kutuphane_al.py), bozuk bir sey degil.
    # CSP'nin esm.sh tasiyip tasimadigi da ayni gercege bagli; ikisi
    # ayrisirsa GERCEK bir hata var: yerel dosya duruyorken CSP hala
    # CDN'e izin veriyorsa daralma yapilmamis, ya da tersi olursa giris
    # kirilmis demektir.
    try:
        lib = oku("app", "lib", "supabase-js.js")
    except Exception:
        s.append("app/lib/supabase-js.js yok; kimlik.js onu ithal ediyor")
        return s
    yer_tutucu = "esm.sh" in lib
    csp = next((h["value"] for grup in v.get("headers", [])
                if grup.get("source") == "/(.*)"
                for h in grup.get("headers", [])
                if h.get("key") == "Content-Security-Policy"), "")
    if yer_tutucu != ("esm.sh" in csp):
        s.append("CSP ile kutuphane ayrisiyor: kutuphane %s, CSP'de esm.sh %s"
                 % ("yer tutucu" if yer_tutucu else "yerel",
                    "var" if "esm.sh" in csp else "yok"))
    return s


def _kontrast(a, b):
    """WCAG kontrast orani. Iki onaltilik renk."""
    def kanal(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    def parlaklik(h):
        h = h.lstrip("#")
        r, g, bl = (kanal(int(h[i:i+2], 16) / 255) for i in (0, 2, 4))
        return 0.2126 * r + 0.7152 * g + 0.0722 * bl
    x, y = sorted((parlaklik(a), parlaklik(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def palet_okunur_mu():
    """Marka paletinin OKUNUR kaldigini olcer.

    Renk degistirmek en kolay ve en sessiz kirma yollarindan biri: sayfa
    acilir, her sey calisir, sadece yazi okunmaz. Bu kontrol degerleri
    stil.css'ten OKUYUP hesapliyor -- elle yazilmis bir liste ilk renk
    degisiminde eskirdi.

    Marka kilavuzunun ekran maketlerinde turuncu dugmenin uzerinde BEYAZ
    yazi vardi ve olculdugunde 2,61:1 cikti (esik 4,5). Renk degil
    MUREKKEP degistirildi; bu kontrol o karari tutuyor.
    """
    s = []
    css = oku("app", "stil.css")

    def belirtec(blok, ad):
        m = re.search(r"--%s:\s*(#[0-9a-fA-F]{6})" % re.escape(ad), blok)
        return m.group(1) if m else None

    # BLOKLAR SECICIYE GORE BULUNUYOR, dosya sirasina gore degil. Ilk
    # yazimda "koyu = :root{ ile @media arasi" diye okunuyordu ve acik
    # tema varsayilan yapilinca kontrol sessizce YANLIS blogu koyu
    # sanardi -- yani iki temanin da kontrastini olcuyor gorunup birini
    # iki kez olcerdi.
    def blok_al(secici):
        i = css.index(secici) + len(secici)
        return css[i:css.index("\n}", i)]

    acik = blok_al(":root{")
    koyu = blok_al(':root[data-tema="koyu"]{')

    # (blok adi, blok, zemin, metin ciftleri)
    for ad, blok in (("koyu", koyu), ("acik", acik)):
        zemin = belirtec(blok, "zemin")
        marka = belirtec(blok, "marka")
        murekkep = belirtec(blok, "vurgu-metin")
        if not (zemin and marka and murekkep):
            s.append("%s tema: --zemin/--marka/--vurgu-metin okunamadi" % ad)
            continue
        for etiket, renk, esik in (("metin", belirtec(blok, "metin"), 4.5),
                                   ("metin-2", belirtec(blok, "metin-2"), 4.5),
                                   ("vurgu", belirtec(blok, "vurgu"), 4.5),
                                   ("yesil", belirtec(blok, "yesil"), 4.5),
                                   ("kirmizi", belirtec(blok, "kirmizi"), 4.5),
                                   ("sari", belirtec(blok, "sari"), 4.5)):
            if not renk:
                s.append("%s tema: --%s yok" % (ad, etiket)); continue
            o = _kontrast(renk, zemin)
            if o < esik:
                s.append("%s tema: --%s (%s) zemin uzerinde %.2f:1, en az %.1f olmali"
                         % (ad, etiket, renk, o, esik))
        # Dugme: MARKA zemininde vurgu-metin murekkebi.
        o = _kontrast(murekkep, marka)
        if o < 4.5:
            s.append("%s tema: dugme yazisi (%s) marka zemininde (%s) %.2f:1"
                     % (ad, murekkep, marka, o))

    # Marka rengi IKI TEMADA DA ayni olmali: dugme rengi temaya gore
    # degisirse marka degisir.
    if belirtec(koyu, "marka") != belirtec(acik, "marka"):
        s.append("--marka iki temada farkli: %s / %s"
                 % (belirtec(koyu, "marka"), belirtec(acik, "marka")))

    # Iki KOYU TEMA blogu (sistem tercihi + elle secim) ayni degerleri
    # tasimali; ayrisirlarsa elle secilen tema sistemden farkli gorunur.
    # (Acik tema artik varsayilan ve tek yerde: :root)
    sistem = css[css.index("@media (prefers-color-scheme:dark)"):
                 css.index(':root[data-tema="koyu"]{')]
    ayikla = lambda b: sorted(re.findall(r"(--[\w-]+):\s*([^;]+);", b))
    a1, a2 = ayikla(sistem), ayikla(koyu)
    if a1 != a2:
        fark = set(a1) ^ set(a2)
        s.append("iki koyu tema blogu ayrisiyor: %s" % sorted(fark)[:4])

    # ACIK TEMA VARSAYILAN OLMALI: marka kilavuzunun ekran maketlerinin
    # hepsi acik. :root koyu renklere donerse uygulama maketlerden yine
    # ayrilir ve bunu hicbir sey soylemez.
    if belirtec(acik, "zemin") != "#ffffff":
        s.append("varsayilan tema acik degil: :root --zemin %s"
                 % belirtec(acik, "zemin"))

    # BIRINCIL EYLEM DUGMESI (Okyanus) uzerindeki murekkep okunmali.
    # Maketteki beyaz yazi 2,33:1 -- turuncu dugmeyle ayni hata.
    for ad, blok in (("acik", acik), ("koyu", koyu)):
        t, tm = belirtec(blok, "teal"), belirtec(blok, "teal-metin")
        if not (t and tm):
            s.append("%s tema: --teal/--teal-metin yok" % ad); continue
        o = _kontrast(tm, t)
        if o < 4.5:
            s.append("%s tema: teal dugme yazisi (%s) zemininde (%s) %.2f:1"
                     % (ad, tm, t, o))
    if belirtec(acik, "teal") != belirtec(koyu, "teal"):
        s.append("--teal iki temada farkli: %s / %s"
                 % (belirtec(acik, "teal"), belirtec(koyu, "teal")))

    # Eski paletten kalan sabit renk olmamali.
    ESKI = ("f08a3c", "15110e", "1d1815", "272019", "f4efe7", "a2957f",
            "332a21", "453a2d", "d9701f", "3d2413", "b3a695", "fbf7f0")
    for y in sorted(glob.glob(os.path.join(KOK, "app", "*.html")) +
                    glob.glob(os.path.join(KOK, "app", "*.css")) +
                    glob.glob(os.path.join(KOK, "app", "*.js"))):
        metin = io.open(y, encoding="utf-8").read().lower()
        kalan = [c for c in ESKI if "#" + c in metin]
        if kalan:
            s.append("%s eski paletten renk tasiyor: %s"
                     % (os.path.basename(y), ", ".join(kalan)))
    return s


def pwa_tutarli_mi():
    """Manifest, service worker ve Play parcalari birbirini tutuyor mu.

    Hepsi SESSIZCE bozulabilecek turden -- yanlisi hicbir yerde patlamaz:
      - manifest bozuksa uygulama kurulabilir gorunmez, hata vermez;
      - sw damgasi eskirse kullanicilar eski surumu kullanmaya devam eder;
      - paket adi iki dosyada ayrisirsa TWA dogrulamasi tutmaz ve
        uygulamanin ustunde ADRES CUBUGU cikar, sebebi yazmaz.
    """
    s = []
    try:
        m = json.loads(oku("app", "manifest.webmanifest"))
    except Exception as e:
        return ["app/manifest.webmanifest okunamadi: %s" % e]

    # Play/TWA'nin ISTEDIGI asgari alanlar.
    for alan in ("name", "short_name", "start_url", "scope", "display",
                 "background_color", "theme_color", "icons"):
        if not m.get(alan):
            s.append("manifest: %s yok" % alan)
    if m.get("display") not in ("standalone", "fullscreen", "minimal-ui"):
        s.append("manifest: display %r -- TWA standalone bekliyor" % m.get("display"))

    # 192 ve 512 SART; maskelenebilir olmadan Android ikonu kirpiyor.
    olculer = {i.get("sizes") for i in m.get("icons", [])}
    for gerekli in ("192x192", "512x512"):
        if gerekli not in olculer:
            s.append("manifest: %s ikon yok" % gerekli)
    if not any("maskable" in (i.get("purpose") or "") for i in m.get("icons", [])):
        s.append("manifest: maskelenebilir ikon yok (Android ikonu kirpar)")

    # Ikon dosyalari GERCEKTEN var mi ve olculeri manifest'in dedigi mi.
    # Manifest'in dogru olmasi yetmiyor: dosya yoksa kurulum sessizce
    # basarisiz oluyor.
    for i in m.get("icons", []):
        yol = os.path.join(KOK, "app", i["src"])
        if not os.path.exists(yol):
            s.append("manifest %s dosyasi yok" % i["src"])
            continue
        try:
            from PIL import Image
            g = Image.open(yol)
            beklenen = tuple(int(x) for x in i["sizes"].split("x"))
            if g.size != beklenen:
                s.append("%s olcusu %s, manifest %s diyor"
                         % (i["src"], g.size, i["sizes"]))
        except ImportError:
            pass

    # Sayfalarin hepsi manifest'e baglanmali: biri unutulursa o sayfadan
    # giren kullaniciya kurulum onerilmez.
    for y in sorted(glob.glob(os.path.join(KOK, "app", "*.html"))):
        metin = io.open(y, encoding="utf-8").read()
        if 'rel="manifest"' not in metin:
            s.append("%s manifest'e baglanmiyor" % os.path.basename(y))

    # Service worker damgasi guncel mi.
    y = subprocess.run([sys.executable, "sw_uret.py", "kontrol"], cwd=KOK,
                       capture_output=True, text=True)
    if y.returncode != 0:
        s.append((y.stdout + y.stderr).strip()[-200:])

    # Kayit gercekten yapiliyor mu. sw.js'in var olmasi yetmez.
    if 'navigator.serviceWorker.register' not in oku("app", "ortak.js"):
        s.append("ortak.js service worker kaydetmiyor")

    # Paket adi IKI dosyada ayni olmali.
    try:
        twa = json.loads(oku("twa-manifest.json"))
    except Exception as e:
        return s + ["twa-manifest.json okunamadi: %s" % e]
    al = oku("assetlinks_uret.py")
    m2 = re.search(r'^PAKET = "([^"]+)"', al, re.M)
    if not m2:
        s.append("assetlinks_uret.py icinde PAKET yok")
    elif m2.group(1) != twa.get("packageId"):
        s.append("paket adi ayrisiyor: twa-manifest %r, assetlinks_uret %r"
                 % (twa.get("packageId"), m2.group(1)))

    # twa-manifest'teki start_url manifest ile ayni olmali; ayrisirsa
    # uygulama baska bir sayfada aciliyor ve cevrimdisi on yuklemesi
    # yanlis dosyayi tutuyor.
    if twa.get("startUrl") != m.get("start_url"):
        s.append("startUrl ayrisiyor: twa %r, manifest %r"
                 % (twa.get("startUrl"), m.get("start_url")))
    if twa.get("themeColor") != m.get("theme_color"):
        s.append("tema rengi ayrisiyor: twa %r, manifest %r"
                 % (twa.get("themeColor"), m.get("theme_color")))

    # Cevrimdisi sayfasi TEK BASINA durmali: son savunma katmani, bir
    # parcasi eksikse kullanici tarayicinin hata ekranini gorur.
    cd = oku("app", "cevrimdisi.html")
    # GERCEK basvuruya bakiliyor, metinde gecmesine degil: dosyanin
    # basindaki yorum "sahne.js BILEREK yok" diyor ve duz arama ona
    # takiliyordu -- yani kontrol, tam da dogru davranisi hata sayardi.
    basvurular = set(re.findall(r'(?:src|href)="([^"]+\.(?:js|css))"', cd))
    for yasak in ("ortak.js", "sahne.js", "sahne.css", "kimlik.js", "kesfet.js"):
        if yasak in basvurular:
            s.append("cevrimdisi.html %s'e bagli; tek basina durmali" % yasak)
    if m.get("start_url", "").lstrip("/") not in oku("app", "sw.js").replace("./", ""):
        s.append("sw.js manifest'in start_url'ini on yuklemiyor "
                 "(ilk acilista cevrimdisi kalirsa 'baglanti yok' cikar)")

    # Imzalama anahtari depoya SIZMAMIS olmali.
    izlenen = subprocess.run(["git", "ls-files"], cwd=KOK,
                             capture_output=True, text=True).stdout.split()
    for dosya in izlenen:
        if dosya.endswith((".jks", ".keystore")):
            s.append("IMZALAMA ANAHTARI DEPODA: %s" % dosya)
    return s


def sirlar_sizmis_mi():
    """Depoya girmemesi gerekenler.

    Onemli olan sey metinde bir kelimenin gecmesi degil, o kelimenin KOD
    olarak gecmesi. Anahtar da adiyla degil ICINDEKI ROLLE dogrulaniyor --
    "service_role" diye adlandirilmamis ama service_role olan bir jeton da
    yakalansin."""
    s = []

    # Depodaki her metin dosyasinda JWT ara, rolunu coz. anon disi her rol
    # tarayiciya inmemeli; service_role RLS'in tamamini atlar.
    jwt = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
    for p in glob.glob(os.path.join(KOK, "app", "*.js")) + \
             glob.glob(os.path.join(KOK, "app", "*.html")) + \
             glob.glob(os.path.join(KOK, "*.py")) + \
             glob.glob(os.path.join(KOK, "veritabani", "*.sql")):
        metin = io.open(p, encoding="utf-8").read()
        for jeton in jwt.findall(metin):
            rol = _jwt_rolu(jeton)
            if rol != "anon":
                s.append("%s: rolu '%s' olan jeton depoda — yalniz 'anon' olabilir"
                         % (os.path.relpath(p, KOK), rol))

    # SAGLAYICI ANAHTARLARI. JWT olmayan bicimler de var ve
    # bunlar depoya girerse fatura baskasina yazilir. veri.yml
    # anahtari GitHub Secrets'tan aliyor; dosyada duz yazilmis bir
    # anahtar o tasarimi sessizce bozar.
    #
    # Is akislari (.yml) DA taraniyor: bir sirri oraya duz yazmak,
    # koda yazmakla ayni sey ve daha kolay gozden kaciyor.
    ANAHTAR_BICIMLERI = [
        (re.compile(r"nvapi-[A-Za-z0-9_-]{20,}"), "NVIDIA NIM"),
        (re.compile(r"sk-[A-Za-z0-9]{32,}"),      "OpenAI"),
        (re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), "GitHub"),
        (re.compile(r"AKIA[0-9A-Z]{16}"),         "AWS"),
    ]
    for p in (glob.glob(os.path.join(KOK, "*.py")) +
              glob.glob(os.path.join(KOK, "app", "*.js")) +
              glob.glob(os.path.join(KOK, "app", "*.html")) +
              glob.glob(os.path.join(KOK, "*.md")) +
              glob.glob(os.path.join(KOK, ".github", "workflows", "*.yml"))):
        if os.path.basename(p) == "test.py":
            continue          # kaliplarin kendisi burada
        metin = io.open(p, encoding="utf-8").read()
        for kalip, ad in ANAHTAR_BICIMLERI:
            if kalip.search(metin):
                s.append("%s: %s anahtari duz yazilmis — GitHub Secrets'a "
                         "tasi ve anahtari IPTAL ET"
                         % (os.path.relpath(p, KOK), ad))

    # .env DEPODA OLMAMALI. .gitignore onu tutuyor ama dosya bir kez
    # zorla eklenirse gitignore geriye donuk calismaz.
    y = subprocess.run(["git", "ls-files", ".env", ".env.*"],
                       cwd=KOK, capture_output=True, text=True)
    for satir in y.stdout.split():
        if satir != ".env.ornek":
            s.append("%s git tarafindan IZLENIYOR — sir depoya girmis olabilir"
                     % satir)

    # TLS: yorum degil, kod arayacagiz. test.py kendi arama dizesini
    # tasidigi icin disarida.
    for p in glob.glob(os.path.join(KOK, "*.py")):
        if os.path.basename(p) == os.path.basename(__file__):
            continue
        if "verify=False" in _yorumsuz(io.open(p, encoding="utf-8").read()):
            s.append("%s: TLS dogrulamasi sabit kapali" % os.path.basename(p))

    if os.path.exists(os.path.join(KOK, ".env")):
        y2 = subprocess.run(["git", "check-ignore", ".env"], cwd=KOK, capture_output=True)
        if y2.returncode != 0:
            s.append(".env var ve .gitignore kapsaminda degil")
    return s


def kurulum_dosyalari_izleniyor_mu():
    """veritabani/ altindaki her SQL dosyasi depoda OLMALI.

    Bu gercek bir kayip oldu ve sessizdi: .gitignore'a foto_cek.py'nin
    urettigi dosya icin "mekan_foto.sql" satiri yazildi. Kalip yol
    belirtmiyordu, yani AYNI ADLI her dosyayi yutuyor -- ve
    veritabani/mekan_foto.sql SEMA dosyasini da yuttu. Dosya diskte
    duruyordu, testler geciyordu, ama depoya hic girmedi; kullanici
    depoyu cektiginde kurulum eksikti.

    KURULUM.md'nin listeledigi her dosyanin gercekten var oldugu da
    burada denetleniyor: belge var olmayan bir dosyayi isaret edemez."""
    s = []
    izlenen = set(subprocess.run(["git", "ls-files", "veritabani/"], cwd=KOK,
                                 capture_output=True, text=True).stdout.split())
    for yol in sorted(glob.glob(os.path.join(KOK, "veritabani", "*.sql"))):
        goreli = os.path.relpath(yol, KOK)
        if goreli not in izlenen:
            y = subprocess.run(["git", "check-ignore", "-v", goreli],
                               cwd=KOK, capture_output=True, text=True)
            s.append("%s depoda yok%s" % (
                goreli, (" (.gitignore: %s)" % y.stdout.strip()) if y.stdout else ""))

    # kos.sh calistirdigi her dosya gercekten var mi
    kos = io.open(os.path.join(KOK, "veritabani", "kos.sh"), encoding="utf-8").read()
    m = re.search(r'DOSYALAR="([^"]+)"', kos)
    if not m:
        s.append("kos.sh: DOSYALAR listesi okunamadi")
    else:
        for ad in m.group(1).split():
            if not os.path.exists(os.path.join(KOK, "veritabani", ad + ".sql")):
                s.append("kos.sh %s.sql dosyasini cagiriyor ama dosya yok" % ad)

    # KURULUM.md'nin isaret ettigi her dosya var mi
    kur = io.open(os.path.join(KOK, "KURULUM.md"), encoding="utf-8").read()
    for ad in set(re.findall(r"veritabani/(\w+\.sql)", kur)):
        if not os.path.exists(os.path.join(KOK, "veritabani", ad)):
            s.append("KURULUM.md veritabani/%s diyor ama dosya yok" % ad)
    return s


def adres_ve_tarih_mi():
    """Iki kural, ikisi de bir kez BOZULDU ve sessiz kaldi.

    1) ?donus= parametresi ADRES olarak kullaniliyor. Denetimsiz hali
       (P.get("donus") dogrudan location.href'e) iki sey yapiyordu -- ikisi
       de gercek Chromium'da olculdu:
         donus=javascript:...      -> CALISIYOR, hem de tam giris yapildiktan
                                      sonra, oturum jetonu okunabilirken.
         donus=https://taklit.site -> gercek sitede giris yapip taklit siteye
                                      dusmek; klasik kimlik avi zinciri.
       guvenliDonus()'un DAVRANISI ortak.js oz kontrolunde (109 kontrol);
       burada denetlenen sey cagri yerinin onu ATLAMAMASI.

    2) Gunun tarihi. toISOString() UTC verir; Turkiye kalici UTC+3, yani her
       gece 00:00-03:00 arasi dunu gosterir -- tam da disari cikip fis
       paylasan insanin saati. paylas.html hem varsayilan tarihi hem de
       <input max> degerini oradan aliyordu: bugunu SECTIRMIYORDU.
       kimlik.js ortak.js'e bagli degil (tek basina import edilebilen bir ES
       modulu), o yuzden kendi kopyasi var; ikisinin ayrismasi burada
       yakalaniyor."""
    s = []
    okun = lambda ad: io.open(os.path.join(KOK, "app", ad), encoding="utf-8").read()

    giris = _yorumsuz(okun("giris.html"))
    for kotu in re.findall(r'location\.href\s*=\s*([^;\n]*donus[^;\n]*)', giris):
        if "guvenliDonus" not in kotu:
            s.append("giris.html: donus denetimsiz adres olarak kullaniliyor -> %s"
                     % kotu.strip()[:60])
    if "function guvenliDonus" not in okun("ortak.js"):
        s.append("ortak.js: guvenliDonus() yok")

    # Adres semasi: href kuran her yer guvenliBag()'dan gecmeli. kacir()
    # tirnagi kacirir ama SEMAYA bakmaz; etkinlik baglantilari ucuncu
    # taraf RSS akislarindan geliyor.
    if "function guvenliBag" not in okun("ortak.js"):
        s.append("ortak.js: guvenliBag() yok")
    # Olumsuz bicim ARAMIYORUZ (bir yazim sekli yasaklanir, yenisi kacar);
    # olumlu kural aranıyor: satir() e.link'i guvenliBag'dan gecirmeli.
    ix = _yorumsuz(okun("index.html"))
    m = re.search(r"function satir\(e\)\{(.*?)\n  \}", ix, re.S)
    if not m:
        s.append("index.html: satir(e) bulunamadi (kontrol koru kaldi)")
    elif "guvenliBag(e.link)" not in m.group(1):
        s.append("index.html: etkinlik baglantisi guvenliBag'dan gecmiyor")
    cek = io.open(os.path.join(KOK, "etkinlik_cek.py"), encoding="utf-8").read()
    if "def guvenli_bag" not in cek:
        s.append("etkinlik_cek.py: guvenli_bag() yok")
    if '"link": guvenli_bag(' not in cek:
        s.append("etkinlik_cek.py: link denetimden gecmeden dosyaya yaziliyor")
    # Uretilmis dosyada da kalmis olmasin.
    yol = os.path.join(KOK, "app", "veri", "etkinlik.json")
    if os.path.exists(yol):
        d = json.loads(io.open(yol, encoding="utf-8").read())
        kotu = [e["link"] for il in d.get("iller", {}).values() for e in il
                if e.get("link") and not re.match(r"^https?://", e["link"], re.I)]
        if kotu:
            s.append("etkinlik.json: http/https disi %d baglanti (%s)"
                     % (len(kotu), kotu[0][:40]))

    # toISOString().slice(0,10) = UTC gun. Hicbir yerde kalmamali.
    for ad in ("ortak.js", "kimlik.js", "kesfet.js",
               "paylas.html", "isletme.html", "hesabim.html", "yonetim.html"):
        if re.search(r"toISOString\(\)\s*\.slice\(\s*0\s*,\s*10\s*\)",
                     _yorumsuz(okun(ad))):
            s.append("%s: gunun tarihi UTC'den aliniyor (toISOString)" % ad)

    # Iki bugunYerel() ayni formulu kullanmali.
    govde = []
    for ad in ("ortak.js", "kimlik.js"):
        m = re.search(r"function bugunYerel\(d\)\{(.*?)\n\}",
                      okun(ad).replace("function bugunYerel(d){",
                                       "function bugunYerel(d){"), re.S)
        if not m:
            s.append("%s: bugunYerel() yok" % ad)
        else:
            govde.append(re.sub(r"\s+", " ", m.group(1)).strip())
    if len(govde) == 2 and govde[0] != govde[1]:
        s.append("ortak.js ve kimlik.js'teki bugunYerel() ayrismis")
    return s


def ana_ekran_butce_mi():
    """Ana ekran butceyi SORUYOR mu, ve sordugu seyi DOGRU anlatiyor mu.

    Marka yol haritasi "Bugun cebimde: 300 TL -> kategori -> Yakinimda Bul"
    diyor. Ekran o hale getirildi; bu kontrol grubu onun iki sessiz bicimde
    bozulmasini engelliyor.

    1) BUTCE SUZGEC SANILMASIN. Olculdu: 3 km'lik gercek semt cemberlerinde
       300 TL butce listenin yalniz %2,7-%5,1'ini eliyor (Kadikoy 1.096
       mekandan 36, Beyoglu 2.203'ten 81, Kizilay 599'dan 16). Sebep:
       35.852 mekanin 163'unde (%0,45) olculmus menu fiyati var. Ekran
       butceyi suzgec gibi gosterirse -- "300 TL ile 12 mekan" -- kullanici
       12'sinin OLCULDUGUNU saniyor. O yuzden #butce-ozet satiri sart ve
       icerigi butceCumlesi()'nden gelmeli.

    2) DOKUM UC KARTTAN DEGIL, BUTUN LISTEDEN CIKMALI. Once uc aday secip
       sonra saymak, %0,45'lik olcumu ucte bir gibi gosterirdi. Sayim
       suzulmemis `konu` listesinden yapiliyor.

    3) IKI EKRAN AYNI KURALI KULLANMALI. Butce ustu elemesi once hem
       index.html'de hem kesfet.js'te ayri ayri yaziliydi; birini
       degistiren otekini sessizce ayristirabiliyordu. Ikisi de
       butceDurumu()'ndan geciyor.

    Kural gorunmez oldugu icin bu kontrol var: ekranda "12 mekan" yaziyor
    ve rakamin arkasinda olcum mu tahmin mi oldugunu HICBIR SEY soylemiyor.
    """
    s = []
    okun = lambda ad: io.open(os.path.join(KOK, "app", ad), encoding="utf-8").read()
    ham = okun("index.html")
    # _yorumsuz() DEGIL: o Python icin yazildi ve "#"den sonrasini atiyor,
    # yani el("#butce-ozet") satirini ikiye boluyor. Ustelik JS yorumlarini
    # HIC atmiyor -- silinmis bir cagri, onu anlatan yorum cumlesi
    # sayesinde "var" sayilirdi.
    ix = _js_yorumsuz(ham)
    ortak = _js_yorumsuz(okun("ortak.js"))
    kes = _js_yorumsuz(okun("kesfet.js"))

    # --- ekran butceyi soruyor mu
    # Marka maketindeki "Butceni Gir" ekrani: buyuk rakam + KAYDIRICI.
    # Onceden hazir butce CIPLERI vardi; makette cip yok, kaydirici var.
    # Yazi alani duruyor cunku kaydiricinin ustu 1.000 TL'de bitiyor ve
    # daha buyugunu yazmak isteyenin baska yolu kalmiyordu.
    for parca, ne in (('id="cep"', "butce formu"),
                      ('id="butce-girdi"', "butce yazi alani"),
                      ('id="butce-kaydirici"', "butce kaydiricisi"),
                      ('id="canim"', "kategori cipleri"),
                      ('id="butce-ozet"', "olcum/tahmin satiri")):
        if parca not in ham:
            s.append("index.html: %s yok (%s)" % (ne, parca))

    # --- rakamlar ve tur adlari TEK yerde
    if "const BUTCE_SECENEK" not in ortak:
        s.append("ortak.js: BUTCE_SECENEK yok")
    if "const CANIM" not in ortak:
        s.append("ortak.js: CANIM (kategori listesi) yok")
    # Kaydiricinin sinirlari ISARETLEMEDE duruyor (min/max/step) ve
    # sifirdan basliyor: sol uc "farketmez", yani butceOku()'nun sifir
    # degeri. Ayri bir "farketmez" dugmesi maketin tek kaydiricili
    # duzenini bozardi.
    m = re.search(r'id="butce-kaydirici"[^>]*min="(\d+)"[^>]*max="(\d+)"', ham)
    if not m:
        s.append("index.html: kaydiricinin min/max degerleri yok")
    elif int(m.group(1)) != 0:
        s.append("index.html: kaydirici sifirdan baslamiyor (%s); "
                 "farketmez hali kayboldu" % m.group(1))
    if "CANIM.map" not in ix:
        s.append("index.html: kategori cipleri CANIM'dan cizilmiyor")
    # Cipler elle yazilmis olmasin: sabit data-butce="150" gibi bir satir,
    # ortak.js'teki listeyle sessizce ayrisir.
    if re.search(r'data-butce="\d', ham):
        s.append("index.html: butce cipi elle yazilmis (data-butce=\"...\")")

    # --- siniflandirma yeniden yazilmamis
    for f in ("butceDurumu", "butceOzeti", "butceCumlesi"):
        if ("function %s(" % f) not in ortak:
            s.append("ortak.js: %s() yok" % f)
        if f not in ix:
            s.append("index.html: %s() kullanilmiyor" % f)
    # Ekran butceyi kendi karsilastirmasin.
    if re.search(r"yemekFiyati\([^)]*\)\s*[<>]", ix):
        s.append("index.html: butce karsilastirmasi ekranda tekrar yazilmis")

    # --- dokum SUZULMEMIS listeden
    if "butceOzeti(konu" not in ix:
        s.append("index.html: butce dokumu suzulmemis listeden alinmiyor")
    for kotu in ("butceOzeti(secim", "butceOzeti(aday"):
        if kotu in ix:
            s.append("index.html: dokum uc karttan cikariliyor (%s)" % kotu)

    # --- olcum/tahmin satiri gercekten basiliyor
    if "butceCumlesi(ozet" not in ix:
        s.append("index.html: #butce-ozet butceCumlesi()'nden beslenmiyor")

    # --- eleme YALNIZ kesin bilinen icin
    for ad, govde in (("index.html", ix), ("kesfet.js", kes)):
        if 'sinif === "asiyor"' not in govde:
            s.append("%s: butce elemesi butceDurumu()'ndan gecmiyor" % ad)
        for tahmin in ('sinif === "zor"', 'sinif === "bilinmiyor"'):
            m = re.search(r"filter\([^)]*%s" % re.escape(tahmin), govde)
            if m:
                s.append("%s: TAHMINE dayanarak mekan eleniyor (%s)" % (ad, tahmin))

    # --- secim kesfete tasiniyor
    if ix.count('p.set("butce", butce)') + ix.count('hepsi.set("butce", butce)') < 3:
        s.append("index.html: butce kesfete/mekana giden her baglantida tasinmiyor")
    if 'append("tur", t)' not in ix:
        s.append("index.html: secilen kategori kesfete tasinmiyor")

    # --- cihazda saklanan anahtarlar marka onekiyle
    for anahtar in re.findall(r'localStorage\.(?:get|set)Item\("([^"]+)"', ix):
        if not anahtar.startswith("cebimde."):
            s.append("index.html: localStorage anahtari marka onekli degil: %s" % anahtar)

    # --- BUTCE UCUNCU EKRANDA DA DURMALI
    # Olculdu: kesfette ?butce=300 ile gezip bir mekan acinca panelin
    # "Isletme sayfasi" baglantisi
    #     isletme.html?il=34&id=node%2F9730253703
    # veriyordu -- butce yok. Mekan sayfasi butceyi ?butce= ile okuyor,
    # yani kullanicinin bir kere yazdigi rakam ucuncu ekranda kayboluyor
    # ve kombin "En ucuz ogun" diyor, menu listesi kac kalemin butceye
    # girdigini hic yazmiyordu.
    kes = _js_yorumsuz(io.open(os.path.join(KOK, "app", "kesfet.js"),
                               encoding="utf-8").read())
    sayfa = re.search(r'el\("#d-sayfa"\)\.href\s*=(.*?);', kes, re.S)
    if not sayfa:
        s.append("kesfet.js: #d-sayfa adresi okunamadi")
    elif "butce" not in sayfa.group(1):
        s.append("kesfet.js: mekan sayfasina butce tasinmiyor")

    # Mekan sayfasi da onu OKUMALI; iki uc birbirini tutmali.
    isl = _js_yorumsuz(io.open(os.path.join(KOK, "app", "isletme.html"),
                               encoding="utf-8").read())
    # 'get("butce")' TEK BASINA YETMIYOR: sayfada ikinci bir okuma daha
    # var (butceBandi -> sayac). Sabotaj kombin/menu dalini butceOku("")
    # yapip kontrolu gecti. Aranan sey ADRESTEKI degerin butceOku()'ya
    # GIRMESI.
    if not re.search(r'butceOku\(\s*new URLSearchParams\(location\.search\)'
                     r'\.get\("butce"\)\s*\)', isl):
        s.append("isletme.html: adresteki butceyi okumuyor")
    return s


def fiyat_dayanagi_mi():
    """Fiyat KAC OLCUMDEN geldigini soyluyor mu.

    OLCULDU ve sonuc urunu degistirdi: menu fiyati gosterilebilen 163
    mekan yalniz 53 FARKLI ISLETME. 94'u Domino's subesi (%58), 10'u
    Papa John's -- iki pizza zinciri listenin %64'u. Ayni ilde cok
    subeli 113 mekanin HICBIRINDE subeler arasi fiyat farki yok, yani
    menu bir kez kazinmis ve 56 ayri olcum gibi gosteriliyordu.

    Bu, TEK FISI MEKANIN FIYATI SAYMAKLA ayni hata; depoda o hata
    FIS_ESIK ile kapatildi. Kural burada da ayni: rakam kaldirilmiyor
    ama neye dayandigi yaziliyor.

    UC EKRAN AYNI KAPIDAN GECMELI. Kart, mekan sayfasi ve ana ekranin
    oneri karti ayni fiyati gosteriyor; biri dayanagi yazip otekiler
    susarsa kullanici hangisine bakarsa ona inanir.

    ZINCIR HARITASI IL BASINA BIR KEZ kurulmali: kart basina hesaplanirsa
    2.300 kartlik listede 2.300 kez butun il taranir.
    """
    s = []
    okun = lambda ad: io.open(os.path.join(KOK, "app", ad), encoding="utf-8").read()
    ortak = _js_yorumsuz(okun("ortak.js"))
    kes = _js_yorumsuz(okun("kesfet.js"))
    ix = _js_yorumsuz(okun("index.html"))
    isl = _js_yorumsuz(okun("isletme.html"))

    for f in ("zincirHaritasi", "fiyatDayanagi", "dayanakCumlesi"):
        if ("function %s(" % f) not in ortak:
            s.append("ortak.js: %s() yok" % f)
    if "const ZINCIR_ESIK" not in ortak:
        s.append("ortak.js: ZINCIR_ESIK yok")

    # Uc ekran da dayanagi SORMALI.
    for ad, govde in (("kesfet.js", kes), ("index.html", ix), ("isletme.html", isl)):
        if "fiyatDayanagi(" not in govde:
            s.append("%s: fiyatin dayanagini hic sormuyor" % ad)
        if "zincirHaritasi(" not in govde:
            s.append("%s: zincir haritasini kurmuyor" % ad)

    # Harita IL BASINA bir kez: kart/satir cizen fonksiyonun icinde
    # kurulursa liste boyunca tekrar tekrar hesaplanir.
    for ad, govde, kalip in (
            ("kesfet.js", kes, r"function kartHTML\(m\)\{(.*?)\n\}"),
            ("index.html", ix, r"const kart = x => \{(.*?)\n    \};")):
        m = re.search(kalip, govde, re.S)
        if m and "zincirHaritasi(" in m.group(1):
            s.append("%s: zincir haritasi kart basina kuruluyor" % ad)

    # Mekan sayfasi TAM CUMLEYI basmali; kisa etiket tek basina
    # "56 subede ayni menu" der ama NEDEN onemli oldugunu soylemez.
    if "dayanakCumlesi(" not in isl:
        s.append("isletme.html: dayanak cumlesi basilmiyor")
    if 'id="dayanak"' not in okun("isletme.html"):
        s.append("isletme.html: #dayanak satiri yok")

    # Detay paneli de tam cumleyi vermeli: karar orada veriliyor.
    if "dayanakCumlesi(" not in kes:
        s.append("kesfet.js: detay paneli dayanak cumlesini basmiyor")

    # Ad normallestirmesi sade() OLMAMALI: sade() Turkce harfleri
    # dusuruyor ve iki AYRI isletmeyi ayni zincir sayabilir.
    m = re.search(r"function _adAnahtari\(ad\)\{(.*?)\n\}", ortak, re.S)
    if not m:
        s.append("ortak.js: _adAnahtari() yok")
    elif "sade(" in m.group(1):
        s.append("ortak.js: ad anahtari sade() kullaniyor; ayri isletmeler birlesebilir")

    # Fiyat anahtarda olmali: ayni adli ama AYRI kazinmis iki yer iki
    # ayri olcumdur ve tek olcum sayilmamali.
    m = re.search(r"function zincirHaritasi\(mekanlar, bugun\)\{(.*?)\n\}", ortak, re.S)
    if not m:
        s.append("ortak.js: zincirHaritasi() govdesi okunamadi")
    elif "_adAnahtari(m.ad) + \" \" + f" not in m.group(1):
        s.append("ortak.js: zincir anahtarinda fiyat yok; ayri kazimalar birlesir")

    # Ana sayfa ISLETME sayisini da yazmali: "291 mekan" tek basina
    # arkasindaki 93 kazimayi gizliyor.
    if 'id="d-marka"' not in okun("index.html"):
        s.append("index.html: menulu mekanlarin kac ISLETME oldugu yazmiyor")
    v = json.loads(okun("vitrin.json"))
    if "fiyatliMarka" not in v:
        s.append("vitrin.json: fiyatliMarka yok — vitrin_uret.py calistir")
    return s


def guven_skoru_mu():
    """Fiyat guven skoru (yesil/sari/kirmizi) ve butceye gore renklenen harita.

    Bantlar OLCULDU (35.852 mekan): yesil 50 (%0,14), sari 113 (%0,32),
    kirmizi 35.689 (%99,55). Kirmizinin genisligi skorun kusuru degil
    verinin durumu -- skorun isi tam olarak bunu soylemek.

    UC SESSIZ KUSUR VAR, ucu de burada aranıyor:

    1) RENK TEK BASINA BILGI TASIYAMAZ. Renk koru bir kullanici ve ekran
       okuyucu ayni seyi ogrenmeli. Rozet ya gorunur metin ya aria-label
       tasimali; ikisi de yoksa nokta anlamsiz bir susten ibarettir.

    2) HARITA RENK HARITASI EKSIK KALABILIR. butceDurumu() bes sinif
       donduruyor; harita bunlardan birini tanimazsa o mekanin noktasi
       renksiz (undefined) cizilir ve haritada SESSIZCE kaybolur. Bu
       kosum takimi haritayi goremiyor (Leaflet unpkg'den geliyor, aglar
       kapali), o yuzden kontrol KAYNAK uzerinden yapiliyor.

    3) RENKLER JS'E GOMULEBILIR. Tema degisince (acik/koyu) palet
       degisiyor; sabit onaltilik deger acik temada okunmaz hale gelir.
       Ayni sorun kartlarda yasandi. Renkler CSS degiskeninden okunmali.
    """
    s = []
    okun = lambda ad: io.open(os.path.join(KOK, "app", ad), encoding="utf-8").read()
    ortak = _js_yorumsuz(okun("ortak.js"))
    kes = _js_yorumsuz(okun("kesfet.js"))
    ix = _js_yorumsuz(okun("index.html"))
    isl = _js_yorumsuz(okun("isletme.html"))
    css = okun("stil.css")

    for f in ("fiyatGuveni", "guvenRozeti"):
        if ("function %s(" % f) not in ortak:
            s.append("ortak.js: %s() yok" % f)

    # Dort ekran da skoru gostermeli: ayni fiyat dort yerde goruluyor.
    for ad, govde in (("kesfet.js", kes), ("index.html", ix), ("isletme.html", isl)):
        if "guvenRozeti(" not in govde:
            s.append("%s: guven rozetini basmiyor" % ad)

    # Rozet renk DISINDA bir sey tasimali.
    m = re.search(r"function guvenRozeti\(g, kisa\)\{(.*?)\n\}", ortak, re.S)
    if not m:
        s.append("ortak.js: guvenRozeti() govdesi okunamadi")
    else:
        g = m.group(1)
        if "aria-label" not in g:
            s.append("ortak.js: guven rozeti aria-label tasimiyor (renk tek basina)")
        if "title=" not in g:
            s.append("ortak.js: guven rozeti gerekceyi title'a koymuyor")

    # Uc sinifin da CSS'i olmali; biri eksikse o bant renksiz kalir.
    for sinif in ("yesil", "sari", "kirmizi"):
        if (".guven.%s" % sinif) not in css:
            s.append("stil.css: .guven.%s kurali yok" % sinif)

    # --- harita: butceDurumu'nun DONDURDUGU her sinif renk haritasinda mi
    d = re.search(r"function butceDurumu\(m, butce, bugun\)\{(.*?)\n\}", ortak, re.S)
    h = re.search(r"const bRenk = \{(.*?)\};", kes, re.S)
    if not d:
        s.append("ortak.js: butceDurumu() govdesi okunamadi")
    elif not h:
        s.append("kesfet.js: harita renk haritasi (bRenk) yok")
    else:
        siniflar = set(re.findall(r'sinif:"(\w+)"', d.group(1)))
        renkli = set(re.findall(r"^\s*(\w+):", h.group(1), re.M))
        eksik = siniflar - renkli
        fazla = renkli - siniflar
        if eksik:
            s.append("kesfet.js: harita %s sinifini tanimiyor; o mekanlar renksiz cizilir"
                     % ", ".join(sorted(eksik)))
        if fazla:
            s.append("kesfet.js: harita renk haritasinda karsiligi olmayan sinif: %s"
                     % ", ".join(sorted(fazla)))
        # Renkler CSS'ten okunmali: sabit deger tema degisince bozulur.
        if "getPropertyValue" not in h.group(1):
            s.append("kesfet.js: harita renkleri CSS degiskeninden okunmuyor")

    # Harita butceDurumu'ndan gecmeli: ayri bir olcut, ayni mekani
    # listede bir renkte haritada baska renkte gosterirdi.
    m2 = re.search(r"function katmanCiz\(l, ortala\)\{(.*?)\n\}", kes, re.S)
    if not m2:
        s.append("kesfet.js: katmanCiz() govdesi okunamadi")
    elif "butceDurumu(" not in m2.group(1):
        s.append("kesfet.js: harita butceDurumu()'ndan gecmiyor")
    return s


def esik_iki_tarafta_ayni_mi():
    """k-anonimlik esigi TARAYICI ile SUNUCUDA ayni mi.

    BULGU: esik once YALNIZ tarayicidaydi. ortak.js fisGoster() tutari
    gizliyordu ama mekan_fis_ozeti(), civar_fis_ozeti() ve (ilk yazimda)
    fiyat_oy_ozeti() rakami oldugu gibi donduruyordu. anon anahtar
    TASARIM GEREGI herkese acik -- yani RPC'yi dogrudan cagiran biri
    ekranda gizlenen sayiyi okuyabiliyordu. Gizlemeyi yalniz arayuze
    birakmak, k-anonimligi bir gorunum meselesine indirger.

    Esik artik uc SQL fonksiyonunda da var. Bu kontrol ikisinin
    AYRISMASINI yakaliyor: tarayicidaki sayiyi 3'ten 5'e cikaran biri
    sunucuyu 3'te birakirsa, arada kalan iki kayit icin sunucu hala
    rakam veriyor demektir ve bunu hicbir sey soylemez.
    """
    s = []
    okun = lambda *y: io.open(os.path.join(KOK, *y), encoding="utf-8").read()
    ortak = _js_yorumsuz(okun("app", "ortak.js"))

    def sabit(ad):
        m = re.search(r"const %s\s*=\s*(\d+)" % ad, ortak)
        return int(m.group(1)) if m else None

    fis = sabit("FIS_ESIK")
    oy = sabit("OY_ESIK")
    if fis is None:
        s.append("ortak.js: FIS_ESIK yok")
    if oy is None:
        s.append("ortak.js: OY_ESIK yok")

    # SQL tarafi: her fonksiyonun icindeki esik.
    hedefler = [
        ("veritabani/sema.sql", "mekan_fis_ozeti", r"count\(\*\) >= (\d+)", fis),
        ("veritabani/akran.sql", "civar_fis_ozeti", r"count\(\*\) >= (\d+)", fis),
        ("veritabani/fiyat_oyu.sql", "fiyat_oy_ozeti",
         r"count\(distinct o\.kullanici\) >= (\d+)", oy),
    ]
    for yol, fn, kalip, bekleyen in hedefler:
        try:
            govde = okun(*yol.split("/"))
        except IOError:
            s.append("%s yok" % yol)
            continue
        bulunan = set(re.findall(kalip, govde))
        if not bulunan:
            s.append("%s: %s() k-anonimlik esigi TASIMIYOR; "
                     "RPC'yi dogrudan cagiran esik altini okuyabilir" % (yol, fn))
            continue
        if len(bulunan) > 1:
            s.append("%s: %s() icinde birden cok esik (%s)"
                     % (yol, fn, ", ".join(sorted(bulunan))))
            continue
        n = int(bulunan.pop())
        if bekleyen is not None and n != bekleyen:
            s.append("%s: %s() esigi %d ama ortak.js %d diyor — ayrismis"
                     % (yol, fn, n, bekleyen))

    # Tarayici tarafi hala yerinde mi: esik sunucuya tasindi diye
    # istemcideki kontrol SILINMEMELI. Sunucu eski surumdeyse (kullanici
    # SQL'i guncellemediyse) tek savunma o.
    if "function fisGoster(o){" not in ortak:
        s.append("ortak.js: fisGoster() yok — sunucu eski surumdeyken savunma kalmaz")
    if "function oyKarari(oy){" not in ortak:
        s.append("ortak.js: oyKarari() yok")
    return s


def menu_listesi_mi():
    """Mekan sayfasi MENUYU GOSTERIYOR ve rozet menuyle celismiyor.

    IKI AYRI KUSUR, ikisi de olculdu.

    (1) MENU EKRANDA HIC YOKTU. 291 mekanin menusunde 7.335 fiyatli
        kalem duruyor; mekan sayfasi bunlarin hicbirini basmiyordu.
        Ekranda kombin ("en ucuz ogun") ve fis ozeti vardi, menu yoktu --
        "Menu" sekmesine basan kullanici menuyu goremiyordu.

    (2) ROZET MENUYLE CELISIYORDU. Menusunde fiyat yazan 291 mekanin
        128'i (%44) "FIYAT YOK" rozeti aliyordu. Rozet dogru bir sey
        soyluyor (yemekFiyati() bir OGUNUN kaca geldigini cikaramiyor:
        84 mekanda ana urun kalemi ikiden az, 27'sinde hic kategori yok,
        16'sinda butun kategoriler icecek) ama CUMLESI yanlisti: 42
        kalemin fiyati ekranda yaziyorken "fiyat yok" demek.

    TASARIM KARARLARI DA BURADA KILITLENIYOR, cunku hepsi bir olcume
    dayaniyor ve olcum kaybolursa karar keyfi gorunur:

      fotograf yok      -> 7.335 kalemin sifirinda fotograf alani var
      gruplama yok      -> kategori kapsami mekan basina ortanca %47
      fiyata gore sirali-> uygulamanin sorusu "bu parayla ne yenir"
      ad kirpilmiyor    -> kalemlerin %16'sinin adi 34 harften uzun
      liste katlaniyor  -> mekan basina ortanca 34 kalem, en cok 50
    """
    s = []
    okun = lambda *y: io.open(os.path.join(KOK, *y), encoding="utf-8").read()
    ham = okun("app", "isletme.html")
    isl = _js_yorumsuz(ham)
    ortak = _js_yorumsuz(okun("app", "ortak.js"))

    # --- (1) menu listesi ---
    if 'id="menuListe"' not in ham:
        s.append("isletme.html: menu listesi bolumu yok")
    # Etiketin TAMAMINA bakiliyor: ilk yazim yalniz id'den ONCEKI 160
    # harfi tariyordu ve data-grup id'den SONRA yazildigi icin, dogru
    # isaretlemeye "bagli degil" dedi.
    etiket = re.search(r"<section[^>]*id=\"menuListe\"[^>]*>", ham)
    if not etiket:
        s.append("isletme.html: menuListe etiketi okunamadi")
    elif 'data-grup="menu"' not in etiket.group(0):
        s.append("isletme.html: menu listesi Menu sekmesine bagli degil")
    if "function menuListesi(" not in isl:
        s.append("isletme.html: menuListesi() yok")
    if "menuListesi(" not in isl.split("function menuListesi(")[0]:
        s.append("isletme.html: menuListesi() hic cagrilmiyor")

    m = re.search(r"function menuListesi\(m, butce\)\{(.*?)\n\}", isl, re.S)
    if not m:
        s.append("isletme.html: menuListesi() govdesi okunamadi")
    else:
        g = m.group(1)
        # Fiyata gore siralama: listenin ilk satiri "bu parayla ne
        # alinir" sorusunu cevaplamali.
        # "sort(" YETMIYOR: sabotaj `mn.sort(` yerine `[].sort(` yazdi ve
        # kontrol gecti -- liste siralanmadan basiliyordu. Siralanan sey
        # LISTENIN KENDISI olmali.
        if "mn.sort(" not in g:
            s.append("menuListesi: kalemler siralanmiyor")
        # Fiyatsiz kalem SONA. MAX_VALUE ile sayiya cevirmek onu "cok
        # pahali" yapar ve butce sayimina da oyle girerdi.
        if "MAX_VALUE" in g or "Infinity" in g:
            s.append("menuListesi: fiyatsiz kalem sayiya cevriliyor")
        if "a.f == null" not in g or "b.f == null" not in g:
            s.append("menuListesi: fiyatsiz kalem icin ayri dal yok")
        # Butce varsa SAYI yaziliyor, tahmin degil.
        if "butce > 0" not in g:
            s.append("menuListesi: butceyi hic okumuyor")
        if "k.f <= butce" not in g:
            s.append("menuListesi: butceye giren kalemi saymiyor")
        # Katlama: 50 satirlik liste sayfanin altini ekranin cok
        # asagisina itiyordu.
        # "MENU_ILK" YETMIYOR: esik dugme metninde de geciyor, yani
        # kirpma satiri silindiginde bile kontrol geciyordu. Aranan sey
        # KIRPMANIN KENDISI.
        if "slice(0, MENU_ILK)" not in g:
            s.append("menuListesi: uzun menu katlanmiyor")
    if "const MENU_ILK" not in isl:
        s.append("isletme.html: MENU_ILK esigi yok")

    # UYDURMA GORSEL YOK. Makette kalemlerin yaninda fotograf var ama
    # veride yok; bos gri kare ya da uydurma gorsel koymak bilgi
    # tasimayan (ya da yalan) bir sey basmak olurdu.
    ms = re.search(r"function menuSatiri\(k, butce\)\{(.*?)\n\}", isl, re.S)
    if not ms:
        s.append("isletme.html: menuSatiri() govdesi okunamadi")
    elif "<img" in ms.group(1):
        s.append("menuSatiri: kalem satirina gorsel konmus (veride fotograf yok)")

    # Ad KACIRILIYOR: kalem adlari kazimadan geliyor.
    if ms and "kacir(k.a" not in ms.group(1):
        s.append("menuSatiri: kalem adi kacirilmiyor (XSS)")

    # --- (2) rozet celiskisi ---
    if "function menudeFiyatVar(" not in ortak:
        s.append("ortak.js: menudeFiyatVar() yok")
    gv = re.search(r"function fiyatGuveni\(.*?\n\}", ortak, re.S)
    if not gv:
        s.append("ortak.js: fiyatGuveni() govdesi okunamadi")
    else:
        if "menudeFiyatVar(" not in gv.group(0):
            s.append("fiyatGuveni: menude fiyat olup olmadigina bakmiyor")
        if "GUVEN_ADI.menu" not in gv.group(0):
            s.append("fiyatGuveni: menulu mekan icin ayri ad kullanmiyor")
    if 'menu:"öğün fiyatı yok"' not in ortak.replace(" ", "").replace("\n", "") \
       and 'menu:"öğün fiyatı yok"' not in ortak:
        s.append("ortak.js: GUVEN_ADI.menu cumlesi degismis")

    return s   # kayit() LISTE bekliyor: `s or True` bos listede
               # True donuyordu, kayit onu BASARISIZ sayiyordu.


def platform_kapisi_mi():
    """Menu kazima kapisi PLATFORMLARI gercekten eliyor mu.

    NEDEN ONEMLI: bu kapi, deponun en cok savundugu sinirin kodda duran
    hali. "Yapilmayacaklar" listesi Google Maps, Yemeksepeti, Getir ve
    TrendyolGo'yu telif gerekcesiyle disarida birakiyor; platform_mu()
    o karari uygulayan tek yer.

    BULUNAN ACIK: kapi yalniz "m." ve "mobile." oneklerini taniyordu ve
    platformlarin DIL ALT ALANLARI geciyordu. Olculdu: "tr-tr.facebook.com"
    ve "tr.foursquare.com" isletmenin kendi sitesi sayiliyordu. Ayrica
    restaurantguru.com hic listede yoktu -- 17 kayit. Bir isletme
    rehberinden menu almak, Google Maps'ten almakla ayni sey.

    Veri o an degismedi (o 21 mekanin zaten menusu yoktu); kapi ILERIDE
    onemli, cunku menu_pdf_tara.py tam da o yigini tariyor.
    """
    s = []
    try:
        from app_veri import platform_mu
    except Exception as e:
        return ["app_veri.platform_mu okunamadi: %s" % e]

    # (a) PLATFORM SAYILMASI GEREKENLER -- dil alt alanlariyla birlikte.
    for u in ("https://www.instagram.com", "https://tr-tr.facebook.com",
              "https://en-gb.facebook.com", "https://tr.foursquare.com",
              "https://www.yemeksepeti.com", "https://getir.com",
              "https://www.trendyol.com", "https://www.google.com/maps/x",
              "https://restaurantguru.com/kafe", "https://wa.me/905550000000",
              "https://www.tripadvisor.com", "https://m.youtube.com"):
        if not platform_mu(u):
            s.append("platform_mu KACIRDI (kazimamaliyiz): %s" % u)

    # (b) ISLETMENIN KENDI SITESI SAYILMASI GEREKENLER.
    #
    # qr.menulux.com ve qrmenu.actdurum.com ISLETMENIN KENDI QR MENUSU:
    # barindirici bir SaaS ama icerik isletmenin. Kapinin bunlari elemesi,
    # elimizdeki mesru kaynagi atmak olurdu.
    #
    # "kumpirbox.com" ve "taproomx.com" kapiyi ELEMEMELI: kalip "x.com"u
    # gevsek ararsa bu adresler platform sanilir (ilk olcumumde tam
    # olarak bu oldu).
    for u in ("https://kaffamiro.com", "https://qrmenu.actdurum.com",
              "https://misoramenankara.qr.menulux.com", "https://kumpirbox.com",
              "https://taproomx.com", "https://www.westmix.com.tr",
              "https://mygoogle.com"):
        if platform_mu(u):
            s.append("platform_mu YANLIS ELEDI (kendi sitesi): %s" % u)

    # (c) TARAYICI HATTI da ayni kapiyi kullanmali.
    #
    # menu_pdf_tara.py siteyi TAM calistirip menu sayfasina geciyor;
    # platform kapisi ve robots.txt kapisi ORADA olmali.
    yol = os.path.join(KOK, "menu_pdf_tara.py")
    if os.path.exists(yol):
        d = io.open(yol, encoding="utf-8").read()
        if "robots_izin" not in d:
            s.append("menu_pdf_tara.py robots.txt kapisi tasimiyor")
        # TAM UA dizgesi verilirse robotparser adi "mozilla" diye okur
        # ve bizi adimizla yasaklayan site kapiyi gecer.
        if "can_fetch(BOT_ADI" not in d:
            s.append("menu_pdf_tara.py robots.txt'ye bot adini vermiyor")

    # METIN DEGIL DAVRANIS. Ilk hali dosyada dizge ariyordu ve iki
    # sabotaj birden gecti (fonksiyonu lambda ile takma, robotparser'i
    # atma). Artik fonksiyon CAGIRILIYOR.
    try:
        import menu_pdf_tara as MT
    except Exception as e:
        return s + ["menu_pdf_tara.py okunamadi: %s" % e]
    MT._robot_onbellek.clear()
    if MT.robots_izin("https://a.test",
                      getir=lambda u: "User-agent: *\nDisallow: /\n"):
        s.append("menu_pdf_tara robots.txt 'Disallow: /' dedigi halde tariyor")
    MT._robot_onbellek.clear()
    if not MT.robots_izin("https://b.test", getir=lambda u: ""):
        s.append("menu_pdf_tara robots.txt YOKKEN taramayi durduruyor "
                 "(yokluk kisitlama degil)")
    MT._robot_onbellek.clear()
    if MT.robots_izin("https://c.test",
                      getir=lambda u: "User-agent: CebimdeBot\nDisallow: /\n"):
        s.append("menu_pdf_tara bizi ADIMIZLA yasaklayan robots.txt'yi "
                 "gecersiz sayiyor")
    MT._robot_onbellek.clear()

    # KAPI GERCEKTEN CAGRILIYOR MU. Yukaridakiler fonksiyonun DOGRU
    # calistigini gosteriyor; cagrildigini GOSTERMIYOR. Sabotajla
    # goruldu: site_isle'deki uc satiri silmek butun kontrolleri
    # gecirdi. Simdi site_isle'nin KENDISI kosuluyor.
    import asyncio

    class _Catlayan:
        """Sayfa acilmaya calisilirsa kontrol patlasin."""
        async def new_page(self):
            raise AssertionError("robots.txt YASAKLARKEN sayfa acildi")

    MT._robot_onbellek.clear()
    MT._robot_onbellek["https://yasakli.test"] = False   # kapi "hayir" desin
    try:
        bulgu, kalemler = asyncio.run(MT.site_isle(
            _Catlayan(), None,
            {"mekan": "Deneme", "il": "34", "website": "https://yasakli.test"},
            None))
        if bulgu.get("tur") != "robots-yasak":
            s.append("menu_pdf_tara robots yasagini bulguya yazmiyor: %r"
                     % bulgu.get("tur"))
        if kalemler:
            s.append("menu_pdf_tara robots yasakliyken kalem uretti")
    except AssertionError as e:
        s.append("menu_pdf_tara: %s" % e)
    except Exception as e:
        s.append("menu_pdf_tara.site_isle kosulamadi: %s: %s"
                 % (type(e).__name__, e))
    MT._robot_onbellek.clear()
    return s


def site_sosyal_mi():
    """Isletme sitesinden sosyal bag toplama gercekten calisiyor mu.

    NEDEN VAR: sosyal hesabi olan mekan 304 (%0,8) ve HEPSI Instagram --
    turkiye_mekanlar.csv dort sutun eklenmeden onceki surumle uretilmis.
    OSM'yi yeniden cekmek o sutunlari dolduruyor ama etiketin OLMADIGI
    yerde yine bos kaliyor. menu_pdf_tara.py zaten her isletme sitesini
    gercek tarayicida aciyor; ayni geciste sayfadaki sosyal baglar da
    toplanabiliyor -- ek istek yok, ek kaynak yok, ve kaynak isletmenin
    KENDI sitesi.

    METIN DEGIL DAVRANIS: site_isle'nin kendisi taklit bir sayfayla
    kosuluyor ve yazdigi CSV okunuyor. Dosyada dizge aramak, toplama
    kodunu silen sabotaji gecirirdi (robots kapisinda tam bu oldu).
    """
    s = []
    try:
        import menu_pdf_tara as MT
        from app_veri import SOSYAL_ALANDAN, sosyal_adi
    except Exception as e:
        return ["menu_pdf_tara/app_veri okunamadi: %s" % e]

    # (a) SUZGEC. Paylasim baglari her sitede var ve bir hesap DEGIL;
    # alinsalar her mekana ayni sahte hesap yazilirdi. Turkce Facebook
    # alt alan adi ise en sik gorulen gercek bicim.
    for u, beklenen in (
            ("https://www.instagram.com/xkafe/", "instagram.com"),
            ("https://tr-tr.facebook.com/xkafe", "facebook.com"),
            ("https://x.com/xkafe", "x.com"),
            ("https://www.tiktok.com/@xkafe", "tiktok.com"),
            ("https://www.facebook.com/sharer/sharer.php?u=https://a.com", None),
            ("https://twitter.com/intent/tweet?url=a", None),
            ("https://www.facebook.com/plugins/page.php?href=a", None),
            ("https://xkafe.com/menu", None)):
        k = MT.SOSYAL_BAG.match(u)
        gecti = bool(k) and not MT.SOSYAL_DEGIL.search("/" + u[k.end():])
        alan = k.group(1).lower() if k else None
        if beklenen is None and gecti:
            s.append("site sosyal: hesap OLMAYAN bag toplandi: %s" % u)
        elif beklenen is not None and (not gecti or alan != beklenen):
            s.append("site sosyal: gercek hesap bagi elendi: %s (%s)" % (u, alan))

    # (b) TOPLAMA GERCEKTEN CAGRILIYOR MU. site_isle taklit sayfayla
    # kosuluyor; CSV'ye ne yazildigina bakiliyor.
    import asyncio
    import tempfile

    class _Sayfa:
        # SIRA BILEREK BOYLE. Paylasim baglari GERCEK baglardan ONCE
        # geliyor -- platform basina bir tane alindigi icin, suzgec
        # kalkarsa toplanan sey paylasim bagi OLUR ve gercek hesap
        # dusme sirasina girer. Ayrica twitter YALNIZ paylasim bagi
        # olarak var: suzgec kalkarsa cikan listede "twitter.com"
        # belirir ve kontrol bunu goruyor. Ilk yazimda ikisi de yoktu
        # ve "suzgeci sil" sabotaji KACTI: sharer bagi zaten
        # facebook.com diye tekillenip dusuyordu.
        BAGLAR = ["https://twitter.com/intent/tweet?url=a",
                  "https://www.facebook.com/sharer/sharer.php?u=https://a.com",
                  "https://www.instagram.com/xkafe/",
                  "https://tr-tr.facebook.com/xkafe",
                  "https://www.instagram.com/xkafe/",       # tekrar: bir kez
                  "/menu.html"]
        url = "https://xkafe.test/"
        def set_default_timeout(self, *a):
            pass
        async def goto(self, *a, **k):
            pass
        async def wait_for_timeout(self, *a):
            pass
        async def inner_text(self, *a):
            return ""
        async def eval_on_selector_all(self, secici, betik):
            if secici == "img":
                return []
            if "innerText" in betik:
                return [["", h] for h in self.BAGLAR]
            return list(self.BAGLAR)
        async def close(self):
            pass

    class _Tarayici:
        async def new_page(self):
            return _Sayfa()

    # (b0) TOPLAMA CALISTIRILABILIR MI. En pahali hata bu olurdu:
    # site_isle sosyal bag topluyor AMA islenmis() ayni siteyi iki kez
    # taramiyor. Olculdu -- 2.294 js sitesinin 2.372'si menu icin
    # taranmis ve "bu turda islenecek site: 0". Yani toplama, hicbir
    # zaman kosmayacak bir kod yolu olacakti. Ayri bir "sosyal" kipi
    # var ve KENDI gunlugune bakiyor.
    for ad in ("sosyal_isle", "sosyal_islenmis", "sosyal_turu"):
        if not hasattr(MT, ad):
            s.append("menu_pdf_tara: sosyal turu yok (%s) -- toplama "
                     "islenmis() yuzunden hic kosamaz" % ad)
    if hasattr(MT, "main"):
        import inspect
        if '"sosyal"' not in inspect.getsource(MT.main):
            s.append("menu_pdf_tara.main 'sosyal' kipini tanimiyor")

    gecici = tempfile.mkdtemp()
    eski = (MT.SOSYAL, MT.BULGU, MT.KALEM)
    MT.SOSYAL = os.path.join(gecici, "sosyal.csv")
    MT.BULGU = os.path.join(gecici, "bulgu.csv")
    MT.KALEM = os.path.join(gecici, "kalem.csv")
    MT._robot_onbellek.clear()
    MT._robot_onbellek["https://xkafe.test"] = True      # robots izin versin
    try:
        asyncio.run(MT.site_isle(
            _Tarayici(), None,
            {"mekan": "X Kafe", "il": "34", "website": "https://xkafe.test"},
            asyncio.Lock()))
        if not os.path.exists(MT.SOSYAL):
            s.append("site sosyal: site_isle hicbir bag yazmadi "
                     "(toplama cagrilmiyor)")
        else:
            with io.open(MT.SOSYAL, encoding="utf-8") as f:
                satir = list(csv.DictReader(f))
            alanlar = [r["alan"] for r in satir]
            if sorted(alanlar) != ["facebook.com", "instagram.com"]:
                s.append("site sosyal: beklenen iki platform yerine %r" % alanlar)
            # Yazilan bag KULLANICI ADINA cozulmeli ve o ad "xkafe"
            # olmali. Sadece "cozuluyor mu" demek yetmezdi: paylasim
            # bagi toplansaydi kullanici adi "sharer" diye cozulur ve
            # kontrol gecerdi.
            for r in satir:
                alan = SOSYAL_ALANDAN.get(r["alan"])
                if not alan:
                    s.append("site sosyal: taninmayan platform yazildi: %s"
                             % r["alan"])
                    continue
                if sosyal_adi(alan, r["url"]) != "xkafe":
                    s.append("site sosyal: yazilan bag 'xkafe' vermiyor: %s -> %r"
                             % (r["url"], sosyal_adi(alan, r["url"])))
    except Exception as e:
        s.append("site_isle kosulamadi: %s: %s" % (type(e).__name__, e))
    finally:
        MT.SOSYAL, MT.BULGU, MT.KALEM = eski
        MT._robot_onbellek.clear()
        shutil.rmtree(gecici, ignore_errors=True)

    # (c) SOSYAL KIPI: gunluge yaziyor mu (yoksa her kosuda bastan
    # baslar) ve robots kapisi orada da gecerli mi.
    gecici = tempfile.mkdtemp()
    eski = (MT.SOSYAL, MT.SOSYAL_LOG)
    MT.SOSYAL = os.path.join(gecici, "s.csv")
    MT.SOSYAL_LOG = os.path.join(gecici, "log.csv")
    MT._robot_onbellek.clear()
    MT._robot_onbellek["https://xkafe.test"] = True
    MT._robot_onbellek["https://yasakli.test"] = False
    try:
        n = asyncio.run(MT.sosyal_isle(
            _Tarayici(), {"mekan": "X", "il": "34",
                          "website": "https://xkafe.test"}, asyncio.Lock()))
        if n != 2:
            s.append("sosyal turu: 2 bag beklenirken %d" % n)
        if MT.sosyal_islenmis() != {"https://xkafe.test"}:
            s.append("sosyal turu gunluge yazmiyor; her kosuda bastan baslar")

        class _Catlayan:
            async def new_page(self):
                raise AssertionError("robots YASAKLARKEN sayfa acildi")

        MT.sosyal_isle  # noqa -- asagida cagriliyor
        asyncio.run(MT.sosyal_isle(
            _Catlayan(), {"mekan": "Y", "il": "34",
                          "website": "https://yasakli.test"}, asyncio.Lock()))
        with io.open(MT.SOSYAL_LOG, encoding="utf-8") as f:
            son = list(csv.DictReader(f))[-1]
        if son["durum"] != "robots-yasak":
            s.append("sosyal turu robots yasagini gunluge yazmiyor: %r"
                     % son["durum"])
    except AssertionError as e:
        s.append("sosyal turu: %s" % e)
    except Exception as e:
        s.append("sosyal turu kosulamadi: %s: %s" % (type(e).__name__, e))
    finally:
        MT.SOSYAL, MT.SOSYAL_LOG = eski
        MT._robot_onbellek.clear()
        shutil.rmtree(gecici, ignore_errors=True)
    return s


def konum_paneli_mi():
    """Isletme sayfasi mekanin NEREDE oldugunu soyluyor mu.

    NEDEN: adresi olan mekan yalniz 9.397/35.852 (%26,2). Kalan
    26.455 mekanda koordinat "burasi nerede" sorusunun TEK cevabi ve
    sayfada bugune kadar hic gorunmuyordu -- yalniz "cevresini haritada
    gor" diye kesfet ekranina bir bag vardi.

    YORUMLAR KAZINMIYOR. Maps/Yandex/Instagram yorumlari yazarlarinin
    telifinde ve platforma lisansli; buraya kopyalamak fotograflarla
    ayni ihlal olurdu (CEBIMDE.md "Yapilmayacaklar"). Kullaniciyi
    KAYNAGA gonderiyoruz ve sayfa bunu YAZIYOR -- sessizce yapilan bir
    tercih, kullanicinin "yorumlar nerede" sorusunu cevapsiz birakirdi.
    Kontrol o cumlenin varligini da ariyor.
    """
    s = []
    okun = lambda *y: io.open(os.path.join(KOK, *y), encoding="utf-8").read()
    ham = okun("app", "isletme.html")
    js  = _js_yorumsuz(okun("app", "ortak.js"))

    # (1) Kutuphane YEREL. unpkg'den cekmek hem CSP'yi genisletir hem
    # sayfayi bir CDN'e baglar; kesfet ile ayni dosya kullaniliyor.
    if '<script src="lib/leaflet.js">' not in ham:
        s.append("isletme.html: konum haritasi icin yerel Leaflet yuklenmiyor")
    if '<link rel="stylesheet" href="lib/leaflet.css">' not in ham:
        s.append("isletme.html: leaflet.css yuklenmiyor "
                 "(harita uslupsuz ve bozuk cizilir)")
    if 'id="mekanHarita"' not in ham:
        s.append("isletme.html: harita kabi yok")

    # (2) HARITA ISTEGE BAGLI. typeof denetimi olmazsa korumanin
    # KENDISI ReferenceError firlatir -- kesfet.js'te olculmus hata.
    if 'typeof L === "undefined"' not in ham:
        s.append("isletme.html: Leaflet yoksa sayfa cokuyor "
                 "(typeof denetimi yok)")
    if "harita-yok" not in ham:
        s.append("isletme.html: harita yuklenemediginde yerine aciklama yok")

    # (3) YOL TARIFI KOORDINATA, ARAMA ADLA. Ikisinin AYRI olmasi
    # kuralin kendisi: Maps yer kimligi (place_id) elimizde yok, yani
    # "bu mekanin sayfasi" diyemeyiz. Kural ortak.js'te tek yerde.
    for ad in ("koordinatVar", "koordinatYaz", "disHaritalar", "aramaMetni"):
        if ("function " + ad) not in js:
            s.append("ortak.js: %s yok (konum kurali tek yerde durmali)" % ad)
    # DUZ ARAMA YETMIYOR: ayni dizgi asagidaki kendi-kendini-kontrol
    # blogunda BEKLENEN DEGER olarak da duruyor, yani DIS_HARITA'daki
    # taban degistirilse bile arama gecerdi. Sabotajla goruldu.
    # Onun yerine "yol" kaydinin KENDI tabanina bakiliyor.
    yol_kaydi = re.search(r'anahtar:"yol".*?taban:"([^"]+)"', js, re.S)
    if not yol_kaydi:
        s.append("ortak.js: DIS_HARITA'da yol tarifi kaydi yok")
    elif "maps/dir/" not in yol_kaydi.group(1):
        s.append("ortak.js: yol tarifi bagi koordinata degil aramaya "
                 "gidiyor: %s" % yol_kaydi.group(1))
    # Koordinat denetimi TIP bakmali: veride dizgi gelirse toFixed
    # catlar ve harita hic cizilmez.
    if 'typeof m.lat === "number"' not in js:
        s.append("ortak.js: koordinat denetimi tipe bakmiyor")

    # (4) DIS BAGLAR https. Karisik icerik hem CSP'ye takilir hem
    # baglantiyi aciga cikarir.
    for esles in re.findall(r'taban:"([^"]+)"', js):
        if not esles.startswith("https://"):
            s.append("ortak.js: dis harita bagi https degil: %s" % esles)

    # (5) NEDEN YORUM YOK, EKRANDA YAZIYOR MU.
    #
    # YORUMLAR SILINEREK ARANIYOR. Ilk hali duz "telifinde in ham" idi
    # ve SABOTAJ GECTI: ayni kelime bolumun ustundeki HTML yorumunda da
    # geciyor, yani kullaniciya gorunen cumle silinse bile kontrol
    # gecerdi. Gizlilik tablosu kontrolunde de tam olarak bu olmustu.
    gorunen = re.sub(r"<!--.*?-->", " ", ham, flags=re.S)
    gorunen = re.sub(r"/\*.*?\*/", " ", gorunen, flags=re.S)
    if "yazarlarının telifinde" not in gorunen:
        s.append("isletme.html: yorumlarin neden kaynaginda okundugu "
                 "EKRANDA yazmiyor")

    # (6) YORUM KAZIYAN BIR SEY EKLENMEDI. Depoda Maps/Yandex yorum
    # ucu aramak, kuralin kendisini kontrole cevirmek.
    for yol in ("app/isletme.html", "app/ortak.js", "app/kesfet.js"):
        d = okun(*yol.split("/"))
        for kotu in ("maps.googleapis.com", "place/details",
                     "reviews?", "api.yandex", "graph.facebook.com"):
            if kotu in d:
                s.append("%s: yorum/veri kaziyan uc bulundu (%s)" % (yol, kotu))
    return s


def harita_karti_mi():
    """Haritada acilan panel HARITAYI GOSTERIYOR ve tek kopya bilgi basiyor.

    MAKET: "Haritada Kesfet" ekraninda beyaz kart altta duruyor, ustunde
    harita ve isaretciler NET.

    (1) PERDE HARITAYI YUTUYORDU. Olculdu (gercek Leaflet, 390x844):
        panel 554 px (ekranin %66'si), ustunde 290 px harita KALIYOR --
        ama rgba(0,0,0,.66) + blur(3px) ardinda, yani isaretciler
        secilmiyor. Perde LISTE gorunumunde dogru (arkada rakip bir
        metin listesi var); harita gorunumunde arkadaki sey cevabin
        parcasi. Modal kaliyor -- odak tuzagi ve Esc onunla geliyor.

    (2) BALON PANELLE BIRLIKTE ACILIYORDU. Olculdu:
            dialog acik   : True
            leaflet popup : {'metin': '#saltbae\\nKafe\\nhesapli...', 'gorunur': True}
        Balonun tasidigi uc bilgi (ad, tur, butce durumu) panelin
        basliginda zaten yaziyor ve panel modal: balon perdenin
        ardinda kaliyordu. Balonun KENDISI duruyor (isaretciye tiklayan
        kullanicinin tek bilgi kaynagi o); kaldirilan sey ac()'in balonu
        DA acmasi.
    """
    s = []
    okun = lambda *y: io.open(os.path.join(KOK, *y), encoding="utf-8").read()
    ham = okun("app", "kesfet.html")
    kes = _js_yorumsuz(okun("app", "kesfet.js"))

    # (1) Hafif perde kurali VE onu tetikleyen durum, ikisi birden.
    if 'dialog#detay[data-uzerinde="harita"]::backdrop' not in ham:
        s.append("kesfet.html: harita gorunumu icin hafif perde kurali yok")
    else:
        kural = ham.split('dialog#detay[data-uzerinde="harita"]::backdrop')[1][:200]
        if "backdrop-filter:none" not in kural.replace(" ", ""):
            s.append("kesfet.html: harita perdesinde bulaniklik hala acik")
    if "dataset.uzerinde" not in kes:
        s.append("kesfet.js: panel hangi gorunumun uzerinde acildigini yazmiyor")
    # KART HARITAYI KAPATMAMALI. Olculdu: harita alani 295-792 px,
    # panel 290 px'ten basliyor ve 554 px yuksekliginde -- yani alanin
    # tamamini ortuyordu.
    if 'dialog#detay[data-uzerinde="harita"]{ max-height' not in ham:
        s.append("kesfet.html: harita gorunumunde panelin boyu sinirsiz "
                 "(haritanin tamamini ortuyor)")

    # HARITA EKRANA SIGMALI. Olculdu: .govde 497 px iken #harita 2194 px
    # cikiyordu -- ekranin 4,4 kati. Sebep grid satirinin ortulu `auto`
    # olmasi; cocugun height:100% degeri cozulemiyordu.
    if "grid-template-rows:minmax(0,1fr)" not in re.sub(r"\s+", "", ham):
        s.append("kesfet.html: .govde satiri belirli degil (harita tasar)")
    if "min-height:0" not in ham.split("#harita{")[1][:120]:
        s.append("kesfet.html: #harita grid icinde kucuIemiyor (min-height:0 yok)")

    # (2) Panel acilirken balon acilmamali. openPopup() ac() govdesinde
    #     olmamali; bindPopup ise DURMALI.
    if "bindPopup(" not in kes:
        s.append("kesfet.js: isaretcinin balonu kaldirilmis (haritada tek bilgi kaynagi)")
    m = re.search(r"function ac\(id\)\{(.*?)\n\}", kes, re.S)
    if not m:
        s.append("kesfet.js: ac() govdesi okunamadi")
    elif "openPopup(" in m.group(1):
        s.append("kesfet.js: panel acilirken balon da aciliyor (perdenin ardinda kaliyor)")

    return s   # kayit() LISTE bekliyor: `s or True` bos listede
               # True donuyordu, kayit onu BASARISIZ sayiyordu.


def yazi_tipi_tutarli_mi():
    """Sayfanin INDIRDIGI yazi tipi, CSS'in ISTEDIGI yazi tipi olmali.

    OLCULDU (gercek tarayici, index.html):
        istenen adres : ...family=Fraunces...&family=Karla...
        h1 kullaniyor : Montserrat, ui-sans-serif, system-ui, ...
        yuklenen yuz  : []              <-- HICBIRI

    stil.css marka kilavuzuna gecirilirken --font-baslik/--font-govde
    Montserrat oldu; sayfalardaki <link> Fraunces + Karla'da kaldi.
    Sonuc: uygulama iki yazi tipini agdan cekiyor, hicbirini
    kullanmiyor ve gercekte SISTEMIN varsayilan sans'iyla ciziliyordu.
    Iki maliyet birden -- her sayfada bosa inen, cizimi bekleten bir
    stil dosyasi ve marka yazi tipinin hicbir yerde gorunmemesi.

    Bu sessiz bir kusurdu: sayfa acilir, "calisiyor" gorunur. Ancak
    tarayicida hangi yuzun YUKLENDIGINE bakinca ortaya cikti.

    Paylasim karti (og_uret.py) da ayni aileyi kullanmali: kart baska
    bir yazi tipiyle cikarsa onizleme uygulamaya benzemez.
    """
    s = []
    stil = oku("app", "stil.css")

    # CSS'in ISTEDIGI aileler: token'larin BASINDAKI tirnakli ad.
    istenen = set()
    for token in ("--font-baslik", "--font-govde"):
        m = re.search(re.escape(token) + r'\s*:\s*"([^"]+)"', stil)
        if not m:
            s.append("stil.css: %s tanimli degil ya da tirnakli ad ile baslamiyor"
                     % token)
        else:
            istenen.add(m.group(1))
    if not istenen:
        return s

    for y in sorted(glob.glob(os.path.join(KOK, "app", "*.html"))):
        ad = os.path.basename(y)
        govde = io.open(y, encoding="utf-8").read()
        baglar = re.findall(r'href="(https://fonts\.googleapis\.com/[^"]+)"', govde)
        if ad == "cevrimdisi.html":
            # TEK ISTISNA ve gerekcesi sayfanin kendi basinda yazili:
            # cevrimdisi sayfasi ag YOKKEN aciliyor. Oraya bir Google
            # Fonts baglantisi koymak, tanimi geregi gelmeyecek bir
            # istek eklemek olurdu. Kontrol bunu ADIYLA muaf tutuyor --
            # sessizce atlamiyor, cunku baska bir sayfa ayni sekilde
            # unutulursa yakalanmali.
            if baglar:
                s.append("cevrimdisi.html: ag YOKKEN acilan sayfa yazi tipi "
                         "indirmeye calisiyor")
            continue
        if not baglar:
            # Yazi tipi indirmeyen sayfa: yalniz sistem yazi tipiyle
            # cizilir. Sayfalarin geri kalani indiriyorsa, indirmeyen
            # unutulmus demektir.
            s.append("%s: yazi tipi hic yuklenmiyor" % ad)
            continue
        alinan = set()
        for b in baglar:
            alinan |= set(re.findall(r"family=([A-Za-z0-9+]+)", b))
        alinan = {a.replace("+", " ") for a in alinan}
        if alinan != istenen:
            s.append("%s: indirilen %s, CSS'in istedigi %s"
                     % (ad, sorted(alinan) or "-", sorted(istenen)))

    # Paylasim karti ayni aileyi kullanmali.
    og = oku("og_uret.py")
    for aile in istenen:
        if "family=" + aile.replace(" ", "+") not in og and \
           "family=" + aile not in og:
            s.append("og_uret.py: paylasim karti %s kullanmiyor" % aile)

    return s


def kurulum_belgesi_tam_mi():
    """Kurulan HER SQL dosyasi KURULUM.md'de yaziyor mu, ve bagimliliklari
    ham bir Postgres hatasiyla mi patliyor?

    YASANDI: topluluk.sql yazildi, kos.sh'a eklendi, testleri gecti --
    ama KURULUM.md'ye yazilmadi. Kullanici dosyayi Supabase'te
    calistirdiginda su cikti:

        ERROR: 42P01: relation "public.yorumlar" does not exist
        LINE 93:  from public.yorumlar y

    Iki ayri kusur birden: (1) dosya kurulum listesinde yoktu, yani
    kullanici onu SIRANIN NERESINDE calistiracagini bilemezdi;
    (2) dosya kendi bagimliligini soylemiyordu. Depoda bu is icin bir
    gelenek zaten var -- yorum.sql sirasi yanlissa "Once profil.sql
    calistirilmali" diye duruyor.

    Bu grup ikisini de olcuyor. Kontrol dosya adlarini kos.sh'tan
    okuyor: yeni bir SQL dosyasi eklendiginde liste kendiliginden
    buyuyor ve belgelenmemis dosya hemen goze carpiyor.
    """
    s = []
    kos = oku("veritabani", "kos.sh")
    belge = oku("KURULUM.md")

    m = re.search(r'DOSYALAR="([^"]+)"', kos)
    if not m:
        return ["veritabani/kos.sh: DOSYALAR listesi okunamadi"]

    # Kurulum dosyalari: _test ile bitenler ve taklit HARIC. Testler
    # kullanicinin calistiracagi seyler degil.
    dosyalar = [d for d in m.group(1).split()
                if not d.endswith("_test") and d != "supabase_taklit"]

    for d in dosyalar:
        yol = "veritabani/%s.sql" % d
        if not os.path.exists(os.path.join(KOK, yol)):
            s.append("%s kos.sh'ta var ama dosya yok" % yol)
            continue
        # sema.sql listede degil, ADIM 2 olarak ayrica anlatiliyor.
        if ("`%s`" % yol) not in belge:
            s.append("KURULUM.md: %s hic gecmiyor (kullanici sirayi bilemez)"
                     % yol)

    # BAGIMLILIK KAPISI. Baska bir dosyanin tablosunu okuyan her kurulum
    # dosyasi, o tablo yokken ANLASILIR bir cumleyle durmali.
    TABLO_SAHIBI = {
        "yorumlar": "yorum",
        "menu_katkilari": "menu_katki",
        "mekan_fotolari": "mekan_foto",
        "fiyat_oylari": "fiyat_oyu",
        "sahiplenme_kodlari": "sahiplenme",
    }
    for d in dosyalar:
        govde = oku("veritabani", "%s.sql" % d)
        for tablo, sahip in TABLO_SAHIBI.items():
            if sahip == d:
                continue
            if ("public.%s" % tablo) not in govde:
                continue
            # Tabloyu KULLANIYOR ama kendisi kurmuyor: kapi sart.
            if ("to_regclass('public.%s')" % tablo) not in govde:
                s.append("veritabani/%s.sql: public.%s tablosunu kullaniyor "
                         "ama yoksa ham hata veriyor (to_regclass kapisi yok)"
                         % (d, tablo))

    return s


def kutuphaneler_yerel_mi():
    """Harita kutuphanesi UCUNCU BIR TARAFIN ayakta olmasina bagli olmasin.

    VARSAYIM DEGIL, YASANMIS: Leaflet CDN'den gelmeyince kesfet ekraninin
    TAMAMI oluyordu -- sifir kart, sayac "..."da donmus. SRI o gun hicbir
    sey yapamadi, cunku SRI dosyanin DOGRU olup olmadigini soyluyor,
    GELIP GELMEDIGINI degil.

    Dosya artik depoda. Kutuphane_al.py onu npm kayit defterinden aliyor
    ve kayit defterinin RESMI sha512 ozetiyle dogrulanmadan yazmiyor;
    yani SRI'nin verdigi guvence duruyor, uzerine erisilebilirlik
    geliyor.

    OLCULDU (butun dis istekler kesili, gercek tarayici):
        Leaflet yuklendi : True
        harita kabi      : True   (.leaflet-container)
        harita-yok kutusu: False
    Onceden bu uc satirin ucu de tersiydi.

    BSD-2-Clause lisans metni de depoda: kodu kopyalayip lisansi
    birakmak sartin yarisini atlamak olurdu.
    """
    s = []
    lib = os.path.join(KOK, "app", "lib")
    js = os.path.join(lib, "leaflet.js")
    if not os.path.exists(js):
        return ["app/lib/leaflet.js yok; `python kutuphane_al.py leaflet` calistir"]
    if os.path.getsize(js) < 100 * 1024:
        s.append("app/lib/leaflet.js cok kucuk (%d bayt)" % os.path.getsize(js))
    if not os.path.exists(os.path.join(lib, "leaflet.css")):
        s.append("app/lib/leaflet.css yok")
    # BSD-2-Clause: telif bildirimi ve izin metni korunmali.
    lis = os.path.join(lib, "leaflet-LICENSE.txt")
    if not os.path.exists(lis):
        s.append("app/lib/leaflet-LICENSE.txt yok (BSD-2-Clause lisans metni)")
    govde = io.open(js, encoding="utf-8", errors="replace").read(2000)
    if "Vladimir Agafonkin" not in govde:
        s.append("app/lib/leaflet.js atif basligi dusmus")

    # Sayfa YERELDEN yuklemeli. Yerel dosya dururken CDN'e donmek,
    # yasanmis arizayi geri getirirdi.
    kes = oku("app", "kesfet.html")
    if 'src="lib/leaflet.js"' not in kes:
        s.append("kesfet.html leaflet.js'i yerelden yuklemiyor")
    if 'href="lib/leaflet.css"' not in kes:
        s.append("kesfet.html leaflet.css'i yerelden yuklemiyor")
    for satir in re.findall(r"<(?:script|link)[^>]*>", kes):
        if "unpkg.com" in satir and "leaflet" in satir.lower():
            s.append("kesfet.html hala CDN'den Leaflet cekiyor: %s" % satir[:70])

    # CSP DARALMALI: yerel kutuphane dururken unpkg.com kalmasi, artik
    # kullanilmayan bir kaynagi acik birakmak olurdu.
    ayar = oku("vercel.json")
    if "unpkg.com" in ayar:
        s.append("vercel.json'da unpkg.com hala var (kutuphane yerelde)")

    # Kabuk surumu leaflet.css'i de saymali: saymazsa cevrimdisi acilan
    # haritada uslup gelmezdi ve surum degisimi fark edilmezdi.
    sw = oku("sw_uret.py")
    if "lib/*.css" not in sw:
        s.append("sw_uret.py: lib/*.css kabuk surumune girmiyor")

    return s


def gizlilik_ucuncu_taraf_mi():
    """Gizlilik sayfasindaki saglayici listesi CSP ile TUTUYOR mu.

    CSP tarayicinin hangi kaynaklara gidebilecegini soyleyen TEK YETKILI
    yer. Gizlilik sayfasi ise kullaniciya "tarayicin sunlarla konusuyor"
    diyor. Ikisi ayrisirsa sayfa yanlis sey soyluyor demektir ve bu
    sessizce olur -- kimse iki listeyi yan yana koymaz.

    UC SAPMA BIRDEN BULUNDU:
        unpkg              yaziyordu, artik HIC cagrilmiyor (Leaflet yerelde)
        upload.wikimedia   cagriliyordu, YAZMIYORDU (Commons fotograflari)
        esm.sh             cagriliyordu, YAZMIYORDU (supabase-js yer tutucusu)
    Ilki fazla beyan; digerleri EKSIK beyan ve daha agir.

    Vercel listede ama CSP'de YOK ve olmasi da gerekmiyor: sitenin
    kendisi oradan geliyor, yani 'self'. Muafiyet adiyla yazili.
    """
    s = []
    ayar = oku("vercel.json")
    sayfa = oku("app", "gizlilik.html")

    m = re.search(r'"value":\s*"(default-src[^"]+)"', ayar)
    if not m:
        return ["vercel.json: CSP satiri okunamadi"]
    csp = m.group(1)

    # CSP'deki dis konaklar -> gizlilik sayfasinda aranacak ad.
    # 'self', data:, blob: ve karma degerleri dis taraf degil.
    AD = {
        "https://unpkg.com":                 "unpkg",
        "https://esm.sh":                    "esm.sh",
        "https://fonts.googleapis.com":      "Google Fonts",
        "https://fonts.gstatic.com":         "Google Fonts",
        "https://*.supabase.co":             "Supabase",
        "wss://*.supabase.co":               "Supabase",
        "https://*.basemaps.cartocdn.com":   "CARTO",
        "https://upload.wikimedia.org":      "Wikimedia Commons",
    }
    # Sitenin KENDI barindiricisi CSP'de gecmiyor ('self') ama listede
    # olmasi dogru: kullanici acisindan bir ucuncu taraf.
    MUAF = {"Vercel"}

    # SATIRLAR TABLODAN OKUNUYOR, sayfanin tamamindan DEGIL. Ilk yazim
    # "ad sayfada geciyor mu" diye bakiyordu ve UC SABOTAJ birden gecti:
    # "Wikimedia Commons" ve "esm.sh" sayfanin metninde de aciklaniyor,
    # "unpkg" ise tablonun ustundeki HTML yorumunda geciyor. Yani satir
    # silinse bile kontrol yesil kaliyordu. Ayni tuzak bu depoda daha
    # once de yasandi (href ile gorunen metin, title ile gorunen etiket).
    tablo = re.search(r"<thead><tr><th>Sağlayıcı</th>.*?</table>", sayfa, re.S)
    if not tablo:
        return ["gizlilik.html: saglayici tablosu bulunamadi"]
    satirlar = re.findall(r"<td>(.*?)</td>\s*<td>", tablo.group(0), re.S)
    satirlar = [x.strip() for x in satirlar]

    def listede(ad):
        return any(ad in x for x in satirlar)

    bulunan = set()
    for konak, ad in AD.items():
        if konak in csp:
            bulunan.add(ad)
            if not listede(ad):
                s.append("gizlilik.html: %s CSP'de var ama TABLODA YOK "
                         "(tarayici oraya gidiyor)" % ad)

    # Ters yon: tabloda olup CSP'de olmayan -- fazla beyan.
    for ad in sorted(set(AD.values())):
        if ad in bulunan:
            continue
        if listede(ad):
            s.append("gizlilik.html: %s tabloda ama CSP'de yok "
                     "(artik cagrilmiyor)" % ad)

    for ad in sorted(MUAF):
        if not listede(ad):
            s.append("gizlilik.html: %s tablodan dusmus" % ad)

    return s


def turler_ulasilabilir_mi():
    """VERIDEKI HER TUR bir cip ile secilebiliyor mu.

    Ana ekran kategorileri altidan DORDE indirildi (marka maketi dort
    daire gosteriyor). Secim sayimla yapildi -- ust dort mekanlarin
    %94,9'unu kapsiyor -- ama iki kategori dustu: Icki (Bar+Pub, 1.443)
    ve Dondurma (395).

    ANA EKRANDAN DUSMEK URUNDEN DUSMEK DEGIL: ana ekran "canin ne cekti"
    kisayolu, kesfet ekrani tam suzgec. Bar ve Pub cipleri kesfette
    zaten vardi. DONDURMA YOKTU -- yani degisiklik 395 dondurmaciyi
    aramanin disinda hicbir yoldan ulasilamaz yapacakti. Kesfete
    Dondurma cipi eklendi.

    Bu kontrol o deligi genel olarak kapatiyor: veri hattina yeni bir
    tur eklendiginde (turkiye_cek.py yeni bir OSM etiketi tanidiginda)
    cipi unutulursa burada goze carpiyor. Olculdu: 26 tur, ulasilmaz 0.

    Not: kontrol AGA CIKMIYOR, il dosyalarini okuyor -- yani veri
    degistiginde kendiliginden guncelleniyor.
    """
    s = []
    kes = oku("app", "kesfet.html")
    cipler = re.findall(r'data-tur="([^"]+)"', kes)
    if not cipler:
        return ["kesfet.html: hic tur cipi yok"]

    # TUR_GRUP ortak.js'te; grup cipleri (grup:eglence) bir kume aciyor.
    ortak = oku("app", "ortak.js")
    gruplar = {}
    m = re.search(r"const TUR_GRUP = \{(.*?)\n\};", ortak, re.S)
    if m:
        for ad, govde in re.findall(r'(\w+):\s*new Set\(\[(.*?)\]\)',
                                    m.group(1), re.S):
            gruplar[ad] = set(re.findall(r'"([^"]+)"', govde))

    # KATEGORI cipleri (kat:...) tur VE mutfak tasiyor; tur tarafi burada
    # aciliyor. Acilmasaydi "kat:kahve" duz bir tur adi sanilir ve Kafe
    # yalniz eski cip sayesinde ulasilabilir gorunurdu -- yani eski cip
    # silindiginde kontrol yanlis yerden yesil kalirdi.
    ortak_js = oku("app", "ortak.js")
    kat, KATEGORI_AD = {}, {}
    mk = re.search(r"const KATEGORI = \{(.*?)\n\};", ortak_js, re.S)
    if mk:
        for ad, govde in re.findall(r"(\w+):\s*\{(.*?)\}", mk.group(1), re.S):
            mt = re.search(r"tur:\s*\[(.*?)\]", govde, re.S)
            kat[ad] = re.findall(r'"([^"]+)"', mt.group(1)) if mt else []
            ma = re.search(r'ad:\s*"([^"]+)"', govde)
            KATEGORI_AD[ad] = ma.group(1) if ma else ad

    secilebilir = set()

    def ekle(sec):
        if sec.startswith("grup:"):
            secilebilir.update(gruplar.get(sec[5:], set()))
        elif sec.startswith("kat:"):
            for t in kat.get(sec[4:], []):
                ekle(t)
        else:
            secilebilir.add(sec)

    for c in cipler:
        ekle(c)

    # Veride gecen turler.
    idx = json.loads(oku("app", "veri", "index.json"))
    say = {}
    for il in idx["iller"]:
        ham = json.loads(oku("app", "veri", "%s.json" % il["kod"]))
        for m2 in veri_bicim.coz(ham)["mekanlar"]:
            t = m2.get("tur")
            if t:
                say[t] = say.get(t, 0) + 1

    ulasilmaz = sorted(((n, t) for t, n in say.items() if t not in secilebilir),
                       reverse=True)
    for n, t in ulasilmaz:
        s.append("kesfet.html: '%s' turu hicbir ciple secilemiyor (%d mekan)"
                 % (t, n))

    # TANIMLI HER KATEGORININ CIPI OLMALI. Bu ayri bir sart: Esnaf
    # lokantasinin mekanlari (mutfagi turkish olan Restoranlar) Yemek
    # cipiyle de listeye giriyor, yani "her tur ulasilabilir" kontrolu
    # Esnaf cipi silinince bile yesil kaliyor -- sabotaj bunu gosterdi.
    # Kategoriyi tanimlayip cipini koymamak, yazilmis ama hicbir yerden
    # secilemeyen bir suzgec birakmak demek.
    for ad in sorted(kat):
        if ("kat:" + ad) not in cipler:
            s.append("kesfet.html: '%s' kategorisi tanimli ama cipi yok"
                     % KATEGORI_AD.get(ad, ad))

    # Ana ekranin kategorileri de kesfette karsiligini bulmali: ana
    # ekrandan kesfete gecen kullanici ayni secimi orada gormeli.
    mc = re.search(r"const CANIM = \[(.*?)\];", ortak, re.S)
    if not mc:
        s.append("ortak.js: CANIM listesi okunamadi")
    else:
        girisler = re.findall(r'tur:\[([^\]]+)\]', mc.group(1))
        for g in girisler:
            for t in re.findall(r'"([^"]+)"', g):
                if t not in cipler:
                    s.append("ana ekrandaki '%s' kesfette cip olarak yok" % t)

    return s


def kombin_mi():
    """Cebimde kombini: "bu butceyle burada ne yenir".

    OLCUM KOMBININ SEKLINI BELIRLEDI. Iki mekanli kombin ("A'da kahve,
    B'de tatli") bu veriyle kurulamiyor: 400 m icinde FARKLI adli ikinci
    fiyatli mekani olan 22/163 = %13. Tek mekan icinde %90 (146/163).
    Kombin bu yuzden mekanin KENDI menusunden kuruluyor.

    KALEM KATEGORISI VERIDE OLMALI. Kombin ana urun ile icecegi ayirt
    etmek zorunda; kategori once yalniz kat[] toplamlarindaydi. Kural
    PYTHON'DA (fiyat_analiz.kategorile) -- tarayiciya kopyalamak ayni
    sozlugu iki dilde tutmak demekti.

    HER KATEGORIDEN EN UCUZ KALEM LISTEDE OLMALI. Menu en ucuz 40 kalem
    olarak kirpiliyordu ve olculdu: kombin 163 mekanin yalniz 47'sinde
    kurulabiliyordu, tikanan 116'nin 99'u Domino's -- pizzalarin hepsi
    (~480 TL) en ucuz 40'in disinda kaliyordu, yani mekanin ANA URUNU
    kayda hic girmiyordu. Ayni carpiklik kullaniciya da gorunuyordu:
    panel "en ucuz 40 kalem, 35-165 TL" yazip ustunde "yemek ~480 TL"
    gosteriyordu.
    """
    s = []
    okun = lambda *y: io.open(os.path.join(KOK, *y), encoding="utf-8").read()
    ortak = _js_yorumsuz(okun("app", "ortak.js"))
    kes = _js_yorumsuz(okun("app", "kesfet.js"))
    isl = _js_yorumsuz(okun("app", "isletme.html"))
    uret = okun("app_veri.py")

    for f in ("kombinKur", "kombinCumlesi"):
        if ("function %s(" % f) not in ortak:
            s.append("ortak.js: %s() yok" % f)

    # Iki ekran da gostermeli.
    for ad, govde in (("kesfet.js", kes), ("isletme.html", isl)):
        if "kombinKur(" not in govde:
            s.append("%s: kombini hic kurmuyor" % ad)
        if "kombinCumlesi(" not in govde:
            s.append("%s: kombin cumlesini basmiyor" % ad)

    # Ana urun karari ortak.js'te kalmali; kombin onu yeniden yazmamali.
    m = re.search(r"function kombinKur\(m, butce, bugun\)\{(.*?)\n\}", ortak, re.S)
    if not m:
        s.append("ortak.js: kombinKur() govdesi okunamadi")
    else:
        g = m.group(1)
        if "anaKategoriler(" not in g:
            s.append("ortak.js: kombin ana urunu anaKategoriler()'den almiyor")
        if "ICECEK_KAT" not in g or "TATLI_KAT" not in g:
            s.append("ortak.js: kombin icecek/tatli kumelerini kullanmiyor")
        # Yanina hicbir sey yoksa kombin KURULMAMALI.
        if "if (!yanina) return null;" not in g:
            s.append("ortak.js: yanina kalem yokken kombin yine donuyor")

    # Kategorisiz kalem sepete girmemeli.
    m2 = re.search(r"function _ucuzKalem\(menu, kume\)\{(.*?)\n\}", ortak, re.S)
    if not m2:
        s.append("ortak.js: _ucuzKalem() yok")
    elif "!k.k" not in m2.group(1):
        s.append("ortak.js: kategorisiz kalem sepete girebiliyor")

    # --- veri tarafi: kalem kategorisi ve kategori basina en ucuz kalem
    if 'kalem["k"] = kat' not in uret:
        s.append("app_veri.py: menu kalemine kategori yazilmiyor")
    if "_gorulen" not in uret or "kalemler.append(k)" not in uret:
        s.append("app_veri.py: her kategoriden en ucuz kalem listeye alinmiyor")

    # Uretilmis veride GERCEKTEN var mi: betigi degistirip veriyi
    # yeniden uretmeyi unutmak, ekranda kombini sessizce yok eder.
    import veri_bicim as _vb
    kategorili = kalem = 0
    for kod in ("34", "06"):
        yol = os.path.join(KOK, "app", "veri", kod + ".json")
        if not os.path.exists(yol):
            continue
        d = _vb.coz(json.loads(io.open(yol, encoding="utf-8").read()))
        for mk in d.get("mekanlar", []):
            for x in (mk.get("menu") or []):
                kalem += 1
                if "k" in x:
                    kategorili += 1
    if kalem and not kategorili:
        s.append("app/veri: menu kalemlerinde kategori yok — python app_veri.py calistir")
    return s


def seviye_mi():
    """Kullanici seviyesi: SUS degil SAYIM.

    Uc sessiz kusur var, ucu de burada araniyor:

    1) GONDERILEN katki sayilirsa seviye kuyruga cop atarak
       yukseltilebilir. Yalniz durum='onaylandi' sayilmali. On onay
       zaten hakaret ve yanlis bilgi icin var; seviye de ayni kapidan
       gecsin.

    2) FIYAT OYU seviyeye girerse ozellik oyunlastirmanin bozuldugu yere
       duser: oy tek dokunus ve onay kuyrugu YOK (savunma orada esik).
       Oy sayisi ekranda ayri yaziyor, seviyeye etkisiz.

    3) SAYIM SATIR CEKEREK yapilirsa hesabim ekranindaki tembel
       sekmelere baglanir ve seviye "hangi sekmeye bastigina gore"
       degisir. Sayim head:true ile, ayri bir uctan.
    """
    s = []
    okun = lambda *y: io.open(os.path.join(KOK, *y), encoding="utf-8").read()
    ortak = _js_yorumsuz(okun("app", "ortak.js"))
    kim = _js_yorumsuz(okun("app", "kimlik.js"))
    hes = _js_yorumsuz(okun("app", "hesabim.html"))

    for f in ("seviyeHesapla", "seviyeCumlesi"):
        if ("function %s(" % f) not in ortak:
            s.append("ortak.js: %s() yok" % f)
    if "const SEVIYELER" not in ortak:
        s.append("ortak.js: SEVIYELER yok")

    # Esikler artan olmali ve 0'dan baslamali; bozuk siralama seviyeyi
    # sessizce yanlis hesaplatir.
    m = re.search(r"const SEVIYELER = \[(.*?)\];", ortak, re.S)
    if not m:
        s.append("ortak.js: SEVIYELER listesi okunamadi")
    else:
        esikler = [int(x) for x in re.findall(r"esik:\s*(\d+)", m.group(1))]
        if not esikler:
            s.append("ortak.js: SEVIYELER bos")
        else:
            if esikler[0] != 0:
                s.append("ortak.js: SEVIYELER 0'dan baslamiyor (%d)" % esikler[0])
            if esikler != sorted(esikler) or len(set(esikler)) != len(esikler):
                s.append("ortak.js: SEVIYELER esikleri artan degil: %s" % esikler)
            # 3. esik FIS_ESIK ile ayni olmali: "Dogrulayici" adinin
            # gerekcesi tam olarak o sayi.
            mf = re.search(r"const FIS_ESIK = (\d+)", ortak)
            if mf and int(mf.group(1)) not in esikler:
                s.append("ortak.js: FIS_ESIK (%s) SEVIYELER esiklerinde yok; "
                         "'Dogrulayici' gerekcesini kaybetti" % mf.group(1))

    # --- sayim ucu
    if "async katkiOzetim(" not in kim:
        s.append("kimlik.js: katkiOzetim() yok")
    else:
        m2 = re.search(r"async katkiOzetim\(\)\{(.*?)\n  \},", kim, re.S)
        if not m2:
            s.append("kimlik.js: katkiOzetim() govdesi okunamadi")
        else:
            g = m2.group(1)
            if "head: true" not in g:
                s.append("kimlik.js: katki sayimi satir cekiyor (head:true yok)")
            if 'eq("durum", "onaylandi")' not in g:
                s.append("kimlik.js: ONAYLANMAMIS katki da sayiliyor; "
                         "seviye kuyruga cop atarak yukseltilebilir")
            # Oy AYRI donmeli ve toplama girmemeli.
            if "onayli: fis + katki + yorum + menu + foto" not in g:
                s.append("kimlik.js: onayli toplami beklenen bilesenlerden degil")
            if re.search(r"onayli:[^;\n]*\boy\b", g):
                s.append("kimlik.js: fiyat oyu seviye toplamina giriyor")

    # --- ekran
    if "seviyeHesapla(" not in hes:
        s.append("hesabim.html: seviyeyi hic hesaplamiyor")
    if "katkiOzetim(" not in hes:
        s.append("hesabim.html: katki sayimini istemiyor")
    # Sekmelerden bagimsiz olmali: seviye cizimi bir sekme cizicisinin
    # icinden cagrilirsa o sekmeye basilmadan gorunmez.
    for sekme in ("paylasimlariCiz", "yorumlariCiz", "katkilariCiz"):
        m3 = re.search(r"async function %s\(\)\{(.*?)\n\}" % sekme, hes, re.S)
        if m3 and "seviyeyiCiz(" in m3.group(1):
            s.append("hesabim.html: seviye %s() icinden cagriliyor; "
                     "sekmeye basilmadan gorunmez" % sekme)
    return s


def butce_talebi_mi():
    """Isletme panelindeki butce talebi: OZGUN sayi, ama ifsa etmeden.

    Uc sessiz kusur var:

    1) TAM TUTAR SAKLANIRSA sayac satiri (mekan, gun, cihaz) giderek
       daha ayirt edici olur. Bant saklanmali, rakam degil -- ve bant
       esikleri BUTCE_SECENEK'ten gelmeli, ikinci bir olcek
       uydurulmamali.

    2) K-ANONIMLIK ESIGI SUNUCUDA olmali. Kucuk sayilarda "bakanlarin
       1'i 150 TL altiydi" demek o tek kisinin butcesini ifsa etmekle
       ayni sey. Istemcide gizlemek yetmez: anon anahtar tasarim geregi
       herkese acik.

    3) IKI IMZA YAN YANA DURAMAZ. mekan_goruldu artik iki argumanli;
       eski tek argumanli surum dusurulmezse PostgREST hangisini
       cagiracagini bilemez ve sayac SESSIZCE calismaz olur.
    """
    s = []
    okun = lambda *y: io.open(os.path.join(KOK, *y), encoding="utf-8").read()
    ortak = _js_yorumsuz(okun("app", "ortak.js"))
    kim = _js_yorumsuz(okun("app", "kimlik.js"))
    isl = _js_yorumsuz(okun("app", "isletme.html"))
    pan = _js_yorumsuz(okun("app", "isletmem.html"))
    sql = okun("veritabani", "sayac.sql")

    for f in ("butceBandi", "butceBandiAdi", "butceTalebiCumlesi", "sayiEki"):
        if ("function %s(" % f) not in ortak:
            s.append("ortak.js: %s() yok" % f)

    # Bant esikleri BUTCE_SECENEK'ten gelmeli.
    m = re.search(r"function butceBandi\(butce\)\{(.*?)\n\}", ortak, re.S)
    if not m:
        s.append("ortak.js: butceBandi() govdesi okunamadi")
    elif "BUTCE_SECENEK" not in m.group(1):
        s.append("ortak.js: bant esikleri BUTCE_SECENEK'ten gelmiyor; "
                 "ikinci bir olcek uydurulmus")

    # Istemci BANT gonderiyor, tam tutar degil.
    if "p_butce_bandi" not in isl:
        s.append("isletme.html: goruntulenmeye butce bandi gonderilmiyor")
    if re.search(r"p_butce\b\s*:", isl):
        s.append("isletme.html: sunucuya TAM TUTAR gonderiliyor (bant degil)")

    # --- SQL tarafi
    if "butce_bandi smallint" not in sql:
        s.append("sayac.sql: butce_bandi sutunu yok")
    if "add column if not exists butce_bandi" not in sql:
        s.append("sayac.sql: var olan tabloya sutun eklenmiyor; "
                 "eski kurulumda ozellik sessizce bos kalir")
    if "create or replace function public.mekan_butce_talebi" not in sql:
        s.append("sayac.sql: mekan_butce_talebi() yok")
    else:
        m2 = re.search(r"create or replace function public\.mekan_butce_talebi.*?\$\$(.*?)\$\$",
                       sql, re.S)
        if not m2:
            s.append("sayac.sql: mekan_butce_talebi() govdesi okunamadi")
        else:
            g = m2.group(1)
            if ">= 5" not in g:
                s.append("sayac.sql: butce talebinde k-anonimlik esigi yok; "
                         "tek kisinin butcesi disari cikabilir")
            if "current_date - 30" not in g:
                s.append("sayac.sql: butce talebi pencere kullanmiyor (30 gun)")
    # Eski imza dusurulmus mu.
    if "drop function if exists public.mekan_goruldu(text);" not in sql:
        s.append("sayac.sql: eski tek argumanli mekan_goruldu dusurulmemis; "
                 "PostgREST hangisini cagiracagini bilemez")

    # Panel gostermeli.
    if "mekanButceTalebi(" not in kim:
        s.append("kimlik.js: mekanButceTalebi() yok")
    if "butceTalebiCumlesi(" not in pan:
        s.append("isletmem.html: butce talebini gostermiyor")

    # --- satilmayacaklar: urunun kendisi
    belge = okun("CEBIMDE.md")
    for satir in ("Sıralamada üst sıra", "Olumsuz yorumu kaldırma",
                  "Fiyatı gizleme"):
        if satir not in belge:
            s.append("CEBIMDE.md: gelir modelinde '%s' satiri yok" % satir)
    return s


def sayfa_kontrolleri():
    """Sayfalari GERCEK tarayicida acar (test_sayfa.py).

    test_tarayici.mjs betikleri vm kutusunda calistiriyor: DOM yok,
    yukleme sirasi yok, CDN yok. Bu yuzden gercek bir hatayi goremedi --
    Leaflet gelmediginde kesfet ekraninin tamami oluyordu. Tarayici
    yoksa ATLANIR, gectigi soylenmez."""
    yol = os.path.join(KOK, "test_sayfa.py")
    if not os.path.exists(yol):
        return kayit("test_sayfa.py", ["dosya yok"])
    try:
        c = subprocess.run([sys.executable, yol, "test"], capture_output=True,
                           text=True, timeout=420, cwd=KOK)
    except subprocess.TimeoutExpired:
        return kayit("test_sayfa.py (gercek tarayici)", ["zaman asimi"])
    cikti = (c.stdout or "") + (c.stderr or "")
    if "ATLANDI" in cikti:
        return kayit("test_sayfa.py (gercek tarayici)",
                     [cikti.strip().splitlines()[-1]], atlandi=True)
    if c.returncode != 0:
        return kayit("test_sayfa.py (gercek tarayici)",
                     [x for x in cikti.splitlines() if x.strip()][:8])
    kayit("test_sayfa.py (gercek tarayici)", [])


def sql_kontrolleri():
    """SQL davranis kontrollerini GERCEK Postgres'te kosar (veritabani/kos.sh).

    Politikalarin metnini okumak yetmiyor. Bu depoda tam olarak sunlar
    OLCULEREK bulundu, hicbiri statik okumayla gorunmezdi:
      - supabase_taklit.sql'de eksik bir grant yuzunden dosya 6. adimda
        patliyordu; 11 kontrolun ALTISI hic kosmuyordu.
      - 2. adim ("kullanici sahiplik tablosuna dogrudan yazamaz") YANLIS
        SEBEPTEN geciyordu: engel politika degil, eksik yetkiydi.
      - RLS SATIR duzeyinde: "onaylanmis herkese acik" politikalari satiri
        aciyor ve satirin icindeki `kullanici` uuid'sini de aciyordu.

    Postgres yoksa ATLANIR, gectigi soylenmez."""
    yol = os.path.join(KOK, "veritabani", "kos.sh")
    if not os.path.exists(yol):
        return kayit("veritabani/kos.sh", ["dosya yok"])
    try:
        c = subprocess.run(["sh", yol], capture_output=True, text=True,
                           timeout=300, cwd=KOK)
    except subprocess.TimeoutExpired:
        return kayit("SQL davranisi (gercek Postgres)", ["zaman asimi"])
    cikti = (c.stdout or "") + (c.stderr or "")
    if "ATLANDI" in cikti:
        return kayit("SQL davranisi (gercek Postgres)",
                     [x for x in cikti.splitlines() if "ATLANDI" in x][:1], atlandi=True)
    if c.returncode != 0:
        return kayit("SQL davranisi (gercek Postgres)",
                     [x for x in cikti.splitlines() if x.strip()][-8:])
    # HER test dosyasinin SONUNA kadar gittigini dogrula. Tek bir imza
    # aramak yetmez: iki dosya var ve biri yarida kesilse otekinin bitis
    # satiri kontrolu yine yesil yapardi.
    # HER IMZA DOSYA ADIYLA BASLIYOR. Onceden sahiplenme imzasi adsizdi
    # ("20 kontrolun hepsi gecti") ve yorum dosyasinin bitis satirinin
    # ICINDE geciyordu -- sahiplenme kosumu bastan sona patlasa bile bu
    # kontrol yesil kalirdi. Sayilar da elle guncelleniyor: bir dosyaya
    # adim eklenince imza da buyumeli, yoksa yarim kosum fark edilmez.
    eksik = [ad for ad, imza in
             (("sahiplenme", "sahiplenme: 21 kontrolun hepsi gecti"),
              ("sayac", "sayac: 16 kontrolun hepsi gecti"),
              ("yorum", "yorum: 20 kontrolun hepsi gecti"),
              ("menu katkisi", "menu katkisi: 12 kontrolun hepsi gecti"),
              ("mekan fotografi", "mekan fotografi: 12 kontrolun hepsi gecti"),
              ("akran", "akran_test: 12 adimin hepsi gecti"),
              ("fiyat oyu", "fiyat_oyu_test: 15 adimin hepsi gecti"),
              ("topluluk", "topluluk_test: 11 adimin hepsi gecti"))
             if imza not in cikti]
    if eksik:
        return kayit("SQL davranisi (gercek Postgres)",
                     ["%s kosumu sonuna ulasmadi" % a for a in eksik])
    # KURULUM.md, kullaniciya "su cikti gorunmeli" diyor. O satirlar
    # SQL'in gercekten bastigi seyle ayni olmali; ayrisirsa kullanici
    # ekranda baska bir sey gorup kurulumun bozuldugunu sanar.
    # Bu gercek bir kayma oldu: politika sayisi 4'ten 3'e indi (kullanicinin
    # dogrudan silme politikasi kaldirilinca) ama belge 4 demeye devam etti.
    import io as _io
    kur = _io.open(os.path.join(KOK, "KURULUM.md"), encoding="utf-8").read()
    s2 = []
    for satir in cikti.splitlines():
        m = re.search(r"NOTICE:\s+((?:Sema|Sayac|Katki tablosu|Sahiplenme) kuruldu[^\n]*)",
                      satir)
        if m and m.group(1).strip() not in kur:
            s2.append("KURULUM.md bu ciktiyi soz vermiyor: %r" % m.group(1).strip())
    if s2:
        return kayit("SQL davranisi (gercek Postgres)", s2)

    kayit("SQL davranisi (gercek Postgres)", [])


def main():
    betik_kontrolleri()
    tarayici_kontrolleri()
    sayfa_kontrolleri()
    sql_kontrolleri()
    kayit("degismez: katki alanlari dort dosyada ayni", alanlar_ayni_mi())
    kayit("degismez: veri, index ve vitrin tutarli", veri_tutarli_mi())
    kayit("degismez: sayfa meta ve sekme tutarli", sayfalar_tutarli_mi())
    kayit("degismez: sema korumalari yerinde", sema_tutarli_mi())
    kayit("degismez: sahne perdesi acilabiliyor", sahne_tutarli_mi())
    kayit("degismez: yayin yapilandirmasi", yayin_basliklari_mi())
    kayit("degismez: PWA ve Play parcalari", pwa_tutarli_mi())
    kayit("degismez: marka paleti okunur", palet_okunur_mu())
    kayit("degismez: yazi tipi indirilen ile kullanilan ayni",
          yazi_tipi_tutarli_mi())
    kayit("degismez: ana ekran butceyi olcum diye satmiyor", ana_ekran_butce_mi())
    kayit("degismez: her tur bir ciple secilebiliyor",
          turler_ulasilabilir_mi())
    kayit("degismez: fiyat kac olcumden geldigini soyluyor", fiyat_dayanagi_mi())
    kayit("degismez: guven skoru renk disinda da okunuyor", guven_skoru_mu())
    kayit("degismez: k-anonimlik esigi sunucuda da var", esik_iki_tarafta_ayni_mi())
    kayit("degismez: kombin mekanin kendi menusunden", kombin_mi())
    kayit("degismez: mekan sayfasi menuyu gosteriyor", menu_listesi_mi())
    kayit("degismez: harita karti maketteki gibi", harita_karti_mi())
    kayit("degismez: isletme sayfasi konumu gosteriyor", konum_paneli_mi())
    kayit("degismez: kazima kapisi platformlari eliyor", platform_kapisi_mi())
    kayit("degismez: sosyal bag isletmenin kendi sitesinden", site_sosyal_mi())
    kayit("degismez: seviye onayli katkiyi sayiyor", seviye_mi())
    kayit("degismez: butce talebi ifsa etmiyor", butce_talebi_mi())
    kayit("degismez: kurulum dosyalari depoda", kurulum_dosyalari_izleniyor_mu())
    kayit("degismez: kurulum belgesi eksiksiz",
          kurulum_belgesi_tam_mi())
    kayit("degismez: harita kutuphanesi yerelde",
          kutuphaneler_yerel_mi())
    kayit("degismez: gizlilik listesi CSP ile tutuyor",
          gizlilik_ucuncu_taraf_mi())
    kayit("degismez: donus adresi ve gunun tarihi", adres_ve_tarih_mi())
    kayit("degismez: sir sizmamis", sirlar_sizmis_mi())

    hata = atlanan = 0
    print()
    for ad, gecti, ayrinti in sonuc:
        if gecti is None:
            atlanan += 1
            print("  ATLANDI  %s" % ad)
            continue
        print("  %s %s" % ("gecti    " if gecti else "BASARISIZ", ad))
        if not gecti:
            hata += 1
            for a in ayrinti:
                for satir in str(a).splitlines():
                    print("      " + satir)
    toplam = len(sonuc) - atlanan

    # "--tam": ATLANDI da hata sayilir. CI bunu kullaniyor.
    #
    # Neden gerekli: bu depoda tam olarak bu sekilde bir kontrol curudu --
    # SQL davranis kontrolleri aylarca kosmadi ve kimse gormedi. Bir
    # kontrolu atlamak, olmamasiyla ayni sey; yerel makinede atlanabilir
    # olmasi makul (herkeste Postgres/Chromium olmayabilir), CI'da degil.
    if "--tam" in sys.argv and atlanan:
        print()
        for ad, gecti, ayrinti in sonuc:
            if gecti is None:
                print("  --tam: '%s' ATLANDI, CI'da atlama kabul edilmiyor" % ad)
        return 1

    print()
    if hata:
        print("%d/%d BASARISIZ%s" % (hata, toplam, (" · %d atlandi" % atlanan) if atlanan else ""))
    else:
        print("%d kontrol grubunun hepsi gecti%s"
              % (toplam, (" · %d atlandi" % atlanan) if atlanan else ""))
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
