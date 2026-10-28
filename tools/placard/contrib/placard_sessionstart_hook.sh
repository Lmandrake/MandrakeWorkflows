#!/usr/bin/env bash
# Placard SessionStart hook — tell a starting session that this tree has
# digests, and say NOTHING when it doesn't.
#
# Read-only by construction: it runs `placard announce`, which walks the tree
# and prints. It never writes a sidecar, never opens an original, and never
# fails a session — every path exits 0.
#
# Two design choices worth keeping (see INTEGRATION.md):
#   * It calls `announce`, not `verify`. `verify` hashes every original to
#     detect staleness (slow) and reports how many artifacts are un-digested —
#     at a Drive root that is thousands of files, which reads as a to-do list
#     and pushes a session into digesting work nobody asked for.
#   * Silence is a feature. No output means no digests here, and a session in a
#     source tree should never hear about Placard at all.
#
# Install: see INTEGRATION.md ("Layer 3"). Override the CLI location with
# PLACARD_PY; by default it is the placard.py beside this contrib/ directory.

set -u

PLACARD_PY="${PLACARD_PY:-$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)/placard.py}"
[ -f "$PLACARD_PY" ] || exit 0

# Prefer whatever python3 is on PATH, but fall back to the system one: hooks do
# not always inherit an interactive shell's PATH. placard.py is stdlib-only and
# carries `from __future__ import annotations`, so macOS's 3.9 runs it fine.
PY="$(command -v python3 || true)"
[ -n "$PY" ] || PY=/usr/bin/python3
[ -x "$PY" ] || exit 0

# The event JSON arrives on stdin; `cwd` is the session's directory.
payload="$(cat 2>/dev/null || true)"
dir=""
# jq if present, else the python3 already required above: without a parser the
# payload's cwd was ignored and $PWD announced instead (measured in a container).
if command -v jq >/dev/null 2>&1; then
  dir="$(printf '%s' "$payload" | jq -r '.cwd // empty' 2>/dev/null || true)"
else
  dir="$(printf '%s' "$payload" | "$PY" -c 'import json,sys
try: print(json.load(sys.stdin).get("cwd") or "")
except Exception: pass' 2>/dev/null || true)"
fi
[ -n "$dir" ] && [ -d "$dir" ] || dir="$PWD"

# Home or filesystem root: huge tree, never a project. Stay silent at once.
real="$(cd "$dir" 2>/dev/null && pwd -P || printf '%s' "$dir")"
homereal="$(cd "$HOME" 2>/dev/null && pwd -P || printf '%s' "$HOME")"
if [ "$real" = "/" ] || [ "$real" = "$homereal" ]; then exit 0; fi

out="$("$PY" "$PLACARD_PY" --root "$dir" announce 2>/dev/null || true)"
[ -n "$out" ] || exit 0        # unplacarded tree: stay quiet

# Emit both channels, because they go to different readers:
#   * additionalContext -> the model's context. This is the payload; it is
#     invisible to the user by design.
#   * systemMessage     -> one line on the user's screen. Without it the hook is
#     completely undetectable from the outside, and a nudge you cannot observe
#     is a nudge you cannot trust. Only the count line goes here; the reading
#     protocol is for the model, not the terminal.
# Built with json.dumps so quotes/newlines in the text can't break the envelope.
"$PY" -c 'import json,sys
out = sys.argv[1]
print(json.dumps({
    "systemMessage": out.split("\n", 1)[0],
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": out,
    },
}))' "$out"
exit 0
