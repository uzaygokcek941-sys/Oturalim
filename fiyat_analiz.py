# -*- coding: utf-8 -*-
"""Menu kalemlerini urun kategorisine ayirip fiyat olcutu cikarir.

Cikti: app/veri/fiyat_olcut.json  — "Ankara'da latte kac TL olmali" sorusunun
cevabi. Uygulama bunu kullanip bir mekani ucuz / normal / pahali isaretler.

Iki yontem karari:
1) Olcut, tum kalemlerin medyani DEGIL: once her mekanin kendi medyani, sonra
   o medyanlarin medyani. Aksi halde 749 pizza satirli tek bir zincir
   Turkiye'nin pizza fiyatini belirliyor.
2) Veri setindeki bazi "kafe"ler aslinda kahve satan e-ticaret dukkani
   (makine, fincan takimi, 500gr paket) ya da kiloyla satan borekci. Bunlar
   mekan duzeyinde tamamen eleniyor; kalem kalem ayiklamak yetmiyor.
"""
import csv, io, json, re, html, collections, statistics, os

KAYNAK = "tr_menu.csv"
CIKTI = "app/veri/fiyat_olcut.json"

# Sira onemli — ilk eslesen kazanir, ozelden genele.
# Sondaki [kg] / [td] Turkce SESSIZ YUMUSAMASI icin: borek -> boregi,
# tavuk -> tavugu, levrek -> levregi, balik -> baligi, simit -> simidi.
# Kok haliyle yazilan desen ekli hali kaciriyordu; veride olculdu, 22 gercek
# kalem ("Anne Boregi", "Akya baligi", "Deniz Levregi") siniflanamiyordu.
KURAL = [
    ("Türk kahvesi",   [r"turk kahve", r"menengic", r"dibek"], []),
    ("Matcha",         [r"matcha"], []),
    ("Espresso",       [r"espresso", r"macchiato", r"cortado"], [r"tonic"]),
    ("Latte",          [r"latte", r"flat white", r"cappuc", r"kapucino"], []),
    ("Americano",      [r"americano"], []),
    ("Filtre kahve",   [r"filtre kahve", r"chemex", r"french press", r"v60", r"cold brew"], []),
    ("Sıcak çikolata", [r"sicak cikolata", r"hot chocolate", r"salep"], []),
    ("Çay",            [r"\bcay\b", r"bitki cay", r"\bcayi\b"], [r"buzlu", r"\bice\b", r"fusetea"]),
    ("Su",             [r"^su$", r"^su ", r"kaynak suyu", r"\bsoda\b", r"maden suyu"], []),
    ("Ayran",          [r"ayran"], []),
    ("Kola / gazlı",   [r"coca.?cola", r"\bkola\b", r"fanta", r"sprite", r"pepsi", r"gazoz", r"7up"], []),
    ("Meyve suyu",     [r"meyve suyu", r"portakal suyu", r"limonata", r"fusetea", r"ice tea", r"buzlu cay"], []),
    ("Bira",           [r"\bbira\b", r"\befes\b", r"tuborg", r"\bbeer\b"], []),
    ("Şarap",          [r"\bsarap\b", r"\bwine\b", r"\broze\b"], []),
    ("Rakı / içkiler", [r"\braki\b", r"votka", r"viski", r"whisk", r"tekila", r"kokteyl", r"cocktail"], []),
    ("Pizza",          [r"pizza", r"pizzetta"], []),
    ("Burger",         [r"burger"], []),
    ("Döner / dürüm",  [r"doner", r"durum", r"iskender"], []),
    ("Lahmacun",       [r"lahmacun"], []),
    ("Pide",           [r"\bpide\b", r"pideli"], []),
    ("Kebap",          [r"kebap", r"kebab", r"adana", r"urfa", r"\bsis\b", r"beyti", r"kaburga"], []),
    ("Köfte",          [r"kofte"], []),
    # Malzeme degil YEMEK belirleyici: "Sehriyeli Tavuk Corbasi" bir corba.
    # Corba kurali asagida oldugu icin tavuk once esleşip ana yemek
    # sayiliyordu.
    ("Tavuk",          [r"tavu[kg]", r"chicken", r"kanat", r"nugget"], [r"corba"]),
    # \bhamsi\b sinirli: sinirsizken "Hamsikoy Sutlac" -- bir TATLI --
    # balik sayiliyordu. Yer adi malzeme sanildi ve balik pahali oldugu
    # icin mekanin fiyatini yukari cekiyordu.
    ("Balık",          [r"bali[kg]", r"levre[kg]", r"cipura", r"somon", r"\bhamsi\b",
                        r"kalamar"], [r"corba"]),
    # Marka adi jenerik kelimeyi YENER: "Algida Magnum Sandwich" bir
    # dondurma, tost degil. Dondurma kurali (asagida) bu satirdan sonra
    # geldigi icin "sandwich" once esleşiyordu; 96 subede tost sayildi.
    ("Tost / sandviç", [r"\btost\b", r"sandvic", r"sandwich", r"bagel"],
                       [r"algida", r"magnum", r"cornetto"]),
    ("Makarna",        [r"makarna", r"penne", r"spaghetti", r"fettuc", r"manti"], []),
    ("Çorba",          [r"corba"], []),
    ("Salata",         [r"salata", r"salad"], []),
    ("Kahvaltı",       [r"kahvalti", r"serpme", r"menemen", r"omlet", r"sahanda"], []),
    ("Patates",        [r"patates kizart", r"\bfries\b", r"parmak patates", r"\bpatates\b"], []),
    # \btatli: kategorinin adi "Tatli" olmasina ragmen kelimenin kendisi
    # kurallarda YOKTU. Ayva, kabak, incir, katmer, Hayrabolu, Mustafakemalpasa
    # tatlisi -- 11 gercek tatli siniflanamiyordu. Govdeye demirli (\b sonda
    # yok) cunku Turkce ek aliyor: "tatlisi", "tatlilar".
    ("Tatlı",          [r"sufle", r"kunefe", r"baklava", r"tiramisu", r"cheesecake", r"brownie",
                        r"waffle", r"\bpasta\b", r"magnolia", r"kazandibi", r"sutlac",
                        r"profiterol", r"\btatli"], []),
    ("Dondurma",       [r"dondurma", r"algida", r"magnum", r"cornetto"], []),
    ("Poğaça / börek", [r"pogaca", r"bore[kg]", r"\bacma\b", r"simi[td]", r"kruvasan",
                        r"croissant"], []),
]

