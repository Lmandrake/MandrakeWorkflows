#!/usr/bin/env python3
"""R2_MACOS #9: `Sprites --native-qos-bench S` runs one JSContext per worker thread. Every JS timer of a bench host must fire
on THAT worker thread (never main, which would race the worker on the same JSContext), and the bench must run its timers
at all (stage start-up arms some: > 0 fired). Hand-derived: 4 QoS classes -> 4 result lines, each 'on the host thread N>0,
off it 0'. Runs under tools/gate.py; exit 0 = pass."""
import re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
GATE = Path.home() / "agent-storage/sprites/live/native/tools/gate.py"
exe = subprocess.check_output([str(HERE / "build.sh")], text=True).strip().splitlines()[-1]
p = subprocess.run([sys.executable, str(GATE), exe, "--native-qos-bench", "1"], capture_output=True, text=True)
lines = [l for l in p.stderr.splitlines() if "qos-bench" in l]
got = [tuple(map(int, m.groups())) for l in lines if (m := re.search(r"on the host thread (\d+), off it (\d+)", l))]
ok = p.returncode == 0 and len(got) == 4 and all(on > 0 and off == 0 for on, off in got)
print(f"{'PASS' if ok else 'FAIL'} qos bench timers (on, off) per QoS: {got}, exit {p.returncode}")
sys.exit(0 if ok else 1)
