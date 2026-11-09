#!/usr/bin/env python3
"""The Night Signals vector sheet: all 8 glyphs as rows; columns = the high-res source, then 23 / 64 / 256 CSS px,
each idle and working, rendered through the real piece (prototype/c6_night.html, the vector engine) at dpr 2.

  python3 tools/build_night_vector.py        # (re)build the glyph table and its high-res sources first
  python3 tools/build_night_vector_sheet.py

Writes <agent storage>/sprites/symbol-resolution-comparison/NIGHT_SIGNALS_VECTOR.png, every raw still in
night_vector/stills/ and every crop placed on the sheet in night_vector/crops/ beside it. Derived, never committed.

Deterministic, as tools/build_symbol_comparison.py: one fresh page per still, one synthetic live message, 300 fixed
simulation steps, a screenshot round the sprite's reported position. The URL size is solved so the glyph extent E is
exactly 23, 64 or 256 CSS px (E = 54 * sqrt(mem / 0.8) * size * STAGE in live mode). Panels are device pixels; the
23 px column is magnified 4x nearest-neighbour and the 64 px column 2x, so no detail is invented or smoothed away.
One browser, sequential renders.
"""
import functools, http.server, math, socketserver, subprocess, sys, threading
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

SPR = Path(__file__).resolve().parents[1]
import sys as _sys; from pathlib import Path as _P; _sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "tests/tools")); import load_rule  # owner rule: renders are load

def storage():
    h = Path.home() / "dev/Lodestar/bin/lib/agent_storage.py"
    return Path(subprocess.check_output([sys.executable, str(h)], text=True).strip())


ROOT = storage() / "sprites"
OUT = ROOT / "symbol-resolution-comparison"; NV = OUT / "night_vector"; STILLS = NV / "stills"; CROPS = NV / "crops"
SRC = ROOT / "night_vector/sources"
for d in (STILLS, CROPS): d.mkdir(parents=True, exist_ok=True)
W, H, DPR, TOPM, BOTM = 2560, 1440, 2, 26, 86
STAGE = 0.5 * min(W / 1280, H / 800)
NAMES = ["Batman", "Bat Signal", "Delta", "Autobot", "TARDIS", "Fuji", "Starbird", "Cog"]
# (key, E css px, mem, state, cpu, rx, tx, magnification)
CASES = [("e23i", 23, 0.33, "idle", 0.03, 0, 0, 4), ("e23w", 23, 0.33, "working", 0.9, 8, 3, 4),
         ("e64i", 64, 0.8, "idle", 0.03, 0, 0, 2), ("e64w", 64, 0.8, "working", 0.9, 8, 3, 2),
         ("e256i", 256, 0.8, "idle", 0.03, 0, 0, 1), ("e256w", 256, 0.8, "working", 0.9, 8, 3, 1)]
LABEL = {"e23i": "23 px idle (4x)", "e23w": "23 px working (4x)", "e64i": "64 px idle (2x)", "e64w": "64 px working (2x)",
         "e256i": "256 px idle (1:1)", "e256w": "256 px working (1:1)"}


