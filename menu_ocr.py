# -*- coding: utf-8 -*-
"""Gorsel ve taranmis PDF menuleri NVIDIA NIM gorme modeliyle okur.

menu_pdf_tara.py'nin "gorsel-ocr-gerekli" / "pdf-ocr-gerekli" diye
isaretledigi kayitlari alir, gorseli modele verir, urun+fiyat cikarir.

Dogrulanmis calisma: Guney Yildizi'nin menu.jpeg'i 8/8 dogru okundu
(fiyatlar gorselle elle karsilastirildi). Model uydurmuyor: fiyat
yazmayan menude "fiyat yok" dedi, alakasiz gorselde bos dizi dondurdu.

    python menu_ocr.py pilot   ilk 10 kayit
    python menu_ocr.py tam     hepsi, kaldigi yerden devam eder
    python menu_ocr.py test    kendini kontrol

Her fiyat kaynak URL'siyle kaydedilir; supheli bir deger cikarsa insan
ayni gorsele bakip dogrulayabilir.
"""
import base64
import collections
import csv
import io
import json
import os
import re
import sys
import time

import httpx

from fiyat_analiz import kategorile

BULGU = "menu_pdf_bulgu.csv"
CIKTI = "menu_ocr_kalem.csv"
MODEL = "nvidia/nemotron-nano-12b-v2-vl"
UC = "https://integrate.api.nvidia.com/v1/chat/completions"

# Bu basliklar olmadan bircok sunucu 403 donuyor (olculdu).
TARAYICI = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
}

# DIKKAT: sonuna "Menu degilse bos dizi dondur" eklenmisti ve model ayni
# gorsel icin 8 kalem yerine [] dondurmeye basladi — kacis kapisi verilince
# kacis kapisini kullaniyor. Menu olmayan gorseli menu_mu() zaten eliyor,
# istemde ayrica soylemeye gerek yok.
ISTEM = ("Bu bir restoran menusu gorseli. Gorunen her urunu ve fiyatini oku. "
         "YALNIZCA JSON dizisi dondur: [{\"ad\":\"...\",\"fiyat\":123}]. "
         "Fiyati okunamayan urunu atla. Gormedigin hicbir seyi uydurma.")

# Fix/set menu: tek fiyat TUM menuyu kapsiyor, tek yemegi degil. Muhtar
# vakasi: gorselde "HAFTA ICI 2.500₺ / CUMA-CUMARTESI 3.150₺" yaziyor,
# yemeklerin yaninda fiyat yok; model 2500'u 9 yemege birden yazdi.
# uydurma_mi() kacirdi (9/13 = %69, esik %80) ve esigi dusuremeyiz:
# Guney Yildizi'nda da 5/8 kofte ayni fiyat (%62) ve o gercek.
FIX_MENU = re.compile(r"fix[\s_-]*men[uü]|set[\s_-]*men[uü]|tabldot", re.I)

# Ucuncu taraf toplayicilar: mekanin KENDI sitesi degil. Projenin kurali
# bunlardan veri almamak (kullanim sartlari + yayinlama hakki). Olculen
# vaka: restaurantguru'daki Bagdat Marmaris gorseli filigranli, yillar
# oncesinin fiyatlarini tasiyor (7₺ corba) ve OCR isimleri bozdu
# ("ARNAVUT CIGERI" -> "ARNAUT OGRER"), bir fiyati da yanlis okudu (23->25).
UCUNCU_TARAF = re.compile(
    r"restaurantguru|zomato|tripadvisor|yelp|foursquare|yemeksepeti|"
    r"getir\.com|trendyol|migros|fuudy|neredeyesek", re.I)

TABAN, TAVAN = 15.0, 5000.0
MENU_SAYILIR = 2          # bu kadar yiyecek tanimlanmazsa gorsel menu degil
BEKLE = 1.5               # ucretsiz katman: istekler arasi saniye


