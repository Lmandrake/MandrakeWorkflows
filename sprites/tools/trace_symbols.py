#!/usr/bin/env python3
"""Trace the edge-only symbol outlines for the resolution experiment (docs/SYMBOL_RESOLUTION.md, round 2).

  python3 tools/trace_symbols.py [--ref <batman_reference.png>]

Writes prototype/experiments/resolution/symbols_edge.js: every symbol as a list of closed polylines in
the UNIT BOX (x, y in -1..1, +y down, centred, mirror-symmetric about x = 0). Both experiment arms read
it: arm C strokes the polylines as hairlines, arm B rasterises them into an N x N edge mask at any N.

Batman is TRACED from the owner's reference image, never drawn by eye (two by-eye attempts were judged
poor): threshold the yellow, run marching squares on the anti-aliased field at level 0.5 (sub-pixel
contours), keep the outer ring edge and the edge of the black interior (the bat silhouette, which meets
the ring's inner edge at the wing tips), mirror-average about the measured axis, and simplify with
Ramer-Douglas-Peucker. It then re-rasterises the traced polygons and reports IoU against the reference's
own yellow mask, so the fidelity claim is a number. TARDIS and Cog are the arm-C geometry, unchanged.

Reference default: <agent storage>/sprites/refs/batman_reference.png. The reference is the owner's image
and is not committed; this script and its output are.
"""
import argparse, json, math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

SPR = Path(__file__).resolve().parents[1]
OUT = SPR / "prototype/experiments/resolution/symbols_edge.js"


def storage():
    h = Path.home() / "dev/Lodestar/bin/lib/agent_storage.py"
    return Path(subprocess.check_output([sys.executable, str(h)], text=True).strip())


# ---------- marching squares on a scalar field, level 0.5; returns closed loops in pixel coords ----------
def marching(f, lev=0.5):
    H, W = f.shape
    g = np.zeros((H + 2, W + 2)); g[1:-1, 1:-1] = f          # pad so every contour closes
    segs = {}
    def interp(p, q, a, b):
        t = (lev - a) / (b - a) if b != a else 0.5
        return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))
    edges = []
    for y in range(H + 1):
        for x in range(W + 1):
            v = [g[y, x], g[y, x + 1], g[y + 1, x + 1], g[y + 1, x]]
            c = [(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)]
            idx = sum(1 << k for k in range(4) if v[k] > lev)
            if idx in (0, 15): continue
            # edge midpoints by edge id: 0 top, 1 right, 2 bottom, 3 left
            def E(e):
                a, b = e, (e + 1) % 4
                return interp(c[a], c[b], v[a], v[b])
            table = {1: [(3, 0)], 2: [(0, 1)], 3: [(3, 1)], 4: [(1, 2)], 5: [(3, 0), (1, 2)], 6: [(0, 2)],
                     7: [(3, 2)], 8: [(2, 3)], 9: [(2, 0)], 10: [(0, 1), (2, 3)], 11: [(2, 1)], 12: [(1, 3)],
                     13: [(1, 0)], 14: [(0, 3)]}
            for e0, e1 in table[idx]:
                k0 = (x, y, e0) ; k1 = (x, y, e1)
                edges.append((canon(x, y, e0), canon(x, y, e1), E(e0), E(e1)))
    # stitch segments into loops via shared edge keys
    adj = {}
    pts = {}
    for a, b, pa, pb in edges:
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a); pts[a] = pa; pts[b] = pb
    seen, loops = set(), []
    for s in adj:
        if s in seen: continue
        loop, cur, prev = [s], s, None
        seen.add(s)
        while True:
            nx = [n for n in adj[cur] if n != prev and n not in seen]
            if not nx: break
            prev, cur = cur, nx[0]; seen.add(cur); loop.append(cur)
        loops.append(np.array([(pts[k][0] - 1, pts[k][1] - 1) for k in loop]))   # undo the pad
    return loops


def canon(x, y, e):
    # an edge shared by two cells gets one key: top of (x,y) == bottom of (x,y-1), left of (x,y) == right of (x-1,y)
    if e == 0: return ("h", x, y)
    if e == 2: return ("h", x, y + 1)
    if e == 3: return ("v", x, y)
    return ("v", x + 1, y)