# Porsiyon degil, urun: makine, fincan takimi, 500gr paket, kiloluk borek.
PERAKENDE = [
    r"canta", r"termos", r"bardak", r"fincan", r"hediye kart", r"\bkupa\b",
    r"\bmug\b", r"kavanoz", r"ogutucu", r"demlik", r"aparat", r"tisort",
    r"makine", r"takim", r"\bpot\b", r"filtre kagi", r"\bset\b",
    r"[\d,.]+\s*(g|gr|gram|kg)\b", r"\bposet\b", r"teneke", r"cekirdek", r"ogutulmus",
    r"\d+\s*adet\b",
]

# Kampanya/paket satiri tek urun fiyati degil.
PAKET = [r"alana \d", r"bedava", r"\bmenu\b", r"combo", r"firsat", r"kampanya",
         r"\d+.?l[iu]\b", r"paket", r"secili", r"\bseri\b", r"\bbox\b", r"\+"]

PERAKENDE_ESIK = 0.35   # bu orani asan mekan bir menu degil, bir katalog
# Menu kalemi sayilabilecek makul aralik (TL). TEK YERDE: app_veri.py bunu
# ice aktariyor. Onceden iki dosyada iki farkli deger vardi (5-3000 burada,
# 25-2000 orada) ve olcut, uygulamanin GOSTERMEDIGI kalemlerden hesaplaniyordu:
# 12,55 TL'lik bir "Pizza margherita" markanin medyani olup Turkiye pizza
# bandini bozuyordu. Olculdu, hizalayinca bant 1,03 -> 0,19'a indi ve hicbir
# kategori kaybedilmedi.
TABAN, TAVAN = 25.0, 2000.0
EN_AZ_MEKAN = 3         # olcut icin gereken en az mekan sayisi

