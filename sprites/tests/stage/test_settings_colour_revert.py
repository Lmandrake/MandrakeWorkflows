#!/usr/bin/env python3
"""Owner, 2026-11-08 ~4:50 PM: "In settings, when I pick a new color, then try to adjust its darkness, it reverts back to
the previous color instead of darkening the new color I picked."

Proven cause (host log, SPRITES_DEBUG_SETTINGS=1): every successful colour write was answered {error: "no handler"}
(app/macos/Settings.swift), so the page's revert pushed the OLD hex into the input while NSColorPanel was open, and the
next brightness drag started from it. The host half is checked in tests/swift/host; this file holds the page to:
  a pick then a darker pick ends at the darker NEW colour, for the project and the Aether picker, even when the host
  answers the first write with an error (a stale answer) after the second pick; and a stale re-init mid-edit moves
  neither picker, nor replaces the Aether input under the panel.
One headless Chromium page, stub host. SETTINGS_JS=<path> serves another settings.js (to prove the checks fail on the
old code). Exit 0 = pass."""
import json, os
from playwright.sync_api import sync_playwright
from harness import check, done, PORT, errors_on

STUB = """
window.__posts = []; window.__answer = {};   // id -> error to answer with; absent = success
window.webkit = { messageHandlers: { settings: { postMessage: m => { window.__posts.push(JSON.parse(JSON.stringify(m))); } } } };
window.__reply = (id, err) => SpritesSettings.writeResult({ id, error: err || null });
"""
TABLE = [{"key": "lodestar", "name": "Lodestar", "dir": "/x/L", "alias": "Lodestar", "hex": "#FFCA42", "focus": True},
         {"key": "ember28", "name": "Ember28", "dir": "/x/H", "alias": "Ember28", "hex": "#8888EE", "focus": True}]
INIT = {"cast": {"projects": {"ember28": {"concept": "c2_siphon", "iv": 6, "hex": "#8888EE"}}}, "projects": TABLE,
        "behaviors": {"aether": {"colour": "#0433ff"}}, "hasWaypoint": True}
pick = lambda sel, v: f"(() => {{ const c = {sel}; c.value = {v!r}; c.dispatchEvent(new Event('input', {{bubbles: true}})); }})()"
CLR = "document.getElementById('clr')"
AE = "document.querySelector('[aria-label=\"Aether colour\"]')"
writes = lambda pg: pg.evaluate("__posts.filter(m => m.setProjectColour).map(m => m.setProjectColour)")

