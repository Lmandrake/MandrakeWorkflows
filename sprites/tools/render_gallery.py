#!/usr/bin/env python3
"""Render every (piece x scenario) as a looping mp4 for the side-by-side gallery.

  python3 tools/render_gallery.py [--pieces c1_choir,...] [--scen g_cpu,...] [--fps 30] [--jobs 5]

Load-adaptive (see --max-load); run under `nice -n 10` (taskpolicy -b pins it to the efficiency cores: ~20x slower). Deterministic: drives each piece with window.__advanceTo(t) at fixed steps (no wall clock), screenshots,
pipes PNGs to ffmpeg. Output: <agent storage>/sprites/gallery/v/<piece>__<scenario>.mp4 + .jpg poster.
"""
import argparse, json, re, subprocess, sys, threading, http.server, functools, socketserver
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIECES = ROOT / "prototype"
OUT = Path.home() / "ClaudeWork/sprites/gallery/v"
ALL = ["c1_choir", "c2_siphon", "c3_sigils", "c4_kaleido", "c5_fireflies"]


def scenarios():
    s = (PIECES / "scenarios.js").read_text()
    return json.loads(s[s.index("=") + 1:].rstrip().rstrip(";"))


def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(PIECES))
    h.log_message = lambda *a: None
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), h); srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


def render_one(port, piece, sid, dur, fps, scale):
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    mp4 = OUT / f"{piece}__{sid}.mp4"
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 640, "height": 400}, device_scale_factor=scale)
        pg.on("pageerror", lambda e: print("pageerror", piece, sid, e, flush=True))
        pg.goto(f"http://127.0.0.1:{port}/{piece}.html?tl={sid}&w=640&h=400&chrome=0&hud=1&dim=0.55&dpr={scale}")
        pg.wait_for_function("typeof window.__advanceTo === 'function'", polling=100, timeout=15000)
        pg.wait_for_timeout(300)
        ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(fps),
                               "-c:v", "png", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21",
                               "-preset", "medium", "-threads", "2", "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
        n = int(round(dur * fps)); poster = None
        for i in range(n + 1):
            pg.evaluate(f"window.__advanceTo({i / fps})")
            png = pg.screenshot(type="png")
            ff.stdin.write(png)
            if i == int(n * 0.6): poster = png
        ff.stdin.close(); ff.wait()
        errs = pg.evaluate("window.__errors")
        b.close()
    if poster:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "png_pipe", "-i", "-", "-q:v", "4",
                        str(mp4.with_suffix(".jpg"))], input=poster)
    return piece, sid, ff.returncode, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pieces", default=",".join(ALL)); ap.add_argument("--scen", default="")
    ap.add_argument("--fps", type=int, default=30); ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--scale", type=float, default=1.5)
    ap.add_argument("--max-load", type=float, default=0)
    a = ap.parse_args()
    sc = scenarios(); ids = a.scen.split(",") if a.scen else list(sc)
    port = serve(); jobs = [(p, s) for p in a.pieces.split(",") for s in ids]
    bad = 0
    # Adaptive: --jobs is a ceiling. A job starts only while the 1-min load average is under --max-load
    # (default 80% of cores), so renders fill idle capacity and back off when the owner's machine is busy.
    import os, time
    gate = threading.Lock(); maxload = a.max_load or 0.8 * os.cpu_count()
    def gated(j):
        with gate:
            while os.getloadavg()[0] >= maxload: time.sleep(5)
            time.sleep(20)   # let the previous job's load register before the next check
        return render_one(port, j[0], j[1], sc[j[1]]["duration"], a.fps, a.scale)
    with ThreadPoolExecutor(a.jobs) as ex:
        for piece, sid, rc, errs in ex.map(gated, jobs):
            ok = rc == 0 and not errs; bad += not ok
            print(("ok  " if ok else "FAIL"), piece, sid, "" if ok else (rc, errs[:2]), flush=True)
    print(f"{len(jobs) - bad}/{len(jobs)} rendered -> {OUT}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
