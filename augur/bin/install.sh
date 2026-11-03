#!/usr/bin/env bash
# Install (or remove) the com.mandrake.augur LaunchAgent on THIS Mac.
#   augur/bin/install.sh                    render, lint, bootout, bootstrap
#   augur/bin/install.sh --remove           bootout, delete the plist
#   augur/bin/install.sh --render-only PATH render to PATH and lint; launchd untouched
set -euo pipefail
AUG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # .../augur
REPO="$(dirname "$AUG")"
LABEL="${AUGUR_LABEL:-com.mandrake.augur}"   # AUGUR_LABEL=com.mandrake.augur.check24h installs the 24 h checker
SRC="$AUG/launchd/$LABEL.plist"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"
[ -n "${HOME:-}" ] && [ -d "$HOME" ] || { echo "refused: HOME unset or not a directory" >&2; exit 2; }
# DESIGN section 8: refuse on a different $HOME (a sudo shell, another account): the plist's
# paths and the LaunchAgent domain must be the logged-in user's own
REAL_HOME="$(dscl . -read "/Users/$(id -un)" NFSHomeDirectory 2>/dev/null | awk '{print $2}')"
[ -n "$REAL_HOME" ] || REAL_HOME="$(eval echo "~$(id -un)")"
[ "$(cd "$HOME" && pwd -P)" = "$(cd "$REAL_HOME" && pwd -P)" ] || { echo "refused: HOME=$HOME is not $(id -un)'s home ($REAL_HOME)" >&2; exit 2; }
if [ "${1:-}" = "--remove" ]; then
  launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
  rm -f "$DEST"; echo "removed $LABEL"; exit 0
fi
OUT="$DEST"; RENDER_ONLY=0
if [ "${1:-}" = "--render-only" ]; then
  [ -n "${2:-}" ] || { echo "refused: --render-only needs a PATH" >&2; exit 2; }
  OUT="$2"; RENDER_ONLY=1
fi
if [ -z "${AUGUR_HOME:-}" ]; then
  ROOT="$(python3 "$HOME/dev/Lodestar/bin/lib/agent_storage.py")" || { echo "refused: agent_storage.py failed; set AUGUR_HOME or fix the helper" >&2; exit 2; }
  [ -n "$ROOT" ] || { echo "refused: agent_storage.py printed nothing" >&2; exit 2; }
  AUGUR_HOME="$ROOT/augur"
fi
PY="$HOME/ClaudeWork/python/py"
[ -x "$PY" ] || { echo "refused: $PY is not executable" >&2; exit 2; }
esc() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }
sed -e "s|__HOME__|$(esc "$HOME")|g" -e "s|__REPO__|$(esc "$REPO")|g" -e "s|__AUGUR_HOME__|$(esc "$AUGUR_HOME")|g" "$SRC" > "$OUT"
if grep -E '__[A-Z_]+__' "$OUT" >/dev/null; then echo "refused: placeholder survived in $OUT" >&2; exit 2; fi
plutil -lint "$OUT" >/dev/null
if [ "$RENDER_ONLY" = 1 ]; then echo "rendered $OUT"; exit 0; fi
mkdir -p "$AUGUR_HOME" "$HOME/Library/Logs"
launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$DEST"
echo "installed $DEST (AUGUR_HOME=$AUGUR_HOME)"