def anahtar():
    """NVIDIA anahtarini once ortamdan, sonra .env'den okur."""
    k = os.environ.get("NVIDIA_API_KEY")
    if k:
        return k.strip()
    if os.path.exists(".env"):
        for satir in io.open(".env", encoding="utf-8"):
            if satir.startswith("NVIDIA_API_KEY="):
                return satir.split("=", 1)[1].strip()
    sys.exit("NVIDIA_API_KEY yok: .env dosyasina yaz veya ortam degiskeni ver")


def json_ayikla(metin):
    """Modelin cevabindaki JSON dizisini cikarir (``` blogu icinde olabilir)."""
    e = re.search(r"\[.*\]", metin, re.S)
    if not e:
        return []
    try:
        return json.loads(e.group(0))
    except json.JSONDecodeError:
        return []


def kalemleri_dogrula(ham):
    """Modelin dondurdugu listeyi suzer.

    Model dogru davraniyor ama guvenmek yerine sinirlari burada zorunlu
    kiliyoruz: fiyati olmayan, sayiya cevrilemeyen veya makul araligin
    disinda kalan kalem alinmaz.
    """
    cikan = []
    for k in ham:
        if not isinstance(k, dict):
            continue
        ad = str(k.get("ad", "")).strip()
        if len(ad) < 3:
            continue
        try:
            fiyat = float(str(k.get("fiyat", "")).replace(",", "."))
        except (ValueError, TypeError):
            continue
        if TABAN <= fiyat <= TAVAN:
            cikan.append((ad, fiyat))
    return cikan


def menu_mu(kalemler):
    """Yiyecek olarak siniflanan kalem yoksa gorsel menu degildir."""
    return sum(1 for ad, _ in kalemler if kategorile(ad)[0]) >= MENU_SAYILIR


def uydurma_mi(kalemler):
    """Fiyatlarin uydurulmus olma isaretini arar.

    Olculmus vaka: Sagaris'in menusunde HIC fiyat yok (yemek adi + malzeme
    yaziyor). Model gorseldeki "01, 02, 03" sira numaralarini gorup 12
    kalemin hepsine 123 TL yazdi. menu_mu() yakalayamadi cunku adlar gercek
    yiyecek. Gercek bir menude fiyatlar cesitlenir; tek degere yapisma
    uydurmanin en guclu isaretidir.
    """
    if len(kalemler) < 3:
        return False, ""
    farkli = {f for _, f in kalemler}
    if len(farkli) == 1:
        return True, "%d kalemin hepsi ayni fiyat (%s)" % (len(kalemler), farkli.pop())
    en_sik = max(farkli, key=lambda f: sum(1 for _, x in kalemler if x == f))
    oran = sum(1 for _, f in kalemler if f == en_sik) / len(kalemler)
    if oran >= 0.8:
        return True, "kalemlerin %%%d'i ayni fiyat (%s)" % (round(oran * 100), en_sik)
    return False, ""


def pdf_metniyle_dogrula(pdf_verisi, kalemler):
    """PDF'in metin katmani varsa her fiyatin sayfada gercekten yazdigini sinar.

    Tasarim PDF'lerinin cogunda secilebilir metin var; fiyat orada
    gecmiyor ise model onu uydurmustur. Metin katmani yoksa (taranmis
    sayfa) sinama yapilamaz, kalemler oldugu gibi doner.
    """
    import fitz
    try:
        with fitz.open(stream=pdf_verisi, filetype="pdf") as d:
            metin = "\n".join(s.get_text() for s in d)
    except Exception:
        return kalemler, ""
    if len(metin.strip()) < 40:
        return kalemler, ""            # taranmis sayfa: metin katmani yok
    sayilar = set(re.findall(r"\d{1,4}(?:[.,]\d{1,2})?", metin))
    normal = {s.replace(",", ".").rstrip("0").rstrip(".") for s in sayilar}
    kalan = []
    for ad, f in kalemler:
        for bicim in ("%g" % f, "%d" % int(f) if f == int(f) else "%g" % f):
            if bicim in normal or bicim in sayilar:
                kalan.append((ad, f))
                break
    atilan = len(kalemler) - len(kalan)
    return kalan, ("%d fiyat PDF metninde yok, atildi" % atilan) if atilan else ""


