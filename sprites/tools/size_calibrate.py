#!/usr/bin/env python3
"""Size calibration: make every sprite the same DRAWN size, per render context, and write prototype/size_norm.js.

  python3 tests/tools/gate.py python3 tools/size_calibrate.py            # measure, iterate, write the table + sheets
  python3 tools/size_calibrate.py --measure-only [--root DIR] [--tag before]   # measure a tree as it stands (no write)

Owner, 2026-11-07: "for the same memory configuration the stdev of the distribution of pixel distance from its center
is roughly equal (a more resilient stat than min/max matching). Scale them out here on the screen and within both places
in the settings menu."

THE STAT (per rendered sprite, CSS px). Every sprite is drawn additively on black, so a pixel's light is its linear
luminance L = (0.2126 R + 0.7152 G + 0.0722 B) x alpha (sRGB decoded). Pixels with L < THR (0.02, about sRGB 39/255)
are dropped: that cuts the faint body halos and glow tails, whose reach depends on the glow sprite and not on the
creature, while every stroke, dot and bead survives. With weight w = L over the kept pixels, the centre is the
luminance-weighted centroid and the size is sigma = sqrt(sum w r^2 / sum w), r = distance to that centroid: the 2-D
standard deviation of the light about its centre (sqrt(var x + var y)). NOT the standard deviation of r itself, which is
~0 for any thin ring whatever its radius and would call a big halo and a small one the same size.

THE CONDITION (timeline g_calib, tools/make_scenarios.py): one session, steady working (cpu 0.3), 0.8 GB, no background
tasks, no network beads, no strain, no focus. sigma is the mean over sim times 5, 6 and 7 s (the CPU sweep and the
chase move light round the figure). Live is driven through app/stage.html itself (one Augur-shaped snapshot, the cast
naming the species and form, the owner's Size slider read from `defaults read com.mandrake.sprites size`), so the live
number is measured, not inferred. Settings contexts load the piece page exactly as app/settings.js url() builds it.

THE TABLE. k[context][species][iv] multiplies the creature about its reported centre (visitors_runtime.js creature()):
k never depends on data, so memory -> area holds within a species. Targets: live = the median sigma of the tree as it
stood before calibration (the owner's screen does not jump); hero / tile / form = that context's own median, lowered if
the largest sprite would no longer fit its cell. The stat is not exactly linear in k (stroke widths and dot floors do not
scale), so it iterates k <- k x target / sigma until every sprite is within TOL of its target.

Renders are serial (one headless Chromium, one page at a time); run it through tests/tools/gate.py.
Outputs: prototype/size_norm.js (committed), and under <agent storage>/sprites/size-calibration/: report.json and one
contact sheet per context (sheet_<ctx>_<tag>.png: 11 species x 8 forms, each cell the same crop).
"""
import argparse, base64, functools, http.server, io, json, socketserver, statistics, subprocess, sys, threading
from pathlib import Path

SPR = Path(__file__).resolve().parents[1]
SPECIES = ["c1_choir", "c2_siphon", "c3_sigils", "c4_kaleido", "c5_fireflies", "c6_night", "c7_patches", "c8_instruments",
           "c9_wild", "c10_made", "c11_old"]
# context -> (stage w, h) in CSS px; live is the laptop's screen (1728 x 1117 "looks like" at 3456 x 2234)
CTX = {"live": (1728, 1117), "hero": (380, 245), "tile": (165, 110), "form": (112, 112)}
THR, TIMES, DPR, TOL = 0.02, (5.0, 6.0, 7.0), 2, 0.015
LIVE_CROP = 300   # CSS px square cut round each live sprite's centroid for its contact sheet (same for all)


def storage():
    return Path(subprocess.check_output([sys.executable, str(Path.home() / "dev/Lodestar/bin/lib/agent_storage.py")], text=True).strip())


def serve(root):
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
        def end_headers(self): self.send_header("Cache-Control", "no-store"); super().end_headers()
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Q, directory=str(root))); srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


