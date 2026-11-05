#!/usr/bin/env python3
"""Movement and terrain (owner rulings 2026-11-01; was ~/agent-storage/sprites/live/verify/move_test.py, which printed FAIL
but exited 0). Per species, one session: (a) a focused window dropped over it -> it ends outside, visible; (b) a focus
splitting the screen -> it never crosses to the other side; (c) a focus leaving a 80 px sliver -> hidden or not
squeezed into it; (d) no jitter; (e) it prefers bare desktop to a non-focused window. One headless Chromium.
Args: species to run (default all five). Exit 0 = pass."""
import json, sys
from playwright.sync_api import sync_playwright
from harness import check, done, url, one_session, Layer, SPECIES

base, proj = one_session()
W, H = 1728, 1117
def inside(p, r): return r[0] < p[0] < r[0] + r[2] and r[1] < p[1] < r[1] + r[3]
with sync_playwright() as pw:
    b = pw.chromium.launch()
    def run(sp, steps):
        pg = b.new_page(viewport={"width": W, "height": H}); pg.goto(url()); pg.wait_for_timeout(300)
        cast = {"projects": {proj: {"concept": sp, "iv": 1, "hex": "#55aaff"}}}
        pg.evaluate(f"SpritesStage.setSize({W},{H}); SpritesStage.setCast({json.dumps(cast)}); SpritesStage.update({json.dumps(base)})")
        pg.wait_for_timeout(1500); fr = Layer(pg, sp); traj = []
        for st in steps:
            if "wins" in st:
                ws = [{"x": r[0], "y": r[1], "w": r[2], "h": r[3], "pid": 1} for r in st["wins"]]; f = st.get("focus")
                fj = "null" if not f else json.dumps({"x": f[0], "y": f[1], "w": f[2], "h": f[3]})
                pg.evaluate(f"SpritesStage.setWindows({json.dumps(ws)}); SpritesStage.setFocus({fj})")
            if "place" in st: fr.evaluate(f"V._def.place(V, V.sessions[0].id, {st['place'][0]}, {st['place'][1]})")
            for _ in range(st.get("secs", 0) * 10):
                r = fr.evaluate("(() => { const s = V.sessions[0], q = __report().reports[s.id]; return q ? [q.x, q.y, q.r, V.alpha(s.id)] : null; })()")
                if r: traj.append(r)
                pg.wait_for_timeout(100)
        pg.close(); return traj
    for sp in sys.argv[1:] or SPECIES:
        F = [300, 150, 900, 800]
        t = run(sp, [{"wins": [], "secs": 3}, {"place": [700, 500]}, {"wins": [F], "focus": F, "secs": 10}]); e = t[-1]
        check(not inside(e, F) and e[3] > 0.5, f"{sp} evict: ends outside the focus, visible {[round(v) for v in e[:3]]} a={e[3]:.2f}")
        F2 = [600, 40, 500, 1050]
        t = run(sp, [{"wins": [], "secs": 1}, {"place": [250, 500]}, {"wins": [F2], "focus": F2, "secs": 14}])
        mx = max(p[0] for p in t[20:]); check(mx <= F2[0], f"{sp} split: stays left of the focus (max x {round(mx)} <= {F2[0]})")
        ys = [p[1] for p in t[-30:]]; flips = sum(1 for i in range(2, len(ys)) if (ys[i] - ys[i-1]) * (ys[i-1] - ys[i-2]) < -0.25)
        check(flips <= 4, f"{sp} no jitter: y reversals in the last 3 s = {flips} (<= 4)")
        # Sliver (R1-SPEC S2: the old check also passed a false "no room"). Hand-derived: the visible frame is y 44..1031
        # (stage TOP 44, BOT 86); this focus covers y 80..1080, leaving a 36 px band, narrower than any creature's FIT
        # extent (2 x (r + 10) >= 52 px). Nothing fits anywhere, so the only right answer is hidden.
        F3 = [0, 80, 1728, 1000]
        t = run(sp, [{"wins": [], "secs": 1}, {"wins": [F3], "focus": F3, "secs": 8}]); e = t[-1]
        check(e[3] < 0.2, f"{sp} sliver: nothing fits, hidden (y {round(e[1])} r {round(e[2])} a {e[3]:.2f})")
        # Strip: a near-maximised focus (0,30,1480x1087) leaves x 1480..1728 bare (248 px), which fits every species, so a
        # creature evicted from mid-screen must end VISIBLE and in that strip, not faded in the menu-bar band.
        F4 = [0, 30, 1480, 1087]
        t = run(sp, [{"wins": [], "secs": 1}, {"place": [875, 300]}, {"wins": [F4], "focus": F4, "secs": 10}]); e = t[-1]
        if __import__("os").environ.get("DBG"): print([[round(v, 2) for v in p] for p in t[::10]])
        check(e[3] > 0.5 and e[0] - e[2] >= F4[0] + F4[2] - 1, f"{sp} strip: room exists, ends visible in it (x {round(e[0])} r {round(e[2])} a {e[3]:.2f})",
              open_finding="S2-SPEC c3" if sp == "c3_sigils" else None)   # c3 in Chromium ended at x 1380 r 36 once (node passes); open
        Wn = [0, 33, 1728, 700]
        t = run(sp, [{"wins": [], "secs": 1}, {"place": [860, 400]}, {"wins": [Wn], "focus": None, "secs": 10}]); e = t[-1]
        check(e[1] > Wn[1] + Wn[3], f"{sp} terrain: leaves a big non-focus window for bare desktop (y {round(e[1])} > {Wn[1] + Wn[3]})")
    # Needs-you (R1-SPEC S1): a creature resting below a focus (200,120,1328x700) turns needs-you; on its way to the knock
    # spot its hit disc (postHits: max(18, r)) must never overlap the focused window, where it would capture clicks.
    def needs_run(sp):
        pg = b.new_page(viewport={"width": W, "height": H}); pg.goto(url()); pg.wait_for_timeout(300)
        cast = {"projects": {proj: {"concept": sp, "iv": 1, "hex": "#55aaff"}}}; F = [200, 120, 1328, 700]
        pg.evaluate(f"SpritesStage.setSize({W},{H}); SpritesStage.setCast({json.dumps(cast)}); SpritesStage.update({json.dumps(base)})")
        pg.wait_for_timeout(1000); fr = Layer(pg, sp)
        pg.evaluate(f"SpritesStage.setWindows([{{x:200,y:120,w:1328,h:700,pid:1}}]); SpritesStage.setFocus({{x:200,y:120,w:1328,h:700}})")
        fr.evaluate("V._def.place(V, V.sessions[0].id, 1000, 1000)"); pg.wait_for_timeout(2500)
        nb = json.loads(json.dumps(base)); nb["sessions"][0]["attention"] = {"state": "needs_you"}
        pg.evaluate(f"SpritesStage.update({json.dumps(nb)})"); bad = n = 0
        for _ in range(100):
            for h in pg.evaluate("__stage.allHits()"):
                n += 1; dx = max(F[0] - h["x"], 0, h["x"] - F[0] - F[2]); dy = max(F[1] - h["y"], 0, h["y"] - F[1] - F[3])
                if (dx * dx + dy * dy) ** 0.5 < h["r"]: bad += 1
            pg.wait_for_timeout(100)
        pg.close(); return bad, n
    for sp in sys.argv[1:] or SPECIES:
        bad, n = needs_run(sp)
        check(n > 0 and bad == 0, f"{sp} needs-you: hit disc never over the focus on the way to the knock spot ({bad}/{n} samples)")
    b.close()
done()
