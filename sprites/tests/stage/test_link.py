#!/usr/bin/env python3
"""Three-signal link (was ~/ClaudeWork/sprites/live/verify/vpn_truth.py, which printed FAIL but exited 0). Owner,
2026-11-01 ~08:15: VPN, on-site network and API, "interrelated and each informative". want() restates the table by hand:
  lost = API failing with error_kind network (whatever the VPN says)
  risk = VPN down and not on the on-site network (on_site false or unknown), API ok/absent/other failure
  ok   = otherwise when anything is known      none = VPN and API both unknown
Debounce (SHIP_PLAN; 2 s here via ?vpndebounce=2, 20 s live): entering lost or risk holds; recovery is immediate;
any adverse time counts toward the hold (owner ruling 2026-11-01 13:27, R1 #15). Transitions and the live cue too.
One headless Chromium. Exit 0 = pass."""
import copy, itertools, json
from playwright.sync_api import sync_playwright
from harness import check, done, url, feed

base = feed("--scenario", "calm", "--at", "30")
def snap(vpn, site, api):
    d = copy.deepcopy(base); M = d["machine"]; M.pop("api", None)
    if vpn is None: M.pop("vpn", None)
    else:
        M["vpn"]["state"] = vpn
        if site is None: M["vpn"].pop("on_site", None)
        else: M["vpn"]["on_site"] = site
    if api is not None:
        st, kind = api; M["api"] = {"observed_at": d["written_at"], "valid_until": d["written_at"] + 30, "state": st, **({"error_kind": kind} if kind else {})}
    return d
def want(vpn, site, api):
    if api and api[0] == "failing" and api[1] == "network": return "lost"
    if vpn == "down" and site is not True: return "risk"
    if vpn is None and api is None: return "none"
    return "ok"
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(url("stale=0&dpr=1&vpndebounce=2")); pg.wait_for_timeout(300)
    APIS = [None, ("ok", None), ("failing", "network"), ("failing", "rate_limit"), ("failing", "server"), ("failing", None)]
    bad, n = [], 0
    for vpn, site, api in itertools.product([None, "up", "down"], [True, False, None], APIS):
        if vpn is None and site is not None: continue
        got = pg.evaluate(f"__stage.adaptState({json.dumps(snap(vpn, site, api))}).S.net.linkRaw ?? 'none'"); n += 1
        if got != want(vpn, site, api): bad.append(f"vpn={vpn} on_site={site} api={api}: {got} (want {want(vpn, site, api)})")
    check(not bad and n == 42, f"truth table, {n} combinations {bad[:3]}")
    # the hover label names the signals that are down
    why = lambda s: pg.evaluate(f"__stage.adaptState({json.dumps(s)}).S.net.why")
    check(why(snap("down", False, ("ok", None))) == ["VPN down", "not on the on-site network"], "why: VPN down off site")
    check(why(snap("up", True, ("failing", "network"))) == ["API unreachable"], "why: API unreachable")
    # debounce: sequences of (raw, ms) -> shown
    def seq(steps): return pg.evaluate(f"(() => {{ __stage.resetVpn(); return {json.dumps(steps)}.map(([r, t]) => __stage.linkDebounce(r, t)); }})()")
    r = seq([["ok" if k % 2 else "lost", k * 1000] for k in range(8)])
    check("lost" not in r and "risk" not in r, f"flapping lost/ok never shows lost or risk: {r}")
    check(seq([["lost", 0], ["lost", 1999], ["lost", 2000], ["lost", 5000]]) == ["ok", "ok", "lost", "lost"], "steady lost shows after the hold")
    check(seq([["risk", 0], ["risk", 1999], ["risk", 2000]]) == ["ok", "ok", "risk"], "steady risk shows after the hold")
    check(seq([["risk", 0], ["risk", 3000], ["lost", 3100], ["lost", 5100]]) == ["ok", "risk", "risk", "lost"], "risk -> lost needs lost's own hold")
    check(seq([["lost", 0], ["lost", 3000], ["ok", 3001]]) == ["ok", "lost", "ok"], "lost -> ok: recovery immediate")
    check(seq([["risk", 0], ["risk", 3000], ["ok", 3001]]) == ["ok", "risk", "ok"], "risk -> ok: recovery immediate")
    check(seq([["none", 0]]) == ["none"], "all unknown shows nothing")
    # owner ruling 13:27 (R1 #15): adverse time counts. 19 s of LOST (scaled: 1.9 s), then API ok with the VPN down off
    # site: AT RISK at once once the 2 s hold has run, with no "ok" gap.
    check(seq([["lost", 0], ["risk", 1900], ["risk", 2000]]) == ["ok", "ok", "risk"], "lost 1.9 s then risk: risk at 2.0 s (adverse time counts)")
    check(seq([["lost", 0], ["lost", 2500], ["risk", 2600]]) == ["ok", "lost", "risk"], "shown lost -> risk: straight to risk, no ok gap")
    b.close()

    # live: risk = one beacon, no huddle; lost = huddle. Transitions as the layers see them.
    def live_page():
        p = b.new_page(viewport={"width": 1440, "height": 900}); p.goto(url("stale=0&dpr=1&vpndebounce=0")); p.wait_for_timeout(300)
        p.evaluate("SpritesStage.setSize(1440,900)"); return p
    b = pw.chromium.launch()
    for case, s, huddle in [("risk", snap("down", False, ("ok", None)), False), ("lost", snap("up", True, ("failing", "network")), True)]:
        p = live_page(); p.evaluate(f"SpritesStage.update({json.dumps(s)})"); p.wait_for_timeout(3500)
        r = p.evaluate("(() => { const out = {}; for (const c of Object.keys(__stage.layers)) { const V = __stage.V(c); out[c] = [!!V._beacon(), V.huddlePt ? 1 : 0]; } return [__stage.model.S.net.linkRaw, out]; })()")
        beacons = sum(v[0] for v in r[1].values())
        check(beacons == 1, f"live {case}: exactly one beacon across {len(r[1])} layers ({beacons})")
        p.close()
    # LOST -> AT RISK must not tell the pieces the link came back. R1 #7 was fixed by exposing S.net.link: the pieces
    # bloom only when vpn goes down -> up AND link is "ok" (V.reconnected), so the layers must never see link "ok" here.
    p = live_page()
    p.evaluate("""(() => { window.__seen = []; const c0 = Object.keys(__stage.layers); })()""")
    p.evaluate(f"SpritesStage.update({json.dumps(snap('down', False, ('failing', 'network')))})"); p.wait_for_timeout(1500)
    p.evaluate("""(() => { for (const c of Object.keys(__stage.layers)) { const V = __stage.V(c), f = V._onLive;
        V._onLive = m => { if (m.S && m.S.net) window.__seen.push(m.S.net.link); return f(m); }; } })()""")
    p.evaluate(f"SpritesStage.update({json.dumps(snap('down', False, ('ok', None)))})"); p.wait_for_timeout(1500)
    seen = p.evaluate("[__stage.model.S.net.link, window.__seen]")
    check(seen[0] == "risk" and "ok" not in seen[1], f"LOST -> AT RISK: the layers never see the link come back {seen}")
    p.close(); b.close()
done()
