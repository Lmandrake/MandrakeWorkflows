#!/usr/bin/env python3
"""Build the Night Signals vector glyphs (prototype/vector/glyphs_night_vector.js) from VERY HIGH RES source art.

  python3 tools/build_night_vector.py [--only Batman,Delta,...] [--px 2048]

Owner, 2026-11-07: "For the symbol catalog that Batman belongs a part of (Night Signals), I think we must go with
the vector edges to preserve visual identity ... Please make sure to use very high res initial art to base your
vector versions on to avoid blurriness."

Method, per glyph (all eight go through the same pipeline, so none is drawn "by eye" as a path):
  1. SOURCE ART. A filled silhouette is drawn at 2x the field size (default 4096 px) with PIL and box-downsampled
     to the field (2048 px), which gives an anti-aliased field with exact sub-pixel edges. Batman alone is not drawn:
     it is the owner's reference image (512x360, the only source there is), its yellow-ness field upsampled 4x with
     Lanczos so the contour is traced on a smooth 2048-wide field rather than interpolated across 512 px steps.
     Bat Signal reuses that traced bat, scaled into a round lamp, so the two bats are the same bat.
  2. MIRROR-AVERAGE the field about the glyph's axis (x = 0), so the source itself is symmetric.
  3. MARCHING SQUARES at level 0.5 (sub-pixel contours; the same algorithm as tools/trace_symbols.py, vectorised
     so a 2048 field takes a second instead of minutes).
  4. EXACT SYMMETRY by construction: a loop that crosses the axis is cut at its two crossings, its right half is
     simplified (Ramer-Douglas-Peucker, ends fixed on the axis) and mirrored; a loop wholly right of the axis is
     simplified and gets a mirrored twin; loops wholly left are dropped (they are the twins). So every glyph is
     bilaterally symmetric to the last digit, which tests/test_vector_glyphs.py checks.
  5. Normalise into the UNIT BOX (x, y in -1..1, +y down, centred on the axis) and write the table.
The fidelity of each outline is measured, not claimed: the simplified loops are re-rasterised (even-odd) and
compared with the source field's own mask (IoU, in the table's header line per glyph).

Outputs: the table file (committed) and, under the agent storage root, sprites/night_vector/sources/<Glyph>.png
(the high-res source field), <Glyph>_overlay.png (the outline over it) and sources/stats.json. The source PNGs are
derived and are never committed; this script is their provenance.
"""
import argparse, json, math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

SPR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPR / "tools"))
import trace_symbols as TS   # noqa: E402  (marching-squares edge keys, area, the bat's reference loader)

OUT = SPR / "prototype/vector/glyphs_night_vector.js"
NAMES = ["Batman", "Bat Signal", "Delta", "Autobot", "TARDIS", "Fuji", "Starbird", "Cog"]   # order = iv 0..7
LO_EPS = 0.006      # the coarse level of detail (`lo`), unit coords: what the engine strokes below ~90 CSS px
SPAN = 1.1          # the source canvas covers -SPAN..SPAN in unit coordinates on both axes


def storage():
    h = Path.home() / "dev/Lodestar/bin/lib/agent_storage.py"
    return Path(subprocess.check_output([sys.executable, str(h)], text=True).strip())


# ------------------------------------------------------------------ marching squares, vectorised cell search
TABLE = {1: [(3, 0)], 2: [(0, 1)], 3: [(3, 1)], 4: [(1, 2)], 5: [(3, 0), (1, 2)], 6: [(0, 2)], 7: [(3, 2)],
         8: [(2, 3)], 9: [(2, 0)], 10: [(0, 1), (2, 3)], 11: [(2, 1)], 12: [(1, 3)], 13: [(1, 0)], 14: [(0, 3)]}


