#!/bin/sh
# step_check.sh NEWFILE MAXLINES: NEWFILE exists under app/macos and is listed in the Makefile, Aether.swift has at most
# MAXLINES lines, and everything still compiles with the seeded goldens bit-identical (new.sh). Used per extraction step.
set -u
here=$(cd "$(dirname "$0")" && pwd); mac=$(cd "$here/../../../app/macos" && pwd)
f=$1; max=$2
if [ "$f" != - ]; then
  [ -f "$mac/$f" ] || { echo "FAIL: $f does not exist"; exit 1; }
  grep -q "$f" "$mac/Makefile" || { echo "FAIL: $f is not in the Makefile SOURCES"; exit 1; }
fi
l=$(wc -l < "$mac/Aether.swift"); [ "$l" -le "$max" ] || { echo "FAIL: Aether.swift still has $l lines (need at most $max)"; exit 1; }
sh "$here/new.sh" > /tmp/qwen_step.out 2>&1; rc=$?; grep -E 'error:|FAIL|passed' /tmp/qwen_step.out | head -15; exit $rc
