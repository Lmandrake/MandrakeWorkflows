#!/usr/bin/env python3
"""Species style samples: which drawing style suits each planned symbol species (owner, 2026-11-07).

  python3 tools/species_glyph_sources.py        # regenerate the 2048 px sources + species_glyphs.js
  python3 tools/build_species_style_samples.py

Two glyphs per species (Mission Patches, Instrument Marks, Wild Signs, Made Marks, Old Signs), each rendered
by real headless Chromium on prototype/experiments/resolution/species_styles.html at dpr 2, idle, hue 200, in
two styles: (a) crisp vector edges (Choir idiom) and (b) fine hard dots filling the silhouette, at glyph
extent 23, 64 and 256 CSS px. Panels are the screenshot's own device pixels; 23 px is magnified 4x nearest,
64 px 2x, 256 px 1x. Sequential renders, one browser (no load test).

Writes <agent storage>/sprites/symbol-resolution-comparison/SPECIES_STYLE_SAMPLES.png and every panel crop in
species_styles/ beside it. Uses grid() from tools/build_symbol_comparison.py (import only).
"""
import functools, http.server, socketserver, subprocess, sys, threading
from pathlib import Path
from PIL import Image, ImageDraw

SPR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPR / "tools"))
from build_symbol_comparison import grid, font, BG, FG, DIM, ACC   # noqa: E402  (import only)
from species_glyph_sources import GLYPHS                          # noqa: E402

PAGE = "prototype/experiments/resolution/species_styles.html"
SIZES = (23, 64, 256)
MAG = {23: 4, 64: 2, 256: 1}
DPR = 2

# One line per species, written AFTER looking at the renders. The split that decides it is line-shaped vs mass-shaped
# glyphs, not engineered vs organic: dots fill masses well and break lines into beads.
VERDICT = {
    "Mission Patches": "VERDICT: vector. The record's grooves and the 18 hex rims stay distinct; in dots the grooves turn to moire and at 23 px the mirror is a lumpy disc.",
    "Instrument Marks": "VERDICT: vector. Orbits and network links are lines by nature; dots break them into scattered beads, and at 23 px the atom and the net fall apart.",
    "Wild Signs": "VERDICT: dots. Filled wings and owl body read as a solid creature at every size, even 23 px (owl's eyes only from 64 up); vector reads, but as a line drawing.",
    "Made Marks": "VERDICT: vector, narrowly. Both read at every size; dots make the lighthouse a bold silhouette but blur the target's crosshair gaps at 23 px.",
    "Old Signs": "VERDICT: dots. Skull and phoenix read as bold carved silhouettes at all three sizes; vector at 23 px turns the teeth and feathers to scribble.",
}
import sys as _sys; from pathlib import Path as _P; _sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "tests/tools")); import load_rule  # owner rule: renders are load

def storage():
    h = Path.home() / "dev/Lodestar/bin/lib/agent_storage.py"
    return Path(subprocess.check_output([sys.executable, str(h)], text=True).strip())


OUT = storage() / "sprites/symbol-resolution-comparison"
CROPS = OUT / "species_styles"; CROPS.mkdir(parents=True, exist_ok=True)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def serve():
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(SPR)))
    srv.daemon_threads = True; threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


def slug(s): return s.replace(" ", "_")


def render(errors):
    from playwright.sync_api import sync_playwright
    port = serve(); shots = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(); print("chromium", b.version, flush=True)
        pg = b.new_page(viewport={"width": 400, "height": 400}, device_scale_factor=DPR)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        for _sp, glyphs in GLYPHS:
            for name, _fn in glyphs:
                for st in ("vec", "dot"):
                    for E in SIZES:
                        pg.goto(f"http://127.0.0.1:{port}/{PAGE}?g={name}&s={st}&E={E}&hue=200")
                        pg.wait_for_function("window.__done === true", timeout=20000)
                        fn = CROPS / f"{slug(name)}_{st}_{E}.png"
                        pg.locator("#c").screenshot(path=str(fn))
                        shots[(name, st, E)] = fn
        b.close()
    return shots


def main():
    load_rule.require()   # only on on-site network without the VPN; unknown = refuse
    errors = []
    shots = render(errors)
    if errors: print("PAGE ERRORS:", errors[:5], file=sys.stderr); sys.exit(1)
    cols = [(f"{st}{E}", f"{'vector' if st == 'vec' else 'dots'} {E} px ({MAG[E]}x)") for st in ("vec", "dot") for E in SIZES]
    parts = []
    for sp, glyphs in GLYPHS:
        cells = {}
        for name, _fn in glyphs:
            for st in ("vec", "dot"):
                for E in SIZES:
                    im = Image.open(shots[(name, st, E)]).convert("RGB")
                    if MAG[E] > 1: im = im.resize((im.width * MAG[E], im.height * MAG[E]), Image.NEAREST)
                    im.save(CROPS / f"{slug(name)}_{st}_{E}_sheet.png"); cells[(name, f"{st}{E}")] = im
        g = grid(sp.upper(), "", cols, [(n, n) for n, _ in glyphs], cells)
        part = Image.new("RGB", (g.width, g.height + 44), BG); part.paste(g, (0, 0))
        ImageDraw.Draw(part).text((16, g.height + 4), VERDICT[sp], font=font(24, True), fill=ACC)
        parts.append(part)
    head_h = 92
    Wt = max(p.width for p in parts); Ht = head_h + sum(p.height for p in parts) + 18 * len(parts)
    sheet = Image.new("RGB", (Wt, Ht), BG); d = ImageDraw.Draw(sheet)
    d.text((16, 12), "SPECIES STYLE SAMPLES - (a) crisp vector edges vs (b) fine hard dots, idle, hue 200", font=font(30, True), fill=FG)
    d.text((16, 52), "Real Chromium canvas renders, dpr 2, additive on #0b0d12. Panels are device pixels: 23 px glyphs magnified 4x nearest, "
                     "64 px 2x nearest, 256 px 1:1. Vector: hairline strokes (1 device px at 23, 1 CSS px at 64, 2 CSS px at 256), no fill. "
                     "Dots: whole-device-pixel squares filling the silhouette (1 dev px dots on a 2 px lattice at 23, 2 px on 4x3 at 64, 4 px on 6x5 at 256), edge dots brighter, no halo.",
           font=font(15), fill=DIM)
    y = head_h
    for p in parts: sheet.paste(p, (0, y)); y += p.height + 18
    fn = OUT / "SPECIES_STYLE_SAMPLES.png"; sheet.save(fn); print("SHEET:", fn, sheet.size)


if __name__ == "__main__":
    main()
