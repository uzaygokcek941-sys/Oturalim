/* ============================================================
   Cebimde — tüm sayfaların paylaştığı davranış
   Tema, açılış saati mantığı, biçimlendirme, kohort ölçümü.
   Bağımlılık yok. Her sayfa <script src="ortak.js" defer> ile alır.
   ============================================================ */

/* ---------- tema ----------
   Seçim <head> içindeki küçük satır içi betikle uygulanıyor (FOUC olmasın).
   Buradaki iş yalnızca düğmeye davranış vermek. */
const TEMA_ANAHTAR = "cebimde.tema";

function temaUygula(t){
  if (t === "acik" || t === "koyu") document.documentElement.dataset.tema = t;
  else delete document.documentElement.dataset.tema;
  const koyuMu = t === "koyu" ||
    (!t && matchMedia("(prefers-color-scheme: dark)").matches);
  document.querySelectorAll("[data-tema-dugme]").forEach(d => {
    d.setAttribute("aria-label", koyuMu ? "Açık temaya geç" : "Koyu temaya geç");
    const ay = d.querySelector("[data-ay]"), gunes = d.querySelector("[data-gunes]");
    if (ay) ay.hidden = !koyuMu;
    if (gunes) gunes.hidden = koyuMu;
  });
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = koyuMu ? "#0f172a" : "#ffffff";
}

function temaKur(){
  let t = null;
  try { t = localStorage.getItem(TEMA_ANAHTAR); } catch (e) {}
  temaUygula(t);
  document.querySelectorAll("[data-tema-dugme]").forEach(d =>
    d.addEventListener("click", () => {
      const suan = document.documentElement.dataset.tema ||
        (matchMedia("(prefers-color-scheme: dark)").matches ? "koyu" : "acik");
      const yeni = suan === "koyu" ? "acik" : "koyu";
      try { localStorage.setItem(TEMA_ANAHTAR, yeni); } catch (e) {}
      temaUygula(yeni);
    }));
}

/* ---------- biçimlendirme ---------- */
const tl = n => n == null ? "" : Math.round(n).toLocaleString("tr-TR") + " ₺";
const sayi = n => Number(n || 0).toLocaleString("tr-TR");
/* Kuruş -> "1.250,00 ₺". tl() ile AYRI ve sebebi ayrı: tl() tam sayıya
   yuvarlıyor, menü fiyatında doğru olan da bu ("kişi başı 347 ₺"). Bayi
   hakedişi ve ödemesi kuruş hassasiyetinde tutuluyor (bayilik.sql) ve
   yuvarlanmış bir bakiye "5 kuruş nerede" sorusunu doğurur. */
const kurus = n => (Number(n || 0) / 100).toLocaleString("tr-TR",
  { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " ₺";
/* Tek tirnak da kaciriliyor. Bugun her oznitelik cift tirnakli, yani
   teknik olarak gerekli degildi; ama kacir()'in guvenli oldugunu varsayip
   href='...' yazan biri icin sessiz bir tuzakti. Kacis dizisi bir yerde
   eksikse, o eksigi bilmeyen kisi acigi acan kisi olur. */
const kacir = s => String(s == null ? "" : s)
  .replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;",
                               '"':"&quot;", "'":"&#39;" }[c]));

/* ---------- açılış saati ----------
   OSM opening_hours'un tamamı çok geniş; Türkiye'de fiilen görülen biçimler:
   "24/7", "09:00-23:00", "Mo-Su 09:00-23:00", "Su-Th 12:00-22:00; Fr-Sa 12:00-23:30" */
const GUNLER = ["Su","Mo","Tu","We","Th","Fr","Sa"];

/* Turkce gun adlari. OSM'nin kendi bicimi Ingilizce kisaltma ama veride
   Turkce yazilmislar var ve daha onemlisi: eksik saati KATKI olarak giren
   kullanici Turkce yaziyor. "Pazartesi-Pazar 10:00-22:00" katki
   dogrulamasindan GECIYORDU (bicim tanidik) ama gunUyar gunu cozemedigi
   icin mekan her gun KAPALI gorunuyordu -- onaylanmis bir bilgi, sessizce
   yanlis. Kisaltmalar tek anlamli secildi: Pzt/Paz ve Cum/Cmt karismasin.
   Anahtarlar sadelestirilmis (turkce harfsiz, kucuk harf) tutuluyor. */
const GUN_ADI = {
  su:0, sun:0, pazar:0, paz:0,
  mo:1, mon:1, pazartesi:1, pzt:1,
  tu:2, tue:2, sali:2, sal:2,
  we:3, wed:3, carsamba:3, car:3,
  th:4, thu:4, persembe:4, per:4,
  fr:5, fri:5, cuma:5, cum:5,
  sa:6, sat:6, cumartesi:6, cmt:6
};
const GUN_CEVIR = { "ç":"c","ğ":"g","ı":"i","ö":"o","ş":"s","ü":"u","â":"a","î":"i" };
const gunSade = s => String(s || "").trim().toLocaleLowerCase("tr")
  .replace(/[çğıöşüâî]/g, c => GUN_CEVIR[c]);

/* Her gun: "24/7" degil ama "hafta boyunca" demek. */
const HER_GUN = /^(her\s*gun|hergun|daily|everyday)$/;

const gunNo = a => {
  const d = gunSade(a);
  return Object.prototype.hasOwnProperty.call(GUN_ADI, d) ? GUN_ADI[d] : -1;
};

/* Doner: true (uyuyor), false (uymuyor), null (gun adi HIC taninmadi).
   null onemli: eskiden taninmayan ad sessizce atlaniyor ve fonksiyon
   false donuyordu -- "Pazartesi-Pazar 10:00-22:00" gibi bir deger
   "hicbir gun acik degil" anlamina geliyordu. Cagiran artik ayirt edip
   ifadeyi OKUNAMADI sayabiliyor. */
function gunUyar(ifade, gun){
  if (!ifade) return true;
  let tanindi = false;
  for (const p of ifade.split(",")){
    const t = p.trim();
    if (HER_GUN.test(gunSade(t))) return true;
    const [a, b] = t.split("-");
    const i = gunNo(a), j = b ? gunNo(b) : i;
    if (i < 0 || j < 0) continue;
    tanindi = true;
    if (j >= i ? (gun >= i && gun <= j) : (gun >= i || gun <= j)) return true;
  }
  return tanindi ? false : null;
}

function acikMi(ifade, simdi){
  simdi = simdi || new Date();
  if (!ifade) return null;
  if (/24\/7/.test(ifade)) return true;
  const gun = simdi.getDay(), dk = simdi.getHours()*60 + simdi.getMinutes();
  let sonuc = null;
  /* OSM'de kurallar ";" ile ayrilir ama veride cogu VIRGUL kullanmis:
     "Mo-Fr 10:00-20:00, Sa-Su 11:00-21:00". Duz virgulden bolmek olmaz --
     virgul gun listesinde de kullaniliyor ("Mo,We,Fr 09:00-17:00") ve
     boyle bolunce Mo ile We dusuyordu. Yalniz TAM BIR SAATTEN SONRA gelen
     virgul kural ayiracidir; gun listesindeki virgulun oncesinde saat
     olmaz. Olculdu: saati olan 3.714 mekanin 160'i hic okunamiyordu,
     bunlarin cogu bu yuzden. */
  for (const parca of ifade.replace(/(\d{1,2}:\d{2})\s*,\s*/g, "$1;").split(";")){
    /* Gun ifadesi "rakam olmayan her sey": [A-Za-z] Turkce harfleri
       disariya atiyordu, "Salı 11:00-22:00" ve "Hergün 09:00-23:00" hic
       eslesmiyordu. Bosluga da izin var ("Her gün", "Mo-Su, PH").
       Saat ayraci ":" ya da ".": Turkce yazimda "10.00-22.00" yaygin. */
    const m = parca.trim().match(
      /^(?:([^\d]+?)\s+)?(\d{1,2})[:.](\d{2})\s*-\s*(\d{1,2})[:.](\d{2})$/);
    if (!m) continue;
    const uy = gunUyar(m[1], gun);
    if (uy === null) continue;              /* gun adi taninmadi: kural okunmadi */
    if (!uy) { if (sonuc === null) sonuc = false; continue; }
    const bas = +m[2]*60 + +m[3];
    let bit = +m[4]*60 + +m[5];
    if (bit <= bas) bit += 1440;                            // gece yarısını aşıyor
    if (dk >= bas && dk < bit) return true;
    if (dk + 1440 >= bas && dk + 1440 < bit) return true;   // dünden taşan aralık
    sonuc = false;
  }
  return sonuc;
}

/* OSM "cuisine" etiketi Ingilizce ve alt cizgili geliyor
   ("coffee_shop;savory_pancakes"). Turkce bir sitede oldugu gibi
   gostermek hem cirkin hem anlasilmaz. Olculdu: 485 farkli deger var ama
   ilk 40'i kullanimlarin %90,9'unu kapsiyor -- yani kisa bir sozluk
   isin neredeyse tamamini goruyor.

   Sozlukte olmayan deger UYDURULMUYOR: alt cizgisi bosluga cevrilip
   oldugu gibi yaziliyor. Eksik cevirinin yerine yanlis ceviri koymak,
   bu projede baska hicbir yerde yapilmayan sey. */
const MUTFAK_TR = {
  turkish:"Türk", coffee_shop:"Kahveci", kebab:"Kebap", burger:"Burger",
  pizza:"Pizza", regional:"Yöresel", chicken:"Tavuk", sandwich:"Sandviç",
  fish:"Balık", seafood:"Deniz ürünleri", breakfast:"Kahvaltı", tea:"Çay",
  steak_house:"Et restoranı", ice_cream:"Dondurma", italian:"İtalyan",
  dessert:"Tatlı", cake:"Pasta", local:"Yerel", international:"Dünya mutfağı",
  pasta:"Makarna", barbecue:"Mangal", mediterranean:"Akdeniz", grill:"Izgara",
  fish_and_chips:"Balık ekmek", salad:"Salata", asian:"Asya", chinese:"Çin",
  bagel:"Simit/bagel", sushi:"Suşi", japanese:"Japon", juice:"Meyve suyu",
  soup:"Çorba", pide:"Pide", pancake:"Krep", friture:"Kızartma",
  coffee:"Kahve", mexican:"Meksika", american:"Amerikan",
  italian_pizza:"İtalyan pizza", fast_food:"Fast food", indian:"Hint",
  meat:"Et", waffle:"Waffle", greek:"Yunan", fine_dining:"Üst segment",
  french:"Fransız", hot_dog:"Sosisli", diner:"Lokanta", kahve:"Kahve",
  pastry:"Pastane", lahmacun:"Lahmacun", doner:"Döner", kofte:"Köfte",
  vegetarian:"Vejetaryen", vegan:"Vegan", bakery:"Fırın", donut:"Donut",
  crepe:"Krep", noodle:"Erişte", ramen:"Ramen", thai:"Tayland",
  arab:"Arap", lebanese:"Lübnan", georgian:"Gürcü", russian:"Rus",
  german:"Alman", spanish:"İspanyol", korean:"Kore", vietnamese:"Vietnam",
  savory_pancakes:"Gözleme", gozleme:"Gözleme", manti:"Mantı",
  borek:"Börek", corba:"Çorba", tantuni:"Tantuni", cig_kofte:"Çiğ köfte",
  baklava:"Baklava", waffles:"Waffle", sea_food:"Deniz ürünleri",
  hookah:"Nargile", beer:"Bira", wine:"Şarap", cocktails:"Kokteyl"
};

/* Gosterime hazir mutfak metni: "coffee_shop;savory_pancakes" ->
   "Kahveci · Gözleme". Ayrac NOKTA: virgul mutfak adlarinin icinde de
   gecebiliyor ve iki ayri sey ayni isarete binmesin. */
function mutfakYaz(ham){
  const parca = String(ham == null ? "" : ham).split(";")
    .map(x => x.trim()).filter(Boolean)
    .map(x => Object.prototype.hasOwnProperty.call(MUTFAK_TR, x)
              ? MUTFAK_TR[x] : x.replace(/_/g, " "));
  /* Tekrari at: "coffee;kahve" ikisi de "Kahve" oluyor. */
  return [...new Set(parca)].join(" · ");
}

/* OSM'deki web adreslerinin bir kismi SEMASIZ yazilmis ("www.narli.cafe",
   "instagram.com/x"). Oldugu gibi href'e konursa tarayici GORELI adres
   sanip site icinde arar ve baglanti kirilir. Olculdu: 120 mekan.
   isletme.html bunu duzeltiyordu, kesfet.js detay paneli duzeltmiyordu --
   ayni kural iki yerde farkliydi, bir yerde eksikti. */
/* Bir adresin href'e KONULABILIR olmasi. kacir() bunu yapmiyor: tirnak ve
   koseli parantez kaciriyor ama SEMAYA bakmiyor, yani kacir("javascript:...")
   sorunsuz bir href uretir. Adreslerin bir kismi ucuncu taraftan geliyor
   (etkinlik baglantilari RSS akislarindan), yani bu bir varsayim degil.

   Sema YOKSA https varsayiliyor -- OSM'de 117 mekanin web alani
   "instagram.com/x" gibi semasiz ve bunlar dogru adresler.
   Sema VARSA http/https olmali; degilse bos doner. */
function guvenliBag(u){
  const ham = String(u == null ? "" : u).trim();
  if (!ham) return "";
  /* "//baska.site/x" (protokolsuz adres) SEMASIZ SAYILMAZ. Sayilsaydi
     basina "https://" eklenip "https:////baska.site/x" olurdu; tarayici
     bunu https://baska.site/x diye cozer. Yani "instagram.com/x" gibi
     gorunen bir deger, tamamen baska bir siteye giden bir baglantiya
     donusurdu -- ustelik ekranda "Instagram" yaziyorken. Deger kullanici
     katkisindan da gelebiliyor. */
  if (ham.slice(0, 2) === "//") return "";
  const tam = /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(ham) ? ham : "https://" + ham;
  return /^https?:\/\//i.test(tam) ? tam : "";
}

function webBagi(u){
  const ham = String(u == null ? "" : u).trim();
  if (!ham) return "";
  const gorunen = kacir(ham.replace(/^https?:\/\//i, "").replace(/\/$/, ""));
  const tam = guvenliBag(ham);
  /* Adres kullanilamiyorsa METIN yine gosteriliyor, yalniz baglanti
     kurulmuyor. Veride iki gercek ornek var: "htttps://selfiepark.com.tr"
     ve "htpps://lunapark...". Eskiden bunlarin basina bir https daha
     ekleniyor ve hicbir yere gitmeyen bir baglanti cikiyordu; tamamen
     silmek ise kullanicinin elle duzeltebilecegi bilgiyi goturuyor. */
  if (!tam) return gorunen;
  return '<a href="' + kacir(tam) + '" target="_blank" rel="noopener nofollow">' +
         gorunen + "</a>";
}

/* ---------- dönüş adresi ----------
   giris.html, ?donus= parametresini DOGRUDAN adres olarak kullaniyordu.
   Denetimsiz birakildiginda iki sey oluyor; ikisi de bu depoda gercek
   Chromium ile olculdu:

     donus=javascript:...     -> location.href atamasi bunu CALISTIRIYOR.
                                 Ustelik tam giris yapildiktan sonra, yani
                                 oturum jetonu okunabilir haldeyken.
     donus=https://baska.site -> kullanici GERCEK sitede giris yapip taklit
                                 siteye dusuyor ("tekrar giris yap"). Klasik
                                 kimlik avi zinciri; adres cubugunda dogru
                                 alan adini gordugu icin de ikna edici.

   Kural: yalniz AYNI KOKENDE ve uygulamanin kendi klasorunde duran bir
   .html sayfasi. Uymayan her sey null; cagiran varsayilanina duser.
   Uretenlerin hepsi zaten kendi goreli adresini yaziyor, yani bu kural
   dogru kullanimin hicbirini kesmiyor. */
function guvenliDonus(ham, taban){
  if (!ham) return null;
  taban = taban || location.href;
  let u, t;
  try { u = new URL(String(ham), taban); t = new URL(taban); }
  catch (e) { return null; }
  /* javascript:, data:, blob: -> origin "null"; //baska.site -> baska origin. */
  if (u.origin === "null" || u.origin !== t.origin) return null;
  const klasor = t.pathname.replace(/[^/]*$/, "");
  if (u.pathname.indexOf(klasor) !== 0) return null;
  const sayfa = u.pathname.slice(klasor.length);
  if (!/^[A-Za-z0-9._-]+\.html$/.test(sayfa)) return null;   // alt klasor de yok
  return sayfa + u.search + u.hash;
}

/* ---------- bugün ----------
   YEREL gun. new Date().toISOString() UTC veriyor; Turkiye kalici UTC+3,
   yani her gece 00:00-03:00 arasi (gunun %12,5'i) UTC hala DUNU gosteriyor.
   Bu, disari cikan insanin fis paylastigi saat araligi. paylas.html hem
   varsayilan tarihi hem de <input max> degerini buradan aliyordu: gece 1'de
   form dunun tarihiyle aciliyor ve BUGUNU secmeye izin vermiyordu. */
function bugunYerel(d){
  d = d || new Date();
  return d.getFullYear() + "-" +
         String(d.getMonth() + 1).padStart(2, "0") + "-" +
         String(d.getDate()).padStart(2, "0");
}

/* ---------- yüklenemeyen resmi gizle ----------

   Bir kullanıcı fotoğrafı yüklenemezse (dosya silinmiş, ağ kesik, adres
   bozuk) tarayıcı kırık simgeyi ve alt metnini gösteriyor: kutunun içine
   sığmayan, taşan, bozuk görünen bir blok. Kırık bir küçük resim, hiç
   küçük resim olmamasından kötü.

   error olayı BALONLAMAZ, o yüzden yakalama evresinde dinleniyor
   (üçüncü argüman true). Tek dinleyici bütün sayfaları kapsıyor:
   isletme, hesabim ve yonetim aynı resimleri gösteriyor ve üç ayrı
   yerde üç ayrı çözüm, ikisinin unutulması demekti. */
function resimHatalariniGizle(hedef){
  (hedef || document).addEventListener("error", olay => {
    const g = olay.target;
    if (!g || g.tagName !== "IMG") return;
    /* YEDEKLI RESIM: kabı değil KENDİNİ gizler. Kart görsel yuvasında
       resmin altında kategori simgesi duruyor; kabı gizlemek kutuyu
       yok eder ve kartı zıplatırdı. */
    if (g.hasAttribute("data-yedekli")){ g.hidden = true; return; }
    /* Yalnız işaretlenmiş resimler: site kendi svg/logolarını gizlemesin. */
    const kap = g.closest("[data-resim]");
    if (kap) kap.hidden = true;
  }, true);
}

/* ---------- yüklenecek resmi hazırla ----------

   Dosyayı OLDUĞU GİBİ yüklemiyoruz; tuvale çizip yeniden kodluyoruz.
   Üç şey birden oluyor ve üçü de gerekli:

   1) EXIF TAMAMEN DÜŞÜYOR. Telefon fotoğrafı GPS koordinatı, çekim saati
      ve cihaz modeli taşır. Bu projede ham IP bile saklanmıyor -- günlük
      yenilenen bir özete çevriliyor (veritabani/sayac.sql). Kullanıcının
      bulunduğu yerin koordinatını bir menü fotoğrafının içinde yayımlamak
      o özenle çelişirdi. Tuval yalnız piksel taşır; üstveri taşımaz.

   2) Küçülüyor. 12 MP telefon fotoğrafı ~5 MB; menü okumak için 1600 px
      fazlasıyla yeter. Az veri, az yükleme süresi ve az depolama.

   3) Biçim tekleşiyor (JPEG). Kovanın kabul ettiği tür sayısı azaldıkça
      ayrıştırıcı yüzeyi de daralıyor.

   ÖNEMLİ: createImageBitmap'e imageOrientation veriliyor. Verilmezse EXIF
   yönü okunmaz ve dik çekilmiş fotoğraflar YAN yüklenirdi -- EXIF'i
   silmenin bilinen yan etkisi tam olarak budur. */
const RESIM_EN_BUYUK = 1600;      // uzun kenar, piksel
const RESIM_KALITE    = 0.82;

async function resimHazirla(dosya, enBuyuk, kalite){
  enBuyuk = enBuyuk || RESIM_EN_BUYUK;
  const tuvalVar = typeof OffscreenCanvas !== "undefined" || typeof document !== "undefined";
  if (typeof createImageBitmap !== "function" || !tuvalVar)
    throw new Error("Tarayıcın resim işlemeyi desteklemiyor.");

  const resim = await createImageBitmap(dosya, { imageOrientation: "from-image" });
  const oran = Math.min(1, enBuyuk / Math.max(resim.width, resim.height));
  const g = Math.max(1, Math.round(resim.width  * oran));
  const y = Math.max(1, Math.round(resim.height * oran));

  const tuval = typeof OffscreenCanvas !== "undefined"
    ? new OffscreenCanvas(g, y)
    : Object.assign(document.createElement("canvas"), { width: g, height: y });
  const ctx = tuval.getContext("2d");
  /* Beyaz zemin: saydam PNG'yi JPEG'e çevirince saydam alan SIYAH olur ve
     beyaz zeminli bir menü fotoğrafı okunamaz hale gelirdi. */
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, g, y);
  ctx.drawImage(resim, 0, 0, g, y);
  if (resim.close) resim.close();

  const tur = "image/jpeg";
  const veri = tuval.convertToBlob
    ? await tuval.convertToBlob({ type: tur, quality: kalite || RESIM_KALITE })
    : await new Promise(c => tuval.toBlob(c, tur, kalite || RESIM_KALITE));
  if (!veri) throw new Error("Resim işlenemedi.");
  return veri;
}

/* ---------- profil ve yorum yardımcıları ---------- */

/* Doğum yılından yaş. Veride yaş DEĞİL doğum yılı duruyor (profil.sql):
   yaş her yıl eskir, doğum yılı eskimez. Gün/ay olmadığı için sonuç bir
   yıl şaşabilir; "28" yerine "28" yazmak yine de doğruya en yakını ve
   daha azını söylüyor. */
function yasHesapla(dogumYili, bugun){
  const y = parseInt(dogumYili, 10);
  if (!Number.isFinite(y)) return null;
  const su = (bugun || new Date()).getFullYear();
  const yas = su - y;
  return (yas >= 13 && yas <= 120) ? yas : null;
}

/* "28 · Öğretmen" — ikisi de isteğe bağlı, ikisi de yoksa boş dizgi.
   Ayırıcıyı burada kurmak, üç sayfada üç ayrı birleştirme yazmaktan iyi. */
function profilOzeti(p, bugun){
  if (!p) return "";
  const yas = yasHesapla(p.dogum_yili != null ? p.dogum_yili : p.yazar_dogum, bugun);
  const meslek = (p.meslek || p.yazar_meslek || "").trim();
  return [yas, meslek].filter(Boolean).join(" · ");
}

/* Adın baş harfi. Fotoğrafı olmayan için; boş bir daire, kim olduğu
   belirsiz bir daireden iyi. */
function basHarf(ad){
  const t = (ad || "").trim();
  if (!t) return "?";
  return t[0].toLocaleUpperCase("tr");
}

/* ============================================================
   FİŞ EŞİĞİ — ağın atomu ve k-anonimlik sınırı

   Ortalama ancak 3 fişten sonra gösteriliyor. İki sebep:
   (1) tek fiş bir kişinin o günkü seçimidir, mekanın fiyatı değil;
   (2) k-anonimlik — tek fiş, tanıdığı biri tarafından kişiye bağlanabilir.
   Eşiğin altında TUTAR SIZMIYOR, kaç fiş kaldığı söyleniyor; böylece eşik
   kendisi katkı çağrısına dönüşüyor.

   BURADA DURUYOR ÇÜNKÜ İKİ EKRAN DA KULLANIYOR. Önce yalnız
   isletme.html'de tanımlıydı ve keşfet ekranı eşikten habersizdi:
   kart rozeti ("kişi başı ~X ₺") ve detay panelindeki "Gerçekten ödenen"
   kutusu TEK FİŞTEN çiziliyordu -- üstelik panel "1 kişinin
   paylaşımından" diye bunu açıkça yazıyordu. Yani işletme sayfasının
   gizlediği şeyi keşfet ekranı yayımlıyordu. Aynı kural iki yerde
   yaşayamaz; kural burada, gösterim çağıranda.
   ============================================================ */
const FIS_ESIK = 3;

/* Saf: fiş ÖZETİ -> gösterilecek cümle.
   Girdi {fis, kisi, medyan}. `kisi` yoksa uydurulmuyor -- keşfet ekranı
   onu bilemiyor (kimlik sütunu kapalı), işletme sayfası sunucudan alıyor. */
function fisOzeti(o){
  const n = (o && o.fis) || 0;
  if (!n)
    return "Buranın fiyatını kimse yazmamış. Gittiysen ödediğini yaz — " +
           "bir sonraki kişi kazık yemeden gitsin.";
  if (n < FIS_ESIK)
    return "Şu ana kadar " + sayi(n) + " fiş var. " +
           (FIS_ESIK - n) + " tane daha gelince ortalama burada görünecek.";
  return "Kişi başı ~" + tl(o.medyan) + " · " +
         ((o && o.kisi) ? sayi(o.kisi) + " kişinin " : "") + sayi(n) + " fişinden.";
}

/* Tutar gösterilebilir mi. Tek yerde dursun: rozet, kutu ve süzgeç
   üçü de buna soruyor. medyan null ise sayı yok demektir -- fiş sayısı
   eşiği geçse bile uydurulmuyor. */
function fisGoster(o){
  return !!(o && o.fis >= FIS_ESIK && o.medyan != null);
}

/* ============================================================
   İL DOSYASI — sıkıştırılmış biçimi açar

   Kural ve gerekçe `veri_bicim.py` başında yazılı; burası onun tarayıcı
   tarafı. İki uçta iki kod var ama TEK biçim: Python tarafı 81 ilin
   hepsinde kodla/çöz turunu yapıp eşitlik arıyor, buradaki öz kontrol de
   aynı örneği açıyor.

   Kısaca: her mekanda bulunan beş alan **sütun**, seyrek alanlar
   **indeksli sözlük**. Ölçüldü (İstanbul): ham 1733 → 1325 KB, gzip
   396 → 322 KB. İkisinin de düşmesi önemli — gzip indirmeyi, ham boyut
   `JSON.parse` süresini belirliyor.

   ESKİ BİÇİMİ DE OKUR: `mekanlar` anahtarı varsa dosya dönüştürülmemiş
   demektir ve olduğu gibi dönüyor. Yarım kalmış bir dağıtımda uygulama
   çalışmaya devam etsin diye.
   ============================================================ */
const VERI_YOGUN = ["id", "ad", "tur", "lat", "lon"];
const VERI_ONEK  = { n: "node", w: "way", r: "relation" };

function ilCoz(d){
  if (!d || typeof d !== "object") return { il: null, mekanlar: [] };
  if (d.mekanlar) return d;                     /* eski biçim */
  const sutun = d.sutun || {}, kimlikler = sutun.id || [], mekanlar = [];
  for (let i = 0; i < kimlikler.length; i++){
    const m = {};
    for (const k of VERI_YOGUN) m[k] = sutun[k] ? sutun[k][i] : undefined;
    /* Önek geri açılıyor: dışarıya giden kimlik DEĞİŞMİYOR. O kimlik
       veritabanında mekan_id olarak duruyor ve adres çubuğunda geziniyor;
       kısaltılmış hali sızsaydı eski bağlantılar kırılırdı. */
    const ham = String(m.id == null ? "" : m.id), bas = VERI_ONEK[ham[0]];
    /* Rakam denetimi şart: "nazar" gibi bir değer kimlik sanılmasın. */
    if (bas && ham.length > 1 && /^\d+$/.test(ham.slice(1)))
      m.id = bas + "/" + ham.slice(1);
    mekanlar.push(m);
  }
  const ek = d.ek || {};
  for (const alan of Object.keys(ek)){
    const kayitlar = ek[alan];
    for (const indeks of Object.keys(kayitlar)){
      const m = mekanlar[+indeks];
      if (m) m[alan] = kayitlar[indeks];
    }
  }
  return { il: d.il, mekanlar: mekanlar };
}

/* ============================================================
   CİVAR — "mahalle statüsü"

   NEDEN BU KUTUNUN BAŞLIĞINDA MAHALLE ADI YOK. Bu cümlenin ilk hali
   "mahalle adı veride yok" diyordu ve ADRES METNİNDEN AYRIŞTIRMAYI
   kastediyordu: 9.397 adresin yalnız 49'unda (%0,14) ayrıştırılabilir
   bir mahalle adı geçiyor. O ölçüm hâlâ doğru.

   AMA MAHALLE ADI ARTIK VAR: OSM'in kendi `addr:*` etiketlerinden
   geliyor ve 3.788 mekanda (%10,6) yazıyor; ilçe 7.195'te (%20,1).
   İkisi de veride duruyordu ve uygulamaya hiç ulaşmıyordu.

   Kutunun başlığı yine de YARIÇAP diyor, çünkü burada sayılan şey bir
   mahallenin tamamı değil, 500 m'lik bir daire. "Suadiye'de 55 mekan"
   demek, elimizde olmayan bir sınırı iddia etmek olurdu. Mahalle adı
   mekanın KENDİ satırında yazıyor (semtYaz), sayımın başlığında değil.

   NEDEN 500 m: yürüme mesafesi ve veri buna elveriyor. Ölçüldü (500 m
   yarıçapta komşu sayısı medyanı): Ankara 13, İstanbul 40, İzmir 19,
   Aksaray 4. Hiç komşusu olmayan mekan oranı Ankara %4, İstanbul %1,
   İzmir %8, Aksaray %20 -- yani çoğu sayfada dolu bir cevap çıkıyor.

   NEDEN "ÇEVRESİNE GÖRE PAHALI" DEMİYORUZ: diyemiyoruz. Menü fiyatı
   bilinen mekan 35.852'de 293 (%0,82); 500 m içinde en az 3 fiyatlı
   komşusu olan mekan yalnız %4,16. Üç örnekten çıkan bir medyana dayanıp
   "burası çevresine göre pahalı" demek, uydurma seviyeden farksız olurdu.
   Gösterilen şey KAPSAM: kaç mekan var, kaçının fiyatı biliniyor. Ağ
   büyüdükçe fiş medyanı bu kutunun içinde kendiliğinden beliriyor.
   ============================================================ */
const CIVAR_YARICAP = 500;   /* metre */
const CIVAR_EN_AZ   = 3;     /* altında "civar" diye bir şey yok */
const CIVAR_EN_COK  = 500;   /* sunucunun kabul ettiği liste uzunluğu */

/* İki nokta arası kaba metre. Eşdeğer dikdörtgen yaklaşımı: birkaç yüz
   metrede haversine ile farkı milimetrik, hesabı çok daha ucuz --
   ve bu fonksiyon bir il dosyasındaki 12 bin mekan için koşuyor. */
function mesafeM(a, b){
  const k = Math.cos(a.lat * Math.PI / 180);
  const dx = (b.lon - a.lon) * k * 111320;
  const dy = (b.lat - a.lat) * 110540;
  return Math.hypot(dx, dy);
}

/* Bir mekanın çevresi. `hepsi` ilin tamamı (statik JSON), mekanın kendisi
   listeye GİRMİYOR: kutu bir karşılaştırma, kendini kendiyle kıyaslamaz.

   YARIÇAP DARALTILABİLİR, LİSTE KIRPILMAZ. Sunucu 500'den uzun mekan
   listesini reddediyor (akran.sql). Listeyi sessizce kırpmak, ekranda
   yazan "500 m çevresinde" ifadesini yalan yapardı -- İstanbul'un yoğun
   caddelerinde 500 m'de 600 mekan olabiliyor. Onun yerine yarıçap 100'er
   metre daraltılıyor ve DARALTILMIŞ yarıçap dönüyor; ekranda o yazıyor. */
/* ---------- "bu civarda ne yenir" ----------
   Ürün tarifinin 10. maddesi. Tarif "bugün popüler" diyor; POPÜLERLİK
   VERİSİ YOK ve uydurulamaz -- tek kullanıcı yok, tıklama geçmişi yok.
   Sıfır tıklamayı "popüler" diye sıralamak ölçülmemiş bir şey uydurmak
   olurdu.

   Sorunun kendisi ise cevaplanabilir: 1 km çemberinde fiyatlı menü
   kalemi olan mekan 12.102 (%44,3), kalem ortancası 47.

   SIRA UCUZDAN PAHALIYA. Uygulamanın sorusu "bu parayla ne yenir";
   ucuzdan sıralamak onu ilk satırda cevaplıyor ve uydurma bir
   popülerlik iddiası taşımıyor.

   İÇECEK VE TATLI DIŞARIDA: soru "ne YENİR". Menüdeki en ucuz kalem
   neredeyse her zaman bir içecek olduğu için liste ayransa hiçbir şey
   söylemezdi -- yemekFiyati()'nin dışladığı kümelerin aynısı. */
const CIVAR_KALEM_EN_COK = 5;

function civarKalemleri(m, hepsi, butce, yaricap){
  if (!m || typeof m.lat !== "number") return [];
  if (!Array.isArray(hepsi) || !hepsi.length) return [];
  const tavan = yaricap || CIVAR_YARICAP;
  const disi = new Set([...ICECEK_KAT, ...TATLI_KAT]);
  const l = [];
  for (const o of hepsi){
    if (!o || o === m || o.id === m.id) continue;
    if (typeof o.lat !== "number" || !(o.menu || []).length) continue;
    const d = mesafeM(m, o);
    if (d > tavan) continue;
    /* Bir mekandan EN UCUZ TEK kalem: aynı restoranın altı çeşidi
       listeyi doldurup çevreyi göstermez hale getirirdi. */
    let en = null;
    for (const k of o.menu){
      if (!k || k.f == null || !k.a) continue;
      if (k.k && disi.has(k.k)) continue;
      if (kampanyaMi(k)) continue;      /* teklif, porsiyon fiyati degil */
      if (!en || k.f < en.f) en = k;
    }
    if (en) l.push({ ad: en.a, fiyat: en.f, mekan: o.ad, id: o.id,
                     uzak: Math.round(d) });
  }
  l.sort((a, b) => a.fiyat - b.fiyat || a.uzak - b.uzak);
  /* AYNI KALEM BIR KEZ. Ölçüldü: liste "Caffe Latte 10'lu — Kahve
     Dünyası" satırını ÜÇ KEZ veriyordu, çünkü aynı zincirin üç şubesi
     500 m içinde. Beş satırın üçü tek bir ürüne gidince liste
     "civarda ne var" sorusunu cevaplamıyor. Ad anahtarı zincir
     haritasınınkiyle aynı (_adAnahtari): boşluk ve büyük/küçük harf
     farkları aynı kalemi ikiye bölmesin. En YAKIN şube kalıyor. */
  const gorulen = new Set();
  const tekil = [];
  for (const k of l){
    const anahtar = _adAnahtari(k.ad);
    if (gorulen.has(anahtar)) continue;
    gorulen.add(anahtar);
    tekil.push(k);
  }
  /* Bütçe varsa AŞANLAR ELENMİYOR, sona atılıyor: "300 TL'ye ne var"
     diye bakan biri 320 TL'lik bir seçeneği de görmeli. */
  if (butce > 0)
    tekil.sort((a, b) => (a.fiyat > butce) - (b.fiyat > butce) ||
                         a.fiyat - b.fiyat);
  return tekil.slice(0, CIVAR_KALEM_EN_COK);
}

function civarOzeti(m, hepsi, yaricap){
  if (!m || typeof m.lat !== "number" || typeof m.lon !== "number") return null;
  if (!Array.isArray(hepsi) || !hepsi.length) return null;

  const tavan = yaricap || CIVAR_YARICAP;
  const olculu = [];
  for (const o of hepsi){
    if (o === m || (o && o.id === m.id)) continue;
    if (!o || typeof o.lat !== "number" || typeof o.lon !== "number") continue;
    const d = mesafeM(m, o);
    if (d <= tavan) olculu.push([d, o]);
  }

  let r = tavan, yakin = olculu;
  while (yakin.length > CIVAR_EN_COK && r > 100){
    r -= 100;
    yakin = olculu.filter(x => x[0] <= r);
  }
  /* Aynı koordinata yığılmış mekanlar yüzünden 100 m'de bile sığmıyorsa
     fiş sorulmuyor. Sayım yine doğru; yalnız o satır susuyor. */
  const sorulabilir = yakin.length <= CIVAR_EN_COK;
  if (yakin.length < CIVAR_EN_AZ) return null;

  const say = new Map();
  let fiyatli = 0;
  for (const [, o] of yakin){
    if (o.tur) say.set(o.tur, (say.get(o.tur) || 0) + 1);
    if (yemekFiyati(o) != null) fiyatli++;
  }
  return {
    yaricap: r,
    yakin: yakin.length,
    fiyatli: fiyatli,
    /* En kalabalık üç tür. Hepsini yazmak 20 satırlık bir liste demekti
       ve soruyu ("burada ne var") cevaplamıyordu. */
    turler: [...say.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "tr"))
              .slice(0, 3),
    idler: sorulabilir ? yakin.map(x => x[1].id).filter(Boolean) : []
  };
}

