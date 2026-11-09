#!/bin/sh
# Fast loop: only the acceptance tests in new_tests.swift (AETHER_NEW_ONLY=1). The full suite is run.sh.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
mac=$(cd "$here/../../../app/macos" && pwd)
root=$(python3 "$HOME/dev/Lodestar/bin/lib/agent_storage.py")
out="$root/sprites/build/aether_tests_new_$$"; mkdir -p "$out"
nice -n 19 /usr/bin/swiftc -O -swift-version 5 -target arm64-apple-macos13.0 "$mac"/Decide.swift $(ls "$mac"/Aether*.swift | grep -v AetherHost.swift) "$here"/main.swift "$here"/new_tests.swift -o "$out/t"
rc=0; AETHER_NEW_ONLY=1 nice -n 19 "$out/t" || rc=$?; rm -rf "$out"; exit $rc
