# -*- coding: utf-8 -*-
"""Saha kartlari — Faz 3.

sahiplen.py yuruyus kumelerini uretiyor; bu betik o kumelerden secilenler
icin KAPIYA BIRAKILACAK karti basiyor. Kartin uzerinde mekana ozel bir QR
ve tek kullanimlik bir sahiplenme kodu var (Faz 4).

    python saha.py cebimde.vercel.app             # en degerli 3 kume
    python saha.py cebimde.vercel.app --kume 5
    python saha.py cebimde.vercel.app --il Ankara --kume 2
    python saha.py cebimde.vercel.app --il Ankara --atla 1 --kume 1  # ikinci kume
    python saha.py cebimde.vercel.app --il Ankara --bayi 3 --parti ankara-eylul
    python saha.py sql saha_liste.csv --bayi 1     # basilmis partiyi bayiye bagla
    python saha.py olc                             # dagitim sonrasi olcum
    python saha.py test

BAYI (istege bagli). --bayi verilirse basilan PARTI o bayiye baglaniyor:
uretilen SQL sahiplenme_kodu satirlarina bayi ve parti yaziyor, isletme
kodu kullandiginda hakedis KENDILIGINDEN dusuyor (veritabani/bayilik.sql).
Bayi "su kadar yere ugradim" demiyor; olculen sey kartin kendisi.
--bayi verilmezse eski davranis aynen suruyor, kartlar bayisiz basiliyor.

ALAN ADI DISARIDAN VERILIYOR, sabit degil. site_haritasi.py ile ayni
gerekce: QR mutlak adres istiyor ve depoda gercek alan adi yazili degil.
Uydurulmus bir alan adiyla basilmis kart, basilmamis karttan kotudur --
tarandiginda hicbir yere gitmez ve isletme bir daha denemez.

UZERINE YAZMIYOR. Ucu de SABIT ada yaziliyor ve ikinci parti birincinin
uzerine biniyordu -- yani hangi kodun hangi kapiya gittigini gosteren TEK
kayit siliniyordu. Dagitilmis bir kart geri alinamiyor, o kayit da geri
gelmiyor. Betik artik var olan ciktiyi gorunce duruyor ve ne yapilacagini
soyluyor; bilerek isteniyorsa --ustune-yaz.

UC CIKTI, UCU DE .gitignore'DA:
  saha_kartlar.html   yazdirilacak kartlar (A4, sayfa basina 4)
  saha_kodlar.sql     Supabase'e yapistirilacak kod OZETLERI
  saha_liste.csv      ziyaret listesi (kod dahil), sahada isaretlenecek

DUZ KOD YALNIZ KARTTA VE CSV'DE. Veritabanina yalniz sha256 ozeti gidiyor;
kodun kendisi hicbir yerde saklanmiyor. saha_liste.csv duz kodu tasiyor
cunku sahada hangi karti kime verdigini bilmen gerekiyor -- o dosya da
depoya girmiyor.
"""
import argparse
import collections
import csv
import glob
import hashlib
import html
import io
import os
import secrets
import sys

import veri_bicim   # il dosyasi bicimi tek yerde

KUME_CSV = "sahiplenme_kume.csv"
KART_CIKTI = "saha_kartlar.html"
SQL_CIKTI = "saha_kodlar.sql"
LISTE_CIKTI = "saha_liste.csv"

# Karisabilecek harfler YOK: I/1, O/0, S/5, Z/2 elendi. Kart elle de
# okunabilmeli -- QR taranmazsa kullanici kodu yazacak.
KOD_ALFABE = "ABCDEFGHJKLMNPQRTUVWXY3456789"
KOD_UZUNLUK = 8

# Kartin gecerlilik suresi. sahiplenme.sql'deki varsayilan da 180 gun;
# ikisi ayrisirsa kart "gecerli" gorunup sunucuda reddedilir.
GECERLILIK_GUN = 180


def kod_uret():
    """Tahmin edilemez kod. secrets, random DEGIL: random tohumdan
    turetilebilir ve bu kod bir yetki anahtari."""
    return "".join(secrets.choice(KOD_ALFABE) for _ in range(KOD_UZUNLUK))


def ozet(kod):
    """Veritabanina giden deger. sahiplenme_kodu_kullan() ile AYNI
    normalizasyon: buyuk harf, harf-rakam disi her sey atiliyor."""
    temiz = "".join(c for c in kod.upper() if c.isalnum())
    return hashlib.sha256(temiz.encode("ascii")).hexdigest()


def _guncel_kimlikler():
    """app/veri'deki butun mekan kimlikleri."""
    import json
    import re as _re
    kimlik = set()
    for yol in glob.glob(os.path.join("app", "veri", "*.json")):
        if not _re.search(r"[\\/]\d\d\.json$", yol):
            continue
        with io.open(yol, encoding="utf-8") as f:
            for m in veri_bicim.coz(json.load(f))["mekanlar"]:
                kimlik.add(m["id"])
    return kimlik


