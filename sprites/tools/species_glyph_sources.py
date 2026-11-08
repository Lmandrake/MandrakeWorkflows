#!/usr/bin/env python3
"""High-res glyph sources for the species-style sample sheet (tools/build_species_style_samples.py).

  python3 tools/species_glyph_sources.py

Forty glyphs (the eight of each of five species, docs/SYMBOL_SPECIES.md roster) are drawn PROGRAMMATICALLY as 2048 x 2048 binary masks in the unit box
(x, y in -1..1, +y down), then forced exactly mirror-symmetric (mask |= its left-right flip). Interior detail is
drawn as HOLES in the mask, so both styles carry the same detail: style (a) strokes every hole's edge, style (b)
leaves the hole dark. From each mask this writes:
  (a) vector: contours by marching squares on a 512 px box-filtered field (tools/trace_symbols.py, imported),
      RDP-simplified, made exactly symmetric (axis-crossing loops via trace_symbols.symmetrise; off-axis loops
      kept on the right and mirrored), plus the IoU of the re-rasterised contours against the mask.
  (b) dots: for each render extent E (23, 64, 256 CSS px at dpr 2) a lattice in DEVICE pixels (integer
      offsets from the glyph centre), lit where the mask covers > half the dot's lattice cell; dots with an
      unlit neighbour are flagged as edge dots (drawn brighter).
Sources (PNG) go to <agent storage>/sprites/species_style_sources/; the generated data file is
prototype/experiments/resolution/species_glyphs.js. Form carries no data: these are identity marks only.
"""
import json, math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

SPR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPR / "tools"))
from trace_symbols import marching, rdp_closed, symmetrise, area, raster   # noqa: E402  (import only; never edited)

OUT_JS = SPR / "prototype/experiments/resolution/species_glyphs.js"
S = 2048                     # source resolution
F = 512                      # contour field resolution (box filter of the source)
DPR = 2
# per extent E (CSS px): dot square size, horizontal pitch, row pitch, row offset -- all in DEVICE px
LATTICE = {23: dict(dot=1, px=2, py=2, off=0), 64: dict(dot=2, px=4, py=3, off=2), 256: dict(dot=4, px=6, py=5, off=3)}


def storage():
    h = Path.home() / "dev/Lodestar/bin/lib/agent_storage.py"
    return Path(subprocess.check_output([sys.executable, str(h)], text=True).strip())


# ------------------------------------------------------------------ drawing helpers (unit box -> source px)
def P(u, v): return ((u + 1) * S / 2, (v + 1) * S / 2)
def L(d): return d * S / 2


class Pen:
    def __init__(self): self.im = Image.new("L", (S, S), 0); self.d = ImageDraw.Draw(self.im)
    def poly(self, pts, on=True): self.d.polygon([P(*p) for p in pts], fill=255 if on else 0)
    def disc(self, c, r, on=True):
        x, y = P(*c); self.d.ellipse([x - L(r), y - L(r), x + L(r), y + L(r)], fill=255 if on else 0)
    def ell(self, c, rx, ry, on=True):
        x, y = P(*c); self.d.ellipse([x - L(rx), y - L(ry), x + L(rx), y + L(ry)], fill=255 if on else 0)
    def ring(self, c, r0, r1, on=True):   # annulus r0..r1
        self.disc(c, r1, on); self.disc(c, r0, not on)
    def line(self, pts, w, on=True):
        q = [P(*p) for p in pts]; self.d.line(q, fill=255 if on else 0, width=max(1, int(round(L(w)))), joint="curve")
        for p in (pts[0], pts[-1]): self.disc(p, w / 2, on)
    def rect(self, x0, y0, x1, y1, on=True): self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], on)
    def mask(self):
        a = np.asarray(self.im) > 127
        return a | a[:, ::-1]                      # exact mirror symmetry about x = 0


def both(f):
    """Call f(sign) for the right (+1) and left (-1) halves."""
    for s in (1, -1): f(s)


def spline(pts, n=24, closed=True):
    """Catmull-Rom through pts (unit coords)."""
    p = list(pts); m = len(p); out = []
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0, p1, p2, p3 = p[(i - 1) % m] if closed or i > 0 else p[0], p[i], p[(i + 1) % m], p[(i + 2) % m] if closed or i + 2 < m else p[-1]
        for k in range(n):
            t = k / n; t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    if not closed: out.append(p[-1])
    return out


def hexagon(c, r, rot=0.0):
    return [(c[0] + r * math.cos(rot + k * math.pi / 3), c[1] + r * math.sin(rot + k * math.pi / 3)) for k in range(6)]


# ------------------------------------------------------------------ the ten glyphs
def jwst():
    """18 flat-top hex segments in columns of 3-4-4-4-3 around an empty centre, plus the secondary mirror."""
    g = Pen(); r = 0.218
    for q in range(-2, 3):
        for t in range(-2, 3):
            if 1 <= max(abs(q), abs(t), abs(q + t)) <= 2:     # axial distance 1 or 2: 6 + 12 = 18 segments
                g.poly(hexagon((1.5 * r * q, math.sqrt(3) * r * (t + q / 2)), r * 0.80))
    g.disc((0, 0), 0.075)
    return g.mask()


def golden_record():
    """A disc with five fine grooves, a label ring, the spindle hole, and the hydrogen 'o-o' on the label."""
    g = Pen(); g.disc((0, 0), 0.95)
    for rg in (0.86, 0.78, 0.70, 0.62, 0.54): g.ring((0, 0), rg - 0.018, rg + 0.018, on=False)
    g.ring((0, 0), 0.38, 0.44, on=False)           # label edge
    g.disc((0, 0), 0.06, on=False)                 # spindle hole
    for k in range(14):                            # the cover's pulsar map, as a burst of hairline gaps on the label
        t = 2 * math.pi * (k + 0.5) / 14
        g.line([(0.11 * math.cos(t), 0.11 * math.sin(t)), (0.33 * math.cos(t), 0.33 * math.sin(t))], 0.028, on=False)
    return g.mask()