# Turkce harfleri sadelestir: kaynak veride hem "cay" hem "çay" gecebiliyor,
# kurallari tek bicimde yazabilmek icin normalize ediyoruz.
CEVIR = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def temizle(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def sadelestir(s):
    return s.lower().translate(CEVIR)


def eslesir(desenler, metin):
    return any(re.search(d, metin) for d in desenler)


def _kural_ara(d):
    """Sadelestirilmis ada uyan ilk KURAL kategorisi, yoksa None."""
    for kat, var, yok in KURAL:
        if eslesir(var, d) and not (yok and eslesir(yok, d)):
            return kat
    return None


def kategorile(ad):
    if ad.count(",") >= 3:
        return None, "malzeme listesi"
    d = sadelestir(ad)
    if eslesir(PERAKENDE, d):
        return None, "perakende urun"
    if eslesir(PAKET, d):
        return None, "paket/kampanya"
    kat = _kural_ara(d)
    return (kat, None) if kat else (None, "siniflanamadi")


def yiyecek_mi(ad):
    """Ad bir yiyecek/icecek turune benziyor mu? Uyan kategoriyi dondurur.

    kategorile()'den TEK farki: perakende ve paket kapilarini atlar. Cunku
    o iki kapi "bu fiyat porsiyon fiyati mi" sorusunun cevabi, "bu bir yemek
    mi" sorusunun degil. "1 KG Kol Boregi" porsiyon degildir ama boregin ta
    kendisidir; "Kucuk Boy Pizza + Patates + Pepsi" tek urun fiyati degildir
    ama pizzadir.

    Kullanildigi yer app_veri.menu_mu(): 33 kategori Turkiye'deki bir kafe ya
    da restoran menusunun kelime dagarcigini kapsiyor. Bir listenin HICBIR
    kalemi bu 33'ten birine uymuyorsa, o liste bir menu degildir -- oyle
    listeler olculdu ve icleri kitap, pil, muzayede, sinema seansi ve
    kamp konaklama fiyati cikti.
    """
    return _kural_ara(sadelestir(ad))


# Sube/tur eki: "Domino's Pizza Beytepe" ile "Domino's" ayni marka sayilmali.
SUBE_KELIMESI = {"pizza", "coffee", "cafe", "kafe", "restoran", "restaurant",
                 "kahve", "sube", "bostanci", "kizilay", "beytepe", "gorukle",
                 "sumer", "kirkagac", "and", "more"}


def marka(ad):
    """Sube adini kirpip zincirin cekirdek adini dondurur."""
    kelimeler = sadelestir(ad).split()
    cekirdek = []
    for k in kelimeler:
        if k.strip("&") in SUBE_KELIMESI:
            break
        cekirdek.append(k)
    return " ".join(cekirdek) or sadelestir(ad).strip()


def ozet(liste):
    liste = sorted(liste)
    n = len(liste)
    return {"kaynak": n,
            "medyan": round(statistics.median(liste)),
            "alt": round(liste[n // 4]),
            "ust": round(liste[(3 * n) // 4]) if n > 1 else round(liste[-1])}


def main():
    ham = list(csv.DictReader(io.open(KAYNAK, encoding="utf-8-sig")))

    # 0. adim: perakende dukkanlarini mekan duzeyinde ele
    toplam, perakende = collections.Counter(), collections.Counter()
    for x in ham:
        m = (x["mekan"], x["il"])
        toplam[m] += 1
        if eslesir(PERAKENDE, sadelestir(temizle(x["kalem"]))):
            perakende[m] += 1
    kara = {m for m in toplam
            if toplam[m] >= 5 and perakende[m] / toplam[m] >= PERAKENDE_ESIK}
    print("Perakende dukkani sayilip elenen mekan: %d" % len(kara))
    for m in sorted(kara, key=lambda a: -toplam[a]):
        print("   - %-32s %-10s %d/%d kalem" % (m[0][:32], m[1], perakende[m], toplam[m]))
    print()

    sayac = collections.Counter()
    kova = collections.defaultdict(list)
    mekan_ili = {}
    for x in ham:
        mekan = (x["mekan"], x["il"])
        if mekan in kara:
            sayac["perakende mekan"] += 1
            continue
        try:
            fiyat = float(x["fiyat"])
        except (ValueError, TypeError):
            sayac["fiyat okunamadi"] += 1
            continue
        if not (TABAN <= fiyat <= TAVAN):
            sayac["fiyat araligin disi"] += 1
            continue
        kat, sebep = kategorile(temizle(x["kalem"]))
        if kat is None:
            sayac[sebep] += 1
            continue
        sayac["siniflandi"] += 1
        mekan_ili[mekan] = x["il"]
        kova[(kat, mekan)].append(fiyat)

    il_medyan = collections.defaultdict(list)
    # Ulke olcutu MARKA bazinda: Domino's 10 ilde ayri mekan olarak sayilirsa
    # 10 oy kullaniyor ve Turkiye'nin pizza fiyati Domino's oluyor.
    marka_medyan = collections.defaultdict(list)
    for (kat, mekan), fiyatlar in kova.items():
        m = statistics.median(fiyatlar)
        il_medyan[(kat, mekan_ili[mekan])].append(m)
        marka_medyan[(kat, marka(mekan[0]))].append(m)

    ulke_medyan = collections.defaultdict(list)
    for (kat, _mk), liste in marka_medyan.items():
        ulke_medyan[kat].append(statistics.median(liste))

    cikti = {"turkiye": {}, "il": {}}
    for kat, liste in ulke_medyan.items():
        if len(liste) >= EN_AZ_MEKAN:
            cikti["turkiye"][kat] = ozet(liste)
    for (kat, il), liste in il_medyan.items():
        if len(liste) >= EN_AZ_MEKAN:
            cikti["il"].setdefault(il, {})[kat] = ozet(liste)

    os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
    with io.open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=1)

    print("HAM %d kalem" % len(ham))
    for k, v in sayac.most_common():
        print("  %-22s %5d" % (k, v))
    print()
    print("TURKIYE OLCUTU  (mekan medyanlarinin medyani, TL)")
    print("  %-16s %5s %6s %7s %6s" % ("kategori", "marka", "alt", "MEDYAN", "ust"))
    for kat, o in sorted(cikti["turkiye"].items(), key=lambda a: a[1]["medyan"]):
        print("  %-16s %5d %6d %7d %6d" % (kat, o["kaynak"], o["alt"], o["medyan"], o["ust"]))
    print()
    print("IL BAZLI olcut cikan il: %d" % len(cikti["il"]))
    for il, kats in sorted(cikti["il"].items(), key=lambda a: -len(a[1])):
        print("  %-12s %2d kategori" % (il, len(kats)))
    print()
    print("-> " + CIKTI)


def kendini_kontrol_et():
    """python fiyat_analiz.py test  -> siniflandirma kurallarini dogrular."""
    ornekler = [
        # (kalem adi, beklenen kategori)
        ("Cafe Latte", "Latte"),
        ("BADEMLI MATCHA LATTE (S)", "Matcha"),          # matcha, latte'den once
        ("Turk Kahvesi", "Türk kahvesi"),
        ("Adana Kebap", "Kebap"),
        ("Guatemala Filtre Kahve Kilitli 250g", None),   # 250g paket = perakende
        ("Moccamaster Filtre Kahve Makinesi", None),     # makine
        ("Julius Meinl Espresso Bardak 6 ADET", None),   # 6 adet + bardak
        ("Sucuk , Misir , Mozarella Peyniri , Pizza Sos", None),  # malzeme listesi
        ("1 Alana 1 Bedava Citir Tavuk", None),          # kampanya
        ("Buyuk Boy Pizza + Tatli + Coca-Cola", None),   # paket
        ("Ayran", "Ayran"),
        ("Su", "Su"),
        ("Buzlu Cay", "Meyve suyu"),                     # cay degil, ice tea
        ("Coca-Cola 330 ML", "Kola / gazlı"),
        # --- kural sirasindan dogan uc gercek hata; veride olculdu ---
        # Marka adi jenerik kelimeyi yener: dondurma, tost degil.
        ("Algida Magnum Sandwich", "Dondurma"),
        ("Magnum Mini Sandwich Badem", "Dondurma"),
        ("Sucuklu Kasarli Tost", "Tost / sandviç"),      # gercek tost bozulmadi
        # Yemek belirleyici malzemeyi yener: corba, corbadir.
        ("Sehriyeli Tavuk Corbasi", "Çorba"),
        ("Balik Corbasi", "Çorba"),
        ("Tavuk Sis Porsiyon", "Kebap"),                 # gercek ana yemek bozulmadi
        # Yer adi malzeme sanilmasin: Hamsikoy sutlaci bir TATLI.
        ("Findikli Hamsikoy Sutlac", "Tatlı"),
        ("Hamsi Tava", "Balık"),                         # gercek balik bozulmadi
        # Kategorinin adi kuralda yoktu: 11 gercek tatli siniflanamiyordu.
        ("Ayva Tatlisi", "Tatlı"),
        ("Mustafakemalpasa Peynir Tatlisi", "Tatlı"),
        ("Kabak Tatlisi", "Tatlı"),
        ("Tatli Patates Kizartmasi", "Patates"),          # sifat, tatli degil
        # Sessiz yumusamasi: ekli hal de eslesmeli.
        ("Anne Boregi", "Poğaça / börek"),
        ("Akya baligi", "Balık"),
        ("Deniz Levregi", "Balık"),
        ("Cerkez Tavugu", "Tavuk"),
        ("Susamli Simidi", "Poğaça / börek"),
        ("Sucuklu Pogaca", "Poğaça / börek"),             # kok hali bozulmadi
        ("Hamsi Tava", "Balık"),
    ]
    hata = 0
    for ad, beklenen in ornekler:
        cikan = kategorile(ad)[0]
        if cikan != beklenen:
            print("  HATA: %-45s bekleniyordu=%s cikan=%s" % (ad, beklenen, cikan))
            hata += 1

    # yiyecek_mi: perakende ve paket kapilarini ATLAR, KURAL'i uygular.
    # menu_degil_mi() bu ayrima dayaniyor -- bozulursa gercek menuler duser.
    for ad, bekle in [
        ("1 KG KIYMALI KOL BOREGI", True),      # porsiyon degil ama borek
        ("Kucuk Boy Pizza + Patates + Pepsi", True),   # tek urun degil ama pizza
        ("Filtre Kahve 250 gr", True),          # perakende ama kahve
        ("Adana Kebap", True),
        ("Roxy AA Alkaline Pil", False),        # pil
        ("Raisa Drop Earrings", False),         # kupe
        ("Cadirla Konaklama", False),           # kamp
        ("Hafta Ici", False),                   # mekan kirasi
        ("PRAML, SABINE", False),               # kitap
    ]:
        if bool(yiyecek_mi(ad)) != bekle:
            print("  HATA: yiyecek_mi(%r)=%r, %r bekleniyordu"
                  % (ad, yiyecek_mi(ad), bekle))
            hata += 1
        # yiyecek_mi eslesiyorsa kategorile de ya ayni kategoriyi ya da bir
        # KAPI sebebi dondurmeli; "siniflanamadi" ikisinde de olmamali.
        if yiyecek_mi(ad):
            kat, sebep = kategorile(ad)
            if sebep == "siniflanamadi":
                print("  HATA: %r yiyecek ama siniflanamadi" % ad)
                hata += 1
    # marka(): sube adi kirpilmali
    assert marka("Domino's Pizza Beytepe") == marka("Domino's"), marka("Domino's Pizza Beytepe")
    assert marka("Veganarsist Kizilay") == marka("Veganarsist")
    print("kontrol: %d/%d gecti" % (len(ornekler) - hata, len(ornekler)))
    return hata == 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.exit(0 if kendini_kontrol_et() else 1)
    main()
