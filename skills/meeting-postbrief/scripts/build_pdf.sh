#!/bin/sh
# Render a postbrief markdown to a one-page letter PDF beside it.
# Usage: build_pdf.sh <postbrief.md>   Needs pandoc and Google Chrome. Shrinks until it fits one page.
set -e
MD="$1"; [ -f "$MD" ] || { echo "usage: build_pdf.sh <file.md>" >&2; exit 2; }
HERE="$(cd "$(dirname "$0")/.." && pwd)"; OUT="${MD%.md}.pdf"
TMP="$(mktemp -d)"; CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for z in 1.0 0.95 0.92 0.88 0.84 0.8; do
  { cat "$HERE/assets/postbrief.css"; echo "html { zoom: $z }"; } > "$TMP/s.css"
  pandoc "$MD" -s --embed-resources -c "$TMP/s.css" -o "$TMP/p.html"
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --user-data-dir="$TMP/chrome" \
    --print-to-pdf="$OUT" "$TMP/p.html" >/dev/null 2>&1
  P=$(pdfinfo "$OUT" | awk '/^Pages/{print $2}')
  [ "$P" = 1 ] && { echo "$OUT (1 page, zoom $z)"; rm -rf "$TMP"; exit 0; }
done
echo "$OUT is $P pages even at zoom 0.8: cut content, do not shrink further" >&2; rm -rf "$TMP"; exit 1
