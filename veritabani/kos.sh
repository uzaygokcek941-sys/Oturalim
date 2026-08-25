#!/bin/sh
# SQL davranis kontrollerini gercek Postgres'te kosturur.
#
# NEDEN VAR: sahiplenme_test.sql yazildigi gun elle calistirildi, sonra bir
# daha calismadi. Bu arada supabase_taklit.sql'de eksik bir grant yuzunden
# dosya 6. adimda patliyordu -- yani 11 kontrolun ALTISI aylarca hic
# kosmadi ve kimse gormedi. Bir kontrolu elle calistirmak, olmamasiyla
# ayni sey.
#
#     sh veritabani/kos.sh                # kendi Postgres'ini kurar
#     PGURL=postgres://... sh veritabani/kos.sh   # hazir sunucuya
set -e
KOK=$(cd "$(dirname "$0")/.." && pwd)
DOSYALAR="supabase_taklit sema sayac katki sahiplenme profil yorum menu_katki mekan_foto akran sahiplenme_test sayac_test yorum_test menu_katki_test mekan_foto_test akran_test"

if [ -n "$PGURL" ]; then
  for f in $DOSYALAR; do
    psql "$PGURL" -q -v ON_ERROR_STOP=1 -f "$KOK/veritabani/$f.sql"
  done
  exit 0
fi

BIN=$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)
[ -n "$BIN" ] || { echo "ATLANDI: postgres yok"; exit 0; }
command -v psql >/dev/null || { echo "ATLANDI: psql yok"; exit 0; }

DIZIN=${PGTMP:-/tmp/cebimde-pg}
PORT=${PGPORT_TEST:-5433}
rm -rf "$DIZIN"; mkdir -p "$DIZIN"
# initdb root olarak kosmuyor; root isek postgres kullanicisina devrediyoruz.
if [ "$(id -u)" = "0" ] && id postgres >/dev/null 2>&1; then
  chown postgres:postgres "$DIZIN"
  KOS="su postgres -c"
else
  KOS="sh -c"
fi
$KOS "$BIN/initdb -D $DIZIN/veri -U postgres" >"$DIZIN/kur.log" 2>&1 \
  || { echo "ATLANDI: initdb calismadi"; tail -3 "$DIZIN/kur.log"; exit 0; }
$KOS "$BIN/pg_ctl -D $DIZIN/veri -o '-k $DIZIN -p $PORT' -l $DIZIN/pg.log start" \
  >>"$DIZIN/kur.log" 2>&1 \
  || { echo "ATLANDI: sunucu baslamadi"; tail -5 "$DIZIN/pg.log" 2>/dev/null; exit 0; }
trap '$KOS "$BIN/pg_ctl -D $DIZIN/veri stop" >/dev/null 2>&1 || true' EXIT

# Soket DIZIN'in icinde: /tmp'de baska bir Postgres ayni portta duruyorsa
# ona baglanip yanlis veritabanini sinamayalim.
i=0
while [ $i -lt 60 ]; do
  psql -h "$DIZIN" -p "$PORT" -U postgres -c "select 1" >/dev/null 2>&1 && break
  i=$((i+1)); sleep 0.25
done
[ $i -lt 60 ] || { echo "ATLANDI: sunucuya baglanilamadi"; exit 0; }

for f in $DOSYALAR; do
  psql -h "$DIZIN" -p "$PORT" -U postgres -q -v ON_ERROR_STOP=1 -f "$KOK/veritabani/$f.sql"
done