with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1100, "height": 760}); errs = errors_on(pg)
    pg.add_init_script(STUB)
    alt = os.environ.get("SETTINGS_JS")
    if alt: pg.route("**/app/settings.js", lambda r: r.fulfill(body=open(alt).read(), content_type="text/javascript"))
    pg.goto(f"http://127.0.0.1:{PORT}/app/settings.html"); pg.wait_for_timeout(500)
    pg.evaluate(f"SpritesSettings.init({json.dumps(INIT)})"); pg.wait_for_timeout(150)
    pg.evaluate("document.querySelector('#projects li[data-key=ember28]').click()"); pg.wait_for_timeout(100)

    # ---- 1. project colour: pick, the write lands (success), then darken: ends at the darker NEW colour
    pg.evaluate(pick(CLR, "#ff3300")); pg.wait_for_timeout(350)
    w = writes(pg); pg.evaluate(f"__reply({w[-1]['id']!r})"); pg.wait_for_timeout(50)
    pg.evaluate(pick(CLR, "#801a00")); pg.wait_for_timeout(350)
    w = writes(pg); pg.evaluate(f"__reply({w[-1]['id']!r})"); pg.wait_for_timeout(50)
    got = [pg.evaluate(f"{CLR}.value"), pg.evaluate("SpritesSettings.projects.find(p => p.key === 'ember28').hex"), [x["hex"] for x in writes(pg)]]
    check(got[0] == "#801a00" and got[1] == "#801A00" and got[2] == ["#FF3300", "#801A00"], f"project: pick then darken ends at the darker new colour {got}")

    # ---- 2. a stale answer: the first write's ERROR arrives after the second pick; the picker must not move back
    pg.evaluate(pick(CLR, "#2244aa")); pg.wait_for_timeout(350); first = writes(pg)[-1]["id"]
    pg.evaluate(pick(CLR, "#112255")); pg.wait_for_timeout(350); second = writes(pg)[-1]["id"]
    pg.evaluate(f"__reply({first!r}, 'stale failure')"); pg.wait_for_timeout(50)
    got = [pg.evaluate(f"{CLR}.value"), pg.evaluate("SpritesSettings.projects.find(p => p.key === 'ember28').hex")]
    check(got == ["#112255", "#112255".upper()], f"project: an older write's error mid-edit does not revert the picker {got}")
    pg.evaluate(f"__reply({second!r})"); pg.wait_for_timeout(50)
    check(pg.evaluate(f"{CLR}.value") == "#112255", "project: and the newest write's success keeps it")

    # ---- 3. a real failure of the newest write still reverts, to the last colour the host CONFIRMED (#801A00)
    pg.evaluate(pick(CLR, "#00ff00")); pg.wait_for_timeout(350); pg.evaluate(f"__reply({writes(pg)[-1]['id']!r}, 'disk full')"); pg.wait_for_timeout(50)
    got = [pg.evaluate(f"{CLR}.value"), pg.evaluate("document.getElementById('focusWhy').textContent")]
    check(got[0] == "#112255" and "disk full" in got[1], f"project: the newest write failing reverts to the last confirmed colour and says why {got}")

    # ---- 4. a stale host repaint mid-edit (render after a snapshot, with the old hex in hand) does not move it
    pg.evaluate(pick(CLR, "#aa5500")); pg.wait_for_timeout(50)
    pg.evaluate("(() => { const p = SpritesSettings.projects.find(p => p.key === 'ember28'); const h = p.hex; p.hex = '#8888EE'; document.querySelector('#projects li[data-key=ember28]').click(); p.hex = h; })()")
    check(pg.evaluate(f"{CLR}.value") == "#aa5500", f"project: a repaint mid-drag never writes into the open picker {pg.evaluate(CLR + '.value')}")

    # ---- 5. Aether: pick, then a repaint of the grid (a choice click, as a host echo or drift does), then darken
    pg.evaluate("SpritesSettings.showTab('aether')"); pg.wait_for_timeout(100)
    pg.evaluate(f"window.__ae0 = {AE}")
    pg.evaluate(pick(AE, "#ff2200")); pg.wait_for_timeout(50)
    pg.evaluate("[...document.querySelectorAll('#aeGrid .aeOpt')].find(b => b.textContent === 'Reflect').click()"); pg.wait_for_timeout(50)
    same = pg.evaluate(f"window.__ae0 === {AE} && window.__ae0.isConnected")
    check(same, "aether: repainting the grid keeps the SAME colour input (the panel stays bound to it)")
    pg.evaluate(pick("window.__ae0", "#801100")); pg.wait_for_timeout(400)
    saved = [m["saveBehaviors"]["aether"]["colour"] for m in pg.evaluate("__posts") if "saveBehaviors" in m]
    got = [pg.evaluate(f"{AE}.value"), saved[-1] if saved else None]
    check(got == ["#801100", "#801100"], f"aether: pick then darken ends at the darker new colour, on screen and saved {got}")

    # ---- 6. Aether: a stale re-init (behaviours carrying the OLD colour) arriving mid-edit moves nothing
    pg.evaluate(pick("window.__ae0", "#601000")); pg.wait_for_timeout(20)
    pg.evaluate(f"SpritesSettings.init({json.dumps(INIT)}); SpritesSettings.showTab('aether')"); pg.wait_for_timeout(50)
    got = [pg.evaluate(f"{AE}.value"), pg.evaluate(f"window.__ae0 === {AE}")]
    check(got == ["#601000", True], f"aether: a stale host echo mid-edit neither moves nor replaces the input {got}")

    check(not errs, f"no page errors {errs}")
    b.close()
done()