def marching(f, lev=0.5):
    """Closed contours of f at `lev`, in pixel coordinates (x = column, y = row). Same cases and edge keys as
    trace_symbols.marching, but only boundary cells are visited."""
    H, W = f.shape
    g = np.zeros((H + 2, W + 2)); g[1:-1, 1:-1] = f
    b = g > lev
    idx = (b[:-1, :-1] * 1 + b[:-1, 1:] * 2 + b[1:, 1:] * 4 + b[1:, :-1] * 8).astype(np.int8)
    ys, xs = np.nonzero((idx != 0) & (idx != 15))
    adj, pts = {}, {}
    for y, x in zip(ys.tolist(), xs.tolist()):
        v = (g[y, x], g[y, x + 1], g[y + 1, x + 1], g[y + 1, x]); c = ((x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1))
        for e0, e1 in TABLE[int(idx[y, x])]:
            for e in (e0, e1):
                k = TS.canon(x, y, e)
                if k not in pts:
                    a, bb = e, (e + 1) % 4; va, vb = v[a], v[bb]; t = (lev - va) / (vb - va) if vb != va else 0.5
                    pts[k] = (c[a][0] + t * (c[bb][0] - c[a][0]) - 1, c[a][1] + t * (c[bb][1] - c[a][1]) - 1)
            ka, kb = TS.canon(x, y, e0), TS.canon(x, y, e1)
            adj.setdefault(ka, []).append(kb); adj.setdefault(kb, []).append(ka)
    seen, loops = set(), []
    for s in adj:
        if s in seen: continue
        loop, cur, prev = [s], s, None; seen.add(s)
        while True:
            nx = [n for n in adj[cur] if n != prev and n not in seen]
            if not nx: break
            prev, cur = cur, nx[0]; seen.add(cur); loop.append(cur)
        if len(loop) > 8: loops.append(np.array([pts[k] for k in loop]))
    return loops


def rdp(p, eps):
    """Ramer-Douglas-Peucker on an OPEN polyline, ends fixed (iterative, so long contours cannot hit recursion)."""
    if len(p) < 3: return p
    keep = np.zeros(len(p), bool); keep[0] = keep[-1] = True; stack = [(0, len(p) - 1)]
    while stack:
        i0, i1 = stack.pop()
        if i1 <= i0 + 1: continue
        a, b = p[i0], p[i1]; ab = b - a; L = math.hypot(*ab) or 1e-12; q = p[i0 + 1:i1]
        d = np.abs(ab[0] * (q[:, 1] - a[1]) - ab[1] * (q[:, 0] - a[0])) / L
        k = int(np.argmax(d))
        if d[k] > eps: m = i0 + 1 + k; keep[m] = True; stack += [(i0, m), (m, i1)]
    return p[keep]


def rdp_closed(p, eps):
    i = int(np.argmax(np.hypot(*(p - p[0]).T)))
    a = rdp(p[:i + 1], eps); b = rdp(np.vstack([p[i:], p[:1]]), eps)
    return np.vstack([a[:-1], b[:-1]])


def symmetric_loops(loops, eps):
    """Loops in unit coords (axis x = 0) -> exactly mirror-symmetric simplified loops (see the module doc, step 4)."""
    out = []
    for p in loops:
        xs = p[:, 0]
        if xs.min() > 1e-9:                                   # wholly right of the axis: keep + mirrored twin
            q = rdp_closed(p, eps); out.append(q); out.append((q * [-1, 1])[::-1]); continue
        if xs.max() < -1e-9: continue                         # wholly left: its twin comes from the right
        n = len(p)                                            # crosses the axis: cut at the crossings
        cr = []
        for k in range(n):
            a, b = p[k], p[(k + 1) % n]
            if (a[0] >= 0) != (b[0] >= 0):
                t = -a[0] / (b[0] - a[0]); cr.append((k, np.array([0.0, a[1] + t * (b[1] - a[1])])))
        if len(cr) != 2:
            raise SystemExit(f"a loop crosses the axis {len(cr)} times; symmetric_loops expects 2")
        (k0, c0), (k1, c1) = cr
        seg1 = [c0] + [p[(k0 + 1 + j) % n] for j in range((k1 - k0) % n)] + [c1]
        seg2 = [c1] + [p[(k1 + 1 + j) % n] for j in range((k0 - k1) % n)] + [c0]
        half = np.array(seg1 if np.mean([q[0] for q in seg1[1:-1]] or [0]) > 0 else seg2)
        h = rdp(half, eps); h[0, 0] = h[-1, 0] = 0.0
        mir = (h[1:-1] * [-1, 1])[::-1]
        out.append(np.vstack([h, mir]))
    return out


