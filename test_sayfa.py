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
import subprocess
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

# GPS ve cihaz bilgisi tasiyan GERCEK bir EXIF blogu (APP1). Elle
# kuruldu; hazir bir fotograf koymak depoya ikili dosya sokardi.
EXIF_BLOK = base64.b64decode(
    "/+EAfUV4aWYAAElJKgAIAAAAAAMPAQIADQAAADIAAAAQAQIADQAAADIAAAAliAQAAQAAAD8AAAAAAAAAT3R1cmFsaW1UZXN0AAIAAQACAAIAAABOAAAAAgAFAAMAAABdAAAAAAAAACkAAAABAAAAAQAAAAEAAAAAAAAAAQAAAA==")

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
    /* Biri kalem, biri YALNIZ fotograf: ikisi de cizilmeli. */
    mekan_menu_katkilari: () => ({ data: [
      { id: 1, urun: "Latte", fiyat: 95, foto: null,
        olusturuldu: "2026-08-22T12:00:00Z" },
      { id: 2, urun: null, fiyat: null, foto: "kul-1/1.jpg",
        olusturuldu: "2026-08-21T12:00:00Z" }], error: null }),
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
  ("hesabim.html/isletmeler", "/hesabim.html", '[data-bolum="isletmeler"]',
   ["Sahip Kafe", "doğrulanmış"], ["Yükleniyor", "kul-1"]),
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
  ("isletme.html/yorumlar", "/isletme.html?il=34&id=node/8223784325", None,
   ["Yorumlar", "Deneme Kisi", "28 · Öğretmen", "Sessiz ve ucuz",
    "Bir kullanıcı", "4,0"], ["kul-1"]),
  ("profil.html", "/profil.html?k=deneme_kisi", None,
   ["Deneme Kisi", "@deneme_kisi", "28 · Öğretmen", "Yorum Kafe"],
   ["Yükleniyor", "kul-1", "Profil bulunamadı"]),
  # Yonetim: yorum kuyrugu da cizilmeli.
  ("yonetim.html/yorumlar", "/yonetim.html", None,
   ["Yorumlar", "Yorum Kafe", "Sessiz ve ucuz"], ["kul-1"]),
  ("yonetim.html/menu", "/yonetim.html", None,
   ["Menü katkıları", "Menu Kafe", "Latte"], ["kul-1"]),
  # Isletme sayfasi: kalem ve fotograf ayri ayri cizilmeli.
  ("isletme.html/menu", "/isletme.html?il=34&id=node/8223784325", None,
   ["Kullanıcıların eklediği fiyatlar", "Latte", "Menüyü görüyor musun"],
   ["kul-1"]),
]

