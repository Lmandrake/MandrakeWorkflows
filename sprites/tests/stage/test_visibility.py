#!/usr/bin/env python3
"""Per-project visibility (owner, 2026-11-04: ProjectCert "is an outside project"; "Show/Hide/Hide @ Location" in the
Settings window). cast.projects[key].visibility: "hide" drops the project's sessions and ghost; "hide_at_work" drops them
while machine.vpn.on_site is true, and an unknown on_site keeps the last known one. Settings' segmented control writes
it. One headless Chromium. Exit 0 = pass."""
import copy, json
from playwright.sync_api import sync_playwright
from harness import check, done, url, feed, PORT, errors_on

base = feed("--scenario", "ghosts", "--at", "30")
def snap(site):
    d = copy.deepcopy(base); v = d["machine"].setdefault("vpn", {"observed_at": d["written_at"], "valid_until": d["written_at"] + 30, "state": "up"})
    if site is None: v.pop("on_site", None)
    else: v["on_site"] = site
    return d
keys = lambda pg, site: sorted({x["key"] for x in pg.evaluate(f"__stage.adaptState({json.dumps(snap(site))}).sessions")})
STUB = "window.__posts = []; window.webkit = { messageHandlers: { settings: { postMessage: m => window.__posts.push(JSON.parse(JSON.stringify(m))) } } };"
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(url("stale=0&dpr=1")); pg.wait_for_timeout(300)
    allk = keys(pg, False); check("projectcert" in allk and "dialexis" in allk, f"control: projectcert and dialexis present: {allk}")
    pg.evaluate("SpritesStage.setCast({projects: {projectcert: {visibility: 'hide_at_work'}, dialexis: {visibility: 'hide'}}})")
    off = keys(pg, False); check("projectcert" in off and "dialexis" not in off, f"off site: hide_at_work shows, hide hides: {off}")
    on = keys(pg, True); check("projectcert" not in on and "dialexis" not in on and len(on) == len(allk) - 2, f"at work: both hidden, rest kept: {on}")
    check("projectcert" not in keys(pg, None), "on_site unknown after on site: still hidden (last known)")
    check("projectcert" in keys(pg, False), "back off site: shows again")
    pg.close()
    pg = b.new_page(viewport={"width": 1100, "height": 760}); errs = errors_on(pg); pg.add_init_script(STUB)
    pg.goto(f"http://127.0.0.1:{PORT}/app/settings.html"); pg.wait_for_timeout(600)
    pg.evaluate("SpritesSettings.init({cast: {projects: {projectcert: {concept: 'c4_kaleido', iv: 6, hex: '#3388EE'}}}, projects: [{key: 'projectcert', name: 'ProjectCert', hex: '#3388EE'}], behaviors: {}, demo: false, size: 1})")
    pg.wait_for_timeout(200)
    on_ = lambda: pg.evaluate("[...document.querySelectorAll('#visSeg button')].filter(b => b.getAttribute('aria-checked') === 'true').map(b => b.dataset.v)")
    check(on_() == ["show"], f"default is Show: {on_()}")
    pg.click("#visSeg button[data-v=hide_at_work]"); last = pg.evaluate("window.__posts.filter(p => p.saveCast).pop()")
    check(last and last["saveCast"]["projects"]["projectcert"] == {"concept": "c4_kaleido", "iv": 6, "hex": "#3388EE", "visibility": "hide_at_work"} and on_() == ["hide_at_work"], f"Hide @ Work saves visibility: {last}")
    pg.click("#visSeg button[data-v=show]"); last = pg.evaluate("window.__posts.filter(p => p.saveCast).pop()")
    check("visibility" not in last["saveCast"]["projects"]["projectcert"], "Show clears it")
    check(not errs, f"no page errors {errs[:2]}")
    b.close()
done()
