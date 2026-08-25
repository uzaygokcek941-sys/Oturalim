# -*- coding: utf-8 -*-
"""Gelistirme sunucusu — app/ klasorunu onbelleksiz servis eder.

python -m http.server tarayiciya Last-Modified gonderiyor, tarayici da
degisen .js/.css dosyalarini bellek onbelleginden veriyordu: kod
guncelleniyor ama sayfa eski surumu calistiriyordu. Burada her yanita
no-store ekleniyor, boylece her yenileme dosyanin son halini aliyor.

Onbellek disinda YAYINDAKI GUVENLIK BASLIKLARI da gonderiliyor ve
degerler vercel.json'dan OKUNUYOR, burada tekrar yazilmiyor.

NEDEN: Content-Security-Policy satir ici scriptleri karma ile geciriyor.
Yanlis bir karma ancak TARAYICIDA gorunuyor -- sayfa acilir, tek bir blok
sessizce calismaz. Yerel sunucu basligi gondermeseydi, CSP hicbir yerde
sinanmamis olurdu ve ilk kanit yayindaki kirik sayfa olurdu.
Baslik burada gonderildigi icin test_sayfa.py'nin butun kontrolleri
GERCEK CSP ALTINDA kosuyor.

    python sunucu.py            -> 8123
    python sunucu.py 9000       -> 9000
"""
import io
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

KOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
AYAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vercel.json")


def guvenlik_basliklari():
    """vercel.json'daki '/(.*)' grubunun basliklari. Onbellek basliklari
    ALINMIYOR: bu sunucunun butun varlik sebebi onbellegi kapatmak."""
    try:
        d = json.loads(io.open(AYAR, encoding="utf-8").read())
    except Exception:
        return []                       # dosya yoksa/bozuksa sunucu yine kalksin
    for grup in d.get("headers", []):
        if grup.get("source") == "/(.*)":
            return [(h["key"], h["value"]) for h in grup.get("headers", [])
                    if h.get("key") and h.get("key").lower() != "cache-control"]
    return []


BASLIKLAR = guvenlik_basliklari()


class OnbelleksizIsleyici(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=KOK, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        for ad, deger in BASLIKLAR:
            self.send_header(ad, deger)
        super().end_headers()

    def log_message(self, bicim, *args):
        # 404/500 gorunsun, basarili istekler gurultu yapmasin
        if len(args) > 1 and str(args[1]).startswith(("4", "5")):
            super().log_message(bicim, *args)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    if not os.path.isdir(KOK):
        sys.exit("app/ klasoru bulunamadi: " + KOK)
    with ThreadingHTTPServer(("127.0.0.1", port), OnbelleksizIsleyici) as s:
        print("Oturalim -> http://localhost:%d  (onbellek kapali)" % port)
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            print("\ndurduruldu")


if __name__ == "__main__":
    main()
