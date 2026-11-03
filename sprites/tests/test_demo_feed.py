#!/usr/bin/env python3
"""Review R1 #12: demo_feed must exercise every state of the three-signal link (VPN, on-site network, API).
The truth table below is restated by hand from the owner's ruling (2026-11-01 ~08:15, SHIP_PLAN "VPN, on-site network and API"),
NOT read from stage.html:
  lost = API failing with error_kind network, whatever the VPN says
  risk = VPN down and not on the on-site network (on_site false or absent), API not failing on the network
  ok   = otherwise, when the VPN or the API state is known
  none = VPN and API both unknown
Pure Python, no browser. Exit 0 = pass."""
import json, subprocess, sys
from pathlib import Path
FEED = Path(__file__).resolve().parents[1] / "tools/demo_feed.py"
fails = []
def check(cond, msg):
    if not cond: fails.append(msg)
    print(("PASS " if cond else "FAIL ") + msg)

def feed(*a):
    return json.loads(subprocess.check_output([sys.executable, str(FEED), "--print", "--check", *a], stderr=subprocess.DEVNULL))

def link(snap):
    M = snap["machine"]; vpn, api = M.get("vpn"), M.get("api")
    if api and api.get("state") == "failing" and api.get("error_kind") == "network": return "lost"
    if vpn and vpn.get("state") == "down" and vpn.get("on_site") is not True: return "risk"
    if (vpn and vpn.get("state")) or (api and api.get("state")): return "ok"
    return "none"

# 1. named scenarios: each pins one link state, with the signals that make it so
WANT = {  # scenario -> (link, vpn state or None, on_site, api (state, error_kind) or None)
    "vpn_down": ("risk", "down", False, ("ok", None)),
    "lost": ("lost", "down", False, ("failing", "network")),
    "api_network": ("lost", "up", True, ("failing", "network")),
    "api_ratelimit": ("ok", "up", False, ("failing", "rate_limit")),
    "onsite_vpn_down": ("ok", "down", True, ("ok", None)),
    "link_unknown": ("none", None, None, None),
}
names = subprocess.check_output([sys.executable, str(FEED), "--list-scenarios"], text=True).split()
for sc, (lk, vs, site, api) in WANT.items():
    if sc not in names: check(False, f"scenario {sc} exists"); continue
    d = feed("--scenario", sc, "--at", "30"); M = d["machine"]
    check(link(d) == lk, f"{sc}: link {link(d)} (want {lk})")
    check((M.get("vpn") or {}).get("state") == vs, f"{sc}: vpn state {(M.get('vpn') or {}).get('state')} (want {vs})")
    if vs is not None: check(M["vpn"].get("on_site") is site, f"{sc}: on_site {M['vpn'].get('on_site')} (want {site})")
    got = (M["api"]["state"], M["api"].get("error_kind")) if "api" in M else None
    check(got == api, f"{sc}: api {got} (want {api})")
    if "api" in M: check(M["api"]["observed_at"] <= d["written_at"] <= M["api"]["valid_until"], f"{sc}: api block is fresh")

# 2. the cycling demo, sampled every 5 s over the 2 h loop: every link state and every API reason shows up
sys.path.insert(0, str(FEED.parent)); import demo_feed as DF
args = type("A", (), dict(scenario=None, seed=20261031, period=2, at=0))()
seen, reasons, onsite = set(), set(), False
for t in range(0, 7200, 5):
    d = DF.snapshot(args, t, DF.EPOCH0); seen.add(link(d)); M = d["machine"]
    if "api" in M: reasons.add((M["api"]["state"], M["api"].get("error_kind")))
    onsite |= M["vpn"].get("on_site") is True
for lk in ("ok", "risk", "lost"):
    check(lk in seen, f"cycling demo reaches {lk} (seen {sorted(seen)})")
check(onsite, "cycling demo is on site (on-site network) some of the time")
for r in [("ok", None), ("failing", "network"), ("failing", "rate_limit")]:
    check(r in reasons, f"cycling demo emits api {r}")
print("ALL PASS" if not fails else f"{len(fails)} FAIL")
sys.exit(1 if fails else 0)
