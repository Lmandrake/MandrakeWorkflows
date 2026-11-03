#!/usr/bin/env python3
"""Review R1 #18 (JS half): the runtime's per-id maps (lastData, prevState, steerSt, navPlan, pull, navA, navVis,
motePts) must not keep sessions that have left while the species layer lives on. Hand truth: after 6 sessions of one
species come and go in turn, with one long-lived session staying, every map holds at most the ids on stage now.
One headless Chromium. Exit 0 = pass."""
import copy, json
from playwright.sync_api import sync_playwright
from harness import check, done, url, feed, Layer, errors_on

SP = "c5_fireflies"
base = feed("--scenario", "churn", "--at", "30")
keep = copy.deepcopy(base["sessions"][0]); keep["managed"] = True
def with_sessions(extra):
    d = copy.deepcopy(base); d["projects"] = []; d["sessions"] = [keep] + extra; return d
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900}); errs = errors_on(pg)
    pg.goto(url()); pg.wait_for_timeout(300)
    others = []
    for i in range(6):
        s = copy.deepcopy(base["sessions"][1]); s["id"] = f"{91000 + i}@{1793490000 + i}"; s["pid"] = 91000 + i; s["project"] = f"Temp{i}"; s["managed"] = True; others.append(s)
    cast = {"projects": {p: {"concept": SP, "iv": 2, "hex": "#66ccff"} for p in [keep["project"]] + [s["project"] for s in others]}}
    pg.evaluate(f"SpritesStage.setSize(1440,900); SpritesStage.setCast({json.dumps(cast)})")
    pg.evaluate("SpritesStage.setWindows([{x:500,y:100,w:400,h:400,pid:1}]); SpritesStage.setFocus({x:500,y:100,w:400,h:400})")
    for s in others:   # each temp session joins, lives 1.5 s (hovered once, so pull/motePts are used), then leaves
        pg.evaluate(f"SpritesStage.update({json.dumps(with_sessions([s]))})"); pg.wait_for_timeout(1500)
        h = [x for x in pg.evaluate("__stage.allHits()") if x["id"] == s["id"]]
        if h: pg.evaluate(f"SpritesStage.setCursor({{x:{h[0]['x']},y:{h[0]['y']}}})"); pg.wait_for_timeout(400); pg.evaluate("SpritesStage.setCursor(null)")
        pg.evaluate(f"SpritesStage.update({json.dumps(with_sessions([]))})"); pg.wait_for_timeout(2200)   # past the 1.6 s fade
    pg.wait_for_timeout(1000)
    m = Layer(pg, SP).evaluate("V.__idMaps ? V.__idMaps() : null")
    if check(m is not None, "runtime exposes V.__idMaps (QA)"):
        live = {keep["id"]}
        for k, ids in m.items():
            extra = sorted(set(ids) - live)
            check(not extra, f"{k}: holds only on-stage ids (extra {extra})")
    check(any(h["id"] == keep["id"] for h in pg.evaluate("__stage.allHits()")), "the long-lived session is still on stage")
    check(not errs, f"no page errors {errs[:2]}")
    b.close()
done()