# The in-page stat: canvas -> {sigma, cx, cy, ext (half-extent of kept light, max |dx|/|dy| ratio to the cell), png}
STAT_JS = """([cv, thr, dpr, crop, cellW, cellH]) => {
  const w = cv.width, h = cv.height, d = cv.getContext('2d').getImageData(0, 0, w, h).data;
  const lut = new Float32Array(256); for (let i = 0; i < 256; i++) { const v = i / 255; lut[i] = v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
  let sw = 0, sx = 0, sy = 0; const W = new Float32Array(w * h);
  for (let i = 0, p = 0; p < w * h; p++, i += 4) { const a = d[i + 3] / 255; if (!a) continue;
    const L = (0.2126 * lut[d[i]] + 0.7152 * lut[d[i + 1]] + 0.0722 * lut[d[i + 2]]) * a; if (L < thr) continue;
    W[p] = L; sw += L; sx += L * (p % w); sy += L * ((p / w) | 0); }
  if (!sw) return null; const cx = sx / sw, cy = sy / sw; let s2 = 0, ex = 0, ey = 0;
  for (let p = 0; p < w * h; p++) { const L = W[p]; if (!L) continue; const dx = p % w - cx, dy = ((p / w) | 0) - cy; s2 += L * (dx * dx + dy * dy);
    if (Math.abs(dx) > ex) ex = Math.abs(dx); if (Math.abs(dy) > ey) ey = Math.abs(dy); }
  const out = { sigma: Math.sqrt(s2 / sw) / dpr, cx: cx / dpr, cy: cy / dpr, ex: ex / dpr, ey: ey / dpr, lit: sw };
  if (crop !== null) { const c = document.createElement('canvas'), cw = crop > 0 ? crop : cellW, ch = crop > 0 ? crop : cellH; c.width = cw * dpr; c.height = ch * dpr;
    const x = c.getContext('2d'); x.fillStyle = '#000'; x.fillRect(0, 0, c.width, c.height);
    if (crop > 0) x.drawImage(cv, cx - cw * dpr / 2, cy - ch * dpr / 2, cw * dpr, ch * dpr, 0, 0, cw * dpr, ch * dpr); else x.drawImage(cv, 0, 0);
    out.png = c.toDataURL('image/png'); }
  return out; }"""


def snapshot():
    far = 4e12
    blk = lambda **k: dict(k, observed_at=0, valid_until=far)
    return {"schema": "augur.snapshot", "version": "1.1", "valid_until": far, "written_at": 0, "seq": 1,
            "machine": {"strain": blk(score=0.0, level="light"), "thermal": blk(state=0), "memory": blk(pressure=0),
                        "net": blk(rx_mbps=0.0, tx_mbps=0.0), "vpn": blk(state="up", on_site=False), "bandwidth": blk(strain=0.0)},
            "sessions": [{"id": "1@1", "pid": 1, "started_at": 1.0, "project": "Calib", "project_key": "calib", "managed": True,
                          "attention": blk(state="working", since=0), "load": blk(cpu_cores=0.3, mem_gb=0.8, procs=1),
                          "tasks": blk(total=0, background=0), "net": blk(rx_mbps=0.0, tx_mbps=0.0)}], "projects": []}


class Renderer:
    def __init__(self, root, live_size):
        from playwright.sync_api import sync_playwright
        self.root, self.port, self.live_size = Path(root), serve(root), live_size
        self.pw = sync_playwright().start(); self.b = self.pw.chromium.launch()

    def close(self): self.b.close(); self.pw.stop()

    def _stat(self, pg, canvas_js, crop, cell):
        return pg.evaluate(f"(a) => ({STAT_JS})([{canvas_js}, ...a])", [THR, DPR, crop, cell[0], cell[1]])

    def proto(self, ctx, sp, iv, sheet):
        w, h = CTX[ctx]
        pg = self.b.new_page(viewport={"width": w, "height": h})
        u = (f"http://127.0.0.1:{self.port}/prototype/{sp}.html?tl=g_calib&w={w}&h={h}&chrome=0&bg=0&dim=0&hover=0"
             f"&hue=190&iv={iv}&fit=1&norm={ctx}&autostart=0&dpr={DPR}")
        pg.goto(u); pg.wait_for_function("typeof window.__renderAt === 'function'")
        out = []
        for t in TIMES:
            pg.evaluate(f"window.__renderAt({t})")
            out.append(self._stat(pg, "document.querySelectorAll('canvas')[1]", 0 if sheet and t == TIMES[1] else None, (w, h)))
        errs = pg.evaluate("window.__errors || []"); pg.close()
        if errs: raise SystemExit(f"{sp} iv {iv} {ctx}: page errors {errs[:2]}")
        return out

    def live(self, sp, iv, sheet):
        w, h = CTX["live"]
        pg = self.b.new_page(viewport={"width": w, "height": h})
        pg.goto(f"http://127.0.0.1:{self.port}/app/stage.html?stale=0&dpr={DPR}&vpndebounce=0")
        pg.wait_for_function("!!window.SpritesStage")
        cast = {"projects": {"calib": {"concept": sp, "iv": iv, "hex": "#33CCFF"}}}
        pg.evaluate(f"SpritesStage.setSize({w},{h}); SpritesStage.setScale({self.live_size}); SpritesStage.setPaused(true);"
                    f"SpritesStage.setCast({json.dumps(cast)}); SpritesStage.update({json.dumps(snapshot())})")
        pg.wait_for_function(f"(() => {{ const V = __stage.V({sp!r}); return V && V.sessions.length === 1; }})()", timeout=15000)
        out = []
        for t in TIMES:
            pg.evaluate(f"__stage.renderAt({t})")
            out.append(self._stat(pg, "__stage.canvas", LIVE_CROP if sheet and t == TIMES[1] else None, (LIVE_CROP, LIVE_CROP)))
        errs = pg.evaluate("window.__errors || []"); pg.close()
        if errs: raise SystemExit(f"{sp} iv {iv} live: page errors {errs[:2]}")
        return out

    def measure(self, ctx, sp, iv, sheet=False):
        rs = self.live(sp, iv, sheet) if ctx == "live" else self.proto(ctx, sp, iv, sheet)
        if any(r is None for r in rs): raise SystemExit(f"{sp} iv {iv} {ctx}: nothing lit")
        m = {"sigma": statistics.fmean(r["sigma"] for r in rs), "ex": max(r["ex"] for r in rs), "ey": max(r["ey"] for r in rs)}
        png = next((r.get("png") for r in rs if r.get("png")), None)
        return m, png


