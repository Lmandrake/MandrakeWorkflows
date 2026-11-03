#!/bin/sh
# Every Sprites test, one at a time. Swift logic tests build into the agent storage root; each browser test runs as the
# machine's one render through gate.py (nice 19, load < 8). Exit 0 = all pass; the summary names each failure.
# Known-open review findings print XFAIL and do not fail the run.
here=$(cd "$(dirname "$0")" && pwd)
gate="$HOME/ClaudeWork/sprites/live/native/tools/gate.py"
[ -f "$gate" ] || { echo "missing $gate (the render gate)"; exit 2; }
fails=""
run() { name=$1; shift; echo "=== $name"; if "$@"; then echo "--- $name ok"; else fails="$fails $name"; echo "--- $name FAILED"; fi; }
run swift sh "$here/swift/run.sh"
run host_safety sh "$here/swift/host/run.sh"
run qa_scripts sh "$here/test_qa_scripts.sh"
run demo_feed python3 "$here/test_demo_feed.py"
run r1_runtime nice -n 19 node "$here/js/test_r1_runtime.js"
run project_map python3 "$here/test_project_map.py"
run project_keys node "$here/node/test_project_keys.js"
run labels python3 "$gate" python3 -m pytest -q "$here/test_labels.py"
run native_gradient python3 "$here/native/test_gradient.py"
run native_label_quad python3 "$here/native/test_label_quad.py"
run native_shim_visibility nice -n 19 node "$here/native/test_shim_visibility.js"
run native_present_stall python3 "$here/native/test_present_stall.py"
run native_qos_bench python3 "$here/native/test_qos_bench.py"
for t in stage link settings_visibility settings_keys idmaps huddle hover_follow move; do
  run "$t" sh -c "cd '$here/stage' && python3 '$gate' python3 test_$t.py"
done
if [ -n "$fails" ]; then echo "FAILED:$fails"; exit 1; fi
echo "ALL TESTS PASS"