def gorsel_indir(istemci, url):
    """(gorsel_baytlari, mime, pdf_baytlari_veya_None, hata) dondurur."""
    y = istemci.get(url, headers=TARAYICI, timeout=40, follow_redirects=True)
    tur = y.headers.get("content-type", "")
    if y.status_code != 200:
        return None, None, None, "HTTP %s" % y.status_code
    if "image" in tur:
        return y.content, ("image/png" if "png" in tur else "image/jpeg"), None, None
    if "pdf" in tur or url.lower().split("?")[0].endswith(".pdf"):
        import fitz
        with fitz.open(stream=y.content, filetype="pdf") as d:
            if not len(d):
                return None, None, None, "bos pdf"
            # ilk sayfa 200 dpi: taranmis menuler genelde tek sayfa
            png = d[0].get_pixmap(dpi=200).tobytes("png")
        return png, "image/png", y.content, None
    return None, None, None, "beklenmeyen tur: %s" % tur[:30]


def oku(istemci, k, veri, mime, deneme=3):
    """NIM cagrisi. HTTP 5xx gecici sunucu hatasi — yeniden denenir."""
    son = ""
    for i in range(deneme):
        y = istemci.post(
            UC, headers={"Authorization": "Bearer " + k}, timeout=180,
            json={"model": MODEL, "max_tokens": 1600, "temperature": 0.0,
                  "messages": [{"role": "user", "content": [
                      {"type": "text", "text": ISTEM},
                      {"type": "image_url", "image_url": {
                          "url": "data:%s;base64,%s"
                                 % (mime, base64.b64encode(veri).decode())}}]}]})
        if y.status_code == 200:
            return y.json()["choices"][0]["message"]["content"]
        son = "NIM HTTP %s: %s" % (y.status_code, y.text[:100])
        if y.status_code < 500:
            break
        time.sleep(2 * (i + 1))
    raise RuntimeError(son)


YAZI_SORUSU = (
    "Bu gorselde okunabilir YAZI var mi? Sadece gorduklerini soyle. "
    "Cevap bicimi: once EVET veya HAYIR, sonra gordugun ilk 5 kelime. "
    "Yazi yoksa sadece HAYIR yaz.")


def yazi_var_mi(istemci, k, veri, mime):
    """Fiyat sormadan ONCE: bu gorselde yazi var mi?

    Olculen vaka: Adanali Kebapci Mehmet'in "menu" gorseli aslinda bir
    YEMEK FOTOGRAFI — uzerinde tek harf yok. Model yine de 10 kalem ve 9
    farkli fiyat uydurdu; uydurma_mi() yakalayamadi cunku fiyatlar
    cesitliydi. Model tembel degil, IKNA EDICI uyduruyor.

    Cozum: fiyatin varligini varsaymayan notr bir soru. Yemek fotografina
    "HAYIR", gercek menuye "EVET + gordugu kelimeler" donuyor.
    """
    y = istemci.post(
        UC, headers={"Authorization": "Bearer " + k}, timeout=120,
        json={"model": MODEL, "max_tokens": 120, "temperature": 0.0,
              "messages": [{"role": "user", "content": [
                  {"type": "text", "text": YAZI_SORUSU},
                  {"type": "image_url", "image_url": {
                      "url": "data:%s;base64,%s"
                             % (mime, base64.b64encode(veri).decode())}}]}]})
    if y.status_code != 200:
        raise RuntimeError("NIM HTTP %s: %s" % (y.status_code, y.text[:100]))
    return y.json()["choices"][0]["message"]["content"].strip().upper().startswith("EVET")