def bohr():
    """Nucleus, three crossed elliptical orbits (0, 60, 120 deg), two electrons per pair, mirror-placed."""
    g = Pen(); a, b, w = 0.86, 0.31, 0.06
    for ang in (0, 60, 120):
        t = math.radians(ang); pts = []
        for k in range(181):
            u = 2 * math.pi * k / 180; x, y = a * math.cos(u), b * math.sin(u)
            pts.append((x * math.cos(t) - y * math.sin(t), x * math.sin(t) + y * math.cos(t)))
        g.line(pts, w)
    g.disc((0, 0), 0.17)
    for ang in (60,):
        t = math.radians(ang); x, y = a * math.cos(t), a * math.sin(t)
        both(lambda s: g.disc((s * x, y), 0.085))
    both(lambda s: g.disc((s * a, 0), 0.085))
    return g.mask()


def neural_net():
    """Three layers (3-3-3, a denser 3-4-3 was a tangle at 23 px) of ring nodes, every node joined to every node of the next
    layer by a hairline. Edges stop at the rings and are thin enough to stroke as one line (0.045 doubled into a tangle)."""
    g = Pen(); xs = (-0.76, 0, 0.76); ys = (-0.62, 0, 0.62); rn = 0.16
    for i in range(2):
        for y0 in ys:
            for y1 in ys:
                x0, x1 = xs[i], xs[i + 1]; L = math.hypot(x1 - x0, y1 - y0); ux, uy = (x1 - x0) / L, (y1 - y0) / L
                g.line([(x0 + ux * rn, y0 + uy * rn), (x1 - ux * rn, y1 - uy * rn)], 0.022)
    for x in xs:
        for y in ys: g.ring((x, y), rn - 0.07, rn)
    return g.mask()


def butterfly():
    """Body, clubbed antennae, upper and lower wings cut into a vein mosaic with marginal spots."""
    g = Pen()
    up = [(0.07, -0.28), (0.30, -0.70), (0.66, -0.86), (0.93, -0.74), (0.92, -0.40), (0.66, -0.10), (0.08, -0.02)]
    lo = [(0.08, 0.02), (0.50, 0.04), (0.76, 0.30), (0.70, 0.62), (0.44, 0.82), (0.20, 0.72), (0.07, 0.36)]
    def wings(s):
        g.poly([(s * x, y) for x, y in spline(up)]); g.poly([(s * x, y) for x, y in spline(lo)])
    both(wings)
    # veins (holes) from the wing roots toward the margin
    def veins(s):
        for tip in ((0.40, -0.70), (0.68, -0.72), (0.84, -0.50), (0.70, -0.24)):
            g.line([(s * 0.12, -0.10), (s * (0.12 + 0.86 * (tip[0] - 0.12)), -0.10 + 0.86 * (tip[1] + 0.10))], 0.032, on=False)
        for tip in ((0.62, 0.28), (0.56, 0.60), (0.28, 0.68)):
            g.line([(s * 0.12, 0.08), (s * (0.12 + 0.86 * (tip[0] - 0.12)), 0.08 + 0.86 * (tip[1] - 0.08))], 0.032, on=False)
        for c in ((0.62, -0.80), (0.82, -0.72), (0.90, -0.56), (0.86, -0.40), (0.70, 0.44), (0.58, 0.68), (0.40, 0.76)):
            g.disc((s * c[0], c[1]), 0.035, on=False)
        # the inner cell gap that separates the body from the wings
        g.line([(s * 0.075, -0.30), (s * 0.075, 0.42)], 0.03, on=False)
    both(veins)
    g.ell((0, 0.05), 0.05, 0.50)                    # body
    g.disc((0, -0.50), 0.075)                       # head
    def ant(s):
        g.line([(s * 0.03, -0.55), (s * 0.10, -0.76), (s * 0.22, -0.90)], 0.028); g.disc((s * 0.23, -0.91), 0.045)
    both(ant)
    return g.mask()


def owl():
    """Egg body, ear tufts, ringed eyes, beak, wing lines and rows of chevron breast feathers (holes)."""
    g = Pen()
    g.ell((0, 0.22), 0.60, 0.72)
    g.ell((0, -0.30), 0.62, 0.46)
    both(lambda s: g.poly([(s * 0.18, -0.62), (s * 0.58, -0.94), (s * 0.62, -0.42)]))   # ear tufts
    def eye(s):
        g.disc((s * 0.27, -0.28), 0.25, on=False); g.disc((s * 0.27, -0.28), 0.18); g.disc((s * 0.27, -0.28), 0.075, on=False)
    both(eye)
    g.poly([(-0.075, -0.10), (0.075, -0.10), (0, 0.08)], on=False)                    # beak
    both(lambda s: g.line(spline([(s * 0.46, 0.0), (s * 0.40, 0.40), (s * 0.30, 0.82)], 12, closed=False), 0.035, on=False))
    for row, (y, xs) in enumerate([(0.26, (0.0, 0.17)), (0.44, (0.085, 0.255)), (0.62, (0.0, 0.17)), (0.78, (0.085,))]):
        for x in xs:
            for s in ((1, -1) if x else (1,)):
                cx = s * x; g.line([(cx - 0.06, y - 0.05), (cx, y), (cx + 0.06, y - 0.05)], 0.03, on=False)
    g.rect(-0.20, 0.90, -0.07, 0.97); g.rect(0.07, 0.90, 0.20, 0.97)                  # feet
    return g.mask()


def lighthouse():
    """Tapered banded tower, gallery, lantern with window, dome and finial, door, base, two light beams."""
    g = Pen()
    g.poly([(-0.20, -0.34), (0.20, -0.34), (0.34, 0.84), (-0.34, 0.84)])
    for y0, y1 in ((-0.04, 0.03), (0.34, 0.41)):    # stripe bands, as gaps
        g.rect(-0.5, y0, 0.5, y1, on=False)
    g.rect(-0.30, -0.42, 0.30, -0.34)               # gallery
    g.rect(-0.15, -0.66, 0.15, -0.46)               # lantern room
    g.rect(-0.08, -0.62, 0.08, -0.50, on=False)     # lantern window
    g.poly(spline([(-0.17, -0.66), (0, -0.84), (0.17, -0.66)], 12, closed=False) + [(0.17, -0.66)])
    g.disc((0, -0.88), 0.04)
    g.poly([(-0.08, 0.84), (-0.08, 0.66), (0, 0.60), (0.08, 0.66), (0.08, 0.84)], on=False)   # door
    g.rect(-0.52, 0.84, 0.52, 0.95)                 # base
    both(lambda s: g.poly([(s * 0.22, -0.58), (s * 0.98, -0.82), (s * 0.98, -0.34), (s * 0.22, -0.52)]))   # beams
    return g.mask()