def rdp(p, eps):
    if len(p) < 3: return p
    a, b = p[0], p[-1]; ab = b - a; L = np.hypot(*ab) or 1e-9
    d = np.abs(ab[0] * (p[:, 1] - a[1]) - ab[1] * (p[:, 0] - a[0])) / L
    i = int(np.argmax(d))
    if d[i] > eps:
        return np.vstack([rdp(p[:i + 1], eps)[:-1], rdp(p[i:], eps)])
    return np.array([a, b])


def rdp_closed(p, eps):
    # split the ring at its two mutually farthest points so RDP has fixed ends
    i = int(np.argmax(np.hypot(*(p - p[0]).T)));
    a = rdp(np.vstack([p[:i + 1]]), eps); b = rdp(np.vstack([p[i:], p[:1]]), eps)
    return np.vstack([a[:-1], b[:-1]])


def area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def symmetrise(p, ax):
    """Mirror-average one closed loop about x = ax: resample the right half by y, reflect it.
    Done on the RIGHT half (x >= ax) so the output is exactly symmetric by construction."""
    # rotate so the loop starts at its top-most point on the axis side
    q = p.copy()
    # signed: keep the half x >= ax, ordered along the loop, then append its reflection reversed
    right = []
    n = len(q)
    # find a crossing of the axis to start from: the top-most crossing
    cross = [k for k in range(n) if (q[k, 0] - ax) * (q[(k + 1) % n, 0] - ax) <= 0]
    cross.sort(key=lambda k: q[k, 1])
    k0 = cross[0]
    seq = np.vstack([q[k0 + 1:], q[:k0 + 1]])
    # walk from the top crossing; collect points with x >= ax until the next crossing (the bottom one)
    side = 1 if seq[1, 0] >= ax else -1
    half = [np.array([ax, seq[0, 1]])]
    for k in range(1, len(seq)):
        if (seq[k, 0] - ax) * side < 0:
            # interpolate the crossing and stop
            a, b = seq[k - 1], seq[k]; t = (ax - a[0]) / (b[0] - a[0]); half.append(np.array([ax, a[1] + t * (b[1] - a[1])])); break
        half.append(seq[k])
    half = np.array(half)
    if side < 0: half[:, 0] = 2 * ax - half[:, 0]
    # the left half: the reflection, reversed (so the loop stays one orientation)
    left = half[::-1].copy(); left[:, 0] = 2 * ax - left[:, 0]
    return np.vstack([half, left[1:-1]])


def raster(loops, W, H, scale=4):
    im = Image.new("L", (W * scale, H * scale), 0); d = ImageDraw.Draw(im)
    # even-odd fill of all loops: draw each, XOR into the mask
    acc = np.zeros((H * scale, W * scale), bool)
    for p in loops:
        m = Image.new("L", im.size, 0); ImageDraw.Draw(m).polygon([(x * scale, y * scale) for x, y in p], fill=255)
        acc ^= np.asarray(m) > 127
    return np.asarray(Image.fromarray(acc.astype(np.uint8) * 255).resize((W, H), Image.BOX)) > 127


def trace_bat(ref):
    a = np.asarray(Image.open(ref).convert("RGB")).astype(float) / 255
    f = np.clip(((a[..., 0] + a[..., 1]) / 2 - a[..., 2]) * 1.4, 0, 1)    # yellow-ness: R,G high, B low
    m = f > 0.5
    H, W = m.shape
    loops = [l for l in marching(f) if len(l) > 40]
    loops.sort(key=lambda l: -abs(area(l)))
    outer, inner = loops[0], loops[1]       # outer ring edge, then the black interior's edge (the bat)
    ys, xs = np.nonzero(m)
    ax = (outer[:, 0].min() + outer[:, 0].max()) / 2
    cy = (outer[:, 1].min() + outer[:, 1].max()) / 2
    outerS, innerS = symmetrise(outer, ax), symmetrise(inner, ax)
    # fidelity of the TRACE itself, before simplification and before symmetrising: polygon vs mask
    iou = lambda A, B: float((A & B).sum() / (A | B).sum())
    raw_iou = iou(raster([outer, inner], W, H), m)
    sym_iou = iou(raster([outerS, innerS], W, H), m)
    eps = 0.6
    outerR, innerR = rdp_closed(outerS, eps), rdp_closed(innerS, eps)
    simp_iou = iou(raster([outerR, innerR], W, H), m)
    half_w = (outer[:, 0].max() - outer[:, 0].min()) / 2
    aspect = (outer[:, 0].max() - outer[:, 0].min()) / (outer[:, 1].max() - outer[:, 1].min())
    norm = lambda p: [[round((x - ax) / half_w, 4), round((y - cy) / half_w, 4)] for x, y in p]
    stats = {"ref": str(ref), "iou_trace": round(raw_iou, 4), "iou_symmetrised": round(sym_iou, 4),
             "iou_simplified": round(simp_iou, 4), "outer_aspect": round(aspect, 3),
             "points": [len(outerR), len(innerR)], "rdp_eps_px": eps, "ref_px": [W, H]}
    return [norm(outerR), norm(innerR)], stats, (ax, cy, half_w, m, [outerR, innerR])