def islenmis():
    if not os.path.exists(CIKTI):
        return set()
    with io.open(CIKTI, encoding="utf-8") as f:
        return {r["kaynak_url"] for r in csv.DictReader(f)}


def yaz(mekan, site, url, kalemler):
    yeni = not os.path.exists(CIKTI)
    with io.open(CIKTI, "a", encoding="utf-8", newline="") as f:
        y = csv.writer(f)
        if yeni:
            y.writerow(["mekan", "website", "kaynak_url", "kalem", "fiyat", "model"])
        y.writerows([[mekan, site, url, ad, fiyat, MODEL] for ad, fiyat in kalemler])


def kendini_kontrol_et():
    ham = json_ayikla('```json\n[{"ad":"Adana Köfte","fiyat":130},'
                      '{"ad":"Ayran","fiyat":"60"},{"ad":"Xy","fiyat":300},'
                      '{"ad":"Kola","fiyat":null}]\n```')
    assert len(ham) == 4, ham
    c = dict(kalemleri_dogrula(ham))
    # "Xy" 3 harften kisa, null fiyat sayiya cevrilemez -> ikisi de elenir
    assert c == {"Adana Köfte": 130.0, "Ayran": 60.0}, c
    assert dict(kalemleri_dogrula([{"ad": "Cay", "fiyat": 9}])) == {}, "taban alti alindi"
    assert menu_mu(list(c.items())), "gercek menu reddedildi"
    assert not menu_mu([("FOR FISCAL YEAR", 2025.0), ("Table", 79.0)]), "cop menu sayildi"
    assert json_ayikla("bu bir menu degil") == []

    # Fix menu kaynagi elenmeli: tek fiyat tum menuyu kapsiyor (Muhtar vakasi)
    assert FIX_MENU.search("https://x.com/uploads/Muhtar-fixmenu-04-2026.jpg")
    assert FIX_MENU.search("https://x.com/fix menu.jpg")
    assert not FIX_MENU.search("https://x.com/uploads/2025/06/menu.jpeg"), \
        "normal menu fix menu sayildi"

    # Ucuncu taraf toplayici elenmeli: mekanin kendi sitesi degil
    assert UCUNCU_TARAF.search("https://menu02.restaurantguru.com/m6/X-menu.jpg")
    assert not UCUNCU_TARAF.search("https://yumurtalikguneyyildizi.com/menu.jpeg"), \
        "mekanin kendi sitesi ucuncu taraf sayildi"

    # Gercek uydurma vakasi: Sagaris menusunde hic fiyat yok, model 12
    # kalemin hepsine 123 TL yazdi. Bu bir daha gecmemeli.
    sagaris = [("ROKA DOMATES", 123.0), ("İSTANBUL SALATASI", 123.0),
               ("ÇOBAN SALATA", 123.0), ("MİDYE DOLMA", 123.0),
               ("BİBER BORANI", 123.0)]
    supheli, sebep = uydurma_mi(sagaris)
    assert supheli, "Sagaris uydurmasi yakalanmadi"
    assert menu_mu(sagaris), "test kurgusu bozuk: adlar yiyecek olmali"
    # gercek menu (Guney Yildizi, elle dogrulandi) supheli sayilmamali
    guney = [("Ekmek Arası Köfte", 130.0), ("Servis Köfte", 160.0),
             ("Adana Köfte", 130.0), ("Kasap Köfte", 130.0),
             ("Tekirdağ Köfte", 130.0), ("Hamburger & Patates", 150.0),
             ("Şnitzel & Patates", 150.0), ("Balık Ekmek", 130.0)]
    assert not uydurma_mi(guney)[0], "gercek menu uydurma sayildi"

    print("kontrol gecti: JSON ayiklama, fiyat suzme, menu ve uydurma dogrulamasi")
    return True


