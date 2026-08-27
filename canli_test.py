#!/usr/bin/env python3
"""YAYINDAKI siteyi gercek tarayicida sinar. Kullanim:

    python canli_test.py https://oturalim.vercel.app

NEDEN AYRI BIR BETIK, test_sayfa.py VARKEN
==========================================
test_sayfa.py yerel sunucuya bakiyor ve Supabase'i TAKLIT ediyor. Ikisi
de bilerek: kontroller aga cikmadan kosabilmeli. Ama o yuzden su dordunu
BIR KEZ BILE sinamis degiliz:

  1) Vercel'in gercekten gonderdigi CSP basligi. sunucu.py vercel.json'u
     okuyup ayni basligi gonderiyor, yani karma hatasi yerelde de
     yakalaniyor -- ama YAYIN yapilandirmasinin uygulandigini degil.
  2) Yayina cikan dosyalarin hepsinin ORADA oldugu. Yerelde dosya diskte
     duruyor; Vercel'e gitmemis olabilir.
  3) Supabase'e ANONIM olarak ulasilabildigi. Anon anahtari genel ve RLS
     tek yetki -- ama anahtarin yayinda dogru oldugunu yerel taklit
     soyleyemez.
  4) Service worker'in gercek bir kaynakta kurulup cevrimdisi sayfayi
     verdigi.

DUMAN_TESTI.md'nin GIRIS GEREKTIRMEYEN maddeleri buraya tasindi
(A1-A7, G2-G3). Kalanlar elde kaliyor ve sebebi teknik degil: hesap
acmak, e-posta okumak ve moderasyon karari vermek bir insan istiyor.

BU BETIK HICBIR SEY YAZMIYOR. Yalniz okuyor ve konum izni istiyor.
Yayindaki veriye tek satir eklemez.
"""
import os
import re
import sys

BEKLE = 15000            # ms; yayin yerelden yavas

# TURUN NE GORDUGU. "temiz" tek basina bir sey kanitlamiyor: sayfa hic
# yuklenmese de bircok kontrol "kotu bir sey bulamadim" der ve tur yesil
# yanar. Bu depodaki kural basarisizligi sayiya cevirmemek; ayni kural
# HICBIR SEYI de basari sayamaz. Tur artik NE GORDUGUNU yaziyor ve
# gormesi gerekeni gormediyse dusuyor.
OLCUM = {}


def _tarayici_yolu():
    kok = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if kok and os.path.isdir(kok):
        import glob
        for d in sorted(glob.glob(os.path.join(kok, "chromium-*",
                                               "chrome-linux", "chrome"))):
            return d
    return None


def _sayfa_ac(t, adres, izin=None, konum=None):
    """Yeni baglam + sayfa. Hatalar ve CSP ihlalleri TOPLANIYOR.

    CSP ihlali AYRI toplaniyor cunku ENGELLENEN BIR SCRIPT HATA
    FIRLATMIYOR: tarayici blogu sessizce calistirmiyor ve sayfa
    "hatasiz" gorunuyor."""
    kw = {}
    if izin:
        kw["permissions"] = izin
    if konum:
        kw["geolocation"] = konum
    ctx = t.new_context(**kw)
    s = ctx.new_page()
    hatalar, csp = [], []
    s.on("pageerror", lambda e: hatalar.append(str(e).split("\n")[0][:120]))

    def konsol(m):
        y = m.text
        if "Content Security Policy" in y or "Refused to" in y:
            csp.append(y[:160])
    s.on("console", konsol)
    s.goto(adres, wait_until="domcontentloaded", timeout=BEKLE)
    return ctx, s, hatalar, csp


def kos(taban):
    from playwright.sync_api import sync_playwright
    taban = taban.rstrip("/")
    OLCUM.clear()
    s = []

    with sync_playwright() as p:
        yol = _tarayici_yolu()
        t = (p.chromium.launch(executable_path=yol, args=["--no-sandbox"])
             if yol else p.chromium.launch(args=["--no-sandbox"]))
        try:
            s += _a1_a7(t, taban)
            s += _g2_g3(t, taban)
            s += _cevrimdisi(t, taban)
        finally:
            t.close()
    return s


