#!/usr/bin/env python3
"""Build the symbol x arm comparison grid for docs/SYMBOL_RESOLUTION.md.

  python3 -I prototype/experiments/resolution/render_comparison.py

Writes to <agent storage>/sprites/symbol-resolution-comparison/ -- large artifacts never go in git.
Deterministic: one synthetic live message, a fixed number of simulation steps, then a screenshot of
the sprite's reported position, so re-running gives the same pixels. Renders at device resolution (dpr 2) and lays out:
  - a 1:1 panel at the size the sprite actually appears on screen
  - a 2x nearest-neighbour detail crop of the same pixels, since the complaint is perceived resolution
Arm A is the SHIPPED renderer untouched; B and C are the experiment pages."""
import functools, http.server, socketserver, threading, math, json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

SPR = Path(__file__).resolve().parents[3]          # the sprites repo root
# agent storage root, per the machine's own helper; never a hardcoded path
def _storage():
    import subprocess
    h = Path.home()/"dev/Lodestar/bin/lib/agent_storage.py"
    if h.exists():
        try: return Path(subprocess.check_output([sys.executable, "-I", str(h)], text=True).strip())
        except Exception: pass
    return Path.home()/"agent-storage"
OUT = _storage()/"sprites/symbol-resolution-comparison"
OUT.mkdir(parents=True, exist_ok=True)
STILLS = OUT/"stills"; STILLS.mkdir(exist_ok=True)

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
h = functools.partial(Quiet, directory=str(SPR))
srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), h); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
PORT = srv.server_address[1]
W, H = 1920, 1080
DPR = 2

ARMS = [
 ("A", "A - current (9x9, glow as shipped)",
  "prototype/c6_night.html", ""),
 ("B", "B - tightened LED (15x15, blob 1.2x, hard core)",
  "prototype/experiments/resolution/armB_led15.html", "&n=15&blob=1.2&core=0.9&floor=1"),
 ("C", "C - vector paths (arc / lineTo / bezier)",
  "prototype/experiments/resolution/armC_vector.html", ""),
]
SYMS = [("Batman", 0), ("TARDIS", 4), ("Cog", 7)]
# the state the owner actually watches: a working session with traffic, at the max size slider (his
# words: "the largest end of what should be permitted"), plus the small idle case for the honest floor
CASES = [
 ("work", 2.0, 0.8, "working", 0.9, 8.0, 3.0, "working, 8/3 Mbit/s, size 200%"),
 ("idle", 1.0, 0.33, "idle", 0.03, 0.0, 0.0, "idle, no traffic, size 100%"),
]
def msg(iv, mem, state, cpu, rx, tx):
    return {"cmd":"live","sessions":[{"id":"s1","hue":200,"iv":iv,"ghost":False,"white":False}],
      "S":{"s":{"s1":{"state":state,"cpu":cpu,"mem":mem,"procs":5,"rx":rx,"tx":tx}},
           "m":{"level":0.3,"thermal":0,"mempress":0},
           "net":{"mbps":14,"vpn":"up","loss":0,"strain":0},"play":{"pair":["",""],"amt":0}}}

def font(sz, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

shots = {}   # (case, arm, sym) -> (path, css_extent_px)
errors = []
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for cname, slider, mem, state, cpu, rx, tx, caption in CASES:
        SZ = slider*0.5*min(W/1280, H/800)
        E  = 9*6*math.sqrt(max(0.2,min(2.6,mem))/0.8)*SZ
        R  = E*0.62 + 9*SZ + 16                       # crop radius: glyph + satellites + halo margin
        for arm, _label, page, extra in ARMS:
            for sym, iv in SYMS:
                pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=DPR)
                pg.on("pageerror", lambda e, a=arm, s=sym: errors.append(f"{a}/{s}: {e}"))
                pg.goto(f"http://127.0.0.1:{PORT}/{page}?live=1&w={W}&h={H}&dpr={DPR}&size={slider}&top=26&bot=86{extra}")
                pg.wait_for_function("typeof window.__live === 'function'", timeout=20000)
                pg.evaluate("document.documentElement.style.background='#0b0d12'")
                rep = pg.evaluate("m => window.__live(m, 300)", msg(iv, mem, state, cpu, rx, tx))
                if rep.get("errors"): errors.extend(f"{arm}/{sym}: {e}" for e in rep["errors"])
                r = rep["reports"]["s1"]
                fn = STILLS/f"{cname}_{arm}_{sym}.png"
                pg.screenshot(path=str(fn), clip={"x": r["x"]-R, "y": r["y"]-R, "width": 2*R, "height": 2*R})
                shots[(cname, arm, sym)] = (fn, 2*R)
                pg.close()
        print(f"{cname}: E={E:.1f} CSS px, pitch9={E/9:.2f}, pitch15={E/15:.2f}, crop={2*R:.0f} CSS", flush=True)
    b.close()
