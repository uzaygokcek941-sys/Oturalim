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
            "ikon_uret.py", "sw_uret.py", "assetlinks_uret.py"]

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
    for ad in sorted(glob.glob(os.path.join(KOK, "app", "*.html"))):
        h = io.open(ad, encoding="utf-8").read()
        for yazan in set(re.findall(r"(\d{2}\.\d{3}) mekan", h)):
            if yazan.replace(".", "") != str(toplam):
                s.append("%s: metinde '%s mekan' yaziyor, gercek %s"
                         % (os.path.basename(ad), yazan, "{:,}".format(toplam).replace(",", ".")))

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

    kesfet = oku("app", "kesfet.html")
    if kesfet.count("integrity=") != 2:
        s.append("kesfet.html: Leaflet css+js icin iki integrity bekleniyordu, %d var"
                 % kesfet.count("integrity="))

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

    koyu = css[css.index(":root{"):css.index("@media (prefers-color-scheme:light)")]
    acik = css[css.index(':root[data-tema="acik"]{'):]
    acik = acik[:acik.index("}")]

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

    # Iki ACIK TEMA blogu (sistem tercihi + elle secim) ayni degerleri
    # tasimali; ayrisirlarsa elle secilen tema sistemden farkli gorunur.
    sistem = css[css.index("@media (prefers-color-scheme:light)"):
                 css.index(':root[data-tema="acik"]{')]
    ayikla = lambda b: sorted(re.findall(r"(--[\w-]+):\s*([^;]+);", b))
    a1, a2 = ayikla(sistem), ayikla(acik)
    if a1 != a2:
        fark = set(a1) ^ set(a2)
        s.append("iki acik tema blogu ayrisiyor: %s" % sorted(fark)[:4])

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
    for parca, ne in (('id="cep"', "butce formu"),
                      ('id="butce-girdi"', "butce yazi alani"),
                      ('id="butceler"', "hazir butce cipleri"),
                      ('id="canim"', "kategori cipleri"),
                      ('id="butce-ozet"', "olcum/tahmin satiri")):
        if parca not in ham:
            s.append("index.html: %s yok (%s)" % (ne, parca))

    # --- rakamlar ve tur adlari TEK yerde
    if "const BUTCE_SECENEK" not in ortak:
        s.append("ortak.js: BUTCE_SECENEK yok")
    if "const CANIM" not in ortak:
        s.append("ortak.js: CANIM (kategori listesi) yok")
    if "BUTCE_SECENEK.map" not in ix:
        s.append("index.html: butce cipleri BUTCE_SECENEK'ten cizilmiyor")
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
    eksik = [ad for ad, imza in (("sahiplenme", "20 kontrolun hepsi gecti"),
                                 ("sayac", "sayac: 11 kontrolun hepsi gecti"),
                                 ("yorum", "yorum: 20 kontrolun hepsi gecti"),
                                 ("menu katkisi", "menu katkisi: 12 kontrolun hepsi gecti"),
                                 ("mekan fotografi", "mekan fotografi: 12 kontrolun hepsi gecti"),
                                 ("akran", "akran_test: 11 adimin hepsi gecti"))
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
    kayit("degismez: ana ekran butceyi olcum diye satmiyor", ana_ekran_butce_mi())
    kayit("degismez: fiyat kac olcumden geldigini soyluyor", fiyat_dayanagi_mi())
    kayit("degismez: guven skoru renk disinda da okunuyor", guven_skoru_mu())
    kayit("degismez: k-anonimlik esigi sunucuda da var", esik_iki_tarafta_ayni_mi())
    kayit("degismez: kurulum dosyalari depoda", kurulum_dosyalari_izleniyor_mu())
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
