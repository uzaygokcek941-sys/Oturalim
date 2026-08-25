#!/usr/bin/env python3
"""81 ilin konser, festival ve fuar etkinliklerini etkinlik.io RSS'inden ceker.

NEDEN RSS, NEDEN API DEGIL
  V2 API daha zengin (mekan adi, lat/lng, ilce, tarih araligi, sayfalama) ama
  X-Etkinlik-Token istiyor; o token yayinci basvurusu + onayla geliyor.
  RSS kayit gerektirmiyor ve sehir + tur suzgecini destekliyor.

RSS'IN SINIRI -- ONEMLI
  RSS kaydinda MEKAN ADI, ADRES ve KOORDINAT YOK. Bu veriyle ancak SEHIR
  duzeyinde oneri yapilabilir. Ilce ve mesafe bazli oneri API tokeni ister.
  Ayrica akis basina 50 kayit tavani var, sayfalama yok.

ETKINLIK BAYATLAR
  Restoran koordinatta durur, bir kez cekilir. Konser bir tarihte olur; bugun
  dogru olan dosya yarin yanlistir. Bu script duzenli calistirilmali.

Kullanim:
    python etkinlik_cek.py            # 81 il
    python etkinlik_cek.py 06 34      # sadece belirtilen plakalar
Cikti:
    app/veri/etkinlik.json
"""
import json, os, re, subprocess, sys, time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

RSS = "https://etkinlik.io/rss/sorgu"
BEKLEME = 1.5          # saniye, iller arasi -- ucretsiz servise saygi
# Turler AYRI AYRI cekiliyor. Tek istekte "19,21,4" verince akis basina 50
# kayit tavani tarihe gore doluyor ve konserler festival ile fuari eziyor
# (olculdu: 3 ilde 148 konser, 2 festival, 0 fuar). Ayri cekince her turun
# kendi 50'lik butcesi oluyor.
TURLER = {"19": "Konser", "21": "Festival", "4": "Fuar"}

# etkinlik.io sehir kimligi -> bizim plaka kodumuz. Kaynak: RSS ozellestirme
# formundaki sehir kutulari. "Afyon"(3) ve "Afyonkarahisar"(85) ayni il olarak
# iki kez geciyor, 3 kullaniliyor. KKTC(84) ve Lefkosa(83) alinmiyor.
SEHIR = {
    "01": 1,  "02": 2,  "03": 3,  "04": 4,  "05": 6,  "06": 7,  "07": 8,
    "08": 10, "09": 11, "10": 12, "11": 16, "12": 17, "13": 18, "14": 19,
    "15": 20, "16": 21, "17": 22, "18": 23, "19": 24, "20": 25, "21": 26,
    "22": 28, "23": 29, "24": 30, "25": 31, "26": 32, "27": 33, "28": 34,
    "29": 35, "30": 36, "31": 37, "32": 39, "33": 58, "34": 40, "35": 41,
    "36": 45, "37": 46, "38": 47, "39": 49, "40": 50, "41": 52, "42": 53,
    "43": 54, "44": 55, "45": 56, "46": 42, "47": 57, "48": 59, "49": 60,
    "50": 61, "51": 62, "52": 63, "53": 65, "54": 66, "55": 67, "56": 68,
    "57": 69, "58": 70, "59": 73, "60": 74, "61": 75, "62": 76, "63": 71,
    "64": 77, "65": 78, "66": 80, "67": 81, "68": 5,  "69": 15, "70": 44,
    "71": 48, "72": 14, "73": 72, "74": 13, "75": 9,  "76": 38, "77": 79,
    "78": 43, "79": 51, "80": 64, "81": 27,
}

AY = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
      "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
TR = timezone(timedelta(hours=3))
DESEN = re.compile(r"(%sd{1,2}) (%sw{3}) (%sd{4}) (%sd{2}):(%sd{2})(?::(%sd{2}))?" % ((chr(92),) * 6))


def tarih_coz(s):
    """RSS pubDate -> ISO. 'Sat, 22 Aug 2026 19:00:00 +0300' veya saniyesiz."""
    m = DESEN.search(s or "")
    if not m:
        return None
    g, ay, y, sa, dk, sn = m.groups()
    if ay not in AY:
        return None
    return datetime(int(y), AY[ay], int(g), int(sa), int(dk), int(sn or 0),
                    tzinfo=TR).isoformat()