# ------------------------------------------------------------------ drawing helpers (unit coords -> source px)
class Canvas:
    """A supersampled binary canvas in unit coordinates; .field() is the anti-aliased field at the output size."""
    def __init__(self, px, ss=2):
        self.px, self.S = px, px * ss; self.im = Image.new("L", (self.S, self.S), 0); self.d = ImageDraw.Draw(self.im)

    def P(self, pts): return [((x + SPAN) / (2 * SPAN) * self.S, (y + SPAN) / (2 * SPAN) * self.S) for x, y in pts]

    def poly(self, pts, on=True, mirror=True):
        """pts: the RIGHT half (x >= 0) of a symmetric polygon, start and end on the axis, unless mirror=False."""
        if mirror: pts = list(pts) + [(-x, y) for x, y in reversed(pts)]
        self.d.polygon(self.P(pts), fill=255 if on else 0)

    def disc(self, cx, cy, r, on=True):
        (x0, y0), (x1, y1) = self.P([(cx - r, cy - r), (cx + r, cy + r)]); self.d.ellipse([x0, y0, x1, y1], fill=255 if on else 0)

    def field(self):
        return np.asarray(self.im.resize((self.px, self.px), Image.BOX)).astype(float) / 255


def bez(p0, p1, p2, p3, n=64):
    t = np.linspace(0, 1, n)[:, None]; p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return [tuple(v) for v in ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)]


def arcpts(cx, cy, r, a0, a1, n=180):
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(a0, a1, n)]


# ------------------------------------------------------------------ the bat (traced from the owner's reference)
def bat_loops_unit(ref, up=4):
    """The reference's ring and bat, traced on a 4x Lanczos-upsampled yellow-ness field. Unit coords: x = ±1 at the
    ring's outer extremes, centred on the ring. Returns (outer ring loop, bat loop, field, stats)."""
    a = np.asarray(Image.open(ref).convert("RGB")).astype(float) / 255
    f0 = np.clip(((a[..., 0] + a[..., 1]) / 2 - a[..., 2]) * 1.4, 0, 1)
    h0, w0 = f0.shape
    f = np.asarray(Image.fromarray((f0 * 65535).astype(np.uint16).astype(np.int32), "I").resize((w0 * up, h0 * up), Image.LANCZOS)).astype(float) / 65535
    # the reference's own 1-px jaggies survive Lanczos as a staircase on the level-0.5 contour; a Gaussian of 0.75
    # reference px removes them without moving the edge (a blur of a symmetric step leaves its 0.5 level in place)
    from scipy.ndimage import gaussian_filter
    f = np.clip(gaussian_filter(np.clip(f, 0, 1), 0.75 * up), 0, 1)
    loops = [l for l in marching(f) if len(l) > 200]; loops.sort(key=lambda l: -abs(TS.area(l)))
    outer, inner = loops[0], loops[1]
    ax = (outer[:, 0].min() + outer[:, 0].max()) / 2; cy = (outer[:, 1].min() + outer[:, 1].max()) / 2
    hw = (outer[:, 0].max() - outer[:, 0].min()) / 2
    U = lambda p: np.column_stack([(p[:, 0] - ax) / hw, (p[:, 1] - cy) / hw])
    geo = (ax / up, cy / up, hw / up, f0 > 0.5)        # for the IoU against the reference's own mask
    return U(outer), U(inner), f, geo, {"ref": str(ref), "ref_px": [w0, h0], "traced_px": [w0 * up, h0 * up],
                                   "outer_aspect": round(float(np.ptp(outer[:, 0]) / np.ptp(outer[:, 1])), 3)}


def unit_to_canvas_mask(loops, px):
    """Even-odd raster of unit-coordinate loops on the standard source canvas, for IoU and the source PNG."""
    c = Canvas(px); acc = np.zeros((c.S, c.S), bool)
    for p in loops:
        m = Image.new("L", (c.S, c.S), 0); ImageDraw.Draw(m).polygon(c.P(p.tolist()), fill=255); acc ^= np.asarray(m) > 127
    return np.asarray(Image.fromarray(acc.astype(np.uint8) * 255).resize((px, px), Image.BOX)).astype(float) / 255


# ------------------------------------------------------------------ the eight designs
def g_batman(px, ctx):
    outer, inner = ctx["bat"]
    return unit_to_canvas_mask([outer, inner], px)


