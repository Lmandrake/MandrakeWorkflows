#!/bin/sh
# Aether simulation tests: app/macos/Aether.swift + Decide.swift (jsonNumber), built into the agent storage root,
# seeded and headless (simulated seconds; no window, no Metal, no benchmark). Exit 0 = all pass.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
mac=$(cd "$here/../../../app/macos" && pwd)
root=$(python3 "$HOME/dev/Lodestar/bin/lib/agent_storage.py")
out="$root/sprites/build/aether_tests"; mkdir -p "$out"
nice -n 19 /usr/bin/swiftc -O -enforce-exclusivity=unchecked -swift-version 5 -target arm64-apple-macos13.0 "$mac/Decide.swift" $(ls "$mac"/Aether*.swift | grep -v AetherHost.swift) "$here/main.swift" "$here/new_tests.swift" -o "$out/aether_tests"
exec nice -n 19 "$out/aether_tests"