def target():
    """Two bold rings and a big bullseye, cut by four crosshair gaps (so it is a target, not a record). Three thinner rings
    broke into a maze on the 23 px dot lattice."""
    g = Pen()
    for r0, r1 in ((0.70, 0.95), (0.34, 0.54)): g.ring((0, 0), r0, r1)
    g.disc((0, 0), 0.18)
    g.rect(-0.05, -1, 0.05, -0.24, on=False); g.rect(-0.05, 0.24, 0.05, 1, on=False)
    g.rect(-1, -0.05, -0.24, 0.05, on=False); g.rect(0.24, -0.05, 1, 0.05, on=False)
    return g.mask()


def skull():
    """Cranium, cheekbones, jaw; eye sockets, nasal cavity and tooth gaps as holes."""
    g = Pen()
    g.ell((0, -0.22), 0.74, 0.68)
    g.poly(spline([(-0.46, 0.18), (0.46, 0.18), (0.42, 0.66), (0.24, 0.84), (-0.24, 0.84), (-0.42, 0.66)]))
    both(lambda s: g.ell((s * 0.30, -0.10), 0.21, 0.19, on=False))
    g.poly([(0, 0.10), (-0.10, 0.32), (0.10, 0.32)], on=False)
    g.line([(-0.36, 0.55), (0.36, 0.55)], 0.035, on=False)
    for x in (0.0, 0.12, 0.24):
        for s in ((1, -1) if x else (1,)): g.line([(s * x, 0.44), (s * x, 0.72)], 0.032, on=False)
    both(lambda s: g.poly([(s * 0.74, 0.0), (s * 0.80, 0.30), (s * 0.48, 0.30), (s * 0.48, 0.10)], on=False))   # temple notch
    return g.mask()


def phoenix():
    """Heraldic phoenix rising: crested head, body, two broad raised wings whose trailing edges are notched into
    feathers, a short forked tail. No flames (owner, 2026-11-07: bird only; a first draft with fanned 'finger' feathers
    read as a hand on a stalk in both styles)."""
    g = Pen()
    g.poly(spline([(0, -0.42), (0.13, -0.28), (0.12, 0.08), (0, 0.30), (-0.12, 0.08), (-0.13, -0.28)], 16))   # body
    g.disc((0, -0.50), 0.11)                                                                              # head
    g.poly([(-0.03, -0.46), (0.03, -0.46), (0, -0.36)], on=False)                                         # beak
    for x, top in ((0, -0.84), (0.11, -0.74)):                                                             # crest
        for s in ((1, -1) if x else (1,)):
            g.poly(spline([(s * x - 0.04, -0.56), (s * x + (0.05 * s if x else 0), top), (s * x + 0.04, -0.56)], 10, closed=False))
    def wing(s):
        w = [(0.08, -0.30), (0.36, -0.52), (0.66, -0.78), (0.97, -0.94), (0.93, -0.62), (0.82, -0.38),
             (0.64, -0.16), (0.40, 0.00), (0.12, 0.06)]
        g.poly([(s * x, y) for x, y in spline(w, 16)])
        for (x, y), (dx, dy) in (((0.90, -0.60), (-0.26, -0.10)), ((0.78, -0.37), (-0.26, -0.12)), ((0.60, -0.16), (-0.22, -0.14))):
            n = 0.045
            g.poly([(s * (x + 0.06), y + 0.03), (s * (x + dx), y + dy), (s * (x - 0.02), y + 0.06)], on=False)
    both(wing)
    both(lambda s: g.poly(spline([(s * 0.02, 0.22), (s * 0.20, 0.46), (s * 0.24, 0.50), (s * 0.10, 0.40)], 8)))   # forked tail
    return g.mask()


# ------------------------------------------------------------------ the other thirty (roster order, docs/SYMBOL_SPECIES.md)
def arc(c, r, a0, a1, n=48):
    """Points on a circle, angles in degrees (+y down, so 90 is straight down)."""
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
            for k in range(n + 1)]


def rrect(r0, r1, hw, ang, c=(0, 0)):
    """A rectangle along the ray at ang (degrees) from radius r0 to r1, half-width hw."""
    t = math.radians(ang); ux, uy = math.cos(t), math.sin(t); vx, vy = -uy, ux
    return [(c[0] + ux * r + vx * w, c[1] + uy * r + vy * w) for r, w in ((r0, -hw), (r1, -hw), (r1, hw), (r0, hw))]


def voyager():
    """High-gain dish with its feed, the bus, two angled RTG booms and the long magnetometer boom."""
    g = Pen()
    g.ell((0, -0.40), 0.66, 0.26); g.ell((0, -0.40), 0.50, 0.17, on=False); g.ell((0, -0.40), 0.36, 0.10)
    g.line([(0, -0.40), (0, -0.82)], 0.04); g.disc((0, -0.86), 0.07)
    g.rect(-0.20, -0.14, 0.20, 0.16); g.rect(-0.10, -0.06, 0.10, 0.08, on=False)
    both(lambda s: g.line([(s * 0.18, 0.06), (s * 0.90, 0.56)], 0.035))
    both(lambda s: g.line([(s * 0.60, 0.35), (s * 0.86, 0.53)], 0.10))
    g.line([(0, 0.16), (0, 0.90)], 0.03); g.disc((0, 0.92), 0.05)
    return g.mask()


def dsn_dish():
    """The 70 m dish side-on: a bowl, its feed tripod, the elevation bearing, the pedestal with a door, the base."""
    g = Pen(); X = 0.94
    outer = [(x, -0.62 + 0.56 * (1 - (x / X) ** 2)) for x in np.linspace(-X, X, 61)]
    inner = [(x, -0.62 + 0.40 * (1 - (x / (X - 0.06)) ** 2)) for x in np.linspace(X - 0.06, -(X - 0.06), 61)]
    g.poly(outer + inner)
    both(lambda s: g.line([(s * 0.62, -0.42), (0, -0.90)], 0.035))
    g.line([(0, -0.24), (0, -0.90)], 0.035); g.disc((0, -0.90), 0.07)
    g.disc((0, -0.04), 0.13)
    g.poly([(-0.12, -0.02), (0.12, -0.02), (0.30, 0.72), (-0.30, 0.72)])
    g.poly([(-0.08, 0.72), (-0.08, 0.50), (0, 0.44), (0.08, 0.50), (0.08, 0.72)], on=False)
    g.rect(-0.62, 0.72, 0.62, 0.88)
    return g.mask()


