# Faz 1 — Kararlar

## Yönetmen ve film

**Wong Kar-wai — Chungking Express (1994)**

Seçim gerekçesi tesadüf değil: filmin ikinci hikâyesi **Midnight Express** adlı
ayaküstü bir yemek büfesinde geçer. Kalabalık bir şehirde yalnız insanlar,
gece açık bir tezgâh, oraya uğrayıp birbirine değme. Oturalım'ın sorduğu soru
bu — "bu akşam nereye oturayım".

### Araştırma notu (web, doğrulanmış)

| Bulgu | Kaynak | Web karşılığı |
|---|---|---|
| **Step-printing**: 6 kare/sn çekilip her kare dörtlenmiş. Yalnız öndeki özne net kalır, arkası gözün algılayamayacağı hızla akar | colorculture.org, deepfilmanalysis.com | **Odaklanılan kart netleşip durur, diğerleri bulanıklaşıp kayar** |
| Baskın renkler **sarı ve yeşil** — yaygın sanılan turkuaz-amber değil | colorculture.org | Palet sarıya kaydırılıyor, mevcut turuncu vurgu korunuyor |
| Geniş açı + elde kamera + doğal ışıkla neon karışımı | robertcmorton.com | Kenarlarda hafif optik bozulma, mikro-titreme, sıcak nokta ışıklar |
| İki ayrı görüntü yönetmeni (Lau / Doyle), iki hikâye iki dil | araştırma | **İki tempo**: ana sayfa sinematik, keşfet araç gibi hızlı |

**Son kullanma tarihi motifi** (1 Mayıs'ta bozulan ananas konservesi) uygulamada
zaten var: *şu an açık / kapalı*. Zaman baskısı ürünün içinde, uydurmaya gerek yok.

## Uygunluk denetimi

**Önceki iş denetimi:** Bu kullanıcı için bu projede daha önce cinematic-ui
çıktısı yok — karşılaştırılacak önceki kabuk yok. Bunun yerine, bu oturumda
teşhis edilen **mevcut arayüzün kendi kalıpları** yasak listesi sayılıyor.

**Kabuk yasak listesi** (mevcut arayüzden devralınmayacaklar):
- Ortalanmış başlık + altında form kutusu şeklindeki kahraman bölümü
- Eşit boşluklu, tek tip yuvarlatılmış kart ızgarası
- Filtre çipi sırası + altında düz liste
- Her bölümün aynı `fadeUp` ile gelmesi (mevcutta zaten 2 keyframe var, ikisi de bu)
- Yüzey ayrımını yalnız `border` + `border-radius` ile kurmak
- Hareketsizlik: 291 satır CSS, 6 geçiş — bu bir kalıp değil, kalıp yokluğu

**Birincil kompozisyon ailesi: KORİDOR**

Chungking Mansions bir koridor binasıdır; film boyunca insanlar dar geçitlerden,
kapı aralıklarından, tezgâh açıklıklarından görünür. Aynı zamanda bir mekan
listesinin doğal biçimi: sokakta yürürken vitrinlerin önünden geçersin.

Full-bleed sahne, dikey kule, arşiv duvarı ve panoramik levha bilinçli olarak
elenmiştir — hepsi bu üründe ya kullanımı yavaşlatır ya da koridor okumasını bozar.

## Ürün gerçeği — filmden önce gelen kısıt

Bu bir tanıtım sayfası değil, **sokakta kullanılan bir araç**. Keşfet ekranı
36.102 mekanlık liste + harita taşıyor. Sinematik dil şuna hizmet etmeli:
kullanıcı 3 saniyede "bu akşam nereye" sorusunun cevabını görmeli.

Bu yüzden **iki tempo** kuruluyor (filmin iki görüntü yönetmeni mantığı):

| Sayfa | Tempo | Gerekçe |
|---|---|---|
| Ana sayfa | Sinematik, yavaş, atmosferik | Karar anı. Kullanıcı henüz aramıyor, ikna oluyor |
| Keşfet | Hızlı, keskin, araç gibi | Kullanım anı. Ağır hareket burada düşmandır |
| Diğer 7 sayfa | Sakin, tipografik | Aynı filmin sessiz sahneleri |

## Görsel karar

Görsel kullanılmıyor. Atmosfer tamamen CSS ile kurulacak: neon sızıntısı,
ıslak asfalt parlaması, grain, hareket izi. Sebep: 36.102 mekan için telifsiz
fotoğraf bulunamaz ve sayfa hızı bu üründe özellik değil zorunluluk.
