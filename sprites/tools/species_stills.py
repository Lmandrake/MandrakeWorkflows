#!/usr/bin/env python3
"""Deterministic stills of every species, for a "did my edit change any other species" byte check.

  python3 tools/species_stills.py --out <dir> [--pieces c1_choir,...] [--root <a sprites/ tree>]
  python3 tools/species_stills.py --compare <dirA> <dirB>

Each still is one fresh page and `window.__renderAt(t)` (the runtime re-simulates 0..t on a fixed clock, so the
frame is a pure function of the page and its URL). Two families per piece:
  scen_<scenario>   the gallery scenarios at 640x400, dpr 2, t = 4.5
  tile_iv<N>        the Settings tile path (app/settings.js): g_cast, 112x112, hue 200, iv N, t = 4.5
One browser, sequential renders (no render farm). Writes PNGs plus MANIFEST.json (sha256 per still).
"""
import argparse, functools, hashlib, http.server, json, socketserver, sys, threading
from pathlib import Path

SPR = Path(__file__).resolve().parents[1]
ALL = ["c1_choir", "c2_siphon", "c3_sigils", "c4_kaleido", "c5_fireflies", "c6_night"]
SCEN = ["g_idle", "g_cpu", "g_net", "g_needs", "g_strain", "g_vpn", "g_variants"]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def serve(root):
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
    srv.daemon_threads = True; threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]


def render(out, pieces, root=SPR):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True); port = serve(root); man, errs = {}, []
    jobs = [(p, f"scen_{s}", f"tl={s}&w=640&h=400&chrome=0&hud=0&dpr=2", 640, 400) for p in pieces for s in SCEN]
    jobs += [(p, f"tile_iv{i}", f"tl=g_cast&w=112&h=112&chrome=0&hue=200&iv={i}&autostart=0&dpr=2", 112, 112) for p in pieces for i in range(8)]
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for piece, name, q, w, h in jobs:
            pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
            pg.on("pageerror", lambda e, k=f"{piece}/{name}": errs.append(f"{k}: {e}"))
            pg.goto(f"http://127.0.0.1:{port}/prototype/{piece}.html?{q}")
            pg.wait_for_function("typeof window.__renderAt === 'function'", timeout=20000)
            pg.evaluate("window.__renderAt(4.5)")
            fn = out / f"{piece}__{name}.png"; fn.write_bytes(pg.screenshot(type="png"))
            man[fn.name] = hashlib.sha256(fn.read_bytes()).hexdigest(); pg.close()
        b.close()
    (out / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True))
    print(f"{len(man)} stills -> {out}" + (f"; PAGE ERRORS {errs[:5]}" if errs else ""))
    return 1 if errs else 0


def compare(a, b):
    A = json.loads((a / "MANIFEST.json").read_text()); B = json.loads((b / "MANIFEST.json").read_text())
    common = sorted(set(A) & set(B)); diff = [k for k in common if A[k] != B[k]]
    print(f"{len(common)} common stills, {len(common) - len(diff)} byte-identical, {len(diff)} differ"
          + (f": {diff}" if diff else "") + (f"; only in one side: {sorted(set(A) ^ set(B))}" if set(A) ^ set(B) else ""))
    return 1 if diff else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--pieces", default=",".join(ALL))
    ap.add_argument("--compare", nargs=2); ap.add_argument("--root", default=str(SPR),
                    help="serve this sprites/ tree instead of the checkout (e.g. a git-archive of a commit)")
    a = ap.parse_args()
    sys.exit(compare(Path(a.compare[0]), Path(a.compare[1])) if a.compare else render(Path(a.out), a.pieces.split(","), Path(a.root)))