def _a1_a7(t, taban):
    """DUMAN_TESTI A1-A6: acilis, keşfet, konum, fiyat."""
    s = []
    ctx, sayfa, hatalar, csp = _sayfa_ac(t, taban + "/")
    try:
        # A1 -- ana ekranda butce girilince oneri cikiyor mu.
        kutu = sayfa.query_selector("#butce-girdi")
        if not kutu:
            s.append("A1: ana ekranda butce kutusu bulunamadi")
        else:
            kutu.fill("200")
            kutu.press("Enter")
            sayfa.wait_for_timeout(1500)
            # ONERININ KENDISI DEGIL, BOS OLMADIGI onemli: bos bir oneri
            # listesi "calisiyor" gibi gorunup hicbir sey soylemiyor.
            metin = sayfa.inner_text("body")
            if not re.search(r"\d", metin):
                s.append("A1: butce 200 girildi, ekranda hic sayi yok")
        if hatalar:
            s.append("A1: ana ekranda JS hatasi: %s" % hatalar[0])
        if csp:
            s.append("A1: CSP ihlali: %s" % csp[0])
    finally:
        ctx.close()

    # A2 -- kesfet, Ankara. Il dosyasi YAYINDA duruyor mu.
    ctx, sayfa, hatalar, csp = _sayfa_ac(t, taban + "/kesfet.html?il=06")
    try:
        try:
            sayfa.wait_for_selector(".kart", timeout=BEKLE)
        except Exception:
            s.append("A2: kesfet Ankara'da hic kart cizilmedi (il dosyasi "
                     "yayinda yok olabilir)")
        kart = sayfa.query_selector_all(".kart")
        OLCUM["ankara_kart"] = len(kart)
        # "kart and ..." YAZMIYORUM ve sebebi var: bos liste yanlis tarafa
        # dusuyordu -- SIFIR kart "5'ten az" kontrolunu hic calistirmiyordu.
        if len(kart) < 5:
            s.append("A2: kesfet Ankara'da yalniz %d kart var" % len(kart))
        # YUVA HER ZAMAN DOLU olmali: fotograf yoksa kategori simgesi.
        #
        # ILK YAZIMDA BU KONTROL SAHTEYDI ve sabotaj gosterdi: yalnizca
        # <svg> ETIKETININ varligina bakiyordum. Simgenin ICINI bosalttim
        # -- etiket yerinde kaldi, kontrol "temiz" dedi, kart ise BOMBOS
        # bir kare cizdi. Etiketin varligi doluluk degil; icinde cizim
        # olmasi doluluk.
        bos = sayfa.evaluate("""() => {
            const g = [...document.querySelectorAll('.kart-gorsel')];
            return g.filter(x => {
              if (x.querySelector('img')) return false;
              const s = x.querySelector('svg');
              return !s || s.children.length === 0;
            }).length;
        }""")
        if bos:
            s.append("A2: %d kartin gorsel yuvasi BOS (ne fotograf ne simge)" % bos)
        if hatalar:
            s.append("A2: kesfet JS hatasi: %s" % hatalar[0])
        if csp:
            s.append("A2: kesfet CSP ihlali: %s" % csp[0])
    finally:
        ctx.close()

    # A3 -- konum verilince liste YAKINDAN UZAGA siralaniyor mu.
    #      Kizilay'dan olculdu: 110 m, 131, 131, 139, 153, 158.
    ctx, sayfa, hatalar, _ = _sayfa_ac(
        t, taban + "/kesfet.html?il=06", izin=["geolocation"],
        konum={"latitude": 39.9208, "longitude": 32.8541})
    try:
        dug = sayfa.query_selector("#konum-al")
        if not dug:
            s.append("A3: 'Konumum' dugmesi yok")
        else:
            dug.click()
            sayfa.wait_for_timeout(3000)
            sira = sayfa.evaluate("""() => {
                const t = [...document.querySelectorAll('.kart')]
                  .map(k => (k.innerText.match(/([\\d.,]+)\\s*(m|km)\\b/) || [])
                             .slice(1))
                  .filter(x => x.length === 2)
                  .map(([n, b]) => parseFloat(n.replace(',', '.')) *
                                   (b === 'km' ? 1000 : 1));
                return t.slice(0, 8);
            }""")
            OLCUM["mesafe"] = sira[:4]
            if len(sira) < 3:
                s.append("A3: konum verildi ama kartlarda mesafe rozeti yok")
            elif sira != sorted(sira):
                s.append("A3: liste yakindan uzaga SIRALANMADI: %s" % sira)
            durum = sayfa.query_selector("#konum-durum")
            if not durum or not (durum.inner_text() or "").strip():
                s.append("A3: konum durum yazisi bos")
    finally:
        ctx.close()

    # A5/A6 -- fiyat DAYANAGIYLA yaziliyor mu, yoksa hic yazilmiyor mu.
    #      Bu depodaki kural: yanlis fiyat, fiyatsizliktan kotudur.
    #
    # IL SECIMI KEYFI DEGIL VE ILK YAZIMDA YANLISTI: Ankara'ya bakiyordum
    # ve kontrol "fiyat gosteren tek kart yok" diyordu. Uygulamanin hatasi
    # degil, SAYIM: Ankara'nin 2.360 mekaninin 6'sinda fiyat var (%0,25)
    # ve ilk sayfaya hicbiri dusmuyor. "bayrak=menu" fiyati olanlari
    # suzuyor; Istanbul'da 191 tane var, yani tur DETERMINIST.
    ctx, sayfa, hatalar, _ = _sayfa_ac(
        t, taban + "/kesfet.html?il=34&bayrak=menu")
    try:
        try:
            sayfa.wait_for_selector(".kart", timeout=BEKLE)
        except Exception:
            s.append("A5: 'fiyati olan' suzgeci Istanbul'da HIC kart getirmedi")
            return s
        fiyatsiz = sayfa.evaluate("""() => {
            const k = [...document.querySelectorAll('.kart')];
            // SUZGEC FIYATI OLANLARI GETIRIYOR: fiyatsiz bir kart cikarsa
            // suzgec yalan soyluyor demektir.
            return k.filter(x => !/\\d[\\d.]*\\s*₺/.test(x.innerText)).length;
        }""")
        OLCUM["fiyatli_kart"] = len(sayfa.query_selector_all(".kart"))
        if fiyatsiz:
            s.append("A5: 'fiyati olan' suzgecinde %d kart fiyat GOSTERMIYOR"
                     % fiyatsiz)
        # A5'in asil maddesi: fiyat varsa KAC OLCUMDEN geldigi de yazmali.
        # Kartta degil DETAY PANELINDE -- 2.300 karta ayni cumleyi yazmak
        # listeyi bogardi. Karti acip panele bakiyoruz.
        sayfa.query_selector(".kart").click()
        sayfa.wait_for_timeout(1500)
        if not re.search(r"kalem|ölçüm|fiş", sayfa.inner_text("body"), re.I):
            s.append("A5: mekan paneli fiyat yaziyor ama DAYANAGINI yazmiyor "
                     "(kac kalem / kac fis)")
        if hatalar:
            s.append("A5: panel JS hatasi: %s" % hatalar[0])
    finally:
        ctx.close()
    return s


