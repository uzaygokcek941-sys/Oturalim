# Faz 3 — Derlenmiş spec

## External Library Decision

### Q1: Bu sayfanın çekirdek hareket deneyimi nedir?
Parçacık/iz alanı — step-printing'in web karşılığı: yatay akan ışık izleri,
hız yükseldikçe bulanıklaşan, düştükçe netleşen.

### Q2: Yerel kütüphane girdileri bunu yapabilir mi?
Evet. `camera-shots-50 #6` (rack focus) ve `#31` (tilt-shift bulanıklık) CSS
tarafını veriyor; iz alanı ise 60 satırlık canvas + `requestAnimationFrame`
ile çözülüyor. GSAP/Three/Lenis hiçbiri gerekmiyor ve hepsi projenin build'siz
yapısını bozar.

### Q3: Dış kütüphane kullanılacaksa neden?
Kullanılmıyor.

### Karar
**Dış kütüphane yok, yalnız yerel efektler.** Kullanıcının açık isteği
"elle kodlanmış gibi olsun"; CDN'den 90 KB animasyon kütüphanesi çekmek
bunun tam tersi.

## Tokenlar — mevcut sisteme eklenenler

```css
:root{
  --neon-sari:#ffd24a;   --neon-sari-los:rgba(255,210,74,.14);
  --neon-yesil:#4ad9a0;  --neon-yesil-los:rgba(74,217,160,.12);
  --asfalt:#0d0a08;                 /* cerceve disi — sokak */
  --cerceve-kalinlik:clamp(10px,2.2vw,22px);
  --iz-hiz:1;                       /* JS yaziyor: 1 = hizli/bulanik, 0 = durgun/net */
  --grain:.035;
}
```

## Ana sayfa — bölüm bölüm

### 1. Kahraman — Framed Viewport (`hero-archetypes #18`)

**Yerleşim.** `min-height:100svh`. İçinde iki katman:
- `canvas.sokak` — mutlak, tam kaplar, `z-index:0`
- `.cerceve` — `--cerceve-kalinlik` kadar kalın kenarlı kutu, **sağa kaçık**
  (`margin-left:auto; max-width:min(680px,92vw); margin-right:clamp(16px,6vw,90px)`),
  `z-index:1`

Çerçeve merkezde olmadığı ve izler sol kenardan içeri taştığı için ortalanmış
kart olarak okunmuyor (imza kompozisyonu, storyboard).

**Giriş.** Rack focus (`camera-shots-50 #6`):
`filter:blur(18px); transform:scale(1.06)` → `blur(0) scale(1)`, 1s.

**Ağır etkileşim (sayfa tavanı 1/1).** Canvas iz alanı. İmleç birincil düğmeye
yaklaştıkça `--iz-hiz` 1 → 0.15 iner: izler yavaşlar, kuyrukları kısalır,
kenarları netleşir. *Seçmeye yaklaştığında dünya duruyor.*

**Görsel eleman sayısı (min 3):** ışık izi alanı, çerçeve kasası, ıslak zemin
yansıması, grain katmanı → 4.

### 2. Sayılar şeridi
**Giriş.** Jump cut stagger (`#20`) — her sayı 60 ms arayla sıçrayarak.
**Etkileşim.** none (bilinçli).

### 3. Tür kartları
**Giriş.** Curtain wipe (`#10`) — `clip-path:inset(0 100% 0 0)` → `inset(0)`.
**Etkileşim.** Hover'da o kart netleşir, **kardeşleri `blur(2px)` olur**
(`#31` tilt-shift akrabası) — step-printing'in kart ölçeğinde tekrarı.

### 4. Vitrin mekanlar
**Giriş.** Crossfade overlap (`#21`, **Wong Kar-wai**) — 1.5 s, gecikmeli.
**Etkileşim.** Kart hover'ında neon halo (`--neon-sari-los`) alttan sızar.

### 5. Kapanış
**Giriş.** Iris-in (`#1`) — `clip-path:circle(0%)` → `circle(75%)`, 1.5 s.
**Etkileşim.** none.

**Giriş çeşitliliği:** 5 bölüm, 5 farklı giriş, `fadeUp` 0 kez. Komşu bölümler
farklı. Kural karşılandı.

## Keşfet — koridor

**İmza kompozisyonu.** Tek sütun kart akışı + sol kenarda dikey mesafe cetveli.
Kart hover/focus → o kart net + hafif öne, komşuları `blur(1.5px)` +
`opacity:.72` (`#31`). Ağır etkileşim bütçesi **0** — burası araç.

**Giriş.** Yalnız stagger (`#20`), kısa (40 ms). Liste yeniden çizildiğinde
tekrar oynamaz — sadece ilk yüklemede.

## Erişilebilirlik ve performans

- `prefers-reduced-motion:reduce` → canvas hiç başlamaz, tek kare statik çizilir,
  tüm blur girişleri kapanır, geçiş süreleri 0.01 ms.
- Canvas `IntersectionObserver` ile kahraman görünmezken durur.
- `visibilitychange` ile sekme arkaya alınınca durur.
- Canvas `aria-hidden="true"`, klavye odağı almaz.
- Blur yalnız `filter` üzerinden, layout tetiklemiyor.
- Kontrast: neon renkler yalnız dekoratif katmanda; metin `--metin` tokeninde kalıyor.
