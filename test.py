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

KOK = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(KOK, "app", "veri")

# Kendi kontrolu olan betikler. Hepsi "test" argumanini ayni sekilde anliyor.
BETIKLER = ["app_veri.py", "etkinlik_cek.py", "fiyat_analiz.py", "menu_cikar.py",
            "turkiye_cek.py",
            "menu_ocr.py", "menu_pdf_tara.py", "saha.py", "sahiplen.py",
            "site_haritasi.py"]

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
    for kod in dosyalar:
        d = json.loads(oku("app", "veri", kod + ".json"))
        for m in d.get("mekanlar", []):
            toplam += 1
            kalem += len(m.get("menu") or [])
            if m.get("min") is not None:
                fiyatli += 1
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
        d = json.loads(oku("app", "veri", kod + ".json"))
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
    for anahtar, gercek in (("toplam", toplam), ("kalem", kalem), ("fiyatliMekan", fiyatli)):
        if v.get(anahtar) != gercek:
            s.append("vitrin.json %s=%s ama veride %s — vitrin_uret.py calistir"
                     % (anahtar, v.get(anahtar), gercek))

    # Anasayfadaki SABIT yedekler: JS kapaliyken gorunen sayi bunlar.
    ana = oku("app", "index.html")
    for kimlik, gercek in (("d-toplam", toplam), ("d-kalem", kalem), ("d-fiyatli", fiyatli)):
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

    CSP BILEREK YOK: Supabase adresi kuruluma gore degisiyor
    (yapilandirma.js), yani depoda sabit bir CSP yazmak baska bir Supabase
    projesiyle kuran kisinin girisini sessizce kirardi.
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
                    "X-Frame-Options", "Permissions-Policy"):
        if gerekli not in basliklar:
            s.append("vercel.json: %s basligi yok" % gerekli)
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
                                 ("yorum", "yorum: 20 kontrolun hepsi gecti"))
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