def tardis():
    # arm C's TARDIS, as edges: body, roof, lamp, 8 door panels, the door split (unit box)
    L = []
    L.append([[-0.60, 0.86], [-0.60, -0.52], [0.60, -0.52], [0.60, 0.86]])
    L.append([[-0.60, -0.52], [-0.46, -0.68], [0.46, -0.68], [0.60, -0.52]])
    L.append([[round(0.085 * math.cos(a * math.pi / 12), 4), round(-0.78 + 0.085 * math.sin(a * math.pi / 12), 4)] for a in range(24)])
    for c in range(2):
        for r in range(4):
            x0 = 0.07 if c else -0.51; y0 = -0.40 + r * 0.30
            L.append([[x0, y0], [x0 + 0.44, y0], [x0 + 0.44, y0 + 0.21], [x0, y0 + 0.21]])
    open_ = [[[0, -0.46], [0, 0.82]]]
    return [[[round(x, 4), round(y, 4)] for x, y in p] for p in L], open_


def cog():
    # arm C's Cog as ONE outer silhouette (ring rOut with 8 teeth) + the bore + the hub
    rIn, rOut, teeth, hub, halfA = 0.46, 0.72, 0.97, 0.17, 0.19
    out = []
    for k in range(8):
        a = k * 2 * math.pi / 8
        a0, a1, a0o, a1o = a - halfA, a + halfA, a - halfA * 0.62, a + halfA * 0.62
        # rim arc from the previous tooth to this tooth's left flank
        prev = a - 2 * math.pi / 8 + halfA
        for s in range(9):
            t = prev + (a0 - prev) * s / 8; out.append([rOut * math.cos(t), rOut * math.sin(t)])
        out.append([teeth * math.cos(a0o), teeth * math.sin(a0o)]); out.append([teeth * math.cos(a1o), teeth * math.sin(a1o)])
        out.append([rOut * math.cos(a1), rOut * math.sin(a1)])
    circ = lambda r, n: [[r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)] for k in range(n)]
    return [[[round(x, 4), round(y, 4)] for x, y in p] for p in (out, circ(rIn, 64), circ(hub, 24))]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ref", default=None); ap.add_argument("--overlay", default=None)
    a = ap.parse_args()
    ref = Path(a.ref) if a.ref else storage() / "sprites/refs/batman_reference.png"
    bat, stats, (ax, cy, hw, m, loopsPx) = trace_bat(ref)
    td, td_open = tardis()
    js = ("/* GENERATED by tools/trace_symbols.py -- do not edit by hand; re-run the script.\n"
          " * Edge-only symbol outlines for the resolution experiment (docs/SYMBOL_RESOLUTION.md, round 2).\n"
          " * Unit box: x,y in -1..1, +y down, centred, mirror-symmetric about x = 0. `loops` are closed\n"
          " * polylines, `open` are open ones. Batman is traced from the owner's reference image:\n"
          f" *   {json.dumps(stats)}\n"
          " * EXPERIMENT ONLY: nothing in app/ or tests/ loads this file. */\n"
          "this.SPRITES_SYMBOLS_EDGE = " + json.dumps({
              "Batman": {"loops": bat, "open": [], "aspect": stats["outer_aspect"]},
              "TARDIS": {"loops": td, "open": td_open},
              "Cog": {"loops": cog(), "open": []},
          }, separators=(",", ":")) + ";\n")
    OUT.write_text(js)
    print(json.dumps(stats))
    print("wrote", OUT)
    if a.overlay:   # outline over the reference, for the eye
        im = Image.open(ref).convert("RGB"); d = ImageDraw.Draw(im)
        for p in loopsPx:
            d.line([tuple(q) for q in p] + [tuple(p[0])], fill=(255, 0, 255), width=1)
        im = im.resize((im.width * 2, im.height * 2), Image.NEAREST); im.save(a.overlay); print("overlay", a.overlay)


if __name__ == "__main__":
    main()