def main(kip):
    if not os.path.exists(BULGU):
        sys.exit("%s yok — once: python menu_pdf_tara.py pilot" % BULGU)
    with io.open(BULGU, encoding="utf-8") as f:
        hepsi = list(csv.DictReader(f))

    # Ayni gorsel birden fazla mekana aitse o bir sablon/platform gorseli,
    # o mekanin menusu degil. Olculen vaka: menus_side_image.7077f229.jpeg
    # 8 ayri mekanda cikti ve dordune ayni "Cay 15 / Biber Corba 25" menusu
    # yazildi. Uydurma degil ama YANLIS MEKANA atanmis veri.
    sahip = collections.defaultdict(set)
    for r in hepsi:
        if r["kaynak_url"]:
            sahip[r["kaynak_url"]].add(r["mekan"])
    paylasilan = {u for u, m in sahip.items() if len(m) > 1}
    if paylasilan:
        print("Sablon sayilip atlanan kaynak: %d" % len(paylasilan))

    aday = [r for r in hepsi
            if r["tur"] in ("gorsel-ocr-gerekli", "pdf-ocr-gerekli")
            and r["kaynak_url"] and r["kaynak_url"] not in paylasilan
            and not FIX_MENU.search(r["kaynak_url"])
            and not UCUNCU_TARAF.search(r["kaynak_url"])]
    atla = islenmis()
    kalan = [r for r in aday if r["kaynak_url"] not in atla]
    if kip == "pilot":
        kalan = kalan[:10]
    print("OCR adayi: %d · islenmis: %d · bu turda: %d" % (len(aday), len(atla), len(kalan)))

    k = anahtar()
    basarili = toplam_kalem = 0
    with httpx.Client(verify=False) as istemci:
        for i, r in enumerate(kalan, 1):
            url = r["kaynak_url"]
            etiket = "[%2d/%d] %-24s" % (i, len(kalan), r["mekan"][:24])
            try:
                veri, mime, pdf, hata = gorsel_indir(istemci, url)
                if hata:
                    print("%s indirilemedi: %s" % (etiket, hata))
                    continue
                # Once notr kapi: gorselde yazi var mi? Yoksa fiyat sormak
                # modeli uydurmaya davet ediyor (Adanali vakasi).
                if not yazi_var_mi(istemci, k, veri, mime):
                    print("%s gorselde yazi yok (yemek fotografi), atlandi" % etiket)
                    time.sleep(BEKLE)
                    continue
                kalemler = kalemleri_dogrula(json_ayikla(oku(istemci, k, veri, mime)))
                if pdf and kalemler:
                    kalemler, uyari = pdf_metniyle_dogrula(pdf, kalemler)
                    if uyari:
                        print("%s %s" % (etiket, uyari))
                supheli, sebep = uydurma_mi(kalemler)
                if not kalemler:
                    print("%s fiyat cikmadi" % etiket)
                elif supheli:
                    print("%s UYDURMA SUPHESI, atlandi: %s" % (etiket, sebep))
                elif not menu_mu(kalemler):
                    print("%s menu degil (%d kalem elendi)" % (etiket, len(kalemler)))
                else:
                    yaz(r["mekan"], r["website"], url, kalemler)
                    basarili += 1
                    toplam_kalem += len(kalemler)
                    print("%s %d kalem  ornek: %s %s TL"
                          % (etiket, len(kalemler), kalemler[0][0][:22], kalemler[0][1]))
            except Exception as e:
                print("%s HATA %s" % (etiket, str(e)[:70]))
            time.sleep(BEKLE)

    print("\n%d/%d gorselden menu okundu · %d kalem -> %s"
          % (basarili, len(kalan), toplam_kalem, CIKTI))


if __name__ == "__main__":
    kip = sys.argv[1] if len(sys.argv) > 1 else "pilot"
    if kip == "test":
        sys.exit(0 if kendini_kontrol_et() else 1)
    main(kip)
