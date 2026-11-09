#!/bin/sh
# Acceptance for MANDRAKEWORKFLOWS_SPLIT_AETHER_FILE_AROUND_ONE_SETTINGS_TABLE (the file split): every Aether*.swift under
# app/macos is at most 600 lines, there are at least 4 simulation files besides AetherHost.swift, and the Makefile builds them all.
set -u
here=$(cd "$(dirname "$0")" && pwd)
mac=$(cd "$here/../../../app/macos" && pwd)
bad=0; n=0
for f in "$mac"/Aether*.swift; do
  l=$(wc -l < "$f"); b=$(basename "$f")
  [ "$b" != AetherHost.swift ] && n=$((n+1))
  [ "$l" -le 600 ] || { echo "FAIL: $b has $l lines (max 600)"; bad=1; }
  grep -q "$b" "$mac/Makefile" || { echo "FAIL: $b is not in the Makefile SOURCES"; bad=1; }
done
[ "$n" -ge 4 ] || { echo "FAIL: only $n simulation files (need at least 4)"; bad=1; }
[ $bad = 0 ] && echo "split check: ok ($n files)" || exit 1
