#!/usr/bin/env python3
"""Stage adapter and render health (was ~/agent-storage/sprites/live/verify/stage_test.py + stale_test.py, which asserted
nothing). Expected values are derived by hand from tests/fixtures/augur_test_snapshot.json and the owner's rulings
(augur/DESIGN.md s11: a stale block is absent; ruling 3: lights on a project's OLDEST session; ruling 4: a ghost per
burning project with no session). One headless Chromium. Exit 0 = pass."""
import copy, json, sys
from playwright.sync_api import sync_playwright
from harness import check, done, url, feed, fixture, errors_on, layer_errors

AUG = fixture("augur_test_snapshot.json")
L, SP, OL = "88586@1793461778", "43901@1793472837", "70112@1793505000"   # Lodestar, SidePulse, ollama (unmanaged)
W, H = 1728, 1117
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": W, "height": H}); errs = errors_on(pg)
    pg.goto(url()); pg.wait_for_timeout(500)
    ad = lambda snap, now="undefined": pg.evaluate(f"__stage.adaptState({json.dumps(snap)}, {now})")

    # 1. the adapter on the real Augur sample (staleness ignored with ?stale=0)
    a = ad(AUG); s = a["S"]["s"]; ids = [x["id"] for x in a["sessions"]]
    check(ids == [L, SP, OL], f"augur sample: 3 sessions, no ghost (Lodestar has a session): {ids}")
    check(s[L].get("burning") == 14 and s[L]["state"] == "working" and s[L]["cpu"] == 0.41 and s[L]["procs"] == 1,
          f"Lodestar: working, cpu 0.41, satellites = tasks.background 1 (C5), lights 14: {s[L]}")
    check(s[SP]["state"] == "needs" and "burning" not in s[SP] and "rx" not in s[SP],
          f"SidePulse: needs_you -> needs, burning 0 -> no lights, net unknown -> no rx: {s[SP]}")
    check(s[OL]["state"] == "idle" and [x for x in a["sessions"] if x["id"] == OL][0]["white"] is True,
          "ollama: unmanaged -> white, stopped -> idle")
    check(a["S"]["net"].get("linkRaw") == "ok" and a["S"]["net"]["mbps"] == 14.0, f"net: vpn up -> link ok, mbps 8.1+5.9: {a['S']['net']}")
    check(abs(a["S"]["m"]["level"] - 1.3 * 0.75) < 1e-9, "strain score 1.3 -> level 0.975")

    # 2. a whole stale snapshot: sessions kept, every measurement absent (stale page, now past valid_until)
    p2 = b.new_page(); p2.goto(url("dpr=1")); p2.wait_for_timeout(300)
    st = p2.evaluate(f"__stage.adaptState({json.dumps(AUG)}, {AUG['valid_until'] + 1})"); p2.close()
    check([x["id"] for x in st["sessions"]] == [L, SP, OL] and all(v == {} for v in st["S"]["s"].values()),
          f"stale snapshot: 3 sessions kept, all values absent: {st['S']['s']}")
    check(st["S"]["m"] == {} and "linkRaw" not in st["S"]["net"], "stale snapshot: no machine values, no link cue")
    # one stale block only: attention past its valid_until while the rest is fresh
    one = copy.deepcopy(AUG); now = 1793509003.0; one["valid_until"] = now + 10
    for x in one["sessions"]:
        for k in ("load", "tasks", "net"):
            if k in x: x[k]["valid_until"] = now + 10
    one["sessions"][0]["attention"]["valid_until"] = now - 1
    p3 = b.new_page(); p3.goto(url("dpr=1")); p3.wait_for_timeout(300)
    o = p3.evaluate(f"__stage.adaptState({json.dumps(one)}, {now})")["S"]["s"]; p3.close()
    check("state" not in o[L] and o[L].get("cpu") == 0.41, f"one stale block is absent, the rest kept: {o[L]}")

    # 3. ghosts and lights on demo_feed scenarios (hand truth from SCENARIOS in tools/demo_feed.py)
    g = ad(feed("--scenario", "lodestar_closed", "--at", "30"))
    check("ghost:lodestar" in [x["id"] for x in g["sessions"]], "lodestar_closed: Lodestar burning 6, no session -> ghost:lodestar")
    g = ad(feed("--scenario", "lodestar_closed_quiet", "--at", "30"))
    check(not any(x["ghost"] for x in g["sessions"]), "lodestar_closed_quiet: burning 0 -> no ghost")
    g = ad(feed("--scenario", "ghosts", "--at", "30"))
    check(sorted(x["id"] for x in g["sessions"] if x["ghost"]) == ["ghost:machinist", "ghost:projectcert", "ghost:projectdial"], "ghosts: one per burning project")
    g = ad(feed("--scenario", "twin", "--at", "30")); lit = [k for k, v in g["S"]["s"].items() if v.get("burning")]
    check(lit == ["90011@1793497011"], f"twin: lights only on SidePulse's oldest session (90011): {lit}")
    g = ad(feed("--scenario", "unmanaged", "--at", "30"))
    check([x["white"] for x in g["sessions"]] == [True, True, False] and not any(x["ghost"] for x in g["sessions"]), "unmanaged: two white, one managed, no ghost")

    # 4. live render: demo mode, feed churn, scenarios, the sample -> layers draw, hits match sessions, no errors
    pg.evaluate(f"SpritesStage.setSize({W},{H}); SpritesStage.setFocus({{x:200,y:150,w:800,h:600}})")
    def live(name, wait):
        pg.wait_for_timeout(wait)
        ids = sorted(x["id"] for x in pg.evaluate("__stage.model.sessions")); hits = sorted(h["id"] for h in pg.evaluate("__stage.allHits()"))
        e = layer_errors(pg) + list(errs); errs.clear()
        check(ids and hits == ids and not e, f"{name}: {len(ids)} sessions, every one has a hit, no errors {e[:2]}")
    pg.evaluate("SpritesStage.setDemo(true)"); live("demo mode", 5000); pg.evaluate("SpritesStage.setDemo(false)")
    for t in (0, 200, 400):
        pg.evaluate(f"SpritesStage.update({json.dumps(feed('--at', str(t)))})"); live(f"feed t={t}", 3000)
    for sc in ("lodestar_closed", "twin", "unmanaged", "vpn_down", "lost", "strain"):
        pg.evaluate(f"SpritesStage.update({json.dumps(feed('--scenario', sc, '--at', '30'))})"); live(f"scenario {sc}", 3000)
    pg.evaluate(f"SpritesStage.update({json.dumps(AUG)})"); live("augur sample", 4000)
    # 5. continuity: a session leaves; survivors keep their place. A re-init without carry would teleport them (hundreds
    # of px); their own drift over the same 0.4 s, measured just before, is the control. Allowed: control + 15 px.
    pos = lambda: {h["id"]: (h["x"], h["y"]) for h in pg.evaluate("__stage.allHits()")}
    dist = lambda a, b: {k: round(max(abs(a[k][0] - b[k][0]), abs(a[k][1] - b[k][1]))) for k in (SP, OL) if k in a and k in b}
    p0 = pos(); pg.wait_for_timeout(400); p1 = pos(); ctrl = dist(p0, p1)
    aug2 = dict(AUG); aug2["sessions"] = AUG["sessions"][1:]
    pg.evaluate(f"SpritesStage.update({json.dumps(aug2)})"); pg.wait_for_timeout(400)
    moved = dist(p1, pos())
    check(len(moved) == 2 and all(moved[k] <= ctrl.get(k, 0) + 15 for k in moved), f"continuity: survivors moved {moved} px (own drift {ctrl})")
    pg.wait_for_timeout(2500)
    check("ghost:lodestar" in [x["id"] for x in pg.evaluate("__stage.model.sessions")], "Lodestar's session left with burning 14 -> its ghost")
    # 6. stage-level hover label (R1 #1, which shipped because only shortname.js was tested): hover a long-named
    # session and record what the stage hands SpritesLabels.draw. Hand truth: shortname.js's rule drops "Mandrake",
    # so Orchard_Mandrake shows "Orchard"; a cast short name overrides it.
    lg = feed("--scenario", "calm", "--at", "30"); lg["projects"] = []
    lg["sessions"] = [s for s in lg["sessions"] if s.get("managed", True)][:1]; lg["sessions"][0]["project"] = "Orchard_Mandrake"
    lg["sessions"][0]["project_key"] = "orchard_mandrake"
    def hover_short(cast):
        p4 = b.new_page(viewport={"width": W, "height": H}); p4.goto(url()); p4.wait_for_timeout(300)
        p4.evaluate(f"SpritesStage.setSize({W},{H}); SpritesStage.setCast({json.dumps(cast)}); SpritesStage.update({json.dumps(lg)})"); p4.wait_for_timeout(2500)
        p4.evaluate("(() => { window.__shorts = []; const d = SpritesLabels.draw; SpritesLabels.draw = (c, o, ...r) => { window.__shorts.push(o.short); return d(c, o, ...r); }; })()")
        h = p4.evaluate("__stage.allHits()")[0]; p4.evaluate(f"SpritesStage.setCursor({{x:{h['x']},y:{h['y']}}})"); p4.wait_for_timeout(2000)
        out = p4.evaluate("[...new Set(window.__shorts)]"); p4.close(); return out
    got = hover_short({"projects": {"Orchard_Mandrake": {"concept": "c1_choir", "iv": 0, "hex": "#CB50F0"}}})
    check(got == ["Orchard"], f"hover label for Orchard_Mandrake reads 'Orchard': {got}")
    got = hover_short({"projects": {"Orchard_Mandrake": {"concept": "c1_choir", "iv": 0, "hex": "#CB50F0", "short": "Aim"}}})
    check(got == ["Aim"], f"the cast short name 'Aim' overrides it: {got}")
    b.close()
done()
