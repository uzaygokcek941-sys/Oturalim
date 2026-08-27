# -*- coding: utf-8 -*-
"""Sayfalari GERCEK tarayicida acan kontroller.

    python test_sayfa.py            # hepsi
    python test_sayfa.py test       # ayni sey (test.py boyle cagiriyor)

NEDEN AYRI BIR KOSUM TAKIMI: test_tarayici.mjs betikleri bir vm kutusunda
calistiriyor, yani DOM yok, yukleme sirasi yok, CDN yok. Gercek bir hatayi
o yuzden goremedi:

  Leaflet CDN'den gelmediginde ("L is not defined") kesfet ekraninin
  TAMAMI oluyordu -- sifir kart, sayac "…"da donmus, bos sayfa. Oysa
  liste, filtreler ve butce kaydiricisi haritaya hic ihtiyac duymuyor.

GIRIS YAPILMIS HAL DE SINANIYOR. Dis baglantilar kesildigi icin
supabase-js hicbir zaman gelmiyordu; yan etkisi, girisli sayfalarin
hicbirinin gercek tarayicida HIC calistirilmamis olmasiydi. Artik
supabase-js istegi yerel bir taklit modulle karsilaniyor
(test_sahte_supabase.js) ve hesabim.html'in dort sekmesi, yonetim.html'in
onay dugmesi, isletme.html'in fis ve sayac katmanlari cizilerek olculuyor.
Yetki taklit EDILMIYOR: RLS gercek Postgres'te sinaniyor
(veritabani/kos.sh).

DIS BAGLANTILAR BILEREK ENGELLENIYOR. Iki sebep: (1) kontrol ag'a
bagimli olmasin, aksi halde CDN yavaslayinca kirmizi yanar; (2) asil
sinanmak istenen sey ZOR hal -- CDN'siz kullanici. Kurumsal ag, okul agi
ve ulke capinda engel gercek; uygulama o kosulda da calismali.

Tarayici yoksa kontrol ATLANIR, gectigi soylenmez.
"""
import base64
import io
import os
import re
import subprocess
import struct
import sys
import time

TABAN = "http://localhost:8199"
KOK = os.path.dirname(os.path.abspath(__file__))

# Leaflet taklidi: gercek Leaflet'e ulasamiyoruz ama kodun NORMAL yolu
# izledigini dogrulamamiz gerekiyor -- haritaKur erken donmemeli,
# isaretciler cizilmeli. Taklit yalniz kullanilan arayuzu sunuyor.
LEAFLET_TAKLIT = """
window.__cagri = [];
const kat = { addTo(){ window.__cagri.push("addTo"); return this; },
              clearLayers(){ window.__cagri.push("clearLayers"); },
              removeLayer(){} };
const isaretci = { addTo(){ return this; }, bindPopup(){ return this; },
                   on(){ return this; }, openPopup(){} };
window.L = {
  map(){ window.__cagri.push("map");
    const h = { setView(){ return h; }, removeLayer(){},
                fitBounds(){ window.__cagri.push("fitBounds"); },
                getZoom: () => 12, invalidateSize(){} };
    return h; },
  tileLayer(){ window.__cagri.push("tileLayer"); return kat; },
  layerGroup(){ window.__cagri.push("layerGroup"); return kat; },
  circleMarker(){ window.__cagri.push("circleMarker"); return isaretci; }
};
"""

# supabase-js yerine donen yerel taklit modul (test_sahte_supabase.js).
SAHTE_MODUL = io.open(os.path.join(KOK, "test_sahte_supabase.js"),
                      encoding="utf-8").read()

# GPS ve cihaz bilgisi tasiyan GERCEK bir EXIF blogu (APP1).
#
# URETILIYOR, ELLE YAZILMIYOR. Onceden sabit bir base64 dizgisiydi ve
# icinde cihaz adi GOMULUYDU. Marka adi degisince asagidaki beklenti
# guncellendi ama base64 GUNCELLENEMEDI -- ikili bir sabitin icindeki
# metni hicbir arama gormuyor. Sonuc: kontrol "girdi dosyasinda EXIF
# yok" diye patladi. Sabit yerine uretici koyunca isim TEK yerde kaldi.
EXIF_CIHAZ = "CebimdeTest"


def _exif_kur(cihaz=EXIF_CIHAZ):
    """Gecerli bir APP1 blogu: Make, Model ve GPS IFD isaretcisi.

    Hazir bir fotograf koymak depoya ikili dosya sokardi; ustelik
    fotografin EXIF tasidigini de ayrica dogrulamak gerekirdi."""
    ad = cihaz.encode("ascii") + b"\x00"
    tiff = b"II" + struct.pack("<HI", 0x2A, 8)
    veri_ofs = 8 + 2 + 3 * 12 + 4           # IFD0'dan sonraki ilk bos bayt
    gps_ofs = veri_ofs + len(ad)
    girisler = [(0x010F, 2, len(ad), veri_ofs),    # Make
                (0x0110, 2, len(ad), veri_ofs),    # Model
                (0x8825, 4, 1, gps_ofs)]           # GPS IFD isaretcisi
    ifd0 = struct.pack("<H", len(girisler))
    for t, tur, n, v in girisler:
        ifd0 += struct.pack("<HHII", t, tur, n, v)
    ifd0 += struct.pack("<I", 0)
    gps = [(0x0001, 2, 2, int.from_bytes(b"N\x00\x00\x00", "little")),
           (0x0003, 2, 2, int.from_bytes(b"E\x00\x00\x00", "little"))]
    gpsb = struct.pack("<H", len(gps))
    for t, tur, n, v in gps:
        gpsb += struct.pack("<HHII", t, tur, n, v)
    gpsb += struct.pack("<I", 0)
    govde = b"Exif\x00\x00" + tiff + ifd0 + ad + gpsb
    return b"\xff\xe1" + struct.pack(">H", len(govde) + 2) + govde


EXIF_BLOK = _exif_kur()

# Girisli halin verisi. Degerler BILEREK ayirt edilebilir: ekranda
# "Ornek Kafe" gormek, listenin gercekten bu satirdan cizildigini
# gosteriyor -- sabit bir baslik gormek gostermezdi.
GIRIS_TAKLIT = """
window.__SAHTE_VERI = {
  oturum: { user: { id: "kul-1", email: "ben@ornek.test" } },
  tablolar: {
    profiller:  [{ id: "kul-1", ad: "Deneme Kisi", yonetici: true,
                   kullanici_adi: "deneme_kisi", dogum_yili: 1998,
                   meslek: "Öğretmen", kisilik: "Sessiz köşe severim",
                   avatar: null, herkese_acik: true }],
    mekan_fotolari: [{ id: 1, kullanici: "kul-1", mekan_id: "node/1", il: "34",
                   mekan_ad: "Foto Kafe", yol: "kul-1/a.jpg", adres: null,
                   aciklama: "Bahçe", kaynak: "kullanici", durum: "bekliyor",
                   olusturuldu: "2026-08-20T10:00:00Z" }],
    menu_katkilari: [{ id: 1, kullanici: "kul-1", mekan_id: "node/1", il: "34",
                   mekan_ad: "Menu Kafe", urun: "Latte", fiyat: 95, foto: null,
                   durum: "bekliyor", olusturuldu: "2026-08-22T12:00:00Z" }],
    yorumlar:   [{ id: 1, kullanici: "kul-1", mekan_id: "node/1", il: "34",
                   mekan_ad: "Yorum Kafe", puan: 4, metin: "Sessiz ve ucuz",
                   durum: "bekliyor", olusturuldu: "2026-08-23T12:00:00Z" }],
    favoriler:  [{ mekan_id: "node/1", il: "34", mekan_ad: "Favori Kafe",
                   eklendi: "2026-08-01T10:00:00Z" }],
    paylasimlar:[{ id: 1, kullanici: "kul-1", mekan_id: "node/1",
                   mekan_ad: "Ornek Kafe", il: "34", tutar: 850, kisi: 3,
                   tarih: "2026-08-20", aciklama: "ucuzdu",
                   durum: "bekliyor", olusturuldu: "2026-08-20T12:00:00Z" }],
    katkilar:   [{ id: 1, kullanici: "kul-1", mekan_id: "node/1", il: "34",
                   mekan_ad: "Katki Kafe", alan: "tel", deger: "0312 000 00 00",
                   durum: "bekliyor", olusturuldu: "2026-08-21T12:00:00Z" }],
    sahiplik:   [{ id: 1, kullanici: "kul-1", mekan_id: "node/1", il: "34",
                   mekan_ad: "Sahip Kafe", dogrulandi: "2026-08-22T12:00:00Z",
                   durum: "aktif", iptal_notu: null }]
  },
  rpc: {
    mekan_sayaci:    () => ({ data: [{ bugun: 2, son30: 47, toplam: 90,
                                       ilk_gun: "2026-06-01" }], error: null }),
    mekan_goruldu:   () => ({ data: null, error: null }),
    mekan_fis_ozeti: () => ({ data: [{ fis: 5, kisi: 3, medyan: 300 }], error: null }),
    /* Civar ve akran: sayilar BILEREK ayirt edilebilir (kesfet ve isletme
       ekranlarindaki oteki sayilara benzemiyor), boylece kutunun gercekten
       bu cagridan cizildigi gorulebiliyor. */
    civar_fis_ozeti: () => ({ data: [{ fis: 7, kisi: 4, mekan: 3, medyan: 265 }],
                              error: null }),
    butce_akranlari: () => ({ data: [{ akran: 37, fis: 80, mekan: 12 }], error: null }),
    profil_getir: () => ({ data: [{ kullanici_adi: "deneme_kisi", ad: "Deneme Kisi",
      dogum_yili: 1998, meslek: "Öğretmen", kisilik: "Sessiz köşe severim",
      avatar: null, katildi: "2026-03-01T10:00:00Z" }], error: null }),
    profil_yorumlari: () => ({ data: [
      { id: 1, mekan_id: "node/1", mekan_ad: "Yorum Kafe", il: "34", puan: 4,
        metin: "Sessiz ve ucuz", olusturuldu: "2026-08-01T10:00:00Z" }], error: null }),
    /* Uc yorum: ortalama ancak YORUM_ESIK'ten (3) sonra gosteriliyor,
       yani esigin gectigi hal de sinaniyor. Ikisi ADSIZ: profilini
       kapatanin yorumu gorunur, adi gorunmez. */
    mekan_yorumlari: () => ({ data: [
      { id: 1, puan: 5, metin: "Sessiz ve ucuz", olusturuldu: "2026-08-01T10:00:00Z",
        yazar_adi: "deneme_kisi", yazar_ad: "Deneme Kisi", yazar_avatar: null,
        yazar_dogum: 1998, yazar_meslek: "Öğretmen" },
      { id: 2, puan: 4, metin: "Fena degil", olusturuldu: "2026-07-01T10:00:00Z",
        yazar_adi: null, yazar_ad: null, yazar_avatar: null,
        yazar_dogum: null, yazar_meslek: null },
      { id: 3, puan: 3, metin: null, olusturuldu: "2026-06-01T10:00:00Z",
        yazar_adi: null, yazar_ad: null, yazar_avatar: null,
        yazar_dogum: null, yazar_meslek: null }], error: null }),
    mekan_puani: () => ({ data: [{ adet: 3, ortalama: 4 }], error: null }),
    /* Uc kaynak birden: sahip, kullanici ve commons. Ucuncusu ATIFLI
       olmali, dorduncusu ATIFSIZ -- atifsiz olan CIZILMEMELI. */
    mekan_fotograflari: () => ({ data: [
      { id: 1, yol: "kul-1/a.jpg", adres: null, aciklama: "Bahçe",
        kaynak: "sahip", yazar: null, lisans: null, kaynak_bag: null,
        olusturuldu: "2026-08-20T10:00:00Z" },
      { id: 2, yol: "kul-1/b.jpg", adres: null, aciklama: "Salon",
        kaynak: "kullanici", yazar: null, lisans: null, kaynak_bag: null,
        olusturuldu: "2026-08-19T10:00:00Z" },
      { id: 3, yol: null, adres: "/og.png?commons=c", aciklama: null,
        kaynak: "commons", yazar: "Bir Fotografci", lisans: "CC BY-SA 4.0",
        kaynak_bag: "https://commons.wikimedia.org/wiki/File:C.jpg",
        olusturuldu: "2026-08-18T10:00:00Z" },
      { id: 4, yol: null, adres: "/og.png?commons=d", aciklama: null,
        kaynak: "commons", yazar: null, lisans: null, kaynak_bag: null,
        olusturuldu: "2026-08-17T10:00:00Z" }], error: null }),
    /* Biri kalem, biri YALNIZ fotograf: ikisi de cizilmeli. */
    mekan_menu_katkilari: () => ({ data: [
      /* TARIH HESAPLANIYOR, sabit yazilmiyor: kalem duzeyinde tarih
         (urun tarifi md.4) "3 gun once" diye GORECELI ciziliyor ve sabit
         bir damga kontrolu yarin curuturdu. Tam 3 gun geri: zamanYasi
         asagi yuvarliyor, cizim aninda gecen milisaniyeler sonucu
         buyutur, kucultmez. */
      { id: 1, urun: "Latte", fiyat: 95, foto: null,
        olusturuldu: new Date(Date.now() - 3 * 86400000).toISOString() },
      { id: 2, urun: null, fiyat: null, foto: "kul-1/1.jpg",
        olusturuldu: "2026-08-21T12:00:00Z" }], error: null }),
    /* TOPLULUK AKISI. Uc satir, uc ayri hal:
         1) yorum + ACIK profil   -> ad ve avatar gorunuyor
         2) yorum + KAPALI profil -> yorum duruyor, ad "Bir kullanici"
         3) menu katkisi          -> ADSIZ (sunucu yazar sutunlarini
                                     bilerek null donduruyor)
       Fis ve fiyat oyu taklitte de YOK: sunucu onlari hic dondurmuyor
       ve arayuzun "gelirse ne yapacagi" diye bir hali olmamali. */
    topluluk_akisi: () => ({ data: [
      { tur: "yorum", id: 1, mekan_id: "node/1", mekan_ad: "Akis Kafe",
        il: "34", puan: 5, metin: "Akista gorunen yorum",
        urun: null, fiyat: null, foto: null,
        olusturuldu: "2026-08-24T10:00:00Z",
        yazar_adi: "deneme_kisi", yazar_ad: "Deneme Kisi", yazar_avatar: null },
      { tur: "yorum", id: 2, mekan_id: "node/2", mekan_ad: "Gizli Yazar Kafe",
        il: "34", puan: 4, metin: "Adsiz gorunen yorum",
        urun: null, fiyat: null, foto: null,
        olusturuldu: "2026-08-23T10:00:00Z",
        yazar_adi: null, yazar_ad: null, yazar_avatar: null },
      { tur: "menu", id: 3, mekan_id: "node/3", mekan_ad: "Akis Menu",
        il: "34", puan: null, metin: null,
        urun: "Latte", fiyat: 145, foto: "kul-1/1.jpg",
        olusturuldu: "2026-08-22T10:00:00Z",
        yazar_adi: null, yazar_ad: null, yazar_avatar: null }], error: null }),
    /* FIYAT OYU OZETI. Onceden hic taklit edilmiyordu, yani guven
       rozetinin OY dali gercek tarayicida HIC cizilmemisti. Uc kisi ve
       son oy 2 gun once: esik gecildigi icin hem dagilim hem tarih
       geliyor -- rozet "3 kisi ... — 2 gun once" demeli. */
    /* Mekan ve FIYAT gercek olmali: oyKatmani ekranda YAZAN rakamin
       satirini ariyor (yemekFiyati). Bambi Cafe'nin hesaplanan ogun
       fiyati 243 TL; baska bir sayi yazarsak satir hic eslesmez ve
    kontrol "rozet cizilmedi" derdi -- kod dogru olsa bile. */
    fiyat_oy_ozeti: () => ({ data: [
      { mekan_id: "node/6324460285", fiyat: 243, gecerli: 3, degisti: 0,
        kisi: 3, son_gun: 2 },
      /* IKINCI SATIR TARIHSIZ. Sunucu esigin altinda son_gun
         dondurmuyor; istemci onu SIFIRA cevirirse rozet "bugün" der ve
         elimizde olmayan bir tazeligi iddia eder. Sabotajla dogrulandi:
         `+o.son_gun || 0` yazildiginda bu satir "bugün" cikiyor. */
      { mekan_id: "node/4914653325", fiyat: 243, gecerli: 3, degisti: 0,
        kisi: 3, son_gun: null }], error: null }),
    il_puanlari: () => ({ data: [], error: null }),
    /* Birakma SILMIYOR, durumu degistiriyor -- taklit de oyle davranmali,
       yoksa arayuz kontrolu gercekte olmayan bir davranisi dogrular. */
    sahipligi_birak: (p) => {
      const r = (window.__SAHTE_VERI.tablolar.sahiplik || [])
        .find(x => String(x.id) === String(p.p_id));
      if (r) r.durum = "birakildi";
      return { data: null, error: null };
    }
  }
};
"""