def msg(iv, mem, state, cpu, rx, tx):
    return {"cmd": "live", "sessions": [{"id": "s1", "hue": 200, "iv": iv, "ghost": False, "white": False}],
            "S": {"s": {"s1": {"state": state, "cpu": cpu, "mem": mem, "procs": 3, "rx": rx, "tx": tx}},
                  "m": {"level": 0.3, "thermal": 0, "mempress": 0},
                  "net": {"mbps": 11, "vpn": "up", "loss": 0, "strain": 0}, "play": {"pair": ["", ""], "amt": 0}}}


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def font(sz, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()


def main():
    load_rule.require()   # only on on-site network without the VPN; unknown = refuse
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(SPR)))
    srv.daemon_threads = True; threading.Thread(target=srv.serve_forever, daemon=True).start(); port = srv.server_address[1]
    errs, cells = [], {}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for ck, E, mem, state, cpu, rx, tx, mag in CASES:
            size = E / (54 * math.sqrt(mem / 0.8) * STAGE)
            # crop: the glyph plus the satellite orbit (E*0.62 + 9*SZ) plus a dot and a margin
            R = E * 0.62 + 9 * size * STAGE + 6
            for iv, name in enumerate(NAMES):
                pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=DPR)
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto(f"http://127.0.0.1:{port}/prototype/c6_night.html?live=1&w={W}&h={H}&dpr={DPR}&top={TOPM}&bot={BOTM}&size={size:.5f}")
                pg.wait_for_function("typeof window.__live === 'function'", timeout=20000)
                pg.evaluate("document.documentElement.style.background='#0b0d12'")
                r = pg.evaluate("m => window.__live(m, 300)", msg(iv, mem, state, cpu, rx, tx))["reports"]["s1"]
                fn = STILLS / f"{ck}_{name.replace(' ', '_')}.png"
                pg.screenshot(path=str(fn), clip={"x": r["x"] - R, "y": r["y"] - R, "width": 2 * R, "height": 2 * R}); pg.close()
                im = Image.open(fn).convert("RGB"); im = im.resize((im.width * mag, im.height * mag), Image.NEAREST)
                im.save(CROPS / fn.name); cells[(name, ck)] = im
            print(ck, f"E={E} size={size:.3f}", flush=True)
        b.close()
    if errs: print("PAGE ERRORS", errs[:5], file=sys.stderr)
    for name in NAMES:
        s = Image.open(SRC / f"{name.replace(' ', '_')}.png").convert("RGB").resize((360, 360), Image.LANCZOS)
        s.save(CROPS / f"source_{name.replace(' ', '_')}.png"); cells[(name, "src")] = s
    cols = [("src", "high-res source (2048 px)")] + [(c[0], LABEL[c[0]]) for c in CASES]
    cw = {k: max(cells[(n, k)].width for n in NAMES) for k, _ in cols}
    rh = {n: max(cells[(n, k)].height for k, _ in cols) for n in NAMES}
    pad, left, hdr = 18, 150, 120
    Wi = left + sum(cw.values()) + pad * (len(cols) + 1); Hi = hdr + sum(rh.values()) + pad * (len(NAMES) + 1) + 40
    BG, FG, DIM, RULE = (11, 13, 18), (226, 232, 243), (150, 163, 184), (44, 52, 66)
    img = Image.new("RGB", (Wi, Hi), BG); d = ImageDraw.Draw(img)
    d.text((pad, 14), "NIGHT SIGNALS - vector edges (prototype/vector/engine.js), rendered through prototype/c6_night.html at dpr 2", font=font(28, True), fill=FG)
    d.text((pad, 52), "Rows: the 8 glyphs (iv 0..7). Columns: the high-res source each outline was traced from, then glyph extent 23 / 64 / 256 CSS px, "
           "idle and working (CPU 0.9, 8/3 Mbit/s, 3 tasks). Device pixels; 23 px magnified 4x and 64 px 2x, nearest-neighbour.", font=font(17), fill=DIM)
    x = left + pad; xs = {}
    for k, l in cols: xs[k] = x; d.text((x, hdr - 32), l, font=font(18), fill=FG); x += cw[k] + pad
    y = hdr + pad
    for n in NAMES:
        d.text((pad, y + rh[n] // 2 - 12), n, font=font(22, True), fill=FG)
        for k, _ in cols:
            im = cells[(n, k)]; X, Y = xs[k] + (cw[k] - im.width) // 2, y + (rh[n] - im.height) // 2
            d.rectangle([xs[k] - 1, y - 1, xs[k] + cw[k], y + rh[n]], outline=RULE); img.paste(im, (X, Y))
        y += rh[n] + pad
    d.text((pad, Hi - 34), "Rebuild: python3 tools/build_night_vector.py && python3 tools/build_night_vector_sheet.py", font=font(16), fill=DIM)
    out = OUT / "NIGHT_SIGNALS_VECTOR.png"; img.save(out); print("SHEET:", out, img.size)


if __name__ == "__main__":
    main()
