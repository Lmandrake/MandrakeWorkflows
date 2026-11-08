#!/usr/bin/env python3
"""Render sheets for an outside art and perception review of the Sprites encoding (docs/GRAMMAR_V2.md).

  python3 tools/build_art_review_sheets.py [--only 01a,01b,01c,02,03,04,05]

Writes to <agent storage>/sprites/art-review/: one PNG per sheet (text legend burned in) plus a companion
.md with the same text, stills/ (raw shots), and METRICS.json (every per-cell measurement). Large derived
artifacts never go in git; this script is their provenance.

Every still is the real runtime fed through its live hook: a fresh page at ?live=1 (2560x1440 CSS, dpr 2,
the owner's 2x screens), `window.__live(msg, n)` with a synthetic Augur-shaped message (the same shape
app/stage.html posts), n fixed 60 Hz steps, then a screenshot. Nothing is faked or drawn by hand: a sheet
cell is the page's own device pixels on black, cropped (never rescaled) unless its caption says otherwise.
Filmstrips continue the same simulation 6 steps (0.1 s) per frame.
"""
import argparse, colorsys, json, math, subprocess, sys, textwrap
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageCms
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_symbol_comparison as bsc  # noqa: E402  (serve(), font(), the fine-jelly tune, the bat assets)

SPR = Path(__file__).resolve().parents[1]
OUT = bsc.ROOT / "art-review"; STILLS = OUT / "stills"
for d in (OUT, STILLS): d.mkdir(parents=True, exist_ok=True)
SRC_CMP = bsc.OUT                                   # the symbol-resolution comparison's outputs (read only)
W, H = 2560, 1440
BG = (0, 0, 0); FG = (232, 236, 244); DIM = (150, 160, 178); RULE = (48, 54, 66); ACC = (255, 214, 90)
HUE = 150                                            # ladder hue: green, clear of rx blue, tx gold and ember red

JELLY = ("prototype/c2_siphon.html", f"window.SPRITES_JELLY_TUNE = {json.dumps(bsc.JELLY_FINE)};", "Siphonophores (fine-dot jellyfish)")
JELLY_SHIP = ("prototype/c2_siphon.html", None, "Siphonophores (as shipped)")
CHOIR = ("prototype/c1_choir.html", None, "Choir")
SIGILS = ("prototype/c3_sigils.html", None, "Living Sigils")
KALEI = ("prototype/c4_kaleido.html", None, "Kaleidoscope")
FIRE = ("prototype/c5_fireflies.html", None, "Fireflies")
NIGHT = ("prototype/c6_night.html", None, "Night Signals vector (d995c41)")
NIGHT_OLD = ("OLD:prototype/c6_night.html", None, "Night Signals 9x9 (before vector, 4cac820)")
NIGHT_C2 = ("prototype/experiments/resolution/armC_edge.html", None, "Night Signals vector prototype (round-2 arm C2)")

METRICS = {}


def M(state="working", cpu=0.9, mem=0.8, procs=4, rx=0.0, tx=0.0, level=0.0, thermal=0.0, mempress=0.0,
      strain=0.0, hue=HUE, iv=0, vpn="up"):
    """One live message, the shape app/stage.html posts from the Augur feed."""
    return {"cmd": "live", "sessions": [{"id": "s1", "hue": hue, "iv": iv, "ghost": False, "white": False}],
            "S": {"s": {"s1": {"state": state, "cpu": cpu, "mem": mem, "procs": procs, "rx": rx, "tx": tx}},
                  "m": {"level": level, "thermal": thermal, "mempress": mempress},
                  "net": {"mbps": rx + tx, "vpn": vpn, "loss": 0, "strain": strain}, "play": {"pair": ["", ""], "amt": 0}}}


ERR = []
OLDPORT = None
OLDTREE = OUT / "old_tree/sprites"   # `git archive 4cac820 sprites` (before the vector Night Signals), for the before/after


def serve_old():
    import functools, http.server, socketserver, threading
    if not OLDTREE.exists():
        OLDTREE.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(f"git -C {SPR.parent} archive 4cac820 sprites | tar -x -C {OLDTREE.parent}", shell=True, check=True)
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(bsc.Quiet, directory=str(OLDTREE)))
    srv.daemon_threads = True; threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]
HW, UP, DN = 380, 300, 460                          # fixed CSS box around the reported position


