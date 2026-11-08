#!/usr/bin/env python3
"""Owner, 2026-11-05: a per-project COLOUR picker and a FOCUS toggle in Settings.

ONE colour per project (his explicit choice): the picker moves the project's canonical hex, and the hue
drives the existing --hue / hexHue() path, so the hero and the species stills follow it. Focus writes the
launches.md Focus column through the host. Both post to the host when Waypoint is present
({setProjectColour} / {setProjectFocus}, answered by SpritesSettings.writeResult) and fall back to the
browser's own store when there is no bridge, as Demo Mode does.

A project with no launch alias cannot be coloured or focused with Waypoint present: the controls are
disabled and the window SAYS why rather than silently doing nothing.

A stub webkit.messageHandlers records posts and answers them. One headless Chromium. Exit 0 = pass."""
import json
from playwright.sync_api import sync_playwright
from harness import check, done, PORT, errors_on

# The stub answers every project write with success unless __fail is set to a message.
STUB = """
window.__posts = []; window.__fail = null;
window.webkit = { messageHandlers: { settings: { postMessage: m => {
  window.__posts.push(JSON.parse(JSON.stringify(m)));
  const o = m.setProjectColour || m.setProjectFocus;
  if (o) setTimeout(() => SpritesSettings.writeResult({id: o.id, error: window.__fail}), 0);
} } } };
"""
TABLE = [
  {"key": "lodestar", "name": "Lodestar", "dir": "/x/Lodestar", "alias": "Lodestar", "hex": "#FFCA42", "focus": True},
  {"key": "orchard-mandrake", "name": "Orchard_Mandrake", "dir": "/x/Orchard", "alias": "Orchard", "hex": "#CB50F0", "focus": True},
  # an active project with NO launch alias: it has no launch row, so it cannot be focused or coloured
  {"key": "hestia", "name": "Hestia", "dir": "/x/Hestia", "alias": None, "hex": "#EECC22", "focus": True},
]
INIT = {"cast": {"projects": {}}, "projects": TABLE, "behaviors": {}, "demo": False, "size": 1, "hasWaypoint": True}