def juno():
    """Juno: hexagonal bus with its high-gain dish, three long solar wings at 120 degrees (one straight up)."""
    g = Pen()
    for ang in (-90, 30, 150):
        g.poly(rrect(0.20, 0.95, 0.09, ang))
        for r in (0.45, 0.70): g.poly(rrect(r - 0.015, r + 0.015, 0.12, ang), on=False)
    g.poly(hexagon((0, 0), 0.24, math.pi / 6)); g.disc((0, 0), 0.15, on=False); g.disc((0, 0), 0.07)
    return g.mask()


def iss():
    """The station: the long truss, four solar array pairs, the module stack and its cross module."""
    g = Pen()
    g.rect(-0.95, -0.045, 0.95, 0.045)
    for x in (0.42, 0.74):
        for s in (1, -1):
            for y0, y1 in ((-0.66, -0.08), (0.08, 0.66)):
                g.rect(s * x - 0.12, y0, s * x + 0.12, y1); g.rect(s * x - 0.012, y0 + 0.04, s * x + 0.012, y1 - 0.04, on=False)
    g.rect(-0.09, -0.40, 0.09, 0.44); g.rect(-0.24, 0.20, 0.24, 0.32)
    g.disc((0, -0.40), 0.09)
    return g.mask()


def mars_rover():
    """A rover face-on: the mast and camera head, the deck, the body, rocker legs and two wheels a side."""
    g = Pen()
    g.rect(-0.045, -0.62, 0.045, -0.06); g.rect(-0.22, -0.82, 0.22, -0.60)
    both(lambda s: g.disc((s * 0.11, -0.71), 0.05, on=False))
    g.rect(-0.72, -0.08, 0.72, 0.04); g.rect(-0.46, 0.04, 0.46, 0.34)
    g.rect(-0.30, 0.12, 0.30, 0.18, on=False)
    def side(s):
        g.line([(s * 0.40, 0.22), (s * 0.66, 0.56)], 0.06)
        for x, r in ((0.76, 0.20), (0.40, 0.16)):
            g.disc((s * x, 0.70), r); g.disc((s * x, 0.70), r * 0.40, on=False)
    both(side)
    return g.mask()


def orbit_primary():
    """A primary inside one wide orbit, the planet riding the orbit's near (lower) point. One ring, not three,
    so it stays apart from the Bohr atom."""
    g = Pen()
    g.ell((0, 0), 0.95, 0.44); g.ell((0, 0), 0.88, 0.37, on=False)
    g.disc((0, 0), 0.34, on=False); g.disc((0, 0), 0.27)
    g.disc((0, 0.40), 0.17, on=False); g.disc((0, 0.40), 0.11)
    return g.mask()


def chip():
    """A packaged chip: body, a gap round the die, five pins a side."""
    g = Pen()
    g.rect(-0.56, -0.56, 0.56, 0.56); g.rect(-0.44, -0.44, 0.44, 0.44, on=False); g.rect(-0.30, -0.30, 0.30, 0.30)
    for y in (-0.40, -0.20, 0.0, 0.20, 0.40):
        g.rect(0.62, y - 0.05, 0.94, y + 0.05); g.rect(-0.94, y - 0.05, -0.62, y + 0.05)
        g.rect(y - 0.05, -0.94, y + 0.05, -0.62); g.rect(y - 0.05, 0.62, y + 0.05, 0.94)
    return g.mask()


def light_bulb():
    """A glass globe outline, the filament on two posts, the neck and a three-thread screw base."""
    g = Pen()
    g.disc((0, -0.30), 0.62); g.disc((0, -0.30), 0.50, on=False)
    g.poly([(-0.30, 0.14), (0.30, 0.14), (0.24, 0.52), (-0.24, 0.52)])
    both(lambda s: g.line([(s * 0.12, 0.16), (s * 0.12, -0.22)], 0.035))
    g.line([(-0.12, -0.22), (-0.06, -0.36), (0, -0.22), (0.06, -0.36), (0.12, -0.22)], 0.035)
    for y0, y1, w in ((0.56, 0.64, 0.24), (0.68, 0.76, 0.22), (0.80, 0.86, 0.18)): g.rect(-w, y0, w, y1)
    g.disc((0, 0.90), 0.06)
    return g.mask()


def water_molecule():
    """H2O: the oxygen above, two hydrogens at the real 104.5 degree bond angle, each atom ringed."""
    g = Pen(); O = (0, -0.22)
    both(lambda s: g.line([O, (s * 0.66, 0.30)], 0.13))
    g.disc(O, 0.46); g.ring(O, 0.20, 0.27, on=False)
    both(lambda s: (g.disc((s * 0.66, 0.30), 0.28), g.ring((s * 0.66, 0.30), 0.09, 0.14, on=False)))
    return g.mask()


def binary_tree():
    """A root, two children, four grandchildren: ringed nodes on straight edges."""
    g = Pen(); R = (0, -0.74); L1 = [(s * 0.46, -0.06) for s in (1, -1)]
    L2 = [(s * 0.76, 0.68) for s in (1, -1)] + [(s * 0.26, 0.68) for s in (1, -1)]
    for c in L1: g.line([R, c], 0.05)
    for s in (1, -1):
        for x in (0.76, 0.26): g.line([(s * 0.46, -0.06), (s * x, 0.68)], 0.05)
    for c in [R] + L1 + L2: g.disc(c, 0.17); g.disc(c, 0.08, on=False)
    return g.mask()