def shoot(b, port, sp, size, seq, name, dpr=2, extra="", frames=0, step=6):
    """seq = [(msg, ticks), ...] fed in order. Returns (images, report). Each image is a fixed-size canvas
    centred on the creature's reported position (so crops of one row share a frame), black outside the page."""
    page, init, _ = sp
    if page.startswith("OLD:"): page = page[4:]; port = OLDPORT
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=dpr)
    pg.on("pageerror", lambda e: ERR.append(f"{name}: {e}"))
    if init: pg.add_init_script(init)
    pg.goto(f"http://127.0.0.1:{port}/{page}?live=1&w={W}&h={H}&dpr={dpr}&top=26&bot=86&size={size:.5f}{extra}")
    pg.wait_for_function("typeof window.__live === 'function'", timeout=20000)
    pg.evaluate("document.documentElement.style.background='#000'; document.body.style.background='#000'")
    for m, n in seq:
        rep = pg.evaluate("([m, n]) => window.__live(m, n)", [m, n])
        if rep.get("errors"): ERR.extend(f"{name}: {e}" for e in rep["errors"])
    ims = []
    for k in range(max(1, frames)):
        if k: rep = pg.evaluate(f"window.__live(null, {step})")
        r = rep["reports"]["s1"]; k_ = max(0.35, size)
        x0, y0, x1, y1 = r["x"] - HW * k_, r["y"] - UP * k_, r["x"] + HW * k_, r["y"] + DN * k_
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        fn = STILLS / (f"{name}.png" if frames <= 1 else f"{name}_f{k}.png")
        pg.screenshot(path=str(fn), clip={"x": cx0, "y": cy0, "width": cx1 - cx0, "height": cy1 - cy0})
        canvas = Image.new("RGB", (int(round((x1 - x0) * dpr)), int(round((y1 - y0) * dpr))), BG)
        canvas.paste(Image.open(fn).convert("RGB"), (int(round((cx0 - x0) * dpr)), int(round((cy0 - y0) * dpr))))
        ims.append(canvas)
    pg.close()
    return ims, r


# ---------------------------------------------------------------- measurement
def lin(a): return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def metrics(im, thr=20):
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    mx = a.max(axis=2); lit = mx > thr; n = int(lit.sum())
    s = a / 255.0; Y = (0.2126 * lin(s[..., 0]) + 0.7152 * lin(s[..., 1]) + 0.0722 * lin(s[..., 2]))
    hsv = np.asarray(im.convert("RGB").convert("HSV")).astype(np.float32)
    Hh, S, V = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
    rx = lit & (Hh >= 182) & (Hh <= 228) & (V > 0.6) & (S > 0.08)
    tx = lit & (Hh >= 28) & (Hh <= 60) & (S > 0.4) & (V > 0.5)
    red = lit & ((Hh <= 18) | (Hh >= 342)) & (S > 0.45) & (V > 0.22)
    gx = np.abs(np.diff(V, axis=1)); gy = np.abs(np.diff(V, axis=0))
    g = np.concatenate([gx.ravel(), gy.ravel()])
    p_v = float(np.percentile(V[lit], 99.5)) if n else 0.0; p_g = float(np.percentile(g[g > 0], 99.5)) if (g > 0).any() else 0.0
    sh = np.histogram(S[lit], bins=10, range=(0, 1))[0] if n else np.zeros(10, int)
    return {"lit_px": n, "peak_Y": round(float(Y.max()), 4), "max_channel": int(a.max()),
            "frac_V_gt_0.8": round(float((V[lit] > 0.8).mean()), 4) if n else 0,
            "frac_clipped": round(float((a[lit].max(axis=1) >= 254.5).mean()), 4) if n else 0,
            "mean_S_lit": round(float(S[lit].mean()), 3) if n else 0,
            "frac_S_gt_0.8": round(float((S[lit] > 0.8).mean()), 4) if n else 0,
            "sat_hist": (sh / max(1, n)).round(4).tolist(),
            "rx_px": int(rx.sum()), "tx_px": int(tx.sum()), "red_px": int(red.sum()),
            "edge_width_px": round(p_v / p_g, 2) if p_g else None}


def framediff(ims, thr=20):
    a = [np.asarray(i.convert("L")).astype(np.float32) for i in ims]
    lit = np.zeros_like(a[0], bool)
    for x in a: lit |= x > thr
    if not lit.any(): return 0.0
    return round(float(np.mean([np.abs(a[k + 1] - a[k])[lit].mean() for k in range(len(a) - 1)])), 2)


# ---------------------------------------------------------------- layout
def font(sz, bold=False): return bsc.font(sz, bold)


def union_box(ims, pad=14, thr=14):
    box = None
    for im in ims:
        m = np.asarray(im.convert("RGB")).max(axis=2) > thr; ys, xs = np.nonzero(m)
        if not len(xs): continue
        bb = [xs.min(), ys.min(), xs.max(), ys.max()]
        box = bb if box is None else [min(box[0], bb[0]), min(box[1], bb[1]), max(box[2], bb[2]), max(box[3], bb[3])]
    w, h = ims[0].size
    if box is None: return (0, 0, w, h)
    return (max(0, box[0] - pad), max(0, box[1] - pad), min(w, box[2] + pad), min(h, box[3] + pad))


def wrap(d, text, f, width):
    out = []
    for para in text.split("\n"):
        words, line = para.split(" "), ""
        for w_ in words:
            t = (line + " " + w_).strip()
            if d.textlength(t, font=f) <= width: line = t
            else: out.append(line); line = w_
        out.append(line)
    return out


