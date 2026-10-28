#!/bin/sh
# The 60-second tour, on a copy of the shipped example. Needs only python3 (stdlib).
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
PLACARD="$HERE/../placard.py"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp -R "$HERE/quarterly-review" "$WORK/"
cd "$WORK"

echo "== 1. What is here, and is every digest current?"
python3 "$PLACARD" --root quarterly-review scan
python3 "$PLACARD" --root quarterly-review verify --deep

echo; echo "== 2. Read one digest the way an agent should (state first, then the body)"
python3 "$PLACARD" --root quarterly-review read quarterly-review/review-deck.pptx | sed -n '1,3p'
python3 "$PLACARD" --root quarterly-review read quarterly-review/review-deck.pptx | grep -m1 "Tallis"

echo; echo "== 3. Change an original: the digest goes stale, and verify says so (exit 1)"
printf ' ' >> quarterly-review/sensor-log.xlsx
rc=0; out="$(python3 "$PLACARD" --root quarterly-review verify)" || rc=$?
printf '%s\n' "$out"
if [ "$rc" -ne 1 ] || ! printf '%s\n' "$out" | grep -q '^STALE  *sensor-log.xlsx'; then
  echo "FAIL: expected verify to exit 1 naming sensor-log.xlsx STALE (rc=$rc)" >&2; exit 1
fi
state="$(python3 "$PLACARD" --root quarterly-review read quarterly-review/sensor-log.xlsx | sed -n '1p')" || true
printf '%s\n' "$state"
case "$state" in "state: source-stale"*) ;; *) echo "FAIL: expected source-stale" >&2; exit 1;; esac

echo; echo "quickstart: ok"