def write_table(path, table, meta):
    rows = []
    for ctx in CTX:
        sp_rows = ",\n".join(f"    {sp}: [{', '.join(f'{k:.4f}' for k in table[ctx][sp])}]" for sp in SPECIES)
        rows.append(f"  {ctx}: {{\n{sp_rows}\n  }}")
    js = ("/* GENERATED by tools/size_calibrate.py -- do not edit by hand; re-run the script (through tests/tools/gate.py).\n"
          " * SPRITES_SIZE_NORM[context][species][iv] = the zoom that gives this sprite its context's target DRAWN size: the\n"
          " * luminance-weighted 2-D standard deviation of its light about its centroid (light below linear luminance 0.02 cut),\n"
          " * at 0.8 GB, steady working, no tasks, no network (timeline g_calib). Read by prototype/visitors_runtime.js\n"
          " * (creature(): one zoom about the creature's reported centre; its hit radius, lights, nav and labels follow).\n"
          " * Contexts: live = app/stage.html (live=1); hero / tile / form = app/settings.js (norm=hero|tile|form).\n"
          f" * Targets (CSS px): {json.dumps(meta['target'])}; live measured at Size slider {meta['live_size']}.\n"
          f" * Residual spread, max/min sigma per context: {json.dumps(meta['spread'])} (before: {json.dumps(meta.get('spread_before', {}))}).\n"
          " */\n(function (G) {\nG.SPRITES_SIZE_NORM = {\n" + ",\n".join(rows) + "\n};\n})(this);\n")
    path.write_text(js)


def read_table(path):
    if not path.exists(): return None
    s = path.read_text(); a, b = s.index("G.SPRITES_SIZE_NORM = ") + len("G.SPRITES_SIZE_NORM = "), s.rindex("};") + 1
    import re
    body = re.sub(r"(\w+):", r'"\1":', s[a:b]); return json.loads(body)


