#!/usr/bin/env python3
"""Native gradients interpolate as WebKit (the approved engine) does: a RADIAL gradient with evenly spaced offsets
(0,1; 0,.5,1; ...) between PREMULTIPLIED stops, any other radial and every linear gradient between straight stops.
Truth is hand-derived from the stops; WebKit's getImageData, measured 2026-11-01, agrees: blue(1) -> red(0), t ~ 0.5:
radial 0,1 reads (0,0,255,127); radial 0,.001,1 reads straight; linear 0,1 reads (129,0,126,127).
Renders through `Sprites --native-frames` (raw scene) under tools/gate.py. Exit 0 = pass."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent
GATE = Path.home() / "agent-storage/sprites/live/native/tools/gate.py"
exe = subprocess.check_output([str(HERE / "build.sh")], text=True).strip().splitlines()[-1]
out = Path(tempfile.mkdtemp(prefix="gradtest_", dir=Path.home() / "agent-storage/sprites/scratch" if (Path.home() / "agent-storage/sprites/scratch").is_dir() else None))
# 200 CSS px wide at dpr 1; the radial centred at x=0, r=200; the linear from x=0 to x=200. Pixel 100's centre is t=0.5025.
R, L = "const g = x.createRadialGradient(0, 0, 0, 0, 0, 200);", "const g = x.createLinearGradient(0, 0, 200, 0);"
S2 = " g.addColorStop(0, 'rgba(0,0,255,1)'); g.addColorStop(1, 'rgba(255,0,0,0)');"
S3 = " g.addColorStop(0, 'rgba(0,0,255,1)'); g.addColorStop(0.0001, 'rgba(0,0,255,1)'); g.addColorStop(1, 'rgba(255,0,0,0)');"
RAW = {"radial": R + S2, "radial_uneven": R + S3, "linear": L + S2}
scenes = [{"name": k, "out": str(out), "raw": v + " x.fillStyle = g; x.fillRect(0, 0, 200, 20);"} for k, v in RAW.items()]
spec = out / "spec.json"; spec.write_text(json.dumps({"w": 200, "h": 20, "dpr": 1, "query": "stale=0&dpr=1", "scenes": scenes}))
subprocess.check_call([sys.executable, str(GATE), exe, "--native-frames", str(spec)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
t = 100.5 / 200
def straight(pm):   # premultiplied 0..255 -> straight RGBA, 8-bit, as savePNG writes it
    a = round(pm[3]); return tuple([round(min(255, c * 255 / a)) if a else 0 for c in pm[:3]] + [a])
lerp = lambda t: (round(255 * t), 0, round(255 * (1 - t)), round(255 * (1 - t)))       # straight lerp
want = {"radial": straight([0, 0, 255 * (1 - t), 255 * (1 - t)]),                         # premultiplied lerp
        "radial_uneven": lerp((t - 0.0001) / 0.9999), "linear": lerp(t)}
fails = 0
for k in RAW:
    px = Image.open(out / f"{k}_native.png").convert("RGBA").getpixel((100, 10))
    ok = all(abs(a - b) <= 2 for a, b in zip(px, want[k])); fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} {k}: got {px}, want {want[k]} (+-2)")
sys.exit(1 if fails else 0)