/* ============================================================
   BÜTÇE AKRANLARI

   "Benim bütçemdeki insanlar nereye gidiyor." Fiş katmanının bir üstü:
   orada soru tek bir mekan hakkında, burada bütçe hakkında.

   NEDEN SUNUCUDAN GELİYOR: "kaç KİŞİ" ile "kaç FİŞ" ayrı şeyler ve fark
   bu özelliğin bütün anlamı -- üç fişi olan tek kişi bir akran topluluğu
   değil. Tarayıcı bunu ayırt edemiyor, çünkü `kullanici` sütunu ona
   kapalı (sema.sql). Sayım akran.sql'de.

   AKRAN_GUN, akran.sql'deki pencereyle AYNI OLMAK ZORUNDA: aşağıdaki
   cümle "son 6 ayda" diyor, sorgu 180 günden bakıyor. İkisi ayrışırsa
   ekranda yazan süre yalan olur -- test.py ikisini karşılaştırıyor. */
const AKRAN_GUN = 180;

function akranCumlesi(o, butce){
  if (!o || !(butce > 0)) return null;
  /* Sıfır bir başarısızlık değil, davet: eşiğin kendisi katkı çağrısına
     dönüşüyor (fiş eşiğiyle aynı desen). */
  if (!o.akran)
    return "Kişi başı " + tl(butce) + " altında henüz fiş yok. " +
           "Bu bütçeyle bir yere gittiysen ilk yazan sen ol.";
  return sayi(o.akran) + " kişi son 6 ayda " + sayi(o.mekan) +
         " mekanda kişi başı " + tl(butce) + " altında ödedi.";
}

/* Puan yıldızı. Metin olarak da okunabilsin diye aria-label veriliyor:
   ekran okuyucuya "4,5 yıldız" demek, beş ayrı yıldız karakteri
   okutmaktan iyi. */
const YORUM_ESIK = 3;      /* altında ortalama gösterilmiyor -- bkz. fiş eşiği */

function yildiz(puan){
  /* puan == null KONTROLU SART: Number(null) sifirdir ve sonludur, yani
     yalniz isFinite'a bakan hal puansiz mekana bes bos yildiz basiyordu.
     Aralik da denetleniyor -- 0 ya da 7, yildiz sayisini bozardi. */
  if (puan == null || puan === "") return "";
  const n = Number(puan);
  if (!Number.isFinite(n) || n < 1 || n > 5) return "";
  const tam = Math.round(n);
  return '<span class="yildiz" aria-label="' + kacir(n.toLocaleString("tr-TR")) +
         ' üzerinden 5">' + "★".repeat(tam) + "☆".repeat(5 - tam) + "</span>";
}

/* ---------- sosyal medya ----------
   OSM'de her platform ayrı bir etiket. Kullanıcı adı da tam adres de
   geliyor; ikisini de kabul edip TEK bir adrese çeviriyoruz.

   Adres ŞEMASI guvenliBag()'dan geçiyor: kullanıcı katkısı da bu yoldan
   girebiliyor ve kacir() şemaya bakmaz. */
const SOSYAL = {
  insta:    { ad: "Instagram", taban: "https://instagram.com/",   onek: "@" },
  x:        { ad: "X",         taban: "https://x.com/",           onek: "@" },
  facebook: { ad: "Facebook",  taban: "https://facebook.com/",    onek: "" },
  tiktok:   { ad: "TikTok",    taban: "https://tiktok.com/@",     onek: "@" },
  youtube:  { ad: "YouTube",   taban: "https://youtube.com/",     onek: "" }
};

const sosyalAlanVar = a => Object.prototype.hasOwnProperty.call(SOSYAL, a);

/* Değer ya kullanıcı adı ("cebimde") ya tam adres. Tam adres geldiyse
   olduğu gibi kullanılıyor -- kullanıcı adını ayıklamaya çalışmak,
   /p/, /pages/ gibi biçimlerde yanlış adres üretirdi. */