def g_batsignal(px, ctx):
    """A round searchlight lamp: a rim ring, and inside it the same traced bat, free-standing. Its OUTLINE is a
    circle where Batman's is a 1.8:1 oval, which is what tells the two apart at sprite size."""
    _o, inner = ctx["bat"]
    k = 0.74 / np.abs(inner[:, 0]).max()
    bat = inner * k; bat[:, 1] -= (bat[:, 1].max() + bat[:, 1].min()) / 2
    c = Canvas(px); c.disc(0, 0, 0.98); c.disc(0, 0, 0.86, on=False)
    c.d.polygon(c.P(bat.tolist()), fill=255)
    return c.field()


def g_delta(px, ctx):
    """The Starfleet arrowhead: a spire swept out to two feet, the base curving up between them, a star cut in it."""
    c = Canvas(px)
    right = [(0.0, -0.98)] + bez((0, -0.98), (0.20, -0.50), (0.50, 0.40), (0.68, 0.96))[1:] \
        + bez((0.68, 0.96), (0.44, 0.74), (0.16, 0.50), (0.0, 0.50))[1:]
    c.poly(right)
    star = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5; r = 0.27 if k % 2 == 0 else 0.11
        star.append((r * math.cos(a), 0.06 + r * math.sin(a)))
    c.d.polygon(c.P(star), fill=0)
    return c.field()


def g_autobot(px, ctx):
    """The Autobot face: a crest between two horns, wide cheeks, a chin; eyes, cheek vents and the mouth cut out."""
    c = Canvas(px)
    c.poly([(0, -0.98), (0.13, -0.64), (0.33, -0.58), (0.50, -0.96), (0.68, -0.96), (0.62, -0.50), (0.86, -0.40),
            (0.86, 0.16), (0.68, 0.30), (0.68, 0.62), (0.38, 0.97), (0, 0.97)])
    for m in (1, -1):
        c.poly([(m * 0.10, -0.38), (m * 0.58, -0.34), (m * 0.58, -0.18), (m * 0.14, -0.10)], on=False, mirror=False)
        c.poly([(m * 0.50, 0.02), (m * 0.74, -0.14), (m * 0.74, 0.08), (m * 0.50, 0.26)], on=False, mirror=False)
    c.poly([(0, 0.30), (0.17, 0.30), (0.31, 0.46), (0.24, 0.76), (0, 0.76)], on=False)
    return c.field()


def g_tardis(px, ctx):
    """The police box: lamp, two-step roof, the sign band, two doors of four panels each, a plinth."""
    c = Canvas(px)
    c.poly([(0, -0.98), (0.07, -0.98), (0.07, -0.78), (0.46, -0.78), (0.58, -0.68), (0.58, -0.58), (0.54, -0.58),
            (0.54, 0.86), (0.62, 0.86), (0.62, 0.98), (0, 0.98)])
    c.poly([(0, -0.52), (0.46, -0.52), (0.46, -0.40), (0, -0.40)], on=False)          # the sign band
    for m in (1, -1):
        for r in range(4):
            y0 = -0.30 + r * 0.29
            c.poly([(m * 0.07, y0), (m * 0.44, y0), (m * 0.44, y0 + 0.21), (m * 0.07, y0 + 0.21)], on=False, mirror=False)
    return c.field()


def g_fuji(px, ctx):
    """The Atari mark: a straight centre stem, and a stem each side that flares outward to the base."""
    c = Canvas(px)
    c.poly([(0, -0.92), (0.10, -0.92), (0.10, 0.92), (0, 0.92)])
    ts = np.linspace(0, 1, 120)
    inner = [(0.20 + 0.26 * t ** 2.4, -0.92 + 1.84 * t) for t in ts]
    outer = [(0.36 + 0.62 * t ** 2.0, -0.92 + 1.84 * t) for t in ts]
    for m in (1, -1):
        c.poly([(m * x, y) for x, y in inner + outer[::-1]], mirror=False)
    return c.field()