if errors:
    print("PAGE ERRORS:", errors, file=sys.stderr)

BG=(11,13,18); FG=(226,232,243); DIM=(150,163,184); RULE=(44,52,66)
def build(cname, caption, detail):
    """One grid: rows = symbol, cols = arm. detail=False -> 1:1 at screen size; True -> 2x crop."""
    cell_pad, lab_h, hdr_h, left = 14, 0, 72, 150
    # 1:1 means: the shot is DPR x CSS; display it at CSS size so it matches the screen
    d0 = ImageDraw.Draw(Image.new("RGB",(8,8)))
    panels = {}
    for (c,a,s),(fn,css) in shots.items():
        if c != cname: continue
        im = Image.open(fn).convert("RGB")
        if detail:
            # centre half, then 2x nearest -> twice screen size, no resampling softness invented
            w,hh = im.size; q = int(min(w,hh)*0.36)
            im = im.crop(((w-2*q)//2,(hh-2*q)//2,(w+2*q)//2,(hh+2*q)//2))
            im = im.resize((im.width*2, im.height*2), Image.NEAREST)
        else:
            im = im.resize((int(css), int(css)), Image.LANCZOS)   # device px -> CSS px = on-screen size
        panels[(a,s)] = im
    cw = max(p.width for p in panels.values()); ch = max(p.height for p in panels.values())
    # the header label must fit the column, or the three labels overlap (they did, at screen size)
    f_h0 = font(13)
    cw = max(cw, max(int(d0.textlength(l, font=f_h0)) for _a,l,_p,_e in ARMS) + 12)
    Wimg = left + 3*(cw+cell_pad) + cell_pad
    Himg = hdr_h + 3*(ch+cell_pad) + cell_pad + 34
    img = Image.new("RGB", (Wimg, Himg), BG); d = ImageDraw.Draw(img)
    f_t, f_h, f_s, f_c = font(19, True), font(13), font(14, True), font(12)
    title = ("2x DETAIL CROP - " if detail else "AT SCREEN SIZE - ") + caption
    d.text((cell_pad, 10), title, font=f_t, fill=FG)
    d.text((cell_pad, 36), "arms across, symbols down. Rendered at device resolution (scale 2.0) on a 1920x1080@2x screen."
           + ("  Pixels magnified 2x, nearest-neighbour: no detail invented." if detail else "  Shown 1:1, exactly as it appears on the desktop."),
           font=f_c, fill=DIM)
    for i,(arm,label,_p,_e) in enumerate(ARMS):
        x = left + i*(cw+cell_pad) + cell_pad
        d.text((x, hdr_h-22), label, font=f_h, fill=FG)
        d.line([(x-cell_pad//2, hdr_h-4),(x+cw+cell_pad//2, hdr_h-4)], fill=RULE)
    for j,(sym,_iv) in enumerate(SYMS):
        y = hdr_h + j*(ch+cell_pad) + cell_pad
        d.text((cell_pad, y+ch//2-8), sym, font=f_s, fill=FG)
        for i,(arm,_l,_p,_e) in enumerate(ARMS):
            x = left + i*(cw+cell_pad) + cell_pad
            p = panels[(arm,sym)]
            px, py = x + (cw-p.width)//2, y + (ch-p.height)//2
            d.rectangle([x-1, y-1, x+cw, y+ch], outline=RULE)
            img.paste(p, (px, py))
    d.text((cell_pad, Himg-26), "Arm A is the shipped renderer, unmodified. B and C are experiment pages "
           "(prototype/experiments/resolution/); the live app renders A.", font=f_c, fill=DIM)
    return img

parts = []
for cname,_s,_m,_st,_c,_rx,_tx,caption in CASES:
    for detail in (False, True):
        im = build(cname, caption, detail)
        fn = OUT/f"grid_{cname}_{'detail2x' if detail else 'screen'}.png"
        im.save(fn); parts.append(im); print("wrote", fn)
# one image he can open: all four grids stacked
Wt = max(p.width for p in parts); Ht = sum(p.height for p in parts) + 16*(len(parts)-1)
sheet = Image.new("RGB",(Wt,Ht),BG); y=0
for p in parts:
    sheet.paste(p,(0,y)); y += p.height + 16
big = OUT/"SYMBOL_RESOLUTION_COMPARISON.png"
sheet.save(big)
print("COMPARISON:", big, sheet.size)
