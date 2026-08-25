# -*- coding: utf-8 -*-
"""Sahiplenme hedef motoru — iki cikti, iki ayri kanal.

1) sahiplenme_hedef.csv : TELEFONU OLAN isletmeler, eksige gore siralanmis.
   Kanal uzaktan iletisim. Envanterin ~%10'u.

2) sahiplenme_kume.csv  : NE WEBI NE TELEFONU OLAN isletmeler, yuruyus
   kumelerine ayrilmis ve kume icinde rota sirasina dizilmis. Envanterin
   ~%85'i burada ve bu kisma uzaktan ulasmanin yolu YOK.

Ikinci dosyanin varlik sebebi: 30 bin isletmeye tek kisi ulasamaz, ama bu
isletmeler cografi olarak dagilmis degil. 150 m yaricapli kumelerde onlarca
isletme yan yana duruyor; o zaman is "30 bin isletme" olmaktan cikip "N adet
yuruyus" oluyor. Sayilabilir hale gelen sey planlanabilir.

Mantik (iki dosyada da ayni): eksik veri hem BIZIM zayifligimiz (oneremiyoruz)
hem de ONUN kaybi (musteri goremiyor). Ayni cumle iki tarafi da tarif ediyor --
satis dili degil, olculen gercek.

UYARI: OSM'de "web yok" gorunmesi sitesi olmadigi anlamina GELMEZ; yalniz acik
veride kayitli degil demektir. Ikinci dosya bu yuzden bir MESAJ listesi degil,
bir ZIYARET listesidir -- dogrulama yerinde yapilir.
"""
import csv, glob, io, json, math, os, collections

import veri_bicim   # il dosyasi bicimi tek yerde

VERI = "app/veri"
CIKTI = "sahiplenme_hedef.csv"
KUME_CIKTI = "sahiplenme_kume.csv"

# Yuruyus kumesi yaricapi. 150 m = ayni caddenin iki yakasi; bir isletmeden
# otekine yurumek dakikadan kisa. Buyutmek kumeyi sisiriyor ama "tek
# yuruyus" olmaktan cikariyor, kucultmek ayni caddeyi ikiye boluyor.
KUME_YARICAP = 150

# Bu sayinin altindaki kume icin yola cikilmaz: gidis-donus, o kadar
# isletmeden alinacak veriden pahali. Tek basina duran isletme bu yuzden
# listeye hic girmiyor -- kasten.
KUME_ESIK = 8

# Kullaniciya en cok lazim olan alan en agir. Sirasi olculmedi, gerekce:
# "acik mi" sorusu her oneride soruluyor, menu yalniz fiyat filtresinde.
AGIRLIK = {"saat": 40, "tel": 25, "menu": 20, "adres": 10, "web": 5}

EKSIK_CUMLE = {
    "saat":  "acilis-kapanis saatiniz yazmiyor, sistem 'acik mi' diye soruldugunda sizi eleyip geciyor",
    "tel":   "telefonunuz yok, sayfayi goren kisi sizi arayamiyor",
    "menu":  "fiyat bilgisi yok, 'hesapli yer' arayan kullaniciya cikmiyorsunuz",
    "adres": "acik adres yok, yalniz haritada nokta olarak gorunuyorsunuz",
    "web":   "site veya sosyal medya bagi yok",
}

# Menu/fiyat sayfasi bu turler icin anlamli; muze icin degil.
YEME_ICME = {"Restoran", "Kafe", "Fast food", "Bar", "Pub", "Dondurma", "Pastane"}


# Turkce casefold tuzagi: "Istanbul".casefold() -> "i̇stanbul" (i + birlesen
# nokta), "istanbul" onun alt dizisi DEGIL. Klavyeden "Istanbul" yazan kullanici
# hicbir sey bulamiyordu. Karsilastirma icin harfleri ASCII'ye indiriyoruz --
# yalniz eslestirmede, gosterilen ad hep orijinal kaliyor.
_SADE = str.maketrans("çğıİöşüÇĞÖŞÜ", "cgiiosucgosu")


def sade(x):
    return (x or "").translate(_SADE).lower()


