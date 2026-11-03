#!/usr/bin/env python3
"""Review R1 #13: Settings has show/hide and the meeting-mode hotkey (SHIP_PLAN Settings: "Also in the window:
show/hide, meeting-mode hotkey"). Host contract written into app/settings.js: init({..., hidden, meeting, hotkey,
hotkeyOK}); the switches post {setHidden: bool} and {setMeeting: bool}; SpritesSettings.setVisibility({hidden, meeting})
mirrors a change made from the menu or the hotkey. Hand truth: App.swift registers kVK_ANSI_S with control+option+command,
which macOS writes as ⌃⌥⌘S. A stub webkit.messageHandlers records posts. One headless Chromium. Exit 0 = pass."""
import json
from playwright.sync_api import sync_playwright
from harness import check, done, PORT, errors_on

STUB = "window.__posts = []; window.webkit = { messageHandlers: { settings: { postMessage: m => window.__posts.push(JSON.parse(JSON.stringify(m))) } } };"
INIT = {"cast": {"projects": {}}, "projects": [{"name": "Lodestar", "hex": "#FFCA42"}], "behaviors": {}, "demo": False, "size": 1}
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1100, "height": 760}); errs = errors_on(pg)
    pg.add_init_script(STUB)
    pg.goto(f"http://127.0.0.1:{PORT}/app/settings.html"); pg.wait_for_timeout(600)
    pg.evaluate(f"SpritesSettings.init({json.dumps(dict(INIT, hidden=False, meeting=False, hotkey='⌃⌥⌘S', hotkeyOK=True))})")
    pg.evaluate("SpritesSettings.showTab('behaviours')"); pg.wait_for_timeout(200)
    has = pg.evaluate("[!!document.getElementById('showSw'), !!document.getElementById('meetSw'), (document.getElementById('meetKey') || {}).textContent || '']")
    check(has[0], "Behaviours tab has a Show Sprites switch (#showSw)")
    check(has[1], "Behaviours tab has a Meeting Mode switch (#meetSw)")
    check(has[2] == "⌃⌥⌘S", f"the meeting-mode hotkey is shown as ⌃⌥⌘S: {has[2]!r}")
    if has[0] and has[1]:
        aria = lambda i: pg.evaluate(f"document.getElementById('{i}').getAttribute('aria-checked')")
        check(aria("showSw") == "true" and aria("meetSw") == "false", "init hidden=false, meeting=false: Show on, Meeting off")
        pg.evaluate("window.__posts.length = 0"); pg.click("#showSw"); pg.click("#meetSw")
        posts = pg.evaluate("window.__posts")
        check({"setHidden": True} in posts and {"setMeeting": True} in posts, f"clicks post setHidden true and setMeeting true: {posts}")
        check(aria("showSw") == "false" and aria("meetSw") == "true", "switches follow the clicks")
        check(not any("saveBehaviors" in p for p in posts), "show/hide and meeting are not saved as behaviours (host state, not a file)")
        pg.evaluate("SpritesSettings.setVisibility({hidden: false, meeting: false})")
        check(aria("showSw") == "true" and aria("meetSw") == "false", "setVisibility mirrors a menu or hotkey change")
        pg.evaluate("window.__posts.length = 0; SpritesSettings.setVisibility({hidden: true, meeting: true})")
        check(pg.evaluate("window.__posts.length") == 0, "mirroring a host change posts nothing back (no echo loop)")
        pg.evaluate(f"SpritesSettings.init({json.dumps(dict(INIT, hidden=True, meeting=False, hotkey='⌃⌥⌘S', hotkeyOK=False))})")
        pg.evaluate("SpritesSettings.showTab('behaviours')"); pg.wait_for_timeout(100)
        note = pg.evaluate("document.getElementById('meetKey').closest('.demoRow').textContent")
        check(aria("showSw") == "false" and "unavailable" in note.lower(), f"init hidden=true; hotkey not registered says so: {note.strip()[:90]!r}")
    # browser mode (no bridge): switches still work and persist to localStorage, as Demo Mode does
    p2 = b.new_page(); p2.goto(f"http://127.0.0.1:{PORT}/app/settings.html?demo=1"); p2.evaluate("localStorage.clear()"); p2.reload(); p2.wait_for_timeout(600)
    p2.evaluate("SpritesSettings.showTab('behaviours')")
    if p2.evaluate("!!document.getElementById('meetSw')"):
        p2.click("#meetSw"); check(p2.evaluate("localStorage.getItem('sprites.meeting')") == "true", "browser mode: meeting saved to localStorage")
    else: check(False, "browser mode: meeting switch present")
    check(not errs, f"no page errors {errs[:2]}")
    b.close()
done()
