#!/usr/bin/env python3
"""turkiye_mekanlar.csv + turkiye_eglence.csv + menu verisi -> uygulama JSON'lari.

Kullanim:  python app_veri.py

Cikti:
    app/veri/index.json     il listesi + mekan sayilari
    app/veri/<kod>.json     o ilin mekanlari

Menu gurultusu burada elenir: sitelerin cogu perakende urun katalogu
(kavrulmus cekirdek paketi, pasta siparisi) yayinliyor; bunlar "masada ne
oderim" sorusunun cevabi degil. Bu yuzden asiri uc fiyatlar atilir ve
uygulamada ORTALAMA HESAP degil, MENU KALEMI ARALIGI gosterilir.
"""
import csv
import html
import json
import os
import re
import unicodedata
from collections import defaultdict

from fiyat_analiz import (TABAN, TAVAN, kampanya_mi, kategorile,
                          sadelestir, yiyecek_mi)

import veri_bicim   # il dosyasi bicimi tek yerde

IL_KODU = {
    "Adana": "01", "Adiyaman": "02", "Afyonkarahisar": "03", "Agri": "04",
    "Amasya": "05", "Ankara": "06", "Antalya": "07", "Artvin": "08",
    "Aydin": "09", "Balikesir": "10", "Bilecik": "11", "Bingol": "12",
    "Bitlis": "13", "Bolu": "14", "Burdur": "15", "Bursa": "16",
    "Canakkale": "17", "Cankiri": "18", "Corum": "19", "Denizli": "20",
    "Diyarbakir": "21", "Edirne": "22", "Elazig": "23", "Erzincan": "24",
    "Erzurum": "25", "Eskisehir": "26", "Gaziantep": "27", "Giresun": "28",
    "Gumushane": "29", "Hakkari": "30", "Hatay": "31", "Isparta": "32",
    "Mersin": "33", "Istanbul": "34", "Izmir": "35", "Kars": "36",
    "Kastamonu": "37", "Kayseri": "38", "Kirklareli": "39", "Kirsehir": "40",
    "Kocaeli": "41", "Konya": "42", "Kutahya": "43", "Malatya": "44",
    "Manisa": "45", "Kahramanmaras": "46", "Mardin": "47", "Mugla": "48",
    "Mus": "49", "Nevsehir": "50", "Nigde": "51", "Ordu": "52",
    "Rize": "53", "Sakarya": "54", "Samsun": "55", "Siirt": "56",
    "Sinop": "57", "Sivas": "58", "Tekirdag": "59", "Tokat": "60",
    "Trabzon": "61", "Tunceli": "62", "Sanliurfa": "63", "Usak": "64",
    "Van": "65", "Yozgat": "66", "Zonguldak": "67", "Aksaray": "68",
    "Bayburt": "69", "Karaman": "70", "Kirikkale": "71", "Batman": "72",
    "Sirnak": "73", "Bartin": "74", "Ardahan": "75", "Igdir": "76",
    "Yalova": "77", "Karabuk": "78", "Kilis": "79", "Osmaniye": "80",
    "Duzce": "81",
}

# Ascii il adlarini ekranda dogru yazmak icin
IL_ADI = {
    "Adiyaman": "Adıyaman", "Agri": "Ağrı", "Aydin": "Aydın",
    "Balikesir": "Balıkesir", "Bingol": "Bingöl", "Canakkale": "Çanakkale",
    "Cankiri": "Çankırı", "Corum": "Çorum", "Diyarbakir": "Diyarbakır",
    "Elazig": "Elazığ", "Eskisehir": "Eskişehir", "Gumushane": "Gümüşhane",
    "Hakkari": "Hakkâri", "Istanbul": "İstanbul", "Izmir": "İzmir",
    "Kirklareli": "Kırklareli", "Kirsehir": "Kırşehir", "Kutahya": "Kütahya",
    "Kahramanmaras": "Kahramanmaraş", "Mugla": "Muğla", "Mus": "Muş",
    "Nevsehir": "Nevşehir", "Nigde": "Niğde", "Sanliurfa": "Şanlıurfa",
    "Sirnak": "Şırnak", "Tekirdag": "Tekirdağ", "Usak": "Uşak",
    "Igdir": "Iğdır", "Karabuk": "Karabük", "Duzce": "Düzce",
    "Bartin": "Bartın", "Kirikkale": "Kırıkkale",
}

TUR_TR = {"cafe": "Kafe", "restaurant": "Restoran", "bar": "Bar",
          "pub": "Pub", "fast_food": "Fast food", "ice_cream": "Dondurma",
          # eglence_cek.py'nin topladiklari
          "nightclub": "Gece kulübü", "cinema": "Sinema", "theatre": "Tiyatro",
          "music_venue": "Canlı müzik", "arts_centre": "Sanat merkezi",
          "events_venue": "Etkinlik alanı", "casino": "Kumarhane",
          "bowling_alley": "Bowling", "amusement_arcade": "Oyun salonu",
          "escape_game": "Kaçış oyunu", "water_park": "Aquapark",
          "ice_rink": "Buz pisti", "trampoline_park": "Trambolin parkı",
          "miniature_golf": "Mini golf", "dance": "Dans salonu",
          "adult_gaming_centre": "Oyun merkezi", "museum": "Müze",
          "theme_park": "Tema parkı", "zoo": "Hayvanat bahçesi",
          "aquarium": "Akvaryum", "gallery": "Sanat galerisi"}

# Menu kalemi sayilabilecek makul araliklar (TL). Disari cikan degerler
# perakende urun / hediye paketi / veri hatasidir. Deger fiyat_analiz'den
# geliyor: olcut da bu boru hatti da AYNI kalemleri gormeli, yoksa olcut
# uygulamanin gostermedigi fiyatlardan hesaplanmis olur.
ALT_SINIR, UST_SINIR = TABAN, TAVAN

# --- Fiyatin yasi -------------------------------------------------------
# Enflasyonda tarihsiz fiyat bir iddia degil, bir tahmindir. Toplayici
# betikler (menu_topla, menu_pdf_tara, menu_ocr) artik her satira derleme
# gununu yaziyor. Bu sabit YALNIZ o kolondan onceki satirlar icin:
# tr_menu.csv'nin depoya girdigi gun. Kesin derleme gunu degil, UST SINIR --
# veri o gunden once toplandi, sonra degil. Uydurmak yerine bildigimiz
# siniri yaziyoruz.
TARIHSIZ_TABAN = "2026-08-20"


def _tarih(satir):
    t = (satir.get("tarih") or "").strip()[:10]
    return t if len(t) == 10 and t[4] == "-" else TARIHSIZ_TABAN

# --- Tema demosu tespiti -------------------------------------------------
# Cok sayida isletme hazir bir restoran temasi kurup ORNEK MENUYU HIC
# SILMIYOR. O sayfalar gercek gibi kaziniyor ama icerik temanin demosu:
#   "Meat Cheese", "Behold Meat", "Coffee Cup"  -> 11 kalemin hepsi 30,00 TL
#   "Stylish Flower Pot", "Decorative Telescope" -> mobilya, yemek degil
# Bu, OCR uydurmasindan daha sinsi: veri isletmenin KENDI sitesinden geliyor,
# o yuzden kaynak dogrulamasi yakalamiyor. Yapisal izlerden tespit ediliyor.

# 2026 gercegi: bu esiklerin altinda bir mekan medyani gercek fiyat degildir.
TUR_ALT_MEDYAN = {"Restoran": 80, "Bar": 60, "Pub": 60,
                  "Kafe": 30, "Fast food": 35, "Dondurma": 25}

# Yemek olmayan fiziksel urun ve hizmet: kupa, surahi, elbise, sac orgusu,
# yillik abonelik... Menu sayfasinda ayni tabloda duruyorlar.
URUN_HIZMET = re.compile(r"\b(mug|kupa|sürahi|dress|elbise|tişört|t-shirt|termos|"
                         r"fincan|demlik|öğütücü|abonelik|yıllık üyelik|üyelik|masaj)", re.I)   # sonda sinir yok: Türkçe ek alıyorlar

SOS_AD = re.compile(r"\b(sos|mayonez|ketçap|hardal|wasabi|turşu|garnitür|"
                    r"sriracha|cheddar sos|ranch|barbekü|bbq)(u|su|ları|leri|lar|ler)?[^A-Za-zÇĞİÖŞÜçğıöşü]*$", re.I)   # sona demirli: baş isim sonda

# Malzeme listesi kalem adi degildir: "DOMATES SOS, MOZZARELLA, MANTAR, ..."
MALZEME_AD = re.compile(r"^[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ ,0-9()]{17,}$")