def bell_curve():
    """A filled normal curve on its baseline, cut by sigma lines at 1 and 2 standard deviations."""
    g = Pen(); sd = 0.28
    curve = [(x, 0.62 - 1.40 * math.exp(-x * x / (2 * sd * sd))) for x in np.linspace(-0.96, 0.96, 97)]
    g.poly(curve + [(0.96, 0.66), (-0.96, 0.66)])
    g.rect(-0.96, 0.66, 0.96, 0.74)
    for k in (1, 2):
        both(lambda s: g.line([(s * k * sd, 0.60), (s * k * sd, 0.62 - 1.40 * math.exp(-k * k / 2) + 0.06)], 0.03, on=False))
    return g.mask()


def gear():
    """Ten square teeth (one straight up), a rim, an open web and a free hub with its bore."""
    g = Pen()
    g.disc((0, 0), 0.70)
    for k in range(10): g.poly(rrect(0.55, 0.95, 0.10, -90 + 36 * k))
    g.disc((0, 0), 0.40, on=False); g.disc((0, 0), 0.20); g.disc((0, 0), 0.08, on=False)
    for k in range(6): g.poly(rrect(0.16, 0.44, 0.04, -90 + 60 * k))
    return g.mask()


def sun():
    """A disc with an inner ring, twelve pointed rays (one straight up)."""
    g = Pen()
    g.disc((0, 0), 0.42); g.ring((0, 0), 0.26, 0.31, on=False)
    for k in range(12):
        t = math.radians(-90 + 30 * k)
        g.poly([(0.52 * math.cos(t - 0.13), 0.52 * math.sin(t - 0.13)), (0.96 * math.cos(t), 0.96 * math.sin(t)),
                (0.52 * math.cos(t + 0.13), 0.52 * math.sin(t + 0.13))])
    return g.mask()


def mountain():
    """A main peak with a jagged snow line, two lower shoulder peaks with their ridges cut free."""
    g = Pen()
    both(lambda s: g.poly([(s * 0.26, 0.74), (s * 0.64, -0.26), (s * 0.98, 0.74)]))
    g.poly([(-0.86, 0.74), (0, -0.92), (0.86, 0.74)])
    g.line([(-0.24, -0.38), (-0.12, -0.28), (0, -0.42), (0.12, -0.28), (0.24, -0.38)], 0.04, on=False)
    both(lambda s: g.line([(s * 0.62, -0.20), (s * 0.40, 0.30)], 0.03, on=False))
    g.rect(-0.98, 0.80, 0.98, 0.88)
    return g.mask()


def tree():
    """A round canopy of three lobes, its branches showing as gaps, a flared trunk on a ground line."""
    g = Pen()
    g.disc((0, -0.44), 0.48); both(lambda s: g.disc((s * 0.52, -0.10), 0.42)); g.disc((0, -0.06), 0.42)
    g.line([(0, 0.18), (0, -0.56)], 0.04, on=False)
    both(lambda s: g.line([(0, -0.06), (s * 0.34, -0.40)], 0.035, on=False))
    both(lambda s: g.line([(0, 0.08), (s * 0.56, -0.02)], 0.035, on=False))
    g.poly([(-0.10, 0.22), (0.10, 0.22), (0.18, 0.88), (-0.18, 0.88)])
    g.rect(-0.52, 0.88, 0.52, 0.95)
    return g.mask()


def seed():
    """An almond seed with its seam, sprouting a stem and two veined leaves."""
    g = Pen()
    g.poly(spline([(0, -0.28), (0.40, -0.04), (0.46, 0.42), (0, 0.94), (-0.46, 0.42), (-0.40, -0.04)], 16))
    g.line([(0, -0.14), (0, 0.80)], 0.03, on=False)
    g.line([(0, -0.26), (0, -0.62)], 0.06)
    both(lambda s: g.poly([(s * x, y) for x, y in spline([(0.02, -0.60), (0.36, -0.94), (0.86, -0.84), (0.52, -0.56)], 12)]))
    both(lambda s: g.line([(s * 0.08, -0.62), (s * 0.66, -0.80)], 0.025, on=False))
    return g.mask()


def water_drop():
    """A teardrop (a circle and its tangent cone) with a curved highlight across its crown."""
    g = Pen(); c, r, apex = (0, 0.34), 0.58, (0, -0.96)
    phi = math.asin(r / (c[1] - apex[1])); a = math.pi / 2 - phi
    g.poly([apex, (r * math.sin(a), c[1] - r * math.cos(a)), (-r * math.sin(a), c[1] - r * math.cos(a))])
    g.disc(c, r)
    g.line(arc(c, 0.38, -145, -35, 24), 0.05, on=False)
    return g.mask()


def antlers():
    """A stag's pair: two curving beams from a brow plate, each with an outer pair of tines and an inner brow tine."""
    g = Pen()
    def beam(s):
        g.line([(s * x, y) for x, y in spline([(0.12, 0.66), (0.30, 0.30), (0.50, -0.10), (0.66, -0.50), (0.80, -0.90)], 10, closed=False)], 0.08)
        for a, b in (((0.30, 0.30), (0.70, 0.10)), ((0.50, -0.10), (0.92, -0.32)), ((0.64, -0.48), (0.44, -0.88)), ((0.40, 0.10), (0.16, -0.30))):
            g.line([(s * a[0], a[1]), (s * b[0], b[1])], 0.06)
    both(beam)
    g.ell((0, 0.74), 0.28, 0.16)
    return g.mask()


def arch():
    """A round Roman arch: two piers and a semicircle of voussoirs round a keystone, the opening left dark."""
    g = Pen(); c, R, r = (0, -0.06), 0.86, 0.46
    g.disc(c, R); g.rect(-R, c[1], R, 0.92)
    g.disc(c, r, on=False); g.rect(-r, c[1], r, 0.92, on=False)
    for a in (-165, -135, -105, -75, -45, -15):
        t = math.radians(a); g.line([(c[0] + r * math.cos(t), c[1] + r * math.sin(t)), (c[0] + R * math.cos(t), c[1] + R * math.sin(t))], 0.03, on=False)
    for y in (0.30, 0.62): both(lambda s: g.rect(s * r + (0.01 if s > 0 else -R), y - 0.015, (R if s > 0 else -r - 0.01), y + 0.015, on=False))
    return g.mask()


def ladder():
    """Two rails and five rungs."""
    g = Pen()
    both(lambda s: g.rect(min(s * 0.40, s * 0.53), -0.94, max(s * 0.40, s * 0.53), 0.94))
    for y in (-0.70, -0.35, 0.0, 0.35, 0.70): g.rect(-0.41, y - 0.05, 0.41, y + 0.05)
    return g.mask()