class Sheet:
    """Accumulates blocks (images) and the text that is both burned in and written to the companion .md."""
    def __init__(self, key, title, intro):
        self.key, self.title, self.intro, self.blocks, self.md = key, title, intro, [], [f"# {title}", "", intro, ""]

    def text_block(self, heading, body, width):
        f_h, f_b = font(24, True), font(18)
        d0 = ImageDraw.Draw(Image.new("RGB", (8, 8))); lines = wrap(d0, body, f_b, width - 40)
        im = Image.new("RGB", (width, 50 + 25 * len(lines) + 16), BG); d = ImageDraw.Draw(im)
        d.text((20, 10), heading, font=f_h, fill=ACC)
        for i, l in enumerate(lines): d.text((20, 46 + 25 * i), l, font=f_b, fill=FG)
        self.blocks.append(im); self.md += [f"## {heading}", "", body, ""]

    def row_table(self, heading, sub, cols, rows, scale=1.0, md_rows=None):
        """cols: [header]; rows: [(label, [(img or None, caption)])]. Images are pasted 1:1 unless scale != 1."""
        f_t, f_s, f_h, f_c, f_l = font(24, True), font(17), font(18, True), font(15), font(19, True)
        cells = [[(im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS) if (im is not None and scale != 1) else im, cap)
                  for im, cap in r] for _l, r in rows]
        ncol = len(cols); d0 = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        cw = [max([d0.textlength(cols[i], font=f_h) + 10] + [c[i][0].width if c[i][0] else 0 for c in cells]) for i in range(ncol)]
        cw = [int(max(170, x)) for x in cw]
        caplines = [[wrap(d0, c[i][1], f_c, cw[i]) for i in range(ncol)] for c in cells]
        rh = [max(c[i][0].height if c[i][0] else 0 for i in range(ncol)) for c in cells]
        ch = [max(len(cl) for cl in cls) * 18 for cls in caplines]
        left, pad, hdr = 210, 14, 92
        subl = wrap(d0, sub, f_s, left + sum(cw) + pad * ncol - 40) if sub else []
        hdr += 22 * len(subl)
        Wi = left + sum(cw) + pad * (ncol + 1); Hi = hdr + sum(rh) + sum(ch) + len(rows) * (pad + 10) + pad
        im = Image.new("RGB", (int(Wi), int(Hi)), BG); d = ImageDraw.Draw(im)
        d.text((20, 10), heading, font=f_t, fill=ACC)
        for i, l in enumerate(subl): d.text((20, 44 + 22 * i), l, font=f_s, fill=DIM)
        xs = [left + pad]; [xs.append(xs[-1] + cw[i] + pad) for i in range(ncol)]
        for i, c in enumerate(cols): d.text((xs[i], hdr - 30), c, font=f_h, fill=FG)
        y = hdr
        for j, (lab, _r) in enumerate(rows):
            for k, l in enumerate(wrap(d0, lab, f_l, left - 30)): d.text((20, y + 8 + 24 * k), l, font=f_l, fill=FG)
            for i in range(ncol):
                p = cells[j][i][0]
                d.rectangle([xs[i] - 2, y - 2, xs[i] + cw[i] + 1, y + rh[j] + 1], outline=RULE)
                if p is not None: im.paste(p, (xs[i] + (cw[i] - p.width) // 2, y + (rh[j] - p.height) // 2))
                for k, l in enumerate(caplines[j][i]): d.text((xs[i], y + rh[j] + 4 + 18 * k), l, font=f_c, fill=DIM)
            y += rh[j] + ch[j] + pad + 10
        self.blocks.append(im)
        self.md += [f"## {heading}", "", sub, ""]
        if md_rows is None:
            self.md += ["| row | " + " | ".join(cols) + " |", "|---" * (ncol + 1) + "|"]
            for (lab, r) in rows: self.md.append(f"| {lab} | " + " | ".join(cap.replace("|", "/") for _i, cap in r) + " |")
        else: self.md += md_rows
        self.md.append("")

    def save(self, name):
        f_t = font(34, True)
        Wt = max(b.width for b in self.blocks + [Image.new("RGB", (1800, 1))])
        d0 = ImageDraw.Draw(Image.new("RGB", (8, 8))); il = wrap(d0, self.intro, font(19), Wt - 40)
        head = Image.new("RGB", (Wt, 70 + 26 * len(il) + 10), BG); d = ImageDraw.Draw(head)
        d.text((20, 14), self.title, font=f_t, fill=FG)
        for i, l in enumerate(il): d.text((20, 64 + 26 * i), l, font=font(19), fill=FG)
        parts = [head] + self.blocks
        Ht = sum(p.height for p in parts) + 18 * len(parts)
        sh = Image.new("RGB", (Wt, Ht), BG); y = 0
        for p in parts: sh.paste(p, (0, y)); y += p.height + 18
        fn = OUT / f"{name}.png"; sh.save(fn, optimize=True)
        (OUT / f"{name}.md").write_text("\n".join(self.md) + f"\n\nImage: `{fn}` ({sh.width}x{sh.height} px).\n")
        print("SHEET", fn, sh.size, flush=True)
        return fn


def capm(m, keys):
    lab = {"lit_px": "lit", "rx_px": "rx-blue", "tx_px": "tx-gold", "red_px": "red", "peak_Y": "peakY"}
    return ", ".join(f"{lab.get(k, k)} {m[k]}" for k in keys)


# ---------------------------------------------------------------- sheet 01a / 01b: quantity ladders
BASE = dict(state="working", cpu=0.9, mem=0.8, procs=4)
WARM = 300                                          # 5 s of 60 Hz steps before the shot
LADDERS_DATA = [
    ("Memory footprint (GB) -> body area", "mem", [0.15, 0.4, 0.8, 1.5, 2.6], {}, ["lit_px"]),
    ("Background processes -> satellite / tentacle count", "procs", [1, 2, 4, 7, 10], {}, ["lit_px"]),
    ("Bandwidth IN rx (Mbit/s, log) -> inward cool pulses", "rx", [0.02, 0.2, 1.5, 6, 25], {}, ["rx_px", "tx_px"]),
    ("Bandwidth OUT tx (Mbit/s, log) -> outward gold pulses", "tx", [0.02, 0.2, 1.5, 6, 25], {}, ["rx_px", "tx_px"]),
    ("Bandwidth strained (net.strain 0..1, at rx 8 / tx 3) -> jam", "strain", [0, 0.25, 0.5, 0.75, 1.0], {"rx": 8, "tx": 3}, ["rx_px", "tx_px"]),
]
LADDERS_STATE = [
    ("Machine strain (m.level 0..3; last adds thermal 2) -> ember glow + geometry noise", "level",
     [(0, {}), (1, {}), (2, {}), (3, {}), (3, {"thermal": 2})], {}, ["red_px"]),
    ("Needs you -> ripple rings (time since the state flipped)", "needs", ["working", 0.5, 1.5, 3.0, 6.0], {}, ["lit_px"]),
    ("Busyness: idle breathing .. busy sparkle (cpu, procs, rx/tx together)", "busy",
     [dict(state="idle", cpu=0.03, procs=1), dict(state="working", cpu=0.2, procs=2, rx=0.1, tx=0.05),
      dict(cpu=1.0, procs=4, rx=1, tx=0.5), dict(cpu=2.5, procs=7, rx=6, tx=3), dict(cpu=4, procs=10, rx=25, tx=25)], {}, ["lit_px", "rx_px", "tx_px"]),
    ("Overload: machine strain + bandwidth strain together (rx 8 / tx 3)", "over",
     [dict(level=0, strain=0), dict(level=1, strain=0.25), dict(level=2, strain=0.5), dict(level=3, strain=0.75), dict(level=3, thermal=2, strain=1.0)],
     {"rx": 8, "tx": 3}, ["red_px", "rx_px", "tx_px"]),
]


def level_msgs(var, v, fixed):
    p = dict(BASE); p.update(fixed)
    if var == "level": lv, more = v; p.update(level=lv, **more); return [(M(**p), WARM)], f"level {lv}" + (" + thermal 2" if more else "")
    if var == "needs":
        if v == "working": return [(M(**p), WARM)], "working (not needed)"
        return [(M(**p), WARM), (M(**dict(p, state="needs")), int(round(v * 60)))], f"needs you, {v} s in"
    if var in ("busy", "over"):
        p.update(v); lab = ", ".join(f"{k} {x}" for k, x in v.items()); return [(M(**p), WARM)], lab
    p[var] = v; return [(M(**p), WARM)], f"{var} {v}"


def ladders(b, port, key, title, intro, spec):
    sh = Sheet(key, title, intro)
    for qlab, var, levels, fixed, mkeys in spec:
        rows = []
        for sp in (JELLY, CHOIR):
            ims, caps = [], []
            for i, v in enumerate(levels):
                seq, lab = level_msgs(var, v, fixed)
                im, _r = shoot(b, port, sp, 1.0, seq, f"{key}_{var}_{sp[2][:5]}_{i}")
                ims.append(im[0]); caps.append(lab)
            bx = union_box(ims)
            cells = []
            for im, lab in zip(ims, caps):
                c = im.crop(bx); m = metrics(c); METRICS[f"{key}/{var}/{sp[2]}/{lab}"] = m
                cells.append((c, f"{lab}  |  {capm(m, mkeys)}"))
            rows.append((sp[2], cells))
        sh.row_table(qlab, "Everything else held fixed: working, cpu 0.9, mem 0.8 GB, procs 4, no traffic, machine calm, hue 150, variant 0; "
                     "size slider 100% (the live default) on a 2560x1440 screen at dpr 2; device pixels 1:1, one crop per row so sizes compare. "
                     "Caption numbers are measured on the cell (lit = px above 20/255; rx-blue/tx-gold/red = px in those hue bands).",
                     ["lowest", "low", "mid", "high", "extreme"], rows)
    return sh.save(key)


# ---------------------------------------------------------------- sheet 01c: CPU tempo filmstrips
def tempo(b, port):
    sh = Sheet("01c", "01c  CPU -> INTERNAL TEMPO, as filmstrips",
               "A still cannot show tempo, so each row is 6 consecutive frames 0.1 s apart from one continuous simulation (after 5 s warm-up). "
               "Watch the chase lights / bell pulse move from frame to frame; more cores = bigger step. Frames are downscaled 0.6x (motion, not detail). "
               "Phase advance is from each piece's own tempo formula (source: Choir chase om = 0.16 + 1.9*cpu rad/s; jellyfish bell pulse 0.14 + 0.52*cpu Hz, "
               "rim chase 0.5 + 1.1*cpu units/s). 'Frame change' is MEASURED: mean |delta luma| (0..255) between consecutive frames over lit pixels.")
    for sp in (JELLY, CHOIR):
        rows = []
        for cpu in (0.02, 0.3, 1.0, 2.0, 4.0):
            ims, _r = shoot(b, port, sp, 1.0, [(M(cpu=cpu), WARM)], f"01c_{sp[2][:5]}_{cpu}", frames=6, step=6)
            bx = union_box(ims); crops = [i.crop(bx) for i in ims]; fd = framediff(crops)
            if sp is CHOIR: adv = f"chase {math.degrees((0.16 + 1.9 * cpu) * 0.1):.1f} deg/frame"
            else: adv = f"bell {100 * (0.14 + 0.52 * cpu) * 0.1:.1f}% cycle/frame, chase {(0.5 + 1.1 * cpu) * 0.1:.2f} u/frame"
            METRICS[f"01c/{sp[2]}/cpu {cpu}"] = {"frame_change": fd, "advance": adv}
            rows.append((f"cpu {cpu} cores", [(c, (f"{adv}; frame change {fd}" if k == 0 else f"t+{k / 10:.1f} s")) for k, c in enumerate(crops)]))
        sh.row_table(f"{sp[2]}: cpu 0.02 .. 4 cores", "", [f"t+{k / 10:.1f} s" for k in range(6)], rows, scale=0.6)
    return sh.save("01c_cpu_tempo_filmstrips")


# ---------------------------------------------------------------- sizing helpers
CAL = {}


def body_extent(sp, b, port, mem=0.8):
    """CSS px of the body at url size=1: jelly bell width, Choir saucer width, sigil glyph E (all scale linearly with size)."""
    k = (sp[0], sp[1], mem)
    if k in CAL: return CAL[k]
    _i, r = shoot(b, port, sp, 1.0, [(M(mem=mem), 30)], f"cal_{Path(sp[0]).stem}_{mem}")
    if "siphon" in sp[0]: e = 2 * r["r"] / 1.2
    elif "choir" in sp[0]: e = 2 * r["r"] * (36 + 34 * min(1, mem / 2.5)) / (1.12 * (36 + 34 * min(1, mem / 2.5)) + 6)
    elif "sigils" in sp[0] or "night" in sp[0] or "arm" in sp[0]: e = 54 * math.sqrt(min(2.6, max(0.2, mem)) / 0.8) * 0.5 * min(W / 1280, H / 800)
    else: e = 2 * r["r"] / 1.12
    CAL[k] = e; return e


def tight(im, pad=10, thr=14): return im.crop(union_box([im], pad, thr))


def mag(im, k): return im.resize((im.width * k, im.height * k), Image.NEAREST)


# ---------------------------------------------------------------- sheet 02: confusion pairs
def confusion(b, port):
    sh = Sheet("02", "02  CONFUSION PAIRS: what a human might mistake for what",
               "Each pair puts two states side by side that share a visual cue. The right-hand note says what is supposed to separate them. "
               "Live default size unless stated; device pixels 1:1 unless magnified (nearest-neighbour, no detail invented). Hue 150 unless stated.")
    def pair(sp, a, bb, size=1.0, name="p", k=1):
        ia, _ = shoot(b, port, sp, size, a, f"02_{name}_a"); ib, _ = shoot(b, port, sp, size, bb, f"02_{name}_b")
        bx = union_box([ia[0], ib[0]]); ca, cb = ia[0].crop(bx), ib[0].crop(bx)
        return (mag(ca, k) if k > 1 else ca), (mag(cb, k) if k > 1 else cb), metrics(ca), metrics(cb)
    P = []
    need = [(M(), WARM), (M(state="needs"), 100)]; heavy = [(M(rx=25, tx=25), WARM)]
    for sp in (JELLY, CHOIR):
        a, c, ma, mc = pair(sp, need, heavy, name=f"need_bw_{sp[2][:5]}")
        P.append((f"needs-you ripples vs heavy traffic ({sp[2]})", a, c, f"needs you, 1.7 s in, no traffic | {capm(ma, ['rx_px','tx_px'])}",
                  f"rx 25 + tx 25 Mbit/s, not needed | {capm(mc, ['rx_px','tx_px'])}",
                  "Ripples leave the body as expanding rings in the creature's own hue; pulses ride its structure in blue (in) / gold (out). Needs-you also approaches the focused window (not shown in a still)."))
    for sp in (JELLY, CHOIR):
        a, c, ma, mc = pair(sp, [(M(level=3, thermal=2), WARM)], [(M(hue=15), WARM)], name=f"ember_hue_{sp[2][:5]}")
        P.append((f"machine-strain ember vs an orange-red project hue ({sp[2]})", a, c, f"hue 150, m.level 3 + thermal 2 | {capm(ma, ['red_px'])}",
                  f"hue 15 (orange-red), machine calm | {capm(mc, ['red_px'])}",
                  "Owner ruling: no red except machine strain, so project hues should never sit near 0-20. Ember is a glow BEHIND the body plus geometry noise; a red hue is crisp and aligned."))
    for sp in (JELLY, CHOIR):
        e = body_extent(sp, b, port); s23 = 23 / e
        a, c, ma, mc = pair(sp, [(M(rx=8), WARM)], [(M(tx=8), WARM)], size=s23, name=f"rxtx23_{sp[2][:5]}", k=4)
        P.append((f"rx vs tx at 23 CSS px body ({sp[2]}), 4x nearest", a, c, f"rx 8 only | {capm(ma, ['rx_px','tx_px'])}", f"tx 8 only | {capm(mc, ['rx_px','tx_px'])}",
                  "Only tint (cool white-blue vs warm gold) and direction (rim->core vs core->rim) separate them; direction is invisible in a still and tiny at 23 px."))
    for sp in (JELLY, CHOIR):
        a, c, ma, mc = pair(sp, [(M(mem=0.4), WARM)], [(M(mem=1.6), WARM)], name=f"memdist_{sp[2][:5]}")
        a2, _ = shoot(b, port, sp, 0.5, [(M(mem=1.6), WARM)], f"02_memdist_{sp[2][:5]}_c")
        bx = union_box([a2[0]]); c2 = a2[0].crop(bx)
        P.append((f"memory vs size slider / screen scale ({sp[2]})", a, c2, f"mem 0.4 GB, slider 100% | lit {ma['lit_px']}",
                  f"mem 1.6 GB (4x), slider 50% | lit {metrics(c2)['lit_px']}",
                  "There is no depth cue: body area is memory only RELATIVE to neighbours at one slider value. A 4x memory difference vanishes if the slider (or a different screen) halves the scale."))
    for sp in (JELLY, CHOIR):
        e = body_extent(sp, b, port, mem=0.33); s23 = 23 / e
        a, c, ma, mc = pair(sp, [(M(state="idle", cpu=0.03, procs=1, mem=0.33), WARM)],
                            [(M(mem=0.33, cpu=3, procs=8, rx=8, tx=3, level=3, thermal=2, strain=1), WARM)], size=s23, name=f"idleover_{sp[2][:5]}", k=4)
        P.append((f"idle vs overload at 23 CSS px ({sp[2]}), 4x nearest", a, c, f"idle, cpu 0.03, procs 1 | {capm(ma, ['lit_px','red_px'])}",
                  f"overload: level 3 + thermal 2, strain 1, rx 8/tx 3, cpu 3 | {capm(mc, ['lit_px','red_px','rx_px','tx_px'])}",
                  "At 23 px the ember halo and lit area must carry it; the geometry noise and jam are a few device pixels."))
    a, c, ma, mc = pair(JELLY, [(M(rx=8, tx=3, strain=1), WARM)], [(M(rx=8, tx=3, level=3), WARM)], name="twostrains")
    P.append(("link strain (jam) vs machine strain (Siphonophores)", a, c, f"net.strain 1, machine calm | {capm(ma, ['red_px','rx_px','tx_px'])}",
              f"m.level 3, link fine | {capm(mc, ['red_px','rx_px','tx_px'])}",
              "Jam = pulses stall and pile into a bright band at the throat/rim, no red. Machine strain = red ember + misaligned geometry."))
    rows = [(lab, [(a, ca), (c, cc), (None, note)]) for lab, a, c, ca, cc, note in P]
    for lab, a, c, ca, cc, note in P: METRICS[f"02/{lab}"] = {"a": ca, "b": cc}
    sh.row_table("Pairs", "Left and right share one crop (so size compares). Captions carry the cell's measured hue-band pixel counts.",
                 ["A", "B", "what should tell them apart"], rows)
    return sh.save("02_confusion_pairs")


# ---------------------------------------------------------------- sheet 03: size ladder
def sizes(b, port):
    sh = Sheet("03", "03  SIZE LADDER: where each channel dies",
               "Same sprite (working, cpu 0.9, mem 0.8 GB, procs 4, rx 8 / tx 3 Mbit/s, m.level 1) with the body solved to 23, 40, 64, 128 and 256 CSS px "
               "(jellyfish = bell width, Choir = saucer width, Night Signals = glyph extent E), at dpr 2 on black. Device pixels 1:1; the first column repeats 23 px "
               "at 4x nearest. Measured live defaults at slider 100% on a 2560x1440 screen with the idle-typical 0.33 GB are listed in the text block.")
    D = [23, 40, 64, 128, 256]; rows = []
    for sp, hues in ((JELLY, (200, 45, 285)), (CHOIR, (200, 45, 285)), (NIGHT_OLD, (200,)), (NIGHT, (200, 45))):
        e = body_extent(sp, b, port)
        for hue in hues:
            cells = []
            for d in D:
                ims, _r = shoot(b, port, sp, d / e, [(M(rx=8, tx=3, level=1, hue=hue), WARM)], f"03_{Path(sp[0]).stem}_{hue}_{d}")
                c = tight(ims[0]); m = metrics(c); METRICS[f"03/{sp[2]}/hue {hue}/{d}px"] = m
                cells.append((c, f"{d} px | {capm(m, ['rx_px','tx_px'])}, edge {m['edge_width_px']} px"))
            cells.insert(0, (mag(cells[0][0], 4), "23 px, 4x nearest"))
            rows.append((f"{sp[2]}, hue {hue}", cells))
    defaults = []
    for sp in (JELLY, CHOIR, NIGHT):
        defaults.append(f"{sp[2]}: {body_extent(sp, b, port, mem=0.33):.1f} CSS px")
    sh.text_block("Live default body size (slider 100%, 2560x1440, mem 0.33 GB), computed from the runtime's reported radius",
                  "; ".join(defaults) + ". Edge = measured effective edge width in device px (p99.5 value / p99.5 one-pixel gradient; 1.0 = a one-device-pixel step, larger = softer).", 1800)
    sh.row_table("Ladder", "", ["23 px x4", "23", "40", "64", "128", "256"], rows)
    return sh.save("03_size_ladder")


# ---------------------------------------------------------------- sheet 04: species / art
def species(b, port):
    sh = Sheet("04", "04  SPECIES / ART: the current species, large, in saturated hues",
               "Each species large (hit-disc diameter ~300 CSS px, dpr 2, device pixels shown at 0.75x to fit), working with rx 8 / tx 3 Mbit/s, procs 5, m.level 0.3, "
               "then all 8 identity variants at ~64 CSS px across four hues. Form carries no data (owner ruling): variants are identity only. "
               "Night Signals: old 9x9 LED glyphs (commit 4cac820) beside the new vector-outline engine (commit d995c41, prototype/vector/engine.js), both rendered from their own trees.")
    hero_rows = []
    lineup = [JELLY, JELLY_SHIP, CHOIR, SIGILS, KALEI, FIRE, NIGHT_OLD, NIGHT]
    for sp in lineup:
        _i, r1 = shoot(b, port, sp, 1.0, [(M(mem=0.8), 30)], f"04_cal_{Path(sp[0]).stem}_{bool(sp[1])}")
        R = r1["r"]; ivs = list(range(8)); hues = [200, 285, 45, 150]
        big, _ = shoot(b, port, sp, 150 / R, [(M(rx=8, tx=3, procs=5, level=0.3, hue=285 if sp not in (NIGHT, NIGHT_OLD) else 200), WARM)], f"04_hero_{Path(sp[0]).stem}_{bool(sp[1])}")
        hc = tight(big[0]); m = metrics(hc); METRICS[f"04/{sp[2]}/hero"] = m
        small = []
        for k, iv in enumerate(ivs):
            ims, _ = shoot(b, port, sp, 32 / R, [(M(rx=8, tx=3, procs=5, level=0.3, iv=iv, hue=hues[k % 4]), WARM)], f"04_iv_{Path(sp[0]).stem}_{bool(sp[1])}_{iv}")
            small.append(tight(ims[0]))
        hs = max(s.height for s in small); strip = Image.new("RGB", (sum(s.width for s in small) + 8 * len(small), hs), BG); x = 0
        for s in small: strip.paste(s, (x, (hs - s.height) // 2)); x += s.width + 8
        hero_rows.append((sp[2], [(hc.resize((int(hc.width * 0.75), int(hc.height * 0.75)), Image.LANCZOS),
                                   f"peakY {m['peak_Y']}, mean S {m['mean_S_lit']}, clipped {m['frac_clipped']}, edge {m['edge_width_px']} px"),
                                  (strip, "variants " + ", ".join(map(str, ivs)) + " at hues 200/285/45/150, 1:1")]))
    sh.row_table("Species", "", ["hero (0.75x)", "identity variants (1:1 device px)"], hero_rows)
    # the bat: reference vs traced outline (assets from the symbol-resolution comparison, read only)
    v2 = SRC_CMP / "v2"; cells = []
    for fn, cap in ((bsc.REF, "owner's reference image"), (v2 / "bat_trace_overlay.png", "traced outline (magenta) on the reference"),
                    (v2 / "crops/bat_strip_B65.png", "edge LED 65x65 at 256 px"), (v2 / "crops/bat_strip_C2.png", "vector edge (arm C2) at 256 px")):
        if fn.exists():
            im = Image.open(fn).convert("RGB"); im = im.resize((int(im.width * 300 / im.height), 300), Image.LANCZOS); cells.append((im, cap))
    if cells:
        sh.row_table("The bat: reference vs traced outline", "Trace IoU 0.957 against the reference's own yellow mask (tools/trace_symbols.py). Scaled to 300 px tall.",
                     [c[1] for c in cells], [("Batman", cells)])
    return sh.save("04_species_art")


# ---------------------------------------------------------------- sheet 05: display headroom
def bloom(im, thr=0.55, sigma=7, amt=0.7, satk=1.2):
    from scipy.ndimage import gaussian_filter
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    hi = np.clip((a - thr) / (1 - thr), 0, 1)
    bl = np.stack([gaussian_filter(hi[..., c], sigma) for c in range(3)], -1)
    out = np.clip(a + amt * bl, 0, 1)
    hsv = np.asarray(Image.fromarray((out * 255).astype(np.uint8)).convert("HSV")).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * satk, 0, 255)
    return Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")


def hist_img(m, w=300, h=90):
    im = Image.new("RGB", (w, h + 22), BG); d = ImageDraw.Draw(im); hs = m["sat_hist"]; mx = max(hs) or 1
    for i, v in enumerate(hs):
        x0 = i * w // 10; d.rectangle([x0 + 2, h - int(h * v / mx), x0 + w // 10 - 2, h], fill=(110, 170, 255) if i < 8 else ACC)
    d.text((2, h + 3), "sRGB saturation of lit px, 0 .. 1", font=font(13), fill=DIM)
    return im


def headroom(b, port):
    sh = Sheet("05", "05  DISPLAY HEADROOM: how much resolution, saturation and intensity we use",
               "Measured on the rendered stills (sRGB PNG from Chromium 151, black background). 'Lit' = px whose max channel > 20/255. peak Y = max relative luminance "
               "(linear, 1.0 = sRGB white). V>0.8 = share of lit px above 80% HSV value. Clipped = share of lit px with a channel at 255. Edge = effective edge width in "
               "device px (1.0 = one-device-pixel step). Right column: a MOCK-UP, not the runtime: the same scene at dpr 3 with the runtime's own sat x1.35 and glow x1.25 "
               "URL multipliers, then a post-process additive bloom (highlights > 0.55, sigma 7 px, 0.7x) and HSV saturation x1.2; the file is tagged Display P3, so on a "
               "P3 screen its numbers map to wider primaries. P3/HDR (canvas colorSpace 'display-p3', EDR headroom on XDR / HDR monitors) are QUESTIONS, not current capability.")
    rows, summary = [], []
    for sp in (JELLY, CHOIR, NIGHT, SIGILS, KALEI, FIRE):
        _i, r1 = shoot(b, port, sp, 1.0, [(M(), 30)], f"05_cal_{Path(sp[0]).stem}")
        size = 90 / r1["r"]; seq = [(M(rx=8, tx=3, procs=5, level=0.3, hue=285), WARM)]
        cur, _ = shoot(b, port, sp, size, seq, f"05_cur_{Path(sp[0]).stem}")
        var, _ = shoot(b, port, sp, size, seq, f"05_var_{Path(sp[0]).stem}", dpr=3, extra="&sat=1.35&glow=1.25")
        c = tight(cur[0]); v = bloom(tight(var[0])); mc, mv = metrics(c), metrics(v)
        METRICS[f"05/{sp[2]}/current"] = mc; METRICS[f"05/{sp[2]}/mockup"] = mv
        v.save(OUT / f"05_mockup_{Path(sp[0]).stem}_P3.png", icc_profile=ImageCms.ImageCmsProfile("/System/Library/ColorSync/Profiles/Display P3.icc").tobytes())
        f = lambda m: f"peakY {m['peak_Y']}, max ch {m['max_channel']}, V>0.8 {m['frac_V_gt_0.8']}, S>0.8 {m['frac_S_gt_0.8']}, mean S {m['mean_S_lit']}, clipped {m['frac_clipped']}, edge {m['edge_width_px']} px, lit {m['lit_px']}"
        rows.append((sp[2], [(c, "CURRENT dpr 2: " + f(mc)), (hist_img(mc), ""), (v, "MOCK-UP dpr 3 + bloom: " + f(mv)), (hist_img(mv), "")]))
        summary.append(f"{sp[2]}: current peakY {mc['peak_Y']}, V>0.8 {mc['frac_V_gt_0.8']}, mean S {mc['mean_S_lit']}, clipped {mc['frac_clipped']}, edge {mc['edge_width_px']} px")
    sh.text_block("Numbers in one place", "\n".join(summary) + "\nScreen pitch: 1 device px = 0.5 CSS px at dpr 2 (owner's screens are 2x). An edge width near 1 means a piece already uses the full device resolution at that feature; well above 1 means it is softer than the screen can draw.", 2000)
    sh.row_table("Current vs pushed mock-up", "hit disc ~180 CSS px, hue 285, working, rx 8 / tx 3, m.level 0.3.", ["current", "saturation", "mock-up (dpr 3, 1:1 device px)", "saturation"], rows)
    return sh.save("05_display_headroom")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default="01a,01b,01c,02,03,04,05"); a = ap.parse_args()
    global OLDPORT
    want = set(a.only.split(",")); port = bsc.serve(); OLDPORT = serve_old()
    with sync_playwright() as pw:
        b = pw.chromium.launch(); print("chromium", b.version, flush=True)
        if "01a" in want: ladders(b, port, "01a_quantity_ladders_data", "01a  QUANTITY LADDERS: memory, processes, bandwidth in / out / strained",
                                  "One measured quantity per row, five levels low -> extreme, everything else held fixed, in two species (the fine-dot jellyfish and the Choir) so the "
                                  "encoding can be judged apart from the art. Real runtime, real live-feed message shape (window.__live).", LADDERS_DATA)
        if "01b" in want: ladders(b, port, "01b_quantity_ladders_state", "01b  QUANTITY LADDERS: machine strain, needs you, busyness, overload",
                                  "Same method as 01a. CPU tempo is on sheet 01c (needs motion). VPN-lost and play are whole-desktop behaviours and are not laddered here.", LADDERS_STATE)
        if "01c" in want: tempo(b, port)
        if "02" in want: confusion(b, port)
        if "03" in want: sizes(b, port)
        if "04" in want: species(b, port)
        if "05" in want: headroom(b, port)
        b.close()
    old = json.loads((OUT / "METRICS.json").read_text()) if (OUT / "METRICS.json").exists() else {}
    old.update(METRICS); (OUT / "METRICS.json").write_text(json.dumps(old, indent=1))
    if ERR: print("PAGE ERRORS:", ERR[:10], file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main()
