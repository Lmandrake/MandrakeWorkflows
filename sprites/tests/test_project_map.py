#!/usr/bin/env python3
"""Review R1 #2: app/projects.js (SpritesProjects.build) over this machine's real data files gives ONE entry per project
Augur can report, keyed by Augur's project_key. Truth is independent of projects.js: (a) Augur's own parser
(augur/augur/collectors/sessions.py parse_registry, the code that writes project_key) over the same registry, for every
registry project; (b) the join chain written by hand in reviews/SPRITES_REVIEW_R1.md (Fixer response) for the launch
aliases. Also: every registry project gets a distinct short name of 1-12 characters (the stage's hover label, R1 #1).
Skips when the Lodestar registry is absent (no Lodestar on this machine). Run: python3 sprites/tests/test_project_map.py.
Exit 0 = pass."""
import json, os, socket, subprocess, sys
from pathlib import Path
SPR = Path(__file__).resolve().parents[1]; HOME = Path.home()
sys.path.insert(0, str(SPR.parent / "augur"))
from augur.collectors.sessions import parse_registry, machine_role, machine_key, _real
fails = []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg, flush=True)
    if not ok: fails.append(msg)

lodestar = Path(os.environ.get("AUGUR_LODESTAR") or HOME / "dev/Lodestar")
reg, mach = lodestar / "sync/registry.md", lodestar / "machines.md"
if not reg.exists(): print("SKIP no Lodestar registry on this machine"); sys.exit(0)
wmach = (os.environ.get("WAYPOINT_MACHINE") or socket.gethostname()).strip().lower().removesuffix(".local")
lkey = machine_key()
rd = lambda p: p.read_text(encoding="utf-8") if p.exists() else ""
args = {"registry": rd(reg), "machines": rd(mach), "waypoints": rd(HOME / ".config/waypoint/waypoints.md"),
        "launches": rd(HOME / ".config/waypoint/launches.md"), "home": str(HOME), "machine": wmach, "lodestarMachine": lkey}
JS = """const P = require(process.argv[1]), S = require(process.argv[2]); const a = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const t = P.build(a); console.log(JSON.stringify({ table: t, short: P.shortTable(t, null) }));"""
out = json.loads(subprocess.run(["node", "-e", JS, str(SPR / "app/projects.js"), str(SPR / "prototype/labels/shortname.js")],
                                input=json.dumps(args), capture_output=True, text=True, check=True).stdout)
table, short = out["table"], out["short"]
keyed = [e for e in table if e["key"]]

# (a) every registry project Augur can report on this machine, with Augur's key and name, and its directory
role = machine_role(args["machines"], lkey)
augur = parse_registry(args["registry"], role, lkey)        # {realpath: (name, id)}
want = {i: (n, p) for p, (n, i) in augur.items()}
got = {e["key"]: (e["name"], _real(e["dir"])) for e in keyed}
check(len(keyed) == len(got), f"keys are unique: {len(keyed)} entries, {len(got)} keys")
check(set(got) == set(want), f"same project_keys as Augur ({len(want)}): missing {sorted(set(want) - set(got))}, extra {sorted(set(got) - set(want))}")
bad = [k for k in want if k in got and got[k] != want[k]]
check(not bad, f"name and directory agree with Augur for all {len(want)}: {[(k, got[k], want[k]) for k in bad][:5]}")
total = sum(1 for l in args["registry"].split("## Machine paths")[0].splitlines() if l.startswith("| ") and not l.startswith("| Name") and "---" not in l[:6])
print(f"INFO registry rows {total}, Augur keeps {len(want)} on {lkey} (role {role})")

# (b) the hand-derived joins (Fixer response): alias -> key
by = {e["key"]: e for e in keyed}
hand = {"Orchard": "orchard-mandrake", "ProjectCert": "certanum", "KesMine": "kestrel", "KestrelWorks": "kestrel-team",
        "MSGRAPH": "microsoftgraphaccess", "Lodestar": "lodestar", "ProjectDial": "dialexis", "Granite": "granite", "Ember28": "ember28",
        "Atlas": "atlas", "StayCurrent": "staycurrent", "Hestia": "hestia", "Fetcher": "fetcher"}
for alias, key in hand.items():
    e = by.get(key) or {}
    check(e.get("alias") == alias, f"launch {alias} joins to project_key {key}: alias {e.get('alias')!r}")
check(by.get("orchard-mandrake", {}).get("hex") == "#CB50F0" and by["orchard-mandrake"].get("focus") is True, "Orchard carries its Waypoint colour #CB50F0 and focus")
check(by.get("kestrel", {}).get("focus") is False and by.get("kestrel-team", {}).get("focus") is True,
      "KesMine (private) is not a focus row; KestrelWorks (team) is")
mviz = [e for e in table if e["alias"] == "MandrakeVisualize"]
check(len(mviz) == 1 and mviz[0]["key"] is None, f"MandrakeVisualize (registry row retired) has no project_key: {mviz}")
dl = [e for e in table if e["alias"] == "ProjectDial"]; ft = [e for e in table if e["alias"] == "Fetcher"]
check(len(dl) == 1 and len(ft) == 1, f"per-machine launch rows resolve to one each (ProjectDial {len(dl)}, Fetcher {len(ft)})")

# R1 #1: every registry project has a distinct short name, 1-12 characters
ss = [short.get(k) for k in want]
check(all(isinstance(s, str) and 0 < len(s) <= 12 for s in ss), f"every one of {len(want)} short names is 1-12 chars: {[s for s in ss if not s or len(s) > 12][:5]}")
low = [s.lower() for s in ss if s]
check(len(set(low)) == len(low), f"short names are distinct: {sorted({s for s in low if low.count(s) > 1})}")
check(short.get("orchard-mandrake") == "Orchard" and short.get("kestrel") == "KesMine" and short.get("microsoftgraphaccess") == "MSGRAPH",
      f"Orchard_Mandrake -> Orchard, KestrelWorks_Mandrake -> KesMine, MicrosoftGraphAccess -> MSGRAPH: "
      f"{[short.get(k) for k in ('orchard-mandrake', 'kestrel', 'microsoftgraphaccess')]}")
print("ALL PASS" if not fails else f"{len(fails)} FAIL"); sys.exit(1 if fails else 0)