def pyramid():
    """A stepped-course pyramid: four courses with staggered block joints, on a ground line."""
    g = Pen()
    g.poly([(0, -0.92), (0.96, 0.80), (-0.96, 0.80)])
    for y in (-0.40, 0.0, 0.40): g.rect(-1, y - 0.02, 1, y + 0.02, on=False)
    joints = {(-0.38, 0.0): (0.0,), (0.02, 0.38): (0.30,), (0.42, 0.78): (0.0, 0.56)}
    for (y0, y1), xs in joints.items():
        for x in xs:
            for s in ((1, -1) if x else (1,)): g.rect(s * x - 0.02, y0, s * x + 0.02, y1, on=False)
    g.rect(-0.98, 0.84, 0.98, 0.90)
    return g.mask()


def balance():
    """A balance: post and foot, finial, the beam on its pivot, two deep pans hung on cords. Beam, post and cords are
    thick enough to keep a dot at 23 px (0.06 / 0.025 vanished there)."""
    g = Pen()
    g.rect(-0.08, -0.70, 0.08, 0.80); g.poly([(-0.46, 0.94), (0.46, 0.94), (0.24, 0.76), (-0.24, 0.76)])
    g.disc((0, -0.82), 0.11); g.line([(-0.74, -0.60), (0.74, -0.60)], 0.11); g.disc((0, -0.60), 0.11)
    def pan(s):
        top = (s * 0.70, -0.60)
        g.line([top, (s * 0.46, 0.10)], 0.05); g.line([top, (s * 0.94, 0.10)], 0.05)
        g.poly([(s * x, y) for x, y in arc((0.70, 0.10), 0.28, 0, 180, 24)])
    both(pan)
    return g.mask()


def bell():
    """A tower bell: crown loop, waisted body flaring to a lip, two band lines, the clapper below."""
    g = Pen()
    half = [(0, -0.72), (0.26, -0.66), (0.38, -0.40), (0.42, 0.0), (0.52, 0.34), (0.80, 0.58), (0.94, 0.70)]
    g.poly(half + [(-x, y) for x, y in reversed(half[1:])])
    g.ring((0, -0.80), 0.07, 0.15)
    g.line([(-0.70, 0.56), (0.70, 0.56)], 0.03, on=False); g.line([(-0.30, -0.30), (0.30, -0.30)], 0.03, on=False)
    g.disc((0, 0.84), 0.12)
    return g.mask()


def hourglass():
    """Top and bottom frames on two posts, the glass outline, the upper sand, its falling stream and the pile."""
    g = Pen()
    g.rect(-0.80, -0.96, 0.80, -0.84); g.rect(-0.80, 0.84, 0.80, 0.96)
    both(lambda s: g.rect(min(s * 0.66, s * 0.74), -0.84, max(s * 0.66, s * 0.74), 0.84))
    out = [(0.52, -0.84), (0.50, -0.56), (0.09, -0.05), (0.09, 0.05), (0.50, 0.56), (0.52, 0.84)]
    inn = [(0.44, -0.78), (0.42, -0.56), (0.035, -0.07), (0.035, 0.07), (0.42, 0.56), (0.44, 0.78)]
    g.poly(out + [(-x, y) for x, y in reversed(out)]); g.poly(inn + [(-x, y) for x, y in reversed(inn)], on=False)
    g.poly([(-0.28, -0.40), (0.28, -0.40), (0.03, -0.09), (-0.03, -0.09)])
    g.line([(0, 0.0), (0, 0.42)], 0.025); g.poly([(-0.42, 0.78), (0.42, 0.78), (0, 0.40)])
    return g.mask()


def _heater(k):
    right = [(0.80 * k, -0.92 * k)] + [(0.80 * k * math.cos(t * math.pi / 2), (-0.20 + 1.16 * math.sin(t * math.pi / 2)) * k + 0.02 * (1 - k))
                                       for t in np.linspace(0, 1, 33)]
    return right + [(-x, y) for x, y in reversed(right[:-1])]


def shield():
    """A heater shield with a border and a chevron."""
    g = Pen()
    g.poly(_heater(1.0)); g.poly(_heater(0.88), on=False); g.poly(_heater(0.80))
    g.line([(-0.52, 0.34), (0, -0.18), (0.52, 0.34)], 0.11, on=False)
    return g.mask()


def sword():
    """A point-down sword: pommel, grip, a crossguard with knobbed ends, the fullered blade."""
    g = Pen()
    g.poly([(-0.09, -0.40), (0.09, -0.40), (0.09, 0.70), (0, 0.96), (-0.09, 0.70)])
    g.line([(0, -0.32), (0, 0.66)], 0.03, on=False)
    g.rect(-0.42, -0.49, 0.42, -0.40); both(lambda s: g.disc((s * 0.44, -0.445), 0.07))
    g.rect(-0.05, -0.80, 0.05, -0.49); g.disc((0, -0.86), 0.09)
    return g.mask()


def wing_pair():
    """A heraldic vol: two raised wings, no bird, each cut into flight feathers along its trailing edge."""
    g = Pen()
    w = [(0.06, -0.10), (0.28, -0.50), (0.60, -0.80), (0.96, -0.94), (0.92, -0.52), (0.86, -0.10),
         (0.72, 0.30), (0.52, 0.64), (0.28, 0.86), (0.10, 0.40)]
    def wing(s):
        g.poly([(s * x, y) for x, y in spline(w, 14)])
        root = (0.12, 0.0)
        for tip in ((0.90, -0.36), (0.80, 0.06), (0.62, 0.44), (0.40, 0.72)):
            a = (root[0] + 0.45 * (tip[0] - root[0]), root[1] + 0.45 * (tip[1] - root[1]))
            g.line([(s * a[0], a[1]), (s * tip[0] * 1.02, tip[1] * 1.02)], 0.03, on=False)
        g.line([(s * x, y) for x, y in spline([(0.20, -0.18), (0.46, -0.30), (0.70, -0.40)], 8, closed=False)], 0.03, on=False)
    both(wing)
    return g.mask()