def demo_menu_mu(kalemler, tur):
    """Kalem listesi tema demosu mu? Sebebini dondurur, degilse None."""
    if len(kalemler) < 3:
        return None
    fiyatlar = sorted(k["f"] for k in kalemler)
    orta = fiyatlar[len(fiyatlar) // 2]

    if len(set(fiyatlar)) == 1 and len(kalemler) >= 4:
        return "tum kalemler ayni fiyat (%.0f TL)" % orta

    adlar = [k["a"].strip() for k in kalemler]
    if len(set(adlar)) <= len(adlar) / 2:
        return "kalem adlari tekrar ediyor"

    if sum(1 for a in adlar if MALZEME_AD.match(a)) >= len(adlar) / 2:
        return "kalem adlari malzeme listesi"

    esik = TUR_ALT_MEDYAN.get(tur)
    if esik and orta < esik:
        return "medyan %.0f TL, %s icin %d TL esiginin altinda" % (orta, tur, esik)
    return None


def menu_degil_mi(kalemler):
    """Bu liste bir menu DEGIL mi? Sebebini dondurur, menuyse None.

    demo_menu_mu yapisal ize bakiyor (ayni fiyat, tekrar eden ad); bu ise
    ICERIGE bakiyor: listede tek bir yiyecek ya da icecek adi geciyor mu?

    NEDEN GEREKTI: kaziyici bazi sitelerde menu sayfasini degil baska bir
    sayfayi bulmus, ya da menu diye baska bir sey satan bir listeyi. Olculdu,
    367 menulu mekanin 41 tekilinde listenin TAMAMI menu disiydi:
      Roxy Bar          -> kalem pil (marka adi ayni, site baska)
      Turk Alman Kitabevi, Minoa -> kitap adlari
      Ada Tesisleri     -> kupe, kolye
      Feriye            -> sinema seansi adlari
      Beltur (7 sube)   -> "Hafta Ici 600 TL" — mekan kirasi
      Agora, Sakli Bahce -> cadirla konaklama fiyati
      Oz Izmir Lokma    -> "300 Kisilik lokma" — toplu siparis
    Bunlarin hicbiri "masada ne oderim"in cevabi degil ve hicbiri fiyat
    iddiasi uretmiyordu; ama detay sayfasinda MENU basligi altinda
    duruyorlardi. Baslik yalan soyluyordu.

    yiyecek_mi() kullaniliyor, kategorile() degil: perakende ve paket
    kapilari burada kapali. "1 KG Kol Boregi" bir porsiyon degildir ama
    borekcinin gercek fiyatidir; "Kucuk Boy Pizza + Patates" tek urun
    fiyati degildir ama pizzacinin gercek fiyatidir. Ikisi de kalir --
    fiyat iddiasi zaten ayri kapidan (kat + ana urun kurali) geciyor.
    """
    if not kalemler:
        return None
    if any(yiyecek_mi(k["a"]) for k in kalemler):
        return None
    return "%d kalemin hicbiri yiyecek/icecek degil (\u00f6r. %s)" % (
        len(kalemler), kalemler[0]["a"][:40])


# Menu kalemi olmayan satir adlari
COP_AD = re.compile(r"(kargo|teslimat|hediye|paket|abonelik|kupon|bagis|bağış|"
                    r"sepet|toplam|indirim)", re.I)

# Yiyecek/icecek olmayan fiziksel urun. Kahve dukkanlari menuyle ayni sayfada
# termos ve fincan takimi da satiyor; bunlar "masada ne oderim"in cevabi degil.
# fiyat_analiz.PERAKENDE burada KULLANILMAZ: o filtre porsiyon safligi icin
# kalibre, "4 Adet Pizzetta" gibi gercek menu kalemlerini de eler.
ESYA = re.compile(r"(alışveriş çantası|termos|makinesi|fincan takım|bardak takım|"
                  r"hediye kart|öğütücü|demlik|tişört|kupa takım|filtre kağıd)", re.I)

# Kalem adi degil, SAYFANIN KENDI YAZISI. Kaziyici fiyatin yanindaki etiketi
# urun adi sanip almis: "Normal fiyat 540 TL", "Regular price 1.800 TL",
# "55k kisi favoriledi! 70 TL". Kullaniciya menu diye gosterilen sey, o
# sayfadaki arayuz metniydi.
#
# Tam ad eslesmesi (^...$) BILEREK: "Fiyat" atilir ama "Fiyatlı Kahvaltı"
# kalir. Bu satirlar zaten oldugu gibi tekrar ediyor, parca eslesmesine
# gerek yok ve parca eslesmesi gercek kalem adlarini yerdi.
ARAYUZ_AD = re.compile(
    r"^(fiyat[ıi]?|fiyat\s*:\s*\d*|ürün|ürün detayı|normal fiyat|satış fiyatı|"
    r"güncel fiyat|indirimli fiyat|liste fiyatı|regular price|sale price|price|"
    r"tüm fırsatlar|tüm ürünler|en çok satan(lar)?|tüm ürünlerde\s*\d*|"
    r"(tüm özellikler\s*)?yıllık sadece|"
    r"[\d.,]+\s*[km]?\s*kişi favoriledi!?)$", re.I)


# Isletmenin KENDI sitesi degil, uzerinde durdugu PLATFORM. OSM'de 202 mekan
# website etiketine bir sosyal medya ya da pazaryeri profili yazmis. O adresi
# menu diye kazimak, baskasinin icerigini bu isletmeye yazmak demek:
#
#   shopier.com   -> Giresun'daki "Decorative Art World" ile Istanbul'daki
#                    "Baba Sogus", ikisi de pazaryerinin katalogunu aldi
#   trendyol.com  -> "NUT HUNTER"in menusu Trendyol'un arayuzuydu
#                    ("55k kisi favoriledi!" bir urun adi degil)
#
# Alan adina bakiliyor, yola degil: "instagram.com/xkafe" bir profil,
# "qrmenu.actdurum.com" ise A.C.T Durum'un KENDI QR menusu -- ikincisi
# listede yok ve kalmasi dogru.
#
# ONEK SERBEST, "m." ve "mobile." DEGIL. Ilk hali yalniz o ikisini
# taniyordu ve platformlarin DIL ALT ALANLARI kapiyi geciyordu:
# olculdu, "tr-tr.facebook.com" ve "tr.foursquare.com" isletmenin kendi
# sitesi sayiliyordu. Artik alan adinin SONUNA bakiliyor.
#
# Sona bakmak "qrmenu.actdurum.com" kuralini bozmuyor: o adres
# actdurum.com ile bitiyor ve listede actdurum yok.
#
# restaurantguru EKLENDI (17 kayit): bir isletme rehberi, isletmenin
# kendi sitesi degil. Icerigi baskasinin ve oradan menu almak, Google
# Maps'ten almakla ayni sey olurdu -- "Yapilmayacaklar" listesinin
# gerekcesi bu.
PLATFORM = re.compile(
    r"(^|\.)(facebook|instagram|twitter|tiktok|youtube|linktr\.ee|"
    r"linktree|shopier|google|goo\.gl|wixsite|blogspot|wordpress|yemeksepeti|"
    r"getir|trendyol|foursquare|zomato|tripadvisor|yelp|restaurantguru|"
    r"wa\.me|api\.whatsapp)\.", re.I)


# OSM'de instagram dort ayri bicimde yaziliyor (olculdu, 306 kayit):
#   ortakoyadana                                  164  duz kullanici adi
#   https://www.instagram.com/guneyyildiziyumurtalik/  140  tam URL
#   instagram.com/mandalinsound                     1  yolla
#   @mangocoffee.tr                                 1  @ ile
# Hepsi tek bicime indiriliyor: yalniz KULLANICI ADI saklaniyor, adres
# gosterim aninda kuruluyor. Ham degeri tasimak, dort ayri bicimi dort
# ayri yerde ayristirmak demekti.
INSTAGRAM_AD = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def instagram_adi(ham):
    """OSM contact:instagram degerinden kullanici adi. Cozulemezse None."""
    v = (ham or "").strip()
    if not v:
        return None
    v = re.sub(r"^https?://", "", v, flags=re.I)
    v = re.sub(r"^www\.", "", v, flags=re.I)
    v = re.sub(r"^(?:m\.)?instagram\.com/", "", v, flags=re.I)
    v = v.split("?")[0].split("#")[0].strip("@ ")
    # Yol parcasi kalmissa kullanici adi ilk parca ("x/reels" -> "x").
    # Ama BASKA bir alan adiysa deger tamamen reddediliyor:
    # "facebook.com/x" bir instagram kullanicisi degil, ve kirpilinca
    # "facebook.com" diye gecerli gorunuyordu. Noktali kullanici adlari
    # ("mangocoffee.tr") gecerli -- onlarda egik cizgi yok.
    if "/" in v.strip("/"):
        return None
    v = v.strip("/")
    return v if INSTAGRAM_AD.match(v) else None


# Sosyal platformun alan adlari. Kullanici adi cozulurken KENDI alan
# adi kirpiliyor; baska bir platformun adresi geldiyse deger tamamen
# REDDEDILIYOR. Bunu yapmazsak "facebook.com/x" bir instagram kullanicisi
# sanilip kirpiliyor ve "facebook.com" diye gecerli gorunuyordu (instagram
# icin olculmus gercek bir hata).
#
# ALT ALAN ADI SAYILMIYOR ARTIK. Onceden her platformun alt alan adlari
# TEK TEK yaziliydi (m., web., mobile., music.) ve listede olmayan biri
# kapiyi kapatiyordu: "tr-tr.facebook.com/xkafe" REDDEDILIYORDU.
# Turkce Facebook adresi Turkiye'deki isletmelerin en sik kullandigi
# bicim; bugunku OSM verisinde bir kez geciyor ama isletme sitelerinden
# toplanan baglarda en yaygini o olacak.
#
# ALAN ADININ KENDISI YINE TAM: desen "...facebook.com/" ile bitiyor,
# yani "instagram.com.saldirgan.net/x" gecmiyor ve "facebook.com/x" bir
# instagram kullanicisi sanilmiyor (asagidaki iki kural degismedi).
SOSYAL_ALAN = {
    "insta":    (r"(?:[\w-]+\.)*instagram\.com/",),
    "facebook": (r"(?:[\w-]+\.)*facebook\.com/", r"(?:[\w-]+\.)*fb\.com/"),
    "x":        (r"(?:[\w-]+\.)*twitter\.com/", r"(?:[\w-]+\.)*x\.com/"),
    "tiktok":   (r"(?:[\w-]+\.)*tiktok\.com/",),
    "youtube":  (r"(?:[\w-]+\.)*youtube\.com/", r"(?:[\w-]+\.)*youtu\.be/"),
}

# Kullanici adi bicimleri platforma gore ayri: TikTok ve YouTube nokta ve
# tire kabul ediyor, X yalniz alt cizgi ve en fazla 15 hane.
SOSYAL_BICIM = {
    "insta":    re.compile(r"^[A-Za-z0-9._]{1,30}$"),
    "facebook": re.compile(r"^[A-Za-z0-9.\-]{3,60}$"),
    "x":        re.compile(r"^[A-Za-z0-9_]{1,15}$"),
    "tiktok":   re.compile(r"^[A-Za-z0-9._]{1,24}$"),
    "youtube":  re.compile(r"^@?[A-Za-z0-9._\-]{1,40}$"),
}


def sosyal_adi(alan, ham):
    """OSM sosyal etiketinden kullanici adi. Cozulemezse None.

    YouTube'da kanal adresi "/channel/UC..." ya da "/c/ad" olabiliyor;
    o bicimlerde kullanici adi cikarilamaz ve deger REDDEDILIYOR --
    yanlis bir adres uretmektense hic gostermemek dogru.
    """
    v = (ham or "").strip()
    if not v:
        return None
    v = re.sub(r"^https?://", "", v, flags=re.I)
    v = re.sub(r"^www\.", "", v, flags=re.I)
    for kalip in SOSYAL_ALAN.get(alan, ()):
        v = re.sub("^" + kalip, "", v, flags=re.I)
    v = v.split("?")[0].split("#")[0].strip("@ ")
    if "/" in v.strip("/"):
        return None            # yol parcasi kaldi: baska bir sey bu
    v = v.strip("/")
    bicim = SOSYAL_BICIM.get(alan)
    return v if bicim and bicim.match(v) else None


def platform_mu(url):
    """Bu adres isletmenin kendi sitesi degil, bir platform profili mi?"""
    u = re.sub(r"^https?://", "", (url or "").strip().lower())
    u = re.sub(r"^www\.", "", u).split("/")[0]
    # match DEGIL search: kalip artik "(^|\.)" ile basliyor ve alan adinin
    # ORTASINDAKI noktadan sonra da eslesebilmeli ("tr-tr.facebook.com").
    # match() bastan capaliyor ve o hali dil alt alanlarini kaciriyordu.
    return bool(u) and bool(PLATFORM.search(u + "."))


def kalem_adi(ham):
    """CSV'den gelen kalem adini gosterime hazir hale getirir.

    HTML varligi cozuluyor: kaynak sitelerin bir kismi (WooCommerce)
    adlari "6&#8217;li Macaron" diye veriyor ve o dizge kullaniciya
    OLDUGU GIBI gorunuyordu. Olculdu: 59 kalem adinda cozulmemis varlik.
    Siniflandirma zaten cozulmus metinle calisiyordu (fiyat_analiz.temizle),
    yani ad ile kategori ayni kalemde ayri metinlere bakiyordu.

    Kaynak betikte de duzeltildi; burasi bugunku veriyi yeniden
    kazimadan duzeltiyor ve yeni bir kaynak ayni hatayi yaparsa tutuyor.
    """
    return re.sub(r"\s+", " ", html.unescape(ham or "")).strip(" =:-–—·\t")


def kalem_atilir(ad):
    """Bu ad bir menu kalemi adi degil mi? Iki kaynak da ayni kapidan gecsin."""
    return (len(ad) < 3 or COP_AD.search(ad) or ESYA.search(ad)
            or ARAYUZ_AD.match(ad))


# ---------------------------------------------------------------
# SEMT: ilce ve mahalle
#
# NEDEN VAR: adresi olan mekan 9.397 (%26,2). Kalan 26.455'te "burasi
# nerede" sorusunun tek cevabi koordinat. Ama turkiye_mekanlar.csv
# ILCE ve MAHALLE sutunlarini tasiyor ve IKISI DE uygulamaya hic
# ulasmiyordu:
#
#   ilce    7.186 mekan (%20,0)
#   mahalle 3.985 mekan (%11,1)
#   en az biri 7.460 mekan (%20,8)
#
# Adresi OLMAYAN 26.455 mekanin 883'u (%3,3) bununla ilk kez bir yer
# adi kazaniyor. Adres bosluunun tamamini kapatmiyor -- ve bunu
# oldugundan buyuk gostermiyoruz.
#
# TR_BUYUK: "istanbul".title() Python'da "Istanbul" veriyor, "İstanbul"
# degil. Ayni tuzak fiyat_analiz.py'de de yakalanmisti (377 kalem adi).
TR_BUYUK = str.maketrans("iıçğöşü", "İIÇĞÖŞÜ")
MAHALLE_SONEK = re.compile(r"\s*(mahallesi|mahalle|mah\.?)\s*$", re.I)


def _tr_baslik(s):
    """Turkce buyuk harf kurallariyla kelime baslari.

    ONCE TR_BUYUK, SONRA upper(): "i" -> "İ" ozel kural, "m" -> "M"
    siradan. Yalniz translate kullanmak "merkez"i oldugu gibi
    birakiyordu (m tabloda yok) -- kendi denememde gorundu.
    """
    return " ".join(
        (k[0].translate(TR_BUYUK).upper() + k[1:]) if k else k
        for k in s.split(" "))


def semt_adi(ham, mahalle=False):
    """ilce/mahalle degerini tek bicime indirir; kullanilamazsa None.

    OLCULDU (36.103 kayit):
      - ilce'de 63 deger yalniz BUYUK/KUCUK HARF yuzunden ikiye
        boluyordu ("merkez" ve "Merkez", "cankaya" ve "Cankaya").
      - mahalle'de ayni mahalle 211 kez farkli yazimla duruyordu:
        "Cumhuriyet" / "Cumhuriyet Mah." / "Cumhuriyet Mahallesi" /
        "Cumhuriyet mah.". 1.397 ham deger, sadelestirince 1.133.
      - 3 kayitta BIRLESEN NOKTA (U+0307) var: "Pi̇ri̇celebi̇". "İ".lower()
        Python'da tek harf degil; NFC ile toparlaniyor.

    SONEK ATILIYOR, EKLENMIYOR: 611 degerde zaten sonek yok ve
    "Mahallesi" eklemek veride olmayan bir sey uydurmak olurdu.

    ADRESIN TAMAMI KACMIS degerler eleniyor: bir kayitta mahalle
    sutununda "Buyukkumla, ARMUTLU YOLU UZERI NO:220 A, 16600
    Gemlik/Bursa" yaziyor.
    """
    # BIRLESEN NOKTA SILINIYOR. "İ".lower() Python'da tek harf degil,
    # "i" + U+0307 uretiyor ve NFC bunu geri BIRLESTIRMIYOR (U+0130'un
    # ayrisimi "I" + U+0307, "i" + U+0307 degil). fiyat_analiz.CEVIR
    # ayni noktayi ayni sekilde siliyor.
    v = unicodedata.normalize("NFC", (ham or "").strip()).replace("\u0307", "")
    v = re.sub(r"\s+", " ", v).strip(" ,/")
    if not v or len(v) > 30 or "/" in v or "," in v or re.search(r"\d{3}", v):
        return None
    if mahalle:
        v = MAHALLE_SONEK.sub("", v).strip()
    if len(v) < 2:
        return None
    return _tr_baslik(v)


def _menu_anahtari(il, ad):
    """Menu anahtari: (il, ad) -- ad BUYUK/KUCUK HARFTEN BAGIMSIZ.

    Ilk hali tam dizgeydi ve OSM'de ayni mekan iki farkli yazimla
    duruyordu. Olculdu, 4 mekan menusunu bu yuzden alamiyordu:

        Diyarbakir  "Onur OcakBasi"  <-> "Onur Ocakbasi"
        Istanbul    "BELTUR"         <-> "Beltur"
        Istanbul    "karabatak"      <-> "Karabatak"
        Istanbul    "pizza bulls"    <-> "Pizza Bulls"

    YALNIZ HARF BUYUKLUGU dusuruluyor, Turkce harfler DEGIL. ortak.js
    _adAnahtari'nin gerekcesi burada da gecerli: "Cinar" ile "Cinar"i
    ayni saymak iki AYRI isletmeyi tek zincir yapar ve birinin fiyatini
    otekine yapistirir. Az eslestirmek cok eslestirmekten iyi.

    Il anahtarda KALIYOR: zincir adlari illerde tekrar ediyor.
    """
    return (il, (ad or "").casefold())


def menuleri_oku(yol="tr_menu.csv"):
    """Anahtar (il, mekan adi) -- sadece ada bakmak yetmez: zincir adlari
    illerde tekrar ediyor ve Istanbul'daki subeye Ankara'nin fiyatlari yapisir."""
    menu = defaultdict(list)
    try:
        f = open(yol, encoding="utf-8-sig")
    except FileNotFoundError:
        return menu
    with f:
        for r in csv.DictReader(f):
            if platform_mu(r.get("website")):
                PLATFORM_ELENEN.add((r["il"], r["mekan"]))
                continue
            ad = kalem_adi(r["kalem"])
            fiyat = float(r["fiyat"])
            if not (ALT_SINIR <= fiyat <= UST_SINIR):
                continue
            if kalem_atilir(ad):
                continue
            menu[_menu_anahtari(r["il"], r["mekan"])].append(
                {"a": ad, "f": fiyat, "t": _tarih(r)})
    return menu


def _site_anahtari(u):
    """http/https, www ve sondaki / farkini yok sayan site anahtari."""
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")


def _alan_adi(u):
    """Yolu atip yalniz alan adini dondurur: a.com/menu/ -> a.com"""
    return _site_anahtari(u).split("/")[0]


# Ek menu kaynaklari. IKISI DE SITEYE gore birlestiriliyor (asagida).
EK_MENU_KAYNAKLARI = ("menu_pdf_kalem.csv", "menu_ocr_kalem.csv")


def ek_menuler_oku(mekanlar, yollar=EK_MENU_KAYNAKLARI):
    """PDF/sayfa metni ve gorsel OCR ile toplanan menuler.

    Birlestirme anahtari MEKAN ADI degil WEB SITESI: bu kalemler siteler
    taranarak bulundu ve zincir adlari illerde tekrar ediyor ("Domino's"
    10 ilde). Site adresi tek bir mekani gosteriyor.
    """
    # Tam adres eslesmesi ONCE. Alan adina dusmek gerekiyor cunku OSM
    # etiketi yollu olabiliyor ("dokuzondokuz.com/menu/") ama taramadaki
    # kayit kok adresi ("dokuzondokuz.com"). Alan adi eslesmesi yalnizca
    # o alan adi TEK mekana aitse kullanilir: "adilesultanevyemekleri.com"
    # iki ayri subeye ait ve hangisine ait oldugu belirsiz kalir.
    site_mekan, alan_mekan = {}, defaultdict(set)
    for m in mekanlar:
        u = (m.get("website") or "").strip()
        if u and not platform_mu(u):
            # ANAHTAR menuleri_oku ile AYNI bicimde kurulmali. Ilk
            # yazimda burada ham (il, ad) duruyordu ve menu sozlugu
            # casefold'a gecince PDF/OCR kalemleri kimsenin okumadigi
            # bir anahtara dusuyordu: menulu mekan 291 -> 286.
            site_mekan.setdefault(_site_anahtari(u), _menu_anahtari(m["il"], m["ad"]))
            alan_mekan[_alan_adi(u)].add(_menu_anahtari(m["il"], m["ad"]))
    tekil_alan = {a: next(iter(v)) for a, v in alan_mekan.items() if len(v) == 1}

    ek = defaultdict(list)
    eslesmeyen = set()
    for yol in yollar:
        if not os.path.exists(yol):
            continue
        with open(yol, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                u = r.get("website", "")
                if platform_mu(u):
                    continue
                hedef = (site_mekan.get(_site_anahtari(u))
                         or tekil_alan.get(_alan_adi(u)))
                if not hedef:
                    eslesmeyen.add(r.get("mekan", "?"))
                    continue
                ad = kalem_adi(r["kalem"])
                try:
                    fiyat = float(r["fiyat"])
                except (ValueError, TypeError):
                    continue
                if not (ALT_SINIR <= fiyat <= UST_SINIR):
                    continue
                if kalem_atilir(ad):
                    continue
                ek[hedef].append({"a": ad, "f": fiyat, "t": _tarih(r)})
    if eslesmeyen:
        print("ek menu: OSM mekaniyla eslesmeyen %d kayit (%s)"
              % (len(eslesmeyen), ", ".join(sorted(eslesmeyen)[:3])))
    return ek


# Isletmenin KENDI sitesinde yayimladigi sosyal bag.
# menu_pdf_tara.py her siteyi zaten gercek tarayicida aciyor; sosyal
# baglar ayni geciste, ek istek olmadan toplaniyor.
#
# NEDEN GEREKIYOR: OSM'de sosyal etiket seyrek. Olculdu -- 35.852
# mekanin 304'unde (%0,8) hesap var. OSM'yi yeniden cekmek dort eksik
# sutunu dolduruyor ama etiketin OLMADIGI yerde yine bos kaliyor.
# Isletmenin kendi sitesi o bosluga bakan ikinci kaynak.
SITE_SOSYAL = "menu_site_sosyal.csv"

# Alan adi -> uygulamadaki alan. sosyal_adi() zaten her bicimi
# cozuyor; burada yalniz HANGI alana yazilacagi soyleniyor.
SOSYAL_ALANDAN = {
    "instagram.com": "insta",
    "facebook.com": "facebook", "fb.com": "facebook",
    "twitter.com": "x", "x.com": "x",
    "tiktok.com": "tiktok",
    "youtube.com": "youtube", "youtu.be": "youtube",
}


def site_sosyal_oku(mekanlar, yol=SITE_SOSYAL):
    """Site taramasindan gelen sosyal baglar, mekan anahtarina bagli.

    Birlestirme anahtari ek_menuler_oku ile AYNI: WEB SITESI. Zincir
    adlari illerde tekrar ediyor, site adresi tek mekani gosteriyor.
    """
    if not os.path.exists(yol):
        return {}
    site_mekan, alan_mekan = {}, defaultdict(set)
    for m in mekanlar:
        u = (m.get("website") or "").strip()
        if u and not platform_mu(u):
            site_mekan.setdefault(_site_anahtari(u), _menu_anahtari(m["il"], m["ad"]))
            alan_mekan[_alan_adi(u)].add(_menu_anahtari(m["il"], m["ad"]))
    tekil_alan = {a: next(iter(v)) for a, v in alan_mekan.items() if len(v) == 1}

    bul = defaultdict(dict)
    with open(yol, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            hedef = (site_mekan.get(_site_anahtari(r.get("website", "")))
                     or tekil_alan.get(_alan_adi(r.get("website", ""))))
            alan = SOSYAL_ALANDAN.get((r.get("alan") or "").lower())
            if not hedef or not alan:
                continue
            # Bicim kurali TEK YERDE: sosyal_adi. Cozulemeyen bag
            # (gonderi adresi, kanal kimligi) SESSIZCE dusuyor --
            # yanlis bir hesap adresi uretmek, hic uretmemekten kotu.
            deger = sosyal_adi(alan, r.get("url", ""))
            if deger:
                bul[hedef].setdefault(alan, deger)
    return dict(bul)


def kategori_dokumu(kalemler):
    """Mekanin kendi menusunden urun kategorisi kirilimi.

    Butun fiyatlar gercek: hicbir deger hesaplanmiyor, yalniz mekanin kendi
    kaleminden seciliyor. Cift sayida kalemde ust/alt ortalamasi ALINMAZ
    (o gozlenmemis bir fiyat olurdu) — alt medyan, yani gercekten menude
    yazan bir fiyat dondurulur.
    """
    kova = defaultdict(list)
    for k in kalemler:
        kat = kategorile(k["a"])[0]
        if kat:
            kova[kat].append(k["f"])
    dokum = {}
    for kat, fiyatlar in kova.items():
        fiyatlar.sort()
        dokum[kat] = {
            "n": len(fiyatlar),
            "med": fiyatlar[(len(fiyatlar) - 1) // 2],   # alt medyan = gercek kalem
            "min": fiyatlar[0],
            "max": fiyatlar[-1],
            # Kategorinin fiyat TOPLAMI. Mekanin ortalamasi bundan cikiyor:
            # sum(top) / sum(n). Ortalamayi burada hesaplamiyoruz cunku hangi
            # kategorilerin sayilacagina (icecek ve tatli haric) ortak.js
            # karar veriyor; kurali iki dile birden kopyalamak, ikisinin
            # ayrismasi demekti. Toplam ham veri, karar tek yerde kaliyor.
            "top": round(sum(fiyatlar), 2),
        }
    return dokum


# --- Ayni mekanin iki kaydi ---------------------------------------------
# OSM'de bir isletme hem NOKTA (POI) hem ALAN (bina siniri) olarak
# etiketlenebiliyor; ayrica ayni yeri iki kisi ayri ayri eklemis olabiliyor.
# Ikisi de bize ayri mekan gibi geliyordu: haritada iki isaretci, listede
# iki kart, sayilarda bir fazla.
#
# Olculdu: ayni ilde ayni ada sahip ve 20 m'den yakin 212 cift var; 40 m'ye
# cikinca 300, 60 m'ye cikinca 351. Ama uzaklastikca YANLIS eslesme
# basliyor -- "Starbucks" 54 m, "Burger King" 48 m, "Çay ocağı" 53 m:
# bunlar gercekten ayri isletmeler olabilir. 25 m secildi: bu mesafede
# ayni adi tasiyan iki kayit pratikte ayni yerdir.
#
# Ad karsilastirmasi TURKCE HARFE DUYARSIZ. Ilk yazimda tam eslesme
# vardi ("Kahve Dünyası" ile "Kahve Dunyasi" ayri sayiliyordu) ve gerekce
# "zincir subelerini birlestirmeyelim"di -- ama subeleri ayiran sey ad
# degil 25 m sinirlari: iki sube hicbir zaman 25 m'de olmuyor.
#
# Olculdu: ayni mekan bir kez Turkce harflerle bir kez ASCII ile
# girilmis 14 cift kaciyordu -- "Balikci Sabahattin" / "Balıkçı
# Sabahattin" (21 m), "Balkan lokantasi" / "Balkan Lokantası" (3 m).
KOPYA_METRE = 25


def _metre(a, b):
    """Iki kayit arasi mesafe (m). sahiplen.metre ile ayni haversine."""
    from math import radians, sin, cos, asin, sqrt
    dl = radians(b["lat"] - a["lat"])
    dn = radians(b["lon"] - a["lon"])
    h = (sin(dl / 2) ** 2 +
         cos(radians(a["lat"])) * cos(radians(b["lat"])) * sin(dn / 2) ** 2)
    return 6371000 * 2 * asin(sqrt(h))


BILGI_ALANI = ("saat", "tel", "adres", "web", "menu", "bahce", "wifi", "mutfak")


def _zenginlik(k):
    return sum(1 for a in BILGI_ALANI if k.get(a))


def kopyalari_birlestir(kayitlar):
    """Ayni ad + <=25 m olan kayitlari tek kayda indirir.

    Kalan kayit BILGISI COK OLAN. Esitlikte nokta (POI) tercih ediliyor:
    alan kaydinin koordinati bina merkezidir, nokta isletmenin kendisini
    gosterir. Yine esitse kimlik sirasi -- karar her calistirmada ayni olsun.

    Dusen kaydin BOS OLMAYAN alanlari kalana tasiniyor: iki kayittan biri
    telefonu, digeri saati tasiyor olabiliyor; birlestirme bilgi kaybetmemeli.
    """
    gruplar = defaultdict(list)
    for k in kayitlar:
        # casefold DEGIL sadelestir: "İ".casefold() birlesen nokta
        # birakiyor ve "KISMETİM" ile "Kısmetim" ayri gorunuyordu.
        # Kural fiyat_analiz'de, tek yerde.
        gruplar[sadelestir(k["ad"]).strip()].append(k)

    kalan, birlesen = [], 0
    for grup in gruplar.values():
        if len(grup) == 1:
            kalan.extend(grup)
            continue
        # En iyi kayit once: birlestirme hedefi hep o olsun.
        grup.sort(key=lambda k: (-_zenginlik(k),
                                 0 if k["id"].startswith("node/") else 1,
                                 k["id"]))
        alinan = []
        for k in grup:
            for hedef in alinan:
                if _metre(hedef, k) <= KOPYA_METRE:
                    for alan, deger in k.items():
                        if alan not in hedef and deger not in (None, "", 0):
                            hedef[alan] = deger
                    birlesen += 1
                    break
            else:
                alinan.append(k)
        kalan.extend(alinan)
    return kalan, birlesen


ELENEN = []               # rapor icin: (mekan, tur, sebep)
PLATFORM_ELENEN = set()   # rapor icin: (il, mekan) -- platform profili


def mekan_kaydi(m, menu, site_sosyal=None):
    tum_kalemler = menu.get(_menu_anahtari(m["il"], m["ad"]), [])
    tur_tr = TUR_TR.get(m["tur"], m["tur"])

    # Sos ve garnitur kalem degildir; hepsi alt sinira yigilip medyani
    # asagi cekiyor ve mekani oldugundan ucuz gosteriyordu.
    tum_kalemler = [k for k in tum_kalemler
                    if not SOS_AD.search(k["a"])
                    and not URUN_HIZMET.search(k["a"])]

    # Tema demosu ise menunun TAMAMI dusuyor. Guvenilmeyen fiyati yanlis
    # gostermektense hic gostermemek dogru: uygulama "hesapli yer" vaat
    # ediyor, sahte ucuzluk en kotu hata.
    sebep = (demo_menu_mu(tum_kalemler, tur_tr)
             or menu_degil_mi(tum_kalemler)) if tum_kalemler else None
    if sebep:
        ELENEN.append((m["ad"], tur_tr, sebep))
        tum_kalemler = []

    # Kategori dokumu TAM listeden: kayda giren 40 kalem en ucuzlar oldugu icin
    # onlardan hesaplanan kirilim sistematik olarak asagi kayardi.
    #
    # HER KATEGORIDEN EN UCUZ KALEM DE GIRIYOR. Olculdu: "Cebimde
    # kombini" fiyati gosterilebilen 163 mekanin yalniz 47'sinde
    # kurulabiliyordu ve tikanan 116'nin 99'u Domino's idi -- pizzalarin
    # hepsi (~480 TL) en ucuz 40'in disinda kaliyor, listede yalniz
    # garnitur ve icecek duruyordu. Yani mekanin ANA URUNU kayda hic
    # girmiyordu.
    #
    # Ayni carpiklik kullaniciya da gorunuyordu: detay paneli "en ucuz
    # 40 kalem, 35-165 TL" yazip ustunde "yemek ~480 TL" gosteriyordu.
    #
    # Kural MEKANIN ANA URUNUNE BAKMIYOR: "hangi kategori ana urun"
    # karari ortak.js'te (anaKategoriler) ve onu buraya kopyalamak ayni
    # kurali iki dilde tutmak olurdu. Bunun yerine mekanik bir kural --
    # HER kategoriden en ucuz kalem listede. Ana urun de dahil olmak
    # zorunda, cunku o da bir kategori.
    _sirali = sorted(tum_kalemler, key=lambda x: x["f"])
    kalemler = _sirali[:40]
    _sec = {id(k) for k in kalemler}
    _gorulen = set()
    for k in _sirali:                       # ucuzdan pahaliya
        kat = kategorile(k["a"])[0]
        if not kat or kat in _gorulen:
            continue
        _gorulen.add(kat)
        if id(k) not in _sec:
            kalemler.append(k)
            _sec.add(id(k))
    kalemler.sort(key=lambda x: x["f"])
    kayit = {
        "id": m["osm_id"],
        # OSM'de 12 mekan adi bas/son bosluklu girilmis ("Canikli ").
        # Gorunumde fark etmiyor ama kopya birlestirmesi ve siralama ada
        # gore calisiyor; bosluk oralarda sessizce ayirt edici oluyor.
        "ad": " ".join(m["ad"].split()),
        "tur": tur_tr,
        # 5 basamak ~1,1 m. 6 basamak (~11 cm) haritada bir isaretci icin
        # anlamsiz hassasiyet ve 81 dosyada bedava yer kapliyor: yalniz
        # Istanbul'da gzip sonrasi 16 KB. Kesfet ekrani da anasayfa onerisi
        # de kilometre olceginde calisiyor.
        "lat": round(float(m["lat"]), 5),
        "lon": round(float(m["lon"]), 5),
    }
    # Telefon alanina telefon OLMAYAN sey yazilmis kayitlar var: "0",
    # "Köfteci Yusuf". Sayfada "Telefon: Köfteci Yusuf" diye gorunuyordu
    # ve sahiplen.py o mekani "telefonu var" sayip ARAMA listesine
    # koyuyordu. En az 7 rakam araniyor -- Turkiye'de en kisa gecerli
    # numara (alan kodsuz sabit hat) 7 haneli.
    tel = m["telefon"] if len(re.sub(r"\D", "", m["telefon"] or "")) >= 7 else ""

    for anahtar, deger in (("mutfak", m["mutfak"]), ("tel", tel),
                           ("web", m["website"]), ("saat", m["saatler"]),
                           ("adres", m["adres"]),
                           # SEMT: ilce ve mahalle. Ikisi de CSV'de
                           # DOLUYDU ve uygulamaya hic ulasmiyordu --
                           # 7.460 mekan (%20,8) bir yer adi kazaniyor,
                           # adresi olmayan 26.455'in 883'u de ilk kez.
                           ("ilce", semt_adi(m.get("ilce"))),
                           ("mahalle", semt_adi(m.get("mahalle"), True)),
                           # Instagram TOPLANIYORDU ama uygulamaya hic
                           # ulasmiyordu. Olculdu: 194 mekanin instagrami
                           # var ve sitesi YOK -- yani o isletmelere hem
                           # sayfalarinda hem saha kartinda "sosyal medya
                           # baginiz yok" diyorduk, elimizde dururken.
                           ("insta", instagram_adi(m.get("instagram"))),
                           # Diger platformlar. CSV'de sutun YOKSA (eski
                           # cekim) m.get() bos doner ve alan hic yazilmaz;
                           # boru hatti eski veriyle de calisiyor.
                           ("facebook", sosyal_adi("facebook", m.get("facebook"))),
                           ("x",        sosyal_adi("x",        m.get("x"))),
                           ("tiktok",   sosyal_adi("tiktok",   m.get("tiktok"))),
                           ("youtube",  sosyal_adi("youtube",  m.get("youtube")))):
        if deger:
            kayit[anahtar] = deger

    # UCUNCU KAYNAK: isletmenin kendi sitesindeki sosyal baglar
    # (menu_pdf_tara.py ayni geciste topluyor). OSM etiketi VARSA o
    # kaliyor -- ikisi celisirse OSM'yi bir insan elle yazmis, sitedeki
    # bag bir kaziyicinin buldugu; celiskide elle yazilan kazanir.
    for anahtar, deger in (site_sosyal or {}).get(
            _menu_anahtari(m["il"], m["ad"]), {}).items():
        kayit.setdefault(anahtar, deger)
    if m["bahce"] == "yes":
        kayit["bahce"] = 1
    if m["wifi"] in ("wlan", "yes"):
        kayit["wifi"] = 1
    if kalemler:
        # Mekanin fiyat tarihi = kalemlerin EN ESKISI. Bir menude 39 kalem
        # dun, biri gecen yil derlendiyse o menu bir yillik: yeni kalem
        # eskisini tazelemiyor. Kullaniciya soylenen sey en kotu hal olmali.
        #
        # Ay hassasiyeti: gun bilgisi ekranda hicbir karar degistirmiyor
        # ("14 Agustos" ile "20 Agustos" arasinda kullanici icin fark yok)
        # ve 81 dosyada bedava yer kapliyor.
        kayit["tarih"] = min(k["t"] for k in tum_kalemler)[:7]
        # Kalemin KATEGORISI de yaziliyor ("Pizza", "Kola / gazli").
        #
        # NEDEN: "Cebimde kombini" -- 300 TL ile bu mekanda ne yenir --
        # ana urun ile icecegi AYIRT EDEBILMEYI gerektiriyor. Kategori
        # yalniz kat[] toplamlarindaydi, tek tek kalemlerde yoktu; yani
        # tarayici "bu satir pizza mi kola mi" diyemiyordu.
        #
        # Kural PYTHON'DA KALIYOR (fiyat_analiz.kategorile). Tarayiciya
        # kopyalamak, ayni sozlugu iki dilde tutmak demekti -- kat[]
        # toplamlarinin burada uretilmesinin gerekcesiyle ayni.
        #
        # Kategorilenemeyen kalemde alan HIC YAZILMIYOR: null yazmak 81
        # dosyada bedava yer kaplardi ve "bilinmiyor" ile "yok" ayrimini
        # bozmazdi.
        kayit["menu"] = []
        for k in kalemler:
            kalem = {"a": k["a"], "f": k["f"]}
            kat = kategorile(k["a"])[0]
            if kat:
                kalem["k"] = kat
            # KAMPANYA BAYRAGI ("p"). Satir bir urun degil bir teklif:
            # "1 Alana 1 Bedava Icecek 120 TL" sira menude 120 liralik bir
            # icecek gibi duruyordu. Kural PYTHON'DA (fiyat_analiz), kat[]
            # ve kategori ile ayni gerekce -- sozlugu iki dilde tutmuyoruz.
            #
            # Bayrak, ayirmayi ARAYUZE birakiyor: satir veriden ATILMIYOR
            # (teklif gercek ve butceye bakan icin degerli), yalniz kendi
            # bolumune gidiyor ve kombinden/civardan uzak duruyor.
            if kampanya_mi(k["a"]):
                kalem["p"] = 1
            kayit["menu"].append(kalem)
        kayit["min"] = kalemler[0]["f"]
        kayit["max"] = kalemler[-1]["f"]
        # Liste kirpildiysa GERCEK kalem sayisi da yaziliyor.
        #
        # Neden: "menu" en ucuz 40 kalem, "kat" ise TAM listeden. Ikisi ayri
        # ayri dogru ama arayuz "40 kalem · 35-165 TL" yazip ustunde
        # "yemek ~480 TL" gosterince celisiyordu -- kullanici menusunde en
        # pahali kalemi 165 TL olan bir yerde 480 TL iddiasi goruyor.
        # Olculdu: 367 menulu mekanin 131'inde (%36) kat medyani, gosterilen
        # menunun max'ini asiyor. Arayuz artik aralgin neyin araligi
        # oldugunu soyleyebilsin diye sayi buraya yaziliyor.
        if len(tum_kalemler) > len(kalemler):
            kayit["kalem_n"] = len(tum_kalemler)
        dokum = kategori_dokumu(tum_kalemler)
        if dokum:
            kayit["kat"] = dokum
    return kayit


def main():
    menu = menuleri_oku()
    mekanlar = list(csv.DictReader(open("turkiye_mekanlar.csv", encoding="utf-8-sig")))

    # Eglence mekanlari (eglence_cek.py). Ayni alanlari tasiyorlar ama menuleri
    # yok; mekan_kaydi zaten menusuz kayda tolerant. Dosya yoksa sessizce
    # atlanir -- eglence cekimi yapilmamis kurulumda boru hatti calismaya devam
    # etsin diye.
    if os.path.exists("turkiye_eglence.csv"):
        eglence = list(csv.DictReader(open("turkiye_eglence.csv", encoding="utf-8-sig")))
        varolan = {m["osm_id"] for m in mekanlar}
        yeni_kayit = [e for e in eglence if e["osm_id"] not in varolan]
        mekanlar.extend(yeni_kayit)
        print("eglence: %d kayit eklendi (%d tekrar atlandi)"
              % (len(yeni_kayit), len(eglence) - len(yeni_kayit)))

    # Ikinci kaynak: PDF metni, sayfa metni ve gorsel OCR ile toplananlar.
    # Ayni mekana iki kaynaktan kalem gelirse ikisi de kalir; tekrar eden
    # (ad, fiyat) cifti asagida tekilleniyor.
    once = sum(len(v) for v in menu.values())
    for anahtar, kalemler in ek_menuler_oku(mekanlar).items():
        menu[anahtar].extend(kalemler)
    for anahtar, kalemler in menu.items():
        gorulen, tekil = {}, []
        for k in kalemler:
            imza = (k["a"], k["f"])
            if imza not in gorulen:
                gorulen[imza] = k
                tekil.append(k)
            else:
                # Ayni kalem iki kaynakta: TAZE tarih kazanir. Kalemi ikinci
                # kez eklemiyoruz ama yasini gunceliyoruz -- ayni fiyat daha
                # yeni bir taramada da gorulduyse, o fiyat o gun de gecerliydi.
                onceki = gorulen[imza]
                if k["t"] > onceki["t"]:
                    onceki["t"] = k["t"]
        menu[anahtar] = tekil
    print("menu kalemi: %d -> %d (ek kaynaklar dahil, tekillenmis)"
          % (once, sum(len(v) for v in menu.values())))

    # --- Zincir menusunun subeye uygulanmasi ---------------------------
    # Menu anahtari (il, mekan adi). Yani bir sube, KENDI sitesini
    # bildirmemis olsa bile ayni ildeki ayni adli mekanin menusunu aliyor.
    # Kural bugune kadar hic yazilmamisti; olculdu:
    #
    #   menu alan mekan            401
    #     kendi sitesini bildiren  184
    #     ADINDAN dolayi alan      217   (%54)
    #
    # Daha siki bir kural denendi ve BIRAKILDI: "gruptaki butun bildirimler
    # tek alan adinda uzlassin". Istanbul'daki 52 Kahve Dunyasi subesini
    # dusuruyordu, cunku Ataturk Kitapligi'ndaki sube kutuphanenin sitesiyle
    # etiketlenmis. Gercek bir zinciri, tek bir OSM etiketi yuzunden
    # elemek olurdu; yayilmanin bugun urettigi yanlis eslesme olculemedi
    # (yayilan adlarin hepsi gercek zincir: Domino's, Kahve Dunyasi,
    # Papa John's, Cajun Corner, Pizzabulls...).
    #
    # O yuzden davranis degismedi ama GORUNUR oldu: sayi her calistirmada
    # basiliyor. Adindan menu alan mekan orani firlarsa, kaziyici jenerik
    # bir ada takilmis demektir.
    ad_menusu = kendi_sitesi = 0
    for m in mekanlar:
        if _menu_anahtari(m["il"], m["ad"]) not in menu:
            continue
        if m.get("website") and not platform_mu(m["website"]):
            kendi_sitesi += 1
        else:
            ad_menusu += 1

    # Site taramasindan gelen sosyal baglar. SAYI BASILIYOR: dosya yoksa
    # ya da hicbir bag eslesmediyse sessizce sifir donerdi ve "toplandi"
    # sanilirdi. Sifir da bir olcumdur, ama gorunur olmali.
    site_sosyal = site_sosyal_oku(mekanlar)
    print("site sosyal: %d mekan, %d hesap (%s)"
          % (len(site_sosyal), sum(len(v) for v in site_sosyal.values()),
             SITE_SOSYAL if os.path.exists(SITE_SOSYAL) else SITE_SOSYAL + " yok"))

    iller = defaultdict(list)
    for m in mekanlar:
        iller[m["il"]].append(mekan_kaydi(m, menu, site_sosyal))

    # Kopya kayitlar il icinde birlestiriliyor: ayni isletme iki il dosyasinda
    # olamaz, il disina bakmanin anlami yok ve karsilastirma karesel.
    kopya = 0
    for il in iller:
        iller[il], n = kopyalari_birlestir(iller[il])
        kopya += n
    if kopya:
        print("ayni mekanin ikinci kaydi (ad ayni, <=%d m): %d kayit birlestirildi"
              % (KOPYA_METRE, kopya))

    os.makedirs("app/veri", exist_ok=True)
    dizin = []
    for il, kayitlar in iller.items():
        kod = IL_KODU.get(il)
        if not kod:
            print(f"  UYARI: {il} icin il kodu yok, atlandi")
            continue
        kayitlar.sort(key=lambda r: r["ad"].casefold())
        yol = f"app/veri/{kod}.json"
        # Bicim veri_bicim.py'de: yogun alanlar sutunlu, seyrek alanlar
        # indeksli. Olculdu (Istanbul): ham 1733 -> 1325 KB, gzip 396 -> 322.
        # Kodlayici bilinmeyen bir alan gorurse HATA veriyor -- yeni bir alan
        # eklendiginde sessizce kaybolmasin diye.
        veri_bicim.yaz(yol, IL_ADI.get(il, il), kayitlar)
        # Konumdan il bulmak icin merkez. Ortalama degil medyan: tek bir
        # yanlis etiketlenmis mekan merkezi denize kaydirmasin.
        enler = sorted(r["lat"] for r in kayitlar)
        boylar = sorted(r["lon"] for r in kayitlar)
        orta = len(kayitlar) // 2
        dizin.append({"kod": kod, "ad": IL_ADI.get(il, il), "n": len(kayitlar),
                      "fiyatli": sum(1 for r in kayitlar if "menu" in r),
                      "kb": round(os.path.getsize(yol) / 1024),
                      "lat": round(enler[orta], 4), "lon": round(boylar[orta], 4)})

    dizin.sort(key=lambda d: -d["n"])
    with open("app/veri/index.json", "w", encoding="utf-8") as f:
        json.dump({"varsayilan": "06", "iller": dizin}, f, ensure_ascii=False)

    if ELENEN:
        print()
        print("menusu tumden elenen mekan: %d" % len(ELENEN))
        for ad, tur, sebep in ELENEN[:12]:
            print("  %-30s %-12s %s" % (ad[:30], tur, sebep))
        if len(ELENEN) > 12:
            print("  ... %d tane daha" % (len(ELENEN) - 12))

    if PLATFORM_ELENEN:
        print("platform profili (kendi sitesi degil), menusu alinmadi: %d mekan"
              % len(PLATFORM_ELENEN))
        for il, ad in sorted(PLATFORM_ELENEN)[:6]:
            print("  %-12s %s" % (il, ad))

    print("zincir menusu: %d mekan kendi sitesinden, %d mekan AD eslesmesinden"
          % (kendi_sitesi, ad_menusu))

    toplam = sum(d["n"] for d in dizin)
    assert len(dizin) == 81, f"81 il bekleniyordu, {len(dizin)} yazildi"
    assert toplam > 30000, f"mekan sayisi dusuk: {toplam}"
    print(f"il: {len(dizin)}  mekan: {toplam}")
    print(f"menusu olan mekan: {sum(d['fiyatli'] for d in dizin)}")
    print(f"kalan menu kalemi: {sum(len(v) for v in menu.values())} "
          f"(sinirlar {ALT_SINIR}-{UST_SINIR} TL)")
    print("\nen buyuk 6 dosya:")
    for d in sorted(dizin, key=lambda d: -d["kb"])[:6]:
        print(f"  {d['ad']:<12}{d['n']:>7} mekan  {d['kb']:>5} KB")


def kendini_kontrol_et():
    """python app_veri.py test — kategori dokumunun fiyat uydurmadigini dogrular."""
    kalemler = [{"a": "Turk Kahvesi", "f": 90.0}, {"a": "Turk kahvesi (duble)", "f": 120.0},
                {"a": "Adana Kebap", "f": 700.0}, {"a": "Ayran", "f": 60.0},
                {"a": "Guatemala Filtre Kahve 250g", "f": 350.0}]
    d = kategori_dokumu(kalemler)
    gercek = {k["f"] for k in kalemler}
    for kat, o in d.items():
        for alan in ("med", "min", "max"):
            assert o[alan] in gercek, "uydurma fiyat: %s.%s=%s" % (kat, alan, o[alan])
    # cift sayida kalemde ortalama DEGIL, gozlenen alt medyan gelmeli
    assert d["Türk kahvesi"]["med"] == 90.0, d["Türk kahvesi"]
    assert d["Türk kahvesi"]["n"] == 2
    # 250g paket porsiyon degil: hic kategoriye girmemeli
    assert "Filtre kahve" not in d, d
    assert d["Kebap"]["med"] == 700.0 and d["Ayran"]["med"] == 60.0

    # --- semt adi (ilce / mahalle) ---
    # BUYUK/KUCUK HARF: 63 ilce degeri yalniz bu yuzden ikiye boluyordu.
    # "istanbul".title() Python'da "Istanbul" verir, "İstanbul" degil.
    assert semt_adi("merkez") == "Merkez", semt_adi("merkez")
    assert semt_adi("istanbul") == "İstanbul", semt_adi("istanbul")
    assert semt_adi("çankaya") == "Çankaya"
    assert semt_adi("şişli") == "Şişli"
    assert semt_adi("ıspartakule") == "Ispartakule"
    # SONEK ATILIYOR: ayni mahalle 211 kez farkli yazimla duruyordu.
    for v in ("Cumhuriyet", "Cumhuriyet Mah.", "Cumhuriyet Mahallesi",
              "cumhuriyet mah", "Cumhuriyet Mahalle"):
        assert semt_adi(v, True) == "Cumhuriyet", (v, semt_adi(v, True))
    # SONEK EKLENMIYOR: 611 degerde zaten yok, uydurmak olurdu.
    assert semt_adi("Suadiye", True) == "Suadiye"
    # BIRLESEN NOKTA (U+0307): "İ".lower() tek harf degil ve NFC geri
    # birlestirmiyor.
    assert semt_adi("Pi\u0307ri\u0307çelebi\u0307 Mahallesi", True) == "Piriçelebi", \
        semt_adi("Pi\u0307ri\u0307çelebi\u0307 Mahallesi", True)
    # ADRESIN TAMAMI KACMIS deger ELENMELI (veride gercekten var).
    assert semt_adi("Büyükkumla, ARMUTLU YOLU ÜZERİ NO:220 A, 16600 Gemlik/Bursa",
                    True) is None
    assert semt_adi("Orhaniye Mahallesi/Marmatris") is None
    assert semt_adi("") is None and semt_adi(None) is None
    # Tek harf bir yer adi degil.
    assert semt_adi("A") is None
    # Rakamla BASLAYAN gercek mahalle adlari KALMALI ("17 Eylül").
    assert semt_adi("17 Eylül Mahallesi", True) == "17 Eylül"

    # SOSYAL: alt alan adi gecer, alan adinin KENDISI tam kalir.
    # "tr-tr.facebook.com" Turkiye'deki isletmelerin en sik kullandigi
    # bicim ve eski desen onu REDDEDIYORDU (alt alan adlari tek tek
    # yaziliydi).
    for alan, url, bekle in (
            ("facebook", "https://tr-tr.facebook.com/xkafe", "xkafe"),
            ("facebook", "https://m.facebook.com/xkafe", "xkafe"),
            ("x",        "https://mobile.twitter.com/xk", "xk"),
            ("youtube",  "https://m.youtube.com/@xk", "xk"),
            # Platform karismiyor: facebook adresi bir instagram
            # kullanicisi degil.
            ("insta",    "https://facebook.com/xkafe", None),
            # Alan adi TAM eslesiyor: sahte alt alan gecmiyor.
            ("insta",    "https://instagram.com.saldirgan.net/x", None),
            # Kanal kimligi kullanici adi degil: uydurmaktansa bos birak.
            ("youtube",  "https://www.youtube.com/channel/UC123", None)):
        assert sosyal_adi(alan, url) == bekle, (alan, url, sosyal_adi(alan, url))

    # SITE TARAMASINDAN gelen sosyal baglar: mekana baglaniyor mu,
    # cozulemeyen bag dusuyor mu, OSM etiketi korunuyor mu.
    import tempfile
    _mekanlar = [{"il": "34", "ad": "X Kafe", "website": "https://xkafe.com"},
                 {"il": "34", "ad": "Y Kafe", "website": "https://ykafe.com"}]
    _yol = tempfile.mktemp(suffix=".csv")
    with open(_yol, "w", encoding="utf-8", newline="") as _f:
        _y = csv.writer(_f)
        _y.writerow(["mekan", "il", "website", "alan", "url"])
        _y.writerow(["X Kafe", "34", "https://xkafe.com", "instagram.com",
                     "https://www.instagram.com/xkafe/"])
        _y.writerow(["X Kafe", "34", "https://xkafe.com", "facebook.com",
                     "https://tr-tr.facebook.com/xkafe"])
        # Gonderi adresi HESAP DEGIL: dusmeli.
        _y.writerow(["Y Kafe", "34", "https://ykafe.com", "instagram.com",
                     "https://www.instagram.com/p/ABC/"])
    try:
        _b = site_sosyal_oku(_mekanlar, _yol)
        assert _b.get(("34", "x kafe")) == {"insta": "xkafe", "facebook": "xkafe"}, _b
        assert ("34", "y kafe") not in _b, "gonderi adresi hesap sanildi"
        # CELISKIDE OSM KAZANIR: elle yazilmis etiket, kaziyicinin
        # buldugu bagdan once gelir.
        _m = dict.fromkeys(
            ("mutfak", "telefon", "saatler", "bahce", "wifi", "adres",
             "ilce", "mahalle", "harita"), "")
        _m.update({"il": "34", "ad": "X Kafe", "website": "https://xkafe.com",
                   "tur": "cafe", "instagram": "https://instagram.com/osmdan",
                   "lat": "41.0", "lon": "29.0", "osm_id": "node/1"})
        _k = mekan_kaydi(_m, {}, _b)
        assert _k.get("insta") == "osmdan", _k.get("insta")
        assert _k.get("facebook") == "xkafe", _k.get("facebook")
    finally:
        os.remove(_yol)

    # Fiyatin yasi: kolonsuz eski satir tabana duser, kolonlu satir kendi
    # tarihini tasir. Tarih uydurulmuyor -- bilinmeyen icin bildigimiz UST
    # SINIR yaziliyor.
    assert _tarih({"tarih": "2026-03-14"}) == "2026-03-14"
    assert _tarih({"tarih": "2026-03-14T09:22:00Z"}) == "2026-03-14"
    assert _tarih({}) == TARIHSIZ_TABAN
    assert _tarih({"tarih": ""}) == TARIHSIZ_TABAN
    assert _tarih({"tarih": "bozuk"}) == TARIHSIZ_TABAN

    # Arayuz metni kalem adi degildir; gercek ad bozulmadan kalir.
    for a in ("Normal fiyat", "Regular price", "FİYATI", "Ürün",
              "55k kişi favoriledi!", "Tüm Fırsatlar"):
        assert kalem_atilir(a), a
    for a in ("Fiyatlı Kahvaltı", "Adana Kebap", "Tüm Kahveler Filtre Seti"):
        assert not kalem_atilir(a), a

    # Listenin menu OLDUGU da dogrulaniyor.
    assert menu_degil_mi([{"a": "Roxy AA Alkaline Pil", "f": 160.0},
                          {"a": "Raisa Drop Earrings", "f": 190.0}])
    assert menu_degil_mi([{"a": "Hafta İçi", "f": 600.0}])
    assert not menu_degil_mi([{"a": "Roxy AA Alkaline Pil", "f": 160.0},
                              {"a": "Adana Kebap", "f": 700.0}])
    assert not menu_degil_mi([{"a": "1 KG KIYMALI KOL BÖREĞİ", "f": 900.0}])
    assert menu_degil_mi([]) is None

    # Kopya kayit birlestirme: bilgi kaybetmeden, dogru kaydi birakarak.
    a = {"id": "node/1", "ad": "X", "lat": 39.9, "lon": 32.85, "tel": "111"}
    b = {"id": "way/2",  "ad": "X", "lat": 39.9, "lon": 32.850001, "saat": "24/7"}
    kalan, n = kopyalari_birlestir([a, b])
    assert n == 1 and len(kalan) == 1, (n, kalan)
    assert kalan[0]["tel"] == "111" and kalan[0]["saat"] == "24/7", kalan[0]
    # Esitlikte NOKTA kalir: alan kaydinin koordinati bina merkezi.
    assert kalan[0]["id"] == "node/1", kalan[0]["id"]

    # Bilgisi cok olan kalir, kimlik tipi ne olursa olsun.
    a = {"id": "node/1", "ad": "X", "lat": 39.9, "lon": 32.85}
    b = {"id": "way/2",  "ad": "X", "lat": 39.9, "lon": 32.850001,
         "tel": "111", "saat": "24/7"}
    kalan, _ = kopyalari_birlestir([a, b])
    assert kalan[0]["id"] == "way/2", kalan[0]["id"]

    # Uzaktaki ayni adli mekan AYRI kalir: zincir subesi kopya degildir.
    uzak = [{"id": "node/1", "ad": "X", "lat": 39.9, "lon": 32.85},
            {"id": "node/2", "ad": "X", "lat": 39.91, "lon": 32.85}]   # ~1,1 km
    kalan, n = kopyalari_birlestir(uzak)
    assert n == 0 and len(kalan) == 2, (n, kalan)

    # Farkli adlar birlesmez, ayni noktada olsalar bile.
    ayri = [{"id": "node/1", "ad": "X", "lat": 39.9, "lon": 32.85},
            {"id": "node/2", "ad": "Y", "lat": 39.9, "lon": 32.85}]
    assert kopyalari_birlestir(ayri)[1] == 0

    # Turkce harf farki ayni mekani ayirmamali: gercek veride 14 cift
    # boyle kaciyordu.
    for a1, a2 in (("Balıkçı Sabahattin", "Balikci Sabahattin"),
                   ("KISMETİM", "Kısmetim"),
                   ("Kardeş büfe", "Kardes bufe")):
        c = [{"id": "node/1", "ad": a1, "lat": 39.9, "lon": 32.85},
             {"id": "node/2", "ad": a2, "lat": 39.9, "lon": 32.85001}]
        assert kopyalari_birlestir(c)[1] == 1, (a1, a2)

    # Sonuc calistirma sirasindan bagimsiz olmali.
    karisik = list(reversed(uzak))
    assert sorted(k["id"] for k in kopyalari_birlestir(karisik)[0]) == ["node/1", "node/2"]

    # Kalem adi: HTML varligi cozulmeli, bosluk sadelesmeli.
    assert kalem_adi("Sevgililer Günü 6&#8217;lı Macaron") == "Sevgililer Günü 6’lı Macaron"
    assert kalem_adi("A&#038;B") == "A&B"
    assert kalem_adi("  iki   bosluk  ") == "iki bosluk"
    assert kalem_adi("= Kola =") == "Kola"
    assert kalem_adi(None) == ""

    # Instagram: OSM'de dort ayri bicimde yaziliyor, hepsi tek bicime
    # inmeli. Baska bir alan adi reddedilmeli -- "facebook.com/x"
    # kirpilinca "facebook.com" diye gecerli bir kullanici adi gorunuyordu.
    for ham, bekle in (
            ("ortakoyadana", "ortakoyadana"),
            ("https://www.instagram.com/guneyyildizi/", "guneyyildizi"),
            ("instagram.com/mandalinsound", "mandalinsound"),
            ("@mangocoffee.tr", "mangocoffee.tr"),
            ("https://instagram.com/abc?igsh=1", "abc"),
            ("https://m.instagram.com/x/reels", None),
            ("http://facebook.com/x", None),
            ("instagram.com/", None),
            ("a b c", None), ("", None), (None, None)):
        assert instagram_adi(ham) == bekle, (ham, instagram_adi(ham), bekle)

    # Diger platformlar. Her biri KENDI alan adini kirpiyor; baska bir
    # platformun adresi geldiyse deger tamamen reddediliyor -- instagram
    # icin olculmus gercek hata buydu ("facebook.com/x" -> "facebook.com").
    for alan, ham, bekle in (
            ("facebook", "https://facebook.com/kafemiz",      "kafemiz"),
            ("facebook", "fb.com/kafemiz",                    "kafemiz"),
            ("facebook", "kafemiz",                           "kafemiz"),
            ("facebook", "https://instagram.com/kafemiz",         None),
            ("x",        "https://twitter.com/kafe",           "kafe"),
            ("x",        "https://x.com/kafe",                 "kafe"),
            ("x",        "@kafe",                              "kafe"),
            ("x",        "cok_uzun_bir_kullanici_adi",            None),  # X 15 hane
            ("tiktok",   "https://tiktok.com/@kafe.tr",     "kafe.tr"),
            ("tiktok",   "@kafe.tr",                        "kafe.tr"),
            ("youtube",  "https://youtube.com/@kanal",        "kanal"),
            # Kanal adresinden kullanici adi CIKARILAMAZ; yanlis bir adres
            # uretmektense hic gostermemek dogru.
            ("youtube",  "https://youtube.com/channel/UCabc",     None),
            ("youtube",  "https://youtube.com/c/kanal",           None),
            ("insta",    "https://instagram.com/abc",           "abc"),
            ("facebook", "", None), ("x", None, None),
            ("bilinmeyen", "abc", None)):
        assert sosyal_adi(alan, ham) == bekle, (alan, ham, sosyal_adi(alan, ham), bekle)

    # Platform profili isletmenin kendi sitesi degildir.
    for u in ("https://www.shopier.com/x", "https://trendyol.com",
              "instagram.com/xkafe", "https://m.facebook.com/y",
              "https://www.instagram.com/", "https://tripadvisor.com.tr/a"):
        assert platform_mu(u), u
    # ...ama isletmenin KENDI alan adindaki QR menusu platform degildir.
    for u in ("https://qrmenu.actdurum.com", "https://dominos.com.tr",
              "https://kahvedunyasi.com", "", None,
              "https://instagramcafe.com.tr"):
        assert not platform_mu(u), u

    # Site eslestirme: OSM etiketi yollu, tarama kaydi kok adres olabiliyor
    assert _site_anahtari("https://www.A.com/menu/") == "a.com/menu"
    assert _alan_adi("https://www.A.com/menu/") == "a.com"
    assert _alan_adi("http://a.com") == _alan_adi("https://www.a.com/x/y")

    print("kontrol gecti: %d kategori, uydurma fiyat yok" % len(d))
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.exit(0 if kendini_kontrol_et() else 1)
    main()
