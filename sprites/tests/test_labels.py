"""Hover labels: every style draws at every scale and phase; the shortname table is distinct and <= 12 chars; Settings round-trips
labelStyle and the per-project short name. Browser parts use ONE headless Chromium, and skip while the 1-min load is >= 8
(machine rule on the Laptop). Run: python3 -m pytest sprites/tests/test_labels.py"""
import json, os, re, subprocess, functools, http.server, socketserver, threading
from pathlib import Path
import pytest
SPR = Path(__file__).resolve().parents[1]; LAB = SPR / "prototype/labels"
HOME = Path.home()

def registry_projects():
    """Every project name Augur can report: Lodestar sync registry Names, with Waypoint launch aliases where one exists."""
    def rows(path, k1, k2):
        cols = None
        for l in open(path):
            if not l.startswith("|"): continue
            c = [x.strip() for x in l.strip().strip("|").split("|")]
            if k1 in c and k2 in c: cols = c; continue
            if cols is None or set(c[0]) <= set("-: "): continue
            yield dict(zip(cols, c))
    reg, wp_md, la_md = Path(os.environ.get("AUGUR_LODESTAR") or HOME / "dev/Lodestar") / "sync/registry.md", HOME / ".config/waypoint/waypoints.md", HOME / ".config/waypoint/launches.md"
    if not reg.exists(): pytest.skip("no Lodestar registry on this machine")
    wp = {d["Name"]: d["Path"] for d in rows(wp_md, "Name", "Path")} if wp_md.exists() else {}
    alias = {}
    if la_md.exists():
        for d in rows(la_md, "Name", "Focus"):
            p = wp.get(d.get("Waypoint", ""))
            if p: alias.setdefault(os.path.expanduser(p), d["Name"])
    out, seen = [], set()
    for d in rows(reg, "Name", "Path"):
        if d["Name"] in seen: continue
        seen.add(d["Name"]); out.append({"name": d["Name"], "alias": alias.get(os.path.expanduser(d["Path"]))})
    return out

def test_shortnames_distinct_and_short():
    P = registry_projects()
    js = ("const S=require(process.argv[1]);const P=JSON.parse(process.argv[2]);const r=S.shortNames(P);"
          "console.log(JSON.stringify(P.map(p=>[p.name,S.display(r.short[p.name])])))")
    rows = json.loads(subprocess.check_output(["node", "-e", js, str(LAB / "shortname.js"), json.dumps(P)]))
    shorts = [s for _, s in rows]
    assert len(rows) >= 20
    assert len({s.lower() for s in shorts}) == len(shorts), [s for s in shorts if shorts.count(s) > 1]
    assert all(0 < len(s) <= 12 for s in shorts), [s for s in shorts if len(s) > 12]
    d = dict(rows)
    assert d.get("KestrelWorks_Mandrake") == "KesMine" and d.get("Lodestar") == "Lodestar"

def test_override_wins():
    js = ("const S=require(process.argv[1]);console.log(JSON.stringify(S.shortNames([{name:'MandrakeWorkflows',short:'Flows'},"
          "{name:'MandrakeVisualize'}]).short))")
    r = json.loads(subprocess.check_output(["node", "-e", js, str(LAB / "shortname.js")]))
    assert r == {"MandrakeWorkflows": "Flows", "MandrakeVisualize": "Visualize"}

@pytest.fixture(scope="module")
def page():
    if os.getloadavg()[0] >= 8: pytest.skip("1-min load >= 8: browser tests deferred (machine rule)")
    pw_mod = pytest.importorskip("playwright.sync_api")
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SPR)); h.log_message = lambda *a: None
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), h); srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with pw_mod.sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1100, "height": 760})
        pg.errs = []; pg.on("pageerror", lambda e: pg.errs.append(str(e)))
        pg.base = f"http://127.0.0.1:{srv.server_address[1]}"
        yield pg
        b.close()
    srv.shutdown()

