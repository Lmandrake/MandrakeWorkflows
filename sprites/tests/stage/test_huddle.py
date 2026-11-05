#!/usr/bin/env python3
"""LOST huddle (owner ruling 2026-11-01 08:15; was ~/agent-storage/sprites/live/verify/huddle_test.py, which asserted
nothing). Per species, 4 sessions, link fine, then LOST (VPN down off site and the API unreachable): the flock gathers
at one huddle point outside the focused window. Bars, set from the spec's "gather together", not from a run: by 8 s
every creature is within 120 px of the point and the mean distance is under half of what it was at 0.3 s.
One headless Chromium. Args: species (default all five). Exit 0 = pass."""
import json, sys, time
from playwright.sync_api import sync_playwright
from harness import check, done, url, feed, layer_errors, errors_on, Layer, SPECIES

up = feed("--scenario", "busy", "--at", "30")
up["sessions"] = [s for s in up["sessions"] if s.get("managed", True)][:4]
down = feed("--scenario", "lost", "--at", "30"); down["sessions"] = up["sessions"]; down["projects"] = up["projects"]
names = [s["project"] for s in up["sessions"]]
FOC = [329, 33, 1000, 900]
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for sp in sys.argv[1:] or SPECIES:
        pg = b.new_page(viewport={"width": 1728, "height": 1117}); errs = errors_on(pg)
        pg.goto(url("stale=0&dpr=1&vpndebounce=0")); pg.wait_for_timeout(400)
        cast = {"projects": {n: {"concept": sp, "iv": i, "hex": "#5599ff"} for i, n in enumerate(names)}}
        f = json.dumps({"x": FOC[0], "y": FOC[1], "w": FOC[2], "h": FOC[3]})
        pg.evaluate(f"SpritesStage.setSize(1728,1117); SpritesStage.setCast({json.dumps(cast)}); SpritesStage.setWindows([Object.assign({f}, {{pid:1}})]); SpritesStage.setFocus({f}); SpritesStage.update({json.dumps(up)})")
        pg.wait_for_timeout(4000); fr = Layer(pg, sp)
        check(fr.evaluate("V.huddlePt") is None, f"{sp}: no huddle point while the link is fine")
        pg.evaluate(f"SpritesStage.update({json.dumps(down)})"); t0 = time.time(); d = {}
        for mk in (0.3, 8):
            while time.time() - t0 < mk: pg.wait_for_timeout(50)
            d[mk] = fr.evaluate("(() => { const p = V.huddlePt, R = Object.values(__report().reports); if (!p || !R.length) return null; const ds = R.map(q => Math.hypot(q.x - p[0], q.y - p[1])); return [p, ds.reduce((a, b) => a + b, 0) / ds.length, Math.max(...ds), ds.length]; })()")
        if not check(d[0.3] and d[8], f"{sp}: a huddle point exists once LOST"): pg.close(); continue
        p, m8, x8, n = d[8]
        check(n == 4 and x8 <= 120 and m8 < 0.5 * d[0.3][1], f"{sp}: gathered by 8 s, max {x8:.0f} px (<= 120), mean {m8:.0f} < half of {d[0.3][1]:.0f}")
        check(not (FOC[0] - 110 < p[0] < FOC[0] + FOC[2] + 110 and FOC[1] - 110 < p[1] < FOC[1] + FOC[3] + 110), f"{sp}: huddle point {p} is >= 110 px from the focus")
        e = layer_errors(pg) + errs; check(not e, f"{sp}: no errors {e[:2]}")
        pg.close()
    b.close()
done()
