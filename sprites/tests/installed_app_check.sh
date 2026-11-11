#!/bin/sh
# Is the app HE RUNS the app we BUILD? (owner, 2026-11-09: "the settings menu for Aether still doesn't work")
#
# 🔴 THE BUG CLASS NO SOURCE TEST CAN SEE. Every Sprites suite compiles the CURRENT sources and tests those. The
# settings page, by contrast, is loaded live from the repo tree (Settings.swift load() -> Paths.settings), while the
# HOST is whatever binary sits in ~/Applications/Sprites.app. So the page can be three days newer than the host that
# answers it, every source test can pass, and the owner still sees a dead tab. On 2026-11-09 the installed binary was
# from Nov 5 16:37 and held ZERO occurrences of the string "Aether": the Aether tab painted all 28 of its rows and
# saved correctly, and the host had no code to read any of it. Nothing in the repo was broken.
#
# This check compares the INSTALLED ARTIFACT against the SOURCE, which is the only place the mismatch exists:
#   1. ~/Applications/Sprites.app exists at all, with a binary inside;
#   2. its binary is NEWER than every app/macos/*.swift (else it was built before the code it is meant to run);
#   3. a marker from each late-arriving feature is actually present in the installed binary, so a build that silently
#      dropped a source file (the Makefile SOURCES list is hand-maintained) is caught too;
#   4. the running process, if any, is that same bundle by cdhash -- a stale process of a replaced bundle is the
#      same failure wearing a fresh install (and `make install` alone never restarts it).
#
# Exit 0 = the app he runs matches the source. Exit 1 = it does not; the message says which of the four it is.
# Advisory on a machine that has never installed Sprites (that is not a stale app), which is reported and passes.
set -u
here=$(cd "$(dirname "$0")" && pwd)
mac=$(cd "$here/../app/macos" && pwd)
app="$HOME/Applications/Sprites.app"
bin="$app/Contents/MacOS/Sprites"
bad=0

if [ ! -d "$app" ]; then
  echo "installed app check: SKIP (no $app on this machine; nothing to be stale)"
  exit 0
fi
[ -f "$bin" ] || { echo "FAIL: $app has no binary at Contents/MacOS/Sprites"; exit 1; }

# 2. every source older than the binary. `find -newer` compares mtime, which is what `make` itself uses.
newer=$(find "$mac" -maxdepth 1 -name '*.swift' -newer "$bin" | sed "s#^$mac/##" | sort | tr '\n' ' ')
if [ -n "$newer" ]; then
  echo "FAIL: the installed binary is OLDER than its sources: $newer"
  echo "      binary $(date -r "$bin" '+%Y-%m-%d %H:%M'); run: make -C sprites/app/macos install"
  bad=1
fi

# 3. markers: a feature whose source is built but whose symbol is missing from the artifact, which catches a build
#    that silently dropped a file (the Makefile SOURCES list is hand-maintained) even when mtimes look fine.
#
#    🔴 A MENU TITLE IS THE WRONG MARKER, and it fails OPEN -- it is absent from a perfectly good binary. Swift
#    stores a string of up to 15 UTF-8 bytes inline in the instruction stream (small-string form), so "Stir the
#    Aether" (15), "Hide Sprites" (12) and "Demo Mode" (9) appear in NO section `strings` reads; "Sprites
#    Settings…" (19) is absent too, because the literal the compiler emits is the one it needs, not the one you
#    typed. The first draft of this check used those three and failed on the fixed app. Markers below are each
#    MEASURED present in the current binary (2026-11-09) and MEASURED absent from the Nov-5 stale one, which was
#    rebuilt from 9fbdf43 to confirm the check rejects the real broken input rather than a hypothetical one.
#    When adding one, verify both halves; a type name or an env-var key survives, a short UI label does not.
for m in AetherHost AetherSettings AetherSim SPRITES_DEBUG_AETHER SPRITES_DEBUG_SETTINGS; do
  if ! strings -a "$bin" | grep -qF -- "$m"; then
    echo "FAIL: the installed binary has no \"$m\" (built without the sources that carry it?)"
    bad=1
  fi
done

# 4. the live process is this bundle. `codesign -d +<pid>` reads the RUNNING image, not the file on disk.
#    🔴 --verbose=4 IS LOAD-BEARING: at --verbose=2 codesign prints Identifier, Format and Authority but NO CDHash
#    line, so `sed -n 's/^CDHash=//p'` yields the empty string for both sides, the `-n` test below is false, and this
#    arm silently never fires. The first draft did exactly that and reported "ok" on a pid it had not compared
#    (measured 2026-11-09). If both hashes ever come back empty, say so rather than pass.
pid=$(pgrep -x Sprites 2>/dev/null | head -1)
if [ -n "$pid" ]; then
  want=$(codesign -d --verbose=4 "$app" 2>&1 | sed -n 's/^CDHash=//p' | head -1)
  have=$(codesign -d --verbose=4 "+$pid" 2>&1 | sed -n 's/^CDHash=//p' | head -1)
  if [ -z "$want" ] || [ -z "$have" ]; then
    echo "FAIL: cannot read a CDHash for the bundle and/or pid $pid, so the running image was NOT compared"
    echo "      (codesign output shape changed? this check needs --verbose=4)"
    bad=1
  elif [ "$want" != "$have" ]; then
    echo "FAIL: the RUNNING Sprites (pid $pid) is not the installed bundle (cdhash $have vs $want)"
    echo "      run: launchctl kickstart -k gui/\$(id -u)/com.mandrake.sprites   (twice: the first after a replace"
    echo "      dies with Code Signature Invalid / -9 OS_REASON_CODESIGNING)"
    bad=1
  fi
fi

[ $bad = 0 ] && echo "installed app check: ok (binary $(date -r "$bin" '+%Y-%m-%d %H:%M')${pid:+, running pid $pid})" || exit 1