def ankh():
    """The ankh: an oval loop, flared crossbar, flared stem."""
    g = Pen()
    g.ell((0, -0.54), 0.30, 0.40); g.ell((0, -0.54), 0.16, 0.26, on=False)
    g.poly([(-0.62, -0.26), (-0.50, -0.18), (0.50, -0.18), (0.62, -0.26), (0.62, 0.10), (0.50, 0.02), (-0.50, 0.02), (-0.62, 0.10)])
    g.poly([(-0.10, -0.06), (0.10, -0.06), (0.22, 0.94), (-0.22, 0.94)])
    return g.mask()


def _heart(k):
    pts = []
    for i in range(160):
        t = 2 * math.pi * i / 160
        x = 16 * math.sin(t) ** 3; y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((x * 0.059 * k, (y - 2.5) * 0.059 * k + 0.04))
    return pts


def heart():
    """A heart with an inset border."""
    g = Pen(); g.poly(_heart(1.0)); g.poly(_heart(0.80), on=False); g.poly(_heart(0.68))
    return g.mask()


def anchor():
    """Ring, stock with knobbed ends, shank, curved arms ending in flukes, the crown."""
    g = Pen()
    g.ring((0, -0.80), 0.07, 0.15)
    g.rect(-0.06, -0.66, 0.06, 0.78)
    g.rect(-0.46, -0.58, 0.46, -0.48); both(lambda s: g.disc((s * 0.48, -0.53), 0.07))
    g.line(arc((0, 0.20), 0.66, 15, 165, 48), 0.09)
    both(lambda s: g.poly([(s * 0.66, 0.08), (s * 0.82, 0.46), (s * 0.48, 0.40)]))
    g.disc((0, 0.86), 0.08)
    return g.mask()


GLYPHS = [
    ("Mission Patches", [("Voyager", voyager), ("Golden Record", golden_record), ("DSN dish", dsn_dish), ("Juno", juno),
                         ("ISS", iss), ("JWST mirror", jwst), ("Mars rover", mars_rover), ("Orbit with primary", orbit_primary)]),
    ("Instrument Marks", [("Bohr atom", bohr), ("Chip", chip), ("Light bulb", light_bulb), ("Water molecule", water_molecule),
                          ("Binary tree", binary_tree), ("Bell curve", bell_curve), ("Neural net", neural_net), ("Gear", gear)]),
    ("Wild Signs", [("Sun", sun), ("Mountain", mountain), ("Tree", tree), ("Seed", seed), ("Water drop", water_drop),
                    ("Antlers", antlers), ("Butterfly", butterfly), ("Owl", owl)]),
    ("Made Marks", [("Arch", arch), ("Ladder", ladder), ("Lighthouse", lighthouse), ("Pyramid", pyramid), ("Target", target),
                    ("Balance", balance), ("Bell", bell), ("Hourglass", hourglass)]),
    ("Old Signs", [("Shield", shield), ("Sword", sword), ("Skull", skull), ("Wing pair", wing_pair), ("Phoenix", phoenix),
                   ("Ankh", ankh), ("Heart", heart), ("Anchor", anchor)]),
]


# ------------------------------------------------------------------ (a) contours
def contours(m, eps=0.35):
    f = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((F, F), Image.BOX)).astype(float) / 255
    ax = (F - 1) / 2
    loops = [l for l in marching(f) if len(l) > 8 and abs(area(l)) > 2.0]
    out = []
    for l in loops:
        xs = l[:, 0]
        r = rdp_closed(l, eps)
        if xs.min() < ax < xs.max():
            try:
                q = symmetrise(r, ax)
                if len(q) >= 3 and abs(abs(area(q)) / abs(area(r)) - 1) < 0.02: out.append(q); continue   # else symmetrise mis-cut it
            except Exception:
                pass
            out.append(r)                          # field is exactly symmetric, so the raw loop is too (to RDP)
        elif xs.mean() > ax:
            out.append(r); mir = r.copy(); mir[:, 0] = 2 * ax - mir[:, 0]; out.append(mir[::-1])
    iou_m = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((F, F), Image.BOX)) > 127
    rr = raster(out, F, F)
    iou = float((rr & iou_m).sum() / max(1, (rr | iou_m).sum()))
    to_u = lambda p: [[round((x - ax) / (F / 2), 4), round((y - ax) / (F / 2), 4)] for x, y in p]
    return [to_u(p) for p in out], iou


