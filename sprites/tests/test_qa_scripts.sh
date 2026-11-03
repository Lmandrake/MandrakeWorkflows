#!/bin/sh
# R2_MACOS #3: the QA CPU scripts never disturb the owner's running Sprites. Truth from the review: ab.sh must not
# `pkill -x Sprites` or relaunch a build in his place; both refuse (exit 3, nothing launched) while a Sprites they did
# not start runs. The refusal path is exercised only when a Sprites is running (else SKIP: nothing to protect).
ab=$HOME/ClaudeWork/sprites/live/native/cpu/ab.sh; mine=$HOME/ClaudeWork/sprites/cpu3/mine.sh; f=0
grep -q 'pkill' "$ab" && { echo "FAIL: ab.sh still pkills"; f=1; }
grep -q '^run \${LIVE_TAG' "$ab" && { echo "FAIL: ab.sh relaunches a build at the end"; f=1; }
for s in "$ab" "$mine"; do grep -q 'pgrep -x Sprites' "$s" || { echo "FAIL: $s has no running-Sprites guard"; f=1; }; done
if before=$(pgrep -x Sprites); then
  zsh "$mine" qa_refuse_probe /nonexistent 1 1 >/dev/null 2>&1; [ $? -eq 3 ] || { echo "FAIL: mine.sh did not refuse"; f=1; }
  SPRITES_AB_APP=/nonexistent zsh "$ab" 1 webkit >/dev/null 2>&1; [ $? -eq 3 ] || { echo "FAIL: ab.sh did not refuse"; f=1; }
  [ "$(pgrep -x Sprites)" = "$before" ] || { echo "FAIL: running Sprites changed ($before -> $(pgrep -x Sprites))"; f=1; }
else echo "SKIP: no Sprites running (refusal path not exercised)"; fi
[ $f -eq 0 ] && echo "qa scripts ok"; exit $f
