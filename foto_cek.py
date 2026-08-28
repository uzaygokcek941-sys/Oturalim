#!/usr/bin/env python3
"""Mekanlar icin SERBEST LISANSLI fotograf toplar (Wikimedia Commons).

Kullanim:
    python foto_cek.py TR-06                 # tek il
    python foto_cek.py                       # 81 il
    python foto_cek.py test                  # aga cikmadan mantik kontrolu

ham/ KLASORU GEREKMIYOR. Ilk yazimda turkiye_cek.py'nin urettigi dev
dokumu okuyordu; o dokum 81 il icin SAATLER suruyor ve depoda durmuyor.
Oysa bize gereken sey menunun tamami degil, YALNIZ fotograf etiketi
tasiyan mekanlar -- Overpass'a onu soran sorgu kucuk ve saniyeler suruyor.
ham/ varsa yine de oradan okunuyor (aga hic cikmadan).

Cikti:
    mekan_foto.csv        -- mekan_id, adres, yazar, lisans, kaynak_bag
    foto_ekle.sql        -- Supabase'e yapistirilacak insert'ler (gitignore)

NEDEN BU KAYNAK, BASKASI DEGIL
==============================
Google Maps, TripAdvisor, Foursquare ve benzeri yerlerdeki fotograflar
YAZARLARININ TELIFINDE ve o platforma lisansli. Kendi sitende yayimlama
hakkin yok; Places API'nin kendi sartlari bile fotografi ve yorumu
onbellekte tutmayi ve harita disinda gostermeyi yasakliyor. Bu teknik bir
zorluk degil, ihtarname sebebi -- CEBIMDE.md "Yapilmayacaklar" listesinde
yazili bir karar.

Wikimedia Commons FARKLI: oradaki dosyalar serbest lisansli (CC0, CC BY,
CC BY-SA) ve yeniden yayimlanabilir. KARSILIGINDA ATIF ZORUNLU: yazar adi
ve lisans gosterilmeli. Bu betik atifi TOPLAMADAN fotograf yazmiyor ve
veritabani kisiti da atifsiz satiri kabul etmiyor (foto_ekle.sql).

BEKLENEN KAPSAM DUSUK, bunu bastan soyluyorum
=============================================
Commons'ta anit, cami, tarihi yapi ve muze bol; mahalle kafesi yok
denecek kadar az. Bu betik "her mekana fotograf" getirmiyor; getirdigi
sey, getirebildigi kadari. Sayfalari asil dolduracak olan kullanici ve
DOGRULANMIS ISLETME SAHIBI yuklemeleri (veritabani/foto_ekle.sql).
Kac mekan kapsandigi kosum sonunda YAZIYOR -- tahmin degil, sayim.

UC ETIKET, UC AYRI YOL (OSM'de):
    image=<adres>              -> dogrudan adres; Commons'ta ise atif alinir,
                                  degilse ATLANIR (lisansi bilinmiyor)
    wikimedia_commons=File:X   -> dogrudan dosya
    wikidata=Q123              -> P18 (image) ozelligi uzerinden dosya
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse

# UC SUNUCU, ucu de ayni Overpass API'sini konusuyor.
# 26-27 Agustos kosumunda 81 ilin 20'si (%25) 429/504 ile dustu. 429 "cok
# istedin" demek ve SUNUCUYA OZEL: ayni sorgu bir aynadan gecebiliyor.
# Tek adrese baglilik bu depoda ZATEN bir kez yandi (kutuphane_al.py,
# esm.sh) ve cozum orada da adresi degistirmek degil, ADAY LISTESI olmustu.
SUNUCULAR = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

# GECICI kodlar; yalniz bunlar yeniden deneniyor.
# 400 BURADA YOK ve olmamali: Overpass 400'u BOZUK SORGU icin donduruyor.
# Onu denemek ayni bozuk sorguyu uc kez baskasinin sunucusuna gondermek
# olur -- ve bozuklugu bir de gecikmeyle ogrenirsin.
GECICI = (429, 502, 503, 504)

# Sunucu "Retry-After" yazarsa ona uyuluyor, ama SINIRSIZ degil: ariza
# aninda saatlik degerler donebiliyor ve bu tur 81 il suruyor.
EN_COK_BEKLEME = 60

# TEK ILIN TOPLAM BUTCESI (saniye). DENEMEYI EKLEMEK BIR TUZAK ACIYOR:
# 3 deneme x 3 sunucu x 200 sn zaman asimi = TEK il 30 dakika. Eski kodda
# bu tuzak yoktu cunku hic denemiyordu -- dusen il 200 sn'ye maloluyordu.
# 81 il icin carpim is akisinin 300 dakikalik sinirini asar ve tur
# ORTASINDA kesilir; yani "daha cok deneyelim" derken elde HIC sonuc
# kalmayabilirdi.
#
# 429 BU BUTCEYI NEREDEYSE HIC HARCAMIYOR ve asil dert oydu: hiz siniri
# yaniti ANINDA donuyor, yani gercek 429 durumunda 3x3'un tamami
# kullanilabiliyor. Butce yalniz ZAMAN ASIMI durumunu kesiyor -- orada
# ikinci bir aynaya sorulup birakiliyor.
IL_BUTCESI = 420

# TURUN TOPLAM BUTCESI (saniye). Tek ilin butcesi TURU KURTARMIYOR:
# 81 il x 420 sn = 9,4 saat, oysa veri.yml'nin is siniri 300 DAKIKA.
# Kosucu turu tam ortasinda kesse betik CSV'yi HIC yazamazdi -- yani
# daha yeni kapattigimiz kopuk halka geri gelirdi.
#
# Butce dolunca kalan iller "cekilemedi" sayiliyor ve ozet zaten "Sayilar
# EKSIK" yaziyor. Bu depoda kural: basarisizligi sayiya cevirme. Yarim
# tur yarim yaziliyor, tam gibi degil.
#
# 200 dakika: 300'luk isin geri kalani (uygulama verisi, kontroller,
# dala yazma) icin pay birakiyor.
TUR_BUTCESI = 200 * 60

# Secicileri turkiye_cek.py ve eglence_cek.py'den ALIYORUZ, kopyalamiyoruz:
# uc yerde uc ayri liste, birinin guncellenip otekilerin unutulmasi demekti.
# (import modul duzeyinde: iki betik de aga cikmadan import edilebiliyor.)
# Bekleme ve deneme sayisi da turkiye_cek'ten GELIYOR, kopyalanmiyor.
# Ayni Overpass'a iki betik iki turlu gidiyordu: turkiye_cek uc kez
# deniyor ve iller arasi 4 sn bekliyor, burasi hic denemiyor ve 0,34 sn
# bekliyordu -- 0,34 Wikimedia'nin hiz siniri, Overpass'in degil.
from turkiye_cek import (AMENITY as YEME_AMENITY,
                         BEKLEME as OVERPASS_BEKLEME,
                         DENEME as OVERPASS_DENEME)
from eglence_cek import AMENITY as EGLENCE_AMENITY, LEISURE, TOURISM

import veri_bicim   # il dosyasi bicimi tek yerde

# Yalniz FOTOGRAF ETIKETI tasiyan mekanlar. Uc etiketin uclu de ayri
# sorgu satiri; Overpass'ta "su etiketlerden herhangi biri" diye tek
# satirda yazilamiyor.
FOTO_ETIKET = ("image", "wikimedia_commons", "wikidata")

COMMONS = "https://commons.wikimedia.org/w/api.php"
WIKIDATA = "https://www.wikidata.org/w/api.php"
BEKLEME = 0.34          # saniye; Wikimedia'nin istedigi hiz siniri
YIGIN = 40              # tek istekte sorulan dosya sayisi (API siniri 50)
KULLANICI_AJANI = "Cebimde/0.1 (https://oturalim.vercel.app; menu fiyat projesi)"

ALANLAR = ["mekan_id", "il", "mekan_ad", "adres", "yazar", "lisans", "kaynak_bag"]

# Yeniden yayimlanabilir lisanslar. Listede OLMAYAN her sey ATILIYOR --
# "muhtemelen serbesttir" diye bir sey yok. Commons'ta lisansi belirsiz ya
# da yalniz "adil kullanim" olan dosyalar da var.
# NC (ticari kullanim yasak) ve ND (turetme yasak) BURADA YOK ve olmamali.
# Bu site reklamsiz ama ticari sayilabilir; ayrica fotograflar kucultulerek
# gosteriliyor, ki ND acisindan turetme sayilabilir. Ikisi de "belki
# olur"; yanlis yayimlamanin bedeli hukuki, o yuzden ikisi de disarida.
#
# Kalip $ ile BITIYOR. Ilk yazimda yalniz ^ vardi ve "CC BY-NC 4.0"
# onekten eslesip SERBEST sayiliyordu -- kendi kontrolum yakaladi.
# ONCE REDDET, SONRA IZIN VER. Tek bir "serbest kalibi" yazmayi iki kez
# denedim, ikisi de NC'yi (ticari kullanim yasak) iceri aldi -- kalip
# "CC BY" onekini gorup gerisini yutuyor. Kalibi akillandirmak yerine
# yasakli isaretleri AYRI ve once eliyorum: bir lisansi yanlislikla
# serbest saymanin bedeli hukuki, yanlislikla elemenin bedeli bir eksik
# fotograf.
#
# NC ve ND neden disarida: bu site reklamsiz ama ticari sayilabilir;
# ayrica fotograflar kucultulerek gosteriliyor, ki ND acisindan turetme
# sayilabilir. Ikisi de "belki olur" -- yeterli degil.
YASAK = re.compile(r"(^|[ \-_])(nc|nd|noncommercial|noderiv\w*)([ \-_]|$)", re.I)

SERBEST = re.compile(
    r"^(cc0([ \-][0-9.]+)?"
    r"|cc[ \-]by([ \-]sa)?([ \-][0-9.]+)?"
    r"|public domain.*"
    r"|pd[ \-].*"
    r"|gfdl([ \-][0-9.]+)?"
    r"|attribution"
    r"|fal)$", re.I)


def sorgu(kod):
    """Bir ilin FOTOGRAF ETIKETLI mekanlari. Kucuk sorgu, saniyeler surer.

    turkiye_cek.py'nin sorgusu ilin BUTUN mekanlarini istiyor ve 81 il
    icin saatler suruyor. Burada aranan sey cok daha dar: uc etiketten
    birini tasiyan mekanlar. Turkiye'de bu mekanlarin binde birkacini
    geciyor, yani yanit da o kadar kucuk.
    """
    parcalar = []
    for aile, kalip in (("amenity", YEME_AMENITY), ("amenity", EGLENCE_AMENITY),
                        ("leisure", LEISURE), ("tourism", TOURISM)):
        for etiket in FOTO_ETIKET:
            parcalar.append('nwr["%s"~"%s"]["%s"](area.a);' % (aile, kalip, etiket))
    return ('[out:json][timeout:180];area["ISO3166-2"="%s"]->.a;(%s);out center tags;'
            % (kod, "".join(parcalar)))


def _sunucu_adi(adres):
    return urllib.parse.urlsplit(adres).netloc or adres


def _bekleme_suresi(yanit, varsayilan):
    """Sunucu "Retry-After" yazdiysa ONA uyuluyor.

    429 "cok istedin" demek ve Overpass ne kadar bekleyecegini SOYLUYOR.
    Kendi sayimizi dayatmak iki turlu de yanlis: erken donersen yine 429
    alirsin, gec donersen bosuna beklersin."""
    ham = (getattr(yanit, "headers", None) or {}).get("Retry-After", "")
    try:
        s = float(str(ham).strip())
    except (TypeError, ValueError):
        return varsayilan
    if s <= 0:
        return varsayilan
    return min(s, EN_COK_BEKLEME)


def overpass_iste(sorgu_metni):
    """Overpass'a sor, JSON metnini dondur. Butun yollar tukenirse catlar.

    Onceden burada TEK istek vardi: 429 gelince il "cekilemedi" sayiliyor
    ve bir daha denenmiyordu. Bir sonraki il de hemen 0,34 sn sonra
    soruluyordu, yani sunucu bizi yavaslatmaya calisirken biz hizimizi
    hic degistirmiyorduk."""
    import httpx
    son = "?"
    baslangic = time.monotonic()
    for deneme in range(1, OVERPASS_DENEME + 1):
        for adres in SUNUCULAR:
            gecen = time.monotonic() - baslangic
            if gecen >= IL_BUTCESI:
                raise RuntimeError("il butcesi doldu (%d sn, son: %s)"
                                   % (IL_BUTCESI, son))
            varsayilan = OVERPASS_BEKLEME * deneme
            try:
                with httpx.Client(timeout=200,
                                  headers={"User-Agent": KULLANICI_AJANI}) as c:
                    y = c.post(adres, data={"data": sorgu_metni})
            except Exception as e:               # ag koptu ya da zaman asti
                son = "%s: %s" % (_sunucu_adi(adres), str(e)[:40])
                time.sleep(varsayilan)
                continue
            if getattr(y, "status_code", 0) == 200:
                return y.text
            son = "%s: HTTP %s" % (_sunucu_adi(adres), getattr(y, "status_code", "?"))
            if y.status_code not in GECICI:
                raise RuntimeError(son)
            time.sleep(_bekleme_suresi(y, varsayilan))
    raise RuntimeError("%d deneme x %d sunucu tukendi (son: %s)"
                       % (OVERPASS_DENEME, len(SUNUCULAR), son))


def overpass_oku(kod):
    """Overpass yanitindan fotograf etiketi tasiyan mekanlar."""
    return _elemanlari_coz(json.loads(overpass_iste(sorgu(kod))))


def _elemanlari_coz(veri):
    """Overpass/ham JSON -> mekan listesi. Ikisi de ayni bicimde."""
    cikti = []
    for el in veri.get("elements", []):
        t = el.get("tags") or {}
        ad = t.get("name")
        if not ad:
            continue
        cikti.append({
            "mekan_id": "%s/%s" % (el["type"], el["id"]),
            "mekan_ad": ad,
            "image": t.get("image", ""),
            "commons": t.get("wikimedia_commons", ""),
            "wikidata": t.get("wikidata", ""),
        })
    return cikti


def bizdeki_mekanlar():
    """app/veri/*.json icindeki mekan kimlikleri.

    Overpass bize UYGULAMADA OLMAYAN mekanlar da dondurebiliyor (secici
    ayni ama veri farkli gunde cekilmis olabilir). Onlara fotograf
    yazmak, hicbir sayfada gorunmeyecek satirlar biriktirmek olurdu."""
    import glob as _glob
    kimlik = {}
    for yol in _glob.glob(os.path.join("app", "veri", "*.json")):
        ad = os.path.basename(yol)
        if ad in ("index.json", "etkinlik.json", "vitrin.json", "fiyat_olcut.json"):
            continue
        with open(yol, encoding="utf-8") as f:
            d = veri_bicim.coz(json.load(f))
        for m in d.get("mekanlar", []):
            kimlik[m["id"]] = ad[:-5]        # il kodu
    return kimlik


def _guvenli_dosya_adi(ham):
    """OSM etiketinden Commons dosya adi. Cozulemezse None.

    Etiket uc bicimde geliyor ve ucu de gercek veride var:
        "File:Kafe.jpg"
        "Kafe.jpg"
        "https://commons.wikimedia.org/wiki/File:Kafe.jpg"
    Kategori ("Category:...") bir DOSYA degil; reddediliyor.
    """
    v = (ham or "").strip()
    if not v:
        return None
    v = re.sub(r"^https?://", "", v, flags=re.I)
    v = re.sub(r"^(commons\.)?(m\.)?wikimedia\.org/wiki/", "", v, flags=re.I)
    v = urllib.parse.unquote(v)
    v = v.split("?")[0].split("#")[0].strip()
    if v.lower().startswith("category:"):
        return None
    if not v.lower().startswith("file:"):
        v = "File:" + v
    ad = v[5:].strip()
    if not ad or "/" in ad:
        return None
    # Yalniz resim uzantilari: Commons'ta ses ve video da var.
    if not re.search(r"\.(jpe?g|png|webp|gif|tiff?)$", ad, re.I):
        return None
    return "File:" + ad


def lisans_serbest_mi(kisa_ad):
    """Lisans yeniden yayimlanabilir mi. Bilinmiyorsa HAYIR."""
    v = (kisa_ad or "").strip()
    if not v or YASAK.search(v):
        return False
    return bool(SERBEST.match(v))


def _temiz_yazar(ham):
    """Commons yazar alani HTML tasiyor ("<a href=...>Ad</a>"); metne indir.

    HIC ISIM DUSURULMUYOR ve bu kural burada mutlak: atif ZORUNLU, yani
    temizlik bir ismi kirpiyorsa temizlik degil IHLAL olur. Asagidaki iki
    kural yalnizca ISIM OLMAYAN parcalari atiyor.

    Olculdu (27 Agustos, 84 satirlik gercek tur): 3 satir (%3,6) kirliydi
    ve ucu de ayri desendi:
      "Agora_vue_generale.jpg: Didier Laroche derivative work: IgnisFatuus"
      "Unknown authorUnknown author"
      "Sevki Balmumcu as an exhibition house in 1933, Paul Bonatz ..."
    Ucuncusu KIRLI DEGIL: Commons'ta o alan gercekten boyle yazilmis,
    icinde iki gercek isim var. Ona DOKUNULMUYOR."""
    v = re.sub(r"<[^>]+>", "", ham or "")
    v = re.sub(r"\s+", " ", v).strip()

    # 1) DOSYA ADI ONEKI. Commons'un "derivative work" kalibi ozgun
    #    dosyanin ADIYLA basliyor: "X.jpg: Ali derivative work: Veli".
    #    Dosya adi bir YAZAR DEGIL; sonrasi oldugu gibi kaliyor, yani
    #    turetme zincirindeki iki isim de duruyor.
    v = re.sub(r"^[^\s:]+\.(?:jpe?g|png|webp|gif|tiff?):\s*", "", v, flags=re.I)

    # 2) BIREBIR IKIYE KATLANMIS METIN. Commons bazi kaliplarda ayni adi
    #    hem bagda hem metinde donduruyor ve etiketler silinince
    #    yapisiyor: "Unknown authorUnknown author".
    #    KOSUL DAR TUTULDU: tam ikiye katlanmis ve yarisi en az 4 karakter.
    #    Genis bir kural gercek bir adi yarilayabilirdi.
    n = len(v)
    if n >= 8 and n % 2 == 0 and v[: n // 2] == v[n // 2:]:
        v = v[: n // 2]

    return v[:200] or None


def kayit_kur(mekan, bilgi):
    """API yanitindan CSV satiri. Atif eksikse None -- atifsiz yayimlanmaz."""
    if not bilgi:
        return None
    yazar = _temiz_yazar(bilgi.get("yazar"))
    lisans = (bilgi.get("lisans") or "").strip()
    adres = (bilgi.get("adres") or "").strip()
    sayfa = (bilgi.get("sayfa") or "").strip()
    if not (yazar and lisans and adres and sayfa):
        return None
    if not lisans_serbest_mi(lisans):
        return None
    return {
        "mekan_id": mekan["mekan_id"],
        "il": mekan.get("il", ""),
        "mekan_ad": mekan["mekan_ad"],
        "adres": adres,
        "yazar": yazar,
        "lisans": lisans,
        "kaynak_bag": sayfa,
    }


def _istek(adres, parametre):
    """Tek GET. httpx modul duzeyinde import EDILMIYOR: kontroller aga
    cikmadan kosabilsin (bu depoda betiklerin yarisi o yuzden test
    edilemiyordu)."""
    import httpx
    with httpx.Client(timeout=30, headers={"User-Agent": KULLANICI_AJANI},
                      follow_redirects=True) as c:
        y = c.get(adres, params=parametre)
        y.raise_for_status()
        return y.json()


def commons_bilgi(dosyalar):
    """Commons dosya adlari -> {dosya: {adres, yazar, lisans, sayfa}}."""
    if not dosyalar:
        return {}
    veri = _istek(COMMONS, {
        "action": "query", "format": "json", "formatversion": "2",
        "titles": "|".join(dosyalar),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "1200",
    })
    cikti = {}
    for s in (veri.get("query", {}).get("pages") or []):
        if s.get("missing"):
            continue
        bilgi = (s.get("imageinfo") or [{}])[0]
        ust = bilgi.get("extmetadata") or {}
        al = lambda k: (ust.get(k) or {}).get("value")
        cikti[s.get("title")] = {
            # thumburl: 1200 px'e kucultulmus hali. Tam boy dosya 20 MB
            # olabiliyor ve sayfayi kilitlerdi.
            "adres": bilgi.get("thumburl") or bilgi.get("url"),
            "yazar": al("Artist"),
            "lisans": al("LicenseShortName"),
            "sayfa": bilgi.get("descriptionurl"),
        }
    return cikti


def wikidata_gorselleri(kimlikler):
    """Wikidata Q-kimlikleri -> {Q: "File:..."} (P18 ozelligi)."""
    if not kimlikler:
        return {}
    veri = _istek(WIKIDATA, {
        "action": "wbgetentities", "format": "json", "formatversion": "2",
        "ids": "|".join(kimlikler), "props": "claims",
    })
    cikti = {}
    for q, govde in (veri.get("entities") or {}).items():
        for iddia in ((govde.get("claims") or {}).get("P18") or []):
            deger = (((iddia.get("mainsnak") or {}).get("datavalue") or {})
                     .get("value"))
            if isinstance(deger, str) and deger.strip():
                cikti[q] = "File:" + deger.strip()
                break
    return cikti


def ham_oku(yol):
    """ham/<il>.json -> mekanlar. Varsa aga hic cikilmiyor."""
    with open(yol, encoding="utf-8") as f:
        return _elemanlari_coz(json.load(f))


def sql_uret(satirlar):
    """Supabase'e yapistirilacak insert'ler.

    on conflict do nothing: betik tekrar calistirilabilir olmali ve her
    kosumda kopya uretmemeli (veritabaninda da tekil indeks var)."""
    if not satirlar:
        return "-- fotograf bulunamadi\n"
    tirnak = lambda v: "null" if not v else "'" + str(v).replace("'", "''") + "'"
    govde = ",\n".join(
        "  (%s, %s, %s, %s, 'commons', %s, %s, %s, 'onaylandi')" % (
            tirnak(r["mekan_id"]), tirnak(r["il"]), tirnak(r["mekan_ad"]),
            tirnak(r["adres"]), tirnak(r["yazar"]), tirnak(r["lisans"]),
            tirnak(r["kaynak_bag"]))
        for r in satirlar)
    return ("-- Cebimde - Wikimedia Commons fotograflari\n"
            "-- Uretildi: foto_cek.py. Supabase SQL Editor'e yapistir.\n"
            "-- Atif ZORUNLU ve satirlarda tasiniyor; veritabani kisiti da\n"
            "-- atifsiz satiri kabul etmiyor.\n"
            "insert into public.mekan_fotolari\n"
            "  (mekan_id, il, mekan_ad, adres, kaynak, yazar, lisans, kaynak_bag, durum)\n"
            "values\n" + govde + "\non conflict do nothing;\n")


def sql_yaz():
    """mekan_foto.csv -> foto_ekle.sql. AGA CIKMADAN, saniyeler.

    NEDEN AYRI BIR KIP. foto_ekle.sql .gitignore'da ve orada KALMALI:
    o bir cikti degil, Supabase SQL Editor'e ELLE yapistirilan bir ara
    adim. Ama gitignore'da olmasi "ulasilamaz" demek olmamali -- 27
    Agustos'ta tam bu oldu, dosya 91 dakikalik bir turda uretildi ve
    kosucuyla birlikte kayboldu.

    Izlenen sey CSV. SQL ondan HER ZAMAN yeniden uretilebiliyor ve
    uretmek icin Overpass'a bir daha gitmek gerekmiyor."""
    if not os.path.exists("mekan_foto.csv"):
        sys.exit("mekan_foto.csv yok. Once veri turunu kosur ve dosyayi al:\n"
                 "  git checkout origin/veri/tur-... -- mekan_foto.csv")
    with open("mekan_foto.csv", encoding="utf-8-sig", newline="") as f:
        satirlar = list(csv.DictReader(f))
    # BOS CSV'DEN SQL URETMEK, "fotograf yok" ile "dosya bos geldi"yi
    # ayni seye cevirir. Bu depoda kural: basarisizligi sayiya cevirme.
    if not satirlar:
        sys.exit("mekan_foto.csv BOS. Bu bir olcum degil -- tur yarim "
                 "kalmis olabilir. foto_ekle.sql YAZILMADI.")
    # CSV ESKI BIR TURDAN GELMIS OLABILIR. Atif temizligi 27 Agustos'ta
    # eklendi; o gun sabah kosan turun CSV'si kirli yazar tasiyor. Burada
    # yeniden temizlemek onu da duzeltiyor -- ve temizleyici zaten
    # "hicbir isim dusurme" kuralina gore yazildi, yani tekrar uygulamak
    # guvenli (idempotent).
    for r in satirlar:
        r["yazar"] = _temiz_yazar(r.get("yazar")) or ""

    eksik = [r for r in satirlar if not (r.get("yazar") or "").strip()]
    if eksik:
        # ATIF ZORUNLU. Veritabani kisiti da atifsiz satiri kabul etmiyor;
        # burada durmak, orada 300 satirlik bir hatayla karsilasmaktan iyi.
        sys.exit("%d satirda YAZAR yok. Commons lisansi atif ZORUNLU "
                 "kiliyor; foto_ekle.sql YAZILMADI." % len(eksik))
    with open("foto_ekle.sql", "w", encoding="utf-8") as f:
        f.write(sql_uret(satirlar))
    print("foto_ekle.sql yazildi: %d satir, %d il."
          % (len(satirlar), len({r.get("il") for r in satirlar})))
    print("Supabase -> SQL Editor -> yapistir -> Run.")


def main(kodlar):
    """Fotograf etiketli mekanlari bulup atifli satirlara cevirir.

    ham/ VARSA oradan okunuyor (aga hic cikilmadan); yoksa Overpass'a
    kucuk bir sorgu atiliyor. Ikinci yol saniyeler suruyor -- 81 ilin
    tamamini indirmeye gerek yok, aranan sey uc etiketten birini tasiyan
    mekanlar."""
    from turkiye_cek import ILLER
    if not kodlar:
        kodlar = list(ILLER)
    kotu = [k for k in kodlar if k not in ILLER]
    if kotu:
        sys.exit("bilinmeyen il kodu: %s (ornek: TR-06)" % ", ".join(kotu))

    bizim = bizdeki_mekanlar()
    if not bizim:
        sys.exit("app/veri bos. Once: python app_veri.py")
    print("uygulamada %d mekan var; yalniz bunlara fotograf yazilacak\n"
          % len(bizim), flush=True)

    hepsi, bizde_olan, basarisiz = [], 0, []
    tur_baslangic = time.monotonic()
    for sira, kod in enumerate(kodlar, 1):
        if time.monotonic() - tur_baslangic >= TUR_BUTCESI:
            kalan = list(kodlar[sira - 1:])
            basarisiz.extend(kalan)
            print("TUR BUTCESI DOLDU (%d dk): kalan %d il taranmadi. "
                  "Yarim tur yarim yaziliyor -- ozet EKSIK diyecek."
                  % (TUR_BUTCESI // 60, len(kalan)), flush=True)
            break
        yol = os.path.join("ham", kod + ".json")
        try:
            if os.path.exists(yol):
                mekanlar, kaynak = ham_oku(yol), "ham"
            else:
                mekanlar, kaynak = overpass_oku(kod), "overpass"
                # ILLER ARASI bekleme Overpass'in olcusuyle. BEKLEME (0,34)
                # Wikimedia icin; onu buraya koymak sunucuyu saniyede uc
                # ile sorgulamak demekti ve 20 il o yuzden dustu.
                time.sleep(OVERPASS_BEKLEME)
        except Exception as e:
            basarisiz.append(kod)
            print("[%2d/%d] %s  CEKILEMEDI: %s"
                  % (sira, len(kodlar), kod, str(e)[:60]), flush=True)
            continue

        # Uygulamada OLMAYAN mekana fotograf yazmak, hicbir sayfada
        # gorunmeyecek satirlar biriktirmek olurdu.
        mekanlar = [m for m in mekanlar if m["mekan_id"] in bizim]
        bizde_olan += len(mekanlar)

        # 1) wikidata -> dosya adi
        q = [m["wikidata"].strip() for m in mekanlar
             if re.match(r"^Q\d+$", (m["wikidata"] or "").strip())]
        q_gorsel = {}
        for i in range(0, len(q), YIGIN):
            try:
                q_gorsel.update(wikidata_gorselleri(q[i:i + YIGIN]))
            except Exception as e:
                print("    wikidata: %s" % str(e)[:50], flush=True)
            time.sleep(BEKLEME)

        # 2) her mekan icin BIR dosya adi sec
        istek = {}
        for m in mekanlar:
            dosya = (_guvenli_dosya_adi(m["commons"])
                     or _guvenli_dosya_adi(q_gorsel.get(m["wikidata"].strip()))
                     or _guvenli_dosya_adi(m["image"]))
            if dosya:
                istek[m["mekan_id"]] = (m, dosya)

        # 3) Commons'tan ATIF bilgisi
        adlar = sorted({d for _, d in istek.values()})
        bilgiler = {}
        for i in range(0, len(adlar), YIGIN):
            try:
                bilgiler.update(commons_bilgi(adlar[i:i + YIGIN]))
            except Exception as e:
                print("    commons: %s" % str(e)[:50], flush=True)
            time.sleep(BEKLEME)

        il_satir = []
        for mekan_id, (m, dosya) in istek.items():
            r = kayit_kur(dict(m, il=bizim[mekan_id]), bilgiler.get(dosya))
            if r:
                il_satir.append(r)
        hepsi.extend(il_satir)
        print("[%2d/%d] %-6s %-9s %4d etiketli -> %3d cozuldu -> %3d serbest lisansli"
              % (sira, len(kodlar), kod, kaynak, len(mekanlar), len(istek),
                 len(il_satir)), flush=True)

    # HICBIR IL CEKILEMEDIYSE bu bir OLCUM DEGIL, bir ariza. Dosya yazip
    # "%0.00" demek, ag hatasini "Commons'ta fotograf yok" diye rapor
    # etmek olurdu -- ve kullanici o sayiya bakip kaynagi eler.
    # Bu depoda kural: basarisizligi sayiya cevirme.
    if len(basarisiz) == len(kodlar):
        sys.exit("\nHICBIR IL CEKILEMEDI (%d/%d). Bu bir olcum degil, ag "
                 "arizasi.\nDosya YAZILMADI; onceki mekan_foto.csv / "
                 "foto_ekle.sql varsa oldugu gibi duruyor.\n"
                 "Overpass'a ulasabildigini dogrula: "
                 "curl -sI https://overpass-api.de/api/status"
                 % (len(basarisiz), len(kodlar)))

    with open("mekan_foto.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR)
        w.writeheader()
        w.writerows(hepsi)
    with open("foto_ekle.sql", "w", encoding="utf-8") as f:
        f.write(sql_uret(hepsi))

    kapsanan = len(kodlar) - len(basarisiz)
    oran = (100.0 * len(hepsi) / len(bizim)) if bizim else 0
    print("\nTOPLAM: uygulamadaki %d mekanin %d'inde fotograf etiketi var, "
          "%d'i serbest lisansli (%%%.2f)" % (len(bizim), bizde_olan, len(hepsi), oran))
    if basarisiz:
        # Kismi kosum SESSIZ GECMEMELI: eksik bir sayiya tam sayi gibi
        # bakmak, kaynagi haksiz yere elemeye goturur.
        print("UYARI: %d il cekilemedi (%s%s). Sayilar EKSIK -- o iller icin "
              "tekrar calistir." % (len(basarisiz), ", ".join(basarisiz[:6]),
                                    " ..." if len(basarisiz) > 6 else ""))
    print("%d/%d il tarandi. foto_ekle.sql yazildi -- Supabase SQL Editor'e "
          "yapistir." % (kapsanan, len(kodlar)))
    if oran < 1 and not basarisiz:
        print("\nBEKLENEN BIR SONUC, tahmin degil sayim. Commons'ta anit ve "
              "muze bol, mahalle kafesi yok denecek kadar az.\nSayfalari asil "
              "dolduracak olan DOGRULANMIS ISLETME SAHIBI ve kullanici "
              "yuklemeleri.")


def kendini_kontrol_et():
    """python foto_cek.py test — aga cikmadan mantigi dogrular.

    Buradaki hatalarin hepsi SESSIZ: yanlis cozulen bir dosya adi bos
    sonuc dondurur, eksik atif satiri dusurur. Hicbiri hata vermez,
    yalnizca daha az fotograf gelir."""
    # Dosya adi cozme: ucu de gercek veride goruldu.
    for ham, bekle in (
            ("File:Kafe.jpg", "File:Kafe.jpg"),
            ("Kafe.jpg", "File:Kafe.jpg"),
            ("https://commons.wikimedia.org/wiki/File:Kafe.jpg", "File:Kafe.jpg"),
            ("https://commons.wikimedia.org/wiki/File:Bir%20Kafe.jpg", "File:Bir Kafe.jpg"),
            ("File:Kafe.JPEG", "File:Kafe.JPEG"),
            # Kategori bir DOSYA degil.
            ("Category:Cafes", None),
            # Resim olmayan dosyalar (Commons'ta ses ve video da var).
            ("File:Ses.ogg", None), ("File:Belge.pdf", None),
            # Bos ve bozuk.
            ("", None), (None, None), ("File:", None),
            ("File:a/b.jpg", None)):
        assert _guvenli_dosya_adi(ham) == bekle, (ham, _guvenli_dosya_adi(ham), bekle)

    # Lisans: SERBEST OLMAYAN her sey atiliyor. "Bilmiyorsak serbesttir"
    # diye bir sey yok -- yanlis yayimlamanin bedeli hukuki.
    for iyi in ("CC0", "cc0", "CC BY 4.0", "CC BY-SA 3.0", "CC-BY-SA-4.0",
                "Public domain", "PD-old", "GFDL", "Attribution"):
        assert lisans_serbest_mi(iyi), iyi
    # NC ve ND SERBEST DEGIL. Ilk yazimda kalip yalniz ^ ile baslıyordu ve
    # "CC BY-NC 4.0" onekten eslesip geciyordu; bu kontrol onu yakaladi.
    for kotu in ("Fair use", "All rights reserved", "Copyrighted",
                 "CC BY-NC 4.0", "CC BY-NC-SA 4.0", "CC BY-ND 4.0",
                 "CC BY-NC-ND 3.0", "cc by nc", "", None, "Bilinmiyor",
                 "CC BY 4.0 (yalniz egitim)", "Attribution required, no commercial"):
        assert not lisans_serbest_mi(kotu), kotu

    # Yazar alani HTML tasiyor.
    assert _temiz_yazar('<a href="/wiki/User:X" title="X">Ali Veli</a>') == "Ali Veli"
    assert _temiz_yazar("  Ali   Veli  ") == "Ali Veli"
    # GERCEK TURDAN CIKAN UC DESEN.
    # Dosya adi oneki atiliyor, IKI ISIM DE kaliyor.
    assert _temiz_yazar("Agora.jpg: Didier Laroche derivative work: IgnisFatuus") \
        == "Didier Laroche derivative work: IgnisFatuus"
    # Birebir ikiye katlanmis metin tekilleniyor.
    assert _temiz_yazar("Unknown authorUnknown author") == "Unknown author"
    # ... ama katlanmamis metne DOKUNULMUYOR.
    assert _temiz_yazar("Ali Veli") == "Ali Veli"
    assert _temiz_yazar("AhmetMehmet") == "AhmetMehmet"
    # Kisa tekrar YARILANMIYOR: "Bora" gercek bir ad olabilir.
    assert _temiz_yazar("BoBo") == "BoBo"
    # Icinde iki gercek isim gecen uzun aciklama OLDUGU GIBI kaliyor.
    uzun = ("Şevki Balmumcu as an exhibition house in 1933, "
            "Paul Bonatz as an opera house in 1948")
    assert _temiz_yazar(uzun) == uzun
    assert _temiz_yazar("") is None and _temiz_yazar(None) is None

    # kayit_kur: ATIF EKSIKSE SATIR DUSER. Veritabani da ayni kisiti
    # tasiyor (mekan_fotolari_atif_check); iki kapi da kapali.
    mekan = {"mekan_id": "node/1", "il": "06", "mekan_ad": "Kafe"}
    tam = {"adres": "https://upload.wikimedia.org/x.jpg",
           "yazar": "<b>Ali</b>", "lisans": "CC BY-SA 4.0",
           "sayfa": "https://commons.wikimedia.org/wiki/File:X.jpg"}
    r = kayit_kur(mekan, tam)
    assert r and r["yazar"] == "Ali" and r["lisans"] == "CC BY-SA 4.0", r
    assert set(r) == set(ALANLAR), set(r) ^ set(ALANLAR)
    for eksik in ("yazar", "lisans", "adres", "sayfa"):
        assert kayit_kur(mekan, dict(tam, **{eksik: None})) is None, eksik
    assert kayit_kur(mekan, dict(tam, lisans="Fair use")) is None
    assert kayit_kur(mekan, None) is None

    # SQL: tekrar calistirilabilir olmali ve tirnak kacirmali.
    s = sql_uret([kayit_kur(dict(mekan, mekan_ad="O'Kafe"), tam)])
    assert "on conflict do nothing" in s, s
    assert "O''Kafe" in s, s
    assert "'commons'" in s and "'onaylandi'" in s, s
    assert sql_uret([]).startswith("--")

    # ham_oku: etiketler dogru okunuyor mu.
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump({"elements": [
            {"type": "node", "id": 1, "tags": {"name": "A", "image": "File:A.jpg"}},
            {"type": "way", "id": 2, "tags": {"name": "B", "wikidata": "Q5"}},
            {"type": "node", "id": 3, "tags": {}},          # adsiz: atlanir
        ]}, f)
        gecici = f.name
    try:
        m = ham_oku(gecici)
        assert [x["mekan_id"] for x in m] == ["node/1", "way/2"], m
        assert m[0]["image"] == "File:A.jpg" and m[1]["wikidata"] == "Q5", m
    finally:
        os.unlink(gecici)

    # sorgu(): ham/ OLMADAN da calisabilmenin tek yolu. Kucuk olmasi sart --
    # turkiye_cek.py'nin sorgusu 81 il icin saatler suruyor.
    q = sorgu("TR-06")
    assert '"ISO3166-2"="TR-06"' in q, q
    # Uc etiketin ucu de sorulmali; biri unutulursa o kaynak sessizce kurur.
    for etiket in FOTO_ETIKET:
        assert '["%s"]' % etiket in q, etiket
    # Yeme-icme VE eglence secicilerinin ikisi de: yalniz biri olsaydi
    # muzelerin (Commons'ta en cok fotografi olan tur) hepsi kacardi.
    assert "cafe" in q and "museum" in q, q
    assert q.startswith("[out:json]") and q.endswith("out center tags;"), q
    # Seciciler turkiye_cek/eglence_cek'ten ALINIYOR, kopyalanmiyor.
    assert YEME_AMENITY in q and TOURISM in q

    # _elemanlari_coz: Overpass ve ham/ AYNI bicimde; tek cozucu.
    v = {"elements": [
        {"type": "node", "id": 1, "tags": {"name": "A", "image": "File:A.jpg"}},
        {"type": "relation", "id": 7, "tags": {"name": "M", "wikidata": "Q5"}},
        {"type": "node", "id": 3, "tags": {}},            # adsiz: atlanir
    ]}
    c = _elemanlari_coz(v)
    assert [x["mekan_id"] for x in c] == ["node/1", "relation/7"], c
    assert c[1]["wikidata"] == "Q5" and c[1]["image"] == "", c

    print("kontrol gecti: dosya adi cozme, lisans elemesi, atif zorunlulugu, "
          "kucuk sorgu")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        kendini_kontrol_et()
    elif len(sys.argv) > 1 and sys.argv[1] == "sql":
        sql_yaz()
    else:
        main([a for a in sys.argv[1:]])
