#!/usr/bin/env python3
"""Review R1 #1 and #2 in Settings: the host hands Settings the project table (app/projects.js build: key, name, alias, hex,
focus); one row per focus entry, labelled by its launch alias; a choice saves under the project_key (the key the stage
reads), and a cast saved before under the alias moves to the key. Short-name placeholder = the stage's rule over the
whole table. Hand truth: the table below, from the data files (Fixer response join); Orchard_Mandrake auto-shortens to
"Orchard"; KestrelWorks (the team repo) is a focus row distinct from KesMine (key kestrel, not a focus row).
A stub webkit.messageHandlers records posts. One headless Chromium. Exit 0 = pass."""
import json
from playwright.sync_api import sync_playwright
from harness import check, done, PORT, errors_on

STUB = "window.__posts = []; window.webkit = { messageHandlers: { settings: { postMessage: m => window.__posts.push(JSON.parse(JSON.stringify(m))) } } };"
TABLE = [
  {"key": "orchard-mandrake", "name": "Orchard_Mandrake", "dir": "/x/Orchard_Mandrake", "alias": "Orchard", "hex": "#CB50F0", "focus": True},
  {"key": "kestrel", "name": "KestrelWorks_Mandrake", "dir": "/x/KestrelWorks_Mandrake", "alias": "KesMine", "hex": "#40C888", "focus": False},
  {"key": "kestrel-team", "name": "KestrelWorks", "dir": "/x/KestrelWorks", "alias": "KestrelWorks", "hex": "#40C888", "focus": True},
  {"key": None, "name": "MandrakeVisualize", "dir": "/x/visualize", "alias": "MandrakeVisualize", "hex": "#00CCFF", "focus": True},
  {"key": "lodestar", "name": "Lodestar", "dir": "/x/Lodestar", "alias": "Lodestar", "hex": "#FFCA42", "focus": True},
]
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1100, "height": 760}); errs = errors_on(pg)
    pg.add_init_script(STUB)
    pg.goto(f"http://127.0.0.1:{PORT}/app/settings.html"); pg.wait_for_timeout(600)
    cast = {"projects": {"Orchard": {"concept": "c2_siphon", "iv": 3, "hex": "#CB50F0"}}}
    pg.evaluate(f"SpritesSettings.init({json.dumps({'cast': cast, 'projects': TABLE, 'behaviors': {}})})"); pg.wait_for_timeout(300)
    rows = pg.evaluate("[...document.querySelectorAll('#projects li .nm')].map(e => e.textContent)")
    # R2-SPEC #3: a focus launch with no project_key (MandrakeVisualize: its registry row is retired) can match no session, so
    # a choice there would be saved where no sprite reads it: Settings does not list it
    check(rows == ["Orchard", "KestrelWorks", "Lodestar"], f"one row per focus entry with a project_key, labelled by alias: {rows}")
    # Orchard's row shows the cast saved earlier under the alias (c2_siphon form 3)
    cur = pg.evaluate("document.getElementById('sname').textContent")
    check(cur == "Siphonophores", f"a cast saved before under the alias Orchard is honoured: {cur}")
    ph = pg.evaluate("document.getElementById('short').placeholder")
    check(ph == "Orchard", f"Orchard's automatic short name is the stage's: {ph!r}")
    pg.evaluate("window.__posts.length = 0"); pg.click("#variants .cell:nth-child(6)"); pg.wait_for_timeout(100)
    saves = [p["saveCast"] for p in pg.evaluate("window.__posts") if "saveCast" in p]
    last = saves[-1]["projects"] if saves else {}
    check("orchard-mandrake" in last and last["orchard-mandrake"].get("iv") == 5 and last["orchard-mandrake"].get("concept") == "c2_siphon",
          f"a choice saves under the project_key orchard-mandrake: {last}")
    check("Orchard" not in last, f"the old alias-keyed entry moved to the key: {sorted(last)}")
    pg.click("#projects li:nth-child(2)"); pg.wait_for_timeout(100); pg.evaluate("window.__posts.length = 0")
    pg.click("#species .cell:nth-child(4)"); pg.wait_for_timeout(100)
    saves = [p["saveCast"] for p in pg.evaluate("window.__posts") if "saveCast" in p]; last = saves[-1]["projects"] if saves else {}
    check(last.get("kestrel-team", {}).get("concept") == "c4_kaleido" and "kestrel" not in last,
          f"the team row KestrelWorks saves under kestrel-team, not KesMine's key: {sorted(last)}")
    pg.click("#projects li:nth-child(1)"); pg.wait_for_timeout(100); pg.fill("#short", "Aim"); pg.wait_for_timeout(600)
    saves = [p["saveCast"] for p in pg.evaluate("window.__posts") if "saveCast" in p]; last = saves[-1]["projects"] if saves else {}
    check(last.get("orchard-mandrake", {}).get("short") == "Aim", f"the short-name override saves under the key: {last.get('orchard-mandrake')}")
    # the old host shape ({name, hex}, no table) still works: keyed by name
    pg.evaluate("SpritesSettings.init({cast:{projects:{}}, projects:[{name:'Lodestar',hex:'#FFCA42'}]})"); pg.wait_for_timeout(200)
    check(pg.evaluate("[...document.querySelectorAll('#projects li .nm')].map(e => e.textContent)") == ["Lodestar"], "a plain [{name, hex}] list still lists its rows")
    check(not errs, f"no page errors: {errs[:3]}")
    b.close()
done()