with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1100, "height": 760}); errs = errors_on(pg)
    pg.add_init_script(STUB)
    pg.goto(f"http://127.0.0.1:{PORT}/app/settings.html"); pg.wait_for_timeout(600)
    pg.evaluate(f"SpritesSettings.init({json.dumps(INIT)})"); pg.wait_for_timeout(300)

    # ---- the controls exist, on the per-project pane, and show the selected project's values
    check(pg.evaluate("!!document.getElementById('clr')"), "Settings has a project colour picker (#clr)")
    check(pg.evaluate("!!document.getElementById('focusSeg')"), "Settings has a focus toggle (#focusSeg)")
    val = pg.evaluate("[document.getElementById('clr').value, document.getElementById('clrHex').textContent]")
    check(val[0].lower() == "#ffca42" and val[1] == "#FFCA42", f"the picker opens on Lodestar's own hex: {val}")
    aria = lambda sel: pg.evaluate(f"document.querySelector({sel!r}).getAttribute('aria-checked')")
    check(aria("#focusSeg button[data-f='1']") == "true", "Lodestar is shown as a focus project")

    # ---- setting a colour posts the project's canonical hex, and drives the existing hue path
    pg.evaluate("window.__posts.length = 0")
    pg.evaluate("const c = document.getElementById('clr'); c.value = '#2244aa'; c.dispatchEvent(new Event('input'))")
    pg.wait_for_timeout(500)
    posts = [p["setProjectColour"] for p in pg.evaluate("window.__posts") if "setProjectColour" in p]
    check(len(posts) == 1 and posts[0]["hex"] == "#2244AA",
          f"a new colour posts setProjectColour once, with the uppercase hex: {posts}")
    check(posts and posts[0].get("alias") == "Lodestar" and posts[0].get("key") == "lodestar",
          f"the write names the launch alias AND the project key: {posts}")
    check(pg.evaluate("document.getElementById('clrHex').textContent") == "#2244AA", "the swatch shows the new hex")
    hue = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--hue').trim()")
    check(hue.lower() in ("#2244aa", "rgb(34, 68, 170)"), f"the new colour drives --hue (the live preview path): {hue!r}")
    # the hero cross-fades, so the NEWEST iframe is the one rendered at the new hue (the old one lingers ~650ms)
    pg.wait_for_timeout(900)
    src = pg.evaluate("[...document.querySelectorAll('#heroSlot iframe')].map(f => f.src).pop() || ''")
    check("hue=225" in src, f"the hero preview re-rendered at the new hue (#2244AA is hue 225): {src[-44:]!r}")
    tiles = pg.evaluate("[...document.querySelectorAll('#species .tile, #variants .tile')].map(t => (t._args || [])[2])")
    check(tiles and all(h == 225 for h in tiles if h is not None),
          f"the species and form stills re-rendered at the new hue: {sorted(set(tiles))}")
    check(not any("saveCast" in p and "setProjectColour" not in p for p in pg.evaluate("window.__posts")[:1]),
          "the colour is not smuggled in as a sprite-only cast field")

    # ---- a failed write reverts the control and says so
    pg.evaluate("window.__fail = 'launches.md is read-only'; window.__posts.length = 0")
    pg.evaluate("const c = document.getElementById('clr'); c.value = '#00ff88'; c.dispatchEvent(new Event('input'))")
    pg.wait_for_timeout(600)
    shown = pg.evaluate("[document.getElementById('clrHex').textContent, document.getElementById('focusWhy').textContent]")
    check(shown[0] == "#2244AA" and "read-only" in shown[1],
          f"a refused colour write reverts the swatch and reports the reason: {shown}")
    pg.evaluate("window.__fail = null")

    # ---- the focus toggle writes the Focus column
    pg.evaluate("window.__posts.length = 0"); pg.click("#focusSeg button[data-f='0']"); pg.wait_for_timeout(300)
    f = [p["setProjectFocus"] for p in pg.evaluate("window.__posts") if "setProjectFocus" in p]
    check(len(f) == 1 and f[0]["focus"] is False and f[0]["alias"] == "Lodestar",
          f"Not now posts setProjectFocus false for the alias: {f}")
    check(aria("#focusSeg button[data-f='0']") == "true", "the toggle follows the click")
    pg.evaluate("window.__posts.length = 0"); pg.click("#focusSeg button[data-f='1']"); pg.wait_for_timeout(300)
    f = [p["setProjectFocus"] for p in pg.evaluate("window.__posts") if "setProjectFocus" in p]
    check(len(f) == 1 and f[0]["focus"] is True, f"Focus posts setProjectFocus true: {f}")
    pg.evaluate("window.__fail = 'no launch alias'; window.__posts.length = 0")
    pg.click("#focusSeg button[data-f='0']"); pg.wait_for_timeout(400)
    check(aria("#focusSeg button[data-f='1']") == "true" and "no launch alias" in pg.evaluate("document.getElementById('focusWhy').textContent"),
          "a refused focus write reverts the toggle and reports the reason")
    pg.evaluate("window.__fail = null")

    # ---- a project with no launch alias: disabled, and it says why (never a silent no-op)
    rows = pg.evaluate("[...document.querySelectorAll('#projects li .nm')].map(e => e.textContent)")
    if "Hestia" in rows:
        pg.click(f"#projects li:nth-child({rows.index('Hestia') + 1})"); pg.wait_for_timeout(250)
        pg.evaluate("window.__posts.length = 0")
        state = pg.evaluate("[document.getElementById('clr').disabled, document.getElementById(\"focusSeg\").children[0].disabled, document.getElementById('focusWhy').textContent]")
        check(state[0] and state[1], f"a project with no launch alias has both controls disabled: {state[:2]}")
        check("cannot be a focus project" in state[2], f"and the window says why: {state[2]!r}")
        pg.evaluate("document.getElementById('focusSeg').children[0].click(); const c = document.getElementById('clr'); c.value='#111111'; c.dispatchEvent(new Event('input'))")
        pg.wait_for_timeout(300)
        check(pg.evaluate("window.__posts.length") == 0, "and nothing is posted for it")
    else:
        check(False, f"Hestia listed: {rows}")

    # ---- no Waypoint: the same two controls persist to the browser's own store (the host's local file)
    p2 = b.new_page(); errs2 = errors_on(p2)
    p2.goto(f"http://127.0.0.1:{PORT}/app/settings.html?demo=1&nowp=local")
    p2.evaluate("localStorage.clear()"); p2.reload(); p2.wait_for_timeout(700)
    listed = p2.evaluate("[...document.querySelectorAll('#projects li .nm')].map(e => e.textContent)")
    check(len(listed) > 0, f"no Waypoint: projects are still listed, so there is something to colour: {listed}")
    if listed:
        p2.evaluate("const c = document.getElementById('clr'); c.value = '#3366cc'; c.dispatchEvent(new Event('input'))")
        p2.wait_for_timeout(500)
        store = p2.evaluate("JSON.parse(localStorage.getItem('sprites.projects') || 'null')")
        hexes = [e.get("hex") for e in (store or {}).get("projects", {}).values()]
        check("#3366CC" in hexes, f"no Waypoint: the colour is saved to the local store: {store}")
        check(p2.evaluate("!document.getElementById('clr').disabled"),
              "no Waypoint: the picker is enabled (an alias is a Waypoint concept)")
        p2.click("#focusSeg button[data-f='1']"); p2.wait_for_timeout(400)
        store = p2.evaluate("JSON.parse(localStorage.getItem('sprites.projects') || 'null')")
        check(any(e.get("focus") is True for e in (store or {}).get("projects", {}).values()),
              f"no Waypoint: focus is saved to the local store: {store}")
        # it survives a reload, which is the whole point of a settings file
        p2.reload(); p2.wait_for_timeout(700)
        check(p2.evaluate("document.getElementById('clrHex').textContent") == "#3366CC",
              "no Waypoint: the saved colour comes back after a reload")

    # ---- nowp=1 (nothing to list): the browse-only view, with no per-project controls
    p3 = b.new_page(); errs3 = errors_on(p3)
    p3.goto(f"http://127.0.0.1:{PORT}/app/settings.html?demo=1&nowp=1"); p3.wait_for_timeout(700)
    hid = p3.evaluate("[document.getElementById('clrRow').classList.contains('hidden'), document.getElementById('focusRow').classList.contains('hidden')]")
    check(all(hid), f"the browse-only view offers neither control (there is no project to set): {hid}")

    check(not errs, f"no page errors in the Waypoint view {errs[:3]}")
    check(not errs2, f"no page errors in the local view {errs2[:3]}")
    check(not errs3, f"no page errors in the browse view {errs3[:3]}")
    b.close()
done()
