"""QA for the Sprites backdrops (app/backdrops/backdrops.sl through its WebGL path): per-backdrop stats and a sheet.

Usage: nice -n 19 python3 backdrop_qa.py [--w 1728 --h 1117] [--t 0] [--n 1,2,..] [--out DIR] [--frames N --span S]
Writes DIR/bdNN.png (true), a contact sheet (true + BOOSTED, labelled) and DIR/stats.json. --frames renders N frames over
S seconds of design time for one --n (motion check: per-frame speed of the brightest features). One process, headless.
"""
import argparse, base64, functools, http.server, io, json, os, socketserver, threading, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1] / "app/backdrops"
import sys as _sys; from pathlib import Path as _P; _sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "tests/tools")); import load_rule  # owner rule: renders are load

def srgb_decode(c):
    c = c.astype(np.float32) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def stats(a):
    lin = srgb_decode(a[..., :3]); L = lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722
    m = a[..., :3].reshape(-1, 3).mean(0)
    return {"max_code": int(a[..., :3].max()), "p999_code": int(np.percentile(a[..., :3].max(-1), 99.9)),
            "mean_lum_pct": round(float(L.mean()) * 100, 3), "p999_lum_pct": round(float(np.percentile(L, 99.9)) * 100, 3),
            "red_cast": bool(m[0] > max(m[1], m[2]) + 0.25), "mean_rgb": [round(float(v), 2) for v in m]}

def grab(pg, n, t, boost=False, nc=False):
    pg.evaluate(f"__draw({n}, {t}, {{boost: {str(boost).lower()}, nc: {str(nc).lower()}}})")
    url = pg.evaluate("document.getElementById('c').toDataURL('image/png')")
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(url.split(',')[1]))).convert("RGB"))

def main():
    load_rule.require()   # only on on-site network without the VPN; unknown = refuse
    ap = argparse.ArgumentParser(); ap.add_argument("--w", type=int, default=1728); ap.add_argument("--h", type=int, default=1117)
    ap.add_argument("--t", type=float, default=0); ap.add_argument("--n", default=""); ap.add_argument("--frames", type=int, default=0)
    ap.add_argument("--span", type=float, default=60); ap.add_argument("--out", default=str(Path.home() / "agent-storage/art/backgrounds/live"))
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cat = json.loads((ROOT / "catalog.json").read_text())["backdrops"]
    ns = [int(x) for x in a.n.split(",") if x] or [b["n"] for b in cat]
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT)); h.log_message = lambda *x: None
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), h); srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start(); port = srv.server_address[1]
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--use-gl=angle", "--use-angle=metal"]); pg = b.new_page(viewport={"width": 400, "height": 300})
        pg.goto(f"http://127.0.0.1:{port}/preview.html?n=1&w={a.w}&h={a.h}"); pg.wait_for_function("window.__ready || window.__err", timeout=30000)
        if pg.evaluate("window.__err || null"): raise SystemExit("shader: " + pg.evaluate("window.__err"))
        if a.frames:
            n = ns[0]; fr = [grab(pg, n, a.t + a.span * k / max(1, a.frames - 1)) for k in range(a.frames)]
            for k, f in enumerate(fr): Image.fromarray(f).save(out / f"bd{n:02d}_f{k}.png")
            d = [float(np.abs(fr[k + 1].astype(int) - fr[k].astype(int)).mean()) for k in range(len(fr) - 1)]
            print(json.dumps({"n": n, "mean_abs_code_change_per_step": [round(x, 4) for x in d]})); b.close(); return
        res = {}
        for n in ns:
            img = grab(pg, n, a.t); res[n] = stats(img); Image.fromarray(img).save(out / f"bd{n:02d}.png")
            Image.fromarray(grab(pg, n, a.t, boost=True)).save(out / f"bd{n:02d}_BOOSTED.png")
            print(n, json.dumps(res[n]), flush=True)
        b.close()
    (out / "stats.json").write_text(json.dumps(res, indent=1))
    tw, th, pad = 576, 372, 16; cols = 4; rows = (len(ns) + cols - 1) // cols
    fnt = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 18)
    for tag in ("", "_BOOSTED"):
        S = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + 46) + 70), (0, 0, 0)); d = ImageDraw.Draw(S)
        d.text((pad, 20), "Sprites backdrops (live shader render)" + ("  —  GAMMA-BOOSTED x^0.35, NOT TRUE BRIGHTNESS" if tag else "  —  true values"),
               font=ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 26), fill=(255, 210, 120) if tag else (220, 220, 225))
        for k, n in enumerate(ns):
            r, c = divmod(k, cols); x = pad + c * (tw + pad); y = 70 + r * (th + 46)
            S.paste(Image.open(out / f"bd{n:02d}{tag}.png").resize((tw, th), Image.BOX), (x, y))
            meta = next(m for m in cat if m["n"] == n); st = res[n]
            d.text((x, y + th + 4), f"{meta['id']} {meta['name']} · p99.9 code {st['p999_code']} · mean {st['mean_lum_pct']}%", font=fnt, fill=(200, 200, 205))
        S.save(out / f"backdrops_sheet{tag}.png")
    print(out / "backdrops_sheet.png"); print(out / "backdrops_sheet_BOOSTED.png")

if __name__ == "__main__":
    main()
