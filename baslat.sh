#!/bin/sh
# ===================================================================
# Cebimde - macOS / Linux baslatici.
#
#     sh baslat.sh
#
# baslat.bat ile ayni isi yapiyor ve ayni gerekceyle: "python sunucu.py"
# dogru klasorde olmayi ve Python'un PATH'te olmasini gerektiriyor;
# ikisi de yanlis gidebiliyor ve hata mesajlari anlasilmaz.
# ===================================================================
cd "$(dirname "$0")" || exit 1

echo
echo "  Cebimde - yerel calistirma"
echo "  ---------------------------"
echo

[ -f sunucu.py ] || {
  echo "  HATA: sunucu.py bulunamadi. Bu betik deponun KOKUNDE olmali."
  exit 1
}
[ -f app/index.html ] || {
  echo "  HATA: app/index.html yok. Depo eksik indirilmis olabilir."
  exit 1
}

PY=""
command -v python3 >/dev/null 2>&1 && PY=python3
[ -z "$PY" ] && command -v python >/dev/null 2>&1 && PY=python
[ -z "$PY" ] && {
  echo "  HATA: Python bulunamadi."
  echo "  macOS : brew install python   ya da https://www.python.org/downloads/"
  echo "  Linux : sudo apt install python3"
  exit 1
}

echo "  Sunucu baslatiliyor... (kapatmak icin Ctrl+C)"
echo "  Adres: http://localhost:8123"
echo

# Tarayiciyi ac -- yoksa da sunucu yine kalksin, adres yukarida yaziyor.
( sleep 1
  if command -v open >/dev/null 2>&1; then open http://localhost:8123
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open http://localhost:8123
  fi ) >/dev/null 2>&1 &

exec "$PY" sunucu.py --yerel
