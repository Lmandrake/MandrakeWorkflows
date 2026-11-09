#!/usr/bin/env python3
"""Round 2 of the symbol-resolution comparison (docs/SYMBOL_RESOLUTION.md): edge-only symbols at high
pixel density, plus the fine-pixel jellyfish.

  python3 tools/trace_symbols.py            # regenerate the traced outlines first, if the trace changed
  python3 tools/build_symbol_comparison.py  [--only bat|jelly|grid]

Writes to <agent storage>/sprites/symbol-resolution-comparison/:
  SYMBOL_RESOLUTION_COMPARISON_v2.png   the one sheet for the owner
  v2/stills/*.png                       every raw screenshot, at DEVICE pixels (dpr 2), uncropped by eye
  v2/crops/*.png                        the exact crops placed on the sheet
Large derived artifacts never go in git; this script is their provenance.

Deterministic: each still is one fresh page, one synthetic live message, a fixed number of simulation
steps, then a screenshot around the sprite's reported position. Panels are shown at DEVICE pixels (the
dpr 2 screenshot, not downsampled), because the owner's screens are 2x and downsampling to CSS px would
add the very softness under test. Size is controlled exactly: the URL `size` is solved so the glyph's
extent E is the target CSS px (23 = the measured idle default; 64; 256 = a large monitor).
"""
import argparse, functools, http.server, json, math, socketserver, subprocess, sys, threading
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

SPR = Path(__file__).resolve().parents[1]
import sys as _sys; from pathlib import Path as _P; _sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "tests/tools")); import load_rule  # owner rule: renders are load

def storage():
    h = Path.home() / "dev/Lodestar/bin/lib/agent_storage.py"
    return Path(subprocess.check_output([sys.executable, str(h)], text=True).strip())


ROOT = storage() / "sprites"
OUT = ROOT / "symbol-resolution-comparison"
V2 = OUT / "v2"; STILLS = V2 / "stills"; CROPS = V2 / "crops"
for d in (STILLS, CROPS): d.mkdir(parents=True, exist_ok=True)
REF = ROOT / "refs/batman_reference.png"

W, H, DPR = 2560, 1440, 2
TOPM, BOTM = 26, 86
STAGE = 0.5 * min(W / 1280, H / 800)          # the runtime's LIVE_BASE x the sigil engine's stage scale

# ---- arms. (key, label, page, extra-query). The engine's E = 54*sqrt(mem/0.8)*size*STAGE. ----
RES = "prototype/experiments/resolution/"
ARMS = [
    ("A", "A  shipped: 9x9, blob 3x pitch", "prototype/c6_night.html", ""),
    ("B33", "B2  edge LED 33x33", RES + "armB_edge.html", "&n=33"),
    ("B49", "B2  edge LED 49x49", RES + "armB_edge.html", "&n=49"),
    ("B65", "B2  edge LED 65x65", RES + "armB_edge.html", "&n=65"),
    ("C2", "C2  vector edges (Choir idiom)", RES + "armC_edge.html", ""),
]
SYMS = [("Batman", 0), ("TARDIS", 4), ("Cog", 7)]
# (case key, target E in CSS px, mem, state, cpu, rx, tx, caption)
CASES = [
    ("e23i", 23, 0.33, "idle", 0.03, 0.0, 0.0, "23 CSS px, idle (the measured default size and memory)"),
    ("e23w", 23, 0.33, "working", 0.9, 8.0, 3.0, "23 CSS px, working, 8/3 Mbit/s"),
    ("e64w", 64, 0.8, "working", 0.9, 8.0, 3.0, "64 CSS px, working, 8/3 Mbit/s"),
    ("e256w", 256, 0.8, "working", 0.9, 8.0, 3.0, "256 CSS px (large monitor), working, 8/3 Mbit/s"),
]
# the jellyfish (prototype/c2_siphon.html, the Siphonophores species), variant iv 0 "Moon"
JELLY_IV = 0
JELLY_FINE = {"rings": 2.2, "dots": 2.2, "beads": 1.8, "size": 0.6, "glow": 0.2, "halo": 0.25, "pulseGlow": 0.35, "pulseGlowR": 2.5}
JELLY_CASES = [("j64", 64, "bell 64 CSS px wide"), ("j128", 128, "bell 128 CSS px"), ("j256", 256, "bell 256 CSS px (large monitor)")]


