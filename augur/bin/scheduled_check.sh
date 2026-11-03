#!/bin/bash
# Run the pilot-1 checks unattended (LaunchAgent com.mandrake.augur.check24h) and file the result.
#   bin/scheduled_check.sh [HOURS]   default 24
# Writes $AUGUR_HOME/checks/pilot1-<stamp>.txt and appends one line to checks/index.jsonl.
# One-shot: once a 24 h run has passed or failed (not pending), it writes checks/pilot1-24h.done
# and later runs exit at once; pending (not enough data yet) leaves it armed for the next day.
set -u
H="${1:-24}"
: "${AUGUR_HOME:?AUGUR_HOME must be set (the plist sets it)}"
D="$AUGUR_HOME/checks"; mkdir -p -m 700 "$D"
[ -e "$D/pilot1-${H}h.done" ] && exit 0
HERE="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"   # UTC: the DST fall-back hour never repeats a name (RB-n14)
OUT="$D/pilot1-$STAMP.txt"
{
  echo "# Augur pilot-1 checks, ${H} h window, run $(date '+%Y-%m-%d %H:%M %Z') on $(hostname -s)"
  /usr/bin/python3 "$HERE/pilot1_check.py" all --since-hours "$H"; echo "exit_all=$?"
} > "$OUT" 2>&1
CODE=$(sed -n 's/^exit_all=//p' "$OUT")
case "$CODE" in 0) V=pass;; 1) V=fail;; *) V=pending;; esac
printf '{"t":%s,"hours":%s,"verdict":"%s","file":"%s"}\n' "$(date +%s)" "$H" "$V" "$OUT" >> "$D/index.jsonl"
[ "$V" != pending ] && echo "$V $OUT" > "$D/pilot1-${H}h.done"
exit 0
