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
            "menu_ocr.py", "menu_pdf_tara.py", "sahiplen.py", "site_haritasi.py"]

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


def main():
    betik_kontrolleri()
    tarayici_kontrolleri()
    kayit("degismez: katki alanlari dort dosyada ayni", alanlar_ayni_mi())
    kayit("degismez: veri, index ve vitrin tutarli", veri_tutarli_mi())
    kayit("degismez: sayfa meta ve sekme tutarli", sayfalar_tutarli_mi())
    kayit("degismez: sema korumalari yerinde", sema_tutarli_mi())
    kayit("degismez: yayin yapilandirmasi", yayin_basliklari_mi())
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
    print()
    if hata:
        print("%d/%d BASARISIZ%s" % (hata, toplam, (" · %d atlandi" % atlanan) if atlanan else ""))
    else:
        print("%d kontrol grubunun hepsi gecti%s"
              % (toplam, (" · %d atlandi" % atlanan) if atlanan else ""))
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
