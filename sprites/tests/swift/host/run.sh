#!/bin/sh
# Package C host-safety tests: every app/macos source except App.swift (@main) + host_main.swift, built into the agent
# storage root. Exit 0 = all pass.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
mac=$(cd "$here/../../../app/macos" && pwd)
root=$(python3 "$HOME/dev/Lodestar/bin/lib/agent_storage.py")
out="$root/sprites/build/host_tests"; mkdir -p "$out/tmp"; rm -rf "$out/tmp/run"
srcs=$(sed -n 's/^SOURCES *:= *//p' "$mac/Makefile" | tr ' ' '\n' | grep -v '^App.swift$' | sed "s#^#$mac/#")
nice -n 19 /usr/bin/swiftc -swift-version 5 -target arm64-apple-macos13.0 $srcs "$here/main.swift" -o "$out/sprites_host_tests"
exec "$out/sprites_host_tests" "$mac" "$out/tmp"