function sosyalBag(alan, deger){
  if (!sosyalAlanVar(alan)) return "";
  const ham = String(deger == null ? "" : deger).trim();
  if (!ham) return "";
  const s = SOSYAL[alan];
  const tam = /^[a-zA-Z][a-zA-Z0-9+.-]*:|^\/\//.test(ham)
    ? guvenliBag(ham)
    : s.taban + encodeURIComponent(ham.replace(/^@/, ""));
  if (!tam) return "";
  const gorunen = /^https?:\/\//i.test(ham)
    ? ham.replace(/^https?:\/\//i, "").replace(/\/$/, "")
    : s.onek + ham.replace(/^@/, "");
  return '<a href="' + kacir(tam) + '" target="_blank" rel="noopener">' +
         kacir(gorunen) + "</a>";
}

/* Mekanda dolu olan sosyal alanlar, sabit sırayla. Sıra SOSYAL'in kendi
   sırası: iki sayfada iki ayrı sıra, aynı mekanı iki türlü gösterirdi. */
function sosyalListe(m){
  if (!m) return [];
  return Object.keys(SOSYAL)
    .filter(k => (m[k] || "").toString().trim())
    .map(k => ({ alan: k, ad: SOSYAL[k].ad, bag: sosyalBag(k, m[k]) }))
    .filter(x => x.bag);
}

/* Mekanın semti: "Suadiye · Kadıköy". İkisi de olmayabilir.

   TEK YERDE: keşfet detay paneli ve işletme sayfası aynı satırı
   yazıyor; iki yerde iki türlü kurulursa aynı mekan iki sayfada iki
   türlü okunur (mutfakYaz'ın gerekçesiyle aynı).

   Sıra DAR'DAN GENİŞ'e: mahalle, sonra ilçe. Adres satırının devamı
   gibi okunuyor.

   AYNI DEĞER İKİ KEZ YAZILMIYOR: OSM'de mahalle ile ilçe aynı olabiliyor
   ("Fatih" hem ilçe hem mahalle) ve "Fatih · Fatih" saçma görünürdü. */
function semtYaz(m){
  if (!m) return "";
  const l = [];
  if (m.mahalle) l.push(m.mahalle);
  if (m.ilce && m.ilce !== m.mahalle) l.push(m.ilce);
  return l.join(" · ");
}

/* ---------- dış harita ve "yorumları kaynağında oku" ----------

   İKİ AYRI ŞEY, ve ayrı adlandırılıyorlar:

     yol tarifi  -> KOORDİNATA gidiyor. Yanılma payı yok; enlem-boylam
                    zaten elimizde ve mekanın tek kesin verisi o.
     arama       -> ADLA arıyor. Google Maps'in yer kimliği (place_id)
                    ELİMİZDE YOK ve uydurulamaz; "bu mekanın Maps
                    sayfası" demek, aynı adlı başka bir şubeye
                    yollandığında yalan olurdu. O yüzden düğme "ara"
                    diyor, "aç" demiyor.

   YORUMLAR KAZINMIYOR. Google Maps, Yandex ve Instagram yorumları
   yazarlarının telifinde ve platforma lisanslı; kopyalayıp burada
   yayımlama hakkımız yok (CEBIMDE.md "Yapılmayacaklar", fotoğraflarla
   aynı gerekçe). Yapılabilecek dürüst şey, kullanıcıyı KAYNAĞA
   göndermek -- yorumu orada, yazarının yayımladığı yerde okuyor.
   Cebimde'nin kendi yorumları ayrı ve zaten sayfada. */
function koordinatVar(m){
  return !!(m && typeof m.lat === "number" && typeof m.lon === "number" &&
            isFinite(m.lat) && isFinite(m.lon) &&
            Math.abs(m.lat) <= 90 && Math.abs(m.lon) <= 180);
}

/* Ekranda okunacak koordinat. Altı hane ~11 cm; daha fazlası veride
   olmayan bir kesinlik iddia ederdi. */
function koordinatYaz(m){
  return koordinatVar(m) ? m.lat.toFixed(6) + ", " + m.lon.toFixed(6) : "";
}

/* Mekanı aramak için kullanılacak metin: ad + il. İl olmadan "Bambi
   Cafe" Türkiye'de onlarca yere düşüyor. */
function aramaMetni(m, ilAd){
  return [m && m.ad, m && m.adres, ilAd].filter(Boolean).join(" ");
}

const DIS_HARITA = [
  { anahtar:"yol",    ad:"Yol tarifi", tur:"tarif",
    taban:"https://www.google.com/maps/dir/?api=1&destination=" },
  { anahtar:"google", ad:"Google'da ara", tur:"arama",
    taban:"https://www.google.com/maps/search/?api=1&query=" },
  { anahtar:"yandex", ad:"Yandex'te ara", tur:"arama",
    taban:"https://yandex.com.tr/harita/?text=" },
  { anahtar:"osm",    ad:"OpenStreetMap", tur:"tarif",
    taban:"https://www.openstreetmap.org/?mlat=" }
];

/* Dış harita bağlantıları. Koordinat yoksa BOŞ döner: "yol tarifi"
   düğmesi nereye gideceğini bilmeden gösterilmemeli. */
function disHaritalar(m, ilAd){
  if (!koordinatVar(m)) return [];
  const nokta = m.lat.toFixed(6) + "," + m.lon.toFixed(6);
  const arama = aramaMetni(m, ilAd);
  return DIS_HARITA.map(h => {
    let adres;
    if (h.anahtar === "osm")
      adres = h.taban + m.lat.toFixed(6) + "&mlon=" + m.lon.toFixed(6) +
              "#map=18/" + m.lat.toFixed(6) + "/" + m.lon.toFixed(6);
    else if (h.tur === "tarif")
      adres = h.taban + encodeURIComponent(nokta);
    else
      /* Aramaya KOORDİNAT DA giriyor: ad tek başına yanlış şubeye
         düşürüyor, koordinat aramayı doğru mahalleye çiviliyor. */
      adres = h.taban + encodeURIComponent(arama ? arama + " " + nokta : nokta);
    return { anahtar:h.anahtar, ad:h.ad, tur:h.tur, bag:adres };
  });
}

/* ---------- katkı doğrulama ----------
   Kullanıcıdan gelen eksik alan bilgisi. Onaya gitmeden ÖNCE burada eleniyor;
   yöneticiye ancak kullanılabilir biçimde olanlar ulaşsın.

   Saat için ayrı bir kural YAZILMADI: değer acikMi()'ye veriliyor ve
   ayrıştırılabiliyor mu diye bakılıyor. Kendi regex'ini yazsaydım "Her gün
   09:00-23:00" gibi bir değer doğrulamadan geçer, onaylanır, sonra "şu an
   açık" süzgeci onu sessizce hiç okuyamazdı. Süzgecin okuyamadığı bilgi
   yayımlanmış sayılmaz. */
const KATKI_ALAN = { saat:"Açılış–kapanış", tel:"Telefon", adres:"Adres", web:"Site" };

/* Duz "KATKI_ALAN[alan]" yetmiyor: alan="constructor" gelirse Object'ten
   miras kalan alan dondugu icin kontrol geciliyordu. Deger istemciden
   geliyor, o yuzden yalniz KENDI anahtarlarina bakiliyor. */
const katkiAlaniVar = a => Object.prototype.hasOwnProperty.call(KATKI_ALAN, a);

function katkiSorunu(alan, deger){
  if (!katkiAlaniVar(alan)) return "Bilinmeyen alan.";
  const d = String(deger == null ? "" : deger).trim();
  if (d.length < 2)   return "Boş bırakma.";
  if (d.length > 200) return "Çok uzun, 200 karakteri geçmesin.";

  if (alan === "saat")
    return acikMi(d) === null
      ? "Saati şu biçimde yaz: 09:00-23:00 · Hergün 10:00-22:00 · " +
        "Pazartesi-Cuma 09:00-18:00 · 24/7"
      : null;

  if (alan === "tel"){
    const r = d.replace(/\D/g, "");
    /* 5321234567 (10) · 05321234567 (11) · 905321234567 (12) · +90… (13'e
       kadar). Alt sınırı 10'un altına indirmek kısa numarayı geçirir. */
    return r.length < 10 || r.length > 13 ? "Telefon eksik ya da fazla haneli." : null;
  }

  if (alan === "adres")
    return d.length < 5 ? "Adresi biraz daha aç (cadde, no)." : null;

  /* Site: "@kullanici" KABUL EDİLMİYOR. Hangi platform olduğunu tahmin
     etmek gerekirdi ve tahmin veri uydurmaktır; tam bağlantı isteniyor. */
  return /^(https?:\/\/)?[a-z0-9-]+(\.[a-z0-9-]+)+(\/[^\s]*)?$/i.test(d)
    ? null : "Tam bağlantı yaz: instagram.com/… ya da site adresi.";
}

/* ---------- bütçe bandı ----------
   Kişi başı bütçeyi mekanın MENÜ KALEMİ ORTALAMASIYLA karşılaştırır.
   Bu, "ortalama hesap" DEĞİL: hesap birden fazla kalem + içecek demek,
   bizim bildiğimiz şey menüdeki bir yemeğin ortalama fiyatı. İkisini aynı
   saymak, gerçek hesabın altında bir rakam vaat etmek olurdu. */
/* Butce karsilastirmasi YEMEK fiyatiyla yapilir. m.min ile yapilinca 100 TL
   butce giren kisiye ana yemegi 400 TL olan balikci "butcende" diye
   gosteriliyordu -- cunku m.min menudeki en ucuz icecekti. */
function bant(m, butce, bugun){
  const f = yemekFiyati(m, bugun);
  if (f == null || !butce) return null;
  if (f > butce) return { sinif:"tuz",  ad:"bütçe üstü" };
  return { sinif:"ucuz", ad:"bütçene giriyor" };
}

/* ---------- fiyat seviyesi ----------
   Mekanların %1,2'sinde gerçek menü fiyatı var. Kalanı için tür ve OSM
   mutfak etiketi kullanılıyor; ikisi de sinyal vermiyorsa null dönüp kart
   hiçbir şey iddia etmiyor. Uydurma seviye, seviye yokluğundan kötüdür. */
const MUTFAK_HESAPLI = new Set(["burger","kebab","pizza","sandwich","chicken",
  "doner","kofte","pide","lahmacun","tea","coffee_shop","ice_cream","dessert",
  "breakfast","fish_and_chips","soup","turkish","regional","local"]);
const MUTFAK_UST = new Set(["steak_house","sushi","japanese","seafood","fish",
  "italian","french","international","fine_dining"]);

/* Eğlence mekanlarının menüsü yok; fiyat bilgisi tür seviyesinde kalıyor.
   Müze ve galeri Türkiye'de çoğunlukla düşük ücretli ya da ücretsiz; aquapark
   ve tema parkı günlük biletle pahalı. Ortada kalanlara "biletli" deyip
   rakam iddia etmiyoruz. */
const EGLENCE_UCUZ   = new Set(["Müze","Sanat galerisi","Sanat merkezi"]);
const EGLENCE_PAHALI = new Set(["Aquapark","Tema parkı","Kumarhane"]);
const EGLENCE_BILETLI= new Set(["Sinema","Tiyatro","Canlı müzik","Bowling",
  "Oyun salonu","Kaçış oyunu","Buz pisti","Trambolin parkı","Mini golf",
  "Hayvanat bahçesi","Akvaryum","Etkinlik alanı","Oyun merkezi","Dans salonu"]);

/* Eğlence türleri tek tek çip olamayacak kadar çok. Çip "grup:eglence"
   değerini taşır; süzgeç burada üyeliğe çevirir. Böylece çip mantığı ve URL
   biçimi değişmeden kalıyor. */
const TUR_GRUP = {
  eglence: new Set(["Gece kulübü","Sinema","Tiyatro","Canlı müzik",
    "Sanat merkezi","Etkinlik alanı","Kumarhane","Bowling","Oyun salonu",
    "Kaçış oyunu","Aquapark","Buz pisti","Trambolin parkı","Mini golf",
    "Dans salonu","Oyun merkezi","Müze","Tema parkı","Hayvanat bahçesi",
    "Akvaryum","Sanat galerisi"]),
  yeme: new Set(["Kafe","Restoran","Fast food","Dondurma","Bar","Pub"])
};

/* ---------- kategoriler: tür VE mutfak ----------
   BİR HATA DÜZELTİLDİ. "Kahvaltı, Tatlı ve Esnaf lokantası bu veride
   yok" demiştim; yanlış alana bakmışım. Üçü de `tur` alanında değil
   `mutfak` alanında duruyor ve sayıları küçük değil (81 il, sayım):

       Kahvaltı  breakfast                            313
       Tatlı     dessert, cake, ice_cream, waffle…    850
       Esnaf     turkish, kebab, pide, soup…        4.302
       Kahve     coffee_shop, tea + tur:Kafe       11.000

   Esnaf lokantası, çip olarak koyduğum Gezilecek'ten (2.521) büyük.

   ÖRTÜŞME SERBEST ve bilerek: bir kebapçı hem "Yemek" (tur:Restoran)
   hem "Esnaf lokantası" (mutfak:kebab). Kullanıcının sorduğu şey tür
   değil CANI NE ÇEKTİĞİ; bir mekan iki isteğe birden cevap verebilir.
   Süzgeç birleşim (OR) aldığı için aynı mekan listede iki kez çıkmıyor. */
const KATEGORI = {
  kahvalti:  { ad:"Kahvaltı",        tur:[],                mutfak:["breakfast"] },
  kahve:     { ad:"Kahve",           tur:["Kafe"],
               mutfak:["coffee_shop","coffee","cafe","tea"] },
  yemek:     { ad:"Yemek",           tur:["Restoran"],      mutfak:[] },
  tatli:     { ad:"Tatlı",           tur:["Dondurma"],
               mutfak:["dessert","cake","ice_cream","waffle","chocolate",
                       "donut","bakery","baklava","patisserie","candy"] },
  icecek:    { ad:"İçecek",          tur:["Bar","Pub"],     mutfak:[] },
  hizli:     { ad:"Fast food",       tur:["Fast food"],     mutfak:[] },
  esnaf:     { ad:"Esnaf lokantası", tur:[],
               mutfak:["turkish","kebab","pide","soup","meyhane","lokanta"] },
  gezilecek: { ad:"Gezilecek",       tur:["grup:eglence"],  mutfak:[] }
};

/* ---------- kartın görsel yuvası ----------

   "Ekranda resimler olsun" istendi. ÖLÇÜLDÜ VE BUGÜN TEK BİR FOTOĞRAF
   YOK: il dosyalarında `foto` alanı hiç yok, `foto_cek.py` bir kez bile
   koşmamış (`mekan_foto.csv` üretilmemiş) ve kullanıcı yüklemeleri
   Supabase'de duruyor -- keşfet listesi ise tamamen statik, hiç
   Supabase'e çıkmıyor.

   Her karta BOŞ bir kutu koymak, kutu koymamaktan kötü olurdu: 35.852
   mekanın hepsi aynı gri dikdörtgenle listelenirdi ve liste "yükleniyor"
   gibi görünürdü. Onun yerine yuva HER ZAMAN DOLU -- mekanın kategori
   simgesi. Fotoğraf geldiği gün aynı yuvaya giriyor, kart düzeni
   değişmiyor.

   RENK BİLGİ TAŞIMIYOR, ŞEKİL TAŞIYOR. Sekiz kategoriye sekiz renk
   uydurmak iki temada da kontrast sorunu demekti ve renk zaten bu
   ekranda BÜTÇE BANDININ dili -- ikinci bir renk dili onu boğardı.
   Ayrım simgenin şeklinde. (Güven noktasındaki kural ile aynı.)

   SIRA ÖZELDEN GENELE: "yemek" ölçütü Restoran'ın tamamını yakalıyor,
   o yüzden en sonda. "gezilecek" en başta -- bir müze yemek mekanı
   değil ve müzenin türü hiçbir yemek ölçütüne uymasa da listede
   simgesiz kalmamalı. */
const KART_KATEGORI = ["gezilecek", "kahvalti", "tatli", "kahve",
                       "icecek", "hizli", "esnaf", "yemek"];

/* 24x24, yalnız çizgi (stroke) -- arayüzün geri kalanındaki simgelerle
   aynı dil: stroke-width 2, yuvarlak uç. */
const KATEGORI_SIMGE = {
  gezilecek: '<path d="M3 21h18M5 21V10M9.5 21V10M14.5 21V10M19 21V10M2.5 10 12 3l9.5 7"/>',
  /* CAY BARDAGI. Iki deneme elendi ve ikisi de BUYUTULUP BAKILINCA
     goruldu: tavada yumurta 26 px'te salyangoz, sahanda yumurta ise
     hedef tahtasi (ic ice iki daire) gibi okunuyordu. Ince belli
     bardak hem kahve kupasindan (kulplu, buharli) hem kokteyl
     bardagindan (ucgen) ayriliyor -- ve Turkiye'de kahvaltinin
     simgesi zaten o. */
  kahvalti:  '<path d="M8.4 4h7.2l-1.15 12.4a2.45 2.45 0 0 1-4.9 0z"/>' +
             '<path d="M7.4 20h9.2"/>',
  /* KAP KEK. Dondurma kulahi denendi ve 26 px'te KONUM IGNESI gibi
     okunuyordu -- ustelik igne bu ekranda "Konumum" dugmesinin simgesi,
     yani iki ayri sey ayni sekle dusuyordu. Kagit kalibi + kubbe +
     ustundeki tane, kahve kupasiyla karismiyor. */
  tatli:     '<path d="M6.6 11.6h10.8l-1.25 7.5a1.2 1.2 0 0 1-1.2 1H9.05' +
             'a1.2 1.2 0 0 1-1.2-1z"/>' +
             '<path d="M7.2 11.6a4.8 4.8 0 0 1 9.6 0"/>' +
             '<circle cx="12" cy="5" r="1.15"/>',
  kahve:     '<path d="M4 8h12v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z"/>' +
             '<path d="M16 9.5h2a2.5 2.5 0 0 1 0 5h-2"/><path d="M6 3v2M10 3v2M14 3v2"/>',
  icecek:    '<path d="M4 4h16l-8 9z"/><path d="M12 13v6M8.5 19h7"/>',
  hizli:     '<path d="M4 10a8 4 0 0 1 16 0z"/><path d="M3 13.5h18"/>' +
             '<path d="M3 16h18a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 16z"/>',
  esnaf:     '<path d="M4.5 16h15"/><path d="M5.5 16a6.5 6.5 0 0 1 13 0"/>' +
             '<path d="M12 9.5V7.5"/><path d="M8 19.5h8"/>',
  yemek:     '<path d="M6.5 3v7a2.5 2.5 0 0 0 5 0V3"/><path d="M9 10.5V21"/>' +
             '<path d="M17.5 3c-1.6 2-2.3 4-2.3 6.2 0 1.7.8 2.6 2.3 2.6V21"/>'
};

/* Mekanın kart simgesinde kullanılacak kategorisi. Hiçbirine uymuyorsa
   null -- o zaman yuvaya nötr bir işaret giriyor, uydurma bir kategori
   değil. */
function anaKategori(m){
  for (const k of KART_KATEGORI) if (mekanUyar(["kat:" + k], m)) return k;
  return null;
}

/* Kartın 56x56 görsel yuvası: fotoğraf varsa fotoğraf, yoksa simge.

   ATIF. Commons fotoğrafları serbest lisanslı ama ATIF ZORUNLU (CC BY /
   CC BY-SA). 56 pikselin içine yazar adı ve lisans sığmıyor, o yüzden:
   küçük resimde atıf `alt` ve `title` ile taşınıyor, GÖRÜNÜR hâli ise
   bir dokunuş ötedeki mekan sayfasında duruyor. Bu bir KARAR, ihmal
   değil -- ve sıkılaştırmak gerekirse tek yer burası.

   `sahip` ve `kullanici` fotoğrafları bizim gösterme hakkımız olan
   fotoğraflar; onlarda atıf yükümlülüğü yok, alt metni yine mekanın
   adını söylüyor.

   YÜKLENEMEYEN RESİM GİZLENMİYOR, burada gizlenemez de: ortak.js'in
   resimHatalariniGizle'si `[data-resim]` kabını gizliyor ve o kap
   burada YUVANIN KENDİSİ olurdu -- kutu kaybolur, kart zıplardı.
   Onun yerine <img> hata alınca kendini gizliyor ve altındaki simge
   ortaya çıkıyor: yuva her hâlükârda dolu. */
function kartGorselHTML(m, foto){
  const k = anaKategori(m);
  const simge =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    (KATEGORI_SIMGE[k] || '<circle cx="12" cy="12" r="7"/>') +
    "</svg>";
  let resim = "";
  if (foto && foto.adres){
    const atif = foto.kaynak === "commons" && foto.yazar
      ? "Fotoğraf: " + foto.yazar + (foto.lisans ? " (" + foto.lisans + ")" : "")
      : "";
    const metin = (m && m.ad ? m.ad : "") + (atif ? " — " + atif : "");
    resim = '<img src="' + kacir(foto.adres) + '" alt="' + kacir(metin) + '"' +
            (atif ? ' title="' + kacir(atif) + '"' : "") +
            /* data-yedekli: yuklenemezse KENDINI gizler ve altindaki
               simge ortaya cikar. Inline onerror KULLANILAMAZ --
               script-src 'unsafe-inline' tasimiyor, tarayici o
               ozniteligi sessizce calistirmazdi. */
            ' loading="lazy" decoding="async" data-yedekli>';
  }
  return '<span class="kart-gorsel" data-kat="' + (k || "yok") + '">' +
    simge + resim + "</span>";
}

/* "kebab;barbecue;coffee_shop" -> Set. Küçük harfe çevriliyor: OSM
   etiketleri çoğunlukla küçük ama hepsi değil. */
function mutfaklar(m){
  const k = new Set();
  for (const x of String((m && m.mutfak) || "").toLowerCase().split(";")){
    const y = x.trim();
    if (y) k.add(y);
  }
  return k;
}

/* Bir mekan seçili ölçütlerden HERHANGİ birine uyuyor mu.

   ÜÇ SEÇİCİ BİÇİMİ, hepsi geriye dönük uyumlu:
     "Kafe"           düz tür adı        (eski bağlantılar, saha kartları)
     "grup:eglence"   tür kümesi         (eski)
     "kat:esnaf"      kategori — tür VE mutfak birlikte      (yeni)

   İmza `tur` değil MEKAN alıyor: mutfak ölçütü tür adından okunamaz.
   Eski adı (turUyar) bırakmadım -- iki kapı bırakmak, birinin mutfağı
   görmediği bir çağrı yolu bırakmak olurdu. */
function mekanUyar(secili, m){
  const tur = m && m.tur;
  let mut = null;
  for (const s of secili){
    if (s.slice(0, 5) === "grup:"){
      const g = TUR_GRUP[s.slice(5)];
      if (g && g.has(tur)) return true;
    } else if (s.slice(0, 4) === "kat:"){
      const k = KATEGORI[s.slice(4)];
      if (!k) continue;
      for (const t of k.tur){
        if (t.slice(0, 5) === "grup:"){
          const g = TUR_GRUP[t.slice(5)];
          if (g && g.has(tur)) return true;
        } else if (t === tur) return true;
      }
      if (k.mutfak.length){
        if (mut === null) mut = mutfaklar(m);
        for (const x of k.mutfak) if (mut.has(x)) return true;
      }
    } else if (s === tur) return true;
  }
  return false;
}

/* Menudeki en ucuz kalem neredeyse her zaman bir ICECEK. m.min'i fiyat diye
   gostermek pahali bir baligiyi "25 TL'den baslar" yapiyordu (Milos Balik:
   min=25 "Aci Bal", ana yemek 350-590 TL). Kullaniciya lazim olan sey
   "burada bir YEMEK kac lira" -- icecek ve tatli disi kategorilerin medyani. */
const ICECEK_KAT = new Set(["Ayran","Kola / gazlı","Meyve suyu","Su","Filtre kahve",
  "Espresso","Çay","Türk kahvesi","Latte","Americano","Rakı / içkiler","Matcha",
  "Şarap","Bira","Sıcak çikolata"]);
const TATLI_KAT = new Set(["Tatlı","Dondurma"]);

/* Tema demosu esigi. 2026-08 fiyatlariyla bir ogun bunun altinda olmaz;
   enflasyonla birlikte yukseltilmeli, yoksa gercek ucuz yerleri eler. */
const YEMEK_ALT_SINIR = 80;

/* Tek kalemden yemek fiyati cikarilmiyor.
   Olculen vaka: Kahve Dunyasi'nin 74 subesinde menu olarak alinan sey
   perakende urun katalogu (250 g cekirdek, tablet cikolata, 10'lu paket).
   Bunlardan yalniz BIRI kategorilenebiliyordu -- "Tatli: 1 kalem @350" --
   ve 74 kafenin kartinda "yemek ~350 TL" yaziyordu. Tek basina duran
   Redbox "Balik 1@900", Nebyan "Kebap 1@910" da ayni sinifta.

   Gerekce fis katmanindakiyle ayni: tek fis bir kisinin o gunku secimidir,
   mekanin fiyati degil. Tek kalem de bir urunun fiyatidir, menunun degil.
   Iki kalem zayif ama gercek bir sinyal; olculdu: esigi 2 yapmak 264
   mekanin 99'undan iddiayi kaldiriyor ve kalkanlarin 74'u o tek zincir. */
const YEMEK_ASGARI_KALEM = 2;
const TR_HARF = /[çğıöşüÇĞİÖŞÜ]/;

/* ---------- fiyatin yasi ----------
   Enflasyonda tarihsiz fiyat bir iddia degil, bir tahmindir. Veri artik her
   mekanin menusuyle birlikte derlendigi AYI da tasiyor (m.tarih = "YYYY-AA",
   kalemlerin en eskisi -- yeni kalem eskisini tazelemez).

   Uc bant, tek gerekce: bu uygulamanin isi ucuz yeri pahali yerden ayirmak.
   Turkiye'de yillik enflasyon o ayrimin kendisinden buyuk oldugu icin bir
   yasin otesinde sayi, dogru sirayi bile vermiyor.

     0-6 ay    tarih yazilir, baska bir sey denmez
     6-12 ay   tarih "eski" isaretiyle yazilir
     12+ ay    SAYI GOSTERILMEZ -- mekan olculmemis mekanlar gibi davranir

   Sinir yemekFiyati()'nin icinde: fiyati kim sorarsa sorsun (kart, butce
   suzgeci, detay basligi, "fiyati bilinen" filtresi) ayni cevabi alsin.
   Ayni kural tek yerde dursun. */
const FIYAT_TAZE_AY = 6;
const FIYAT_SON_AY  = 12;

const AY_ADI = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"];

/* "2026-08" -> Ocak 1970'ten beri gecen ay sayisi; bozuksa null. */
function _ayNo(tarih){
  const e = /^(\d{4})-(\d{2})/.exec(tarih || "");
  if (!e) return null;
  const ay = +e[2];
  if (ay < 1 || ay > 12) return null;
  return (+e[1]) * 12 + (ay - 1);
}

/* Fiyatin kac aylik oldugu. Tarihsiz veri null doner: yasi BILINMIYOR,
   sifir degil. Ileriye donuk tarih de null -- saati yanlis kurulmus bir
   cihaz yuzunden fiyat gizlenmesin. */
function fiyatYasi(m, bugun){
  const t = _ayNo(m && m.tarih);
  if (t == null) return null;
  const d = bugun || new Date();
  const su = d.getFullYear() * 12 + d.getMonth();
  return su >= t ? su - t : null;
}

/* Ekranda okunacak hali: "Ağustos 2026". Tarih yoksa bos. */
function fiyatTarihi(m){
  const e = /^(\d{4})-(\d{2})/.exec((m && m.tarih) || "");
  return e ? AY_ADI[+e[2] - 1] + " " + e[1] : "";
}

/* Fiyatin yas etiketi: {ad, eski} ya da null. */
function fiyatYasEtiketi(m, bugun){
  const ay = fiyatYasi(m, bugun);
  const tarih = fiyatTarihi(m);
  if (!tarih) return null;
  return { ad: tarih, eski: ay != null && ay >= FIYAT_TAZE_AY };
}

/* Mekanin ANA URUN turu(leri).

   Icecegi ve tatliyi elemek yetmiyordu: Domino's'ta pizza 15 kalem @480 TL
   ama yaninda "Citir Tavuk Toplari / Tavuk Parcalari" 7 kalem @185 TL ve
   "Algida Magnum Sandwich" tost sayilmis 1 kalem @105 TL duruyor. Hepsinin
   ortalamasi 428 TL cikiyordu -- garnitur, pizzacinin fiyatini asagi
   cekiyor. 400 TL'lik pizzayla 15 TL'lik suyu ortalamak ne kadar sacmaysa
   patates kizartmasiyla ortalamak da oyle.

   Global bir "su kategoriler ana yemektir" listesi TUTULMUYOR, cunku ayni
   kategori mekana gore degisiyor: borekcide poğaça ana urun, kebapcida yan.
   Onun yerine mekanin KENDI dagilimina bakiliyor -- en cok kalemi olan tur
   o mekanin ana urunu; hacmi ona yakin olanlar (yarisi kadar ve ustu) da
   sayiliyor ki dengeli menuler tek ture indirgenmesin.

   Olculdu (165 mekan): 132'sinde fiyat yukseldi, 15'inde dustu, ortalama
   kayma +67 TL. Yon dogru -- yan urunler fiyati sistematik olarak asagi
   cekiyormus. */
const ANA_URUN_ORANI = 0.5;

function anaKategoriler(m){
  const kat = m.kat;
  if (!kat) return null;                  /* kategori yoksa icecegi ayiramayiz */
  let ana = Object.keys(kat).filter(k => !ICECEK_KAT.has(k) && !TATLI_KAT.has(k));
  /* Yalniz tatli varsa (pastane) tatli ana urundur. */
  if (!ana.length) ana = Object.keys(kat).filter(k => TATLI_KAT.has(k));
  if (!ana.length) return null;
  const enCok = Math.max.apply(null, ana.map(k => kat[k].n));
  return ana.filter(k => kat[k].n >= enCok * ANA_URUN_ORANI);
}

function yemekFiyati(m, bugun){
  const kat = m.kat;
  const ana = anaKategoriler(m);
  if (!ana) return null;

  /* Bir yildan eski fiyat sayi olarak gosterilmez. Bkz. FIYAT_SON_AY. */
  const yas = fiyatYasi(m, bugun);
  if (yas != null && yas >= FIYAT_SON_AY) return null;

  /* ORTALAMA. Onceden kategori medyanlarinin medyani aliniyordu; o, "tipik
     bir kalem kac lira" sorusunun cevabiydi. Kullanicinin sordugu soru
     "burada kaca oturulur" -- menunun tamamini temsil eden sey ortalama.
     kat[k].top kategorinin fiyat TOPLAMI, n kalem sayisi; ikisinin orani
     mekanin gercek aritmetik ortalamasi (kirpilmamis tam listeden). */
  let toplam = 0, adet = 0;
  for (const k of ana){
    /* top yoksa eski veri: kategori medyanini n kere sayarak yaklas. */
    toplam += kat[k].top != null ? kat[k].top : kat[k].med * kat[k].n;
    adet   += kat[k].n;
  }
  if (adet < YEMEK_ASGARI_KALEM) return null;
  const orta = Math.round(toplam / adet);

  /* Tema demosu: WordPress sablonundan gelen menuler Ingilizce ve ucuzdur
     ("Fish Tacos" 32 TL). Ikisi birden ise guvenme -- yanlis ucuzluk bu
     uygulamada yapilabilecek en kotu hata. */
  if (orta < YEMEK_ALT_SINIR){
    const mn = m.menu || [];
    if (mn.length >= 8 && !mn.some(k => TR_HARF.test(k.a))) return null;
  }
  return orta;
}

function seviye(m, bugun){
  const yf = yemekFiyati(m, bugun);
  if (yf != null)
    return { sinif:"olcum", ad:"ortalama " + tl(yf), olculdu:true };
  if (m.tur === "Fast food" || m.tur === "Dondurma")
    return { sinif:"hesapli", ad:"hesaplı" };
  const mut = (m.mutfak || "").toLowerCase().split(/[;,]/).map(x => x.trim());
  if (mut.some(x => MUTFAK_UST.has(x)))     return { sinif:"ust",     ad:"üst segment" };
  if (mut.some(x => MUTFAK_HESAPLI.has(x))) return { sinif:"hesapli", ad:"hesaplı" };
  if (m.tur === "Bar" || m.tur === "Pub")   return { sinif:"icki",    ad:"içki mekanı" };
  if (EGLENCE_UCUZ.has(m.tur))  return { sinif:"hesapli", ad:"hesaplı" };
  if (EGLENCE_PAHALI.has(m.tur))return { sinif:"ust",     ad:"biletli, pahalı" };
  if (EGLENCE_BILETLI.has(m.tur))return { sinif:"biletli", ad:"biletli" };
  return null;
}

/* ============================================================
   BÜTÇE: ne biliyoruz, ne bilmiyoruz

   Ana ekran artık bütçeyle başlıyor ("Bugün cebimde ₺300"). Bu blok o
   sorunun cevabını tek yerde topluyor.

   ÖNCE ÖLÇÜM, SONRA TASARIM. Bütçenin listeyi ne kadar değiştirdiği
   sayıldı -- 3 km'lik altı gerçek semt çemberinde:

     Kadıköy   1.096 mekan, ₺300 ile elenen  36  (%3,3)
     Beyoğlu   2.203 mekan, ₺300 ile elenen  81  (%3,7)
     Kızılay     599 mekan, ₺300 ile elenen  16  (%2,7)
     Alsancak    483 mekan, ₺300 ile elenen  18  (%3,7)
     Muratpaşa   469 mekan, ₺300 ile elenen  24  (%5,1)

   Yani BÜTÇE SÜZGEÇ OLARAK NEREDEYSE HİÇBİR ŞEY YAPMIYOR: 35.852
   mekanın 163'ünde (%0,45) ölçülmüş menü fiyatı var, gerisinde yok.
   ₺150 ile ₺700 arasındaki fark Kadıköy'de 37 mekana karşı 28 mekan --
   elenenlerin çoğu bütçeden değil "üst segment" etiketinden geliyor.

   O YÜZDEN BÜTÇE BURADA SÜZGEÇ DEĞİL, SINIFLANDIRICI. Her mekan için
   beş cevaptan biri veriliyor ve hangisinin ÖLÇÜM hangisinin TAHMİN
   olduğu cevabın içinde duruyor:

     girer      ölçülmüş fiyat var ve bütçenin altında      (kesin)
     asiyor     ölçülmüş fiyat var ve bütçenin üstünde      (kesin)
     muhtemel   ölçüm yok; türü/mutfağı hesaplı gösteriyor  (tahmin)
     zor        ölçüm yok; türü/mutfağı üst segment diyor   (tahmin)
     bilinmiyor hiçbir sinyal yok                           (iddia yok)

   Ekran bu ayrımı SAKLAMIYOR, yazıyor. Bir süzgeç "441 mekandan 12'si"
   deseydi kullanıcı 12'sinin ölçüldüğünü sanırdı; bu depodaki kural
   açık: yanlış fiyat, fiyat olmamasından kötüdür.

   Karşılaştırmanın kendisi YENİDEN YAZILMIYOR: kesin cevap bant()'tan,
   tahmin seviye()'den geliyor. İkisi de zaten kart, harita ve süzgeç
   tarafından kullanılıyor -- aynı kural tek yerde dursun.
   ============================================================ */

/* Ana ekrandaki hızlı seçim. Rakamlar burada duruyor ki ekran onları
   kendi içinde ikinci kez tanımlamasın. */
const BUTCE_SECENEK = [150, 250, 400, 700];

/* Elle yazılan bütçenin sınırları. Üst sınır uydurma değil: ölçülmüş
   163 fiyatın en pahalısı ₺1.097 ve kişi başı ₺5.000, Türkiye'de bir
   öğün için üst sınırın çok ötesi. Alt sınır bir çayın altına düşmesin
   diye var -- ₺0 "farketmez" demek ve ayrı ele alınıyor. */
const BUTCE_EN_AZ = 20, BUTCE_EN_COK = 5000;

/* Kullanıcının yazdığını sayıya çevirir. "300", "300 TL", "1.250",
   "₺300" hepsi kabul; çözülemeyen ya da sınır dışı olan 0 döner --
   yani "farketmez". Sessizce bir sayıya YUVARLANMIYOR: ₺9'u ₺20 yapıp
   "bütçen ₺20" demek kullanıcının söylemediği bir şeyi söylemek olurdu. */
function butceOku(ham){
  if (ham == null) return 0;
  /* Binlik ayıracı nokta, ondalık virgül (tr-TR). Ondalık kısım bütçede
     anlamsız, atılıyor. */
  const s = String(ham).replace(/[^\d,.]/g, "").replace(/\./g, "").split(",")[0];
  const n = parseInt(s, 10);
  if (!Number.isFinite(n) || n < BUTCE_EN_AZ || n > BUTCE_EN_COK) return 0;
  return n;
}

/* Tek bir mekan için bütçenin cevabı. Bütçe yoksa null: soru
   sorulmadıysa cevap uydurulmuyor. */
function butceDurumu(m, butce, bugun){
  if (!(butce > 0)) return null;
  /* Kesin taraf: ölçülmüş fiyatla karşılaştırma. Karşılaştırmayı bant()
     yapıyor, burada tekrar edilmiyor. */
  const b = bant(m, butce, bugun);
  if (b) return b.sinif === "ucuz"
    ? { sinif:"girer",  ad:"bütçene giriyor", kesin:true }
    : { sinif:"asiyor", ad:"bütçe üstü",      kesin:true };
  /* Tahmin tarafı: tür ve mutfak etiketi. */
  const s = seviye(m, bugun);
  if (!s)                    return { sinif:"bilinmiyor", ad:"fiyat bilinmiyor", kesin:false };
  if (s.sinif === "hesapli") return { sinif:"muhtemel",   ad:"hesaplı görünüyor", kesin:false };
  if (s.sinif === "ust")     return { sinif:"zor",        ad:s.ad,                kesin:false };
  /* "içki mekanı" ve "biletli" gerçek bilgi ama bütçe sorusunun cevabı
     değil: ₺300 bir bara yeter mi, bunu söyleyecek verimiz yok. Etiket
     korunuyor, iddia korunmuyor. */
  return { sinif:"bilinmiyor", ad:s.ad, kesin:false };
}

/* Bir listenin bütçe dökümü. Ekrandaki bütün sayılar buradan çıkıyor;
   sayfa hiçbir rakamı kendi saymıyor. */
function butceOzeti(liste, butce, bugun){
  if (!liste || !(butce > 0)) return null;
  const o = { toplam:liste.length, girer:0, asiyor:0, muhtemel:0, zor:0, bilinmiyor:0 };
  for (const m of liste){
    const d = butceDurumu(m, butce, bugun);
    if (d) o[d.sinif]++;
  }
  o.olculdu = o.girer + o.asiyor;
  o.tahmin  = o.muhtemel + o.zor;
  return o;
}

/* Dökümü Türkçeye çevirir. Bu cümle ürünün en önemli cümlesi: bütçenin
   ne kadarının ÖLÇÜLDÜĞÜNÜ, ne kadarının TAHMİN olduğunu söylüyor.
   Sıfır bir başarısızlık değil, katkı çağrısı -- fiş eşiğiyle aynı
   desen. */
function butceCumlesi(o, butce){
  if (!o || !(butce > 0) || !o.toplam) return null;
  if (!o.olculdu)
    return "Buradaki hiçbir mekanın menü fiyatı ölçülmedi. " + tl(butce) +
           " yeter mi, söyleyemem — fiyatı gidenler yazıyor.";
  const kalan = o.toplam - o.olculdu;
  const bas = sayi(o.olculdu) + " mekanın menü fiyatı ölçüldü, " +
              (o.girer ? sayi(o.girer) + " tanesi " + tl(butce) + " altında"
                       : "hiçbiri " + tl(butce) + " altında değil") + ".";
  if (!kalan) return bas;
  return bas + " Kalan " + sayi(kalan) + " mekan için " + tl(butce) +
         " yeter mi bilmiyorum; türünden tahmin ediyorum.";
}

/* ---------- ana ekranın kategorileri ----------
   DÖRT ÇİP. Marka maketindeki "Bütçeni Gir" ekranında dört daire var;
   ekran altı çiple iki satıra taşıyordu ve maketteki tek işli görüntüyü
   bozuyordu.

   HANGİ DÖRDÜ, SAYIMLA (81 il, 35.852 mekan, mekanUyar ile):

       Yemek     (tur:Restoran)            14.587   %40,7
       Kahve     (Kafe + coffee_shop, tea) 11.000   %30,7
       Fast food (tur:Fast food)            6.091   %17,0
       Esnaf     (turkish, kebab, pide…)    4.302   %12,0   <- dördüncü
       ---------------------------------------------
       Gezilecek                            2.521   %7,0
       İçecek                               1.443   %4,0
       Tatlı                                  850   %2,4
       Kahvaltı                               313   %0,9

   DÖRDÜNCÜ SIRA DEĞİŞTİ. Önce buraya Gezilecek yazmıştım, çünkü
   "Esnaf lokantası bu veride yok" sanıyordum -- yanlış alana (`tur`)
   bakmışım. Mutfak ekseni sayılınca Esnaf 4.302 çıktı ve Gezilecek'i
   geçti. Gezilecek keşfet ekranında duruyor.

   Dört çip mekanların %94,9'unu kapsıyor. Seçim hevese göre değil; iki
   düşen çip birlikte %5,1.

   DÜŞENLER ÜRÜNDEN KAYBOLMUYOR. Ana ekran "canın ne çekti" kısayolu,
   keşfet ekranı tam süzgeç: Bar ve Pub çipleri keşfette zaten vardı,
   DONDURMA YOKTU ve eklendi. Olmasaydı bu değişiklik 395 dondurmacıyı
   aramanın dışında hiçbir yoldan ulaşılamaz yapardı.

   "Tatlı" diye bir çip YOK: verideki tür "Dondurma" ve 395 tane. Çipe
   "Tatlı" deyip dondurmacı listelemek, olmayan bir kapsamı vaat etmek
   olurdu.

   Eğlence tarafı tek tek çip olamayacak kadar parçalı; keşfet ekranının
   zaten kullandığı "grup:eglence" değeri taşınıyor. Gece kulübü O
   GRUBUN İÇİNDE. */
const CANIM = ["kahve", "yemek", "hizli", "esnaf"].map(k =>
  ({ anahtar: k, ad: KATEGORI[k].ad, tur: ["kat:" + k] }));

/* ============================================================
   FİYATIN DAYANAĞI: bu rakam kaç ölçümden geliyor?

   ÖLÇÜLDÜ, ve sonuç ürünü değiştirdi. Menü fiyatı gösterilebilen 163
   mekan sayıldığında altından şu çıktı:

     163 mekan  ->  53 FARKLI İŞLETME
     94 tanesi Domino's şubesi (%58), 10 tanesi Papa John's

   Yani ekranda "163 mekanda ölçülmüş fiyat var" yazarken aslında iki
   pizza zinciri listenin %64'ünü dolduruyor. Daha kötüsü: aynı ilde
   çok şubesi olan 113 mekanın HİÇBİRİNDE şubeler arası fiyat farkı
   yok -- yani menü bir kez kazınmış ve 56 ayrı ölçümmüş gibi
   gösteriliyor.

   BU, TEK FİŞİ MEKANIN FİYATI SAYMAKLA AYNI HATA. Depoda o hata
   FIS_ESIK ile kapatıldı ("tek fiş bir kişinin o günkü seçimidir,
   mekanın fiyatı değil"). Aynı gerekçe burada da geçerli: tek kazıma
   56 şubenin ölçümü değildir. Bu blok rakamı KALDIRMIYOR -- rakam
   gerçek -- ama neye dayandığını söylüyor.

   YAŞ EKSENİ BUGÜN BOŞ. Yol haritasındaki üç renkli güven skoru için
   önce fiyat yaşına bakıldı: menüsü olan 264 mekanın 264'ü de 0-2
   aylık. Yani yaşa dayalı bir skor bugün herkesi yeşile boyar ve
   hiçbir şey söylemez. Kalem sayısı da işe yaramadı: "15+ kalem"
   bandındaki 120 mekan yalnız 17 farklı ad ve çoğu Domino's. Gerçekten
   AYRIŞAN tek eksen bu: fiyat bu mekanın kendi menüsünden mi geliyor
   (50 mekan, %31) yoksa şubelerle paylaşılan bir zincir menüsünden mi
   (113 mekan, %69).
   ============================================================ */

/* Aynı ilde bu kadar şube aynı fiyatı taşıyorsa "zincir menüsü". */
const ZINCIR_ESIK = 2;

/* Ad normalleştirme. kesfet.js'teki sade() KULLANILMIYOR: o arama için
   yazıldı ve Türkçe harfleri de düşürüyor ("Çınar" -> "cinar"). Arama
   için doğru, burada tehlikeli -- iki AYRI işletmeyi aynı zincir sayıp
   birinin fiyatına "12 şubede aynı" yazdırabilir. Burada az eşleştirmek
   çok eşleştirmekten iyi. */
function _adAnahtari(ad){
  return String(ad || "").trim().replace(/\s+/g, " ").toLocaleLowerCase("tr");
}

/* "ad + fiyat" -> kaç mekan. Fiyat da anahtarda: aynı adı taşıyan ama
   AYRI AYRI kazınmış (dolayısıyla farklı fiyatlı) iki yer, iki ayrı
   ölçümdür ve öyle sayılmalı. */
function zincirHaritasi(mekanlar, bugun){
  const h = new Map();
  for (const m of (mekanlar || [])){
    const f = yemekFiyati(m, bugun);
    if (f == null) continue;
    const a = _adAnahtari(m.ad) + " " + f;
    h.set(a, (h.get(a) || 0) + 1);
  }
  return h;
}

/* Bu mekanın fiyatı neye dayanıyor.

   Harita YOKSA null dönüyor, "kendi menüsü" DEĞİL: il listesini
   yüklememiş bir ekran şube sayısını bilemez ve bilmediği şeyi
   "kendine ait" diye sunmamalı. */
function fiyatDayanagi(m, harita, bugun){
  const f = yemekFiyati(m, bugun);
  if (f == null || !harita) return null;
  const n = harita.get(_adAnahtari(m.ad) + " " + f) || 0;
  if (n < ZINCIR_ESIK)
    return { sinif:"kendi", sube:1, ad:"kendi menüsünden" };
  return { sinif:"zincir", sube:n, ad: sayi(n) + " şubede aynı menü" };
}

/* Mekan sayfasındaki tam cümle. Kart yalnız etiketi gösteriyor; burada
   NEDEN önemli olduğu da yazıyor, çünkü kullanıcı fiyata bakıp yola
   çıkacak. */
function dayanakCumlesi(d){
  if (!d) return "";
  if (d.sinif === "kendi")
    return "Bu fiyat bu işletmenin kendi yayımladığı menüden derlendi.";
  return "Bu fiyat, aynı ilde " + sayi(d.sube) + " şubesi listelenen bir " +
         "zincirin menüsünden geliyor — tek bir menüden. Şubeler farklı " +
         "fiyatlandırma yapabiliyor, o yüzden bu rakam şubeye özel değil.";
}

/* ============================================================
   FİYAT GÜVEN SKORU — yeşil / sarı / kırmızı

   Yol haritasının maddesi. İlk bakışta yazılamıyordu: fiyat yaşı bütün
   menülerde aynıydı (264 menünün 264'ü de 0-2 aylık) ve kalem sayısı
   yanıltıyordu ("15+ kalem" bandındaki 120 mekan yalnız 17 farklı ad).
   Üç renge bölecek gerçek bir eksen yoktu.

   Zincir ölçümü o ekseni verdi. Bantlar SAYILDI (35.852 mekan):

     YEŞİL    50 (%0,14)   mekanın kendi menüsünden, taze
     SARI    113 (%0,32)   zincir menüsünden ya da eskimiş
     KIRMIZI 35.689 (%99,55) ölçülmüş fiyat yok

   Kırmızının bu kadar geniş olması skorun kusuru değil, VERİNİN
   DURUMU -- ve skorun işi tam olarak bunu söylemek. İçi de boş değil:
   17.013'ünde tür/mutfak tahmini var, 18.676'sında hiçbir sinyal yok.
   İkisi ayrı cümleyle anlatılıyor, ama ikisi de aynı renk: hiçbiri
   ölçüm değil.

   FİŞ YEŞİLE ÇIKARIYOR. Üç ayrı fiş gelmiş bir mekan, menüsü hiç
   olmasa da yeşil. Ürünün tezi bu: fiyatı işletme değil giden insan
   yazıyor. Yani skor katkı geldikçe BÜYÜYOR -- bugün 50 olan yeşil
   sayısı sahadan gelen fişlerle artıyor. Eşik FIS_ESIK ile aynı
   (k-anonimlik): tek fiş bir kişinin o günkü seçimidir.

   RENKLER MARKANIN KENDİ PALETİNDEN: Okyanus (#00BFA6), Gün Batımı
   (#FFB74D), Mercan (#FF5A5F). Yeni renk uydurulmadı.

   RENK TEK BAŞINA BİLGİ TAŞIMIYOR. Her rozetin yanında metin var ve
   `title` gerekçeyi yazıyor -- renk körlüğü bir yana, "sarı" tek başına
   neden sarı olduğunu söylemiyor.
   ============================================================ */

const GUVEN_ADI = { yesil:"doğrulanmış", sari:"dolaylı", kirmizi:"fiyat yok",
                    /* MENÜSÜ FİYATLI AMA ÖĞÜN FİYATI ÇIKMIYOR. Ayrı bir ad,
                       çünkü "fiyat yok" o mekanda YALAN: menüde 1.340 kalemin
                       fiyatı yazıyor (291 menülü mekanın 128'i bu halde).
                       Renk kırmızı kalıyor -- bir öğünün kaça geldiğini hâlâ
                       bilmiyoruz -- değişen yalnız yanlış olan cümle. */
                    menu:"öğün fiyatı yok" };

/* KAMPANYA SATIRI: bir ürün değil bir TEKLİF. Bayrağı app_veri.py
   koyuyor (fiyat_analiz.kampanya_mi) -- kural tek dilde, tek yerde.

   Ölçüldü: 291 menülü mekanın 96'sında 672 satır böyle ve o mekanların
   menü satırlarının %17'si. Fiyatları çarpıtmıyorlar; eksik olan ETİKET:
   "1 Alana 1 Bedava İçecek · 120 ₺" sıra menüde 120 liralık bir içecek
   gibi duruyordu.

   ATILMIYOR, AYRILIYOR: teklif gerçek ve bütçesine bakan için değerli.
   Kendi bölümünde gösteriliyor; kombine ve "bu civarda ne yenir"
   listesine girmiyor, çünkü ikisi de "bir öğün kaça gelir" sorusunun
   cevabı ve bir teklifin fiyatı tek porsiyonun fiyatı değil. */
function kampanyaMi(k){ return !!(k && k.p); }

/* Menünün sıradan kalemleri (kampanyasız) ve kampanyaları. */
function menuKalemleri(m){
  return ((m && m.menu) || []).filter(k => k && !kampanyaMi(k));
}
function kampanyalar(m){
  return ((m && m.menu) || []).filter(k => kampanyaMi(k) && k.a);
}

/* Menüde fiyatı yazan kalem var mı. yemekFiyati()'nin sorusundan FARKLI:
   o "bir öğün kaça gelir" diye soruyor, bu "ekranda rakam görünecek mi".

   KAMPANYA SAYILMIYOR: rozet "menüde N kalemin fiyatı var" diyor ve o
   cümle bir ürün fiyatı vaat ediyor. */
function menudeFiyatVar(m){
  const mn = m && m.menu;
  if (!mn || !mn.length) return 0;
  let n = 0;
  for (const k of mn) if (k && k.f != null && !kampanyaMi(k)) n++;
  return n;
}

/* Rakamla yazılmış bir sayıya 3. tekil iyelik eki: 9 -> "9'u".

   NEDEN GEREKLİ: ek, sayının OKUNUŞUNUN son hecesine bakıyor. "9'i"
   yanlış, "9'u" doğru; "3'i" yanlış, "3'ü" doğru. Ekranda iki yerde
   yanlış yazıyordu ("3 kişiden 3'i", "14 kişinin 9'i").

   Ek son SÖYLENEN kelimeden geliyor, sayının tamamından değil:
   14 = "on dört" -> dört -> "14'ü";  47 = "kırk yedi" -> "47'si".
   Sesli harfle biten okunuşlar kaynaştırma "s" alıyor (iki, altı,
   yedi, yirmi, elli). */
const _EK_BIR = ["ı", "i", "si", "ü", "ü", "i", "sı", "si", "i", "u"];
const _EK_ON  = ["u", "si", "u", "ı", "si", "ı", "i", "i", "ı"];

function sayiEki(n){
  const x = Math.abs(Math.floor(Number(n) || 0));
  /* SIFIR AYRI: bütün modlardan geçip "milyon" dalına düşüyordu ("0'u").
     Okunuşu "sıfır" ve eki "ı". Kontrol yakaladı. */
  if (!x) return "ı";
  if (x % 10) return _EK_BIR[x % 10];
  if (x % 100) return _EK_ON[Math.floor((x % 100) / 10) - 1];
  if (x % 1000) return "ü";                    /* yüz */
  if (x % 1000000) return "i";                 /* bin */
  return "u";                                  /* milyon */
}

/* "9" -> "9'u". Binlik ayraçlı hali de doğru: ek sayıdan hesaplanıyor,
   metinden değil. */
function sayiEkli(n){
  return sayi(n) + "'" + sayiEki(n);
}

/* ---------- sosyal fiyat doğrulama ----------
   "Bu fiyat hâlâ geçerli mi?" oylaması (veritabani/fiyat_oyu.sql).

   EŞİK ÜÇ, FİŞ EŞİĞİYLE AYNI GEREKÇE: tek kişinin "değişmiş" demesi bir
   kanı, üç ayrı kişininki bir sinyal. Sayım sunucuda (kişi sayıyor, oy
   değil) çünkü tarayıcı aynı kişinin iki oyunu ayırt edemez.

   OY EKRANDA GÖRÜLEN FİYATA AİT. Menü tazelenip rakam değişirse eski
   oylar yeni rakamı doğrulamış sayılmıyor -- sunucu da fiyata göre
   gruplu dönüyor, istemci de gösterdiği rakamın satırını seçiyor. */
const OY_ESIK = 3;

/* Gün sayısını okunur hale getirir: 0 -> "bugün", 3 -> "3 gün önce".

   ÜRÜN TARİFİNİN İSTEDİĞİ ŞEY. Rozetin yanında "son doğrulanma"
   yazması isteniyordu; oy tablosu bunun için doğru kaynak (birinin
   BUGÜN "hâlâ böyle" demesi) ama tarih ekrana hiç gelmiyordu.

   GÜN CİNSİNDEN, saat değil: saat kişiyi daraltır ve sorulan şey
   "ne kadar taze", "saat kaçta" değil. Sunucu da gün döndürüyor
   (fiyat_oy_ozeti.son_gun) -- biçim tek yerde. */
function gunOnce(gun){
  /* null/undefined/"" ONCE ELENIYOR. Number(null) SIFIR -- yani tarihi
     hic olmayan bir oy "bugün" diye görünürdü ve rozet, elimizde
     olmayan bir tazeliği iddia ederdi. Kontrol bunu yakaladı. */
  if (gun == null || gun === "") return "";
  const g = Math.floor(Number(gun));
  if (!isFinite(g) || g < 0) return "";
  if (g === 0) return "bugün";
  if (g === 1) return "dün";
  if (g < 30) return sayi(g) + " gün önce";
  const ay = Math.round(g / 30);
  if (ay < 12) return sayi(ay) + " ay önce";
  return sayi(Math.round(g / 365)) + " yıl önce";
}

/* ISO zaman damgasindan bugüne kaç gün. Bozuksa ya da ileri tarihliyse
   null -- gunOnce ile aynı kural: bilinmeyen yaş SIFIR DEĞİL.

   NEDEN VAR (ürün tarifi md.4, "kalem düzeyinde tarih"): kazınan menüde
   kalem başına tarih YOK ve uydurulamaz -- ölçüldü, 291 menülü mekanın
   291'inde bütün kalemler aynı gün derlenmiş, yani kalem tarihi mekan
   tarihinin birebir kopyası olurdu (bilgi taşımayan bayt).

   Kalem düzeyinde tarihi GERÇEKTEN olan tek veri kullanıcıdan gelen
   menü katkısı: menu_katkilari.olusturuldu. O tarih bugüne kadar
   çekiliyordu ama ekrana hiç gelmiyordu.

   ADI gunFarki DEĞİL: o ad kohort ölçümünde başka bir anlamla duruyor
   (iki gün arasındaki fark, yuvarlanmış, negatif olabilir). Birleştirmek
   ikisinden birini bozardı; ayrı iş, ayrı ad. */
function zamanYasi(zaman, simdi){
  if (!zaman) return null;
  const t = Date.parse(zaman);
  if (!isFinite(t)) return null;
  const fark = (simdi ? simdi.getTime() : Date.now()) - t;
  if (fark < 0) return null;         /* saati yanlis kurulmus cihaz */
  return Math.floor(fark / 86400000);
}

/* Oy özetinin okunabilir hali. Eşiğin altında SAYI VERİLMİYOR: iki
   kişinin oyu bir mekanın fiyatı hakkında hüküm değil (k-anonimlik,
   fiş eşiğiyle aynı desen) -- eşik yine katkı çağrısına dönüşüyor. */
function oyCumlesi(oy){
  if (!oy || !oy.kisi)
    return "Bu fiyat hâlâ geçerli mi? İlk söyleyen sen ol.";
  if (oy.kisi < OY_ESIK)
    return sayi(OY_ESIK - oy.kisi) + " kişi daha söyleyince sonucu yazacağım.";
  return oy.gecerli >= oy.degisti
    ? sayi(oy.kisi) + " kişiden " + sayiEkli(oy.gecerli) + " \"hâlâ böyle\" dedi."
    : sayi(oy.kisi) + " kişiden " + sayiEkli(oy.degisti) + " \"değişmiş\" dedi.";
}

/* ONAYIN RAF ÖMRÜ (ürün tarifi md.5: 🟢 0-7 gün, 🟡 8-30, 🔴 30+).

   Menü tarihi AY cinsinden geliyor (kazınan sayfada gün yok), o yüzden
   gün eşiği menüye uygulanamıyor -- FIYAT_TAZE_AY orada duruyor. Ama
   OYUN günü var ve bu eşikler tam ona ait: birinin bugün "hâlâ böyle"
   demesiyle 40 gün önce demesi aynı şey değil.

   30 günü geçen onay rozeti KIRMIZIYA ÇEVİRMİYOR, sadece HÜKÜM VERMEYİ
   BIRAKIYOR: karar menü kanıtına düşüyor. Eski bir "hâlâ böyle" oyu
   fiyatın yanlış olduğunun kanıtı değil, doğru olduğunun kanıtı
   olmaktan çıkması. Aksi yön, bir onayı cezaya çevirirdi.

   Sunucunun kendi penceresi 180 gün (fiyat_oy_ozeti); bu eşik onun
   içinde daha dar bir kapı, çelişki değil. */
const OY_TAZE_GUN = 7;
const OY_SON_GUN  = 30;

/* Oyun kaç günlük olduğu; bilinmiyorsa null (sıfır DEĞİL). */
function oyYasi(oy){
  const g = oy && oy.son_gun;
  if (g == null || g === "") return null;
  const n = Math.floor(Number(g));
  return isFinite(n) && n >= 0 ? n : null;
}

/* Oy eşiği geçildi mi ve sonuç ne. null = hüküm yok. */
function oyKarari(oy){
  if (!oy || oy.kisi < OY_ESIK) return null;
  return oy.gecerli >= oy.degisti ? "gecerli" : "degismis";
}

function fiyatGuveni(m, harita, ozet, oy, bugun){
  /* OY EN GÜÇLÜ SİNYAL, çünkü ekranda YAZAN rakama veriliyor. Menü
     kazıması işletmenin ilanı, fiş fiilen ödenen tutar; oy ise "bu
     sayı bugün doğru mu" sorusunun doğrudan cevabı.

     "Değişmiş" kararı rakamı EKRANDAN KALDIRMIYOR, KIRMIZIYA çeviriyor
     ve gerekçeyi yazıyor. Kaldırmak için bütçe süzgecinin de ağdan
     gelen bir cevabı beklemesi gerekirdi; süzgeç bugün saf ve eşzamanlı
     (statik veri üzerinde) ve onu ağa bağlamak listeyi her açılışta
     bekletirdi. Sınır bilerek burada: kullanıcı uyarıyı görüyor. */
  const k = oyKarari(oy);
  if (k === "degismis"){
    const ne = gunOnce(oy.son_gun);
    return { sinif:"kirmizi", ad:"fiyat değişmiş",
             neden: sayi(oy.degisti) + " kişi \"değişmiş\" dedi" +
                    (ne ? " — " + ne : "") };
  }
  if (k === "gecerli"){
    /* TARIH VARSA YAZILIYOR: "3 kişi dedi" ne kadar taze olduğunu
       söylemiyor; ürün tarifinin istediği şey tam olarak buydu.
       Sunucu eşiğin altında tarih döndürmüyor (tek kişinin ne zaman oy
       verdiğini ifşa ederdi), o yüzden yokluğu normal -- cümle
       tarihsiz de tam kalıyor. */
    const ne = gunOnce(oy.son_gun);
    const cumle = sayi(oy.gecerli) + " kişi \"hâlâ böyle\" dedi" +
                  (ne ? " — " + ne : "");
    const g = oyYasi(oy);
    /* TARIHSIZ ONAY YEŞİL OLMUYOR. Yaşını bilmediğimiz bir onay "son 7
       gün" diyemez; sarı, elimizde olmayan tazeliği iddia etmeden
       doğrulamayı da yok saymayan tek basamak. */
    if (g == null)
      return { sinif:"sari", ad:GUVEN_ADI.sari,
               neden: cumle + " (tarihi bilinmiyor)" };
    if (g <= OY_TAZE_GUN)
      return { sinif:"yesil", ad:GUVEN_ADI.yesil, neden: cumle };
    if (g <= OY_SON_GUN)
      return { sinif:"sari", ad:GUVEN_ADI.sari, neden: cumle };
    /* 30 günden eski: hüküm menü kanıtına düşüyor, aşağı devam. */
  }

  /* Fiş katmanı önce: kullanıcıdan gelen fiyat, kazınmış menüden daha
     güçlü bir kanıt -- mekanın ilan ettiği değil, fiilen ödenen tutar. */
  if (fisGoster(ozet))
    return { sinif:"yesil", ad:GUVEN_ADI.yesil,
             neden: sayi(ozet.fis) + " fişten doğrulandı" };

  const f = yemekFiyati(m, bugun);
  if (f == null){
    const s = seviye(m, bugun);
    /* Menüsünde fiyat varsa "fiyat yok" DENMİYOR: aynı ekranda kalemlerin
       fiyatı listeleniyor ve rozet o listeyle çelişirdi. */
    const kalem = menudeFiyatVar(m);
    if (kalem)
      return { sinif:"kirmizi", ad:GUVEN_ADI.menu,
               neden: "menüde " + sayi(kalem) + " kalemin fiyatı var, " +
                      "ama bir öğünün kaça geldiği çıkmıyor" };
    return { sinif:"kirmizi", ad:GUVEN_ADI.kirmizi,
             neden: s ? "türünden tahmin: " + s.ad : "fiyat bilgisi yok" };
  }

  const d = harita ? fiyatDayanagi(m, harita, bugun) : null;
  const yas = fiyatYasEtiketi(m, bugun);
  const eski = !!(yas && yas.eski);
  const zincir = !!(d && d.sinif === "zincir");

  if (!zincir && !eski)
    return { sinif:"yesil", ad:GUVEN_ADI.yesil,
             neden: "kendi menüsünden" + (yas ? ", " + yas.ad : "") };

  const neden = [];
  if (zincir) neden.push(d.ad);
  if (eski) neden.push("fiyat eskimiş" + (yas ? " (" + yas.ad + ")" : ""));
  return { sinif:"sari", ad:GUVEN_ADI.sari, neden: neden.join(" · ") };
}

/* Rozetin HTML'i. Tek yerde duruyor çünkü dört ekran basıyor (kart,
   detay paneli, mekan sayfası, ana ekran önerisi) ve renk ile metnin
   birlikte gitmesi şart: renk tek başına erişilebilir değil. */
function guvenRozeti(g, kisa){
  if (!g) return "";
  const baslik = g.ad + (g.neden ? " — " + g.neden : "");
  return '<span class="guven ' + g.sinif + '" title="' + kacir(baslik) +
         '" aria-label="' + kacir("Fiyat güveni: " + baslik) + '">' +
         '<i aria-hidden="true"></i>' +
         (kisa ? "" : "<span>" + kacir(g.ad) + "</span>") + "</span>";
}

/* ============================================================
   CEBİMDE KOMBİNİ — "bu bütçeyle burada ne yenir?"

   Yol haritasının maddesi. ÖLÇÜLDÜ, ve ölçüm kombinin ŞEKLİNİ belirledi:

     tek mekan içinde (ana ürün + içecek/tatlı)   148 / 163  = %91
     iki mekan, 400 m, FARKLI adlı                 22 / 163  = %13

   Yani "A'da kahve, B'de tatlı" gibi iki mekanlı bir kombin bu veriyle
   kurulamıyor -- ülke çapında 22 mekan. Tek mekan içinde ise %91.
   Kombin bu yüzden TEK MEKANIN KENDİ MENÜSÜNDEN kuruluyor.

   Ortalama fiyat "burada kaça oturulur" diyor; kombin daha somut bir
   soruyu cevaplıyor: "300 lira ile bu mekanda NE alabilirim". Cevap
   uydurma değil, menüde YAZAN iki kalem:

     Margarita 240 ₺ + Ayran 40 ₺ = 280 ₺

   EN UCUZU seçiliyor, bütçeye "oturan" bir sepet aranmıyor. Sebep:
   bütçeye göre kalem seçmek, kullanıcının sormadığı bir tercihte
   bulunmak olurdu ("400 lira varsa en pahalısını al"). Sorulan şey
   "yeter mi" ve onun cevabı en ucuz kombinde.

   KALEM KATEGORİSİ VERİDE. `m.menu` kalemleri artık `k` alanı taşıyor
   (app_veri.py, fiyat_analiz.kategorile). Sınıflanamayan kalemde alan
   hiç yok ve o kalem kombine girmiyor -- ne olduğunu bilmediğimiz bir
   şeyi "yanına içecek" diye sunmak, uydurma bir sepet olurdu.
   Ölçüldü: İstanbul'un 4.499 kaleminin 2.036'sı (%45) sınıflanıyor.

   MENÜ EN UCUZ 40 KALEM. Yani buradan çıkan kombin gerçekten mekanın
   en ucuz kombinidir; kırpılan kalemler daha pahalı olanlar.
   ============================================================ */

/* Yanına ne gider: önce içecek, yoksa tatlı. Bir öğün "yemek + içecek"
   olarak kuruluyor; tatlı ikinci tercih çünkü içeceksiz tatlı bir öğün
   değil, ek. */
/* Alkollü kategoriler. Ayrı bir küme olarak duruyor çünkü ICECEK_KAT
   yemekFiyati()'nin dışlama listesi ve oraya "alkolsüz" ayrımı sokmak
   ortalamayı da değiştirirdi -- iki soru, iki küme. */
const ALKOL_KAT = new Set(["Rakı / içkiler", "Şarap", "Bira"]);
function _alkolsuz(kume){
  return new Set([...kume].filter(k => !ALKOL_KAT.has(k)));
}

function _ucuzKalem(menu, kume){
  let iyi = null;
  for (const k of (menu || [])){
    if (!k.k || !kume.has(k.k) || k.f == null) continue;
    if (!iyi || k.f < iyi.f) iyi = k;
  }
  return iyi;
}

function kombinKur(m, butce, bugun){
  const menu = m && m.menu;
  if (!menu || !menu.length) return null;
  /* Ana ürün, mekanın KENDİ dağılımından (anaKategoriler): börekçide
     poğaça ana ürün, kebapçıda yan. Kural tek yerde. */
  const ana = anaKategoriler(m);
  if (!ana || !ana.length) return null;
  const anaKume = new Set(ana);

  const yemek = _ucuzKalem(menu, anaKume);
  if (!yemek) return null;
  /* İçecek ve tatlı kümeleri yemekFiyati()'nin kullandığıyla AYNI:
     ortalamadan dışlanan şey, kombinde yanına konan şey.

     ALKOLSÜZ ÖNCE. Ölçülen vaka: Amara Şile Ocakbaşı'nda kombin
     "patlıcan salatası + Efes Malt" çıkıyordu, çünkü menüdeki en ucuz
     içecek biraydı. Uygulama alkollü mekanları listeliyor ve bu doğru;
     ama kimsenin istemediği bir öğüne varsayılan olarak içki koymak
     ayrı bir şey. Alkollü kalem ancak alkolsüz hiç yoksa geliyor.
     Ölçüldü: 151 kombinin 0'ında alkol kategorisinde kalem var.

     SINIR: sınıflandırma ADA bakıyor. "Baileys Americano" kategori
     olarak Americano; içindeki likörü ad sözlüğü görmüyor. Bunu
     düzeltmek yeni bir anahtar kelime listesi demek ve o liste de
     kendi başına bir ayrışma kaynağı olurdu -- kategori kuralı
     fiyat_analiz.py'de tek yerde duruyor. */
  const yanina = _ucuzKalem(menu, _alkolsuz(ICECEK_KAT)) ||
                 _ucuzKalem(menu, TATLI_KAT) ||
                 _ucuzKalem(menu, ICECEK_KAT);
  if (!yanina) return null;
  /* Aynı kalemi iki kez saymayalım: tek kategorili bir menüde (yalnız
     tatlı satan pastane) ana ürün ile "yanına" aynı satır olabilir. */
  if (yanina === yemek) return null;

  const toplam = yemek.f + yanina.f;
  return { kalemler: [yemek, yanina], toplam,
           butceIci: !(butce > 0) || toplam <= butce };
}

/* Ekranda okunacak hali. Bütçe girilmişse yeter/yetmez de yazıyor --
   rakamı verip kullanıcıyı hesap yapmaya bırakmak, ekranın işini
   kullanıcıya yıkmak olurdu. */
function kombinCumlesi(k, butce){
  if (!k) return "";
  const liste = k.kalemler.map(x => kacir(x.a) + " " + tl(x.f)).join(" + ");
  const bas = liste + " = " + tl(k.toplam);
  if (!(butce > 0)) return bas;
  return bas + (k.butceIci
    ? " — bütçene giriyor."
    : " — " + tl(k.toplam - butce) + " aşıyor.");
}

/* ---------- çok bütçeli öneri (mekan sayfası) ----------
   Ürün tarifi mekan sayfasında birden çok basamak istiyor:
   "₺200 altında … ✅ / ₺300 altında … ❌". Tek kombin bunu veremiyordu.

   HER BASAMAKTA EN PAHALI UYAN KOMBİN. "₺300'e ne alırım" sorusunun
   cevabı 300'e en yakın olan; en ucuzu vermek kullanıcının elindeki
   parayı bilerek eksik kullanması olurdu.

   BASAMAKLAR MEKANIN KENDİ MENÜSÜNDEN. Sabit bir liste (BUTCE_SECENEK)
   bir kafede üç basamağı birden boş bırakırdı. Kombin fiyatlarının
   kendisi yuvarlanarak basamak oluyor, yani her mekanda dolu satır
   çıkıyor. */
const ONERI_EN_COK = 3;

/* Menüdeki bütün ana ürün + yanına ikililerini kurar, ucuzdan pahalıya.
   kombinKur() TEK en ucuzu veriyor; buradaki liste basamakları
   doldurmak için gerekiyor. Kural aynı: alkolsüz önce, aynı kalem iki
   kez sayılmaz. */
function kombinListesi(m, bugun){
  const menu = m && m.menu;
  if (!menu || !menu.length) return [];
  const ana = anaKategoriler(m);
  if (!ana || !ana.length) return [];
  const anaKume = new Set(ana);
  const yan = _alkolsuz(new Set([...ICECEK_KAT, ...TATLI_KAT]));
  const fiyatli = k => k && k.f != null && k.a;

  const yemekler = menu.filter(k => fiyatli(k) && k.k && anaKume.has(k.k));
  let yanlar = menu.filter(k => fiyatli(k) && k.k && yan.has(k.k));
  /* Alkolsüz hiç yoksa alkollüye düşülüyor -- kombinKur ile aynı sıra. */
  if (!yanlar.length)
    yanlar = menu.filter(k => fiyatli(k) && k.k && ICECEK_KAT.has(k.k));
  if (!yemekler.length || !yanlar.length) return [];

  const l = [];
  for (const y of yemekler)
    for (const z of yanlar){
      if (y === z) continue;
      l.push({ kalemler: [y, z], toplam: y.f + z.f });
    }
  l.sort((a, b) => a.toplam - b.toplam);
  return l;
}

/* Basamaklar: en ucuz kombinin üstünden başlayıp 50'şer yuvarlanmış
   birkaç eşik. Her eşik için o eşiği AŞMAYAN en pahalı kombin. */
function oneriBasamaklari(m, bugun){
  const l = kombinListesi(m, bugun);
  if (!l.length) return [];
  const yuvarla = n => Math.ceil(n / 50) * 50;
  const esikler = [];
  for (const k of l){
    const e = yuvarla(k.toplam);
    if (!esikler.includes(e)) esikler.push(e);
    if (esikler.length >= ONERI_EN_COK) break;
  }
  return esikler.map(e => {
    const uyan = l.filter(k => k.toplam <= e);
    return { esik: e, kombin: uyan.length ? uyan[uyan.length - 1] : null };
  });
}

function oneriCumlesi(b){
  if (!b || !b.kombin) return "";
  const k = b.kombin;
  return k.kalemler.map(x => x.a).join(" + ") + " — " + tl(k.toplam);
}

/* ============================================================
   KULLANICI SEVİYESİ

   Yol haritasının maddesi. Seviye bir SÜS değil, bir SAYIM: kullanıcının
   uygulamaya kaç doğrulanmış katkı yaptığı.

   ONAYDAN GEÇMİŞ KATKI SAYILIYOR, gönderilen değil. Gönderileni saymak,
   seviyeyi kuyruğa çöp atarak yükseltilebilir yapardı; ön onay zaten
   hakaret ve yanlış bilgi için var, seviye de aynı kapıdan geçsin.

   FİYAT OYU SEVİYEYE GİRMİYOR. Oy tek dokunuş ve onay kuyruğu yok
   (veritabani/fiyat_oyu.sql: gönderilen şey bir boolean, oradaki savunma
   eşik). Onaysız ve tek dokunuşluk bir eylemi seviyeye bağlamak, tam da
   oyunlaştırmanın bozulduğu yer olurdu. Oy sayısı ekranda AYRI yazıyor
   -- görünmez değil, seviyeye etkisiz.

   EŞİKLER NEREDEN GELİYOR, VE HANGİSİ UYDURMA:
     0   Yeni Cebimdeci
     1   Menü Avcısı      ilk katkı: bir mekan senin sayende daha eksiksiz
     3   Fiyat Dedektifi  FIS_ESIK ile aynı sayı -- tek başına bir mekanın
                          fiyatını k-anonimlik eşiğine taşıyabilecek katkı
     10  Cebimde Gurmesi  YUVARLAK SAYI, ölçüm değil
     25  Cebimde Elçisi   YUVARLAK SAYI, ölçüm değil

   İlk üçünün gerekçesi var, son ikisi yok ve bu bilerek yazılıyor:
   uygulama daha yayında değil, yani gerçek bir katkı dağılımı yok.
   Dağılım oluşunca bu iki sayı ölçüme göre yeniden konmalı. Uydurma bir
   eğriye "veri" demektense uydurma olduğunu söylemek daha dürüst.

   BASAMAK SAYISI ALTIDAN BEŞE İNDİ: ürün tarifindeki merdiven beş
   basamaklı. Altıncı basamağın eşiği (50) zaten uydurmaydı; uydurma bir
   sayıyı korumak için markanın adlandırmasını bozmanın anlamı yok.

   SEVİYE HERKESE AÇIK DEĞİL. Kullanıcı kendi sayfasında görüyor; başka
   kimseye gösterilmiyor. Başkasına göstermek için sayımın SUNUCUDA
   yapılması gerekirdi -- tarayıcıda hesaplanan bir rozet, sahibi
   tarafından istediği gibi yazılabilir ve "doğrulanmış katkıcı" gibi bir
   iddiayı taşıyamaz.
   ============================================================ */

/* ADLAR MARKA TARIFINDEN. Önce genel adlar yazmıştım (Yeni, Katkıcı,
   Doğrulayıcı, Düzenli, Kâşif, Emektar); ürün tarifindeki adlar hem
   markanın sesini taşıyor hem de KATKININ TÜRÜNÜ söylüyor -- "Menü
   Avcısı" ne yaptığını anlatıyor, "Katkıcı" anlatmıyor.

   Eşikler DEĞİŞMEDİ: adlar süs, sayım değil. */
const SEVIYELER = [
  { esik: 0,  ad: "Yeni Cebimdeci" },
  { esik: 1,  ad: "Menü Avcısı" },
  { esik: 3,  ad: "Fiyat Dedektifi" },
  { esik: 10, ad: "Cebimde Gurmesi" },
  { esik: 25, ad: "Cebimde Elçisi" }
];

/* onayli: onaydan geçmiş katkı sayısı (fiş, katkı, yorum, menü, fotoğraf).
   Dönen: {ad, sira, onayli, sonraki, kalan}. sonraki null ise en üst
   seviyedeyiz ve "kalan" 0. */
function seviyeHesapla(onayli){
  const n = Number.isFinite(+onayli) && +onayli > 0 ? Math.floor(+onayli) : 0;
  let sira = 0;
  for (let i = 0; i < SEVIYELER.length; i++) if (n >= SEVIYELER[i].esik) sira = i;
  const sonraki = SEVIYELER[sira + 1] || null;
  return { ad: SEVIYELER[sira].ad, sira, onayli: n, sonraki,
           kalan: sonraki ? sonraki.esik - n : 0 };
}

/* Ekranda okunacak hali. "Bir sonraki seviyeye ne kadar kaldığı" RAKAMLA
   yazılıyor: kullanıcıyı ilerleme çubuğuna bakıp tahmin etmeye bırakmak,
   ekranın işini kullanıcıya yıkmak olurdu. */
function seviyeCumlesi(s){
  if (!s) return "";
  if (!s.onayli)
    return "Henüz onaylanmış katkın yok. İlk katkın seni " +
           SEVIYELER[1].ad + " yapar.";
  const bas = sayi(s.onayli) + " onaylanmış katkı.";
  if (!s.sonraki) return bas + " En üst seviyedesin.";
  return bas + " " + sayi(s.kalan) + " katkı daha: " + s.sonraki.ad + ".";
}

/* ============================================================
   BÜTÇE TALEBİ — "bana bakanlar hangi bütçeyle arıyordu?"

   İşletme panelindeki tek ÖZGÜN sayı bu. Görüntülenme sayısını her
   sayaç verir; bütçe talebini bu uygulamanın verisi verir.

   TAM TUTAR DEĞİL BANT SAKLANIYOR. Sayaç satırı (mekan, gün, cihaz)
   üçlüsü; oraya "347 TL" yazmak üçlüyü giderek daha ayırt edici
   yapardı. Beş kova, eşikleri BUTCE_SECENEK'ten geliyor -- ekranda
   kullanıcıya sunulan sayılarla aynı, ikinci bir ölçek uydurulmadı.

   NULL = bütçe girilmemiş. Sıfır değil: "bilinmiyor" ile "farketmez"
   ayrı şeyler ve ikisini birleştirmek dağılımı bozar.
   ============================================================ */

/* Bant sınırları BUTCE_SECENEK'ten türetiliyor: [150, 250, 400, 700]
   -> 1: <150, 2: 150-249, 3: 250-399, 4: 400-699, 5: 700+ */
function butceBandi(butce){
  const n = butceOku(butce);
  if (!n) return null;                    /* girilmemiş ya da çözülemedi */
  let b = 1;
  for (const esik of BUTCE_SECENEK) if (n >= esik) b++;
  return b;
}

/* Bandın okunabilir adı. Ekranda "bant 3" yazmak kimseye bir şey
   söylemez. */
function butceBandiAdi(b){
  const e = BUTCE_SECENEK;
  if (b === 1) return tl(e[0]) + " altı";
  if (b > 1 && b <= e.length) return tl(e[b - 2]) + " – " + tl(e[b - 1] - 1);
  if (b === e.length + 1) return tl(e[e.length - 1]) + " ve üstü";
  return "";
}

/* Dağılımı işletme sahibinin okuyacağı cümleye çevirir.
   [{bant, kisi}] -> "Bakanların 62'si 250 ₺ altı bütçeyle arıyordu."

   EN KALABALIK BANT yazılıyor, tam liste değil: beş satırlık bir tablo
   panelde asıl bilgiyi boğardı ve sahip zaten tek bir soru soruyor --
   "bana bakanlar ne kadar harcamayı düşünüyor". */
function butceTalebiCumlesi(dagilim){
  if (!dagilim || !dagilim.length) return "";
  let iyi = dagilim[0];
  for (const d of dagilim) if (d.kisi > iyi.kisi) iyi = d;
  const toplam = dagilim.reduce((t, d) => t + d.kisi, 0);
  return "Bütçe yazan " + sayi(toplam) + " kişinin " + sayiEkli(iyi.kisi) +
         " " + butceBandiAdi(iyi.bant) + " arıyordu.";
}

/* TALEP AÇIĞI (FIKIRLER.md F3). İki tarafı yan yana koyuyor:
   ne aranıyor (sunucudan gelen bant dağılımı) ve ne bulunuyor
   (listedeki ölçülmüş fiyatların medyanı, istemcide).

   NEDEN ÖZGÜN: Google ve Yemeksepeti fiyatı biliyor ama ARAYANIN
   BÜTÇESİNİ yayınlamıyor -- o veri onların reklam ürünü. Cebimde'de
   bütçe zaten ürünün girdisi.

   AÇIK YOKSA AÇIK DENMİYOR. Aranan bant ile bulunan medyan çelişmiyorsa
   cümle yalnız iki sayıyı söylüyor. Olmayan bir açığı yazmak, bu
   depodaki "yanlış fiyat fiyatsızlıktan kötüdür" kuralının ölçüm
   tarafındaki karşılığı olurdu.

   MEDYAN YOKSA CÜMLE DE YOK: karşılaştıracak bir şey olmadan "talep
   açığı" diye bir şey yok. */
function talepAcigiCumlesi(dagilim, medyan){
  if (!dagilim || !dagilim.length) return "";
  let iyi = dagilim[0];
  for (const d of dagilim) if (d.kisi > iyi.kisi) iyi = d;
  const toplam = dagilim.reduce((t, d) => t + d.kisi, 0);
  const bas = "Buraya bakan " + sayi(toplam) + " kişinin " + sayiEkli(iyi.kisi) +
              " " + butceBandiAdi(iyi.bant) + " arıyordu";
  if (medyan == null) return bas + ".";
  const son = "; menüsü ölçülmüş mekanların medyanı " + tl(medyan);
  /* Bandın üst sınırı: aranan bandın tavanı. Son bantta tavan yok --
     "ve üstü" bandında açık tanımlı değil, o yüzden karşılaştırma da
     yapılmıyor. */
  const e = BUTCE_SECENEK;
  const tavan = (iyi.bant >= 1 && iyi.bant <= e.length) ? e[iyi.bant - 1] : null;
  if (tavan != null && medyan > tavan)
    return bas + son + " — aradıklarının üstünde.";
  return bas + son + ".";
}

/* ---------- kohort ölçümü ----------
   Çerezsiz ve sunucusuz: yalnız localStorage, yalnız bu cihaz.
   Hangi günlerde açıldığı tutuluyor; D1/D7/D30 buradan hesaplanıyor. */
const KOHORT = "cebimde.kohort";
const BIRGUN = 86400000;
const bugunISO = () => bugunYerel();   /* yerel gun: gerekce bugunYerel()'de */
const gunFarki = (a,b) => Math.round((Date.parse(b) - Date.parse(a)) / BIRGUN);

function kohortGuncelle(){
  let k = null;
  try { k = JSON.parse(localStorage.getItem(KOHORT)); } catch (e) { k = null; }
  if (!k || !k.ilk || !Array.isArray(k.gunler)) k = { ilk: bugunISO(), gunler: [] };
  const b = bugunISO();
  if (k.gunler.indexOf(b) < 0) k.gunler.push(b);
  k.gunler = k.gunler.slice(-90);
  try { localStorage.setItem(KOHORT, JSON.stringify(k)); } catch (e) {}
  return k;
}

function kohortOzet(k){
  const g = k.gunler.map(d => gunFarki(k.ilk, d));
  const varMi = (alt, ust) => g.some(x => x >= alt && x <= ust);
  return {
    ilkZiyaret: k.ilk,
    ziyaretGunu: k.gunler.length,
    kacGunluk: g.length ? Math.max.apply(null, g) : 0,
    geriDonen: k.gunler.length > 1,
    d1: varMi(1,1), d7: varMi(7,8), d30: varMi(30,32)
  };
}

/* ---------- kendi kendini kontrol:  ?test=1  ---------- */
function kendiniKontrolEt(){
  if (!new URLSearchParams(location.search).has("test")) return;
  const g14 = new Date(2026,7,19,14,0), g03 = new Date(2026,7,19,3,0),
        g01 = new Date(2026,7,19,1,0);
  /* zamanYasi UTC ile calisiyor (Date.parse), o yuzden sabit "simdi" de
     UTC verilmis bir an. */
  const g26 = new Date("2026-08-26T12:00:00Z");
  /* Sabit taban: kontrol sonucu sayfanin nerede servis edildigine
     bagli olmasin. */
  const T = "https://o.test/app/giris.html";

  /* --- il dosyasi cozucusu icin sikistirilmis ornek (ELLE yazildi) --- */
  const SIK = {
    il: "Test",
    sutun: { id:["n1","w2","r3"], ad:["A Kafe","B Bar","C Muze"],
             tur:["Kafe","Bar","Muze"], lat:[39.9,40.0,41.0],
             lon:[32.8,29.0,28.9] },
    ek: { adres:{ "1":"Bagdat Caddesi 448" }, wifi:{ "1":1 } }
  };

  /* --- civar kontrolu icin sahte il --- 39,9 enleminde 0,001 derece
     enlem ~110 m. "uzak" 663 m'de, yani 500 m disinda. */
  const BEN   = { id:"ben",  lat:39.900, lon:32.85, tur:"Kafe" },
        CIVAR = [BEN,
          { id:"a",    lat:39.901, lon:32.85, tur:"Kafe" },
          { id:"b",    lat:39.904, lon:32.85, tur:"Restoran",
            kat:{ "Pizza": { n:2, med:440 } } },          /* tek FIYATLI komsu */
          { id:"c",    lat:39.900, lon:32.85, tur:"Bar"  },  /* ayni koordinat */
          { id:"d",    lat:39.9005,lon:32.85, tur:"Kafe" },
          { id:"uzak", lat:39.906, lon:32.85, tur:"Kafe" }];
  const C = civarOzeti(BEN, CIVAR);

  /* Yaricap DARALMA yolu: 500 m icine 600 mekan sigdirilirsa sunucunun
     500'luk siniri asilir. Liste kirpilmiyor, yaricap kuculuyor ve
     kuculen yaricap DONUYOR -- ekranda yazan sayi dogru kalsin diye. */
  const KALABALIK = [];
  for (let i = 0; i < 600; i++)
    /* ilk 300'u 90 m icinde, kalani 450 m civarinda */
    KALABALIK.push({ id:"k"+i, tur:"Kafe",
                     lat: 39.9 + (i < 300 ? 0.0008 : 0.0040), lon: 32.85 });
  const K = civarOzeti(BEN, KALABALIK);

  /* --- bütçe dökümü için sahte liste ---
     Beş mekan, beş AYRI cevap. Fixture elle yazıldı ki döküm hangi
     kategoriye kimi koyduğunu gerçekten sınasın:
       olcum-ucuz  ölçülmüş ₺120  -> girer
       olcum-tuz   ölçülmüş ₺400  -> asiyor
       hesapli     Fast food      -> muhtemel
       ust         steak_house    -> zor
       yok         sinyal yok     -> bilinmiyor
     Menü kalemleri İKİ tane: YEMEK_ASGARI_KALEM eşiği bir kalemli
     fixture'ı sessizce ölçümsüz sayardı ve döküm sapardı. */
  /* --- kombin fixture'lari ---
     Menu kalemleri artik KATEGORI tasiyor (app_veri.py). Fixture elle
     yazildi ki kombin gercekten EN UCUZ ana urun + EN UCUZ icecegi
     secsin; sirasi karisik veriliyor cunku secim siraya degil FIYATA
     bakmali. */
  const KOMBIN = {
    id:"k1", ad:"Kombin Test", tur:"Restoran",
    kat:{ "Pizza": { n:2, med:300 }, "Kola / gazlı": { n:2, med:60 } },
    menu:[ { a:"Buyuk Pizza", f:400, k:"Pizza" },
           { a:"Kola",        f:60,  k:"Kola / gazlı" },
           { a:"Kucuk Pizza", f:300, k:"Pizza" },
           { a:"Kucuk Kola",  f:40,  k:"Kola / gazlı" },
           { a:"Bilinmeyen",  f:5 } ]          /* kategorisiz: girmemeli */
  };
  /* Icecegi olmayan mekan: TATLIYA dusmeli. */
  const KOMBIN_TATLI = {
    id:"k2", ad:"Tatlici", tur:"Restoran",
    kat:{ "Pizza": { n:2, med:300 }, "Tatlı": { n:2, med:120 } },
    menu:[ { a:"Pizza", f:300, k:"Pizza" }, { a:"Sutlac", f:120, k:"Tatlı" } ]
  };
  /* Sonuc NULL-GUVENLI okunuyor. Ilk yazimda kontroller dogrudan
     kombinKur(...).kalemler diyordu; kombini null'a dusuren bir sabotaj
     TypeError firlatiyor ve kontrol listesi HIC KURULMUYORDU -- yani
     292 kontrolun hicbiri raporlanmadan grup patliyordu. Sabotaj
     "yakalandi" gibi degil "kacti" gibi gorunuyordu. */
  const KR = kombinKur(KOMBIN, 0) || { kalemler: [], toplam: 0, butceIci: null };
  const KR400 = kombinKur(KOMBIN, 400) || {}, KR200 = kombinKur(KOMBIN, 200) || {};

  /* Alkol kurali: EN UCUZ icecek bira ama alkolsuzu de var. */
  const KOMBIN_ALKOL = {
    id:"k4", ad:"Ocakbasi", tur:"Restoran",
    kat:{ "Kebap": { n:2, med:300 }, "Bira": { n:2, med:80 }, "Ayran": { n:2, med:120 } },
    menu:[ { a:"Kebap", f:300, k:"Kebap" },
           { a:"Bira",  f:80,  k:"Bira" },
           { a:"Ayran", f:120, k:"Ayran" } ]
  };
  /* Alkolsuz HIC yoksa alkollu geliyor: mekanin menusu buysa saklamak
     da bir seyi degistirmiyor. */
  const KOMBIN_SADECE_ALKOL = {
    id:"k5", ad:"Meyhane", tur:"Restoran",
    kat:{ "Kebap": { n:2, med:300 }, "Rakı / içkiler": { n:2, med:400 } },
    menu:[ { a:"Kebap", f:300, k:"Kebap" }, { a:"Raki", f:400, k:"Rakı / içkiler" } ]
  };

  /* Yalniz ana urun: kombin kurulamaz, uydurma yanina konmaz. */
  const KOMBIN_TEK = {
    id:"k3", ad:"Tek", tur:"Restoran",
    kat:{ "Pizza": { n:2, med:300 } },
    menu:[ { a:"Pizza", f:300, k:"Pizza" } ]
  };
  const BUTCE_LISTE = [
    { id:"ucuz",    tur:"Restoran", kat:{ "Çorba": { n:2, med:120 } } },
    { id:"tuz",     tur:"Restoran", kat:{ "Kebap": { n:2, med:400 } } },
    { id:"hesapli", tur:"Fast food" },
    { id:"ust",     tur:"Restoran", mutfak:"steak_house" },
    { id:"yok",     tur:"Restoran" }
  ];
  const BO = butceOzeti(BUTCE_LISTE, 200);

  /* --- fiyatin dayanagi icin sahte il ---
     Ucu ayni adli ve AYNI fiyatli (zincir), biri ayni adli ama FARKLI
     fiyatli (ayri kazima), biri tek. Ayni ad + farkli fiyat ayni
     zincir sayilmamali: iki ayri olcum var demektir.

     Kalemler IKI tane: YEMEK_ASGARI_KALEM esigi tek kalemli fixture'i
     olcumsuz sayar ve harita bos cikardi. */
  const _kat = f => ({ "Pizza": { n:2, med:f } });
  const ZIL = [
    { id:"z1", ad:"Domino's",  tur:"Fast food", kat:_kat(528) },
    { id:"z2", ad:"domino's",  tur:"Fast food", kat:_kat(528) },   /* buyuk/kucuk harf */
    { id:"z3", ad:" Domino's ", tur:"Fast food", kat:_kat(528) },  /* bosluk */
    { id:"z4", ad:"Domino's",  tur:"Fast food", kat:_kat(610) },   /* AYRI kazima */
    { id:"z5", ad:"Cozy Etiler", tur:"Restoran", kat:_kat(400) },
    { id:"z6", ad:"Fiyatsiz",  tur:"Restoran" }
  ];
  const ZH = zincirHaritasi(ZIL);

  /* --- guven skoru fixture'lari ---
     Tarih ELLE veriliyor: "eski" bandi fiyatin yasina bakiyor ve bugunun
     tarihine gore degisir. Sabit bir bugun (g14 = 2026-08-19) ile
     olculuyor, yoksa kontrol takvimle birlikte kayardi. */
  const _kendi  = { id:"g1", ad:"Tek Sube", tur:"Restoran",
                    kat:{ "Kebap": { n:2, med:300 } }, tarih:"2026-08" };
  const _eski   = { id:"g2", ad:"Eski Menu", tur:"Restoran",
                    kat:{ "Kebap": { n:2, med:300 } }, tarih:"2025-11" };
  const _yok    = { id:"g3", ad:"Fiyatsiz", tur:"Restoran" };
  const _tahmin = { id:"g4", ad:"Tahminli", tur:"Fast food" };
  /* Menusu FIYATLI ama ogun fiyati cikmayan mekan: 291 menulu mekanin
     128'i (%44) boyle. Burada yalniz icecek kategorisi var, yani
     anaKategoriler() bos donuyor ve yemekFiyati() null. Kalemlerin
     fiyati ise ekranda YAZIYOR. */
  /* Cok butceli oneri fixture'i: iki ana urun (ANA 30, ANA2 60) ve iki
     yan (TATLI 70, TATLI2 150) -> dort ikili, uc ayri basamak. */
  const ONR = { id:"o1", ad:"Oneri", tur:"Kafe", tarih:"2026-08",
    kat:{ "Poğaça / börek": { n:2, med:45 }, "Tatlı": { n:2, med:110 } },
    menu:[ {a:"ANA",    f:30,  k:"Poğaça / börek"},
           {a:"ANA2",   f:60,  k:"Poğaça / börek"},
           {a:"TATLI",  f:70,  k:"Tatlı"},
           {a:"TATLI2", f:150, k:"Tatlı"},
           /* BIRA EN UCUZ YAN. Alkol suzgeci kalkarsa butun basamaklar
              buna kayar; fixture'da alkol hic yokken sabotaj KACIYORDU. */
           {a:"BIRA",   f:10,  k:"Bira"} ] };
  /* YALNIZ TATLI olan mekan (pastane): anaKategoriler tatliya dusuyor,
     yani ayni kalem hem ana urun hem yan olabiliyor. "y === z" korumasi
     kalkarsa "TEK + TEK" diye bir kombin cikar. */
  /* "Bu civarda ne yenir" fixture'i. Koordinatlar Kadikoy civari;
     mesafeler mesafeM ile gercekten hesaplaniyor. */
  const CV0 = { id:"c0", ad:"Merkez", tur:"Kafe", lat:40.9900, lon:29.0280 };
  const CVL = [
    CV0,
    { id:"c1", ad:"Yakin Sube", tur:"Restoran", lat:40.9902, lon:29.0282,
      menu:[{a:"Lahmacun", f:90, k:"Kebap"}] },
    /* Ayni kalem, AYNI YARICAP ICINDE ikinci sube: c1 ~28 m, c2 ~187 m.
       Ikisi de menzilde olmazsa tekillestirme hic denenmemis olur. */
    { id:"c2", ad:"Uzak Sube", tur:"Restoran", lat:40.9915, lon:29.0290,
      menu:[{a:"Lahmacun", f:90, k:"Kebap"}] },
    { id:"c3", ad:"Bufe", tur:"Fast food", lat:40.9901, lon:29.0281,
      menu:[{a:"Tost", f:40, k:"Tost"}, {a:"Ayran", f:15, k:"Ayran"}] },
    /* TEK mekanda IKI yenir kalem: mekan basina yalniz en ucuzu cikmali,
       yoksa bir lokanta butun listeyi doldurur. */
    { id:"c6", ad:"Corbaci", tur:"Restoran", lat:40.9904, lon:29.0284,
      menu:[{a:"Mercimek Corbasi", f:55, k:"Çorba"},
            {a:"Ezogelin Corbasi", f:70, k:"Çorba"}] },
    { id:"c4", ad:"Pahali", tur:"Restoran", lat:40.9903, lon:29.0283,
      menu:[{a:"Kuzu Sis", f:300, k:"Kebap"}] },
    /* Yaninda 20 TL'lik bir TEKLIF var; suzgec kalkarsa listenin basina
       gecer ve "bu civarda 20 TL'ye tost yenir" denmis olur. */
    { id:"c7", ad:"Kampanyali", tur:"Fast food", lat:40.9902, lon:29.0281,
      menu:[{a:"Kampanya Tost", f:20, k:"Tost", p:1}] },
    /* 5 km oteden: yaricap disi. */
    { id:"c5", ad:"Uzak", tur:"Restoran", lat:41.0400, lon:29.0900,
      menu:[{a:"Bonfile", f:10, k:"Kebap"}] }
  ];
  /* Kampanya fixture'i: iki siradan kalem, bir teklif. Teklifin
     kategorisi YOK (app_veri kategorile'yi reddediyor) -- kombinin
     disinda kalmasinin sebebi de bu. */
  const KMP = { id:"p1", ad:"Kampanyali", tur:"Restoran", tarih:"2026-08",
    kat:{ "Kebap": { n:1, med:120 } },
    menu:[ {a:"Latte", f:95, k:"Kahve"},
           {a:"Lahmacun", f:120, k:"Kebap"},
           {a:"1 Alana 1 Bedava Kola", f:80, p:1} ] };
  /* Konum fixture'i: koordinat ve adres ELLE yazildi, il dosyasindan
     alinmadi -- gercek veriden okusa kontrol veriyle birlikte bozulurdu. */
  const KNM = { id:"k1", ad:"Konum Kafe", tur:"Kafe",
                adres:"Moda Caddesi 1", lat:40.99, lon:29.028 };
  const ONR_TEK = { id:"o2", ad:"Pastane", tur:"Kafe", tarih:"2026-08",
    kat:{ "Tatlı": { n:2, med:60 } },
    menu:[ {a:"TEK",  f:40, k:"Tatlı"},
           {a:"TEK2", f:80, k:"Tatlı"} ] };
  const _menulu = { id:"g5", ad:"Sadece Icecek", tur:"Kafe",
                    kat:{ "Bira": { n:3, med:230 } }, tarih:"2026-08",
                    menu:[ {a:"EFES 33", f:230, k:"Bira"},
                           {a:"EFES 50", f:250, k:"Bira"},
                           {a:"SU",      f:30,  k:"Bira"} ] };
  const GH = zincirHaritasi([_kendi, _eski], g14);
  const kontroller = [
    ["acikMi 24/7",             acikMi("24/7", g14),               true],
    ["acikMi gunduz",           acikMi("Mo-Su 09:00-23:00", g14),  true],
    ["acikMi gece kapali",      acikMi("Mo-Su 09:00-23:00", g03),  false],
    ["acikMi gece yarisi asan", acikMi("11:00-02:00", g01),        true],
    ["acikMi kapanmis",         acikMi("11:00-02:00", g03),        false],
    ["acikMi gun tutmuyor",     acikMi("Fr-Sa 20:00-23:00", g14),  false],
    ["acikMi bilgi yok",        acikMi("", g14),                   null],

    /* --- acilis saati: gercek veride olculen bozukluklar ---
       g14 = 2026-08-19 14:00, CARSAMBA. g01/g03 ayni gunun gece saatleri. */
    /* OSM kurallari ";" ile ayrilir, veride cogu VIRGUL kullanmis. */
    ["acikMi virgullu kural ayraci",
      acikMi("Mo-Fr 10:00-20:00, Sa-Su 11:00-21:00", g14),           true],
    ["acikMi virgullu kuralda gun tutmayan",
      acikMi("Mo-Fr 20:00-22:00, Sa-Su 11:00-21:00", g14),           false],
    ["acikMi virgullu kuralda ikinci kural tutar",
      acikMi("Mo-Tu 20:00-22:00, We-Su 11:00-21:00", g14),           true],
    /* Ama gun LISTESINDEKI virgul kural ayraci degil: boyle bolununce
       Mo ile We dusuyordu. Ayraci saatten sonraki virgul belirliyor. */
    ["acikMi gun listesindeki virgul bolunmez",
      acikMi("Mo,We,Fr 09:00-23:00", g14),                           true],
    ["acikMi gun listesi disindaki gun",
      acikMi("Tu,Th,Fr 09:00-23:00", g14),                           false],
    /* Turkce gun adlari: eksik saati giren kullanici bunlari yaziyor. */
    ["acikMi turkce gun araligi",
      acikMi("Pazartesi-Pazar 10:00-22:00", g14),                    true],
    ["acikMi turkce kisaltma",  acikMi("Pzt-Paz 09:00-18:00", g14),  true],
    ["acikMi tek turkce gun",   acikMi("Çarşamba 11:00-22:00", g14), true],
    ["acikMi tek turkce gun tutmuyor",
      acikMi("Salı 11:00-22:00", g14),                               false],
    ["acikMi her gun",          acikMi("Hergün 09:00-23:00", g14),   true],
    ["acikMi her gun ayri yazim", acikMi("Her gün 09:00-23:00", g14), true],
    ["acikMi nokta saat ayraci", acikMi("Mo-Su 10.00-22.00", g14),   true],
    /* ASIL HATA: taninmayan gun adi "hicbir gun acik degil" DEMEK DEGIL,
       "okunamadi" demek. Eskiden false donuyordu; deger katki
       dogrulamasindan geciyor, onaylaniyor ve mekan sonsuza kadar kapali
       gorunuyordu. */
    ["acikMi taninmayan gun adi okunamadi sayilir",
      acikMi("Blah-Blub 10:00-20:00", g14),                          null],
    ["acikMi taninan gun yaninda taninmayan varsa okunur",
      acikMi("Mo-Su, PH 08:00-18:00", g14),                          true],
    /* Katki dogrulamasi bu degerleri gecirmeli/gecirmemeli. */
    ["katki saat uydurma gun reddedilir",
      katkiSorunu("saat", "Blah-Blub 10:00-20:00") != null,          true],
    ["katki saat serbest metin reddedilir",
      katkiSorunu("saat", "Rezervasyona gore acilir") != null,       true],
    /* yemekFiyati: icecek fiyatinin yemek yerine gecmedigini kanitlar */
    ["yemek icecegi saymaz",
      yemekFiyati({kat:{"Kebap":{n:3,med:980},"Su":{n:1,med:30},"Çay":{n:1,med:40}}}), 980],
    /* Tek kalem menu degildir: perakende katalogu bu kapidan giriyordu. */
    ["yemek tek kalemden cikmaz",
      yemekFiyati({kat:{"Tatlı":{n:1,med:350}}}),                     null],
    ["yemek tek ana kalem elenir",
      yemekFiyati({kat:{"Balık":{n:1,med:900},"Çay":{n:5,med:40}}}),  null],
    ["yemek iki kalem yeter",
      yemekFiyati({kat:{"Pizza":{n:2,med:440}}}),                     440],
    /* ORTALAMA: kategori toplamlari / kalem sayisi. Medyan degil -- pahali
       kalemler sonuca giriyor, cunku soru "burada kaca oturulur". */
    ["ortalama kategoriler arasi",
      yemekFiyati({kat:{"Kebap":{n:2,med:300,top:700},
                        "Pizza":{n:2,med:200,top:300}}}),             250],
    ["ortalama icecegi saymaz",
      yemekFiyati({kat:{"Kebap":{n:2,med:300,top:700},
                        "Çay":{n:10,med:40,top:400}}}),               350],
    ["ortalama top yoksa medyandan yaklasir",
      yemekFiyati({kat:{"Kebap":{n:2,med:300}}}),                     300],
    ["ortalama pahali kalemi yutmaz",
      yemekFiyati({kat:{"Balık":{n:4,med:200,top:2000}}}),            500],
    /* ANA URUN: Domino's vakasi. Pizza 15 kalem, yaninda 7 tavuk garnituru
       ve tost sayilmis bir dondurma; hepsi sayilirsa 428, ana urunle 480. */
    ["ana urun yan urunu eler",
      yemekFiyati({kat:{"Pizza":{n:15,med:480,top:7200},
                        "Tavuk":{n:7,med:185,top:1295},
                        "Tost / sandviç":{n:1,med:105,top:105}}}),    480],
    ["dengeli menude hepsi sayilir",
      yemekFiyati({kat:{"Balık":{n:5,med:600,top:3000},
                        "Köfte":{n:5,med:300,top:1500}}}),            450],
    ["esikteki tur (yarisi kadar) sayilir",
      yemekFiyati({kat:{"Pizza":{n:4,med:400,top:1600},
                        "Çorba":{n:2,med:100,top:200}}}),             300],
    ["esigin altindaki tur elenir",
      yemekFiyati({kat:{"Pizza":{n:4,med:400,top:1600},
                        "Çorba":{n:1,med:100,top:100}}}),             400],
    ["pastanede tatli ana urundur",
      yemekFiyati({kat:{"Tatlı":{n:3,med:100,top:300},
                        "Çay":{n:9,med:40,top:360}}}),                100],
    ["anaKategoriler en cok kalemliyi secer",
      anaKategoriler({kat:{"Pizza":{n:15},"Tavuk":{n:7}}}).join(),    "Pizza"],
    ["yemek kat yoksa null", yemekFiyati({min:25, max:290}),          null],
    ["yemek tatlicida tatli",
      yemekFiyati({kat:{"Tatlı":{n:2,med:150},"Çay":{n:1,med:30}}}),  150],
    ["yemek tema demosu elenir",
      yemekFiyati({kat:{"Tavuk":{n:4,med:36}},
        menu:[{a:"Fish Tacos",f:32},{a:"Chicken Alfredo",f:36},{a:"French Fries",f:29},
              {a:"Prawns Fry",f:31},{a:"Vegetable Roll",f:25},{a:"Americano",f:38},
              {a:"Pizza Margherita",f:51},{a:"Berry Chocolate",f:29}]}), null],
    ["yemek ucuz ama turkce kalir",
      yemekFiyati({kat:{"Çorba":{n:2,med:60}},
        menu:[{a:"Mercimek Çorbası",f:60},{a:"Ayran",f:30}]}),        60],

    /* --- fiyatin yasi ---
       "Bugun" disaridan veriliyor: kontrolun sonucu takvime bagli olmasin,
       yoksa yazildiktan bir yil sonra kendiliginden kirmiziya doner. */
    ["yas ayi dogru sayar",
      fiyatYasi({tarih:"2026-02"}, new Date(2026, 7, 15)),            6],
    ["yas ayni ay sifir",
      fiyatYasi({tarih:"2026-08"}, new Date(2026, 7, 15)),            0],
    ["yas yil siniri gecer",
      fiyatYasi({tarih:"2025-11"}, new Date(2026, 1, 3)),             3],
    ["yas tarihsizde BILINMIYOR (sifir degil)",
      fiyatYasi({min:30}, new Date(2026, 7, 15)),                     null],
    ["yas bozuk tarihte null",
      fiyatYasi({tarih:"2026-13"}, new Date(2026, 7, 15)),            null],
    ["yas ileri tarihte null (cihaz saati)",
      fiyatYasi({tarih:"2027-01"}, new Date(2026, 7, 15)),            null],
    ["tarih okunur hale gelir", fiyatTarihi({tarih:"2026-08"}), "Ağustos 2026"],
    ["tarih yoksa bos",         fiyatTarihi({min:30}),                ""],
    ["6 aylik fiyat eski isaretlenir",
      fiyatYasEtiketi({tarih:"2026-02"}, new Date(2026, 7, 15)).eski, true],
    ["5 aylik fiyat taze",
      fiyatYasEtiketi({tarih:"2026-03"}, new Date(2026, 7, 15)).eski, false],
    /* Sinirin yemekFiyati icinde olmasi sart: kart, butce suzgeci ve
       "fiyati bilinen" filtresi ayni fonksiyonu cagiriyor. */
    ["11 aylik fiyat hala gosterilir",
      yemekFiyati({tarih:"2025-09", kat:{"Kebap":{n:2,med:300,top:700}}},
                  new Date(2026, 7, 15)),                             350],
    ["12 aylik fiyat GOSTERILMEZ",
      yemekFiyati({tarih:"2025-08", kat:{"Kebap":{n:2,med:300,top:700}}},
                  new Date(2026, 7, 15)),                             null],
    ["tarihsiz eski veri gosterilmeye devam eder",
      yemekFiyati({kat:{"Kebap":{n:2,med:300,top:700}}},
                  new Date(2026, 7, 15)),                             350],
    ["eskiyen fiyat butce suzgecinden de duser",
      bant({tarih:"2025-08", kat:{"Kebap":{n:2,med:300,top:700}}}, 500,
           new Date(2026, 7, 15)),                                    null],
    ["eskimemis fiyat butce suzgecinde kalir",
      (bant({tarih:"2026-05", kat:{"Kebap":{n:2,med:300,top:700}}}, 500,
            new Date(2026, 7, 15)) || {}).sinif,                      "ucuz"],
    ["eskiyen fiyat seviyeden de duser",
      (seviye({tur:"Restoran", tarih:"2025-08",
               kat:{"Kebap":{n:2,med:300,top:700}}},
              new Date(2026, 7, 15)) || {}).olculdu,                  undefined],
    /* Girdiler iki kalemli: bu kontrollerin isi bant'in KARSILASTIRMASI,
       asgari kalem esigi degil. Tek kalemli fixture ile yazilmislardi ve
       esik gelince ikisi birden kirmizi yandi -- kosum takimi yakaladi. */
    ["bant butce ustu",
      (bant({kat:{"Kebap":{n:2,med:400}}}, 200)||{}).sinif,           "tuz"],
    ["bant butce icinde",
      (bant({kat:{"Çorba":{n:2,med:120}}}, 200)||{}).sinif,           "ucuz"],
    ["bant fiyatsiz",       bant({min:null,max:null}, 200),           null],
    ["tl bicim",            tl(1250),                                 "1.250 ₺"],
    ["kacir xss",           kacir('<img src=x onerror=1>'),
                            "&lt;img src=x onerror=1&gt;"],
    /* Tek tirnakli oznitelik yazan biri icin: kacmazsa oznitelikten
       cikilip yeni oznitelik acilabiliyordu. */
    /* --- mutfak metni ---
       485 farkli OSM etiketi var; sozluk ilk 80'i kapsiyor ve
       olculdu: etiketlerin %93,9'u, mekanlarin %94,0'i tam cevriliyor. */
    ["mutfak cevriliyor",        mutfakYaz("turkish"),            "Türk"],
    ["mutfak coklu ayrilir",     mutfakYaz("burger;coffee_shop"), "Burger · Kahveci"],
    ["mutfak alt cizgi temizlenir",
      mutfakYaz("bilinmeyen_sey"),                                "bilinmeyen sey"],
    ["mutfak tekrar elenir",     mutfakYaz("coffee;kahve"),       "Kahve"],
    ["mutfak bos girdi",         mutfakYaz(null),                 ""],
    /* Duz MUTFAK_TR[x] mirasi da dondururdu: "constructor" -> Object. */
    ["mutfak miras alan gecmez", mutfakYaz("constructor"),        "constructor"],

    /* --- web baglantisi ---
       OSM adreslerinin 120'si semasiz. Semasiz href GORELI adres sanilip
       site icinde aranir ve baglanti kirilir. */
    ["web semasiz adrese sema koyar",
      /href="https:\/\/www\.narli\.cafe"/.test(webBagi("www.narli.cafe")), true],
    ["web mevcut semayi korur",
      /href="http:\/\/b\.com"/.test(webBagi("http://b.com")),              true],
    ["web gosterimde sema ve son egik cizgi yok",
      />([^<]*)<\/a>/.exec(webBagi("https://a.com/"))[1],                    "a.com"],
    ["web bos girdi bos doner",       webBagi(""),                          ""],
    ["web null bos doner",            webBagi(null),                        ""],
    /* Onceden bu adres basina bir "https://" eklenerek etkisizlestiriliyordu;
       cikan sey hicbir yere gitmeyen bir BAGLANTIYDI. Artik href hic
       kurulmuyor -- kural guvenliBag()'da, tek yerde. */
    ["web javascript adresi baglanti kurmuyor",
      webBagi("javascript:alert(1)").includes("href="),                     false],
    ["web tirnak kacirilir",
      webBagi('a.com" onmouseover="x').includes('onmouseover="'),            false],

    ["kacir tek tirnak",    kacir("' onmouseover='kotu()"),
                            "&#39; onmouseover=&#39;kotu()"],
    ["kacir cift tirnak",   kacir('" onclick="x'), "&quot; onclick=&quot;x"],
    ["kacir ampersand once", kacir("<&>"), "&lt;&amp;&gt;"],
    /* katkiSorunu: null = kabul. Saatin ayrıştırılabilirliği acikMi ile
       ölçülüyor, o yüzden burada asıl sınanan şey ikisinin bağlı kalması. */
    ["katki saat duz",      katkiSorunu("saat", "09:00-23:00"),          null],
    ["katki saat gunlu",    katkiSorunu("saat", "Mo-Su 09:00-23:00"),    null],
    ["katki saat 24/7",     katkiSorunu("saat", "24/7"),                 null],
    /* Bu kontrol eskiden Turkce yazimin ELENDIGINI dogruluyordu ve karar
       bilerek degisti: gun adlari artik Turkce de okunuyor. Eski davranis
       sessiz bir hataya yol aciyordu -- "Pazartesi-Pazar 10:00-22:00"
       dogrulamadan GECIYOR (bicim tanidik) ama gunUyar gunu cozemedigi
       icin mekan her gun kapali gorunuyordu. Cozum "Turkce'yi de reddet"
       degil "Turkce'yi de oku" oldu: kullanicinin dogal yazdigi bicim.
       Kural hala ayni yerde -- deger acikMi()'ye veriliyor. */
    ["katki saat turkce yazim kabul",
      katkiSorunu("saat", "Her gün 09:00-23:00"),                        null],
    ["katki saat turkce gun araligi kabul",
      katkiSorunu("saat", "Pazartesi-Pazar 10:00-22:00"),                null],
    ["katki saat serbest metin elenir",
      typeof katkiSorunu("saat", "sabah aksam"),                         "string"],
    ["katki tel 10 hane",   katkiSorunu("tel", "5321234567"),            null],
    ["katki tel bosluklu",  katkiSorunu("tel", "+90 532 123 45 67"),     null],
    ["katki tel kisa elenir", typeof katkiSorunu("tel", "12345"),        "string"],
    ["katki adres kisa elenir", typeof katkiSorunu("adres", "abc"),      "string"],
    ["katki web tam bag",   katkiSorunu("web", "instagram.com/cebimde"), null],
    ["katki web https",     katkiSorunu("web", "https://a.com/b"),       null],
    ["katki web handle elenir", typeof katkiSorunu("web", "@cebimde"),  "string"],
    ["katki bos elenir",    typeof katkiSorunu("adres", "  "),           "string"],
    ["katki bilinmeyen alan elenir",
      typeof katkiSorunu("menu", "100"),                                 "string"],

    /* donus adresi: uretenlerin yazdigi her sey gecmeli, geri kalani DUSMELI */
    ["donus kendi sayfasi",  guvenliDonus("hesabim.html", T),          "hesabim.html"],
    ["donus sorgulu",        guvenliDonus("isletme.html?il=34&id=n1", T),
                                                             "isletme.html?il=34&id=n1"],
    ["donus tam kendi adresi",
      guvenliDonus("https://o.test/app/paylas.html", T),               "paylas.html"],
    ["donus javascript",     guvenliDonus("javascript:alert(1)", T),          null],
    ["donus JaVaScRiPt",     guvenliDonus("JaVaScRiPt:alert(1)", T),          null],
    ["donus data",           guvenliDonus("data:text/html,<b>", T),           null],
    ["donus dis site",       guvenliDonus("https://kotu.test/x.html", T),     null],
    ["donus kokensiz",       guvenliDonus("//kotu.test/x.html", T),           null],
    ["donus ust klasor",     guvenliDonus("../gizli.html", T),                null],
    ["donus alt klasor",     guvenliDonus("ic/x.html", T),                    null],
    ["donus html degil",     guvenliDonus("veri/34.json", T),                 null],
    ["donus bos",            guvenliDonus("", T),                             null],

    /* adres semasi: yalniz http/https href'e girer */
    ["bag semasiz",     guvenliBag("instagram.com/x"),   "https://instagram.com/x"],
    ["bag https",       guvenliBag("https://a.test/b"),  "https://a.test/b"],
    ["bag http",        guvenliBag("http://a.test"),     "http://a.test"],
    ["bag javascript",  guvenliBag("javascript:alert(1)"),                 ""],
    ["bag JaVaScRiPt",  guvenliBag("JaVaScRiPt:alert(1)"),                 ""],
    ["bag data",        guvenliBag("data:text/html,<b>"),                  ""],
    ["bag yazim hatasi",guvenliBag("htttps://a.test"),                     ""],
    ["bag bos",         guvenliBag("   "),                                 ""],
    ["web bagi kotu semada METNI birakiyor",
      webBagi("htttps://a.test"),                          "htttps://a.test"],
    ["web bagi kotu semada baglanti kurmuyor",
      webBagi("javascript:alert(1)").indexOf("<a"),                        -1],

    /* profil: yas dogum yilindan hesaplaniyor, veride yas YOK */
    ["yas 1998 -> 28",   yasHesapla(1998, new Date(2026,7,25)),            28],
    ["yas metin girdi",  yasHesapla("1998", new Date(2026,7,25)),          28],
    ["yas bos",          yasHesapla(null),                               null],
    ["yas sacma",        yasHesapla(1200, new Date(2026,7,25)),          null],
    ["yas 13 alti elenir", yasHesapla(2020, new Date(2026,7,25)),        null],
    ["profil ozeti ikisi de var",
      profilOzeti({dogum_yili:1998, meslek:"Öğretmen"}, new Date(2026,7,25)),
                                                            "28 · Öğretmen"],
    ["profil ozeti yalniz meslek",
      profilOzeti({meslek:"Öğretmen"}, new Date(2026,7,25)),      "Öğretmen"],
    ["profil ozeti yalniz yas",
      profilOzeti({dogum_yili:1998}, new Date(2026,7,25)),              "28"],
    ["profil ozeti bos",  profilOzeti({}),                                ""],
    ["profil ozeti yorum alanlariyla",
      profilOzeti({yazar_dogum:1990, yazar_meslek:"Mühendis"}, new Date(2026,7,25)),
                                                            "36 · Mühendis"],
    ["bas harf turkce",   basHarf("ışık"),                              "I"],
    ["bas harf bos",      basHarf(""),                                   "?"],

    /* sosyal: kullanici adi da tam adres de kabul, sema denetleniyor */
    ["sosyal kullanici adi",
      /href="https:\/\/instagram\.com\/cebimde"/.test(sosyalBag("insta","cebimde")), true],
    ["sosyal @ isareti temizlenir",
      /instagram\.com\/cebimde"/.test(sosyalBag("insta","@cebimde")),       true],
    ["sosyal tam adres korunur",
      /href="https:\/\/facebook\.com\/p\/x-123"/.test(
        sosyalBag("facebook","https://facebook.com/p/x-123")),               true],
    ["sosyal javascript adresi baglanti kurmuyor",
      sosyalBag("insta","javascript:alert(1)").includes("href="),          false],
    ["sosyal kokensiz adres elenir",
      sosyalBag("x","//kotu.test/a"),                                         ""],
    ["sosyal bilinmeyen alan",  sosyalBag("myspace","x"),                     ""],
    ["sosyal bos deger",        sosyalBag("insta","  "),                      ""],
    ["sosyal tirnak kacirilir",
      sosyalBag("insta",'a" onmouseover="x').includes('onmouseover="'),    false],
    ["sosyal liste sirali",
      sosyalListe({insta:"a", tiktok:"b", x:"c"}).map(o => o.alan).join(","),
                                                                  "insta,x,tiktok"],
    ["sosyal liste bos mekan",  sosyalListe({}).length,                        0],

    /* --- semt (ilce + mahalle) ---
       Ikisi de veride DOLUYDU ve uygulamaya hic ulasmiyordu: ilce 7.195
       mekan (%20,1), mahalle 3.788 (%10,6). Adresi olmayan 26.455
       mekanin 883'u bununla ilk kez bir yer adi kazaniyor. */
    ["semt ikisi de var",
      semtYaz({mahalle:"Suadiye", ilce:"Kadıköy"}),         "Suadiye · Kadıköy"],
    /* DAR'DAN GENIS'e: mahalle once. Ters sira adres satirinin
       devami gibi okunmazdi. */
    ["semt yalniz ilce",   semtYaz({ilce:"Kadıköy"}),                 "Kadıköy"],
    ["semt yalniz mahalle",semtYaz({mahalle:"Suadiye"}),              "Suadiye"],
    ["semt ikisi de yok",  semtYaz({ad:"X"}),                               ""],
    ["semt mekansiz",      semtYaz(null),                                   ""],
    /* AYNI DEGER IKI KEZ YAZILMIYOR: OSM'de "Fatih" hem ilce hem
       mahalle olabiliyor ve "Fatih · Fatih" sacma gorunurdu. */
    ["semt ayni degeri tekrarlamiyor",
      semtYaz({mahalle:"Fatih", ilce:"Fatih"}),                       "Fatih"],

    /* --- konum: harita ve dis baglantilar ---
       Adresi olan mekan %26,2 (9.397/35.852). Kalan 26.455'te
       koordinat "burasi nerede" sorusunun TEK cevabi, o yuzden
       koordinat denetimi gevsek olamaz. */
    ["koordinat var",       koordinatVar(KNM),                            true],
    ["koordinatsiz mekan",  koordinatVar({ad:"X"}),                      false],
    /* Metin "41.0" DEGIL sayi bekleniyor: veride dizgi gelirse
       toFixed catlar ve harita hic cizilmez. */
    ["koordinat metinse yok", koordinatVar({lat:"41", lon:"29"}),        false],
    ["koordinat NaN'da yok",  koordinatVar({lat:NaN, lon:29}),           false],
    /* Enlem 90'i, boylam 180'i asamaz. Bozuk bir satir haritayi
       dunyanin disina goturur ve yol tarifi bagi anlamsizlasir. */
    ["koordinat sinir disi yok", koordinatVar({lat:91, lon:29}),         false],
    ["koordinat boylam siniri",  koordinatVar({lat:41, lon:181}),        false],
    /* Alti hane ~11 cm. Daha fazlasi veride olmayan bir kesinlik
       iddia ederdi. */
    ["koordinat alti hane", koordinatYaz(KNM),              "40.990000, 29.028000"],
    ["koordinatsizda bos",  koordinatYaz({ad:"X"}),                         ""],

    /* YOL TARIFI KOORDINATA gidiyor: yanilma payi yok. */
    ["yol tarifi koordinatla",
      disHaritalar(KNM, "İstanbul").find(h => h.anahtar === "yol").bag,
      "https://www.google.com/maps/dir/?api=1&destination=40.990000%2C29.028000"],
    /* ARAMA ADLA arıyor ve KOORDINATI DA tasiyor: ad tek basina ayni
       adli baska bir subeye dusuyor. Mekanin Maps yer kimligi (place_id)
       ELIMIZDE YOK, o yuzden dugme "ara" diyor "ac" demiyor. */
    ["arama adi ve ili tasiyor",
      decodeURIComponent(
        disHaritalar(KNM, "İstanbul").find(h => h.anahtar === "google").bag)
        .includes("Konum Kafe Moda Caddesi 1 İstanbul"),                true],
    ["arama koordinati da tasiyor",
      decodeURIComponent(
        disHaritalar(KNM, "İstanbul").find(h => h.anahtar === "google").bag)
        .includes("40.990000,29.028000"),                              true],
    ["dis harita dort bag",  disHaritalar(KNM, "İstanbul").length,          4],
    /* Koordinat yoksa HIC BAG YOK: "yol tarifi" dugmesi nereye
       gidecegini bilmeden gosterilmemeli. */
    ["koordinatsiz mekanda bag yok", disHaritalar({ad:"X"}, "İstanbul").length, 0],
    /* Hepsi https: karisik icerik hem CSP'ye takilir hem baglantiyi
       aciga cikarir. */
    ["dis baglar https",
      disHaritalar(KNM, "İstanbul").every(h => h.bag.startsWith("https://")), true],
    /* Ad ve adres ADRESE KACIRILARAK giriyor: kesme isareti ve bosluk
       ham birakilirsa adres bozulur (Domino's, gercek veride var). */
    ["arama metni kacirildi",
      disHaritalar({lat:40.99, lon:29.028, ad:"Domino's & Co"}, "Ankara")
        .find(h => h.anahtar === "google").bag.includes("%26"),         true],
    ["arama metni ilsiz de calisiyor",
      aramaMetni({ad:"Kafe"}, ""),                                    "Kafe"],
    ["yildiz 4 -> dort dolu",   (yildiz(4).match(/★/g) || []).length,          4],
    ["yildiz aria etiketi",     yildiz(4.5).includes('aria-label='),        true],
    ["yildiz null",             yildiz(null),                                 ""],
    ["yildiz bos dizgi",        yildiz(""),                                   ""],
    ["yildiz sifir",            yildiz(0),                                    ""],
    ["yildiz alti",             yildiz(6),                                    ""],
    ["yildiz metin",            yildiz("abc"),                                ""],
    ["donus yok",            guvenliDonus(null, T),                           null],

    /* --- il dosyasi cozucusu ---
       Python tarafi 81 ilin hepsinde kodla/coz turunu yapiyor
       (veri_bicim.py); burada sinanan sey TARAYICI tarafinin ayni
       nesneyi uretmesi. Sikistirilmis bicim SIK = ornegin kodlanmis
       hali, elle yazildi -- uretici koddan uretilseydi ikisi birlikte
       bozulur ve kontrol yine gecerdi. */
    ["il coz mekan sayisi",   ilCoz(SIK).mekanlar.length,                       3],
    ["il coz id oneki acildi", ilCoz(SIK).mekanlar.map(m => m.id).join(","),
                                                  "node/1,way/2,relation/3"],
    ["il coz yogun alan",     ilCoz(SIK).mekanlar[0].ad,                 "A Kafe"],
    ["il coz seyrek alan",    ilCoz(SIK).mekanlar[1].adres,   "Bagdat Caddesi 448"],
    ["il coz seyrek alan yoksa yok",
                              "adres" in ilCoz(SIK).mekanlar[0],           false],
    ["il coz il adi",         ilCoz(SIK).il,                             "Test"],
    /* Eski bicim oldugu gibi okunmali: yarim kalmis bir dagitimda
       uygulama calismaya devam etsin. */
    ["il coz eski bicim",
      ilCoz({ il:"X", mekanlar:[{id:"node/9"}] }).mekanlar[0].id,      "node/9"],
    ["il coz bos",            ilCoz(null).mekanlar.length,                     0],
    /* Rakamsiz kuyruk kimlik SANILMAMALI: "nazar" -> "node/azar" olurdu. */
    ["il coz rakamsiz kuyruk",
      ilCoz({ sutun:{ id:["nazar"], ad:["N"], tur:["K"], lat:[1], lon:[2] } })
        .mekanlar[0].id,                                              "nazar"],

    /* --- fis esigi: k-anonimlik siniri ---
       Kural artik ortak.js'te. Onceden yalniz isletme.html'de vardi ve
       kesfet ekrani TEK FISTEN tutar basiyordu. */
    ["fis yok -> davet",       /kimse yazmamış/.test(fisOzeti(null)),        true],
    ["fis 0 -> davet",         /kimse yazmamış/.test(fisOzeti({fis:0})),     true],
    ["fis 1 -> 2 tane daha",   /2 tane daha/.test(fisOzeti({fis:1,medyan:300})), true],
    ["fis 2 -> tutar sizmiyor", /₺/.test(fisOzeti({fis:2,medyan:300})),      false],
    ["fis 3 -> medyan cikiyor", /300/.test(fisOzeti({fis:3,medyan:300})),    true],
    ["fis kisi sayisi yazilir",
      /2 kişinin 4 fişinden/.test(fisOzeti({fis:4,medyan:300,kisi:2})),      true],
    ["fis kisi yoksa uydurmuyor",
      /kişinin/.test(fisOzeti({fis:4,medyan:300})),                          false],
    ["fisGoster esik alti",    fisGoster({fis:2,medyan:300}),                false],
    ["fisGoster esikte",       fisGoster({fis:3,medyan:300}),                true],
    /* Fis sayisi esigi gecse bile medyan yoksa gosterilecek sey yok. */
    ["fisGoster medyansiz",    fisGoster({fis:9,medyan:null}),               false],
    ["fisGoster bos",          fisGoster(null),                             false],

    /* --- butce: girdiyi okuma ---
       Kullanicinin yazdigi seyi cozemiyorsak "farketmez"e dusuyoruz;
       sessizce bir sayiya YUVARLAMIYORUZ. */
    ["butce sade sayi",        butceOku("300"),                              300],
    ["butce birimli",          butceOku("300 TL"),                           300],
    ["butce simgeli ve binlik", butceOku("₺1.250"),                         1250],
    ["butce ondalik atilir",   butceOku("1.250,50"),                        1250],
    ["butce cozulemez",        butceOku("abc"),                                0],
    ["butce bos",              butceOku(""),                                   0],
    ["butce null",             butceOku(null),                                 0],
    /* Sinir disi girdi YUVARLANMIYOR: 5'i 20 yapmak kullanicinin
       soylemedigi bir seyi soylemek olurdu. */
    ["butce alt sinirin altinda", butceOku("5"),                               0],
    ["butce ust sinirin ustunde", butceOku("9000"),                            0],
    ["butce alt sinirda kabul",   butceOku("20"),                             20],
    ["butce ust sinirda kabul",   butceOku("5000"),                         5000],

    /* --- butce: tek mekanin durumu ---
       KESIN ile TAHMIN ayrimi bu ozelligin butun anlami: 35.852 mekanin
       163'unde olculmus fiyat var. Ikisini ayni sinifa koyan bir surum,
       %0,45'lik olcumu %100 gibi gosterirdi. */
    ["butce sorulmazsa cevap yok",
      butceDurumu({kat:{"Çorba":{n:2,med:120}}}, 0),                       null],
    ["butce olculmus ve giriyor",
      butceDurumu({kat:{"Çorba":{n:2,med:120}}}, 200).sinif,            "girer"],
    ["butce olculmus giriyor KESIN",
      butceDurumu({kat:{"Çorba":{n:2,med:120}}}, 200).kesin,               true],
    ["butce olculmus ve asiyor",
      butceDurumu({kat:{"Kebap":{n:2,med:400}}}, 200).sinif,           "asiyor"],
    ["butce hesapli TAHMIN",
      butceDurumu({tur:"Fast food"}, 200).sinif,                     "muhtemel"],
    ["butce hesapli kesin DEGIL",
      butceDurumu({tur:"Fast food"}, 200).kesin,                          false],
    ["butce ust segment",
      butceDurumu({tur:"Restoran", mutfak:"steak_house"}, 200).sinif,     "zor"],
    ["butce sinyal yok",
      butceDurumu({tur:"Restoran"}, 200).sinif,                    "bilinmiyor"],
    /* Bar'a ₺300 yeter mi: verimiz yok. Etiket kalir, IDDIA kalmaz --
       "icki mekani"ni "hesapli" saymak uydurma bir cevap olurdu. */
    ["butce bar iddia etmiyor",
      butceDurumu({tur:"Bar"}, 200).sinif,                         "bilinmiyor"],
    ["butce bar etiketi korunuyor",
      butceDurumu({tur:"Bar"}, 200).ad,                           "içki mekanı"],

    /* --- butce: liste dokumu --- */
    ["butce dokum toplam",     BO.toplam,                                      5],
    ["butce dokum girer",      BO.girer,                                       1],
    ["butce dokum asiyor",     BO.asiyor,                                      1],
    ["butce dokum muhtemel",   BO.muhtemel,                                    1],
    ["butce dokum zor",        BO.zor,                                         1],
    ["butce dokum bilinmiyor", BO.bilinmiyor,                                  1],
    /* Olculen ve tahmin AYRI toplaniyor: ekrandaki cumle bu ikisini
       birbirine karistirmasin diye. */
    ["butce dokum olculen",    BO.olculdu,                                     2],
    ["butce dokum tahmin",     BO.tahmin,                                      2],
    ["butce dokum butcesiz",   butceOzeti(BUTCE_LISTE, 0),                  null],
    ["butce dokum listesiz",   butceOzeti(null, 200),                       null],

    /* --- butce: ekrandaki cumle ---
       Cumlenin isi rakam vermek DEGIL, rakamin NE KADARININ olculdugunu
       soylemek. "Kalan ... tahmin ediyorum" kismi silinirse ekran
       %0,45'lik olcumu butun listeye ait gibi gosterir. */
    ["butce cumle olculeni yaziyor",
      /2 mekanın menü fiyatı ölçüldü/.test(butceCumlesi(BO, 200)),         true],
    ["butce cumle giren sayisini yaziyor",
      /1 tanesi 200 ₺ altında/.test(butceCumlesi(BO, 200)),                true],
    ["butce cumle kalani TAHMIN diyor",
      /Kalan 3 mekan .* tahmin ediyorum/.test(butceCumlesi(BO, 200)),      true],
    /* Hicbiri girmiyorsa "0 tanesi giriyor" demek yerine acikca soyle. */
    ["butce cumle hicbiri girmiyorsa",
      /hiçbiri 100 ₺ altında değil/.test(
        butceCumlesi(butceOzeti(BUTCE_LISTE, 100), 100)),                  true],
    /* Olcum HIC yoksa cumle rakam vermiyor, katki cagirisina donuyor. */
    ["butce cumle olcumsuz -> davet",
      /fiyatı gidenler yazıyor/.test(
        butceCumlesi(butceOzeti([{tur:"Restoran"}], 200), 200)),           true],
    ["butce cumle olcumsuzken rakam vermiyor",
      /mekanın menü fiyatı ölçüldü/.test(
        butceCumlesi(butceOzeti([{tur:"Restoran"}], 200), 200)),          false],
    ["butce cumle butcesiz sus",  butceCumlesi(BO, 0),                     null],
    ["butce cumle dokumsuz sus",  butceCumlesi(null, 200),                 null],
    ["butce cumle bos liste",
      butceCumlesi(butceOzeti([], 200), 200),                              null],

    /* --- fiyatin dayanagi: kac olcumden geliyor ---
       Olculdu: fiyati gosterilen 163 mekan yalniz 53 FARKLI isletme ve
       94'u Domino's subesi. Ayni ilde cok subeli 113 mekanin hicbirinde
       subeler arasi fiyat farki yok -- yani tek kazima 56 olcum gibi
       gosteriliyordu. Tek fisi mekanin fiyati saymakla ayni hata. */
    ["dayanak zincir sayiyor",   fiyatDayanagi(ZIL[0], ZH).sube,               3],
    ["dayanak zincir sinifi",    fiyatDayanagi(ZIL[0], ZH).sinif,       "zincir"],
    /* Buyuk/kucuk harf ve bosluk ayni zinciri bolmemeli. */
    ["dayanak harf/bosluk birlesir", fiyatDayanagi(ZIL[2], ZH).sube,           3],
    /* AYNI ad ama FARKLI fiyat = ayri kazima = ayri olcum. */
    ["dayanak farkli fiyat ayrisir", fiyatDayanagi(ZIL[3], ZH).sube,           1],
    ["dayanak farkli fiyat kendi",   fiyatDayanagi(ZIL[3], ZH).sinif, "kendi"],
    ["dayanak tek mekan",        fiyatDayanagi(ZIL[4], ZH).sinif,        "kendi"],
    ["dayanak fiyatsiz mekan",   fiyatDayanagi(ZIL[5], ZH),                 null],
    /* Harita YOKSA "kendi menusu" DENMEZ: il listesini yuklememis bir
       ekran sube sayisini bilemez ve bilmedigini iddiaya cevirmemeli. */
    ["dayanak haritasiz sus",    fiyatDayanagi(ZIL[0], null),               null],
    ["dayanak bos il",           zincirHaritasi([]).size,                      0],
    ["dayanak fiyatsiz haritaya girmez", ZH.size,                             3],
    /* Ekrandaki cumle: zincir halinde SUBE SAYISI ve uyari gecmeli. */
    ["dayanak cumlesi zinciri anlatiyor",
      /3 şubesi listelenen bir zincirin menüsünden/.test(
        dayanakCumlesi(fiyatDayanagi(ZIL[0], ZH))),                        true],
    ["dayanak cumlesi subeye ozel degil diyor",
      /şubeye özel değil/.test(dayanakCumlesi(fiyatDayanagi(ZIL[0], ZH))), true],
    ["dayanak cumlesi kendi menusu",
      /kendi yayımladığı menüden/.test(
        dayanakCumlesi(fiyatDayanagi(ZIL[4], ZH))),                        true],
    ["dayanak cumlesi bos girdi",  dayanakCumlesi(null),                     ""],

    /* --- fiyat guven skoru: yesil / sari / kirmizi ---
       Bantlar olculdu (35.852 mekan): yesil 50 (%0,14), sari 113
       (%0,32), kirmizi 35.689 (%99,55). Kirmizinin genisligi skorun
       kusuru degil verinin durumu; skorun isi tam olarak bunu soylemek. */
    ["guven kendi menusu yesil",
      fiyatGuveni(_kendi, GH, null, null, g14).sinif,                     "yesil"],
    ["guven kendi menusu gerekce",
      /kendi menüsünden/.test(fiyatGuveni(_kendi, GH, null, null, g14).neden), true],
    /* Zincir menusu SARI: rakam gercek ama subeye ozel degil. */
    ["guven zincir sari",
      fiyatGuveni(ZIL[0], ZH, null, null, g14).sinif,                      "sari"],
    ["guven zincir gerekcesi sube sayisi",
      /3 şubede aynı menü/.test(fiyatGuveni(ZIL[0], ZH, null, null, g14).neden), true],
    /* Eskimis fiyat da SARI: rakam duruyor ama kesinligini kaybetti. */
    ["guven eski fiyat sari",
      fiyatGuveni(_eski, GH, null, null, g14).sinif,                       "sari"],
    ["guven eski gerekcesi",
      /eskimiş/.test(fiyatGuveni(_eski, GH, null, null, g14).neden),        true],
    /* Olcum yoksa KIRMIZI -- tur tahmini rengi degistirmiyor, yalniz
       gerekceyi yaziyor. "hesapli gorunuyor" bir olcum degil. */
    ["guven olcumsuz kirmizi",
      fiyatGuveni(_yok, GH, null, null, g14).sinif,                     "kirmizi"],
    ["guven tur tahmini yine kirmizi",
      fiyatGuveni(_tahmin, GH, null, null, g14).sinif,                  "kirmizi"],
    ["guven tur tahmini gerekcede yaziyor",
      /türünden tahmin/.test(fiyatGuveni(_tahmin, GH, null, null, g14).neden), true],
    /* MENUSU FIYATLI OLANA "FIYAT YOK" DENMIYOR. Ayni ekranda menu
       listesi duruyor; rozet o listeyle celisemez. Renk kirmizi kaliyor:
       bir ogunun kaca geldigi hala bilinmiyor. */
    ["menulu mekan yine kirmizi",
      fiyatGuveni(_menulu, GH, null, null, g14).sinif,                  "kirmizi"],
    ["menulu mekana 'fiyat yok' DENMIYOR",
      /fiyat yok/.test(fiyatGuveni(_menulu, GH, null, null, g14).ad),      false],
    ["menulu mekanin rozeti ogun fiyatindan bahsediyor",
      fiyatGuveni(_menulu, GH, null, null, g14).ad,             "öğün fiyatı yok"],
    ["menulu mekanin gerekcesi kalem sayisini yaziyor",
      /menüde 3 kalemin fiyatı var/.test(
        fiyatGuveni(_menulu, GH, null, null, g14).neden),                   true],
    /* Menusu HIC OLMAYAN mekan eski cumleyi almaya devam ediyor:
       orada "fiyat yok" dogru. */
    ["menusuz mekan hala 'fiyat yok' diyor",
      fiyatGuveni(_yok, GH, null, null, g14).ad,                      "fiyat yok"],
    ["menudeFiyatVar fiyatsiz kalemi saymiyor",
      menudeFiyatVar({ menu:[{a:"X"}, {a:"Y", f:10}] }),                        1],
    ["menudeFiyatVar menusuz mekanda sifir",
      menudeFiyatVar(_yok),                                                    0],
    /* FIS YESILE CIKARIYOR: menusu hic olmayan bir mekan uc fisle
       yesil oluyor. Urunun tezi bu -- skor katki geldikce buyuyor. */
    ["guven fis yesile cikariyor",
      fiyatGuveni(_yok, GH, {fis:3, medyan:300}, null, g14).sinif,        "yesil"],
    ["guven fis gerekcesi",
      /3 fişten doğrulandı/.test(
        fiyatGuveni(_yok, GH, {fis:3, medyan:300}, null, g14).neden),      true],
    /* ESIK ALTI FIS YESIL YAPMAZ: iki fis k-anonimlik esiginin altinda
       ve zaten rakam gostermiyor; rengi degistirmesi celiski olurdu. */
    ["guven esik alti fis yesil yapmaz",
      fiyatGuveni(_yok, GH, {fis:2, medyan:300}, null, g14).sinif,      "kirmizi"],
    /* Harita YOKSA zincir bilinemez; skor yine calismali ama zincir
       oldugunu IDDIA ETMEMELI -- bilmedigi seyi sariya boyamasin. */
    ["guven haritasiz yine calisiyor",
      fiyatGuveni(_kendi, null, null, null, g14).sinif,                  "yesil"],
    /* Rozet: renk TEK BASINA bilgi tasimamali. */
    /* GORUNEN metin araniyor, "dogrulanmis" gecen herhangi bir yer degil:
       ilk yazim /doğrulanmış/ diye bakiyordu ve title ozniteligi de ayni
       kelimeyi tasidigi icin GORUNUR METNI SILEN sabotaj gecti. Ayni
       tuzak bu depoda daha once de yasandi (href ile gorunen metin
       karistirilmisti). */
    ["guven rozeti GORUNEN metin tasiyor",
      /<span>doğrulanmış<\/span>/.test(
        guvenRozeti(fiyatGuveni(_kendi, GH, null, null, g14))),            true],
    ["guven rozeti gerekceyi title'a koyuyor",
      /title="[^"]*kendi menüsünden/.test(
        guvenRozeti(fiyatGuveni(_kendi, GH, null, null, g14))),            true],
    ["guven rozeti aria-label tasiyor",
      /aria-label="Fiyat güveni:/.test(
        guvenRozeti(fiyatGuveni(_kendi, GH, null, null, g14))),            true],
    /* Kisa hal yalniz noktayi basiyor ama aria-label yine tam. */
    ["guven rozeti kisa halde metin yok",
      /<span>doğrulanmış/.test(
        guvenRozeti(fiyatGuveni(_kendi, GH, null, null, g14), true)),     false],
    ["guven rozeti kisa halde de aria-label var",
      /aria-label="Fiyat güveni:/.test(
        guvenRozeti(fiyatGuveni(_kendi, GH, null, null, g14), true)),      true],
    ["guven rozeti bos girdi",  guvenRozeti(null),                     ""],

    /* --- sosyal fiyat dogrulama: "bu fiyat hala gecerli mi" ---
       Esik uc, fis esigiyle ayni gerekce: tek kisinin "degismis" demesi
       bir kani, uc ayri kisininki bir sinyal. Esigin ALTINDA sayi
       verilmiyor -- iki kisinin oyu bir mekanin fiyati hakkinda hukum
       degil. */
    ["oy yokken davet",
      /İlk söyleyen sen ol/.test(oyCumlesi(null)),                     true],
    ["oy sifirken davet",
      /İlk söyleyen sen ol/.test(oyCumlesi({kisi:0})),                 true],
    ["oy esik alti sayi vermiyor",
      /kişiden/.test(oyCumlesi({kisi:2, gecerli:2, degisti:0})),      false],
    ["oy esik alti kac kisi kaldigini soyluyor",
      /1 kişi daha/.test(oyCumlesi({kisi:2, gecerli:2, degisti:0})),   true],
    /* SAYI EKI okunusa gore: "3'i" degil "3'u". Iki cumlede birden
       yanlisti ve kontroller yanlisi pinliyordu. */
    ["oy esikte sonucu yaziyor",
      /3 kişiden 3'ü "hâlâ böyle"/.test(
        oyCumlesi({kisi:3, gecerli:3, degisti:0})),                    true],
    ["oy cogunluk degismis derse onu yaziyor",
      /4 kişiden 3'ü "değişmiş"/.test(
        oyCumlesi({kisi:4, gecerli:1, degisti:3})),                    true],
    /* Karar: esik altinda HUKUM YOK. */
    ["oy karari esik alti yok",  oyKarari({kisi:2, gecerli:2, degisti:0}), null],
    ["oy karari yok girdi",      oyKarari(null),                       null],
    ["oy karari gecerli",
      oyKarari({kisi:3, gecerli:2, degisti:1}),                  "gecerli"],
    ["oy karari degismis",
      oyKarari({kisi:3, gecerli:1, degisti:2}),                 "degismis"],
    /* Berabere GECERLI sayiliyor: "degismis" demek rakami kirmiziya
       cevirmek, yani ekrandaki bilgiyi geri almak. Esit sinyalde
       elimizdekini korumak, elimizdekini atmaktan iyi. */
    ["oy karari berabere gecerli",
      oyKarari({kisi:4, gecerli:2, degisti:2}),                  "gecerli"],

    /* --- oy guven skorunu degistiriyor --- */
    /* Fiyat yokken bile TAZE onay yesile cikariyor: sinanan sey oyun
       rozeti degistirdigi. Tarih ARTIK ZORUNLU -- tarihsizin sarida
       kaldigi ayri bir kontrol. */
    ["oy dogrulayinca YESIL",
      fiyatGuveni(_yok, GH, null, {kisi:3, gecerli:3, degisti:0, son_gun:1},
                  g14).sinif,                                       "yesil"],
    ["oy dogrulayinca gerekce",
      /3 kişi "hâlâ böyle" dedi/.test(
        fiyatGuveni(_yok, GH, null, {kisi:3, gecerli:3, degisti:0}, g14).neden),
                                                                       true],
    /* "Degismis" karari, ZINCIR ya da KENDI menusu farketmeksizin
       kirmiziya cekiyor: ekranda yazan rakama itiraz var. */
    ["oy itiraz edince KIRMIZI",
      fiyatGuveni(_kendi, GH, null, {kisi:3, gecerli:0, degisti:3}, g14).sinif,
                                                                  "kirmizi"],
    ["oy itiraz gerekcesi",
      /3 kişi "değişmiş" dedi/.test(
        fiyatGuveni(_kendi, GH, null, {kisi:3, gecerli:0, degisti:3}, g14).neden),
                                                                       true],
    /* Esik altindaki oy skoru DEGISTIRMEMELI: iki kisilik itiraz bir
       mekanin fiyatini kirmiziya cekemez. */
    ["oy esik alti skoru degistirmiyor",
      fiyatGuveni(_kendi, GH, null, {kisi:2, gecerli:0, degisti:2}, g14).sinif,
                                                                    "yesil"],
    /* Oy yoksa eski davranis aynen duruyor. */
    ["oysuz skor degismedi",
      fiyatGuveni(ZIL[0], ZH, null, null, g14).sinif,                 "sari"],

    /* --- Cebimde kombini ---
       OLCULDU: iki mekanli kombin bu veriyle kurulamiyor (400 m icinde
       farkli adli ikinci fiyatli mekani olan 22/163 = %13); tek mekan
       icinde %90 (146/163). O yuzden kombin mekanin KENDI menusunden.

       EN UCUZ secliyor, butceye "oturan" sepet aranmiyor: butceye gore
       kalem secmek kullanicinin sormadigi bir tercihte bulunmak olurdu.
       Sorulan sey "yeter mi". */
    ["kombin en ucuz ana urunu secer",
      (KR.kalemler[0] || {}).a,                              "Kucuk Pizza"],
    ["kombin en ucuz icecegi secer",
      (KR.kalemler[1] || {}).a,                               "Kucuk Kola"],
    ["kombin toplami",         KR.toplam,                              340],
    /* KATEGORISIZ kalem girmemeli: 5 TL'lik "Bilinmeyen" en ucuz kalem
       ama ne oldugunu bilmedigimiz bir seyi "yanina icecek" diye
       sunmak uydurma bir sepet olurdu. */
    /* Sepetin TAMAMI pinleniyor, "Bilinmeyen yok mu" diye bakmak
       yerine: kategorisiz kalemi kabul eden bir surum sepeti bozup
       null'a dusuyor ve "icinde Bilinmeyen yok" kontrolu o halde de
       gecerdi -- yani dogru sebeple degil yanlis sebeple. */
    ["kombin sepeti tam olarak bu iki kalem",
      KR.kalemler.map(k => k.a).join(" + "),   "Kucuk Pizza + Kucuk Kola"],
    ["kombin butce iciyse isaretler",  KR400.butceIci,               true],
    ["kombin butce disiysa isaretler", KR200.butceIci,              false],
    ["kombin butcesiz hep ici",        KR.butceIci,                  true],
    /* Icecegi olmayan mekan tatliya duser -- ama tatlisi da yoksa
       kombin KURULMAZ. */
    ["kombin icecek yoksa tatliya duser",
      ((kombinKur(KOMBIN_TATLI, 0) || {kalemler:[]}).kalemler[1] || {}).a,
                                                                  "Sutlac"],
    ["kombin yalniz ana urunle kurulmaz",  kombinKur(KOMBIN_TEK, 0),  null],
    ["kombin menusuz mekan",   kombinKur({tur:"Restoran"}, 0),        null],
    ["kombin bos girdi",       kombinKur(null, 0),                    null],

    /* --- kombin cumlesi --- */
    ["kombin cumlesi kalemleri yaziyor",
      /Kucuk Pizza 300 ₺ \+ Kucuk Kola 40 ₺ = 340 ₺/.test(
        kombinCumlesi(kombinKur(KOMBIN, 0), 0)),                      true],
    ["kombin cumlesi butceye giriyorsa soyluyor",
      /bütçene giriyor/.test(
        kombinCumlesi(kombinKur(KOMBIN, 400), 400)),                  true],
    /* Asan tutar RAKAMLA yaziliyor: "yetmiyor" demek kullaniciyi hesap
       yapmaya birakir. */
    ["kombin cumlesi asan tutari yaziyor",
      /140 ₺ aşıyor/.test(kombinCumlesi(kombinKur(KOMBIN, 200), 200)), true],
    ["kombin cumlesi bos girdi",  kombinCumlesi(null, 300),             ""],
    /* ALKOLSUZ ONCE. Olculen vaka: kombin "patlican salatasi + Efes
       Malt" cikiyordu cunku menudeki en ucuz icecek biraydi. Uygulama
       alkollu mekanlari listeliyor ve bu dogru; kimsenin istemedigi bir
       ogune varsayilan olarak icki koymak ayri bir sey. */
    ["kombin ucuz olsa da alkolu secmiyor",
      ((kombinKur(KOMBIN_ALKOL, 0) || {kalemler:[]}).kalemler[1] || {}).a,
                                                                   "Ayran"],
    ["kombin alkolsuz hic yoksa alkollu geliyor",
      ((kombinKur(KOMBIN_SADECE_ALKOL, 0) || {kalemler:[]}).kalemler[1] || {}).a,
                                                                    "Raki"],

    /* --- kullanici seviyesi ---
       ONAYDAN GECMIS katki sayiliyor, gonderilen degil: gonderileni
       saymak seviyeyi kuyruga cop atarak yukseltilebilir yapardi.
       Fiyat oyu seviyeye GIRMIYOR -- tek dokunus ve onay kuyrugu yok. */
    /* --- kampanya satiri (urun tarifi md.3: "kampanya alani") --- */
    ["kampanya bayragi okunuyor",   kampanyaMi({a:"1 Alana 1 Bedava", f:80, p:1}),
                                                                        true],
    ["bayraksiz kalem kampanya degil", kampanyaMi({a:"Latte", f:95}),  false],
    ["kampanya menu listesinden cikiyor",
      menuKalemleri(KMP).map(k => k.a).join(","),              "Latte,Lahmacun"],
    ["kampanya kendi listesinde",
      kampanyalar(KMP).map(k => k.a).join(","),         "1 Alana 1 Bedava Kola"],
    /* Rozet "menude N kalemin fiyati var" diyor ve o cumle bir URUN
       fiyati vaat ediyor -- teklif o sayiya girmemeli. */
    ["kampanya menudeFiyatVar'a girmiyor", menudeFiyatVar(KMP),           2],
    /* Kombin zaten kategori istiyordu; civar listesi ISTEMIYORDU ve
       "Patates Firsati 60 TL" en ucuz yemek diye cikabilirdi. */
    ["civar kampanyayi onermiyor",
      civarKalemleri(CV0, CVL, 0).some(k => k.ad === "Kampanya Tost"), false],
    ["kampanya kombine girmiyor",
      kombinListesi(KMP).length,                                          0],

    /* --- "bu civarda ne yenir" (urun tarifi md.10) ---
       Fixture: iki zincir subesi AYNI kalemi tasiyor (tekillestirme
       sinaniyor), bir mekan yalniz icecek satiyor (disarida kalmali),
       bir mekan cok uzak (yaricap disi). */
    ["civar kalem ucuzdan pahaliya",
      civarKalemleri(CV0, CVL, 0).map(k => k.fiyat).join(","),  "40,55,90,300"],
    ["civar ayni kalemi bir kez veriyor",
      civarKalemleri(CV0, CVL, 0).filter(k => k.ad === "Lahmacun").length,   1],
    ["civar tekrarda EN YAKIN sube kaliyor",
      civarKalemleri(CV0, CVL, 0).find(k => k.ad === "Lahmacun").mekan,
                                                                    "Yakin Sube"],
    /* Icecek ve tatli disarida: soru "ne YENIR" ve menudeki en ucuz
       kalem neredeyse her zaman bir icecek. */
    ["civar icecegi listelemiyor",
      civarKalemleri(CV0, CVL, 0).some(k => k.ad === "Ayran"),          false],
    ["civar yaricap disini almiyor",
      civarKalemleri(CV0, CVL, 0).some(k => k.mekan === "Uzak"),        false],
    /* Butce ASANLARI ELEMIYOR, sona atiyor: 300 TL'ye bakan biri
       320 TL'lik secenegi de gormeli. */
    ["civar butce asani sona atiyor",
      civarKalemleri(CV0, CVL, 100).map(k => k.fiyat).join(","),"40,55,90,300"],
    /* Bir mekandan tek kalem: Corbaci'nin 55'i giriyor, 70'i girmiyor. */
    ["civar mekan basina tek kalem",
      civarKalemleri(CV0, CVL, 0).filter(k => k.mekan === "Corbaci").length, 1],
    ["civar mekandan en ucuzunu aliyor",
      civarKalemleri(CV0, CVL, 0).find(k => k.mekan === "Corbaci").fiyat,   55],
    ["civar butcesiz mekanda bos",   civarKalemleri(CV0, [], 0).length,    0],
    ["civar konumsuz mekanda bos",   civarKalemleri({ad:"X"}, CVL, 0).length, 0],

    /* --- "son dogrulanma" (urun tarifi md.5) --- */
    ["gun once bugun",      gunOnce(0),                              "bugün"],
    ["gun once dun",        gunOnce(1),                                "dün"],
    ["gun once uc gun",     gunOnce(3),                          "3 gün önce"],
    ["gun once ay",         gunOnce(45),                           "2 ay önce"],
    ["gun once yil",        gunOnce(400),                          "1 yıl önce"],
    /* Sunucu esik altinda tarih DONDURMUYOR; yoklugu normal ve cumle
       tarihsiz de tam kalmali. */
    ["gun once null sus",   gunOnce(null),                                 ""],
    ["gun once metin sus",  gunOnce("abc"),                                ""],
    ["gun once negatif sus", gunOnce(-3),                                  ""],
    ["rozet gerekcesinde tarih",
      /3 kişi "hâlâ böyle" dedi — 2 gün önce/.test(
        fiyatGuveni(_yok, GH, null, {kisi:3, gecerli:3, degisti:0, son_gun:2},
                    g14).neden),                                         true],
    /* Tarihsizde cumle "3 kişi ... dedi (tarihi bilinmiyor)" oluyor:
       tire+tarih EKLENMIYOR, yerine bilinmedigi YAZILIYOR. */
    ["rozet tarihsizde tarih uydurmuyor",
      /3 kişi "hâlâ böyle" dedi \(tarihi bilinmiyor\)$/.test(
        fiyatGuveni(_yok, GH, null, {kisi:3, gecerli:3, degisti:0}, g14).neden),
                                                                         true],
    /* ONAYIN RAF OMRU (urun tarifi md.5: 7 / 30 gun). */
    ["taze onay yesil",
      fiyatGuveni(_yok, GH, null, {kisi:3, gecerli:3, degisti:0, son_gun:2},
                  g14).sinif,                                       "yesil"],
    ["yedinci gun hala yesil",
      fiyatGuveni(_yok, GH, null, {kisi:3, gecerli:3, degisti:0, son_gun:7},
                  g14).sinif,                                       "yesil"],
    ["sekizinci gun sariya duser",
      fiyatGuveni(_yok, GH, null, {kisi:3, gecerli:3, degisti:0, son_gun:8},
                  g14).sinif,                                        "sari"],
    ["otuzuncu gun hala sari",
      fiyatGuveni(_yok, GH, null, {kisi:3, gecerli:3, degisti:0, son_gun:30},
                  g14).sinif,                                        "sari"],
    /* 30 gunu gecen onay HUKUM VERMEYI BIRAKIYOR: _yok'un menusunde
       ogun fiyati yok, o yuzden karar menu koluna dusup kirmizi cikiyor.
       Onayin kendisi ceza degil -- sadece artik kanit degil. */
    ["otuz birinci gun hukum vermiyor",
      fiyatGuveni(_yok, GH, null, {kisi:3, gecerli:3, degisti:0, son_gun:31},
                  g14).sinif,                                     "kirmizi"],
    ["eski onay menuyu bastirmiyor",
      fiyatGuveni(_kendi, GH, null, {kisi:3, gecerli:3, degisti:0, son_gun:90},
                  g14).sinif,                                       "yesil"],
    /* Tarihsiz onay yesil OLAMAZ: yasini bilmedigimiz bir onay
       "son 7 gun" diyemez. */
    ["tarihsiz onay yesil degil",
      fiyatGuveni(_yok, GH, null, {kisi:3, gecerli:3, degisti:0}, g14).sinif,
                                                                     "sari"],
    ["oy yasi tarihsizde null",   oyYasi({kisi:3}),                    null],
    ["oy yasi sifiri sifir okur", oyYasi({son_gun:0}),                    0],
    ["oy yasi bozugu null",       oyYasi({son_gun:"abc"}),            null],
    /* Kalem duzeyinde tarih (urun tarifi md.4). Sabit "simdi" veriliyor:
       Date.now() ile kosan bir kontrol yarin baska sonuc verirdi. */
    ["zaman yasi bugun",   zamanYasi("2026-08-26T09:00:00Z", g26),           0],
    ["zaman yasi dun",     zamanYasi("2026-08-25T09:00:00Z", g26),           1],
    ["zaman yasi hafta",   zamanYasi("2026-08-19T12:00:00Z", g26),           7],
    ["zaman yasi bos null",     zamanYasi("", g26),                       null],
    ["zaman yasi bozuk null",   zamanYasi("dun", g26),                    null],
    /* Ileri tarih null: cihazin saati yanlissa kalem "-2 gun once"
       olmasin, tarihsiz kalsin. */
    ["zaman yasi ileri tarih null", zamanYasi("2026-09-01T00:00:00Z", g26), null],
    ["zaman yasi cumleye donuyor",
      gunOnce(zamanYasi("2026-08-23T12:00:00Z", g26)),          "3 gün önce"],
    /* Number(null) ve Number("") SIFIR. Bu iki degeri once elemezsek
       tarihi olmayan bir oy "bugün" diye okunur ve rozet elimizde
       olmayan bir tazeligi iddia eder -- ayni tuzak gunOnce'ta da vardi. */
    ["oy yasi acik null'da null",  oyYasi({son_gun:null}),            null],
    ["oy yasi bos metinde null",   oyYasi({son_gun:""}),              null],
    ["acik null onay yesil degil",
      fiyatGuveni(_yok, GH, null,
        {kisi:3, gecerli:3, degisti:0, son_gun:null}, g14).sinif,     "sari"],
    ["degismis rozetinde de tarih",
      /— dün/.test(fiyatGuveni(_kendi, GH, null,
        {kisi:3, gecerli:0, degisti:3, son_gun:1}, g14).neden),          true],

    /* --- cok butceli oneri (urun tarifi md.11) ---
       Fixture ELLE: menude iki ana urun ve iki yan var, yani dort ikili
       kurulabiliyor ve basamaklarin gercekten AYRILDIGI gorulebiliyor. */
    ["oneri basamaklari cikiyor",     oneriBasamaklari(ONR).length,           3],
    /* HER BASAMAKTA EN PAHALI UYAN. En ucuzu vermek, kullanicinin
       elindeki parayi bilerek eksik kullandirmak olurdu. */
    ["oneri en pahali uyani veriyor",
      oneriBasamaklari(ONR)[2].kombin.toplam,                               180],
    ["oneri basamak esikleri artan",
      oneriBasamaklari(ONR).map(x => x.esik).join(","),           "100,150,200"],
    ["oneri esigi asan kombin secilmiyor",
      oneriBasamaklari(ONR).every(x => x.kombin.toplam <= x.esik),        true],
    /* Menusuz ya da tek kalemli mekanda bolum hic acilmamali. */
    ["oneri menusuz mekanda bos",     oneriBasamaklari({ad:"X"}).length,      0],
    ["oneri tek kalemde bos",
      oneriBasamaklari({ad:"X", kat:{"Kebap":{n:1,med:50}},
                        menu:[{a:"Kebap", f:50, k:"Kebap"}]}).length,        0],
    /* ALKOL YANINDA SONA: kombinKur ile ayni kural. Alkolsuz yan varken
       alkollu kalem basamaklara girmemeli. */
    ["oneri alkolsuz yani secer",
      oneriBasamaklari(ONR).every(x =>
        !x.kombin.kalemler.some(k => ALKOL_KAT.has(k.k))),                true],
    ["oneri cumlesi iki kalemi yaziyor",
      /ANA \+ TATLI/.test(oneriCumlesi(oneriBasamaklari(ONR)[0])),        true],
    ["oneri cumlesi bos girdide sus",  oneriCumlesi(null),                   ""],
    /* Menude ondan UCUZ bir bira var; alkol suzgeci calismazsa butun
       basamaklar ona kayar ve toplamlar degisir. */
    ["oneri en ucuz yan bira olsa da alkolsuz",
      oneriBasamaklari(ONR)[0].kombin.kalemler.map(k => k.a).join("+"),
                                                                  "ANA+TATLI"],
    /* AYNI KALEM IKI KEZ SAYILMAZ: yalniz tatli satan mekanda ana urun
       ile yan ayni kumeden geliyor. */
    ["oneri ayni kalemi kendisiyle eslemiyor",
      oneriBasamaklari(ONR_TEK).every(x =>
        x.kombin.kalemler[0] !== x.kombin.kalemler[1]),                   true],
    ["oneri pastanede yine basamak veriyor",
      oneriBasamaklari(ONR_TEK).length >= 1,                             true],

    ["seviye sifir katki",       seviyeHesapla(0).ad,          "Yeni Cebimdeci"],
    ["seviye ilk katki",         seviyeHesapla(1).ad,            "Menü Avcısı"],
    ["seviye ikide hala menu avcisi", seviyeHesapla(2).ad,       "Menü Avcısı"],
    /* 3 = FIS_ESIK: tek basina bir mekanin fiyatini esige tasiyabilecek
       sayi. Esigin kendisi degisirse bu ad da anlamini kaybeder. */
    ["seviye ucte fiyat dedektifi", seviyeHesapla(3).ad,      "Fiyat Dedektifi"],
    ["seviye onda gurme",        seviyeHesapla(10).ad,       "Cebimde Gurmesi"],
    ["seviye en ust elci",       seviyeHesapla(500).ad,       "Cebimde Elçisi"],
    /* EN UST BASAMAKTA "sonraki" NULL olmali: merdiven bittiginde
       "N katki sonra X" demek, olmayan bir basamagi vaat etmek olurdu. */
    ["seviye en ustte sonraki yok", seviyeHesapla(500).sonraki,          null],
    /* Bozuk girdi seviyeyi yukseltmemeli: negatif, metin, null hepsi
       sifir sayiliyor. */
    ["seviye negatif sifir sayilir",  seviyeHesapla(-5).ad,  "Yeni Cebimdeci"],
    ["seviye metin sifir sayilir",    seviyeHesapla("abc").ad, "Yeni Cebimdeci"],
    ["seviye null sifir sayilir",     seviyeHesapla(null).ad, "Yeni Cebimdeci"],
    ["seviye ondalik asagi yuvarlanir", seviyeHesapla(2.9).ad, "Menü Avcısı"],
    /* Kalan katki RAKAMLA: kullaniciyi ilerleme cubuguna bakip tahmin
       etmeye birakmak, ekranin isini kullaniciya yikmak olurdu. */
    ["seviye kalan katki sayisi",     seviyeHesapla(7).kalan,               3],
    ["seviye en ustte sonraki yok",   seviyeHesapla(50).sonraki,         null],
    ["seviye en ustte kalan sifir",   seviyeHesapla(50).kalan,              0],
    ["seviye cumlesi sifirda davet",
      /İlk katkın seni Menü Avcısı yapar/.test(seviyeCumlesi(seviyeHesapla(0))), true],
    ["seviye cumlesi kalani yaziyor",
      /3 katkı daha: Cebimde Gurmesi/.test(seviyeCumlesi(seviyeHesapla(7))), true],
    ["seviye cumlesi en ustte",
      /En üst seviyedesin/.test(seviyeCumlesi(seviyeHesapla(25))),        true],
    ["seviye cumlesi bos girdi",      seviyeCumlesi(null),                 ""],

    /* --- butce talebi (isletme paneli) ---
       TAM TUTAR DEGIL BANT saklaniyor: sayac satiri (mekan, gun, cihaz)
       uclusu ve oraya "347 TL" yazmak ucluyu giderek daha ayirt edici
       yapardi. Bes kova, esikleri BUTCE_SECENEK'ten -- ekranda
       kullaniciya sunulan sayilarla ayni, ikinci bir olcek uydurulmadi. */
    ["bant girilmemis butce null",   butceBandi(0),                     null],
    ["bant cozulemeyen butce null",  butceBandi("abc"),                 null],
    ["bant ilk esigin altinda",      butceBandi(100),                      1],
    ["bant ilk esikte",              butceBandi(150),                      2],
    ["bant ikinci aralik",           butceBandi(300),                      3],
    ["bant ucuncu aralik",           butceBandi(500),                      4],
    ["bant son esikte",              butceBandi(700),                      5],
    ["bant son esigin ustunde",      butceBandi(4000),                     5],
    /* Bant ADI ekranda okunacak: "bant 3" kimseye bir sey soylemez. */
    ["bant adi ilk",                 butceBandiAdi(1),           "150 ₺ altı"],
    ["bant adi ortada",              butceBandiAdi(3),      "250 ₺ – 399 ₺"],
    ["bant adi son",                 butceBandiAdi(5),       "700 ₺ ve üstü"],
    ["bant adi gecersiz",            butceBandiAdi(9),                    ""],
    /* Cumle EN KALABALIK bandi yaziyor; bes satirlik bir tablo panelde
       asil bilgiyi bogardi. */
    ["talep cumlesi en kalabalik bandi yaziyor",
      /9 kişinin 5'i 250 ₺ – 399 ₺ arıyordu/.test(butceTalebiCumlesi(
        [{bant:1,kisi:2},{bant:3,kisi:5},{bant:5,kisi:2}])),            true],
    /* --- Turkce sayi eki ---
       Ek sayinin OKUNUSUNUN son hecesine bakiyor ve son SOYLENEN
       kelimeden geliyor: 14 = "on dort" -> "14'u"; 47 = "kirk yedi" ->
       "47'si". Ekranda iki yerde yanlis yaziyordu. */
    ["ek bir",        sayiEkli(1),        "1'i"],
    ["ek iki (kaynastirma)", sayiEkli(2), "2'si"],
    ["ek uc",         sayiEkli(3),        "3'ü"],
    ["ek dort",       sayiEkli(4),        "4'ü"],
    ["ek alti (kaynastirma)", sayiEkli(6), "6'sı"],
    ["ek dokuz",      sayiEkli(9),        "9'u"],
    ["ek on",         sayiEkli(10),      "10'u"],
    /* Iki basamakli: son kelime birler basamagi. */
    ["ek on dort",    sayiEkli(14),      "14'ü"],
    ["ek kirk yedi",  sayiEkli(47),      "47'si"],
    /* Tam onluk: son kelime onlar basamagi. */
    ["ek kirk",       sayiEkli(40),      "40'ı"],
    ["ek elli",       sayiEkli(50),      "50'si"],
    ["ek doksan",     sayiEkli(90),      "90'ı"],
    ["ek yuz",        sayiEkli(100),    "100'ü"],
    ["ek bin",        sayiEkli(1000), "1.000'i"],
    /* Binlik ayrac ekten bagimsiz: ek SAYIDAN hesaplaniyor, metinden
       degil. 1.250 = "bin iki yuz elli" -> elli -> si */
    ["ek binlik ayracli", sayiEkli(1250), "1.250'si"],
    ["ek sifir",      sayiEkli(0),        "0'ı"],
    /* TALEP ACIGI. Medyan aranan bandin TAVANININ ustundeyse "aradiklarinin
       ustunde" diyor; altindaysa DEMIYOR -- olmayan bir acik uydurmuyor. */
    ["talep acigi bos",              talepAcigiCumlesi([], 300),         ""],
    ["talep acigi medyansiz",
     /9 kişinin 5'i .*arıyordu\.$/.test(talepAcigiCumlesi(
       [{bant:2,kisi:5},{bant:1,kisi:4}], null)),                        true],
    ["talep acigi ACIK VAR",
     /aradıklarının üstünde/.test(talepAcigiCumlesi(
       [{bant:1,kisi:9}], 9000)),                                        true],
    ["talep acigi ACIK YOK",
     /aradıklarının üstünde/.test(talepAcigiCumlesi(
       [{bant:5,kisi:9}], 100)),                                         false],
    ["talep cumlesi bos dagilim",    butceTalebiCumlesi([]),             ""],
    ["talep cumlesi null",           butceTalebiCumlesi(null),           ""],

    /* --- ana ekranin kategorileri ---
       Ciplerin turleri veride GERCEKTEN var olmali; yanlis yazilmis tek
       bir tur adi, cipe basan kullaniciya bos liste verir ve bunu
       hicbir sey soylemez. */
    /* DORT. Maket dort daire gosteriyor ve ekran altiyla iki satira
       tasiyordu. Sayi burada SABITLENIYOR: besinciyi eklemek ekrani
       sessizce iki satira dondururdu. */
    ["kategori sayisi",        CANIM.length,                                   4],
    ["kategori olcutleri tanimli",
      CANIM.every(k => k.tur.length &&
        k.tur.every(t => t.slice(0,4) === "kat:" && !!KATEGORI[t.slice(4)])), true],
    /* KATEGORININ her turu ve her mutfagi GERCEK olmali. Yanlis yazilmis
       tek bir etiket, cipe basan kullaniciya sessizce bos liste verir. */
    ["kategori turleri gercek",
      Object.values(KATEGORI).every(k => k.tur.every(t =>
        t.slice(0,5) === "grup:" ? !!TUR_GRUP[t.slice(5)]
                                 : TUR_GRUP.yeme.has(t))),                   true],
    ["kategorinin bos olani yok",
      Object.values(KATEGORI).every(k => k.tur.length || k.mutfak.length),   true],
    /* ORTUSME SERBEST -- ve bunu SINIYORUZ, cunku eski kural tam tersiydi
       ("kategoriler ortusmuyor"). Bir kebapci hem Yemek hem Esnaf; iki
       istege birden cevap veriyor. Suzgec birlesim aldigi icin ayni mekan
       listede iki kez cikmiyor. */
    ["kebapci hem yemek hem esnaf",
      mekanUyar(["kat:yemek"], {tur:"Restoran", mutfak:"kebab"}) &&
      mekanUyar(["kat:esnaf"], {tur:"Restoran", mutfak:"kebab"}),            true],
    /* MUTFAK EKSENI: tur'u Restoran olan bir mekan, mutfagi breakfast ise
       Kahvalti'ya da giriyor. Onceki suzgec tur'dan baska bir sey
       gormedigi icin bu mekan hicbir kahvalti aramasinda cikmazdi. */
    ["mutfaktan kahvalti",
      mekanUyar(["kat:kahvalti"], {tur:"Restoran", mutfak:"turkish;breakfast"}), true],
    ["mutfaksiz mekan kahvaltiya girmiyor",
      mekanUyar(["kat:kahvalti"], {tur:"Restoran"}),                        false],
    ["mutfak buyuk harfle de eslesiyor",
      mekanUyar(["kat:tatli"], {tur:"Kafe", mutfak:"Ice_Cream"}),            true],
    /* Tatli IKI EKSENDEN birden: tur:Dondurma da, mutfak:dessert de. */
    ["dondurmaci turden tatliya giriyor",
      mekanUyar(["kat:tatli"], {tur:"Dondurma"}),                            true],
    /* ESKI BICIM CALISMAYA DEVAM ETMELI: saha kartlarindaki ve
       paylasilmis baglantilardaki adresler "?tur=Kafe" tasiyor. */
    ["duz tur adi hala calisiyor",
      mekanUyar(["Kafe"], {tur:"Kafe"}),                                     true],
    ["grup: hala calisiyor",
      mekanUyar(["grup:eglence"], {tur:"Sinema"}),                           true],
    ["bilinmeyen kategori sessizce eslesmiyor",
      mekanUyar(["kat:yokboyle"], {tur:"Kafe"}),                            false],

    /* --- butce akranlari --- */
    ["akran butcesiz sus",     akranCumlesi({akran:5,mekan:2}, 0),           null],
    ["akran ozetsiz sus",      akranCumlesi(null, 300),                      null],
    ["akran sifir -> davet",
      /ilk yazan sen ol/.test(akranCumlesi({akran:0,fis:0,mekan:0}, 300)),   true],
    ["akran sayisi cumlede",
      /37 kişi son 6 ayda 12 mekanda/.test(
        akranCumlesi({akran:37, fis:80, mekan:12}, 300)),                    true],

    /* --- civar (mahalle statusu) ---
       lat +0.001 ~ 110 m, +0.004 ~ 442 m, +0.006 ~ 663 m (39,9 enleminde). */
    ["mesafe 0.001 derece enlem ~110 m",
      Math.round(mesafeM({lat:39.9,lon:32.85}, {lat:39.901,lon:32.85})),     111],
    ["mesafe ayni nokta",
      Math.round(mesafeM({lat:39.9,lon:32.85}, {lat:39.9,lon:32.85})),         0],
    ["civar yakin sayisi",     C.yakin,                                        4],
    ["civar yaricapi",         C.yaricap,                                    500],
    /* 663 m'deki mekan disarida kalmali: yarim kalan bir "civar" tanimi
       kutudaki butun sayilari kaydirir. */
    ["civar uzaktakini almaz", C.idler.includes("uzak"),                   false],
    ["civar kendini saymaz",   C.idler.includes("ben"),                    false],
    /* Fiyati bilinen komsu sayisi: kutunun katki cagrisi buna dayaniyor. */
    ["civar fiyatli komsu",    C.fiyatli,                                      1],
    ["civar tur dagilimi",     C.turler[0][0] + ":" + C.turler[0][1],   "Kafe:2"],
    ["civar tenha yer yok",
      civarOzeti({id:"tek",lat:10,lon:10}, [{id:"a",lat:20,lon:20,tur:"Kafe"}]), null],
    ["civar koordinatsiz mekan",
      civarOzeti({id:"x"}, [{id:"a",lat:20,lon:20,tur:"Kafe"}]),            null],
    /* Kalabalik civar: 600 mekan 500 m'ye sigiyor ama sunucu 500 kabul
       ediyor. Yaricap 100'er metre daraliyor. */
    ["kalabalik yaricap daraldi",  K.yaricap < 500,                        true],
    ["kalabalik liste kirpilmadi", K.idler.length === K.yakin,             true],
    ["kalabalik sunucu sinirinda", K.idler.length <= 500,                  true],
    /* Daralan yaricap EKRANDA yaziyor; sayim da o yaricapa ait olmali.
       300 mekan 90 m'de, digerleri 442 m'de -> 400 m'de 300 kalir. */
    ["kalabalik sayim yaricapla tutarli", K.yakin,                          300],

    /* bugun: YEREL gun. Gece 01:30'da (UTC hala dun) bugunu vermeli. */
    ["bugun gece yarisindan sonra",
      bugunYerel(new Date(2026, 7, 25, 1, 30)),                  "2026-08-25"],
    ["bugun gunduz",  bugunYerel(new Date(2026, 7, 25, 14, 0)),  "2026-08-25"],
    ["bugun tek haneli ay/gun",
      bugunYerel(new Date(2026, 0, 3, 12, 0)),                   "2026-01-03"]
  ];
  const hata = kontroller.filter(k => JSON.stringify(k[1]) !== JSON.stringify(k[2]));
  document.body.insertAdjacentHTML("afterbegin",
    '<pre style="margin:0;padding:12px 16px;font:13px/1.5 ui-monospace,monospace;' +
    'white-space:pre-wrap;color:#fff;background:' + (hata.length ? "#5b1a1a" : "#1d3a17") + '">' +
    (hata.length
      ? "BASARISIZ (" + hata.length + "/" + kontroller.length + "):\n" +
        hata.map(h => "  " + h[0] + " -> " + JSON.stringify(h[1]) +
                      " beklenen " + JSON.stringify(h[2])).join("\n")
      : kontroller.length + " kontrolun hepsi gecti") + "</pre>");
}

