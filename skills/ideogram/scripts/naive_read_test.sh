#!/bin/zsh
# Cold-read test: paste an ideogram into a context-free Claude, ask "what are you?", then 3 busy-colleague follow-ups.
# --bare = no CLAUDE.md, no skills, no hooks, no memory; --tools "" = it can only read what was pasted.
# usage: naive_test.sh <ideogram.md> <transcript_out.md>
set -e
doc=${1:A}; out=${2:A}
tmp=$(mktemp -d); cd $tmp
# --bare skips normal auth, so pass an apiKeyHelper: $IDEOGRAM_API_KEY_HELPER, else the one in
# ~/.claude/settings.json; with neither, claude falls back to ANTHROPIC_API_KEY.
helper=${IDEOGRAM_API_KEY_HELPER:-$(python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.claude/settings.json"))).get("apiKeyHelper",""))' 2>/dev/null)}
C=(command claude -p --bare --tools "" --model sonnet --output-format json)
[[ -n $helper ]] && C+=(--settings "{\"apiKeyHelper\":\"$helper\"}")
# AS_OF=YYYY-MM-DD reads the document on the day it was received, not today (the only priming allowed).
[[ -n $AS_OF ]] && C+=(--append-system-prompt "Today's date is $AS_OF.")
qs=("what are you?"
    "what do you need from me, and by when?"
    "what's already decided, and what's still open?"
    "what's this for? where does it sit in what's happening?")
print "# Naive cold-read transcript: ${doc:t}\n\nRun $(date '+%Y-%m-%d %H:%M %Z'); claude -p --bare (no CLAUDE.md, skills, memory or tools), sonnet, empty dir; as-of date: ${AS_OF:-real today}.\nTurn 1 pastes the whole document, then the question.\n" > $out
sid=""
for q in $qs; do
  if [[ -z $sid ]]; then r=$({ cat $doc; print "\n\n---\n\n$q"; } | $C)
  else r=$(print -r -- "$q" | $C --resume $sid); fi
  sid=$(print -r -- $r | python3 -c 'import sys,json;print(json.load(sys.stdin)["session_id"])')
  ans=$(print -r -- $r | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"])')
  print -r -- "## USER: $q"$'\n\n'"## CLAUDE:"$'\n\n'"$ans"$'\n\n---\n' >> $out
done
rm -rf $tmp
