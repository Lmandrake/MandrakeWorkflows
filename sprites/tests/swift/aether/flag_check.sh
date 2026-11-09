#!/bin/sh
# Acceptance for MANDRAKEWORKFLOWS_TRY_AETHER_LOOPS_WITHOUT_ACCESS_CHECKS: the release build and the Aether test build
# compile with -enforce-exclusivity=unchecked (never -Ounchecked), and the seeded goldens are bit-identical with it.
set -u
here=$(cd "$(dirname "$0")" && pwd)
mac=$(cd "$here/../../../app/macos" && pwd)
bad=0
for f in "$mac/Makefile" "$here/run.sh"; do
  grep -q -- '-enforce-exclusivity=unchecked' "$f" || { echo "FAIL: $f lacks -enforce-exclusivity=unchecked"; bad=1; }
  grep -q -- '-Ounchecked' "$f" && { echo "FAIL: $f uses -Ounchecked"; bad=1; }
done
grep -q 'risk\|RISK\|hides' "$mac/Makefile" || { echo "FAIL: Makefile has no comment naming the risk (the flag hides real exclusivity bugs)"; bad=1; }
root=$(python3 "$HOME/dev/Lodestar/bin/lib/agent_storage.py"); out="$root/sprites/build/flagcheck_$$"; mkdir -p "$out"
nice -n 19 /usr/bin/swiftc -O -enforce-exclusivity=unchecked -swift-version 5 -target arm64-apple-macos13.0 "$mac/Decide.swift" $(ls "$mac"/Aether*.swift | grep -v AetherHost.swift) "$here/main.swift" "$here/new_tests.swift" -o "$out/t" 2>&1 | grep error: | head -5
AETHER_NEW_ONLY=1 nice -n 19 "$out/t" > "$out/log" 2>&1 || true
grep -q "^FAIL" "$out/log" && { echo "FAIL: seeded goldens or acceptance differ under the flag"; grep "^FAIL" "$out/log" | head -3; bad=1; }
tail -1 "$out/log"; rm -rf "$out"
[ $bad = 0 ] && echo "flag check: ok" || exit 1