/* ============================================================
   Service worker kaydı

   BURADA, satır içi bir <script> içinde DEĞİL: ortak.js zaten on
   sayfanın hepsinde yüklü ve satır içi bir blok eklemek CSP karmalarını
   on yerde büyütürdü.

   NEDEN VAR: uygulama Google Play'e TWA olarak paketleniyor (PLAY.md).
   Çevrimdışıyken tarayıcının kendi hata ekranını göstermek Play'in
   "bozuk işlevsellik" kuralına takılıyor; `sw.js` onun yerine
   `cevrimdisi.html`'i veriyor.

   HTTP'DE KAYIT YAPILMIYOR. Service worker yalnız güvenli kaynakta
   (https ya da localhost) çalışıyor; başka bir yerde `register` zaten
   reddediliyor ve konsola hata düşüyor. Koşul burada, hata sessizce
   birikmesin diye.

   HATA YUTULMUYOR AMA SAYFAYI DA DURDURMUYOR: kayıt başarısız olursa
   uygulama service worker'sız çalışmaya devam ediyor — bu bir hızlanma
   katmanı, çalışma şartı değil. */
function swKur(){
  if (!("serviceWorker" in navigator)) return;
  const g = location.protocol === "https:" ||
            location.hostname === "localhost" ||
            location.hostname === "127.0.0.1";
  if (!g) return;
  /* `load` sonrası: kayıt, ilk çizimle ağ için yarışmasın. */
  addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(e =>
      console.warn("service worker kaydedilemedi:", e && e.message));
  });
}

/* ---------- açılış ---------- */
document.addEventListener("DOMContentLoaded", () => {
  swKur();
  temaKur();
  resimHatalariniGizle();
  kohortGuncelle();
  kendiniKontrolEt();
});