def msg(iv, mem, state, cpu, rx, tx, procs=5):
    return {"cmd": "live", "sessions": [{"id": "s1", "hue": 200, "iv": iv, "ghost": False, "white": False}],
            "S": {"s": {"s1": {"state": state, "cpu": cpu, "mem": mem, "procs": procs, "rx": rx, "tx": tx}},
                  "m": {"level": 0.3, "thermal": 0, "mempress": 0},
                  "net": {"mbps": 14, "vpn": "up", "loss": 0, "strain": 0}, "play": {"pair": ["", ""], "amt": 0}}}


def font(sz, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def serve():
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(SPR)))
    srv.daemon_threads = True; threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


errors = []


def shoot(b, port, page, query, m, fn, R, init=None, box=None):
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=DPR)
    pg.on("pageerror", lambda e: errors.append(f"{fn.name}: {e}"))
    if init: pg.add_init_script(init)
    pg.goto(f"http://127.0.0.1:{port}/{page}?live=1&w={W}&h={H}&dpr={DPR}&top={TOPM}&bot={BOTM}{query}")
    pg.wait_for_function("typeof window.__live === 'function'", timeout=20000)
    pg.evaluate("document.documentElement.style.background='#0b0d12'")
    rep = pg.evaluate("m => window.__live(m, 300)", m)
    if rep.get("errors"): errors.extend(f"{fn.name}: {e}" for e in rep["errors"])
    r = rep["reports"]["s1"]
    x0, y0, x1, y1 = box(r) if box else (r["x"] - R, r["y"] - R, r["x"] + R, r["y"] + R)
    x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
    pg.screenshot(path=str(fn), clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0})
    pg.close()
    return fn


def run_symbols(b, port):
    shots = {}
    for ck, E, mem, state, cpu, rx, tx, _cap in CASES:
        size = E / (54 * math.sqrt(min(2.6, max(0.2, mem)) / 0.8) * STAGE)
        SZ = size * STAGE
        R = E * 0.62 + 9 * SZ + 3.4 * math.sqrt(SZ) * 2.5 + 6       # glyph + satellite orbit + its glow
        for ak, _l, page, extra in ARMS:
            for sym, iv in SYMS:
                fn = STILLS / f"{ck}_{ak}_{sym}.png"
                shoot(b, port, page, f"&size={size:.5f}{extra}", msg(iv, mem, state, cpu, rx, tx), fn, R)
                shots[(ck, ak, sym)] = fn
        print(f"{ck}: E={E} CSS px, size={size:.3f}, pitch9={E/9:.2f} pitch33={E/33:.2f} pitch65={E/65:.2f} CSS", flush=True)
    return shots


def run_jelly(b, port):
    shots = {}
    # bell radius r = KMEM*sqrt(mem)*P.size with KMEM = 26*SC*1.45, SC = min((H-TOP-BOT)/400*0.95, min(W/1280,H/800))
    SC = min((H - TOPM - BOTM) / 400 * 0.95, min(W / 1280, H / 800)); KMEM = 26 * SC * 1.45; mem = 0.8
    for jk, bell, _cap in JELLY_CASES:
        psize = (bell / 2) / (KMEM * math.sqrt(mem))
        size = psize / 0.5
        r = bell / 2; TLEN = 118 * psize * SC * 0.78
        box = lambda rr, r=r, TLEN=TLEN: (rr["x"] - 1.9 * r - 8, rr["y"] - 1.25 * r - 8, rr["x"] + 1.9 * r + 8, rr["y"] + 0.6 * r + TLEN + 12)
        for kind, tune in (("ship", None), ("fine", JELLY_FINE)):
            init = None if tune is None else f"window.SPRITES_JELLY_TUNE = {json.dumps(tune)};"
            fn = STILLS / f"{jk}_{kind}.png"
            shoot(b, port, "prototype/c2_siphon.html", f"&size={size:.5f}", msg(JELLY_IV, mem, "working", 0.9, 8.0, 3.0), fn, 0, init, box)
            shots[(jk, kind)] = fn
        print(f"{jk}: bell={bell} CSS px, size={size:.3f}", flush=True)
    return shots