def g_starbird(px, ctx):
    """The Rebel crest: a thick crescent ring open at the top into two upswept horns, an inner prong on each side,
    and a tall centre spire. Round and bottom-heavy, unlike the flat oval bat and the faceted Autobot."""
    c = Canvas(px); S = c.S
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32); u = xx / S * 2 * SPAN - SPAN; v = yy / S * 2 * SPAN - SPAN
    r = lambda cx, cy: np.hypot(u - cx, v - cy)
    ang = np.degrees(np.arctan2(u, -v))                     # 0 = straight up, +-180 = straight down
    ring = (r(0, 0.06) < 0.92) & (r(0, -0.08) > 0.70) & (np.abs(ang) > 34)
    prong = (r(0, 0.22) < 0.58) & (r(0, 0.04) > 0.44) & (np.abs(ang) > 28) & (np.abs(ang) < 125)
    gap = (np.abs(u) > 0.15) & (np.abs(u) < 0.21) & (v > 0.30)          # the slits beside the spire's foot
    m = (ring | prong) & ~gap
    c.im = Image.fromarray(m.astype(np.uint8) * 255); c.d = ImageDraw.Draw(c.im)
    c.poly([(0, -1.0), (0.05, -0.78), (0.10, -0.30), (0.15, 0.40), (0.15, 0.99), (0, 0.99)])
    return c.field()


def g_cog(px, ctx):
    """The Imperial crest: an outer ring, a hub ring, six spokes widening toward the rim (one straight up)."""
    c = Canvas(px)
    c.disc(0, 0, 0.98); c.disc(0, 0, 0.82, on=False); c.disc(0, 0, 0.33); c.disc(0, 0, 0.17, on=False)
    for k in range(6):
        a = -math.pi / 2 + k * math.pi / 3; h0, h1 = math.radians(9), math.radians(17)
        pts = [(0.28 * math.cos(a - h0), 0.28 * math.sin(a - h0)), (0.86 * math.cos(a - h1), 0.86 * math.sin(a - h1)),
               (0.86 * math.cos(a + h1), 0.86 * math.sin(a + h1)), (0.28 * math.cos(a + h0), 0.28 * math.sin(a + h0))]
        c.poly(pts, mirror=False)
    c.disc(0, 0, 0.17, on=False)
    return c.field()


DESIGNS = {"Batman": g_batman, "Bat Signal": g_batsignal, "Delta": g_delta, "Autobot": g_autobot,
           "TARDIS": g_tardis, "Fuji": g_fuji, "Starbird": g_starbird, "Cog": g_cog}
HOW = {"Batman": "traced from the owner's reference (512x360), yellow-ness field Lanczos-upsampled 4x, Gaussian 0.75 ref px, marching squares",
       "Bat Signal": "the traced bat scaled into a PIL-drawn rim ring, 4096 px supersampled to the field",
       **{n: "drawn as a filled silhouette with PIL at 4096 px, box-downsampled to the field" for n in
          ("Delta", "Autobot", "TARDIS", "Fuji", "Starbird", "Cog")}}


def iou(a, b):
    A, B = a > 0.5, b > 0.5; return float((A & B).sum() / max(1, (A | B).sum()))