def _g2_g3(t, taban):
    """DUMAN_TESTI G2-G3: 320 px'te kirpilma ve 44 px dokunma hedefi."""
    s = []
    ctx = t.new_context(viewport={"width": 320, "height": 720})
    sayfa = ctx.new_page()
    try:
        sayfa.goto(taban + "/kesfet.html?il=06", wait_until="domcontentloaded",
                   timeout=BEKLE)
        sayfa.wait_for_timeout(1200)
        kucuk = sayfa.evaluate("""() => {
            const sec = 'button, a.dugme, select, input[type=submit], .mini';
            const kotu = [];
            for (const e of document.querySelectorAll(sec)){
              const r = e.getBoundingClientRect();
              if (r.width === 0 && r.height === 0) continue;   // gizli
              if (r.height < 44)
                kotu.push((e.id || e.className || e.tagName) + ':' +
                          Math.round(r.height));
            }
            return kotu.slice(0, 6);
        }""")
        if kucuk:
            s.append("G3: 320 px'te 44 px'ten kisa dokunma hedefi: %s"
                     % ", ".join(kucuk))
        tasma = sayfa.evaluate(
            "() => document.documentElement.scrollWidth > "
            "document.documentElement.clientWidth + 1")
        if tasma:
            s.append("G2: 320 px'te sayfa YANA kayiyor")
    finally:
        ctx.close()
    return s