# (ad, adres, tiklanacak sekme, ekranda OLMALI, ekranda OLMAMALI)
#
# Beklenen metinler BILEREK ayirt edilebilir: ekranda "Ornek Kafe" gormek
# listenin gercekten o satirdan cizildigini gosteriyor, sabit bir baslik
# gormek gostermezdi.
#
# OLMAMALI listesinde iki sey var, ikisi de sessiz hata bicimi:
#   "Yükleniyor" -> liste hic gelmedi, kutu ilk halinde takili kaldi
#   "kul-1"      -> kullanici kimligi ekrana sizdi (sema.sql "Sutun yetkisi")
GIRISLI = [
  ("hesabim.html/favoriler",  "/hesabim.html", None,
   ["Favori Kafe", "Deneme Kisi"], ["Yükleniyor", "kul-1"]),
  ("hesabim.html/paylasimlar","/hesabim.html", '[data-bolum="paylasimlar"]',
   ["Ornek Kafe", "onay bekliyor"], ["Yükleniyor", "kul-1"]),
  # Katkilar sekmesinde IKI liste var (eksik bilgi + menu); ikisi de
  # cizilmeli. Ilk yazimda katkilariCiz #bolum-katkilar'a innerHTML
  # yaziyordu ve ikinciyi siliyordu.
  ("hesabim.html/katkilar",   "/hesabim.html", '[data-bolum="katkilar"]',
   ["Katki Kafe", "0312 000 00 00", "Menü katkılarım", "Menu Kafe", "Latte"],
   ["Yükleniyor", "kul-1"]),
  # Bu sekme artik liste CIZMIYOR: sahiplik yonetimi isletmem.html'de.
  # Ayni listeyi iki yerde cizmek "ayni kural tek yerde dursun"un
  # ihlaliydi. Sekme yine de duruyor ve bir SAYI + bir KAPI veriyor;
  # bos bir sekme kullaniciyi nereye gidecegini bilmeden birakirdi.
  ("hesabim.html/isletmeler", "/hesabim.html", '[data-bolum="isletmeler"]',
   # GORUNUR metin araniyor: 'isletmem.html' bir href ve inner_text'te
   # gecmiyor. (Ayni tuzak galeri atifinda ve odenen kutusunda da cikti.)
   ["doğrulanmış işletmen var", "İşletme paneline git"],
   ["Yükleniyor", "kul-1", "Sahipliği bırak"]),
  # Isletme paneli: sahibin panele bakma sebebi SAYILAR. Uc kaynaktan
  # uc sayi -- goruntulenme (47), yorum ortalamasi, fis medyani (300) --
  # ve duzeltme formu. Hepsi taklit veriden geliyor, sabit metin degil.
  ("isletmem.html", "/isletmem.html", None,
   ["Sahip Kafe", "47", "300", "Kaydet", "Sahipliği bırak"],
   ["Yükleniyor", "kul-1"]),
  ("hesabim.html/yorumlar",   "/hesabim.html", '[data-bolum="yorumlar"]',
   ["Yorum Kafe", "onay bekliyor"], ["Yükleniyor", "kul-1"]),
  # Profil alanlari MEVCUT degerlerle dolmali: bos bir form kaydetmek
  # kullanicinin yazdiklarini silerdi.
  ("hesabim.html/ayarlar",    "/hesabim.html", '[data-bolum="ayarlar"]',
   ["Kullanıcı adın", "Doğum yılın", "profil.html?k=deneme_kisi"],
   ["Yükleniyor", "kul-1"]),
  ("yonetim.html", "/yonetim.html", None,
   ["Ornek Kafe", "Katki Kafe", "Sahip Kafe"], ["Yükleniyor", "kul-1"]),
  ("isletme.html", "/isletme.html?il=34&id=node/8223784325", None,
   # Sayac cumlesi ve fis ozeti sunucudan gelen sayilarla kurulmali.
   ["47", "3 kişinin 5 fişinden"], ["kul-1"]),
  # Yorumlar: yazarli ve YAZARSIZ olan birlikte cizilmeli. Profilini
  # kapatanin yorumu GORUNUR, adi gorunmez -- yorum mekana ait bir bilgi.
  # YORUMLAR ARTIK SEKME ARDINDA. Sekme cubugu gelmeden once bu satir
  # dugmesiz kosuyordu; sekmelerden sonra yorumlar display:none oldu ve
  # kontrol "'4,0' ekranda yok" diye patladi -- yani sekmelerin icerigi
  # gizledigini ilk soyleyen sey bu kontrol oldu. Dugme tiklanarak
  # sekmenin icerigi GERCEKTEN aciyor oldugu da sinaniyor.
  ("isletme.html/yorumlar", "/isletme.html?il=34&id=node/8223784325",
   '.sekme-cubuk [data-sekme="yorum"]',
   ["Yorumlar", "Deneme Kisi", "28 · Öğretmen", "Sessiz ve ucuz",
    "Bir kullanıcı", "4,0"], ["kul-1"]),
  # KONUM SEKMESI. Adresi olan mekan yalniz %26,2; kalan 26.455 mekanda
  # haritadaki nokta "burasi nerede" sorusunun tek cevabi. Sinanan sey
  # metnin varligi degil, BAGIN KOORDINATA gitmesi: yol tarifi adla
  # aramaya duserse kullanici yanlis subeye gider.
  # SEMT: ilce ve mahalle CSV'de DOLUYDU ve uygulamaya hic ulasmiyordu.
  # Iki hal birden sinaniyor, cunku asil kazanc ikincisinde:
  #   adresi OLAN mekan  -> adresin yanina semt ekleniyor
  #   adresi OLMAYAN     -> semt, sayfadaki TEK yer adi
  # Olculdu: adresi olmayan 26.455 mekanin 883'u boyle.
  ("isletme.html/semt", "/isletme.html?il=34&id=node/9821259942", None,
   ["Şevki Bey Sokağı · Caferağa · Kadıköy · İstanbul"], ["kul-1"]),
  ("isletme.html/semt-adressiz", "/isletme.html?il=34&id=node/7591718367", None,
   ["Üniversite · Avcılar · İstanbul"], ["kul-1"]),
  ("isletme.html/konum", "/isletme.html?il=34&id=node/8223784325",
   '.sekme-cubuk [data-sekme="bilgi"]',
   ["Konum", "40.986810, 29.025530", "Yol tarifi", "Google'da ara",
    "OpenStreetMap", "yazarlarının telifinde"], ["kul-1"]),
  ("profil.html", "/profil.html?k=deneme_kisi", None,
   ["Deneme Kisi", "@deneme_kisi", "28 · Öğretmen", "Yorum Kafe"],
   ["Yükleniyor", "kul-1", "Profil bulunamadı"]),
  # Yonetim: yorum kuyrugu da cizilmeli.
  ("yonetim.html/yorumlar", "/yonetim.html", None,
   ["Yorumlar", "Yorum Kafe", "Sessiz ve ucuz"], ["kul-1"]),
  ("yonetim.html/menu", "/yonetim.html", None,
   ["Menü katkıları", "Menu Kafe", "Latte"], ["kul-1"]),
  ("yonetim.html/foto", "/yonetim.html", None,
   ["Mekan fotoğrafları", "Foto Kafe"], ["kul-1"]),
  # Galeri: atifli commons fotografi ATFIYLA cizilmeli, ATIFSIZ olan
  # HIC cizilmemeli -- atifsiz gostermek lisansi ihlal eder.
  # GALERI DE SEKME ARDINDA (Fotograflar). Sekme cubugu gelince galeri
  # ve fotograf ekleme formu display:none oldu ve bu satir dort ayri
  # eksikle patladi -- sekmelerin neyi gizledigini soyleyen ikinci
  # kontrol bu oldu.
  ("isletme.html/galeri", "/isletme.html?il=34&id=node/8223784325",
   '.sekme-cubuk [data-sekme="foto"]',
   # "İŞLETMEDEN" BUYUK harfle: rozetin CSS'inde text-transform:uppercase
   # var ve innerText donusmus metni veriyor. Kaynakta kucuk harfle
   # yaziyor -- kaynaga bakip burayi "duzeltmek" kontrolu bozar.
   # (Noktali I gelmesi ayrica lang="tr"nin dogru calistigini gosteriyor.)
   ["Bir Fotografci", "CC BY-SA 4.0", "İŞLETMEDEN", "Buranın fotoğrafı var mı"],
   ["kul-1"]),
  # KAPAK: maketteki ust fotograf. Sekmeye bagli DEGIL -- basligin
  # parcasi, yani sekme tiklamadan gorunmeli. Kapak seritteki ilk
  # UYGUN kareyi aliyor ve ATFI da tasiyor: fotograf buyudu diye
  # lisans satiri kaybolamaz. Taklit veride ilk kare "sahip"
  # kaynakli, o yuzden "işletmeden" bekleniyor.
  ("isletme.html/kapak", "/isletme.html?il=34&id=node/8223784325", None,
   ["işletmeden"], ["kul-1"]),
  # TOPLULUK AKISI. Uc sey birden olculuyor:
  #   - acik profilin ADI gorunuyor
  #   - KAPALI profilin yorumu duruyor ama adi "Bir kullanici"
  #   - menu katkisi kalemi ve fiyatiyla cikiyor, ADSIZ
  # "Yukleniyor" hala ekrandaysa akis hic cizilmemis demektir.
  # GUVEN ROZETININ OY DALI + "son dogrulanma" tarihi. Urun tarifinin
  # 5. maddesi rozetin yaninda tarih istiyor; oy tablosu bunun icin
  # dogru kaynak ve tarih artik sunucudan geliyor (fiyat_oy_ozeti.son_gun).
  ("isletme.html/oy-tarihi", "/isletme.html?il=34&id=node/6324460285", None,
   ["hâlâ böyle", "2 gün önce"], ["kul-1"]),
  # TARIHSIZ HAL: cumle tarihsiz de tam kalmali.
  #
  # ARANAN SEY ROZETIN KENDI BICIMI ("dedi — "), sayfada gecen herhangi
  # bir tarih kelimesi DEGIL. Ilk yazimda "bugün" diye bakiyordum ve
  # kontrol yanlis yerden patladi: goruntulenme sayaci da "· bugün 3"
  # yaziyor. Ayni tuzak bu depoda daha once de yasandi (href ile gorunen
  # metin, title ile gorunen etiket).
  ("isletme.html/oy-tarihsiz", "/isletme.html?il=34&id=node/4914653325", None,
   ["hâlâ böyle"], ["kul-1", "dedi — "]),
  ("topluluk.html", "/topluluk.html", None,
   ["Akis Kafe", "Deneme Kisi", "Akista gorunen yorum",
    "Gizli Yazar Kafe", "Bir kullanıcı", "Akis Menu", "Latte", "145"],
   ["Yükleniyor", "kul-1", "Henüz onaylanmış bir katkı yok"]),
  # Isletme sayfasi: kalem ve fotograf ayri ayri cizilmeli.
  # "3 gun once" KALEMIN KENDI tarihi: mekan tarihi degil. Kazinan menude
  # boyle bir tarih yok (291 mekanin 291'inde butun kalemler ayni gun
  # derlenmis); yalniz kullanici katkisinda var ve ekrana yeni geliyor.
  ("isletme.html/menu", "/isletme.html?il=34&id=node/8223784325", None,
   ["Kullanıcıların eklediği fiyatlar", "Latte", "3 gün önce",
    "Menüyü görüyor musun"],
   ["kul-1"]),
]

