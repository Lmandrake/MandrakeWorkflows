#!/bin/sh
# Build a TEST copy of Sprites.app into the agent storage root (never app/macos/build, which the live app may run from).
# Prints the binary path. Same sources and flags as app/macos/Makefile.
set -eu
here=$(cd "$(dirname "$0")" && pwd); mac="$here/../../app/macos"
root=$(python3 "$HOME/dev/Lodestar/bin/lib/agent_storage.py"); B="$root/sprites/build/native_test"; APP="$B/Sprites.app"
mkdir -p "$APP/Contents/MacOS"
cd "$mac"
/usr/bin/swiftc -O -swift-version 5 -parse-as-library -target arm64-apple-macos13.0 -framework AppKit -framework WebKit -framework Carbon \
  -framework Metal -framework QuartzCore -framework JavaScriptCore $(sed -n 's/^SOURCES *:= *//p' Makefile) -o "$B/Sprites" >&2
cp "$B/Sprites" "$APP/Contents/MacOS/Sprites"; cp Info.plist "$APP/Contents/Info.plist"
plutil -replace SpritesHome -string "$(cd "$here/../.." && pwd)" "$APP/Contents/Info.plist"
codesign --force --sign - --entitlements Sprites.entitlements "$APP" >/dev/null 2>&1 || true
echo "$APP/Contents/MacOS/Sprites"