def kumeleri_oku(yol=KUME_CSV, il=None):
    if not os.path.exists(yol):
        sys.exit("%s yok. Once 'python sahiplen.py' calistir." % yol)
    kume = collections.defaultdict(list)
    yok = 0
    disarida = 0
    guncel = _guncel_kimlikler()
    with io.open(yol, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            _, mekan_id = mekan_kimligi(r["sayfa"])
            # BAYAT CSV KORUMASI. Kume dosyasi veriden ONCE uretilmis
            # olabilir; o zaman icinde artik var olmayan mekanlar bulunur
            # (ornegin kopya kayit birlestirmesinde dusenler). Onlar icin
            # basilan kart QR'i olu bir sayfaya gider ve bunu ancak sahada
            # fark ederiz. Bir kez oldu: elimdeki dosya veri
            # yenilenmeden onceydi.
            if guncel and mekan_id not in guncel:
                yok += 1
                continue
            # IL SUZGECI. Kumeler butun Turkiye icin uretiliyor ve en
            # degerli 20 kumenin cogu Istanbul; oysa kart basan kisi
            # yalnizca kendi sehrinde yuruyebiliyor. Suzgec olmadan
            # "Ankara icin kart bas" diye bir sey yok, tek yol elle
            # kume numarasi aramak.
            if il and r["il"] != il:
                disarida += 1
                continue
            kume[r["kume"]].append(r)
    if yok:
        oran = 100.0 * yok / (yok + sum(len(v) for v in kume.values()))
        print("UYARI: %s icindeki %d kayit (%.1f%%) artik veride yok, atlandi."
              % (yol, yok, oran))
        if oran > 5:
            sys.exit("Kume dosyasi bayat gorunuyor. 'python sahiplen.py' calistir.")
    if il and not kume:
        sys.exit("'%s' icin kume yok. Il adi kume dosyasindaki gibi, TURKCE "
                 "harflerle yazilmali: Ankara, \u0130zmir, \u0130stanbul." % il)
    if il:
        print("il suzgeci '%s': %d kayit disarida kaldi, %d kume kaldi"
              % (il, disarida, len(kume)))
    return kume


def sec(kumeler, adet, atla=0):
    """Ilk N kume, NUMARA SIRASIYLA.

    Burada yeniden siralama YAPILMIYOR: sahiplen.py kumeleri zaten
    degerine gore diziyor (uyelerin eksik bilgi toplamina gore) ve 1'den
    baslayarak numaraliyor. Kume 1 = en degerli yuruyus.

    Ilk yazimda burada "en cok uyesi olan" diye ikinci bir tanim vardi ve
    farkli bir sonuc veriyordu: boyuta gore 1, 3, 2; degere gore 1, 2, 3.
    Ayni kavramin iki tanimi, ikisinin ayrismasi demek. Tanim sahiplen.py'de
    kalsin.

    ATLA, ikinci partiyi basmak icin. --kume 2 birinci VE ikinci kumeyi
    birlikte basiyor; ilk kume zaten dagitilmissa bu, ayni mekanlar icin
    IKINCI bir gecerli kod uretmek demek. --atla 1 --kume 1 yalniz ikinci
    kumeyi veriyor."""
    sirali = sorted(kumeler.items(), key=lambda kv: int(kv[0]))
    return sirali[atla:atla + adet]


def _oz(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def kart_html(taban, kayitlar):
    """A4'e 4 kart. Yazdirma icin: renk yok, kenarlik var, kesim kolay."""
    kartlar = []
    for r in kayitlar:
        sayfa = r["sayfa"]
        if not sayfa.startswith("/"):
            sayfa = "/" + sayfa
        url = taban + sayfa + "&kod=" + r["kod"]
        kartlar.append(
            '<article class="kart">'
            '<header><b>%s</b><span>%s · %s</span></header>'
            '<p class="eksik">Sizde eksik görünen: <b>%s</b></p>'
            '<div class="alt"><div class="qr">%s</div>'
            '<div class="kod"><span>Sayfanızı sahiplenme kodu</span>'
            '<b>%s</b><small>%s</small></div></div>'
            '</article>'
            % (html.escape(_oz(r["ad"], 42)),
               html.escape(r["tur"]), html.escape(r["il"]),
               html.escape(_oz(r["sor"], 110)),
               qr_svg(url),
               html.escape(r["kod"]),
               html.escape(taban.replace("https://", ""))))

    return """<!doctype html>
<meta charset="utf-8">
<title>Cebimde — saha kartları</title>
<style>
  @page { size: A4; margin: 12mm; }
  *{box-sizing:border-box}
  body{font:14px/1.45 system-ui,"Segoe UI",Roboto,sans-serif;margin:0;color:#111}
  .sayfa{display:grid;grid-template-columns:1fr 1fr;gap:6mm;
         page-break-after:always}
  .sayfa:last-child{page-break-after:auto}
  .kart{border:1px dashed #999;border-radius:3mm;padding:5mm;
        height:62mm;display:flex;flex-direction:column;justify-content:space-between}
  .kart header b{display:block;font-size:16px;line-height:1.25}
  .kart header span{font-size:11px;color:#666;letter-spacing:.04em;text-transform:uppercase}
  .eksik{margin:2mm 0;font-size:11.5px;color:#333}
  .eksik b{font-weight:600}
  .alt{display:flex;gap:4mm;align-items:flex-end}
  .qr svg{width:26mm;height:26mm;display:block}
  .kod{flex:1;min-width:0}
  .kod span{display:block;font-size:10px;color:#666;text-transform:uppercase;letter-spacing:.06em}
  .kod b{display:block;font:600 20px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;
         letter-spacing:.14em;margin:1mm 0}
  .kod small{font-size:10px;color:#666}
  .not{font-size:11px;color:#555;margin:0 0 5mm}
  @media print{ .not{display:none} }
</style>
<p class="not">Kesikli çizgilerden kesin. Her kart tek bir işletmeye ait —
kodlar farklı, karıştırmayın.</p>
%s
""" % "\n".join(
        '<section class="sayfa">%s</section>' % "".join(kartlar[i:i + 4])
        for i in range(0, len(kartlar), 4))


def qr_svg(veri):
    """QR'i kutuphane uretiyor. Reed-Solomon'u elle yazmak, sahada
    taranmayan bir karti ancak basildiktan SONRA fark etmek demekti."""
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
    except ImportError:
        sys.exit("qrcode gerekli: pip install qrcode")
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                      border=1)
    q.add_data(veri)
    q.make(fit=True)
    tampon = io.BytesIO()
    q.make_image(image_factory=SvgPathImage).save(tampon)
    ham = tampon.getvalue().decode("utf-8")
    # Kendi <?xml?> basligini ve mm olculerini atiyoruz: SVG sayfaya
    # gomuluyor, boyutu CSS veriyor.
    ham = ham[ham.index("<svg"):]
    return ham.replace('width="', 'data-w="', 1).replace('height="', 'data-h="', 1)


def sql_uret(kayitlar, bayi=None, parti=None):
    """Kod ozetleri + (varsa) parti sahibi bayi.

    BAYI SUTUNU YALNIZ ISTENDIGINDE yaziliyor. Sutun bayilik.sql ile
    geliyor; her zaman yazsaydik bayilik kurulmamis bir projede bu betik
    "column bayi does not exist" ile patlardi ve kartlar basilmis olurdu.
    Kart basilip SQL'i calismayan bir parti, dagitildiginda hicbir kodu
    kabul etmez -- basilmamis karttan kotu."""
    bayi_var = bayi is not None
    satirlar = [
        "-- Cebimde — saha kodlari (saha.py uretti)",
        "-- Supabase SQL Editor'e yapistirip BIR KEZ calistir.",
        "--",
        "-- Burada KODUN KENDISI YOK, yalniz sha256 ozeti. Kodlar",
        "-- saha_kartlar.html ve saha_liste.csv icinde; ikisi de depoya girmiyor.",
        "-- Bu dosyayi calistirmadan kart dagitirsan kodlar calismaz.",
    ]
    if bayi_var:
        satirlar += [
            "--",
            "-- PARTI SAHIBI: bayi #%d, parti '%s'. Bu iki sutun"
            % (bayi, parti or ""),
            "-- veritabani/bayilik.sql ile geliyor; o dosya calistirilmadan",
            "-- burasi 'column \"bayi\" does not exist' der ve HICBIR kod",
            "-- yazilmaz (islem tek parca). Kartlari dagitmadan once kos.",
        ]
    sutun = "kod_ozeti, mekan_id, il, mekan_ad, gecerlilik"
    if bayi_var:
        sutun += ", bayi, parti"
    satirlar += [
        "",
        "insert into public.sahiplenme_kodu",
        "  (%s) values" % sutun,
    ]
    govde = []
    for r in kayitlar:
        deger = ("  ('%s', '%s', '%s', '%s', current_date + %d"
                 % (ozet(r["kod"]),
                    r["mekan_id"].replace("'", "''"),
                    r["il_kodu"].replace("'", "''"),
                    r["ad"].replace("'", "''")[:200],
                    GECERLILIK_GUN))
        if bayi_var:
            deger += ", %d, '%s'" % (bayi, (parti or "").replace("'", "''"))
        govde.append(deger + ")")
    satirlar.append(",\n".join(govde))
    if bayi_var:
        # BAYISIZ HALDE 'do nothing' DOGRU, BAYILI HALDE DEGILDI.
        # Yasandi: 51 ve 52. partiler once bayisiz basildi ve SQL'leri
        # calistirildi. Sonra ayni partiler bayiye baglanip yeniden
        # uretildi -- ama kod_ozeti birincil anahtar ve KODLAR AYNI, yani
        # 'do nothing' ikinci calistirmayi tamamen yutuyordu: 64 kod
        # yerinde duruyor, bayi sutunu bos ve hicbir hata yok. Tam olarak
        # bu depoda tekrar tekrar kapattigimiz sey -- basarisizligi
        # goremeyen kapi.
        #
        # Guncelleme YALNIZ iki sutuna dokunuyor. mekan_id, gecerlilik,
        # kullanildi ve kullanan disarida: bir kartin hangi mekana ait
        # oldugu ya da kullanilip kullanilmadigi bu dosyayla degismemeli.
        #
        # KULLANILMIS KART DISARIDA. Kod kullanildiysa hakedis o an
        # dogmus ve tutari donmus (bayilik.sql). Atfi sonradan baska bir
        # bayiye tasimak, kapanmis bir hesabi geriye donuk yeniden
        # yazmak olurdu.
        satirlar.append("on conflict (kod_ozeti) do update")
        satirlar.append("   set bayi = excluded.bayi, parti = excluded.parti")
        satirlar.append(" where public.sahiplenme_kodu.kullanildi is null;")
    else:
        satirlar.append("on conflict (kod_ozeti) do nothing;")
    satirlar.append("")
    return "\n".join(satirlar)


def mekan_kimligi(sayfa):
    """'/isletme.html?il=06&id=node/123' -> ('06', 'node/123')"""
    from urllib.parse import urlparse, parse_qs
    q = parse_qs(urlparse(sayfa).query)
    return (q.get("il", [""])[0], q.get("id", [""])[0])


def _parti_adi(il, kumeler):
    """Insanin okuyabildigi parti etiketi: 'ankara-51-52'.

    Etiket bir KIMLIK degil, bir NOT: sahada 'hangi partiden' sorusunun
    cevabi. Kod tarafinda tekillik kod_ozeti'nde; parti yalniz gruplama."""
    import datetime
    # CEVIRI ONCE, KUCULTME SONRA. Ters sirada yazilmisti ve kendi
    # kontrolum yakaladi: Python'da "İ".lower() tek harf degil, iki kod
    # noktasi veriyor (i + birlesen nokta), yani cevrim tablosu onu hic
    # gormuyor ve etikette ASCII olmayan bir karakter kaliyordu.
    cevir = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    parca = [(il or "turkiye").translate(cevir).lower().replace(" ", "")]
    parca.append("-".join(str(k) for k, _ in kumeler[:3]))
    parca.append(datetime.date.today().strftime("%Y%m%d"))
    ad = "-".join(p for p in parca if p)
    return ad[:60]


def _ciktilari_koru(ustune_yaz):
    """Var olan bir partinin uzerine yazma.

    saha_liste.csv, hangi kodun hangi kapiya gittigini gosteren TEK
    kayit -- kod veritabaninda yalniz sha256 ozeti olarak duruyor, yani
    silinen bir liste geri getirilemiyor. Kartlar da basilip dagitilmis
    olabilir. Bu yuzden sessiz uzerine yazma degil, DURMA."""
    var = [y for y in (KART_CIKTI, SQL_CIKTI, LISTE_CIKTI) if os.path.exists(y)]
    if not var or ustune_yaz:
        return
    sys.exit(
        "Onceki parti duruyor: %s\n"
        "Uzerine yazmiyorum -- %s hangi kodun hangi kapiya gittigini gosteren\n"
        "TEK kayit ve kod veritabaninda yalniz sha256 ozeti olarak duruyor.\n"
        "Once eskiyi yeniden adlandir (ornek: mv %s saha_liste-ankara-51.csv;\n"
        ".gitignore yildizli kaliplarla onu da kapsiyor), sonra tekrar kos.\n"
        "Bilerek istiyorsan: --ustune-yaz"
        % (", ".join(var), LISTE_CIKTI, LISTE_CIKTI))


def main(taban, adet, il=None, bayi=None, parti=None, atla=0,
         ustune_yaz=False):
    if not taban.startswith("http"):
        taban = "https://" + taban
    taban = taban.rstrip("/")

    secilen = sec(kumeleri_oku(il=il), adet, atla=atla)
    if not secilen:
        sys.exit("kume yok")

    kayitlar = []
    for kume_no, satirlar in secilen:
        for r in satirlar:
            il_kodu, mekan_id = mekan_kimligi(r["sayfa"])
            if not mekan_id:
                continue
            r = dict(r)
            r["kod"] = kod_uret()
            r["il_kodu"] = il_kodu
            r["mekan_id"] = mekan_id
            kayitlar.append(r)

    # Ayni kod iki mekana denk gelmesin. 29^8 ~ 5e11 icinde carpisma
    # olasiligi yok denecek kadar az ama "yok denecek kadar" bir kontrol
    # yerine gecmez: carpisma sessizce iki isletmeyi ayni sayfaya baglardi.
    kodlar = [r["kod"] for r in kayitlar]
    assert len(set(kodlar)) == len(kodlar), "kod carpismasi"

    if bayi is not None and not parti:
        parti = _parti_adi(il, secilen)

    _ciktilari_koru(ustune_yaz)

    io.open(KART_CIKTI, "w", encoding="utf-8").write(kart_html(taban, kayitlar))
    io.open(SQL_CIKTI, "w", encoding="utf-8").write(
        sql_uret(kayitlar, bayi=bayi, parti=parti))
    with io.open(LISTE_CIKTI, "w", encoding="utf-8-sig", newline="") as f:
        y = csv.writer(f)
        # il_kodu DA YAZILIYOR: SQL'i listeden yeniden uretmek (asagidaki
        # `sql` kipi) iki basamakli il kodunu istiyor ve il ADINDAN
        # turetilemez. Bu sutun olmadan yazilmis eski listeler icin kume
        # dosyasindan bulunuyor, ama o dosya yenilenirse bag kopar.
        y.writerow(["parti", "kume", "sira", "il", "il_kodu", "ad", "tur",
                    "mekan_id", "kod", "sor", "birakildi_mi", "not"])
        for r in kayitlar:
            y.writerow([parti or "", r["kume"], r["sira"], r["il"],
                        r["il_kodu"], r["ad"], r["tur"], r["mekan_id"],
                        r["kod"], r["sor"], "", ""])

    print("kume: %s" % ", ".join("#%s (%d mekan)" % (k, len(v)) for k, v in secilen))
    print("kart : %d  -> %s" % (len(kayitlar), KART_CIKTI))
    print("sql  : %s  (Supabase'e yapistir, YOKSA KODLAR CALISMAZ)" % SQL_CIKTI)
    print("liste: %s" % LISTE_CIKTI)
    if bayi is not None:
        print("bayi : #%d  parti '%s'  (bayilik.sql calistirilmis olmali)"
              % (bayi, parti))
    print()
    print("Sira: 1) SQL'i calistir  2) karti yazdir  3) kapiya birak")


# ---------------------------------------------------------------------
# Olcum: kart dagitildi da ne oldu?
# ---------------------------------------------------------------------
# Faz 3'un ucuncu ayagi. Kart basmak ve dagitmak bir IS; ise yaramasi
# ayri bir sey. Bu kisim onu olcuyor: kart birakilan mekanlarin sayfasi
# kac kez goruldu, kaci sahiplenildi, kaci bilgi ekledi.
#
# HICBIR GIZLI ANAHTAR KULLANILMIYOR. anon anahtari app/yapilandirma.js'ten
# okunuyor; zaten tarayiciya inen, tasarim geregi acik anahtar. Cagirdigi
# uc sey de herkese acik: mekan_sayaci() ham satir degil SAYI donuyor,
# sahiplik ve onaylanmis katkilar da zaten sayfada gorunuyor.

def _ayar():
    """app/yapilandirma.js'ten Supabase adresi ve anon anahtari."""
    import re
    yol = os.path.join("app", "yapilandirma.js")
    if not os.path.exists(yol):
        sys.exit("app/yapilandirma.js yok")
    metin = io.open(yol, encoding="utf-8").read()
    def al(ad):
        m = re.search(ad + r'\s*:\s*"([^"]*)"', metin)
        return m.group(1) if m else ""
    url, anahtar = al("supabaseUrl"), al("supabaseAnahtar")
    if not url or not anahtar:
        sys.exit("yapilandirma.js bos: supabaseUrl / supabaseAnahtar doldur")
    return url.rstrip("/"), anahtar


def _istek(url, anahtar, yol, govde=None):
    import json as _json
    import urllib.request
    ist = urllib.request.Request(
        url + yol,
        data=_json.dumps(govde).encode() if govde is not None else None,
        headers={"apikey": anahtar, "Authorization": "Bearer " + anahtar,
                 "Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if govde is not None else "GET")
    with urllib.request.urlopen(ist, timeout=20) as c:
        return _json.loads(c.read().decode() or "null")


def _il_kodlari(kimlikler):
    """mekan_id -> il_kodu, kume dosyasindan.

    YALNIZ ESKI LISTELER ICIN. saha_liste.csv artik il_kodu sutununu
    kendisi tasiyor; bu yol, o sutun eklenmeden once basilmis partiler
    (ankara-51, ankara-52) icin var ve bir gun kume dosyasi yenilenirse
    calismayi birakabilir -- o yuzden bulunamayani SAYMIYOR, ADIYLA
    sayiyor ve durduruyor."""
    istenen = set(kimlikler)
    bulunan = {}
    with io.open(KUME_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            il_kodu, mekan_id = mekan_kimligi(r["sayfa"])
            if mekan_id in istenen:
                bulunan[mekan_id] = il_kodu
    return bulunan


def sql_yaz(yol, bayi=None, parti=None):
    """Var olan bir kart listesinden SQL'i YENIDEN uret.

    NEDEN GEREKLI. Basilmis bir partiyi bir bayiye baglamanin tek yolu
    aksi halde kartlari YENIDEN BASMAK olurdu -- yeni kodlarla, yani
    elindeki 64 kart cop. Oysa kodlar listede duruyor ve bayi/parti
    yalniz SQL'de gecen bir sey. Ayni desen foto_cek.py'de de var
    (`python foto_cek.py sql`): CSV kaynak, SQL turetilmis.

    KART DOSYASINA DOKUNMUYOR. Kartlarin uzerindeki kod ve QR aynen
    kaliyor; degisen tek sey veritabanina hangi sutunlarin yazildigi."""
    if not os.path.exists(yol):
        sys.exit("%s yok." % yol)
    with io.open(yol, encoding="utf-8-sig") as f:
        kayitlar = list(csv.DictReader(f))
    if not kayitlar:
        sys.exit("%s bos." % yol)
    if not kayitlar[0].get("kod"):
        sys.exit("%s icinde 'kod' sutunu yok; bu bir saha listesi degil." % yol)

    eksik_kodlu = [r for r in kayitlar if not (r.get("kod") or "").strip()]
    if eksik_kodlu:
        sys.exit("%s icinde %d satirda kod yok; yarim liste yazmiyorum."
                 % (yol, len(eksik_kodlu)))

    if kayitlar[0].get("il_kodu"):
        for r in kayitlar:
            r["il_kodu"] = (r.get("il_kodu") or "").strip()
    else:
        print("liste 'il_kodu' sutunu tasimiyor; %s dosyasindan bulunuyor"
              % KUME_CSV)
        harita = _il_kodlari([r["mekan_id"] for r in kayitlar])
        yok = [r["mekan_id"] for r in kayitlar if r["mekan_id"] not in harita]
        if yok:
            sys.exit("Su mekanlarin il kodu %s icinde bulunamadi (%d): %s"
                     % (KUME_CSV, len(yok), ", ".join(yok[:5])))
        for r in kayitlar:
            r["il_kodu"] = harita[r["mekan_id"]]

    bos_il = [r["mekan_id"] for r in kayitlar if len(r["il_kodu"]) != 2]
    if bos_il:
        sys.exit("Su mekanlarin il kodu iki basamakli degil (%d): %s"
                 % (len(bos_il), ", ".join(bos_il[:5])))

    # Parti etiketi listede zaten varsa ONU kullan: ayni parti iki adla
    # anilmasin.
    if parti is None:
        parti = (kayitlar[0].get("parti") or "").strip() or None

    # Cikti adi girdiden turetiliyor: saha_liste-ankara-51.csv ->
    # saha_kodlar-ankara-51.sql. Boylece iki parti birbirinin ustune
    # yazmiyor.
    taban = os.path.basename(yol)
    ek = taban[len("saha_liste"):-len(".csv")] if taban.startswith("saha_liste") else ""
    cikti = os.path.join(os.path.dirname(yol) or ".", "saha_kodlar%s.sql" % ek)
    io.open(cikti, "w", encoding="utf-8").write(
        sql_uret(kayitlar, bayi=bayi, parti=parti))
    print("%d kod -> %s%s" % (len(kayitlar), cikti,
                              "  (bayi #%d, parti '%s')" % (bayi, parti or "")
                              if bayi is not None else ""))
    print("Kartlar DEGISMEDI: koda ve QR'a dokunulmadi.")


def olc(yol=LISTE_CIKTI):
    if not os.path.exists(yol):
        sys.exit("%s yok. Once kartlari uret." % yol)
    url, anahtar = _ayar()
    with io.open(yol, encoding="utf-8-sig") as f:
        kayitlar = list(csv.DictReader(f))

    kimlikler = [r["mekan_id"] for r in kayitlar]
    # Tek istekte hepsi: sahiplik ve katkilar dogrudan tablodan (ikisi de
    # herkese acik), sayac ise mekan basina RPC.
    icinde = "(" + ",".join('"%s"' % k.replace('"', "") for k in kimlikler) + ")"
    try:
        sahiplik = _istek(url, anahtar,
                          "/rest/v1/sahiplik?select=mekan_id&durum=eq.aktif"
                          "&mekan_id=in." + icinde) or []
        katki = _istek(url, anahtar,
                       "/rest/v1/katkilar?select=mekan_id,alan&durum=eq.onaylandi"
                       "&mekan_id=in." + icinde) or []
    except Exception as e:
        sys.exit("Supabase'e ulasilamadi: %s" % e)

    sahipli = {s["mekan_id"] for s in sahiplik}
    katki_say = collections.Counter(k["mekan_id"] for k in katki)

    print("%-30s %6s %6s %8s %s" % ("mekan", "bugun", "son30", "sahiplik", "katki"))
    print("-" * 66)
    toplam_gorunum = 0
    for r in kayitlar:
        try:
            s = _istek(url, anahtar, "/rest/v1/rpc/mekan_sayaci",
                       {"p_mekan_id": r["mekan_id"]})
            s = (s or [{}])[0] if isinstance(s, list) else (s or {})
        except Exception:
            s = {}
        son30 = s.get("son30") or 0
        toplam_gorunum += son30
        print("%-30s %6s %6s %8s %5d"
              % (_oz(r["ad"], 30), s.get("bugun") or 0, son30,
                 "VAR" if r["mekan_id"] in sahipli else "-",
                 katki_say.get(r["mekan_id"], 0)))

    print("-" * 66)
    print("%d mekan · son 30 gun %d goruntulenme · %d sahiplik · %d onayli katki"
          % (len(kayitlar), toplam_gorunum,
             sum(1 for r in kayitlar if r["mekan_id"] in sahipli),
             sum(katki_say.get(r["mekan_id"], 0) for r in kayitlar)))
    print()
    print("Sifir sahiplik, kartin ise yaramadigi anlamina gelir -- metni ya da")
    print("birakma bicimini degistirmeden ikinci kumeye cikma.")


def kendini_kontrol_et():
    """python saha.py test — aga ve dosyaya dokunmadan."""
    # Kod alfabesi: karisabilecek harf olmamali.
    for c in "IO01SZ2":
        assert c not in KOD_ALFABE or c in "34", (c, KOD_ALFABE)
    k = kod_uret()
    assert len(k) == KOD_UZUNLUK and set(k) <= set(KOD_ALFABE), k
    assert kod_uret() != kod_uret(), "kod tekrar ediyor"

    # Ozet, sunucudaki normalizasyonla AYNI sonucu vermeli. Bu ikisi
    # ayrisirsa kart basilir, dagitilir ve hicbiri calismaz.
    a = ozet("ABCD3456")
    assert a == ozet(" abcd-3456 ") == ozet("abcd 3456"), "normalizasyon ayrisik"
    assert a == hashlib.sha256(b"ABCD3456").hexdigest()
    assert len(a) == 64

    # Mekan kimligi ayristirma
    assert mekan_kimligi("/isletme.html?il=06&id=node/123") == ("06", "node/123")
    assert mekan_kimligi("bozuk") == ("", "")

    # Kume sirasi NUMARADAN geliyor, buyukluk yeniden siralamiyor:
    # sahiplen.py zaten degere gore numaraliyor. (Ilk yazimda burada
    # boyuta gore ikinci bir siralama vardi ve farkli sonuc veriyordu.)
    sahte = {"3": [1] * 9, "1": [1] * 2, "2": [1] * 5}
    assert [k for k, _ in sec(sahte, 2)] == ["1", "2"], sec(sahte, 2)
    assert [k for k, _ in sec(sahte, 3)] == ["1", "2", "3"]

    # LISTEDEN SQL'I YENIDEN URETMEK ayni kodlari vermeli. Bu turun
    # butun degeri burada: basilmis kartlar gecerli kalsin diye yapiliyor,
    # yani ozetler kaymissa tur zararli.
    import tempfile
    with tempfile.TemporaryDirectory() as gecici:
        liste = os.path.join(gecici, "saha_liste-deneme.csv")
        with io.open(liste, "w", encoding="utf-8-sig", newline="") as f:
            y = csv.writer(f)
            y.writerow(["parti", "kume", "sira", "il", "il_kodu", "ad", "tur",
                        "mekan_id", "kod", "sor", "birakildi_mi", "not"])
            y.writerow(["deneme", "1", "1", "Ankara", "06", "Ali'nin Yeri",
                        "Kafe", "node/1", "ABCD3456", "saat", "", ""])
        sql_yaz(liste, bayi=4, parti="deneme")
        uretilen = io.open(os.path.join(gecici, "saha_kodlar-deneme.sql"),
                           encoding="utf-8").read()
    assert ozet("ABCD3456") in uretilen, "yeniden uretilen SQL kodu tutmuyor"
    assert "ABCD3456" not in uretilen, "DUZ KOD yeniden uretilen SQL'e sizmis"
    assert ", 4, 'deneme')" in uretilen, uretilen
    assert "Ali''nin Yeri" in uretilen, "kacis yeniden uretimde kaybolmus"

    # --atla ikinci kumeyi veriyor, birincisini tekrar basmiyor.
    sahte = {"1": ["a"], "2": ["b"], "3": ["c"]}
    assert [k for k, _ in sec(sahte, 1)] == ["1"]
    assert [k for k, _ in sec(sahte, 1, atla=1)] == ["2"]
    assert [k for k, _ in sec(sahte, 2, atla=1)] == ["2", "3"]
    assert sec(sahte, 1, atla=9) == []

    # SQL kacisi: tek tirnakli mekan adi enjeksiyon olmamali
    ornek = [{"kod": "ABCD3456", "mekan_id": "node/1", "il_kodu": "06",
              "ad": "Ali'nin Yeri"}]
    s = sql_uret(ornek)
    assert "Ali''nin Yeri" in s, s
    assert ozet("ABCD3456") in s
    assert "ABCD3456" not in s, "DUZ KOD SQL'e sizmis"

    # BAYISIZ SQL bayi sutununa HIC dokunmamali: bayilik.sql
    # calistirilmamis bir projede kartlar yine basilabilmeli.
    assert ", bayi, parti" not in s, "bayisiz SQL bayi sutunu yaziyor"

    # Bayili SQL: sutunlar ve deger yerinde, parti etiketi de kaciriliyor.
    sb = sql_uret(ornek, bayi=7, parti="ankara'51")
    assert "(kod_ozeti, mekan_id, il, mekan_ad, gecerlilik, bayi, parti) values" in sb, sb
    assert ", 7, 'ankara''51')" in sb, sb
    assert "bayi #7" in sb
    assert "ABCD3456" not in sb, "DUZ KOD bayili SQL'e sizmis"

    # Bayili SQL, ZATEN YAZILMIS bir kodu da bayiye baglamali; bayisiz
    # olan hicbir seyi guncellememeli.
    assert "do update" in sb and "kullanildi is null" in sb, sb
    assert "do nothing" in s and "do update" not in s, s
    # Guncelleme yalniz iki sutuna dokunsun: kartin hangi mekana ait
    # oldugu ve kullanilip kullanilmadigi bu dosyayla degismemeli.
    for yasak in ("mekan_id =", "gecerlilik =", "kullanildi =", "kullanan ="):
        assert yasak not in sb, "guncelleme %s sutununa dokunuyor" % yasak

    # Parti etiketi: Turkce harf ve bosluk tasimamali (dosya adi, SQL ve
    # panelde yan yana geciyor).
    e = _parti_adi("\u0130stanbul", [("1", []), ("2", [])])
    assert e.startswith("istanbul-1-2-"), e
    assert e == e.encode("ascii", "ignore").decode(), e

    # QR gercekten uretiliyor ve veriyi tasiyabilecek boyutta
    svg = qr_svg("https://ornek.test/isletme.html?il=06&id=node/1&kod=ABCD3456")
    assert svg.startswith("<svg") and "path" in svg, svg[:80]

    # Kart HTML'i kacirilmis olmali
    kart = kart_html("https://ornek.test", [{
        "ad": '<script>x</script>', "tur": "Kafe", "il": "Ankara",
        "sor": "telefon", "sayfa": "/isletme.html?il=06&id=node/1",
        "kod": "ABCD3456"}])
    assert "<script>x</script>" not in kart, "kart HTML kacirmiyor"
    assert "&lt;script&gt;" in kart

    # Olcum tarafi: yapilandirma okunabiliyor mu ve HANGI anahtari
    # aliyor. service_role sizarsa RLS tamamen atlanir; kontrol bunu
    # ada gore degil JETONUN ICINDEKI ROLE gore yakaliyor.
    import base64, json as _json
    _url, _anahtar = _ayar()
    assert _url.startswith("https://"), _url
    _govde = _anahtar.split(".")[1]
    _govde += "=" * (-len(_govde) % 4)
    _rol = _json.loads(base64.urlsafe_b64decode(_govde)).get("role")
    assert _rol == "anon", "yapilandirma.js'te anon degil '%s' anahtari var" % _rol

    print("kontrol gecti: kod uretimi, ozet normalizasyonu, SQL kacisi, "
          "bayi sutunu, parti etiketi, kume atlama, listeden yeniden\n"
          "uretim, QR, kart, anon anahtar")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.exit(0 if kendini_kontrol_et() else 1)
    if len(sys.argv) > 1 and sys.argv[1] == "olc":
        olc()
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "sql":
        b = argparse.ArgumentParser(prog="saha.py sql",
                                    description="Var olan bir kart listesinden "
                                                "SQL'i yeniden uret")
        b.add_argument("liste", nargs="?", default=LISTE_CIKTI,
                       help="kart listesi (varsayilan %s)" % LISTE_CIKTI)
        b.add_argument("--bayi", type=int, default=None,
                       help="partiyi bu bayiye bagla")
        b.add_argument("--parti", default=None,
                       help="parti etiketi; verilmezse listedeki kullanilir")
        m = b.parse_args(sys.argv[2:])
        if m.parti and m.bayi is None:
            b.error("--parti yalniz --bayi ile anlamli: parti bir bayiye ait.")
        sql_yaz(m.liste, bayi=m.bayi, parti=m.parti)
        sys.exit(0)
    a = argparse.ArgumentParser(description="Saha kartlari uret")
    a.add_argument("alan_adi", help="ornek: cebimde.vercel.app")
    a.add_argument("--kume", type=int, default=3, help="kac kume (varsayilan 3)")
    a.add_argument("--atla", type=int, default=0,
                   help="ilk N kumeyi atla (ikinci partiyi basmak icin)")
    a.add_argument("--ustune-yaz", action="store_true",
                   help="var olan cikti dosyalarinin uzerine yaz")
    a.add_argument("--il", default=None,
                   help="yalniz bu ildeki kumeler (ornek: Ankara)")
    a.add_argument("--bayi", type=int, default=None,
                   help="partiyi bu bayiye bagla (veritabani/bayilik.sql)")
    a.add_argument("--parti", default=None,
                   help="parti etiketi; verilmezse ilden ve kumeden turetilir")
    n = a.parse_args()
    if n.parti and n.bayi is None:
        a.error("--parti yalniz --bayi ile anlamli: parti bir bayiye ait.")
    main(n.alan_adi, n.kume, il=n.il, bayi=n.bayi, parti=n.parti,
         atla=n.atla, ustune_yaz=n.ustune_yaz)