SAYFALAR = ["/index.html", "/kesfet.html", "/kesfet.html?il=34&tur=Kafe&butce=300",
            "/isletme.html?il=34&id=node/8223784325", "/isletme.html?il=34&id=yok",
            "/paylas.html", "/giris.html", "/hesabim.html", "/yonetim.html",
            "/hakkinda.html", "/gizlilik.html", "/topluluk.html",
            # Profil: hem gecerli hem OLMAYAN kullanici adi. Ikincisi
            # "bulunamadi" ekranini cizmeli, catmamali.
            "/profil.html?k=deneme_kisi", "/profil.html?k=yok_boyle_biri",
            "/profil.html",
            # Isletme sahibinin iki ekrani. isletmem.html girissiz halde
            # isletme-giris.html'e yonlendiriyor; bu listede aranan sey
            # "JS hatasi firlatmasin" ve o yonlendirme de hatasiz olmali.
            "/isletme-giris.html", "/isletmem.html"]


def _tarayici_yolu():
    """Playwright'in indirdigi tarayici ya da ortamda hazir duran."""
    kok = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if kok and os.path.isdir(kok):
        import glob
        for d in sorted(glob.glob(os.path.join(kok, "chromium-*", "chrome-linux", "chrome"))):
            return d
    return None


def kendini_kontrol_et():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ATLANDI: playwright yok")
        return None

    sunucu = subprocess.Popen([sys.executable, os.path.join(KOK, "sunucu.py"), "8199"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                import urllib.request
                urllib.request.urlopen(TABAN + "/index.html", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            print("ATLANDI: yerel sunucu acilmadi")
            return None

        sorunlar = []
        with sync_playwright() as p:
            yol = _tarayici_yolu()
            try:
                t = (p.chromium.launch(executable_path=yol, args=["--no-sandbox"])
                     if yol else p.chromium.launch(args=["--no-sandbox"]))
            except Exception as e:
                print("ATLANDI: tarayici yok (%s)" % str(e).split("\n")[0][:60])
                return None

            # CSP ihlalleri. AYRI toplaniyor cunku ENGELLENEN BIR SCRIPT
            # HATA FIRLATMIYOR: tarayici blogu sessizce calistirmiyor ve
            # sayfa "hatasiz" gorunuyor. Yerel sunucu artik vercel.json'daki
            # basligi gonderdigi icin (sunucu.py), yanlis bir karma tam
            # burada yakalaniyor -- yayinda degil.
            csp_ihlal = []

            def konsol(yolu, ileti):
                m = ileti.text or ""
                if "Content Security Policy" in m or "Refused to" in m:
                    csp_ihlal.append("%s: %s" % (yolu, m[:150]))

            # SERVICE WORKER BU BAGLAMDA KAPALI. Kayitli bir sw, sonraki
            # sayfalara ONBELLEKTEN yanit verebilir ve kontroller o an
            # diskteki dosyayi degil dun akşamki kopyayi sinamis olur --
            # sessizce yanlis gecen bir test takimi, olmayan bir test
            # takiminden kotu. PWA'nin kendisi ayri bir baglamda
            # sinaniyor (asagida).
            ctx = t.new_context(service_workers="block")

            def sayfa_ac(yolu, taklit=None, sahte_modul=False,
                         leafletsiz=False):
                sf = ctx.new_page()
                hata = []
                sf.on("pageerror", lambda e: hata.append(str(e)[:120]))
                sf.on("console", lambda i: konsol(yolu, i))
                if taklit:
                    sf.add_init_script(taklit)
                # Dis baglantilarin hepsi kapali: kontrol ag'a bagli olmasin
                # ve ZOR hal sinansin. Tek istisna, istenirse supabase-js:
                # onun yerine yerel bir taklit MODUL donuyor, boylece
                # girisli hal de sinanabiliyor.
                def yonlendir(r):
                    u = r.request.url
                    # LEAFLET ARTIK YEREL (app/lib/leaflet.js). Eskiden
                    # "harita yok" hali unpkg istegi kesilerek olusuyordu;
                    # kutuphane yerele alininca o hal kendiliginden
                    # imkansizlasti ve zarif dusus yolu (.harita-yok
                    # kutusu) SINANMAMIS kalacakti. Kesme burada.
                    if leafletsiz and u.endswith("/lib/leaflet.js"):
                        return r.abort()
                    # supabase-js KONTROLU ONCE: kutuphane artik yerel bir
                    # adresten (app/lib/supabase-js.js) geliyor, yani
                    # TABAN ile basliyor. Sira ters olsaydi taklit modul
                    # hic devreye girmez, gercek dosya CDN'e yonlenir ve
                    # o istek kesilirdi -- girisli halin 15 ekrani sessizce
                    # sinanmamis olurdu.
                    if "supabase-js" in u:
                        # Kutuphane artik YEREL bir adresten geliyor
                        # (app/lib/supabase-js.js). Iki hal de burada
                        # kuruluyor ve ikisi de kutuphanenin yerelde olup
                        # olmadigindan BAGIMSIZ:
                        #   sahte_modul=True  -> girisli hal sinaniyor
                        #   sahte_modul=False -> "kutuphane gelmedi" hali
                        # Ikincisi onemli: kutuphane yerele alininca o hal
                        # kendiliginden imkansizlasiyordu ve zarif dusus
                        # yollari (giris.html'in "acilamiyor" kutusu, katki
                        # formunun kapali kalmasi) SINANMAMIS kalirdi.
                        if sahte_modul:
                            return r.fulfill(status=200, body=SAHTE_MODUL,
                                             headers={"content-type": "text/javascript",
                                                      "access-control-allow-origin": "*"})
                        return r.abort()
                    if u.startswith(TABAN):
                        return r.continue_()
                    if sahte_modul and "supabase-js" in u:
                        return r.fulfill(status=200, body=SAHTE_MODUL,
                                         headers={"content-type": "text/javascript",
                                                  "access-control-allow-origin": "*"})
                    return r.abort()
                sf.route("**://*/**", yonlendir)
                sf.goto(TABAN + yolu, wait_until="domcontentloaded", timeout=20000)
                sf.wait_for_timeout(2500)
                return sf, hata

            # 1) Hicbir sayfa JS hatasi firlatmamali (CDN'siz).
            for yolu in SAYFALAR:
                sf, hata = sayfa_ac(yolu)
                if hata:
                    sorunlar.append("%s: %s" % (yolu, hata[0]))
                govde = (sf.inner_text("body") or "").strip()
                if len(govde) < 40:
                    sorunlar.append("%s: sayfa bos (%d karakter)" % (yolu, len(govde)))
                sf.close()

            # 1a2) Her sayfanin TAM BIR gorunur h1'i olmali.
            #
            # kesfet.html'in h1'i HIC YOKTU: baslik siralamasi dogrudan
            # kart h3'lerine atliyordu. Ekran okuyucu kullanicisi
            # basliklarla gezer ve sitenin ana ekraninda sayfanin ne
            # oldugunu soyleyen tek bir baslik bulamiyordu; ayrica
            # indekslenen bir sayfada h1 yoktu.
            #
            # "Gorunur" derken CIZILEN kastediliyor: giris.html'de uc h1
            # var (acik / kurulu degil / baglanti yok) ama ayni anda yalniz
            # biri cizilir. .gizli ile gorsel olarak gizlenmis bir h1
            # SAYILIR -- erisilebilirlik agacinda duruyor, ki mesele o.
            for yolu in SAYFALAR:
                sf, _ = sayfa_ac(yolu)
                n = sf.evaluate("""() => [...document.querySelectorAll('h1')]
                    .filter(e => e.getClientRects().length > 0 ||
                                 getComputedStyle(e).position === 'absolute')
                    .filter(e => { let x = e; while (x) {
                        if (x.hasAttribute && x.hasAttribute('hidden')) return false;
                        x = x.parentElement; } return true; })
                    .length""")
                if n != 1:
                    sorunlar.append("%s: %d gorunur h1 (tam 1 olmali)" % (yolu, n))
                sf.close()

            # 1a3) TELEFONDA hicbir denetim 24x24'un altinda olmamali.
            #
            # WCAG 2.5.8'in asgarisi 24x24 CSS px. Butce kaydiricisi 22 px
            # yuksekti -- kutusu 44 px oldugu icin gozle fark edilmiyordu
            # ama parmagin ortadaki dar bandi tutturmasi gerekiyordu.
            #
            # Kapsam BILEREK dar: dugme, alan, secici, sekme ve dugme
            # gorunumlu baglantilar. Metin icindeki satir ici baglantilar
            # disarida -- onlar kuralin kendisinden muaf ve dahil edilseydi
            # kontrol gurultuye bogulup okunmaz olurdu.
            # Telefon olculeri BAGLAM seviyesinde veriliyor: new_page()
            # viewport/is_mobile kabul etmiyor, onlar context secenegi.
            # IKI GENISLIK. 390 px yaygin telefon; 320 px en dar hal
            # (iPhone SE 1. nesil, Android'de kucuk yazi tipi olcegi).
            # 320 uzun sure OLCULMUYORDU ve marka degisiminde ust seridin
            # 335 px'e tasidigi ancak elle bakinca goruldu -- yani kontrol
            # degil sans yakaladi. Butce ve kategori cipleri de tam bu
            # genislikte sikisiyor.
            for _genislik in (320, 390):
              tel_ctx = t.new_context(viewport={"width": _genislik, "height": 844},
                                    is_mobile=True, has_touch=True,
                                    service_workers="block")
              tel = tel_ctx.new_page()
              # Kutuphane TAKLITLE karsilaniyor: mobil olcum, uygulamanin
              # gercek kullanicidaki hali uzerinde yapilmali -- yani kutuphane
              # CALISIRKEN. Onceden supabase-js hic gelmiyordu ve katki formu
              # hic acilmiyordu; formun select'i bu yuzden 23 px'te kalmis ve
              # aylarca olculmemisti. Olcumun, kutuphanenin yerele alinip
              # alinmadigina gore degismemesi de sart.
              tel.route("**://*/**", lambda r: (
                  r.fulfill(status=200, body=SAHTE_MODUL,
                            headers={"content-type": "text/javascript",
                                     "access-control-allow-origin": "*"})
                  if "supabase-js" in r.request.url
                  else (r.continue_() if r.request.url.startswith(TABAN) else r.abort())))
              tel.add_init_script(GIRIS_TAKLIT)
              # Isletme sahibinin iki ekrani da BURADA olmali: ikisi de form
              # ve formlarin olcusu tam bu kontrolun yakaladigi sey (katki
              # formunun select'i 23 px kalmisti). Bu baglam taklit modulu
              # servis ettigi icin panel gercekten CIZILIYOR -- kutuphanesiz
              # bir olcumde panel giris sayfasina yonlenir ve form hic
              # olculmezdi.
              for yolu in ("/index.html", "/kesfet.html?il=34", "/paylas.html",
                           "/giris.html", "/isletme.html?il=34&id=node/8223784325",
                           "/isletme-giris.html", "/isletmem.html"):
                  tel.goto(TABAN + yolu, wait_until="domcontentloaded", timeout=20000)
                  tel.wait_for_timeout(2200)
                  kucuk = tel.evaluate("""() => [...document.querySelectorAll(
                      'button, input:not([type=hidden]), select, textarea,'
                      + ' [role=tab], a.dugme, a.cip')]
                    .filter(e => e.getClientRects().length > 0)
                    /* Gorsel olarak gizlenmis girdi (.gizli) dokunma hedefi
                       DEGIL: yanindaki <label class="dugme"> hedef ve o 44 px.
                       WCAG 2.5.8 bu duruma acik istisna koyuyor -- ayni isi
                       yapan, olcuyu tutturan baska bir denetim varsa kucugu
                       muaf. Dosya secme girdisi tam olarak bu desen. */
                    .filter(e => !(e.classList.contains('gizli') &&
                                   document.querySelector('label[for="' + e.id + '"]')))
                    .map(e => { const r = e.getBoundingClientRect();
                      return { ad: e.tagName.toLowerCase() + '.'
                                   + String(e.className || '').split(' ')[0],
                               g: Math.round(r.width), y: Math.round(r.height) }; })
                    .filter(x => x.y < 24 || x.g < 24)""")
                  for x in kucuk:
                      sorunlar.append("%s (%d px): %s dokunma hedefi %dx%d (en az 24x24)"
                                      % (yolu, _genislik, x["ad"], x["g"], x["y"]))

                  # YATAY TASMA. Sayfa kendi genisligini asarsa kullanici
                  # saga kaydirmak zorunda kaliyor ve saga kayan bir sayfada
                  # dugmelerin yarisi ekran disinda duruyor. Iki kez oldu ve
                  # ikisi de ELLE bulundu: 320 px'te ust serit 335 px'e
                  # tasti, uzun bir Turkce baslik 288 px'lik kaba 308 px
                  # istedi. Olculen sey SONUC -- hangi ogenin tastigi degil,
                  # sayfanin tasip tasmadigi.
                  #
                  # 2 px pay: alt piksel yuvarlamasi ve kaydirma cubugu
                  # genisligi bazi hallerde 1 px oynatiyor.
                  tasma = tel.evaluate("""() => {
                      const d = document.documentElement;
                      if (d.scrollWidth <= d.clientWidth + 2) return null;
                      /* Tasiran ogeyi de soyle: "sayfa tasiyor" tek basina
                         aranacak yer birakmiyor. */
                      const en = d.clientWidth;
                      const suclu = [...document.querySelectorAll('body *')]
                        .filter(e => { const r = e.getBoundingClientRect();
                                       return r.width > 0 && r.right > en + 2; })
                        .map(e => e.tagName.toLowerCase() + '.' +
                                  String(e.className || '').split(' ')[0] +
                                  ' (' + Math.round(e.getBoundingClientRect().right) + ' px)');
                      return { genislik: d.scrollWidth, kap: en, suclu: suclu.slice(0, 3) };
                  }""")
                  if tasma:
                      sorunlar.append("%s (%d px): sayfa yatay tasiyor -- %d px yer istiyor, %s"
                                      % (yolu, _genislik, tasma["genislik"],
                                         ", ".join(tasma["suclu"]) or "sucluyu bulamadim"))
              tel.close()

            # 1a4) Yuklenen resim EXIF TASIMAMALI.
            #
            # Telefon fotografi GPS koordinati, cekim saati ve cihaz
            # modeli tasir. Bu projede ham IP bile saklanmiyor -- gunluk
            # yenilenen bir ozete cevriliyor. Kullanicinin bulundugu yerin
            # koordinatini bir menu fotografinin icinde yayimlamak o
            # ozenle celisirdi.
            #
            # SUNUCU BUNU DOGRULAYAMIYOR: Supabase Storage dosyayi
            # ayristirmiyor, ne verirsen onu saklar. Yani kural yalnizca
            # istemcide (ortak.js resimHazirla) ve tek bekcisi burasi.
            #
            # Sinama GERCEK bir EXIF blogu takiyor: "EXIF yok" diye
            # dogrulamak, hic EXIF'i olmayan bir dosyayla da gecerdi.
            sf, _ = sayfa_ac("/index.html")
            exif = sf.evaluate("""async ({ exifDizi, CIHAZ }) => {
              const t = document.createElement("canvas");
              t.width = 900; t.height = 400;
              const c = t.getContext("2d");
              c.fillStyle = "#c33"; c.fillRect(0, 0, 900, 400);
              const ham = await new Promise(r => t.toBlob(r, "image/jpeg", 0.9));
              const bayt = new Uint8Array(await ham.arrayBuffer());
              const ex = new Uint8Array(exifDizi);
              // SOI (FFD8) + EXIF blogu + geri kalani = "telefondan gelmis" dosya
              const b = new Uint8Array(2 + ex.length + bayt.length - 2);
              b.set(bayt.slice(0, 2), 0);
              b.set(ex, 2);
              b.set(bayt.slice(2), 2 + ex.length);
              const dosya = new File([b], "telefon.jpg", { type: "image/jpeg" });
              const oku = async d => {
                const u8 = new Uint8Array(await d.arrayBuffer());
                let s = ""; for (const x of u8) s += String.fromCharCode(x);
                return s;
              };
              const oncesi = await oku(dosya);
              const hazir = await resimHazirla(dosya, 300);
              const sonrasi = await oku(hazir);
              return {
                oncesiExif:   oncesi.includes("Exif"),
                oncesiCihaz:  oncesi.includes(CIHAZ),
                sonrasiExif:  sonrasi.includes("Exif"),
                sonrasiCihaz: sonrasi.includes(CIHAZ),
                tur: hazir.type, boyut: hazir.size
              };
            }""", {"exifDizi": list(EXIF_BLOK), "CIHAZ": EXIF_CIHAZ})
            # Once girdinin GERCEKTEN EXIF tasidigini dogrula, yoksa
            # kontrol bos bir dosyayla da yesil kalirdi.
            if not (exif["oncesiExif"] and exif["oncesiCihaz"]):
                sorunlar.append("EXIF sinamasi bozuk: girdi dosyasinda EXIF yok")
            if exif["sonrasiExif"]:
                sorunlar.append("yuklenecek resimde EXIF blogu kaliyor")
            if exif["sonrasiCihaz"]:
                sorunlar.append("yuklenecek resimde cihaz bilgisi kaliyor")
            if exif["tur"] != "image/jpeg":
                sorunlar.append("resim JPEG'e cevrilmiyor (%s)" % exif["tur"])
            if not exif["boyut"]:
                sorunlar.append("resim islenince bos ciktI")
            sf.close()

            # 1b) Hicbir [data-giris] bolumu KIRPILI kalmamali.
            #
            # sahne.css bu bolumleri perdeyle kapatiyor ve sahne.js
            # aciyor. Acilmazsa oge DOM'da, metni yerinde, olculebilir
            # bir kutusu var -- ama kullanici hicbir sey gormuyor.
            # checkVisibility() bile "gorunur" diyor, cunku clip-path'e
            # bakmiyor. Statik kontrol (test.py) bildigim SEKLI yakaliyor;
            # bu kontrol SONUCU olcuyor.
            for yolu in ("/index.html", "/isletme.html?il=34&id=node/8223784325",
                         "/hakkinda.html"):
                sf, _ = sayfa_ac(yolu)
                sf.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                sf.wait_for_timeout(2600)
                kirpik = sf.evaluate("""() => [...document.querySelectorAll('[data-giris]')]
                    .filter(e => { const s = getComputedStyle(e);
                        return parseFloat(s.opacity) < 0.05 ||
                               (s.clipPath || '').includes('100%'); })
                    .map(e => e.tagName.toLowerCase() + '.' +
                              String(e.className || '').split(' ')[0])""")
                if kirpik:
                    sorunlar.append("%s: perde acilmayan bolum %s" % (yolu, kirpik))
                sf.close()

            # 1c) Konum izni CEVAPLANMAZSA kullanici kilitlenmemeli.
            #
            # getCurrentPosition'in "timeout" secenegi izin istemi
            # cevaplanana kadar saymaya BASLAMIYOR (sartname boyle).
            # Kullanici istemi yanitlamayip oylece birakirsa -- en yaygin
            # davranis -- hicbir geri cagri gelmiyor. Olculdu: dugme
            # devre disi, yazi sonsuza kadar "Konum aliniyor…".
            # Sayfanin kendi bekcisi 12 sn'de kilidi acmali.
            sf, _ = sayfa_ac("/index.html")     # izin verilmedi, istem yanitsiz
            d = sf.query_selector("#yakinimdakiler")
            if not d:
                sorunlar.append("index.html: #yakinimdakiler dugmesi yok")
            else:
                d.click()
                sf.wait_for_timeout(13500)
                if d.is_disabled():
                    sorunlar.append("Konum izni yanitlanmayinca dugme kilitli kaliyor")
                acik = sf.eval_on_selector("#secim", "n => !n.hidden")
                if not acik:
                    sorunlar.append("Konum alinamayinca sehir secici acilmiyor")
            sf.close()

            # 1c1) ZINCIR MENUSUNDEN GELEN FIYAT ISARETLENIYOR MU,
            #      ve isaret IL DEGISINCE TAZELENIYOR MU.
            #
            # Olculdu: menu fiyati gosterilebilen 163 mekan yalniz 53
            # FARKLI ISLETME; 94'u Domino's subesi. Ayni ilde cok subeli
            # 113 mekanin hicbirinde subeler arasi fiyat farki yok --
            # yani tek kazima 56 ayri olcum gibi listeleniyordu.
            #
            # Buradaki sessiz kusur SAYININ KENDISI: zincir haritasi il
            # basina bir kez kuruluyor ve il degisiminde yenilenmezse
            # ekranda Ankara listesi + Istanbul sayilari kalir. Kart
            # yine cizilir, yine "zincir" yazar, yalniz SAYI yanlis
            # olur -- hicbir sey de bagirmaz.
            sf, _ = sayfa_ac("/kesfet.html?il=34&bayrak=menu")
            sf.wait_for_timeout(2600)
            isaretli = sf.eval_on_selector_all(".kart .tutar .zincir-not", "n => n.length")
            tutarli = sf.eval_on_selector_all(".kart .tutar", "n => n.length")
            if not tutarli:
                sorunlar.append("kesfet: 'fiyati olan' suzgeci hic kart vermedi")
            elif not isaretli:
                sorunlar.append("kesfet: 34'te hicbir fiyat zincir diye isaretlenmemis "
                                "(%d kartin hepsi kendi menusu mu?)" % tutarli)

            # Detay paneli TAM CUMLEYI vermeli: karar orada veriliyor.
            if isaretli:
                sf.click(".kart:has(.zincir-not) >> nth=0")
                sf.wait_for_timeout(900)
                uy = sf.inner_text("#d-govde")
                if "şubesi listelenen bir zincirin menüsünden" not in uy:
                    sorunlar.append("kesfet detay: zincir fiyatinin dayanagi yazmiyor")
                if "şubeye özel değil" not in uy:
                    sorunlar.append("kesfet detay: 'subeye ozel degil' uyarisi yok")
                sf.keyboard.press("Escape")
                sf.wait_for_timeout(300)

            # HARITA IL DEGISINCE YENIDEN KURULMALI.
            #
            # Ikinci il olarak IZMIR seciliyor, Ankara DEGIL: olculdu,
            # Ankara'nin 6 fiyatli mekaninin hicbiri zincir degil, yani
            # orada "isaret yok" DOGRU sonuc ve kontrol bozuk kodda da
            # gecerdi -- bos listeyi bos listeyle karsilastirmak hicbir
            # sey olcmez. Izmir'de 12 fiyatli mekanin 10'u zincir.
            #
            # Boylece iki ayri kusur da yakalaniyor:
            #   harita hic kurulmuyorsa      -> Izmir'de isaret cikmaz
            #   bir kez kurulup birakildiysa -> Istanbul haritasi Izmir
            #                                   adlarini tanimaz, yine cikmaz
            sf.select_option("#il", "35")
            sf.wait_for_timeout(2600)
            izmirTutar = sf.eval_on_selector_all(".kart .tutar", "n => n.length")
            basliklar = sf.eval_on_selector_all(
                ".kart .tutar .zincir-not",
                "n => n.map(x => x.closest('.tutar').getAttribute('title') || '')")
            if not izmirTutar:
                sorunlar.append("kesfet: il 35'e gecince hic fiyatli kart kalmadi")
            elif not basliklar:
                sorunlar.append("kesfet: 35'te %d fiyatli kartin hicbiri isaretli degil"
                                % izmirTutar)
            else:
                # DEGISMEZ: bir subenin sayisi, O ANDA YUKLU ILDEKI fiyatli
                # mekan sayisini ASAMAZ. Ayni ilde 12 fiyatli mekan varken
                # "56 subede ayni menu" demek, sayinin baska bir ilden
                # kaldigini soyler.
                #
                # ILK YAZIMDA "35'te hic isaret var mi" diye bakiyordu ve
                # SABOTAJ KACTI: harita bir kez kurulup birakilinca Izmir'in
                # Domino's subeleri Istanbul haritasinda ZATEN vardi, yani
                # isaret cikiyordu -- yalniz sayi 56 idi, 3 degil. Kusur
                # "isaret yok" degil "sayi yanlis"ti; kontrol de artik
                # SAYIYA bakiyor.
                import re as _re
                for b in basliklar:
                    e = _re.search(r"([\d.]+) şubede", b)
                    if not e:
                        continue
                    n = int(e.group(1).replace(".", ""))
                    if n > izmirTutar:
                        sorunlar.append(
                            "kesfet: 35'te '%d şubede' yaziyor ama ilde %d fiyatli mekan "
                            "var — zincir haritasi eski ilden kalmis" % (n, izmirTutar))
                        break
            sf.close()

            # 1c2) BUTCE GIRISLI ANA EKRAN: rakam, ne kadarinin
            #      OLCULDUGUNU soylemeden ekrana cikmamali.
            #
            # Ana ekran artik butceyle basliyor ("Bugun cebimde 300 TL").
            # Buradaki tehlike bir cokme degil, sessiz bir YALAN:
            #
            #   1. Dokum uc karttan cikarsa "2 mekanin fiyati olculdu"
            #      cumlesi uc mekana ait olur ve %0,45'lik olcum ucte bir
            #      gibi gorunur. Dokum SUZULMEMIS listeden gelmeli.
            #   2. Butce listeyi kesiyormus gibi gorunurse kullanici kalan
            #      mekanlarin butcesine uydugunu sanir. Olculdu: 300 TL
            #      Kadikoy'de 1.096 mekanin yalniz 36'sini eliyor (%3,3),
            #      cunku eleme YALNIZ olculmus fiyatla yapiliyor.
            #
            # Ikisi de sayfa "calisiyor" gorunurken olabilir; o yuzden
            # olculen sey EKRANDAKI SAYININ KENDISI.
            #
            # Konum izni VERILMIS ayri bir baglam: birincil yol bu ve
            # oteki kontroller izni hep reddedilmis halde kosuyor, yani
            # ekranin asil akisi hic acilmiyordu.
            kon_ctx = t.new_context(service_workers="block",
                                    geolocation={"latitude": 40.990,
                                                 "longitude": 29.028},  # Kadikoy
                                    permissions=["geolocation"])
            kon = kon_ctx.new_page()
            kon_hata = []
            kon.on("pageerror", lambda e: kon_hata.append(str(e)[:120]))
            kon.route("**://*/**", lambda r: (
                r.continue_() if r.request.url.startswith(TABAN) else r.abort()))

            def _butce_ara(butce, kategori):
                kon.goto(TABAN + "/index.html", wait_until="domcontentloaded",
                         timeout=20000)
                kon.wait_for_timeout(1400)
                kon.fill("#butce-girdi", butce)
                if kategori:
                    # Cip bir ANAHTAR ve secim cihazda saklaniyor: ikinci
                    # cagride kayitli secim geri geliyor, korlemesine
                    # tiklamak onu KAPATIYORDU. Ilk yazimda tam bu oldu ve
                    # kontrol "payda butceyle degisiyor" diye bagirdi --
                    # dogru bagirdi, sebebi kendi kusuruydu.
                    # SECICI data-tur UZERINDEN, gorunen metin uzerinden
                    # DEGIL. Cip artik ikon + metin tasiyor ve
                    # ":text-is" dis dugmeye degil ic <span>'e esliyor --
                    # kontrol 30 sn bekleyip zaman asimina dustu.
                    # data-tur zaten kodun kendi anahtari.
                    cip = kon.locator('.canim-cip[data-tur="%s"]' % kategori)
                    if cip.get_attribute("aria-pressed") != "true":
                        cip.click()
                kon.click("#yakinimdakiler")
                kon.wait_for_selector(".oneri", timeout=15000)
                kon.wait_for_timeout(400)
                return kon.inner_text("#konum-durum")

            # KATEGORI CIPI ARTIK "kat:..." tasiyor. Onceden duz tur adi
            # ("Kafe") vardi; kategoriler tur VE mutfak eksenine gecince
            # secici degisti ve bu satir 30 sn zaman asimina dustu --
            # yani cipin anahtarini degistirdigimizi ilk soyleyen sey bu
            # kontrol oldu.
            durum = _butce_ara("300", "kat:kahve")
            m = re.search(r"([\d.]+) mekan, en yakın üçü", durum)
            if not m:
                sorunlar.append("ana ekran: '%s' -- kac mekan icinden secildigi yazmiyor"
                                % durum[:70])
            else:
                toplam = int(m.group(1).replace(".", ""))
                # Kadikoy'un 3 km cemberinde 441 kafe olculdu. Kesin sayi
                # veriye bagli, ama UC OLMADIGI kesin: dokum uc karttan
                # cikarsa bu sayi da uce duser.
                if toplam < 50:
                    sorunlar.append("ana ekran: dokum %d mekandan cikmis; "
                                    "uc karttan sayiliyor olabilir" % toplam)
                ozet = kon.eval_on_selector(
                    "#butce-ozet", "n => n.hidden ? '' : n.textContent.trim()")
                if not ozet:
                    sorunlar.append("ana ekran: butcenin ne kadarinin OLCULDUGU yazmiyor")
                else:
                    # Cumledeki iki sayi TOPLAMI listeyi vermeli: "N mekanin
                    # menu fiyati olculdu ... Kalan M mekan". N+M != toplam
                    # ise ekran kendi rakamiyla celisiyor demektir.
                    sy = [int(x.replace(".", "")) for x in
                          re.findall(r"([\d.]+) mekan", ozet)]
                    if len(sy) == 2 and sum(sy) != toplam:
                        sorunlar.append("ana ekran: ozet %d+%d=%d diyor ama liste %d mekan"
                                        % (sy[0], sy[1], sum(sy), toplam))
                    if "tahmin" not in ozet:
                        sorunlar.append("ana ekran: olculmemis mekanlar TAHMIN diye "
                                        "isaretlenmiyor -> %s" % ozet[:80])
                # Secim kesfete tasinmali: kullanici butceyi ve kategoriyi
                # bir kez sesin, iki kez degil.
                hepsi = kon.eval_on_selector(".hepsi", "n => n.getAttribute('href')")
                # Kategori adreste KODLANMIS geciyor: "kat:kahve" ->
                # "kat%3Akahve". Iki nokta URL'de kacirilan bir karakter.
                for parca in ("butce=300", "tur=kat%3Akahve"):
                    if parca not in (hepsi or ""):
                        sorunlar.append("ana ekran: '%s' kesfet baglantisinda yok (%s)"
                                        % (parca, hepsi))

                # BUTCE PAYDAYI DEGISTIRMEMELI. Dokum, butce ustu oldugu
                # OLCULEN mekanlar cikarilmadan onceki listeden aliniyor;
                # 150 TL ile 700 TL ayni paydayi vermeli. Ayrisirsa ekran
                # butceyi suzgec gibi gostermeye baslamis demektir.
                d2 = _butce_ara("700", "kat:kahve")
                m2 = re.search(r"([\d.]+) mekan, en yakın üçü", d2)
                if m2 and int(m2.group(1).replace(".", "")) != toplam:
                    sorunlar.append("ana ekran: payda butceyle degisiyor (300 -> %d, "
                                    "700 -> %s); butce suzgec gibi gorunuyor"
                                    % (toplam, m2.group(1)))

            # Butce cihazda kalmali: ayni kisi ertesi gun yeniden yazmasin.
            kon.goto(TABAN + "/index.html", wait_until="domcontentloaded", timeout=20000)
            kon.wait_for_timeout(1200)
            if kon.input_value("#butce-girdi") != "700":
                sorunlar.append("ana ekran: butce cihazda saklanmiyor (%r)"
                                % kon.input_value("#butce-girdi"))
            if kon_hata:
                sorunlar.append("ana ekran JS hatasi: %s" % kon_hata[0])
            kon.close(); kon_ctx.close()

            # 1d) Turkce harfsiz arama ayni sonucu vermeli.
            #
            # Kullanicilarin cogu "kofte" yaziyor. Olculdu: sadelestirme
            # yokken "köfte" 574 mekan buluyordu, "kofte" 33 -- yani
            # harfsiz yazan kullanici sonuclarin %94'unu hic gormuyordu.
            sf, _ = sayfa_ac("/kesfet.html?il=34")
            sf.wait_for_timeout(1200)
            sayilar = {}
            for q in ("köfte", "kofte", "şişli", "sisli"):
                sf.fill("#ara", q)
                sf.wait_for_timeout(700)
                sayilar[q] = sf.inner_text("#sayac").strip()
            if sayilar["köfte"] != sayilar["kofte"]:
                sorunlar.append("arama: 'köfte' %s ama 'kofte' %s"
                                % (sayilar["köfte"], sayilar["kofte"]))
            if sayilar["şişli"] != sayilar["sisli"]:
                sorunlar.append("arama: 'şişli' %s ama 'sisli' %s"
                                % (sayilar["şişli"], sayilar["sisli"]))
            sf.close()

            # 1e) supabase-js CDN'den GELMEYINCE katki formu cikmamali.
            #
            # Kimlik.acik yalniz yapilandirmanin dolu oldugunu soyluyor;
            # istemcinin kurulup kurulmadigini degil. Bu kosum takimi zaten
            # butun dis baglantilari kesiyor, yani supabase-js hicbir zaman
            # gelmiyor -- ama form yine de aciliyordu. Kullanici formu
            # dolduruyor, "Giris yap ve ekle" diyor ve OLU bir giris
            # sayfasina firlatiliyordu. Ayni kural katki formunun kendi
            # yorumunda yazili: calismayan bir kutu gostermek, hic
            # gostermemekten kotu.
            sf, _ = sayfa_ac("/isletme.html?il=34&id=node/8223784325")
            gorunur = sf.evaluate("""() => {
                const f = document.getElementById('katkiForm');
                return f ? !f.hidden : false; }""")
            if gorunur:
                sorunlar.append("supabase-js yokken katki formu yine de aciliyor")
            sf.close()

            # 1f) ANA EKRANDA SUREKLI CIZIM YOK.
            #
            # ONCE NE OLCULUYORDU: kahramanda bir canvas "gece sokagi"
            # vardi ve kontrol dort hali olcuyordu -- ekrandayken kare
            # uretiyor mu, ekran disindayken duruyor mu, sekmeden donunce
            # ne oluyor. Sebebi olculmus bir kusurdu: visibilitychange
            # KOSULSUZ baslat() cagiriyordu ve sahne ekran disindayken
            # tam hizda yeniden basliyordu (600 ms'de 36 kare -- telefonda
            # dogrudan pil).
            #
            # SIMDI NE OLCULUYOR: o katman KALDIRILDI. Marka maketlerinin
            # hepsi acik temali, beyaz kartli; koyu sokak katmani acik
            # temada buyuk butce rakamini okunmaz yapiyordu. Katman gidince
            # eski kontrol "hic kare uretilmiyor" diye HAKLI olarak bagirdi.
            #
            # Kontrol SILINMIYOR, TERSINE CEVRILIYOR: ana ekranda artik
            # surekli donen bir cizim dongusu OLMAMALI. Silinseydi, yarin
            # geri gelen bir rAF dongusu -- ekran disinda da donen turden --
            # hicbir yerde goze carpmazdi.
            #
            # Bir kereye mahsus kareler serbest: giris animasyonlari
            # (data-giris) ve tarayicinin kendi kaydirma isi rAF
            # kullanabiliyor. Olculen sey SURMESI: sayfa durulduktan
            # sonra iki ayri pencerede de kare akmaya devam ediyor mu.
            sf, _ = sayfa_ac("/index.html", """(() => { window.__kare = 0;
                const a = window.requestAnimationFrame;
                window.requestAnimationFrame = function(f){
                  return a.call(window, function(t){ window.__kare++; return f(t); }); };
              })();""")
            gizle = """(v) => {
                Object.defineProperty(document, 'visibilityState',
                  { get: () => v ? 'hidden' : 'visible', configurable: true });
                Object.defineProperty(document, 'hidden',
                  { get: () => v, configurable: true });
                document.dispatchEvent(new Event('visibilitychange')); }"""

            def kare(ms=600):
                a = sf.evaluate("window.__kare")
                sf.wait_for_timeout(ms)
                return sf.evaluate("window.__kare") - a

            def sekmeden_don():
                sf.evaluate(gizle, True)
                sf.wait_for_timeout(300)
                sf.evaluate(gizle, False)
                sf.wait_for_timeout(300)

            # Giris animasyonlari bitene kadar bekle, sonra olc.
            sf.wait_for_timeout(2500)
            # ESIK 0 DEGIL: tarayici kaydirma/odak isi icin tek tuk kare
            # isteyebiliyor. Aranan sey SUREKLI donen bir dongu -- 600
            # ms'de 60 Hz'de ~36 kare eder; 5 kare onun cok altinda.
            SURUYOR = 5
            n = kare()
            if n > SURUYOR:
                sorunlar.append(
                    "ana ekran duruyorken hala cizim yapiyor (600 ms'de %d kare)" % n)
            sekmeden_don()
            n = kare()
            if n > SURUYOR:
                sorunlar.append(
                    "ana ekran sekmeden donunce cizime basliyor (600 ms'de %d kare)" % n)
            sf.evaluate("scrollTo(0, 3000)")
            sf.wait_for_timeout(800)
            n = kare()
            if n > SURUYOR:
                sorunlar.append(
                    "ana ekran ekran disindayken cizim yapiyor (600 ms'de %d kare)" % n)
            # Katman gercekten gitmis mi: bir canvas geri gelirse yukaridaki
            # sayimlar onu ancak SURDUGUNDE yakalar.
            if sf.evaluate("() => document.querySelectorAll('.kahraman canvas').length"):
                sorunlar.append("ana ekran kahramaninda canvas geri gelmis")
            sf.close()

            # 1g) GIRIS YAPILMIS hal. Bu kosum takimi butun dis
            # baglantilari kesiyor, yani supabase-js hicbir zaman
            # gelmiyordu -- yan etkisi, girisli sayfalarin hicbirinin
            # gercek tarayicida HIC calistirilmamis olmasiydi.
            # hesabim.html'in dort listesi, yonetim.html'in onay dugmeleri,
            # isletme.html'in fis ve sahiplik katmanlari: hepsi yalnizca
            # elle acilarak gorulmustu.
            #
            # Yetki TAKLIT EDILMIYOR: RLS'in dogru oldugu gercek
            # Postgres'te sinaniyor (veritabani/kos.sh). Burada sinanan
            # sey arayuz -- veri gelince ekranda dogru sey cikiyor mu.
            for ad, yol, sekme, bekle, olmasin in GIRISLI:
                sf, hata = sayfa_ac(yol, GIRIS_TAKLIT, sahte_modul=True)
                sf.wait_for_timeout(1200)
                if sekme:
                    d = sf.query_selector(sekme)
                    if not d:
                        sorunlar.append("%s: sekme dugmesi yok (%s)" % (ad, sekme))
                        sf.close(); continue
                    d.click()
                    sf.wait_for_timeout(900)
                if hata:
                    sorunlar.append("%s: %s" % (ad, hata[0]))
                govde = sf.inner_text("body") or ""
                for parca in bekle:
                    if parca not in govde:
                        sorunlar.append("%s: '%s' ekranda yok" % (ad, parca))
                for parca in olmasin:
                    if parca in govde:
                        sorunlar.append("%s: '%s' ekranda GORUNUYOR" % (ad, parca))
                sf.close()

            # 1h) Yonetici onayi gercekten tabloyu degistirmeli. Listenin
            # cizilmesi ile dugmenin CALISMASI ayri sey; dugme metnini
            # aramak ikincisini gostermez.
            sf, _ = sayfa_ac("/yonetim.html", GIRIS_TAKLIT, sahte_modul=True)
            sf.wait_for_timeout(1200)
            d = sf.query_selector('[data-karar="onaylandi"]')
            if not d:
                sorunlar.append("yonetim.html: onay dugmesi hic cizilmedi")
            else:
                d.click()
                sf.wait_for_timeout(900)
                durum = sf.evaluate(
                    "() => (window.__SAHTE_VERI.tablolar.paylasimlar[0]||{}).durum")
                if durum != "onaylandi":
                    sorunlar.append("yonetim.html: onay dugmesi durumu degistirmedi (%s)"
                                    % durum)
            sf.close()

            # 1i) Sahipligi birakmak kaydi SILMEMELI, durumunu
            # degistirmeli -- ve ekranda "biraktin" yazmali.
            #
            # Yonetici iptali kaydi zaten koruyordu, kullanicinin birakmasi
            # SILIYORDU. Ayni gerekce ikisinde de gecerli ve onemi somut:
            # sahibin katkisi INCELENMEDEN onaylaniyor, yani silme kalsaydi
            # biri mekani sahiplenip incelenmemis bilgi yazar, sonra birakir
            # ve sahip OLDUGUNA dair hicbir kayit kalmazdi.
            # Dugme artik ISLETME PANELINDE (isletmem.html): sahiplik
            # yonetimi oraya tasindi. Sinanan DAVRANIS ayni ve asil
            # onemli olan o -- hangi sayfada durdugu degil.
            sf, _ = sayfa_ac("/isletmem.html", GIRIS_TAKLIT, sahte_modul=True)
            sf.wait_for_timeout(2000)
            b2 = sf.query_selector("[data-birak]")
            if not b2:
                sorunlar.append("isletmem.html: sahipligi birak dugmesi yok")
            else:
                sf.once("dialog", lambda dg: dg.accept())
                b2.click()
                sf.wait_for_timeout(900)
                l = sf.evaluate("() => window.__SAHTE_VERI.tablolar.sahiplik")
                if len(l) != 1:
                    sorunlar.append("sahiplik birakinca kayit SILINDI (%d satir)" % len(l))
                elif l[0].get("durum") != "birakildi":
                    sorunlar.append("sahiplik birakinca durum '%s' oldu"
                                    % l[0].get("durum"))
                govde = sf.inner_text("body") or ""
                if "bıraktın" not in govde:
                    sorunlar.append("birakilan sahiplik ekranda 'bıraktın' demiyor")
                if "iptal edildi" in govde:
                    sorunlar.append("birakma 'iptal edildi' diye gosteriliyor "
                                    "(yoneticinin karariymis gibi)")
            sf.close()

            # 1j) "Kurulu degil" ile "su an acilamiyor" ayri sey.
            #
            # supabase-js CDN'den geliyor ve gelmeyebiliyor (kurumsal ag,
            # okul agi, ulke capinda engel -- Leaflet'te tam olarak bu oldu).
            # Onceden iki sebep de tek bir "false"a dusuyordu ve giris.html
            # ikisine de "Giris sistemi henuz kurulu degil -- app/
            # yapilandirma.js dosyasini doldur" diyordu. YAYINDAKI sitede bu
            # yanlis: sistem kurulu ve kullanici o dosyaya erisemiyor bile.
            # Kullaniciya, cozemeyecegi bir sey icin gelistirici talimati
            # gostermek, hicbir sey gostermemekten kotu.
            sf, _ = sayfa_ac("/giris.html")          # dis baglantilar kapali
            g = sf.inner_text("main") or ""
            if "açılamıyor" not in g:
                sorunlar.append("giris.html: supabase-js gelmeyince baglanti "
                                "mesaji cikmiyor")
            if "yapilandirma.js" in g or "kurulu değil" in g:
                sorunlar.append("giris.html: ag sorununda KURULUM talimati "
                                "gosteriliyor (site kurulu, kullanici o dosyaya "
                                "erisemez)")
            if not sf.query_selector("#tekrar"):
                sorunlar.append("giris.html: baglanti kutusunda 'Tekrar dene' yok")
            sf.close()

            # 1k) Yapilandirma GERCEKTEN bossa kurulum metni cikmali.
            # Yukaridaki duzeltmenin dogru mesaji bastirmadigini gormek icin
            # sart: tek basina "acilamiyor" aramak, kurulum ekranini tamamen
            # silmek suretiyle de gecerdi.
            sf = ctx.new_page()
            sf.route("**://*/**", lambda r: (
                r.fulfill(status=200, headers={"content-type": "text/javascript"},
                          body="window.CEBIMDE={supabaseUrl:'',supabaseAnahtar:''};")
                if r.request.url.endswith("yapilandirma.js")
                else (r.continue_() if r.request.url.startswith(TABAN) else r.abort())))
            sf.goto(TABAN + "/giris.html", wait_until="domcontentloaded", timeout=20000)
            sf.wait_for_timeout(2000)
            g = sf.inner_text("main") or ""
            if "kurulu değil" not in g:
                sorunlar.append("giris.html: yapilandirma bosken kurulum metni yok")
            sf.close()

            # 1l) CDN ASILI kalirsa sayfa sonsuza kadar beklememeli.
            # Olculdu: cevaplanmayan bir istekte sayfa SURESIZ bos kaliyordu.
            # kimlik.js'te 12 sn'lik sinir var; burada sonucu olculuyor.
            sf = ctx.new_page()
            asili = []
            def asili_birak(r):
                u = r.request.url
                if u.startswith(TABAN):
                    return r.continue_()
                if "supabase-js" in u:
                    asili.append(r)      # cevaplamadan birak
                    return
                return r.abort()
            sf.route("**://*/**", asili_birak)
            sf.add_init_script("window.__t0 = Date.now();")
            sf.goto(TABAN + "/giris.html", wait_until="domcontentloaded", timeout=20000)
            cikti = None
            for _ in range(44):          # en fazla 22 sn
                cikti = sf.evaluate("""() => {
                  const m = document.querySelector('main');
                  const t = ((m && m.innerText) || '').trim();
                  return t.length > 20 ? (Date.now() - window.__t0) / 1000 : null; }""")
                if cikti:
                    break
                sf.wait_for_timeout(500)
            if not cikti:
                sorunlar.append("giris.html: supabase-js asili kalinca sayfa "
                                "hic acilmiyor (sinirsiz bekliyor)")
            elif cikti > 16:
                sorunlar.append("giris.html: bos ekran %.0f sn surdu" % cikti)
            for r in asili:
                try:
                    r.abort()
                except Exception:
                    pass
            sf.close()

            # 1m) ATIFSIZ Commons fotografi HIC CIZILMEMELI.
            #
            # CC BY ve CC BY-SA, yazar adini ve lisansi gostermeyi ZORUNLU
            # kiliyor; atifsiz kullanim lisansi ihlal eder. Veritabani
            # kisiti atifsiz satiri zaten kabul etmiyor, ama eski bir
            # satir ya da baska bir yol kalabilir -- gosterim tarafi da
            # kendi basina korumali.
            #
            # Kontrol DOM'A bakiyor, metne DEGIL: fotografin adresi
            # src ozniteliginde duruyor ve inner_text'te hic gecmiyor.
            # Ilk yazim metne bakiyordu ve sabotajda KACTI.
            sf, _ = sayfa_ac("/isletme.html?il=34&id=node/8223784325",
                             GIRIS_TAKLIT, sahte_modul=True)
            sf.wait_for_timeout(1500)
            g = sf.evaluate("""() => {
              const k = [...document.querySelectorAll('.galeri-kutu')];
              return {
                adet: k.length,
                kaynaklar: k.map(x => (x.querySelector('img') || {}).src || ""),
                atifsizVar: k.some(x =>
                  ((x.querySelector('img') || {}).src || "").includes('commons=d'))
              };
            }""")
            # Taklit veride 4 fotograf var; biri ATIFSIZ commons.
            if g["adet"] != 3:
                sorunlar.append("galeri: %d kutu cizildi, 3 olmaliydi (%s)"
                                % (g["adet"], g["kaynaklar"]))
            if g["atifsizVar"]:
                sorunlar.append("galeri: ATIFSIZ commons fotografi cizilmis")
            sf.close()

            # 2) Harita YOKKEN kesfet calismali. Asil bulunan hata buydu.
            # Kutuphane yerelde durdugu icin istek ACIKCA kesiliyor:
            # "yerel dosya bir gun bozulursa" hali de bu.
            sf, hata = sayfa_ac("/kesfet.html?il=06", leafletsiz=True)
            kart = sf.eval_on_selector_all(".kart", "n => n.length")
            # Kutunun VARLIGI degil METNI olculuyor: bos bir kutu
            # kullaniciya haritanin neden gitigini soylemiyor ve
            # "yerine bir sey kondu" diye gecen bir kontrol, konmadigini
            # gizler. Sabote edilerek gorüldü.
            yedek = sf.eval_on_selector_all(
                ".harita-yok", "n => n.map(x => x.innerText.trim()).join('')")
            if kart == 0:
                sorunlar.append("Leaflet yokken kesfet hic kart cizmiyor")
            if len(yedek) < 30:
                sorunlar.append("Leaflet yokken harita yerine aciklama konmuyor "
                                "(kutu metni %d karakter)" % len(yedek))
            sf.close()

            # 2a) FILTRE CUBUGU: ETIKETLER KIRPILMAMALI, KUTULAR 44 PX.
            #
            # Play magaza ekran goruntusu alinirken yakalandi: 360 px'de
            # il secici "İstanbu" yaziyordu. Pesinden iki sey daha cikti:
            #
            #   - #konum-al class="mini" tasiyor ama HICBIR kural onu
            #     tutmuyordu (yalniz "select.mini" yaziliydi). Olculdu:
            #     81x41, cerceve 0, zemin saydam. Iki cerceveli kutunun
            #     yaninda ciplak yazi ve dokunma alani 41 px -- bu depo
            #     WCAG 2.5.8'in 44 px'ini her yerde uyguluyor.
            #   - Butonu kutuya sokunca 138 px oldu ve ucu birden ayni
            #     satirda kalamadi: 320 px'te seciciye 29 px metin
            #     alani kaliyordu. 471 px alti buton kendi satirina.
            #
            # HICBIR GENISLIK butun il adlarina yetmiyor
            # ("Kahramanmaraş" 148 px), o yuzden iki sey birden
            # sinaniyor: SECILI ad ve en uzun SIRALAMA etiketi sigmali,
            # sigmayan il adi da ELLIPSIS ile bitmeli -- kirpilan ad
            # yazim hatasi gibi duruyor, ucu ucu kirpildigini soyluyor.
            #
            # 471 de listede: esik oradan gecti; kayarsa burasi yanar.
            for genislik in (320, 360, 390, 430, 471):
                sf, hata = sayfa_ac("/kesfet.html?il=34")
                sf.set_viewport_size({"width": genislik, "height": 844})
                sf.wait_for_timeout(600)
                o = sf.evaluate("""() => {
                  const il = document.getElementById('il');
                  const sr = document.getElementById('sirala');
                  const kb = document.getElementById('konum-al');
                  if (!il || !sr || !kb) return null;
                  const cs = getComputedStyle(il);
                  const c = document.createElement('canvas').getContext('2d');
                  c.font = cs.fontWeight+' '+cs.fontSize+' '+cs.fontFamily;
                  /* Ic genislik: kutudan ic bosluk VE cerceve dusulur.
                     Cerceveyi unutmak 2 px'lik kirpmayi gizler. */
                  const yer = e => {
                    const s = getComputedStyle(e);
                    return Math.round(e.getBoundingClientRect().width
                      - parseFloat(s.paddingLeft)  - parseFloat(s.paddingRight)
                      - parseFloat(s.borderLeftWidth) - parseFloat(s.borderRightWidth));
                  };
                  const enUzun = e => Math.max.apply(null,
                    [...e.options].map(o => Math.ceil(c.measureText(o.text.trim()).width)));
                  return {
                    il_ad: il.options[il.selectedIndex].text,
                    il_metin: Math.ceil(c.measureText(il.options[il.selectedIndex].text).width),
                    il_yer: yer(il),
                    sr_metin: enUzun(sr),
                    sr_yer: yer(sr),
                    ellipsis: cs.textOverflow,
                    kb_boy: Math.round(kb.getBoundingClientRect().height),
                    kb_cerceve: parseFloat(getComputedStyle(kb).borderTopWidth)
                  };
                }""")
                sf.close()
                if not o:
                    sorunlar.append("kesfet: filtre cubugunda secici/buton bulunamadi")
                    break
                if o["il_metin"] > o["il_yer"]:
                    sorunlar.append(
                        "kesfet %dpx: il secicide '%s' kirpiliyor "
                        "(metin %d px, yer %d px)"
                        % (genislik, o["il_ad"], o["il_metin"], o["il_yer"]))
                if o["sr_metin"] > o["sr_yer"]:
                    sorunlar.append(
                        "kesfet %dpx: siralama secicisinde en uzun etiket kirpiliyor "
                        "(metin %d px, yer %d px)"
                        % (genislik, o["sr_metin"], o["sr_yer"]))
                if o["ellipsis"] != "ellipsis":
                    sorunlar.append(
                        "kesfet %dpx: il secicide text-overflow ellipsis yok; "
                        "uzun il adi (Kahramanmaraş 148 px) sessizce kirpilir"
                        % genislik)
                if o["kb_boy"] < 44:
                    sorunlar.append(
                        "kesfet %dpx: Konumum dugmesi %d px yuksek (WCAG 2.5.8 en az 44)"
                        % (genislik, o["kb_boy"]))
                if o["kb_cerceve"] <= 0:
                    sorunlar.append(
                        "kesfet %dpx: Konumum dugmesinin cercevesi yok; "
                        "iki cerceveli secicinin yaninda dugme gibi durmuyor"
                        % genislik)

            # 2c) KONUM VERILINCE LISTE YAKINDAN UZAGA SIRALANMALI.
            #
            # Olculdu (yayindaki ekran goruntusunden): kullanici
            # "Konumum"a basiyor, konum aliniyor, mesafe rozetleri
            # ciziliyor -- ve liste HALA A -> Z'de kaliyordu. Ankara'da
            # ilk dort kart "06 Tado Dondurma, 1. Yurt Kantini,
            # 100 Burger, 1071 Aspava" idi; yani adi rakamla
            # baslayanlar. Konumunu veren kisinin istedigi sey zaten
            # yakindan uzaga; ayri bir menuden bir daha secmesini
            # beklemek ozelligi gorunmez yapiyordu.
            #
            # DUGME YAZISI DA SINANIYOR ve sebebi olculdu: durum yazisi
            # dugmenin ICINDEYDI, "Konumum" (138 px) -> "konumun
            # kullanılıyor" (237 px) olunca yanindaki siralama
            # secicisini eziyor ve "Bana yakın" 471-600 px arasinda
            # kirpiliyordu. Bir de textContent dugmenin <svg> igesini
            # siliyordu. Ikisi de burada yaniyor.
            # AYRI BAGLAM ACILMIYOR, ayni ctx'e izin veriliyor: yeni bir
            # tarayici baglami taze profil demek ve olculdu -- iki yeni
            # kontrol takimi test.py'nin 420 sn sinirinin ustune
            # cikarmisti. 2d de ayni sayfada olculuyor (ayri bir sayfa
            # yuku daha eklemek yerine).
            ctx.grant_permissions(["geolocation"])
            ctx.set_geolocation({"latitude": 39.9208, "longitude": 32.8541})
            try:
                ksf, _hata = sayfa_ac("/kesfet.html?il=06")
                ksf.wait_for_timeout(900)

                # 2d) HER KARTIN BIR GORSEL YUVASI OLMALI -- tiklamadan
                # ONCE, ayni sayfada.
                #
                # "Ekranda resimler olsun" istendi ve olculdu: bugun tek
                # bir fotograf yok (il dosyalarinda foto alani yok,
                # foto_cek.py hic kosmamis, kesfet listesi zaten
                # Supabase'e cikmiyor). Bos kutu birakmak 35.852 mekani
                # ayni gri dikdortgenle listelemek olurdu; yuva HER
                # ZAMAN dolu -- kategori simgesi.
                g = ksf.evaluate("""() => {
                  const k = [...document.querySelectorAll('.kart')].slice(0, 24);
                  const y = k.map(x => x.querySelector('.kart-gorsel'));
                  return {
                    kart: k.length,
                    yuva: y.filter(Boolean).length,
                    cizim: y.filter(x => x && x.querySelector('svg') &&
                                         x.querySelector('svg').children.length).length,
                    olcu: y[0] ? [Math.round(y[0].getBoundingClientRect().width),
                                  Math.round(y[0].getBoundingClientRect().height)] : null,
                    kat: [...new Set(y.filter(Boolean).map(x => x.dataset.kat))]
                  };
                }""")
                if g["kart"] < 10:
                    sorunlar.append("kesfet: kart cizilmedi, gorsel yuvasi olculemedi")
                else:
                    if g["yuva"] != g["kart"]:
                        sorunlar.append("kesfet: %d karttan %d'sinde gorsel yuvasi yok"
                                        % (g["kart"], g["kart"] - g["yuva"]))
                    if g["cizim"] != g["kart"]:
                        sorunlar.append("kesfet: %d gorsel yuvasi BOS -- bos kutu, "
                                        "kutu olmamasindan kotu"
                                        % (g["kart"] - g["cizim"]))
                    if not g["olcu"] or g["olcu"][0] < 40 or g["olcu"][1] < 40:
                        sorunlar.append("kesfet: gorsel yuvasi cok kucuk: %s" % (g["olcu"],))
                    if len(g["kat"]) < 2:
                        sorunlar.append("kesfet: butun kartlar ayni kategori simgesini "
                                        "kullaniyor (%s)" % g["kat"])
                    if "yok" in g["kat"]:
                        sorunlar.append("kesfet: bazi mekanlar hicbir kategoriye "
                                        "dusmuyor, yuvaya notr isaret giriyor")

                once = ksf.eval_on_selector("#sirala", "e => e.value")
                genislik_once = ksf.eval_on_selector(
                    "#konum-al", "e => Math.round(e.getBoundingClientRect().width)")
                ksf.click("#konum-al")
                ksf.wait_for_timeout(1500)
                o = ksf.evaluate("""() => {
                  const kb = document.querySelector('#konum-al');
                  const mesafe = [...document.querySelectorAll('.kart')].slice(0, 8)
                    .map(k => {
                      const r = k.querySelector('.rozet.mesafe');
                      if (!r) return null;
                      const t = r.textContent.trim();
                      /* "110 m" ve "1.4 km" -> metre */
                      const s = parseFloat(t.replace(',', '.'));
                      return t.endsWith('km') ? s * 1000 : s;
                    });
                  return {
                    sirala: document.querySelector('#sirala').value,
                    mesafe: mesafe,
                    kb_genislik: Math.round(kb.getBoundingClientRect().width),
                    kb_simge: !!kb.querySelector('svg'),
                    durum: (document.querySelector('#konum-durum') || {}).textContent || ""
                  };
                }""")
                if once != "ad":
                    sorunlar.append("kesfet: baslangic siralamasi 'ad' degil (%s)" % once)
                if o["sirala"] != "yakin":
                    sorunlar.append(
                        "kesfet: konum alindi ama siralama '%s' kaldi; "
                        "liste yakindan uzaga gecmiyor" % o["sirala"])
                m = [x for x in o["mesafe"] if x is not None]
                if len(m) < 4:
                    sorunlar.append("kesfet: konum verildi ama mesafe rozeti "
                                    "cizilmiyor (%d kart)" % len(m))
                elif any(m[i] > m[i + 1] + 0.5 for i in range(len(m) - 1)):
                    sorunlar.append("kesfet: liste yakindan uzaga sirali degil: %s" % m)
                if not o["kb_simge"]:
                    sorunlar.append("kesfet: Konumum dugmesinin simgesi tiklamadan "
                                    "sonra siliniyor")
                if o["kb_genislik"] != genislik_once:
                    sorunlar.append(
                        "kesfet: Konumum dugmesi tiklaninca %d -> %d px degisiyor; "
                        "yanindaki secicileri eziyor"
                        % (genislik_once, o["kb_genislik"]))
                if "yakın" not in o["durum"].lower():
                    sorunlar.append("kesfet: konum durumu kullaniciya "
                                    "bildirilmiyor (%r)" % o["durum"][:40])
                ksf.close()
            except Exception as e:
                sorunlar.append("kesfet konum kontrolu kosulamadi: %s: %s"
                                % (type(e).__name__, str(e)[:80]))
            finally:
                # Izin geri aliniyor: sonraki kontroller konumsuz halin
                # de calistigini gormeli.
                ctx.clear_permissions()

            # 2b) ISLETME SAYFASINDA KONUM HARITASI.
            #
            # Adresi olan mekan yalniz %26,2 (9.397/35.852); kalan
            # 26.455 mekanda haritadaki nokta "burasi nerede" sorusunun
            # TEK cevabi. Iki hal birden sinaniyor:
            #   harita VARKEN  -> leaflet kabi ve isaret ciziliyor
            #   harita YOKKEN  -> koordinat ve dis baglantilar duruyor
            # Yalniz birine bakmak, ozelligi tamamen silen bir
            # degisiklikten de gecerdi (kesfet haritasiyla ayni desen).
            sf, hata = sayfa_ac("/isletme.html?il=34&id=node/8223784325")
            sf.wait_for_timeout(900)
            # SEKME ACILIYOR: harita "Bilgi" sekmesinin ardinda ve o
            # grup display:none. Tiklamadan olcmek, kullanicinin hic
            # gormedigi bir hali olcmek olurdu.
            sf.eval_on_selector('.sekme-cubuk [data-sekme="bilgi"]', "e => e.click()")
            sf.wait_for_timeout(700)
            k = sf.evaluate("""() => {
              const m = document.getElementById('mekanHarita');
              const r = m.getBoundingClientRect();
              const p = m.querySelector('path');
              const b = p ? p.getBoundingClientRect() : null;
              return {
                kap:    !!document.querySelector('#mekanHarita.leaflet-container'),
                isaret: !!p,
                /* Isaretin MERKEZI, kutunun merkezine gore. Leaflet
                   gizli kapta 0x0 olcup isareti kutunun DISINA
                   koyuyordu; "path var mi" diye bakan bir kontrol bunu
                   goremez. */
                sapmaX: b ? Math.round(Math.abs((b.x + b.width/2) - (r.x + r.width/2))) : -1,
                sapmaY: b ? Math.round(Math.abs((b.y + b.height/2) - (r.y + r.height/2))) : -1,
                icinde: !!(b && b.x >= r.x && b.y >= r.y &&
                           b.x + b.width <= r.x + r.width &&
                           b.y + b.height <= r.y + r.height),
                koord:  (document.getElementById('konumKoordinat')||{}).textContent||'',
                tarif:  (document.querySelector('#konumBaglar a')||{}).href||''
              };
            }""")
            if not k["kap"]:
                sorunlar.append("isletme: konum haritasi kurulmadi")
            if not k["isaret"]:
                sorunlar.append("isletme: haritada mekanin isareti yok")
            # ISARET KUTUNUN ICINDE VE ORTASINDA OLMALI. Bu satir
            # gercek bir hatanin uzerine yazildi: harita gizli sekmede
            # kuruldugu icin Leaflet kabi 0x0 olcuyor ve isaret kutunun
            # sol ust kosesinin DISINA dusuyordu (kutu 16,403 358x220
            # iken isaret 8,395). Ekranda bos bir harita goruluyordu.
            elif not k["icinde"]:
                sorunlar.append("isletme: harita isareti kutunun DISINDA "
                                "(sapma %d,%d px) -- invalidateSize cagrilmiyor"
                                % (k["sapmaX"], k["sapmaY"]))
            elif k["sapmaX"] > 4 or k["sapmaY"] > 4:
                sorunlar.append("isletme: harita isareti merkezde degil "
                                "(sapma %d,%d px)" % (k["sapmaX"], k["sapmaY"]))
            # KOORDINATIN KENDISI: harita cizilse de cizilmese de
            # "burasi nerede" sorusunun bir cevabi ekranda kalmali.
            if "40.986810, 29.025530" not in k["koord"]:
                sorunlar.append("isletme: koordinat ekranda yazmiyor (%r)"
                                % k["koord"][:60])
            # YOL TARIFI KOORDINATA GITMELI. Adla aramaya duserse
            # kullanici ayni adli baska bir subeye gider -- ve bag
            # gorunuste calismaya devam ettigi icin fark edilmez.
            if "destination=40.986810%2C29.025530" not in k["tarif"]:
                sorunlar.append("isletme: yol tarifi koordinata gitmiyor (%r)"
                                % k["tarif"][:80])
            sf.close()

            # HARITASIZ HALDE BASKA BIR MEKAN: node/8223784325 (Draft)
            # MENUSUZ ve ilk yazimda "Leaflet yokken menu de cizilmiyor"
            # diye HATA VERDI -- kod degil KONTROL yanlisti, olmayan bir
            # menuyu ariyordu. Adana'daki bu mekanin menusu de,
            # instagrami da var; yani "harita gitti, geri kalan duruyor"
            # gercekten olculebiliyor.
            sf, hata = sayfa_ac("/isletme.html?il=01&id=node/13068227666",
                                leafletsiz=True)
            sf.wait_for_timeout(700)
            y = sf.evaluate("""() => ({
              yedek: ((document.querySelector('#mekanHarita .harita-yok')||{})
                        .innerText||'').trim(),
              bag:   document.querySelectorAll('#konumBaglar a').length,
              sosyal: document.querySelectorAll('#konumSosyal a').length,
              koord: (document.getElementById('konumKoordinat')||{}).textContent||'',
              menu:  document.querySelectorAll('#menuSatirlar li').length
            })""")
            if len(y["yedek"]) < 30:
                sorunlar.append("isletme: Leaflet yokken harita yerine aciklama "
                                "konmuyor (%d karakter)" % len(y["yedek"]))
            if y["bag"] < 4:
                sorunlar.append("isletme: Leaflet yokken dis harita baglantilari "
                                "da kayboluyor (%d bag)" % y["bag"])
            if y["sosyal"] == 0:
                sorunlar.append("isletme: Leaflet yokken sosyal hesap dugmesi "
                                "de kayboluyor")
            if "36.772070, 35.792900" not in y["koord"]:
                sorunlar.append("isletme: Leaflet yokken koordinat da yaziMIYOR "
                                "(%r)" % y["koord"][:60])
            if y["menu"] == 0:
                sorunlar.append("isletme: Leaflet yokken menu de cizilmiyor")
            sf.close()

            # 2z) FIS ESIGI KESFET EKRANINDA DA GECERLI.
            #
            # Bu kontrol, bulunmus bir hatanin uzerine yazildi: esik
            # (FIS_ESIK=3) yalniz isletme.html'de tanimliydi ve kesfet
            # ekrani ondan habersizdi. Sonuc, TEK BIR kisinin tek fisinin
            # kart rozetinde "kisi basi ~240 TL" diye yayimlanmasiydi --
            # ustelik detay paneli altina "1 kisinin paylasimindan" diye
            # de yaziyordu. Esigin iki sebebi de cignenmis oluyordu:
            # bir kisinin o gunku secimi mekanin fiyati sayiliyordu ve
            # o kisi, tanidigi biri tarafindan fise baglanabiliyordu.
            #
            # Iki yonlu sinaniyor: esigin ALTI sizdirmamali, USTU
            # gostermeli. Yalniz birine bakmak, ozelligi tamamen silen bir
            # degisiklikten de gecerdi.
            def fisli_taklit(adet):
                satir = ('{ id:%d, mekan_id:"node/5284691026", mekan_ad:"Fis Kafe", '
                         'il:"34", tutar:%d, kisi:2, tarih:"2026-08-2%d", '
                         'durum:"onaylandi" }')
                return ("window.__SAHTE_VERI = { oturum:null, tablolar:{ paylasimlar:[" +
                        ",".join(satir % (i + 1, 480 + i * 20, i) for i in range(adet)) +
                        "] }, rpc:{} };")

            for adet, beklenen in ((2, False), (3, True)):
                sf, _ = sayfa_ac("/kesfet.html?il=34&q=aksi%20lounge",
                                 fisli_taklit(adet), sahte_modul=True)
                sf.wait_for_timeout(1500)
                var = sf.eval_on_selector_all(
                    ".kart .rozet.vurgulu",
                    "n => n.some(x => /kişi başı/.test(x.textContent))")
                if var is not beklenen:
                    sorunlar.append(
                        "kesfet: %d fisle kart rozeti %s (beklenen %s) -- "
                        "esik ya sizdiriyor ya da hic gostermiyor"
                        % (adet, "var" if var else "yok",
                           "var" if beklenen else "yok"))
                # Detay paneli de ayni esige uymali: rozet duzeltilip panel
                # unutulabilirdi (iki ayri yerde iki ayri cizim).
                k = sf.query_selector('.kart[data-id="node/5284691026"]')
                if k:
                    k.click(); sf.wait_for_timeout(700)
                    # DOM'A bakiliyor, METNE degil: kutunun basligindaki
                    # span'de text-transform:uppercase var ve inner_text
                    # onu UYGULUYOR -- "Gerçekten ödenen" arayan bir
                    # kontrol, kutu tam ekrandayken bile hic eslesmiyordu.
                    # (Ayni tuzak bu depoda daha once galeri atifinda cikti.)
                    sizdi = sf.eval_on_selector_all(
                        "#d-govde .odenen",
                        "n => n.some(x => !x.classList.contains('az'))")
                    if sizdi is not beklenen:
                        sorunlar.append(
                            "kesfet detay: %d fisle 'gercekten odenen' kutusu %s"
                            % (adet, "cikiyor" if sizdi else "cikmiyor"))
                    panel = sf.inner_text("#d-govde") or ""
                    if not beklenen and "fiş var" not in panel:
                        sorunlar.append("kesfet detay: esik altinda kac fis "
                                        "kaldigi yazmiyor (katki cagrisi kayip)")
                    if beklenen and "250" not in panel:
                        sorunlar.append("kesfet detay: medyan (250) yazmiyor")
                sf.close()

            # 2y) Butce akranlari serit halinde gorunmeli -- ve butce
            # girilmeden GORUNMEMELI. Bos bir "0 kisi" satiri hem yer
            # kapliyor hem cesaret kiriyor.
            sf, _ = sayfa_ac("/kesfet.html?il=34", GIRIS_TAKLIT, sahte_modul=True)
            sf.wait_for_timeout(1500)
            if sf.eval_on_selector("#akran", "n => !n.hidden"):
                sorunlar.append("kesfet: butce girilmeden akran seridi gorunuyor")
            sf.close()

            sf, _ = sayfa_ac("/kesfet.html?il=34&butce=300", GIRIS_TAKLIT,
                             sahte_modul=True)
            sf.wait_for_timeout(1800)
            serit = (sf.inner_text("#akran") or "").strip()
            # Sayilar taklitten geliyor (37 kisi / 12 mekan): sabit bir
            # cumle degil, GELEN VERI ciziliyor mu ona bakiliyor.
            if "37" not in serit or "12" not in serit:
                sorunlar.append("kesfet: akran seridi verideki sayilari "
                                "yazmiyor ('%s')" % serit[:80])
            sf.close()

            # 2x) Civar kutusu ("mahalle statusu"). Gercek bir Istanbul
            # mekani secildi: node/5284691026, 500 m cevresinde 56 mekan.
            # Sayi VERIDEN geliyor, yazili degil -- sabit bir metin aramak
            # hesabin dogru oldugunu gostermezdi.
            sf, _ = sayfa_ac("/isletme.html?il=34&id=node%2F5284691026",
                             GIRIS_TAKLIT, sahte_modul=True)
            sf.wait_for_timeout(1800)
            if sf.eval_on_selector("#civar", "n => n.hidden"):
                sorunlar.append("isletme: civar kutusu 56 komsulu mekanda cikmiyor")
            else:
                civar = sf.inner_text("#civar") or ""
                if "56" not in civar:
                    sorunlar.append("isletme: civar mekan sayisi yanlis "
                                    "(56 bekleniyordu) -- '%s'" % civar[:100])
                if "500 m" not in civar:
                    sorunlar.append("isletme: civar yaricapi yazmiyor")
                # Fis medyani taklitten (265) geliyor ve esigi geciyor (7 fis).
                if "265" not in civar:
                    sorunlar.append("isletme: civar fis medyani cizilmiyor")
                # Katki cagrisi SAYIYLA olmali: "fiyat ekle" soyut, "bu
                # civarda 55 mekanin fiyati yok" degil.
                if "fiyatı bilinmiyor" not in civar:
                    sorunlar.append("isletme: civar katki cagrisi sayisiz")
            sf.close()

            # 2v) ANDROID GERI TUSU. Olculdu: detay paneli acikken geri
            # basinca panel kapanmiyordu, KESFET EKRANINDAN TAMAMEN
            # cikiliyordu (adres index.html oluyordu). Tarayicida can
            # sikici, uygulamada daha kotu: TWA'da baslangic adresinde
            # geri basmak uygulamadan CIKMAK demek -- yani bir mekana
            # bakip geri basan kullanicinin uygulamasi kapaniyordu.
            #
            # UC HALIN UCU DE SINANIYOR. Yalniz birincisine bakmak
            # yetmez: paneli acarken gecmise kayit koyup KAPANIRKEN
            # geri almayan bir surum de ilk adimi gecer, sonra kullanici
            # "geri basiyorum bir sey olmuyor" haline duserdi.
            geri_ctx = t.new_context(viewport={"width": 390, "height": 844},
                                     is_mobile=True, has_touch=True,
                                     service_workers="block")
            gs = geri_ctx.new_page()
            gs.route("**://*/**", lambda r: (r.continue_()
                     if r.request.url.startswith(TABAN) else r.abort()))

            def kesfete_git():
                gs.goto(TABAN + "/index.html", wait_until="load", timeout=20000)
                gs.wait_for_timeout(900)
                gs.goto(TABAN + "/kesfet.html?il=06", wait_until="load", timeout=20000)
                gs.wait_for_timeout(2500)

            def panel_acik():
                return gs.evaluate(
                    "() => { const d=document.getElementById('detay'); "
                    "return !!(d && d.open); }")

            # (a) Panel acikken geri -> panel kapanir, SAYFA DEGISMEZ.
            kesfete_git()
            k = gs.query_selector(".kart")
            if not k:
                sorunlar.append("geri tusu kontrolu: kesfet hic kart cizmedi")
            else:
                k.click(); gs.wait_for_timeout(800)
                if not panel_acik():
                    sorunlar.append("geri tusu kontrolu: panel acilmadi")
                gs.go_back(); gs.wait_for_timeout(1200)
                if panel_acik():
                    sorunlar.append("geri tusu paneli kapatmiyor")
                if "kesfet.html" not in gs.url:
                    sorunlar.append("geri tusu paneli kapatmak yerine sayfadan "
                                    "cikiyor (%s)" % gs.url.split("/")[-1][:30])

                # (b) X ile kapatinca ARTIK KAYIT KALMAMALI: sonraki geri
                # basisi kesfetten cikarmali, "hicbir sey olmamali" degil.
                kesfete_git()
                gs.query_selector(".kart").click(); gs.wait_for_timeout(700)
                gs.query_selector("[data-kapat]").click(); gs.wait_for_timeout(700)
                gs.go_back(); gs.wait_for_timeout(1200)
                if "index.html" not in gs.url:
                    sorunlar.append("panel X ile kapandiktan sonra geri tusu "
                                    "sayfadan cikarmiyor; artik gecmis kaydi "
                                    "kalmis (%s)" % gs.url.split("/")[-1][:30])

                # (c) Tekrar tekrar ac-kapa gecmisi SISIRMEMELI.
                kesfete_git()
                for _ in range(3):
                    gs.query_selector(".kart").click(); gs.wait_for_timeout(450)
                    gs.keyboard.press("Escape"); gs.wait_for_timeout(450)
                gs.go_back(); gs.wait_for_timeout(1200)
                if "index.html" not in gs.url:
                    sorunlar.append("uc kez ac-kapa gecmisi sisiriyor (%s)"
                                    % gs.url.split("/")[-1][:30])
            geri_ctx.close()

            # 2w) PWA / TWA: service worker kaydoluyor mu ve CEVRIMDISI
            # ne oluyor. Google Play, cevrimdisiyken tarayicinin kendi
            # hata ekranini gostermeyi "bozuk islevsellik" sayiyor
            # (PLAY.md). Burasi o hali GERCEKTEN uretip bakiyor.
            #
            # AYRI BAGLAM: yukaridaki kontrollerin baglaminda service
            # worker KAPALI, cunku kayitli bir sw onlara onbellekten
            # yanit verip diskteki dosya yerine eski kopyayi sinatabilir.
            pwa_ctx = t.new_context()          # sw'ye izin var
            ps = pwa_ctx.new_page()
            ps.route("**://*/**", lambda r: (r.continue_()
                     if r.request.url.startswith(TABAN) else r.abort()))
            ps.goto(TABAN + "/index.html", wait_until="load", timeout=20000)
            ps.wait_for_timeout(2500)
            kayit = ps.evaluate("""async () => {
                const r = await navigator.serviceWorker.getRegistration();
                return r && r.active ? r.active.state : null;
            }""")
            if kayit != "activated":
                sorunlar.append("service worker etkinlesmedi (%s)" % kayit)

            # Bir il gezilsin ki veri onbellege girsin.
            ps.goto(TABAN + "/kesfet.html?il=06", wait_until="load", timeout=20000)
            ps.wait_for_timeout(3000)
            kovalar = ps.evaluate("async () => (await caches.keys())")
            if not any(k.endswith("-kabuk") for k in kovalar):
                sorunlar.append("kabuk onbellegi olusmadi (%s)" % kovalar)
            if not any(k.endswith("-veri") for k in kovalar):
                sorunlar.append("il verisi onbellege alinmadi (%s)" % kovalar)

            pwa_ctx.set_offline(True)
            # (a) HIC acilmamis sayfa -> cevrimdisi sayfasi, tarayici
            #     hata ekrani DEGIL.
            o1 = pwa_ctx.new_page()
            o1.goto(TABAN + "/gizlilik.html", wait_until="domcontentloaded", timeout=15000)
            o1.wait_for_timeout(1200)
            if "Bağlantı yok" not in (o1.title() or ""):
                sorunlar.append("cevrimdisi: acilmamis sayfada 'Bağlantı yok' "
                                "ekrani cikmiyor (%r)" % (o1.title() or "")[:40])
            # GERCEK cevrimdisi.html mi, yoksa sw.js icindeki ciplak
            # son care yaniti mi. Ikisinin de basligi ayni ve yalniz
            # baslige bakan bir kontrol, on yuklemenin bozuldugunu
            # goremezdi -- ilk yazimda tam olarak boyleydi ve sabotaj
            # testten gecti. Ayirt edici: "Tekrar dene" dugmesi.
            if not o1.query_selector("#tekrar"):
                sorunlar.append("cevrimdisi: cevrimdisi.html onbellekte yok; "
                                "sw.js'in ciplak yedegi cizilmis")
            o1.close()
            # (b) start_url cevrimdisi ACILMALI: TWA her acilista onu
            #     istiyor ve ilk kosumda ucak modunda olan biri
            #     "baglanti yok" gormemeli. sw.js onu ON YUKLUYOR.
            o2 = pwa_ctx.new_page()
            o2.goto(TABAN + "/index.html", wait_until="domcontentloaded", timeout=15000)
            o2.wait_for_timeout(1200)
            if "Bağlantı yok" in (o2.title() or ""):
                sorunlar.append("cevrimdisi: start_url acilmiyor; sw.js "
                                "index.html'i on yuklemiyor")
            o2.close()
            # (c) DAHA ONCE acilmis kesfet ekrani, veriyle birlikte
            #     gelmeli. Yalniz sayfanin acilmasi yetmez: kart sayisi
            #     sifirsa il dosyasi onbellekten gelmemis demektir.
            o3 = pwa_ctx.new_page()
            o3.goto(TABAN + "/kesfet.html?il=06", wait_until="domcontentloaded", timeout=15000)
            o3.wait_for_timeout(2500)
            kart = o3.eval_on_selector_all(".kart", "n => n.length")
            if kart == 0:
                sorunlar.append("cevrimdisi: gezilmis il hic kart cizmiyor "
                                "(veri onbellekten gelmiyor)")
            o3.close()
            pwa_ctx.set_offline(False)
            pwa_ctx.close()

            # 3) Harita VARKEN normal yol izlenmeli: erken donus olmamali.
            # GERCEK DOSYA KESILIYOR, yerine taklit konuyor. Taklit
            # acilista `window.L` kuruyor; gercek lib/leaflet.js sonradan
            # yuklenip UZERINE YAZIYORDU ve sayaclarin hicbiri dolmuyordu
            # -- kontrol "L.map hic cagrilmadi" diye HAKLI olarak bagirdi.
            sf, hata = sayfa_ac("/kesfet.html?il=06", LEAFLET_TAKLIT,
                                leafletsiz=True)
            cagri = set(sf.evaluate("window.__cagri || []"))
            kart2 = sf.eval_on_selector_all(".kart", "n => n.length")
            yedek2 = sf.eval_on_selector_all(".harita-yok", "n => n.length")
            for gerekli in ("map", "tileLayer", "layerGroup", "circleMarker"):
                if gerekli not in cagri:
                    sorunlar.append("Leaflet varken L.%s hic cagrilmadi" % gerekli)
            if yedek2:
                sorunlar.append("Leaflet varken 'harita yuklenemedi' kutusu cikiyor")
            if kart2 == 0:
                sorunlar.append("Leaflet varken kesfet hic kart cizmiyor")
            sf.close()
            t.close()

        if csp_ihlal:
            # Tekille: ayni ihlal her sayfada tekrar ediyor olabilir.
            for x in sorted(set(csp_ihlal))[:8]:
                sorunlar.append("CSP ihlali -- " + x)

        if sorunlar:
            for x in sorunlar:
                print("  HATA: " + x)
            return False
        print("kontrol gecti: %d sayfa JS hatasiz (gercek CSP altinda), "
              "%d girisli ekran cizildi, kesfet haritali ve haritasiz calisiyor"
              % (len(SAYFALAR), len(GIRISLI)))
        return True
    finally:
        sunucu.terminate()
        try:
            sunucu.wait(timeout=5)
        except Exception:
            sunucu.kill()


if __name__ == "__main__":
    s = kendini_kontrol_et()
    sys.exit(0 if s is not False else 1)