def ilce_haritasi():
    """osm_id -> ilce. Ilce bilgisi app/veri'de yok, ham CSV'de var (%20,1).

    CSV'de ayni ilce iki yazimla geciyor (Sariyer/sariyer, Merkez/merkez...):
    69 cift olcuLdu. Ilce bazli her rapor bundan bolunuyordu. Kanonik ad
    UYDURULMUYOR -- harf duzeltmesi Turkce'de tuzakli (istanbul -> Istanbul
    olur, Istanbul olmaz). Bunun yerine ayni yazimlarin EN SIK olani secilir:
    veriye dayali, tahmin yok."""
    import collections
    sayim = collections.Counter()
    ham = {}
    for dosya in ("turkiye_mekanlar.csv", "turkiye_eglence.csv"):
        if not os.path.exists(dosya):
            continue
        with io.open(dosya, encoding="utf-8-sig") as f:
            for x in csv.DictReader(f):
                ad = (x.get("ilce") or "").strip()
                if not ad:
                    continue
                sayim[ad] += 1
                ham[x["osm_id"]] = ad

    kanonik = {}
    for ad, n in sayim.items():
        k = ad.casefold()
        if k not in kanonik or n > sayim[kanonik[k]]:
            kanonik[k] = ad
    return {oid: kanonik[ad.casefold()] for oid, ad in ham.items()}


def yukle():
    ilce = ilce_haritasi()
    mekanlar = []
    for yol in sorted(glob.glob(os.path.join(VERI, "*.json"))):
        ad = os.path.basename(yol)
        if not ad[0].isdigit():
            continue
        d = veri_bicim.coz(json.load(io.open(yol, encoding="utf-8")))
        il = d.get("il", "")
        for m in d.get("mekanlar", []):
            m["il"] = il
            m["kod"] = ad[:2]
            m["ilce"] = ilce.get(m["id"], "")
            mekanlar.append(m)
    return mekanlar


def yogunluk_haritasi(mekanlar):
    """500 m'lik hucrelerde komsu sayisi. Talep vekili: kalabalik cadde =
    yoldan gecen musteri. O(n), tam mesafe degil -- hucre yeter."""
    HUCRE = 0.0055  # ~600 m enlem
    kova = collections.Counter()
    for m in mekanlar:
        kova[(int(m["lat"] / HUCRE), int(m["lon"] / HUCRE))] += 1
    for m in mekanlar:
        a, b = int(m["lat"] / HUCRE), int(m["lon"] / HUCRE)
        m["yogunluk"] = sum(kova[(a + i, b + j)]
                            for i in (-1, 0, 1) for j in (-1, 0, 1))
    return mekanlar


def bos_mu(m, k):
    """isletme.html icindeki eksikleriBul ile AYNI kurali uygular.
    Ikisi ayrisirsa isletmeye mesajda bir sey, sayfasinda baskasi soylenir --
    sistemin tek vaadi bu ikisinin ayni olmasi, o yuzden kural tek yerde."""
    if k == "menu":
        return m.get("tur") in YEME_ICME and m.get("min") is None
    # "Site / sosyal medya" instagrami da sayiyor: 194 mekanin instagrami
    # var ve sitesi yok. Onlara "sosyal medya baginiz yok" demek, elimizde
    # duran bilgiyi yok saymak olurdu.
    if k == "web":
        return not str(m.get("web", "")).strip() and not str(m.get("insta", "")).strip()
    return not str(m.get(k, "")).strip()


def degerlendir(m):
    eksik = [k for k in AGIRLIK if bos_mu(m, k)]
    m["eksik"] = eksik
    # Ham eksiklik agirligi. Tek isletmenin puani bunu yogunlukla carpiyor;
    # kume puani ise uyelerin bosluklarini topluyor (kume buyuklugu zaten
    # yogunlugun kendisi, ikinci kez carpmak ayni seyi iki kez saymak olurdu).
    m["bosluk"] = sum(AGIRLIK[k] for k in eksik)
    # yogunluk log ile yumusatilir: 200 komsulu cadde 20 komsuludan 10 kat
    # degerli degil, ~2 kat degerli.
    m["puan"] = round(m["bosluk"] * math.log1p(m["yogunluk"]), 1)
    return m