# ------------------------------------------------------------------ (b) dots
def dots(m, E):
    lat = LATTICE[E]; Ed = E * DPR / 2.0             # device px per unit
    ii = np.pad(m.astype(np.float64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    sp = (S / 2) / Ed                                 # source px per device px
    def cov(xd, yd):
        x0 = int(round((xd - lat["px"] / 2) * sp + S / 2)); x1 = int(round((xd + lat["px"] / 2) * sp + S / 2))
        y0 = int(round((yd - lat["py"] / 2) * sp + S / 2)); y1 = int(round((yd + lat["py"] / 2) * sp + S / 2))
        x0, x1, y0, y1 = max(0, x0), min(S, x1), max(0, y0), min(S, y1)
        if x1 <= x0 or y1 <= y0: return 0.0
        return (ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]) / ((x1 - x0) * (y1 - y0))
    lit = {}
    nr = int(Ed / lat["py"]) + 2; nc = int(Ed / lat["px"]) + 2
    for r in range(-nr, nr + 1):
        off = lat["off"] if r % 2 else 0
        for c in range(0, nc + 1):
            x = off + c * lat["px"]
            if x > Ed + lat["px"]: break
            y = r * lat["py"]
            if cov(x, y) > 0.5:
                lit[(x, y)] = 1
                if x: lit[(-x, y)] = 1
    pts = []
    for (x, y) in lit:
        nb = [(x + lat["px"], y), (x - lat["px"], y)] + [(x + dx, y + dy) for dy in (-lat["py"], lat["py"])
              for dx in ((-lat["off"], lat["off"]) if lat["off"] else (-lat["px"], 0, lat["px"]))]
        edge = any(n not in lit for n in nb)
        pts.append([x, y, 1 if edge else 0])
    pts.sort(key=lambda p: (p[1], p[0]))
    return pts


# ------------------------------------------------------------------ per-species tables for the live stage
# species -> (piece id, JS global, file stem, drawing style by the owner's ruling of 2026-11-07)
SPECIES = {
    "Mission Patches": ("c7_patches", "MISSION_PATCHES", "mission_patches", "vector"),
    "Instrument Marks": ("c8_instruments", "INSTRUMENT_MARKS", "instrument_marks", "vector"),
    "Wild Signs": ("c9_wild", "WILD_SIGNS", "wild_signs", "vector"),
    "Made Marks": ("c10_made", "MADE_MARKS", "made_marks", "dots"),
    "Old Signs": ("c11_old", "OLD_SIGNS", "old_signs", "vector"),
}


def _key(x, y): return (round(x * 1e4), round(y * 1e4))


def sym_loop(l):
    """Make one unit-box loop exactly mirror-symmetric about x = 0 (point-set test in tests/test_vector_glyphs.py).
    A loop that already is (an off-axis twin, or an axis-crossing loop that came out exact) is returned as is; otherwise
    keep the half on x >= 0 between its two axis crossings and reflect it. Off-axis loops are left to their twins."""
    S = {_key(x, y) for x, y in l}
    if all(_key(-x, y) in S for x, y in l): return l
    n = len(l)
    cr = [k for k in range(n) if l[k][0] * l[(k + 1) % n][0] <= 0 and not (l[k][0] == 0 and l[(k + 1) % n][0] == 0)]
    if len(cr) != 2: return l

    def at(k):                                      # the axis point on segment k -> k+1
        a, b = l[k], l[(k + 1) % n]
        if a[0] == b[0]: return [0.0, a[1]]
        t = (0 - a[0]) / (b[0] - a[0]); return [0.0, round(a[1] + t * (b[1] - a[1]), 4)]
    c0, c1 = cr
    side = [l[(k) % n] for k in range(c0 + 1, c1 + 1)] if c1 > c0 else []
    if not side or sum(p[0] for p in side) < 0:
        side = [l[k % n] for k in range(c1 + 1, c0 + 1 + n)]; c0, c1 = c1, c0
    half = [at(c0)] + [[abs(p[0]), p[1]] for p in side if p[0] != 0] + [at(c1)]
    out = half + [[-x, y] for x, y in reversed(half[1:-1])]
    return [[round(x, 4) + 0.0, round(y, 4)] for x, y in out]


def write_species(sp, glyphs):
    cid, glob, stem, style = SPECIES[sp]
    out = SPR / f"prototype/vector/glyphs_{stem}_vector.js"
    ent = []
    for name, g in glyphs:
        d = {"loops": [sym_loop(l) for l in g["loops"]], "lo": [sym_loop(l) for l in g["lo"]]}
        if style == "dots":
            d["dots"] = {str(E): {"d": LATTICE[E]["dot"], "p": [v for pt in g["dots"][str(E)] for v in pt]} for E in LATTICE}
        ent.append(f"  [{json.dumps(name)}, {json.dumps(d, separators=(',', ':'))}]")
    hdr = "\n".join(f" *   {n:<14} IoU of outline vs source {g['iou']}" for n, g in glyphs)
    js = (f"/* GENERATED by tools/species_glyph_sources.py -- do not edit by hand; re-run the script.\n"
          f" * {sp} (species {cid}), drawn by prototype/vector/engine.js in {style.upper()} style (owner's ruling, 2026-11-07).\n"
          f" * All {len(glyphs)} glyphs of the docs/SYMBOL_SPECIES.md roster, in roster order. To change one, edit GLYPHS in\n"
          f" * tools/species_glyph_sources.py and re-run.\n"
          f" * Not trademark-bearing: generic, programmatically drawn marks (unlike Night Signals' glyphs_night_vector.js). Identity only.\n"
          f" * Format as glyphs_night_vector.js: unit box, closed loops, exact mirror symmetry about x = 0 (tests/test_vector_glyphs.py)"
          + (";\n * dots: per lattice level {d: dot edge in device px, p: [dx, dy, edge, ...] device px from the centre at dpr 2}" if style == "dots" else "") +
          f"\n{hdr}\n */\n"
          f"this.SPRITES_GLYPHS_{glob}_VECTOR = [\n" + ",\n".join(ent) + "\n];\n")
    out.write_text(js); print("wrote", out, f"{len(js) // 1024} KB")


def main():
    src = storage() / "sprites/species_style_sources"; src.mkdir(parents=True, exist_ok=True)
    data, stats, tables = {}, {}, {}
    for sp, glyphs in GLYPHS:
        for name, fn in glyphs:
            m = fn()
            assert (m == m[:, ::-1]).all()
            Image.fromarray(m.astype(np.uint8) * 255).save(src / f"{name.replace(' ', '_')}.png")
            loops, iou = contours(m)
            lo, _ = contours(m, 1.2)
            d = {str(E): dots(m, E) for E in LATTICE}
            data[name] = {"species": sp, "loops": loops, "dots": d}
            tables.setdefault(sp, []).append((name, {"loops": loops, "lo": lo, "iou": round(iou, 4), "dots": d}))
            stats[name] = {"iou": round(iou, 4), "loops": len(loops), "points": sum(len(l) for l in loops),
                           "dots": {E: len(v) for E, v in d.items()}}
            print(name, json.dumps(stats[name]), flush=True)
    js = ("/* GENERATED by tools/species_glyph_sources.py -- do not edit by hand.\n"
          " * Species-style sample glyphs: unit-box vector loops (x,y in -1..1, +y down, mirror-symmetric) and,\n"
          " * per render extent E (CSS px), dot lattices as [dx, dy, edge] in DEVICE px (dpr 2) from the centre.\n"
          f" * Lattices (device px): {json.dumps(LATTICE)}\n"
          " * EXPERIMENT ONLY: nothing in app/ or tests/ loads this file. Form carries no data. */\n"
          "this.SPRITES_SPECIES_GLYPHS = " + json.dumps(data, separators=(",", ":")) + ";\n"
          "this.SPRITES_SPECIES_GLYPH_STATS = " + json.dumps(stats, separators=(",", ":")) + ";\n")
    OUT_JS.write_text(js)
    for sp, glyphs in tables.items(): write_species(sp, glyphs)
    print("sources", src); print("wrote", OUT_JS, f"{len(js) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
