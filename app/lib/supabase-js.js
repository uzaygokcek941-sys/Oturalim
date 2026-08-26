/* ============================================================
   supabase-js — YER TUTUCU, gercek kutuphane DEGIL.

   Bu dosya su an yalniz CDN'e yonlendiriyor. Gercegini almak icin:

       python kutuphane_al.py

   Betik esm.sh'ten paketlenmis (tek dosya) surumu indiriyor, ICINDE dis
   ithalat kalmadigini dogruluyor ve BU DOSYANIN uzerine yaziyor. Ondan
   sonra kutuphane ayni kaynaktan geliyor.

   NEDEN ONEMLI, iki ayri sebep:

   1) SRI YOK. Leaflet <script integrity=...> ile geliyor; supabase-js
      gelemiyor, cunku dinamik import() integrity DESTEKLEMIYOR. Yani
      bugun esm.sh ne gonderirse dogrulanmadan calisiyor.

   2) CDN TEK ARIZA NOKTASI. Varsayim degil, bu depoda YASANDI: Leaflet
      CDN'den gelmeyince kesfet ekraninin TAMAMI oluyordu. Ayni sey
      supabase-js'e olursa giris, favori, paylasim, yorum ve fotograf --
      hepsi birden kapanir.

   Yer tutucu neden var: kimlik.js TEK bir adres bilsin diye. Yedek
   mantigi, deneme-yanilma, 404 turu yok -- kutuphaneyi degistirmek bu
   dosyanin icerigini degistirmek demek.

   test.py bu dosyanin hala yer tutucu oldugunu SOYLUYOR; sessiz kalmiyor.
   csp_uret.py de bakiyor: yer tutucu oldugu surece esm.sh CSP'de kalmak
   zorunda, gercegi indirilince CSP kendiliginden daraliyor.
   ============================================================ */
export * from "https://esm.sh/@supabase/supabase-js@2.45.4";
