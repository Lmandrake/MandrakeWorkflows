#!/usr/bin/env python3
"""R2_MACOS #8 (native energy, host half): a live present() must never block the main thread waiting for a drawable or a
GPU slot. Probe: `--native-frames` scene {presentProbe: 30} presents 30 changed frames from a view in no window, so the
drawable pool runs dry as it does when the displays sleep. Hand-derived bar: one frame at 24 fps is 41.7 ms; a present
that waits for a drawable blocks up to 1 s (nextDrawable timeout) or 100 ms (the in-flight wait); measured before the fix
here: 8-9 ms EVERY present (nextDrawable pacing). Main should only copy the instances (< 100 KB) and hand off: pass = the
worst present() on main < 3 ms, AND the last recorded frame still reaches the layer (presentedVer == the final version:
a frame skipped while the render queue is busy is re-presented when it frees). Renders under tools/gate.py. Exit 0 = pass."""
import json, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
GATE = Path.home() / "agent-storage/sprites/live/native/tools/gate.py"
exe = subprocess.check_output([str(HERE / "build.sh")], text=True).strip().splitlines()[-1]
out = Path(tempfile.mkdtemp(prefix="stall_", dir=Path.home() / "agent-storage/sprites/scratch"))
spec = out / "spec.json"
spec.write_text(json.dumps({"w": 400, "h": 300, "dpr": 2, "query": "stale=0", "scenes": [{"name": "probe", "out": str(out), "settle": 0.3, "presentProbe": 30},
    {"name": "sleep", "out": str(out), "settle": 0.5, "sleepProbe": 1, "setup": "SpritesStage.setDemo(true);"}]}))
rc = subprocess.call([sys.executable, str(GATE), exe, "--native-frames", str(spec)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
rep = json.loads((out / "probe_native.json").read_text()) if (out / "probe_native.json").exists() else {}
worst = rep.get("presentMaxMs")
last = rep.get("presentedVer") == rep.get("finalVer") and rep.get("finalVer") is not None
ok = rc == 0 and worst is not None and worst < 3 and last
print(f"{'PASS' if ok else 'FAIL'} worst present() on main {worst} ms (bar < 3), last frame shown {last} "
      f"({rep.get('presentedVer')} vs {rep.get('finalVer')}), exit {rc}")
# displays asleep (screensDidSleep, posted in-process): document.hidden false -> true -> false on wake, and NO frames
# recorded while asleep (the stage's page-hidden pause; demo mode keeps creatures on screen, so awake it draws 24/s)
sl = json.loads((out / "sleep_native.json").read_text()) if (out / "sleep_native.json").exists() else {}
ok2 = sl.get("sleep") == [False, True, False] and sl.get("framesWhileAsleep") == 0
print(f"{'PASS' if ok2 else 'FAIL'} display sleep hides the page {sl.get('sleep')}, frames while asleep {sl.get('framesWhileAsleep')}")
sys.exit(0 if ok and ok2 else 1)
