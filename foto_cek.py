#!/usr/bin/env python3
"""Mekanlar icin SERBEST LISANSLI fotograf toplar (Wikimedia Commons).

Kullanim:
    python foto_cek.py TR-06                 # tek il
    python foto_cek.py                       # ham/ altindaki butun iller
    python foto_cek.py test                  # aga cikmadan mantik kontrolu

Cikti:
    mekan_foto.csv        -- mekan_id, adres, yazar, lisans, kaynak_bag
    mekan_foto.sql        -- Supabase'e yapistirilacak insert'ler (gitignore)

NEDEN BU KAYNAK, BASKASI DEGIL
==============================
Google Maps, TripAdvisor, Foursquare ve benzeri yerlerdeki fotograflar
YAZARLARININ TELIFINDE ve o platforma lisansli. Kendi sitende yayimlama
hakkin yok; Places API'nin kendi sartlari bile fotografi ve yorumu
onbellekte tutmayi ve harita disinda gostermeyi yasakliyor. Bu teknik bir
zorluk degil, ihtarname sebebi -- OTURALIM.md "Yapilmayacaklar" listesinde
yazili bir karar.

Wikimedia Commons FARKLI: oradaki dosyalar serbest lisansli (CC0, CC BY,
CC BY-SA) ve yeniden yayimlanabilir. KARSILIGINDA ATIF ZORUNLU: yazar adi
ve lisans gosterilmeli. Bu betik atifi TOPLAMADAN fotograf yazmiyor ve
veritabani kisiti da atifsiz satiri kabul etmiyor (mekan_foto.sql).

BEKLENEN KAPSAM DUSUK, bunu bastan soyluyorum
=============================================
Commons'ta anit, cami, tarihi yapi ve muze bol; mahalle kafesi yok
denecek kadar az. Bu betik "her mekana fotograf" getirmiyor; getirdigi
sey, getirebildigi kadari. Sayfalari asil dolduracak olan kullanici ve
DOGRULANMIS ISLETME SAHIBI yuklemeleri (veritabani/mekan_foto.sql).
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

COMMONS = "https://commons.wikimedia.org/w/api.php"
WIKIDATA = "https://www.wikidata.org/w/api.php"
BEKLEME = 0.34          # saniye; Wikimedia'nin istedigi hiz siniri
YIGIN = 40              # tek istekte sorulan dosya sayisi (API siniri 50)
KULLANICI_AJANI = "Oturalim/0.1 (https://oturalim.vercel.app; menu fiyat projesi)"

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
    """Commons yazar alani HTML tasiyor ("<a href=...>Ad</a>"); metne indir."""
    v = re.sub(r"<[^>]+>", "", ham or "")
    v = re.sub(r"\s+", " ", v).strip()
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
    """ham/<il>.json -> fotograf etiketi TASIYAN mekanlar."""
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
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
    return ("-- Oturalim - Wikimedia Commons fotograflari\n"
            "-- Uretildi: foto_cek.py. Supabase SQL Editor'e yapistir.\n"
            "-- Atif ZORUNLU ve satirlarda tasiniyor; veritabani kisiti da\n"
            "-- atifsiz satiri kabul etmiyor.\n"
            "insert into public.mekan_fotolari\n"
            "  (mekan_id, il, mekan_ad, adres, kaynak, yazar, lisans, kaynak_bag, durum)\n"
            "values\n" + govde + "\non conflict do nothing;\n")


def main(kodlar):
    if not os.path.isdir("ham"):
        sys.exit("ham/ klasoru yok. Once: python turkiye_cek.py")
    if not kodlar:
        kodlar = sorted(x[:-5] for x in os.listdir("ham") if x.endswith(".json"))

    hepsi, toplam_mekan, etiketli = [], 0, 0
    for kod in kodlar:
        yol = os.path.join("ham", kod + ".json")
        if not os.path.exists(yol):
            print("  %s: ham dosya yok, atlandi" % kod)
            continue
        mekanlar = ham_oku(yol)
        toplam_mekan += len(mekanlar)

        # 1) wikidata -> dosya adi
        q = [m["wikidata"] for m in mekanlar
             if re.match(r"^Q\d+$", (m["wikidata"] or "").strip())]
        q_gorsel = {}
        for i in range(0, len(q), YIGIN):
            q_gorsel.update(wikidata_gorselleri(q[i:i + YIGIN]))
            time.sleep(BEKLEME)

        # 2) her mekan icin bir dosya adi sec
        istek = {}
        for m in mekanlar:
            dosya = (_guvenli_dosya_adi(m["commons"])
                     or _guvenli_dosya_adi(q_gorsel.get(m["wikidata"].strip()))
                     or _guvenli_dosya_adi(m["image"]))
            if dosya:
                istek[m["mekan_id"]] = (m, dosya)
        etiketli += len(istek)

        # 3) Commons'tan atif bilgisi
        adlar = sorted({d for _, d in istek.values()})
        bilgiler = {}
        for i in range(0, len(adlar), YIGIN):
            bilgiler.update(commons_bilgi(adlar[i:i + YIGIN]))
            time.sleep(BEKLEME)

        il_satir = []
        for mekan_id, (m, dosya) in istek.items():
            m = dict(m, il=kod[-2:])
            r = kayit_kur(m, bilgiler.get(dosya))
            if r:
                il_satir.append(r)
        hepsi.extend(il_satir)
        print("[%s] %5d mekan, %4d etiketli, %4d serbest lisansli"
              % (kod, len(mekanlar), len(istek), len(il_satir)), flush=True)

    with open("mekan_foto.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR)
        w.writeheader()
        w.writerows(hepsi)
    with open("mekan_foto.sql", "w", encoding="utf-8") as f:
        f.write(sql_uret(hepsi))

    oran = (100.0 * len(hepsi) / toplam_mekan) if toplam_mekan else 0
    print("\nTOPLAM: %d mekanin %d'inde fotograf etiketi, %d'i serbest "
          "lisansli (%%%.2f)" % (toplam_mekan, etiketli, len(hepsi), oran))
    print("mekan_foto.sql yazildi -- Supabase SQL Editor'e yapistir.")
    if oran < 1:
        print("\nBEKLENEN BIR SONUC. Commons'ta anit ve muze bol, mahalle "
              "kafesi yok denecek kadar az.\nSayfalari asil dolduracak olan "
              "kullanici ve dogrulanmis isletme sahibi yuklemeleri.")


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

    print("kontrol gecti: dosya adi cozme, lisans elemesi, atif zorunlulugu")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        kendini_kontrol_et()
    else:
        main([a for a in sys.argv[1:]])
