#!/usr/bin/env python3
"""Side-by-side gallery: concepts as columns, one-indicator scenarios as rows, every cell a looping video.

  python3 tools/build_gallery.py        # then tools/serve_gallery.sh

Writes <agent storage>/sprites/gallery/{index.html,v/,p/}. Not blind (the owner asked to compare
named concepts openly). Ratings, notes and the project cast save to feedback/gallery.decisions.json via the
review-sheets sidecar on every change. p/ holds live copies of the pieces for the cast preview.
"""
import json, shutil, subprocess, threading, functools, http.server, socketserver, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIECES = ROOT / "prototype"
G = Path.home() / "agent-storage/sprites/gallery"
CONCEPTS = [("c1_choir", "Mothership Choir"), ("c2_siphon", "Siphonophores"), ("c3_sigils", "Living Sigils"),
            ("c4_kaleido", "Kaleidoscope Seeds"), ("c5_fireflies", "Firefly Murmurations")]
ROWS = ["g_variants", "g_projects", "g_idle", "g_cpu", "g_mem", "g_tasks", "g_needs", "g_strain", "g_net",
        "g_vpn", "g_play"]
ROWNAME = {"g_variants": "Individualizer", "g_projects": "Your projects", "g_idle": "Idle", "g_cpu": "CPU",
           "g_mem": "Memory", "g_tasks": "Background tasks", "g_needs": "Needs you", "g_strain": "Machine strain",
           "g_net": "Network", "g_vpn": "VPN lost", "g_play": "Play"}


def waypoint_colours():
    seen = {}
    for l in (Path.home() / ".config/waypoint/launches.md").read_text().splitlines():
        if not l.startswith("| ") or "active" not in l: continue
        name = l.strip("| ").split("|")[0].strip(); m = re.search(r"\]10;#([0-9A-Fa-f]{6})", l)
        if m and name not in seen: seen[name] = "#" + m.group(1).upper()
    return seen


def variant_names():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(PIECES)); h.log_message = lambda *a: None
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 320, "height": 200})
        for pid, _ in CONCEPTS:
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/{pid}.html?tl=g_variants&w=320&h=200&chrome=0&dpr=1")
            pg.wait_for_function("typeof window.__advanceTo === 'function'", polling=100, timeout=15000)
            out[pid] = pg.evaluate("window.VARIANT_NAMES || []")
        b.close()
    srv.shutdown(); return out


def main():
    sc = json.loads((PIECES / "scenarios.js").read_text().split("=", 1)[1].rstrip().rstrip(";"))
    # p2 = the current pieces (live round 2); p1 = round-1 pieces from git (d4196e5) for the round switch.
    for d in ("p", "p2"):
        (G / d).mkdir(parents=True, exist_ok=True)
        for f in PIECES.iterdir():
            if f.suffix in (".html", ".js", ".png"): shutil.copy(f, G / d / f.name)
    # p1 = round-1 pieces, a frozen snapshot (MandrakeWorkflows d4196e5) kept in agent storage.
    cfg = {"concepts": [{"id": p, "name": n} for p, n in CONCEPTS],
           "rows": [{"id": r, "name": ROWNAME[r], "title": sc[r]["title"], "hud": sc[r]["hud"]} for r in ROWS],
           "variants": variant_names(), "projects": waypoint_colours()}
    html = (ROOT / "tools/gallery_template.html").read_text().replace("/*CFG*/null", json.dumps(cfg))
    (G / "index.html").write_text(html)
    missing = [f"{p}__{r}" for p, _ in CONCEPTS for r in ROWS if not (G / "v" / f"{p}__{r}.mp4").exists()]
    print(f"gallery -> {G / 'index.html'}; variants: " + ", ".join(f"{k}:{len(v)}" for k, v in cfg["variants"].items())
          + (f"; MISSING {len(missing)} videos" if missing else "; all videos present"))


if __name__ == "__main__":
    main()