def sheet(pngs, ctx, out):
    from PIL import Image, ImageDraw
    ims = {k: Image.open(io.BytesIO(base64.b64decode(v.split(",", 1)[1]))).convert("RGB") for k, v in pngs.items()}
    cw, ch = next(iter(ims.values())).size; pad, lab = 4, 120
    S = Image.new("RGB", (lab + 8 * (cw + pad), len(SPECIES) * (ch + pad)), (30, 30, 34)); d = ImageDraw.Draw(S)
    for r, sp in enumerate(SPECIES):
        d.text((4, r * (ch + pad) + ch // 2 - 6), sp, fill=(200, 200, 200))
        for iv in range(8):
            im = ims.get((sp, iv))
            if im: S.paste(im, (lab + iv * (cw + pad), r * (ch + pad)))
    S.save(out)


def spread(ms):
    v = [m["sigma"] for m in ms.values()]; return round(max(v) / min(v), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(SPR)); ap.add_argument("--measure-only", action="store_true")
    ap.add_argument("--tag", default="after"); ap.add_argument("--contexts", default=",".join(CTX))
    ap.add_argument("--before", default=None, help="report.json of a --measure-only run of the pre-calibration tree (targets)")
    ap.add_argument("--rounds", type=int, default=6)
    a = ap.parse_args()
    try: live_size = float(subprocess.check_output(["defaults", "read", "com.mandrake.sprites", "size"], text=True).strip())
    except Exception: live_size = 1.0
    outdir = storage() / "sprites/size-calibration"; outdir.mkdir(parents=True, exist_ok=True)
    ctxs = a.contexts.split(",")
    R = Renderer(a.root, live_size)
    try:
        if a.measure_only:
            rep = {"live_size": live_size, "thr": THR, "ctx": {}}
            for ctx in ctxs:
                ms, pngs = {}, {}
                for sp in SPECIES:
                    for iv in range(8):
                        m, png = R.measure(ctx, sp, iv, sheet=True); ms[f"{sp}/{iv}"] = m; pngs[(sp, iv)] = png
                sheet(pngs, ctx, outdir / f"sheet_{ctx}_{a.tag}.png")
                rep["ctx"][ctx] = {"spread": spread(ms), "median": statistics.median(m["sigma"] for m in ms.values()), "m": ms}
                print(ctx, "spread", rep["ctx"][ctx]["spread"], "median", round(rep["ctx"][ctx]["median"], 2), flush=True)
            (outdir / f"report_{a.tag}.json").write_text(json.dumps(rep, indent=1)); return
        before = json.loads(Path(a.before).read_text()) if a.before else None
        path = Path(a.root) / "prototype/size_norm.js"
        table = read_table(path) or {c: {sp: [1.0] * 8 for sp in SPECIES} for c in CTX}
        for c in CTX: table.setdefault(c, {sp: [1.0] * 8 for sp in SPECIES})
        meta = {"target": {}, "spread": {}, "live_size": live_size, "spread_before": {}}
        old = read_table(path)
        if old is not None and path.exists():
            hdr = path.read_text(); import re
            m = re.search(r"Targets \(CSS px\): (\{.*?\});", hdr); meta["target"] = json.loads(m.group(1)) if m else {}
            m = re.search(r"\(before: (\{.*?\})\)", hdr); meta["spread_before"] = json.loads(m.group(1)) if m else {}
            m = re.search(r"per context: (\{.*?\}) \(before", hdr); meta["spread"] = json.loads(m.group(1)) if m else {}
        rep = {"live_size": live_size, "thr": THR, "ctx": {}}
        for ctx in ctxs:
            cell = CTX[ctx]; tgt = None; ms = {}
            if before: meta["spread_before"][ctx] = before["ctx"][ctx]["spread"]
            for rnd in range(a.rounds):
                ms = {}
                for sp in SPECIES:
                    for iv in range(8): ms[(sp, iv)], _ = R.measure(ctx, sp, iv)
                if tgt is None:   # live: the pre-calibration median (the screen does not jump); Settings: this context's median
                    tgt = before["ctx"][ctx]["median"] if (before and ctx == "live") else statistics.median(m["sigma"] for m in ms.values())
                err = max(abs(m["sigma"] / tgt - 1) for m in ms.values())
                print(f"{ctx} round {rnd}: target {tgt:.2f} spread {spread({k: v for k, v in ms.items()})} max err {err:.3f}", flush=True)
                if ctx != "live":   # the most spread-out sprite must still fit its cell (6% margin each side)
                    over = max(max(m["ex"] / (cell[0] * 0.47), m["ey"] / (cell[1] * 0.47)) for m in ms.values())
                    if over > 1.0: tgt /= over; err = 1; print(f"  {ctx}: largest sprite overflows the cell x{over:.3f}; target -> {tgt:.2f}", flush=True)
                if err < TOL: break
                for (sp, iv), m in ms.items(): table[ctx][sp][iv] = round(table[ctx][sp][iv] * tgt / m["sigma"], 4)
                meta["target"][ctx] = round(tgt, 2); write_table(path, table, meta)
            meta["target"][ctx] = round(tgt, 2); meta["spread"][ctx] = spread(ms); write_table(path, table, meta)
            pngs = {}
            for sp in SPECIES:
                for iv in range(8): _, pngs[(sp, iv)] = R.measure(ctx, sp, iv, sheet=True)
            sheet(pngs, ctx, outdir / f"sheet_{ctx}_{a.tag}.png")
            rep["ctx"][ctx] = {"target": tgt, "spread": spread(ms), "m": {f"{k[0]}/{k[1]}": v for k, v in ms.items()}}
            print(ctx, "done: spread", spread(ms), "->", outdir / f"sheet_{ctx}_{a.tag}.png", flush=True)
        (outdir / f"report_{a.tag}.json").write_text(json.dumps(rep, indent=1))
    finally:
        R.close()


if __name__ == "__main__":
    main()
