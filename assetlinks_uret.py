#!/usr/bin/env python3
"""app/.well-known/assetlinks.json uretir (Android TWA dogrulamasi).

    python assetlinks_uret.py AA:BB:CC:...   # parmak izini yazar
    python assetlinks_uret.py durum          # dosya var mi, ne diyor
    python assetlinks_uret.py test           # kendi kontrolu

NE ISE YARIYOR
==============
TWA (Trusted Web Activity), uygulamanin GERCEKTEN bu siteye ait oldugunu
Digital Asset Links ile dogruluyor. Dogrulama tutmazsa uygulama ACILIR ama
ustunde ADRES CUBUGU olur -- yani "uygulama" gibi degil, tarayici gibi
gorunur. Play'de reddedilmez, sadece kotu goruur ve sebebi hicbir yerde
yazmaz. TWA'da en sik yasanan sorun budur.

PARMAK IZI NEREDEN GELIYOR
==========================
Play App Signing kullaniyorsan (varsayilan ve onerilen) imzayi Google
atiyor, yani parmak izi SENIN anahtarindan degil GOOGLE'in anahtarindan
geliyor. Ilk yuklemeden SONRA:

    Play Console -> Test ve yayinlama -> Uygulama imzalama
    -> "SHA-256 sertifika parmak izi"

Yerel imzayla (ust ust test ederken) parmak izi:

    keytool -list -v -keystore <anahtar.jks> -alias <ad>

IKISI DE OLABILIR. Betik birden cok parmak izi kabul ediyor; yerel test
anahtarini da eklersen hem magazadan inen surum hem kendi kurdugun APK
dogrulanir.

ANAHTARIN KENDISI DEPOYA GIRMEZ. Parmak izi bir OZET, gizli degil --
zaten uygulamayi indiren herkes hesaplayabiliyor. Ama .jks/.keystore
dosyasi ve parolasi gizli: .gitignore onlari kapatiyor.
"""
import io
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(KOK, "app", ".well-known", "assetlinks.json")

# Play'de yayimlandiktan SONRA DEGISTIRILEMEZ. Ilk yuklemeden once karar
# ver; degistirmek yeni bir uygulama yayimlamak demek.
PAKET = "com.oturalim.app"

PARMAK = re.compile(r"^(?:[0-9A-F]{2}:){31}[0-9A-F]{2}$")


def temizle(ham):
    """Kullanicinin yapistirdigi seyi normalize eder.

    keytool ciktisi kucuk harfli ve basinda "SHA256: " olabiliyor; Play
    Console buyuk harfli veriyor. Ikisi de kabul ediliyor, cikti tek
    bicimde yaziliyor."""
    s = str(ham).strip()
    s = re.sub(r"(?i)^sha[\-_ ]?256\s*[:=]\s*", "", s)
    s = re.sub(r"\s+", "", s).upper()
    # Iki nokta olmadan yapistirilmis 64 haneli hali de kabul et.
    if re.fullmatch(r"[0-9A-F]{64}", s):
        s = ":".join(s[i:i + 2] for i in range(0, 64, 2))
    return s


def dogrula(p):
    if not PARMAK.match(p):
        return ("parmak izi bicimi yanlis: 32 bayt, iki nokta ile ayrilmis "
                "onaltilik olmali (AA:BB:...). Gelen: %r" % p[:80])
    return None


def govde(parmaklar):
    return [{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": PAKET,
            "sha256_cert_fingerprints": parmaklar
        }
    }]


def yaz(hamlar):
    parmaklar = []
    for h in hamlar:
        p = temizle(h)
        sorun = dogrula(p)
        if sorun:
            sys.exit("YAZILMADI: " + sorun)
        if p not in parmaklar:
            parmaklar.append(p)
    os.makedirs(os.path.dirname(HEDEF), exist_ok=True)
    io.open(HEDEF, "w", encoding="utf-8").write(
        json.dumps(govde(parmaklar), indent=2) + "\n")
    print("yazildi: app/.well-known/assetlinks.json")
    print("  paket : %s" % PAKET)
    for p in parmaklar:
        print("  parmak: %s" % p)
    print()
    print("Yayina aldiktan SONRA dogrula:")
    print("  https://<alan-adin>/.well-known/assetlinks.json  ->  200 ve JSON")
    print("  Uygulamayi ac: ustte ADRES CUBUGU GORUNMEMELI.")


def durum():
    if not os.path.exists(HEDEF):
        print("app/.well-known/assetlinks.json YOK.")
        print("TWA yine calisir ama ustunde ADRES CUBUGU olur.")
        print("Parmak izini alip: python assetlinks_uret.py AA:BB:...")
        return 1
    d = json.loads(io.open(HEDEF, encoding="utf-8").read())
    hedef = d[0]["target"]
    print("paket : %s" % hedef["package_name"])
    for p in hedef["sha256_cert_fingerprints"]:
        print("parmak: %s" % p)
    return 0


def kendini_kontrol_et():
    s = []
    ornek = "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:" \
            "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99"
    if dogrula(ornek):
        s.append("saglam parmak izi reddedildi")
    # Temizleyici GERCEKTEN calisiyor mu: uc yaygin yapistirma bicimi.
    if temizle("sha256: " + ornek.lower()) != ornek:
        s.append("keytool bicimi (kucuk harf + onek) cozulmuyor")
    if temizle(ornek.replace(":", "")) != ornek:
        s.append("iki noktasiz 64 haneli hal cozulmuyor")
    if temizle("  " + ornek + "\n") != ornek:
        s.append("bosluklu hal cozulmuyor")
    # Bozuk girdiler REDDEDILMELI. Sessizce kabul edilen bir parmak izi,
    # kullanicinin "yazdim, olmuyor" diye saatlerce aramasi demek.
    for ad, kotu in (("kisa", "AA:BB"),
                     ("uzun", ornek + ":AA"),
                     ("onaltilik disi", ornek[:-2] + "ZZ"),
                     ("bos", ""),
                     ("cumle", "parmak izini buraya yapistir")):
        if not dogrula(temizle(kotu)):
            s.append("bozuk parmak izi kabul edildi: %s" % ad)
    # Cikti bicimi Google'in bekledigi sekilde mi.
    g = govde([ornek])[0]
    if g["relation"] != ["delegate_permission/common.handle_all_urls"]:
        s.append("relation yanlis")
    if g["target"]["namespace"] != "android_app":
        s.append("namespace yanlis")
    if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+)+", PAKET):
        s.append("paket adi Android bicimine uymuyor: %s" % PAKET)
    # twa-manifest.json ile paket adi AYNI olmali; ayrisirsa dogrulama
    # sessizce tutmaz ve adres cubugu cikar.
    twa = os.path.join(KOK, "twa-manifest.json")
    if os.path.exists(twa):
        t = json.loads(io.open(twa, encoding="utf-8").read())
        if t.get("packageId") != PAKET:
            s.append("twa-manifest.json paketi %r, burasi %r"
                     % (t.get("packageId"), PAKET))
    return s


if __name__ == "__main__":
    arg = sys.argv[1:] or ["durum"]
    if arg[0] == "test":
        sorunlar = kendini_kontrol_et()
        for x in sorunlar:
            print("  HATA: " + x)
        if not sorunlar:
            print("kontrol gecti: bes bozuk parmak izi eleniyor, "
                  "uc yapistirma bicimi cozuluyor")
        sys.exit(1 if sorunlar else 0)
    if arg[0] == "durum":
        sys.exit(durum())
    yaz(arg)