def build_one(name, px, ctx, eps_px):
    f = DESIGNS[name](px, ctx)
    f = (f + f[:, ::-1]) / 2                                            # mirror-average the source about x = 0
    s = px / (2 * SPAN)
    U = lambda p: np.column_stack([(p[:, 0] + 0.5) / s - SPAN, (p[:, 1] + 0.5) / s - SPAN])
    raw = [U(l) for l in marching(f)]
    raw = [l for l in raw if abs(TS.area(l)) * s * s > 30]               # drop specks under ~30 source px
    loops = symmetric_loops(raw, eps_px / s)
    lo = symmetric_loops(raw, LO_EPS)
    back = unit_to_canvas_mask(loops, px)
    st = {"source_px": px, "loops": len(loops), "points": int(sum(len(l) for l in loops)), "iou_vs_source": round(iou(back, f), 4),
          "rdp_eps_source_px": eps_px, "how": HOW[name]}
    st["points_lo"] = int(sum(len(l) for l in lo))
    return loops, lo, f, st


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=None); ap.add_argument("--px", type=int, default=2048)
    ap.add_argument("--eps", type=float, default=1.2, help="RDP tolerance in SOURCE px (2048 field: 1.2 px = 0.0013 unit)")
    a = ap.parse_args()
    src = storage() / "sprites/night_vector/sources"; src.mkdir(parents=True, exist_ok=True)
    outer, inner, bf, geo, bst = bat_loops_unit(storage() / "sprites/refs/batman_reference.png")
    Image.fromarray((np.clip(bf, 0, 1) * 255).astype(np.uint8)).save(src / "Batman_reference_traced_field.png")
    ctx = {"bat": (outer, inner)}
    names = a.only.split(",") if a.only else NAMES
    prev = json.loads((src / "stats.json").read_text()) if (src / "stats.json").exists() else {}
    table = {}
    if OUT.exists() and a.only:   # partial rebuild: keep the others as they are
        s0 = OUT.read_text(); table = dict(json.loads(s0[s0.index("= [") + 2:s0.rindex("];") + 1]))
    for n in names:
        loops, lo, f, st = build_one(n, a.px, ctx, a.eps)
        if n == "Batman":
            st.update(bst); ax, cy, hw, m = geo; h0, w0 = m.shape
            px_loops = [np.column_stack([l[:, 0] * hw + ax, l[:, 1] * hw + cy]) for l in loops]
            st["iou_vs_reference"] = round(float((TS.raster(px_loops, w0, h0) & m).sum() / (TS.raster(px_loops, w0, h0) | m).sum()), 4)
        prev[n] = st
        Image.fromarray((f * 255).astype(np.uint8)).save(src / f"{n.replace(' ', '_')}.png")
        ov = Image.fromarray((f * 110).astype(np.uint8)).convert("RGB"); d = ImageDraw.Draw(ov); s = a.px / (2 * SPAN)
        for l in loops:
            pts = [((x + SPAN) * s, (y + SPAN) * s) for x, y in l]; d.line(pts + [pts[0]], fill=(255, 40, 220), width=3)
        ov.save(src / f"{n.replace(' ', '_')}_overlay.png")
        R4 = lambda L: [[[round(float(x), 4), round(float(y), 4)] for x, y in l] for l in L]
        table[n] = {"loops": R4(loops), "lo": R4(lo)}
        print(n, json.dumps(st), flush=True)
    (src / "stats.json").write_text(json.dumps(prev, indent=1))
    hdr = "\n".join(f" *   {n:<10} {json.dumps({k: prev[n][k] for k in ('source_px', 'loops', 'points', 'points_lo', 'iou_vs_source', 'iou_vs_reference') if k in prev[n]})}" for n in NAMES if n in prev)
    js = ("/* GENERATED by tools/build_night_vector.py -- do not edit by hand; re-run the script.\n"
          " * Night Signals (species c6_night) as edge-only VECTOR outlines, drawn by prototype/vector/engine.js.\n"
          " * Owner's selection, 2026-11-06 (Batman and the Bat Signal came from a collaborator); vector edges by ruling, 2026-11-07.\n"
          " *\n"
          " * 🔴 THIS FILE IS THE TRADEMARK-BEARING SET, AND IT IS ONE FILE ON PURPOSE. These eight are other people's marks\n"
          " * (DC, Paramount, Hasbro, the BBC, Atari, Lucasfilm). Private repo, the owner's own desktop, never distributed. If\n"
          " * Sprites is ever published, delete this file, prototype/c6_night.html, and the c6_night registrations\n"
          " * (docs/SYMBOL_SPECIES.md, \"Adding a species\"); nothing else in the tree names these symbols.\n"
          " *\n"
          " * Identity only (GRAMMAR_V2.md, must_not_conclude): a bat does not mean night, a delta does not mean a mission.\n"
          " * Format: [[name, {loops: [[[x, y], ...], ...], lo: (the same loops, coarser)}], ... x8], order = iv. Unit box: x, y in -1..1, +y down, centred,\n"
          " * every loop closed (last point joins the first), the whole set exactly mirror-symmetric about x = 0\n"
          " * (tests/test_vector_glyphs.py). Per glyph: source px, loop and point counts, IoU of the outline vs its source:\n"
          f"{hdr}\n */\n"
          "this.SPRITES_GLYPHS_NIGHT_VECTOR = [\n" +
          ",\n".join(f"  [{json.dumps(n)}, {json.dumps(table[n], separators=(',', ':'))}]" for n in NAMES if n in table) + "\n];\n")
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(js)
    print("wrote", OUT, f"{len(js) // 1024} KB; sources in", src)


if __name__ == "__main__":
    main()