def _cevrimdisi(t, taban):
    """DUMAN_TESTI A7: service worker kurulup cevrimdisi sayfayi veriyor mu.

    YERELDE SINANAMAYAN SEY: service worker guvenli kaynak istiyor.
    localhost istisna ama yayindaki kayit yolunun kendisi (kapsam,
    dosya adlari, surum damgasi) ancak burada gorulur."""
    s = []
    ctx = t.new_context()
    sayfa = ctx.new_page()
    try:
        sayfa.goto(taban + "/", wait_until="load", timeout=BEKLE)
        hazir = sayfa.evaluate("""async () => {
            if (!('serviceWorker' in navigator)) return 'destek yok';
            try {
              const r = await navigator.serviceWorker.ready;
              return r && r.active ? 'hazir' : 'etkin degil';
            } catch (e) { return 'hata: ' + e.message; }
        }""")
        if hazir != "hazir":
            s.append("A7: service worker kurulmadi (%s)" % hazir)
            return s
        sayfa.wait_for_timeout(2500)          # kabuk onbellege girsin
        ctx.set_offline(True)
        try:
            sayfa.goto(taban + "/kesfet.html", wait_until="domcontentloaded",
                       timeout=BEKLE)
            metin = sayfa.inner_text("body")
            OLCUM["cevrimdisi_bayt"] = len(metin.strip())
            if not metin.strip():
                s.append("A7: cevrimdisi sayfa BOS geldi")
        except Exception as e:
            s.append("A7: cevrimdisi acilamadi: %s" % str(e).split("\n")[0][:80])
        finally:
            ctx.set_offline(False)
    finally:
        ctx.close()
    return s


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    taban = sys.argv[1]
    if not taban.startswith("http"):
        taban = "https://" + taban
    try:
        import playwright  # noqa: F401
    except ImportError:
        sys.exit("playwright yok: pip install playwright && playwright install chromium")

    print("YAYIN TURU: %s\n" % taban, flush=True)
    try:
        s = kos(taban)
    except Exception as e:
        # AGA ULASILAMAMASI BIR OLCUM DEGIL. Bu depodaki kural:
        # basarisizligi sayiya cevirme.
        sys.exit("TUR KOSULAMADI: %s: %s\nBu bir sonuc DEGIL -- siteye "
                 "ulasilamadi." % (type(e).__name__, str(e)[:120]))

    print("OLCULEN: Ankara %s kart · fiyatli suzgecte %s kart · "
          "en yakin dort mesafe %s m · cevrimdisi %s karakter"
          % (OLCUM.get("ankara_kart", "?"), OLCUM.get("fiyatli_kart", "?"),
             OLCUM.get("mesafe", "?"), OLCUM.get("cevrimdisi_bayt", "?")))

    # GORMESI GEREKENI GORDU MU. Bir tur 15 saniyede "temiz" donebiliyor
    # ve bu yayinin hizli olmasindan da olabilir, sayfanin hic
    # yuklenmemesinden de. Ikisini ayiran sey SAYI.
    for anahtar, en_az, ad in (("ankara_kart", 5, "Ankara kart"),
                               ("fiyatli_kart", 5, "fiyatli kart"),
                               ("cevrimdisi_bayt", 20, "cevrimdisi metin")):
        if OLCUM.get(anahtar, 0) < en_az:
            s.append("TUR HICBIR SEY GORMEDI: %s = %s (en az %d bekleniyor)"
                     % (ad, OLCUM.get(anahtar, "yok"), en_az))
    print()

    if s:
        print("%d SORUN:" % len(s))
        for x in s:
            print("  " + x)
        return 1
    print("Yayin turu temiz: acilis, kesfet, konum siralamasi, fiyat "
          "dayanagi, 320 px duzen, cevrimdisi.")
    print("\nELDE KALANLAR (DUMAN_TESTI.md): hesap acma ve e-posta (B),\n"
          "katki gonderme (C), moderasyon (D), isletme sahipligi (E),\n"
          "esikler (F). Hepsi giris ve insan karari istiyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
