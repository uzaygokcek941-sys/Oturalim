/* ============================================================
   Oturalım — tüm sayfaların paylaştığı davranış
   Tema, açılış saati mantığı, biçimlendirme, kohort ölçümü.
   Bağımlılık yok. Her sayfa <script src="ortak.js" defer> ile alır.
   ============================================================ */

/* ---------- tema ----------
   Seçim <head> içindeki küçük satır içi betikle uygulanıyor (FOUC olmasın).
   Buradaki iş yalnızca düğmeye davranış vermek. */
const TEMA_ANAHTAR = "oturalim.tema";

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
  if (meta) meta.content = koyuMu ? "#15110e" : "#fbf7f0";
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
function webBagi(u){
  const ham = String(u == null ? "" : u).trim();
  if (!ham) return "";
  const tam = /^https?:\/\//i.test(ham) ? ham : "https://" + ham;
  return '<a href="' + kacir(tam) + '" target="_blank" rel="noopener nofollow">' +
         kacir(ham.replace(/^https?:\/\//i, "").replace(/\/$/, "")) + "</a>";
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

/* ---------- kohort ölçümü ----------
   Çerezsiz ve sunucusuz: yalnız localStorage, yalnız bu cihaz.
   Hangi günlerde açıldığı tutuluyor; D1/D7/D30 buradan hesaplanıyor. */
const KOHORT = "oturalim.kohort";
const BIRGUN = 86400000;
const bugunISO = () => new Date().toISOString().slice(0,10);
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
    /* Sema eklemek javascript: adresini de etkisizlestiriyor. */
    ["web javascript adresi etkisiz",
      webBagi("javascript:alert(1)").includes('href="https://javascript'),   true],
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
    ["katki web tam bag",   katkiSorunu("web", "instagram.com/oturalim"), null],
    ["katki web https",     katkiSorunu("web", "https://a.com/b"),       null],
    ["katki web handle elenir", typeof katkiSorunu("web", "@oturalim"),  "string"],
    ["katki bos elenir",    typeof katkiSorunu("adres", "  "),           "string"],
    ["katki bilinmeyen alan elenir",
      typeof katkiSorunu("menu", "100"),                                 "string"]
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

/* ---------- açılış ---------- */
document.addEventListener("DOMContentLoaded", () => {
  temaKur();
  kohortGuncelle();
  kendiniKontrolEt();
});