def cek(sehir_id, tur_id):
    url = "%s?turIds=%s&sehirIds=%d" % (RSS, tur_id, sehir_id)
    r = subprocess.run(["curl", "-s", "--max-time", "40", "-A", "Cebimde/0.1", url],
                       capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    try:
        return ET.fromstring(r.stdout)
    except ET.ParseError:
        return None


def guvenli_bag(u):
    """href'e konulabilir adres, degilse "".

    Baglantilar UCUNCU TARAF RSS akislarindan geliyor ve olduklari gibi
    app/veri/etkinlik.json'a yaziliyordu. Ana sayfa da onlari href yapiyor:
    akisin verdigi "javascript:..." tiklanabilir bir baglanti olurdu.
    Kural sayfa tarafinda da var (ortak.js guvenliBag) -- burasi verinin
    icine hic girmemesi icin. Ayni ifade iki dilde; test.py ikisinin
    ayrismadigini denetliyor."""
    ham = (u or "").strip()
    if not ham:
        return ""
    return ham if re.match(r"^https?://", ham, re.I) else ""


def kayitlar(kok):
    simdi = datetime.now(TR)
    cikti = []
    for it in kok.iter("item"):
        al = lambda t: (it.findtext(t) or "").strip()
        bas = tarih_coz(al("pubDate"))
        if not bas or datetime.fromisoformat(bas) < simdi:
            continue                      # gecmis etkinlik yazilmaz
        turler = [e.text for e in it.findall("category") if e.text]
        enc = it.find("enclosure")
        cikti.append({
            "ad": al("title"),
            "bas": bas,
            "tur": turler[0] if turler else "",
            "link": guvenli_bag(al("link")),
            "gorsel": (enc.get("url") or "") if enc is not None else "",
        })
    cikti.sort(key=lambda x: x["bas"])
    return cikti


def main(plakalar):
    veri, toplam = {}, 0
    for i, p in enumerate(plakalar, 1):
        sid = SEHIR.get(p)
        if not sid:
            print("  %s: sehir kimligi yok, atlandi" % p)
            continue
        birlesik, hata = [], []
        for tid, tad in TURLER.items():
            kok = cek(sid, tid)
            time.sleep(BEKLEME)
            if kok is None:
                hata.append(tad)
                continue
            birlesik.extend(kayitlar(kok))
        # Ayni etkinlik birden fazla turde gorunebiliyor; link ile tekille.
        # BOS link tekillestirmede kullanilmaz: guvenli_bag() kullanilamaz
        # adresi "" yapiyor ve boyle olan butun etkinlikler tek bir kayda
        # inerdi -- yani bir bicim denetimi sessizce VERI SILERDI.
        gorulen, k = set(), []
        for e in sorted(birlesik, key=lambda x: x["bas"]):
            anahtar = e["link"] or ("ad:" + e["ad"] + "|" + e["bas"])
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            k.append(e)
        if k:
            veri[p] = k
            toplam += len(k)
        print("[%d/%d] %s  %3d etkinlik%s"
              % (i, len(plakalar), p, len(k),
                 "  (cekilemedi: %s)" % ",".join(hata) if hata else ""), flush=True)

    os.makedirs("app/veri", exist_ok=True)
    yol = "app/veri/etkinlik.json"

    # EMNIYET: yarim cekim iyi veriyi ezmesin. Servis gecici olarak
    # cevap vermezse veya ag koparsa elimizde 5 illik dosya kalir ve
    # uygulama dun calisirken bugun bos gorunur. Tam calistirmada
    # (81 il) yeni sonuc eskinin yarisindan azsa YAZILMIYOR.
    if len(plakalar) >= 40 and os.path.exists(yol):
        try:
            with open(yol, encoding="utf-8") as f:
                eski = len(json.load(f).get("iller", {}))
        except Exception:
            eski = 0
        if eski and len(veri) < eski * 0.5:
            print()
            print("YAZILMADI: yeni sonuc %d il, mevcut dosya %d il. "
                  "Yarim cekim suphesi -- eski dosya korundu." % (len(veri), eski))
            sys.exit(1)

    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump({"guncelleme": datetime.now(TR).isoformat(), "iller": veri},
                  f, ensure_ascii=False, separators=(",", ":"))
    os.replace(gecici, yol)

    assert toplam > 0, "hic etkinlik yazilmadi"
    print()
    print("TOPLAM: %d etkinlik / %d il -> %s (%.0f KB)"
          % (toplam, len(veri), yol, os.path.getsize(yol) / 1024))


def kendini_kontrol_et():
    """python etkinlik_cek.py test — aga cikmadan ayristirma mantigini dogrular.

    Buradaki hatalarin hepsi SESSIZ: tarih cozulemezse kayit "gecmis"
    sayilip atiliyor, plaka eslesmezse il atlaniyor. Ikisinde de dosya
    yaziliyor, sadece icinde daha az sey oluyor.
    """
    # pubDate: saniyeli ve saniyesiz bicim, ikisi de RSS'te goruldu.
    assert tarih_coz("Sat, 22 Aug 2026 19:00:00 +0300") == "2026-08-22T19:00:00+03:00"
    assert tarih_coz("Sat, 22 Aug 2026 19:00 +0300")    == "2026-08-22T19:00:00+03:00"
    assert tarih_coz("22 Aug 2026 19:00:00")            == "2026-08-22T19:00:00+03:00"
    # Saniye gercekten okunmali: sabit 0 yazmak sessizce gecerdi.
    assert tarih_coz("Sat, 22 Aug 2026 19:00:45 +0300") == "2026-08-22T19:00:45+03:00"
    # Bozuk girdi None donmeli, catmamalı.
    for kotu in ("", None, "yarin aksam", "Sat, 22 Zzz 2026 19:00:00 +0300"):
        assert tarih_coz(kotu) is None, kotu

    # Plaka -> sehir kimligi: 81 il, tekrar eden kimlik olmamali. Tekrar,
    # iki ilin ayni akisi cekmesi demek.
    assert len(SEHIR) == 81, len(SEHIR)
    assert len(set(SEHIR.values())) == 81, "iki plaka ayni sehir kimligine bakiyor"
    assert sorted(SEHIR) == ["%02d" % i for i in range(1, 82)], "plaka listesi eksik"

    # kayitlar(): gecmis etkinlik yazilmaz, gelecek olan yazilir, sirali gelir.
    gecmis = (datetime.now(TR) - timedelta(days=2)).strftime("%a, %d %b %Y %H:%M:%S +0300")
    yakin  = (datetime.now(TR) + timedelta(days=2)).strftime("%a, %d %b %Y %H:%M:%S +0300")
    uzak   = (datetime.now(TR) + timedelta(days=9)).strftime("%a, %d %b %Y %H:%M:%S +0300")
    xml = ("<rss><channel>"
           "<item><title>Gecmis</title><pubDate>%s</pubDate><link>a</link>"
           "<category>Konser</category></item>"
           "<item><title>Uzak</title><pubDate>%s</pubDate><link>b</link>"
           "<category>Konser</category>"
           "<enclosure url='http://x/y.jpg'/></item>"
           "<item><title>Yakin</title><pubDate>%s</pubDate><link>c</link></item>"
           "<item><title>Tarihsiz</title><pubDate>zzz</pubDate><link>d</link></item>"
           "</channel></rss>") % (gecmis, uzak, yakin)
    k = kayitlar(ET.fromstring(xml))
    assert [e["ad"] for e in k] == ["Yakin", "Uzak"], k
    assert k[1]["gorsel"] == "http://x/y.jpg", k[1]
    assert k[0]["gorsel"] == "" and k[0]["tur"] == "", k[0]
    # Test XML'indeki link'ler semasiz ("a","b"): kullanilamaz, "" olmali.
    assert [e["link"] for e in k] == ["", ""], k

    # Sema denetimi. Baglantilar ucuncu taraf akislarindan geliyor ve
    # ana sayfa onlari href yapiyor; kacir() semaya bakmaz.
    assert guvenli_bag("https://a.test/x") == "https://a.test/x"
    assert guvenli_bag("HTTP://a.test")    == "HTTP://a.test"
    assert guvenli_bag("  https://a.test  ") == "https://a.test"
    for kotu in ("javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,x",
                 "vbscript:x", "//a.test/x", "a.test/x", "", None):
        assert guvenli_bag(kotu) == "", kotu

    # Tekillestirme: BOS link'ler tek kayda inmemeli. guvenli_bag() bozuk
    # adresi "" yaptigi icin, link'e gore tekillestirmek bir bicim
    # denetimini sessiz bir VERI SILME'ye cevirebilirdi.
    xml2 = ("<rss><channel>"
            "<item><title>Bir</title><pubDate>%s</pubDate><link>javascript:x</link></item>"
            "<item><title>Iki</title><pubDate>%s</pubDate><link>vbscript:y</link></item>"
            "</channel></rss>") % (yakin, uzak)
    tek = kayitlar(ET.fromstring(xml2))
    gorulen, kalan = set(), []
    for e in sorted(tek, key=lambda x: x["bas"]):
        a = e["link"] or ("ad:" + e["ad"] + "|" + e["bas"])
        if a in gorulen:
            continue
        gorulen.add(a)
        kalan.append(e)
    assert [e["ad"] for e in kalan] == ["Bir", "Iki"], kalan

    print("kontrol gecti: tarih cozme, 81 plaka eslesmesi, gecmis eleme, "
          "baglanti semasi")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.exit(0 if kendini_kontrol_et() else 1)
    main(sys.argv[1:] or sorted(SEHIR))