# ============================================================
# Yuruyus kumeleri — ulasilamayan %85 icin
# ============================================================

def metre(alat, alon, blat, blon):
    """Iki nokta arasi metre (haversine).

    Duz yaklasiklik degil: Turkiye 36-42 enlemleri arasinda ve boylam
    derecesinin metre karsiligi kuzeyde ~%8 kisaliyor. 150 m'lik esikte bu
    fark kume sinirini kaydirmaya yetiyor."""
    R = 6371000.0
    fa, fb = math.radians(alat), math.radians(blat)
    h = (math.sin((fb - fa) / 2) ** 2 +
         math.cos(fa) * math.cos(fb) * math.sin(math.radians(blon - alon) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def _izgara(mekanlar, yaricap):
    """Kaba izgara indeksi: yaricap taramasini O(n^2) olmaktan cikarir.

    Hucre boyu boylamda EN KUZEY enleme (42.1, Sinop ustu) gore secilir.
    Boylece hucre her enlemde en az yaricap kadar genis kalir ve 3x3 komsuluk
    daireyi her yerde kapsar. Guneyde hucre gereginden genis oluyor -- birkac
    fazla aday demek, kaciran sonuc degil."""
    dlat = yaricap / 111320.0
    dlon = yaricap / (111320.0 * math.cos(math.radians(42.1)))
    kova = collections.defaultdict(list)
    for m in mekanlar:
        kova[(int(m["lat"] / dlat), int(m["lon"] / dlon))].append(m)
    return kova, dlat, dlon


def kumele(mekanlar, yaricap=KUME_YARICAP, esik=KUME_ESIK):
    """Acgozlu kumeleme: en yogun noktadan basla, yaricapi topla, tekrarla.

    Izgara hucresine gore gruplama YAPILMIYOR. Hucre siniri iki metre yan
    yana duran iki isletmeyi ayri kumelere dusurebiliyor; sahada bu "ayni
    caddeyi iki kez yurumek" demek. Tohumdan yaricap saymak bu kusuru
    tasimiyor.

    Esigin altinda kalan tohum uyelerini TUKETMEZ: onlar daha sonra baska bir
    tohumun kumesine girebilsin. Aksi halde seyrek bir tohum, kenarindaki
    yogun kumeyi esik altina dusurup ikisini birden cope atiyordu."""
    kova, dlat, dlon = _izgara(mekanlar, yaricap)

    def komsular(m):
        a, b = int(m["lat"] / dlat), int(m["lon"] / dlon)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for k in kova.get((a + i, b + j), ()):
                    yield k

    def yakinlar(t, disinda):
        return [k for k in komsular(t) if k["id"] not in disinda
                and metre(t["lat"], t["lon"], k["lat"], k["lon"]) <= yaricap]

    # Tohum sirasi: yaricapinda en cok komsusu olan once. Esitligi id bozar --
    # ayni veri her calistirmada ayni kumeleri versin, rota tekrar uretilebilsin.
    for m in mekanlar:
        m["_yakin"] = len(yakinlar(m, frozenset()))
    sirali = sorted(mekanlar, key=lambda m: (-m["_yakin"], m["id"]))

    alinmis, kumeler = set(), []
    for t in sirali:
        if t["id"] in alinmis:
            continue
        uyeler = yakinlar(t, alinmis)
        if len(uyeler) >= esik:
            alinmis.update(k["id"] for k in uyeler)
            kumeler.append(uyeler)
    kumeler.sort(key=lambda u: -sum(m["bosluk"] for m in u))
    return kumeler


def baslangic(uyeler):
    """Kumenin sabit kapisi: en guneybatidaki uye. Rotanin nereden basladigi
    her uretimde ayni olmali, yoksa yarim kalan yuruyus ertesi gun baska bir
    siraya oturuyor."""
    return min(uyeler, key=lambda m: (m["lat"] + m["lon"], m["id"]))


def rota(uyeler):
    """Kume ici ziyaret sirasi: en guneybatidan basla, hep en yakina git.

    En kisa tur DEGIL (o NP-zor ve 20 durak icin gereksiz); komsuyu atlamayan
    bir sira. Baslangic sabit secilir ki ayni kume her uretimde ayni rotayi
    versin -- sahada yarim kalan liste ertesi gun ayni yerden devam etsin.

    Doner: [(mekan, bir onceki duraktan metre), ...]"""
    su = baslangic(uyeler)
    kalan = [x for x in uyeler if x["id"] != su["id"]]
    yol = [(su, 0)]
    while kalan:
        s = yol[-1][0]
        y = min(kalan, key=lambda m: (metre(s["lat"], s["lon"], m["lat"], m["lon"]), m["id"]))
        kalan = [x for x in kalan if x["id"] != y["id"]]
        yol.append((y, int(round(metre(s["lat"], s["lon"], y["lat"], y["lon"])))))
    return yol


def cap(uyeler):
    """Kumenin en uzak iki uyesi arasi metre. Yaricapin iki katini gecemez;
    gecerse kumeleme bozulmustur (kontrol() bunu sinar)."""
    return int(round(max(metre(a["lat"], a["lon"], b["lat"], b["lon"])
                         for a in uyeler for b in uyeler)))


def kume_adi(uyeler):
    """Kumenin etiketi. Ilce app/veri'de yok, ham CSV'den geliyor ve yalniz
    %20 dolu; kumede en cok gecen ad kullanilir, yoksa ad UYDURULMAZ."""
    say = collections.Counter(m["ilce"] for m in uyeler if m["ilce"])
    return say.most_common(1)[0][0] if say else "(ilce yok)"


def kanca(m):
    """Ilk mesajin ilk cumlesi. En agir tek eksigi soyler, liste saymaz."""
    if not m["eksik"]:
        return ""
    en = max(m["eksik"], key=lambda k: AGIRLIK[k])
    return EKSIK_CUMLE[en]


# Sahada not alinacak alanin kisa adi. kanca() bir MESAJ acilisi; kume
# dosyasinda ise ulasilamayanlarin %95'i ayni cumleyi aliyordu -- sabit sutun
# bilgi tasimaz. Ziyarette lazim olan sey ikna cumlesi degil, ne sorulacagi.
SORULACAK = {"saat": "acilis-kapanis", "tel": "telefon", "menu": "menu fiyati",
             "adres": "acik adres", "web": "site/sosyal medya"}


def sor(m):
    """Kapidan girince not alinacaklar, onem sirasina dizili."""
    return ", ".join(SORULACAK[k] for k in AGIRLIK if k in m["eksik"])


def kontrol():
    """Sessizce bozulursa filtre bos liste dondurur ve kimse fark etmez."""
    assert sade("İstanbul") == "istanbul"     # buyuk I noktali
    assert sade("Sarıyer") == "sariyer"       # tr harfleri
    assert sade("FATIH") == "fatih"
    assert sade("Istanbul") in sade("İstanbul")  # yazim farki eslesmeli
    assert sade(None) == ""

    # --- mesafe: bilinen bir uzunluga karsi ---
    # Ankara enleminde 0.001 derece enlem ~111 m. Yaricap esigi buna
    # dayaniyor; formul bozulursa kume ya sisiyor ya bosaliyor.
    assert 110 < metre(39.920, 32.854, 39.921, 32.854) < 112
    # Ayni boylam farki metreye daha AZ cevrilir (cos(enlem)); duz
    # yaklasiklik bunu kaciriyordu.
    assert metre(39.920, 32.854, 39.920, 32.855) < 86
    assert metre(39.920, 32.854, 39.920, 32.854) == 0

    # --- kumeleme ---
    def sahte(no, lat, lon):
        return {"id": "n/%d" % no, "lat": lat, "lon": lon, "bosluk": 100,
                "ilce": "", "il": "", "kod": "06", "tur": "Kafe", "ad": "m%d" % no,
                "eksik": ["saat"]}

    # Ayni noktada 10 isletme + 5 km otede 3 tane: bir kume cikmali, uzaktaki
    # ucu esigin altinda kaldigi icin listeye hic girmemeli.
    yakin = [sahte(i, 39.9200 + i * 0.00001, 32.8540) for i in range(10)]
    uzak = [sahte(100 + i, 39.9650, 32.8540) for i in range(3)]
    k = kumele(yakin + uzak, yaricap=150, esik=8)
    assert len(k) == 1, "tek kume beklenirdi: %d" % len(k)
    assert len(k[0]) == 10

    # Izgara hucresinin sinirinda yan yana duran iki nokta AYNI kumeye
    # dusmeli. Hucreye gore gruplayan bir surum burada iki kume uretiyordu.
    dlon = 150 / (111320.0 * math.cos(math.radians(42.1)))
    sinir = ([sahte(200 + i, 39.9200, dlon * 500 - 0.000002 * i) for i in range(5)] +
             [sahte(210 + i, 39.9200, dlon * 500 + 0.000002 * i) for i in range(5)])
    assert len(kumele(sinir, yaricap=150, esik=8)) == 1, "hucre siniri kumeyi boldu"

    # Cap yaricapin iki katini asamaz.
    assert cap(k[0]) <= 2 * 150

    # --- rota ---
    # Duz bir dizide sira bastan sona olmali, zikzak degil.
    dizi = [sahte(300 + i, 39.9200 + i * 0.0002, 32.8540) for i in range(5)]
    y = rota(dizi)
    assert [m["id"] for m, _ in y] == ["n/%d" % (300 + i) for i in range(5)]
    assert y[0][1] == 0                       # ilk durakta adim yok
    assert all(0 < a < 30 for _, a in y[1:])  # ~22 m'lik adimlar
    assert len(rota(dizi)) == len(dizi)       # kimse dusmuyor, kimse iki kez yok


def main(secili_il=None, secili_ilce=None):
    kontrol()
    mekanlar = yogunluk_haritasi(yukle())
    for m in mekanlar:
        degerlendir(m)

    # Ulasilabilir = telefonu var. Telefonsuza mesaj atilamaz, listeye girmez.
    hedef = [m for m in mekanlar if str(m.get("tel", "")).strip() and m["eksik"]]
    if secili_il:
        hedef = [m for m in hedef if sade(secili_il) in sade(m["il"])]
    if secili_ilce:
        hedef = [m for m in hedef if sade(secili_ilce) in sade(m["ilce"])]
    hedef.sort(key=lambda m: -m["puan"])

    with io.open(CIKTI, "w", encoding="utf-8-sig", newline="") as f:
        y = csv.writer(f)
        y.writerow(["puan", "il", "ilce", "tur", "ad", "tel", "eksikler", "kanca",
                    "yogunluk", "sayfa", "dogrulandi_mi"])
        for m in hedef:
            y.writerow([m["puan"], m["il"], m["ilce"], m["tur"], m["ad"], m.get("tel", ""),
                        "+".join(m["eksik"]), kanca(m), m["yogunluk"],
                        "/isletme.html?il=" + m["kod"] + "&id=" + m["id"], ""])

    print("ulasilabilir hedef : %d  ->  %s" % (len(hedef), CIKTI))
    print("toplam mekan       : %d" % len(mekanlar))
    print()
    print("--- en agir eksik, kac isletmede ---")
    say = collections.Counter()
    for m in mekanlar:
        for k in m["eksik"]:
            say[k] += 1
    for k, n in say.most_common():
        print("  %-6s %6d  (%%%.1f)" % (k, n, 100.0 * n / len(mekanlar)))
    print()
    print("--- hedef listesi ilce bazinda ilk 10 ---")
    for (il, ilc), n in collections.Counter(
            (m["il"], m["ilce"] or "(ilce yok)") for m in hedef).most_common(10):
        print("  %-24s %4d" % (ilc + ", " + il, n))
    print()
    print("UYARI: 'web yok' OSM'de kayitli olmadigi anlamina gelir, sitesi")
    print("olmadigi anlamina GELMEZ. Mesaj oncesi elle dogrula, dogrulandi_mi")
    print("sutununu doldur. Dogrulanmamis listeye mesaj atma.")

    kume_uret(mekanlar, secili_il, secili_ilce)


def kume_uret(mekanlar, secili_il=None, secili_ilce=None):
    """Ikinci kanal: ne webi ne telefonu olanlar -> yuruyus kumeleri."""
    # Uzaktan ulasilamayanlar: ne site, ne telefon, ne instagram.
    # bos_mu("web") instagrami zaten sayiyor, o yuzden burada ayrica
    # yazmaya gerek yok -- ama SAYISI raporlaniyor, cunku instagrami olup
    # telefonu olmayan mekan iki listeye de girmiyor ve gozden kaybolabilir.
    ulasilamaz = [m for m in mekanlar if bos_mu(m, "web") and bos_mu(m, "tel")]
    yalniz_insta = [m for m in mekanlar
                    if str(m.get("insta", "")).strip()
                    and not str(m.get("web", "")).strip()
                    and bos_mu(m, "tel")]
    if secili_il:
        ulasilamaz = [m for m in ulasilamaz if sade(secili_il) in sade(m["il"])]
    if secili_ilce:
        ulasilamaz = [m for m in ulasilamaz if sade(secili_ilce) in sade(m["ilce"])]

    kumeler = kumele(ulasilamaz)

    with io.open(KUME_CIKTI, "w", encoding="utf-8-sig", newline="") as f:
        y = csv.writer(f)
        y.writerow(["kume", "sira", "adim_m", "il", "ilce", "tur", "ad",
                    "sor", "lat", "lon", "sayfa", "ziyaret_edildi_mi"])
        for no, uyeler in enumerate(kumeler, 1):
            for sira, (m, adim) in enumerate(rota(uyeler), 1):
                y.writerow([no, sira, adim, m["il"], m["ilce"], m["tur"], m["ad"],
                            sor(m), m["lat"], m["lon"],
                            "/isletme.html?il=" + m["kod"] + "&id=" + m["id"], ""])

    kapsanan = sum(len(u) for u in kumeler)
    print()
    print("=" * 60)
    print("ulasilamaz (web/tel/insta yok): %d" % len(ulasilamaz))
    print("  yalniz instagrami olan     : %d  (iki listeye de girmiyor -- "
          "DM ile ulasilabilir)" % len(yalniz_insta))
    print("yuruyus kumesi             : %d  (>=%d isletme, %d m yaricap)"
          % (len(kumeler), KUME_ESIK, KUME_YARICAP))
    print("kumelerde kapsanan isletme : %d  (ulasilamazlarin %%%.1f'i)  ->  %s"
          % (kapsanan, 100.0 * kapsanan / max(len(ulasilamaz), 1), KUME_CIKTI))
    if not kumeler:
        return
    print()
    print("--- en degerli 12 yuruyus ---")
    print("  %-3s %-13s %-18s %5s %5s %6s" % ("no", "il", "ilce", "adet", "cap", "puan"))
    for no, u in list(enumerate(kumeler, 1))[:12]:
        ilk = baslangic(u)
        print("  %-3d %-13s %-18s %5d %4dm %6d   %.5f,%.5f"
              % (no, ilk["il"][:13], kume_adi(u)[:18], len(u), cap(u),
                 sum(m["bosluk"] for m in u), ilk["lat"], ilk["lon"]))
    print()
    print("Son iki sutun ilk duragin koordinati: haritaya yapistirinca rota")
    print("oradan basliyor. Kume icindeki sira sabit -- yarim kalan yuruyus")
    print("ertesi gun ayni yerden devam eder.")
    print()
    print("UYARI: bu bir MESAJ listesi degil, ZIYARET listesi. Bu isletmelerin")
    print("acik veride telefonu yok; olmadigi anlamina gelmez. Iletisim bilgisi")
    print("yerinde ogrenilir, ucuncu bir kaynaktan kazinmaz.")


if __name__ == "__main__":
    import sys
    # "test": yalniz kendini kontrol et, veri okuma ve CSV yazma yok.
    # Diger betiklerle ayni arayuz olsun diye eklendi (test.py hepsini
    # ayni sekilde cagiriyor).
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        kontrol()
        print("kontrol gecti: turkce sadelestirme, mesafe, kumeleme, rota")
        sys.exit(0)
    main(sys.argv[1] if len(sys.argv) > 1 else None,
         sys.argv[2] if len(sys.argv) > 2 else None)
