#!/usr/bin/env python3
"""H2-wire (docs/NATIVE_PORT_HANDOFF.md item 2): between ctx.__beginLabel() and ctx.__endLabel() the native canvas records
through cmdrec.js, the host rasterizes it with CGCanvas, and Metal draws it as ONE textured quad, source-over, in place.
Hand-derived truth (dpr 2, so CSS px x 2 = device px):
  base: opaque blue rect CSS (0,0)-(100,40), drawn by the instanced path, outside the label.
  label: red rect at CSS (10,10)-(30,20), alpha 1  -> device (25,25) = (255,0,0,255); device (70,25) (CSS 35,12) = blue.
         red rect at CSS (50,10)-(70,20), globalAlpha 0.5 over blue -> premultiplied (127.5,0,127.5,255) -> (128,0,127|128,255).
         white fillText "H" 20px at CSS (120,30): ink (alpha > 0) inside CSS x 120..140, y 14..31, none at CSS (160,30).
  every SpritesLabels style, held, draws ink and reports zero unsupported calls (fillText was unsupported before).
Renders through `Sprites --native-frames` (raw scene) under tools/gate.py. Exit 0 = pass."""
import json, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent
GATE = Path.home() / "ClaudeWork/sprites/live/native/tools/gate.py"
exe = subprocess.check_output([str(HERE / "build.sh")], text=True).strip().splitlines()[-1]
out = Path(tempfile.mkdtemp(prefix="labelquad_", dir=Path.home() / "ClaudeWork/sprites/scratch"))
BASE = "x.fillStyle = 'rgba(0,0,255,1)'; x.fillRect(0, 0, 100, 40);"
LAB = ("x.__beginLabel(); x.fillStyle = 'rgba(255,0,0,1)'; x.fillRect(10, 10, 20, 10); x.globalAlpha = 0.5; x.fillRect(50, 10, 20, 10);"
       "x.globalAlpha = 1; x.fillStyle = '#fff'; x.font = '20px Helvetica'; x.fillText('H', 120, 30); x.__endLabel();")
scenes = [{"name": "quad", "out": str(out), "raw": BASE + LAB}]
for st in ["filament", "orbit", "constellation", "tag", "whisper"]:
    scenes.append({"name": st, "out": str(out), "raw": "x.__beginLabel(); SpritesLabels.draw(x, {style: '%s', name: 'Lodestar', short: 'Lodestar',"
                   " hex: '#FFCA42', x: 100, y: 60, r: 14, scale: 1, t: 1, phase: 'hold', p: 1, ground: 'bright', W: 200, H: 120}); x.__endLabel();" % st})
spec = out / "spec.json"; spec.write_text(json.dumps({"w": 200, "h": 120, "dpr": 2, "query": "stale=0", "scenes": scenes}))
rc = subprocess.call([sys.executable, str(GATE), exe, "--native-frames", str(spec)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = 0
def check(ok, what):
    global fails; fails += not ok; print(("PASS " if ok else "FAIL ") + what)
check(rc == 0, f"render exit {rc}")
def near(px, want, tol=2): return all(abs(a - b) <= tol for a, b in zip(px, want))
try:
    im = Image.open(out / "quad_native.png").convert("RGBA"); g = lambda x, y: im.getpixel((x, y))
    check(near(g(25, 25), (255, 0, 0, 255)), f"opaque label rect at device (25,25): {g(25, 25)}")
    check(near(g(70, 25), (0, 0, 255, 255)), f"base shows between label rects (70,25): {g(70, 25)}")
    check(near(g(125, 25), (128, 0, 127, 255), 2), f"half-alpha label rect over blue (125,25): {g(125, 25)}")
    check(near(g(25, 50), (0, 0, 255, 255)), f"below the label rects is base (25,50): {g(25, 50)}")
    ink = [g(x, y)[3] for x in range(240, 280) for y in range(28, 62)]
    check(max(ink) > 200, f"text ink inside the H box (max alpha {max(ink)})")
    check(g(320, 60)[3] == 0 and g(300, 100)[3] == 0, "nothing outside the label")
    rep = json.loads((out / "quad_native.json").read_text()); check(rep.get("unsupported") in ("{}", ""), f"unsupported {rep.get('unsupported')}")
except FileNotFoundError as e: check(False, f"missing output {e}")
for st in ["filament", "orbit", "constellation", "tag", "whisper"]:
    p = out / f"{st}_native.png"
    if not p.exists(): check(False, f"{st}: no output"); continue
    lit = sum(1 for a in Image.open(p).convert("RGBA").getchannel("A").tobytes() if a > 20)
    rep = json.loads((out / f"{st}_native.json").read_text())
    check(lit > 60 and rep.get("unsupported") in ("{}", ""), f"{st}: {lit} lit px, unsupported {rep.get('unsupported')}")
sys.exit(1 if fails else 0)