SAYFALAR = ["/index.html", "/kesfet.html", "/kesfet.html?il=34&tur=Kafe&butce=300",
            "/isletme.html?il=34&id=node/8223784325", "/isletme.html?il=34&id=yok",
            "/paylas.html", "/giris.html", "/hesabim.html", "/yonetim.html",
            "/hakkinda.html", "/gizlilik.html",
            # Profil: hem gecerli hem OLMAYAN kullanici adi. Ikincisi
            # "bulunamadi" ekranini cizmeli, catmamali.
            "/profil.html?k=deneme_kisi", "/profil.html?k=yok_boyle_biri",
            "/profil.html"]


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

            def sayfa_ac(yolu, taklit=None, sahte_modul=False):
                sf = t.new_page()
                hata = []
                sf.on("pageerror", lambda e: hata.append(str(e)[:120]))
                if taklit:
                    sf.add_init_script(taklit)
                # Dis baglantilarin hepsi kapali: kontrol ag'a bagli olmasin
                # ve ZOR hal sinansin. Tek istisna, istenirse supabase-js:
                # onun yerine yerel bir taklit MODUL donuyor, boylece
                # girisli hal de sinanabiliyor.
                def yonlendir(r):
                    u = r.request.url
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
            tel = t.new_page(viewport={"width": 390, "height": 844},
                             is_mobile=True, has_touch=True)
            tel.route("**://*/**", lambda r: (r.continue_()
                      if r.request.url.startswith(TABAN) else r.abort()))
            for yolu in ("/index.html", "/kesfet.html?il=34", "/paylas.html",
                         "/giris.html", "/isletme.html?il=34&id=node/8223784325"):
                tel.goto(TABAN + yolu, wait_until="domcontentloaded", timeout=20000)
                tel.wait_for_timeout(2200)
                kucuk = tel.evaluate("""() => [...document.querySelectorAll(
                    'button, input:not([type=hidden]), select, textarea,'
                    + ' [role=tab], a.dugme, a.cip')]
                  .filter(e => e.getClientRects().length > 0)
                  .map(e => { const r = e.getBoundingClientRect();
                    return { ad: e.tagName.toLowerCase() + '.'
                                 + String(e.className || '').split(' ')[0],
                             g: Math.round(r.width), y: Math.round(r.height) }; })
                  .filter(x => x.y < 24 || x.g < 24)""")
                for x in kucuk:
                    sorunlar.append("%s: %s dokunma hedefi %dx%d (en az 24x24)"
                                    % (yolu, x["ad"], x["g"], x["y"]))
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
            exif = sf.evaluate("""async (exifDizi) => {
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
                oncesiCihaz:  oncesi.includes("OturalimTest"),
                sonrasiExif:  sonrasi.includes("Exif"),
                sonrasiCihaz: sonrasi.includes("OturalimTest"),
                tur: hazir.type, boyut: hazir.size
              };
            }""", list(EXIF_BLOK))
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

            # 1f) Gorunmeyen sahne icin kare uretilmemeli.
            #
            # Kaydirinca gozlemci animasyonu durduruyordu, ama
            # visibilitychange KOSULSUZ baslat() cagiriyordu: baska sekmeye
            # gecip geri donunce, sahne hala ekran disindayken animasyon tam
            # hizda yeniden basliyor ve bir daha durmuyordu (gozlemci ancak
            # kesisim DEGISINCE tetikleniyor). Olculdu: 600 ms'de 36 kare.
            # Telefonda bu dogrudan pil.
            #
            # Dort halin dordu de olculuyor. Yalniz "0 kare" aramak yanlis
            # gecerdi: animasyonu tamamen kapatmak da o kontrolu yesil yapar.
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

            if kare() == 0:
                sorunlar.append("sahne ekrandayken hic kare uretilmiyor")
            sekmeden_don()
            if kare() == 0:
                sorunlar.append("sahne ekrandayken sekmeden donunce baslamiyor")
            sf.evaluate("scrollTo(0, 3000)")
            sf.wait_for_timeout(500)
            if kare() != 0:
                sorunlar.append("sahne ekran disindayken kare uretiliyor")
            sekmeden_don()
            if kare() != 0:
                sorunlar.append("sahne ekran disinda, sekmeden donunce yeniden basliyor")
            sf.evaluate("scrollTo(0, 0)")
            sf.wait_for_timeout(500)
            if kare() == 0:
                sorunlar.append("sahne geri kaydirilinca yeniden baslamiyor")
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
            sf, _ = sayfa_ac("/hesabim.html", GIRIS_TAKLIT, sahte_modul=True)
            sf.wait_for_timeout(1000)
            d = sf.query_selector('[data-bolum="isletmeler"]')
            if d:
                d.click(); sf.wait_for_timeout(800)
            b2 = sf.query_selector("#bolum-isletmeler [data-birak]")
            if not b2:
                sorunlar.append("hesabim.html: sahipligi birak dugmesi yok")
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
            sf = t.new_page()
            sf.route("**://*/**", lambda r: (
                r.fulfill(status=200, headers={"content-type": "text/javascript"},
                          body="window.OTURALIM={supabaseUrl:'',supabaseAnahtar:''};")
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
            sf = t.new_page()
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

            # 2) Harita YOKKEN kesfet calismali. Asil bulunan hata buydu.
            sf, hata = sayfa_ac("/kesfet.html?il=06")
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

            # 3) Harita VARKEN normal yol izlenmeli: erken donus olmamali.
            sf, hata = sayfa_ac("/kesfet.html?il=06", LEAFLET_TAKLIT)
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

        if sorunlar:
            for x in sorunlar:
                print("  HATA: " + x)
            return False
        print("kontrol gecti: %d sayfa JS hatasiz, %d girisli ekran cizildi, "
              "kesfet haritali ve haritasiz calisiyor"
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