def test_every_style_draws(page):
    if not (LAB / "assets/sprites.json").exists(): pytest.skip("mockup assets (a desktop screenshot) are not in this checkout")
    page.goto(page.base + "/prototype/labels/mockup.html?opt=1&e=1&ui=0"); page.wait_for_function("window.__done === true")
    res = page.evaluate("""() => { const c = document.createElement('canvas'); c.width = 600; c.height = 400; const x = c.getContext('2d');
      const out = []; for (const style of SpritesLabels.STYLES) for (const scale of [0.5, 1, 2]) for (const phase of ['in', 'hold', 'out'])
        for (const p of [0, 0.3, 0.99]) for (const ground of ['dark', 'bright']) for (const hex of ['#FFCA42', undefined]) {
          x.clearRect(0, 0, 600, 400);
          try { SpritesLabels.draw(x, { style, name: 'KestrelWorks_Mandrake', short: 'KesMine', hex, x: 300, y: 200, r: 30 * scale, scale, t: 1.7,
                phase, p, ground, motes: [[290, 195], [310, 205]], W: 600, H: 400 });
            const d = x.getImageData(0, 0, 600, 400).data; let lit = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 20) lit++;
            out.push([style, scale, phase, p, ground, !!hex, lit]); }
          catch (e) { out.push([style, scale, phase, p, ground, !!hex, 'ERR ' + e.message]); } }
      return out; }""")
    errs = [r for r in res if isinstance(r[-1], str)]
    assert not errs, errs[:5]
    # held labels must put ink on the canvas, in every style and scale
    blank = [r for r in res if r[2] == "hold" and r[-1] < 30]
    assert not blank, blank[:5]
    assert not page.errs, page.errs

def test_settings_round_trip(page):
    page.goto(page.base + "/app/settings.html?demo=1"); page.evaluate("localStorage.clear()"); page.reload(); page.wait_for_timeout(800)
    assert page.evaluate("SpritesSettings.labelStyle") == "constellation"           # default
    page.evaluate("SpritesSettings.showTab('labels')"); page.wait_for_timeout(300)
    assert page.locator("#labels .cell").count() == 5
    page.click("#labels .cell[data-style=orbit]")
    saved = page.evaluate("JSON.parse(localStorage.getItem('sprites.behaviors'))")
    assert saved["labelStyle"] == "orbit" and saved["hoverName"] is True
    page.evaluate("SpritesSettings.showTab('species')"); page.fill("#short", "Lode"); page.wait_for_timeout(600)
    cast = page.evaluate("JSON.parse(localStorage.getItem('sprites.cast'))")
    assert any(v.get("short") == "Lode" for v in cast["projects"].values())
    page.reload(); page.wait_for_timeout(800)                                       # re-init from what was saved
    assert page.evaluate("SpritesSettings.labelStyle") == "orbit"
    # host path: init() with behaviors carrying labelStyle, and an unknown style falls back to the default
    page.evaluate("SpritesSettings.init({cast:{projects:{}}, projects:[{name:'Lodestar',hex:'#FFCA42'}], behaviors:{labelStyle:'whisper'}})")
    assert page.evaluate("SpritesSettings.labelStyle") == "whisper"
    page.evaluate("SpritesSettings.init({cast:{projects:{}}, projects:[{name:'Lodestar',hex:'#FFCA42'}], behaviors:{labelStyle:'bogus'}})")
    assert page.evaluate("SpritesSettings.labelStyle") == "constellation"
    assert not page.errs, page.errs

def _node(js, *args):
    return json.loads(subprocess.check_output(["node", "-e", js, *args], text=True))

def test_ground_respects_z_order():
    """S5 (reviews/SPRITES_REVIEW_R1_SPEC.md): windows arrive FRONT TO BACK; the ground is the first window under the label
    box's centre. Hand-derived: a dark terminal in front of a maximised browser, label over the terminal -> dark; the same
    windows with the browser in front -> bright; a centre over no window -> dark (wallpaper)."""
    js = ("const S=require(process.argv[1]).SpritesLabels||globalThis.SpritesLabels;"
          "const term={x:100,y:100,w:400,h:300,dark:true},web={x:0,y:0,w:1600,h:1000},box=[200,200,100,80];"
          "console.log(JSON.stringify([S.groundAt([term,web],box),S.groundAt([web,term],box),S.groundAt([term],[600,600,50,50]),"
          "S.groundAt([web],[1580,980,100,80]),S.groundAt([],box)]))")
    # [terminal front, browser front, over wallpaper, centre just past the browser's corner, no windows]
    assert _node(js, str(LAB / "labels.js")) == ["dark", "bright", "dark", "dark", "dark"]
