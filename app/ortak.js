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

   NEDEN MAHALLE ADI YOK: veride yok. Ölçüldü — 35.852 mekanın 9.397'sinde
   adres alanı var ama içinde ayrıştırılabilir bir mahalle adı geçen
   YALNIZ 49 tane (%0,14). Mahalle adını dışarıdan bir coğrafi çözücüyle
   uydurmak, bu depoda kapalı olan bir kapı. Bu yüzden "mahalle" yerine
   ÖLÇÜLEBİLİR bir şey kullanılıyor: yarıçap.

   NEDEN 500 m: yürüme mesafesi ve veri buna elveriyor. Ölçüldü (500 m
   yarıçapta komşu sayısı medyanı): Ankara 13, İstanbul 40, İzmir 19,
   Aksaray 4. Hiç komşusu olmayan mekan oranı Ankara %4, İstanbul %1,
   İzmir %8, Aksaray %20 -- yani çoğu sayfada dolu bir cevap çıkıyor.

   NEDEN "ÇEVRESİNE GÖRE PAHALI" DEMİYORUZ: diyemiyoruz. Menü fiyatı
   bilinen mekan 35.852'de 291 (%0,81); 500 m içinde en az 3 fiyatlı
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

function turUyar(secili, tur){
  for (const s of secili){
    if (s.slice(0, 5) === "grup:"){
      const g = TUR_GRUP[s.slice(5)];
      if (g && g.has(tur)) return true;
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
   Çipler mekan sayısına göre seçildi, hevese göre değil (81 il, sayım):
   Restoran 14.587, Kafe 10.815, Fast food 6.091, Bar+Pub 1.443,
   Dondurma 395, geri kalan eğlence türleri toplam 2.521.

   "Tatlı" diye bir çip YOK: verideki tür "Dondurma" ve 395 tane. Çipe
   "Tatlı" deyip dondurmacı listelemek, olmayan bir kapsamı vaat etmek
   olurdu.

   Eğlence tarafı tek tek çip olamayacak kadar parçalı; keşfet ekranının
   zaten kullandığı "grup:eglence" değeri taşınıyor. Gece kulübü O
   GRUBUN İÇİNDE, o yüzden İçki çipinde tekrar edilmiyor -- iki çipte
   birden görünen tür, sayıları iki kez saydırırdı. */
const CANIM = [
  { ad:"Kafe",      tur:["Kafe"] },
  { ad:"Restoran",  tur:["Restoran"] },
  { ad:"Fast food", tur:["Fast food"] },
  { ad:"İçki",      tur:["Bar","Pub"] },
  { ad:"Dondurma",  tur:["Dondurma"] },
  { ad:"Gezilecek", tur:["grup:eglence"] }
];

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
  const BUTCE_LISTE = [
    { id:"ucuz",    tur:"Restoran", kat:{ "Çorba": { n:2, med:120 } } },
    { id:"tuz",     tur:"Restoran", kat:{ "Kebap": { n:2, med:400 } } },
    { id:"hesapli", tur:"Fast food" },
    { id:"ust",     tur:"Restoran", mutfak:"steak_house" },
    { id:"yok",     tur:"Restoran" }
  ];
  const BO = butceOzeti(BUTCE_LISTE, 200);
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

    /* --- ana ekranin kategorileri ---
       Ciplerin turleri veride GERCEKTEN var olmali; yanlis yazilmis tek
       bir tur adi, cipe basan kullaniciya bos liste verir ve bunu
       hicbir sey soylemez. */
    ["kategori sayisi",        CANIM.length,                                   6],
    ["kategori turleri tanimli",
      CANIM.every(k => k.tur.length &&
        k.tur.every(t => t.slice(0,5) === "grup:"
          ? !!TUR_GRUP[t.slice(5)] : TUR_GRUP.yeme.has(t) ||
            TUR_GRUP.eglence.has(t))),                                      true],
    /* Iki cipte birden gorunen tur, ayni mekani iki kez saydirirdi. */
    ["kategoriler ortusmuyor",
      (() => { const g = new Set();
        for (const k of CANIM) for (const t of k.tur){
          const uy = t.slice(0,5) === "grup:" ? [...TUR_GRUP[t.slice(5)]] : [t];
          for (const x of uy){ if (g.has(x)) return false; g.add(x); }
        } return true; })(),                                                true],

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
