#!/bin/sh
# Build the Swift logic tests into the agent storage root (never the repo) and run them. Exit 0 = all pass.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
mac="$here/../../app/macos"
root=$(python3 "$HOME/dev/Lodestar/bin/lib/agent_storage.py")
out="$root/sprites/build/swift_tests"
mkdir -p "$out/tmp"
/usr/bin/swiftc -swift-version 5 -target arm64-apple-macos13.0 "$mac/Decide.swift" "$here/main.swift" -o "$out/sprites_logic_tests"
exec "$out/sprites_logic_tests" "$out/tmp"