# ---------------------------------------------------------------- sheet
BG = (11, 13, 18); FG = (226, 232, 243); DIM = (150, 163, 184); RULE = (44, 52, 66); ACC = (255, 210, 80)


def common_crop(ims, pad=10, thr=34):
    """One crop box for a row, the union of every arm's lit pixels, so the arms stay comparable in size."""
    W0 = min(i.width for i in ims); H0 = min(i.height for i in ims); box = None
    for im in ims:
        a = np.asarray(im.convert("RGB").crop((0, 0, W0, H0))).max(axis=2) > thr
        ys, xs = np.nonzero(a)
        if not len(xs): continue
        bb = [xs.min(), ys.min(), xs.max(), ys.max()]
        box = bb if box is None else [min(box[0], bb[0]), min(box[1], bb[1]), max(box[2], bb[2]), max(box[3], bb[3])]
    if box is None: return (0, 0, W0, H0)
    return (max(0, box[0] - pad), max(0, box[1] - pad), min(W0, box[2] + pad), min(H0, box[3] + pad))


def grid(title, sub, cols, rows, cells, mag=1, note=None):
    """cols: [(key,label)], rows: [(key,label)], cells[(row,col)] -> PIL image (device px). mag = nearest x."""
    f_t, f_h, f_s, f_c = font(26, True), font(17), font(19, True), font(15)
    panels = {k: (v.resize((v.width * mag, v.height * mag), Image.NEAREST) if mag > 1 else v) for k, v in cells.items()}
    d0 = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    cw = max(max(p.width for p in panels.values()), max(int(d0.textlength(l, font=f_h)) for _k, l in cols) + 16)
    ch = max(p.height for p in panels.values())
    pad, left, hdr = 16, 170, 104
    Wi = left + len(cols) * (cw + pad) + pad; Hi = hdr + len(rows) * (ch + pad) + pad + (40 if note else 10)
    img = Image.new("RGB", (Wi, Hi), BG); d = ImageDraw.Draw(img)
    d.text((pad, 12), title, font=f_t, fill=FG); d.text((pad, 46), sub, font=f_c, fill=DIM)
    for i, (_k, l) in enumerate(cols):
        x = left + i * (cw + pad) + pad; d.text((x, hdr - 28), l, font=f_h, fill=FG)
        d.line([(x - pad // 2, hdr - 6), (x + cw + pad // 2, hdr - 6)], fill=RULE)
    for j, (rk, rl) in enumerate(rows):
        y = hdr + j * (ch + pad) + pad; d.text((pad, y + ch // 2 - 10), rl, font=f_s, fill=FG)
        for i, (ck, _l) in enumerate(cols):
            x = left + i * (cw + pad) + pad; d.rectangle([x - 1, y - 1, x + cw, y + ch], outline=RULE)
            p = panels.get((rk, ck))
            if p is not None: img.paste(p, (x + (cw - p.width) // 2, y + (ch - p.height) // 2))
    if note: d.text((pad, Hi - 32), note, font=f_c, fill=DIM)
    return img


def bat_strip(shots, stats):
    """The fidelity check he asked for: the reference beside the trace and the new bats, same height."""
    ref = Image.open(REF).convert("RGB")
    ov = Image.open(V2 / "bat_trace_overlay.png").convert("RGB")
    cells = {}
    hgt = 300
    def fit(im): return im.resize((int(im.width * hgt / im.height), hgt), Image.LANCZOS)
    cells[("r", "ref")] = fit(ref)
    cells[("r", "ov")] = fit(ov)
    for ak in ("B65", "C2"):
        im = Image.open(shots[("e256w", ak, "Batman")]).convert("RGB")
        w, h = im.size; e = 256 * DPR                 # the glyph only: E = 256 CSS px, the ring spans ~0.97 E
        im = im.crop((w // 2 - int(0.56 * e), h // 2 - int(0.36 * e), w // 2 + int(0.56 * e), h // 2 + int(0.36 * e)))
        im.save(CROPS / f"bat_strip_{ak}.png"); cells[("r", ak)] = fit(im) if im.height > hgt else im
    cols = [("ref", "owner's reference"), ("ov", "traced outline (magenta) on it"),
            ("B65", "new B2 bat, 65x65, at 256 px"), ("C2", "new C2 bat, vector edge, at 256 px")]
    return grid("THE BAT, TRACED - reference beside the new outline bats",
                f"Outline traced from the reference (marching squares, mirror-averaged, simplified): IoU {stats['iou_simplified']:.3f} "
                f"against the reference's own yellow mask ({stats['iou_trace']:.3f} before symmetrising). Ring aspect {stats['outer_aspect']}:1.",
                cols, [("r", "Batman")], cells)


def main():
    load_rule.require()   # only on on-site network without the VPN; unknown = refuse
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=None); a = ap.parse_args()
    stats = json.loads((SPR / RES / "symbols_edge.js").read_text().split(" *   ", 1)[1].split("\n", 1)[0])
    port = serve()
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        print("chromium", b.version, flush=True)
        shots = run_symbols(b, port) if a.only in (None, "grid", "bat") else {}
        jshots = run_jelly(b, port) if a.only in (None, "jelly") else {}
        b.close()
    if errors: print("PAGE ERRORS:", errors[:10], file=sys.stderr)
    parts = []
    if shots:
        parts.append(bat_strip(shots, stats))
        for ck, E, *_r, cap in CASES:
            cells = {}
            for sym, _iv in SYMS:
                ims = {ak: Image.open(shots[(ck, ak, sym)]).convert("RGB") for ak, *_x in ARMS}
                bx = common_crop(list(ims.values()))
                for ak, im in ims.items():
                    c = im.crop(bx); c.save(CROPS / f"{ck}_{ak}_{sym}.png"); cells[(sym, ak)] = c
            mag = 4 if E <= 23 else 2 if E <= 64 else 1
            parts.append(grid(f"{cap.upper()}" + (f"  -  magnified {mag}x, nearest-neighbour" if mag > 1 else "  -  device pixels 1:1"),
                              "Arms across, symbols down. Each panel is the dpr-2 screenshot's own pixels (no downsampling, no detail invented). "
                              "Arm A is the shipped renderer; the rest are experiment pages.",
                              [(ak, l) for ak, l, *_x in ARMS], [(s, s) for s, _ in SYMS], cells, mag=mag))
    if jshots:
        for n, (jk, bell, cap) in enumerate(JELLY_CASES):   # one grid per size, so each row is only as tall as itself
            ims = {k: Image.open(jshots[(jk, k)]).convert("RGB") for k in ("ship", "fine")}
            bx = common_crop(list(ims.values()))
            cells = {}
            for k, im in ims.items():
                c = im.crop(bx); c.save(CROPS / f"{jk}_{k}.png"); cells[(jk, k)] = c
            mag = 2 if bell <= 64 else 1
            parts.append(grid(("THE JELLYFISH - Siphonophores (prototype/c2_siphon.html), variant Moon, working  -  " if n == 0 else "THE JELLYFISH  -  ")
                              + cap + (f", magnified {mag}x nearest" if mag > 1 else ", device pixels 1:1"),
                              "Left: as shipped. Right: fine pixels - " + f"{JELLY_FINE['rings']}x bell rings, {JELLY_FINE['dots']}x dots per ring, "
                              f"{JELLY_FINE['beads']}x tentacle beads, every hard dot {JELLY_FINE['size']}x the size, per-dot glows at {JELLY_FINE['glow']}, body halo at {JELLY_FINE['halo']}.",
                              [("ship", "as shipped"), ("fine", "fine pixels, hard edges")], [(jk, f"{bell} px")], cells, mag=mag))
    Wt = max(p.width for p in parts); Ht = sum(p.height for p in parts) + 24 * (len(parts) - 1)
    sheet = Image.new("RGB", (Wt, Ht), BG); y = 0
    for p in parts: sheet.paste(p, (0, y)); y += p.height + 24
    name = "SYMBOL_RESOLUTION_COMPARISON_v2.png" if a.only is None else f"partial_{a.only}.png"
    big = OUT / name if a.only is None else V2 / name
    sheet.save(big); print("COMPARISON:", big, sheet.size)


if __name__ == "__main__":
    main()
