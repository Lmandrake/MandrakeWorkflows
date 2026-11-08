#!/usr/bin/env python3
"""Before/after sheet for the jellyfish's bandwidth-pulse glow (tune knob `pulseGlow` in prototype/c2_siphon.html).

  python3 tools/build_siphon_glow.py

Renders the fine-pixel jellyfish (build_symbol_comparison.JELLY_FINE) without and with its pulseGlow, at bell 64
and 256 CSS px, dpr 2, working, at 8/3 Mbit/s and at zero traffic, using the same shooting path as
build_symbol_comparison.py. Writes <agent storage>/sprites/symbol-resolution-comparison/SIPHON_GLOW_BEFORE_AFTER.png,
crops in siphon_glow/, and prints the zero-traffic body diff (must be 0) and the changed-pixel count with traffic.
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_symbol_comparison as bsc  # noqa: E402

GLOW = bsc.OUT / "siphon_glow"; GLOW.mkdir(parents=True, exist_ok=True)
BEFORE = {k: v for k, v in bsc.JELLY_FINE.items() if not k.startswith("pulseGlow")}
AFTER = bsc.JELLY_FINE
CASES = [c for c in bsc.JELLY_CASES if c[1] in (64, 256)]
TRAFFIC = [("net", 8.0, 3.0), ("zero", 0.0, 0.0)]


def shots(b, port):
    import math
    SC = min((bsc.H - bsc.TOPM - bsc.BOTM) / 400 * 0.95, min(bsc.W / 1280, bsc.H / 800)); KMEM = 26 * SC * 1.45; mem = 0.8
    out = {}
    for jk, bell, _cap in CASES:
        psize = (bell / 2) / (KMEM * math.sqrt(mem)); size = psize / 0.5
        r = bell / 2; TLEN = 118 * psize * SC * 0.78
        box = lambda rr, r=r, TLEN=TLEN: (rr["x"] - 1.9 * r - 8, rr["y"] - 1.25 * r - 8, rr["x"] + 1.9 * r + 8, rr["y"] + 0.6 * r + TLEN + 12)
        for tk, rx, tx in TRAFFIC:
            for kind, tune in (("before", BEFORE), ("after", AFTER)):
                fn = GLOW / f"still_{jk}_{tk}_{kind}.png"
                bsc.shoot(b, port, "prototype/c2_siphon.html", f"&size={size:.5f}",
                          bsc.msg(bsc.JELLY_IV, mem, "working", 0.9, rx, tx), fn, 0,
                          f"window.SPRITES_JELLY_TUNE = {json.dumps(tune)};", box)
                out[(jk, tk, kind)] = fn
    return out


def main():
    port = bsc.serve()
    with sync_playwright() as pw:
        b = pw.chromium.launch(); print("chromium", b.version, flush=True)
        s = shots(b, port); b.close()
    if bsc.errors: print("PAGE ERRORS:", bsc.errors[:10], file=sys.stderr)
    parts = []
    for jk, bell, cap in CASES:
        for tk, rx, tx in TRAFFIC:
            ims = {k: Image.open(s[(jk, tk, k)]).convert("RGB") for k in ("before", "after")}
            a0, a1 = (np.asarray(ims[k]).astype(int) for k in ("before", "after"))
            d = np.abs(a0 - a1).max(axis=2)
            print(f"{jk} {tk}: max abs diff {d.max()}, differing px {(d > 0).sum()} of {d.size}", flush=True)
        ims = {k: Image.open(s[(jk, "net", k)]).convert("RGB") for k in ("before", "after")}
        bx = bsc.common_crop(list(ims.values()))
        cells = {}
        for k, im in ims.items():
            c = im.crop(bx); c.save(GLOW / f"{jk}_{k}.png"); cells[(jk, k)] = c
        mag = 2 if bell <= 64 else 1
        parts.append(bsc.grid(f"PULSE GLOW - bell {bell} px" + (f", {mag}x nearest" if mag > 1 else ", 1:1"),
                              f"8/3 Mbit/s. Right: pulseGlow {AFTER.get('pulseGlow')}, r {AFTER.get('pulseGlowR', 2.5)} dot diam.",
                              [("before", "before: fine, no pulse glow"), ("after", "after: fine + pulse glow")], [(jk, f"{bell} px")], cells, mag=mag))
    Wt = max(p.width for p in parts); Ht = sum(p.height for p in parts) + 24 * (len(parts) - 1)
    sheet = Image.new("RGB", (Wt, Ht), bsc.BG); y = 0
    for p in parts: sheet.paste(p, (0, y)); y += p.height + 24
    fn = bsc.OUT / "SIPHON_GLOW_BEFORE_AFTER.png"; sheet.save(fn); print("SHEET:", fn, sheet.size)


if __name__ == "__main__":
    main()
