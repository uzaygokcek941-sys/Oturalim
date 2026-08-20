# -*- coding: utf-8 -*-
"""Gelistirme sunucusu — app/ klasorunu onbelleksiz servis eder.

python -m http.server tarayiciya Last-Modified gonderiyor, tarayici da
degisen .js/.css dosyalarini bellek onbelleginden veriyordu: kod
guncelleniyor ama sayfa eski surumu calistiriyordu. Burada her yanita
no-store ekleniyor, boylece her yenileme dosyanin son halini aliyor.

Yayin ortamiyla ilgisi yok; Vercel kendi onbellek basliklarini koyar.

    python sunucu.py            -> 8123
    python sunucu.py 9000       -> 9000
"""
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

KOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")


class OnbelleksizIsleyici(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=KOK, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
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
