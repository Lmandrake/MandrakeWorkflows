#!/usr/bin/env python3
"""Hover follow (owner, 2026-11-01 ~07:10; was ~/agent-storage/sprites/live/verify/hover_follow_test.py): the cursor parked
on a creature -> within 6 px of the cursor at 1.5 s and 4 px at 5 s; dragged into the focused window, the creature
stays outside it. One headless Chromium. Args: species (default: all of harness.SPECIES). Exit 0 = pass."""
import json, math, sys
from playwright.sync_api import sync_playwright
from harness import check, done, url, one_session, SPECIES

base, proj = one_session(); W, H = 1728, 1117
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for sp in sys.argv[1:] or SPECIES:
        pg = b.new_page(viewport={"width": W, "height": H}); pg.goto(url()); pg.wait_for_timeout(300)
        cast = {"projects": {proj: {"concept": sp, "iv": 1, "hex": "#55aaff"}}}
        pg.evaluate(f"SpritesStage.setSize({W},{H}); SpritesStage.setCast({json.dumps(cast)}); SpritesStage.update({json.dumps(base)})"); pg.wait_for_timeout(2500)
        rep = lambda: pg.evaluate(f"(() => {{ const V = __stage.V('{sp}'), q = Object.values(V.__report().reports)[0]; return q && [q.x, q.y, q.r]; }})()")
        r = rep(); cx, cy = r[0] + 0.6 * r[2], r[1] + 0.3 * r[2]
        pg.evaluate(f"SpritesStage.setCursor({{x:{cx},y:{cy}}})")
        pg.wait_for_timeout(1500); q = rep(); d1 = math.hypot(q[0] - cx, q[1] - cy)
        pg.wait_for_timeout(3500); q = rep(); d2 = math.hypot(q[0] - cx, q[1] - cy)
        check(d1 <= 6 and d2 <= 4, f"{sp} follows the cursor: {d1:.1f} px at 1.5 s (<= 6), {d2:.1f} px at 5 s (<= 4)")
        q = rep(); fx = q[0] + q[2] + 20
        pg.evaluate("SpritesStage.setCursor(null)"); pg.wait_for_timeout(300)
        pg.evaluate(f"SpritesStage.setWindows([{{x:{fx},y:0,w:{W - fx},h:{H},pid:1}}]); SpritesStage.setFocus({{x:{fx},y:0,w:{W - fx},h:{H}}})"); pg.wait_for_timeout(1500)
        q = rep(); pg.evaluate(f"SpritesStage.setCursor({{x:{q[0] + 0.5 * q[2]},y:{q[1]}}})"); pg.wait_for_timeout(100)
        pg.evaluate(f"SpritesStage.setCursor({{x:{fx + 40},y:{q[1]}}})"); pg.wait_for_timeout(3000); q2 = rep()
        check(q2[0] <= fx, f"{sp} dragged toward the focus, stays outside it (x {q2[0]:.0f} <= {fx:.0f})")
        pg.close()
    b.close()
done()
