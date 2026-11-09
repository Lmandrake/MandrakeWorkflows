#!/usr/bin/env python3
"""The observation-contract fixtures (tests/fixtures/observation/) are real snapshots: each passes Augur's own schema
(augur/schema/snapshot.schema.json) AND the contract's 1.3 additions (contract.schema.json). The 1.2 fixture carries
neither `coverage` nor `foreign` (acceptance case 2 depends on it). A deliberately broken item is rejected, so the
schema check can see. Pure Python, no browser. Exit 0 = pass."""
import copy, json, sys
from pathlib import Path
import jsonschema

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures/observation"
AUGUR = json.loads((HERE.parents[1] / "augur/schema/snapshot.schema.json").read_text())
CONTRACT = json.loads((FIX / "contract.schema.json").read_text())
fails = 0


def check(ok, msg):
    global fails
    fails += 0 if ok else 1
    print(("PASS " if ok else "FAIL ") + msg)


def errors(schema, doc):
    return [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(doc)]


d13 = json.loads((FIX / "desktop_1_3.json").read_text())
d12 = json.loads((FIX / "laptop_1_2.json").read_text())
for name, d in (("desktop_1_3", d13), ("laptop_1_2", d12)):
    e = errors(AUGUR, d)
    check(not e, f"{name} passes Augur's snapshot schema {e[:2]}")
    e = errors(CONTRACT, d)
    check(not e, f"{name} passes the contract schema {e[:2]}")
check(d13["version"] == "1.3" and "coverage" in d13 and len(d13["foreign"]) == 5, "the 1.3 fixture carries coverage and 5 foreign items")
check(d12["version"] == "1.2" and "coverage" not in d12 and "foreign" not in d12, "the 1.2 fixture carries neither coverage nor foreign")
check({f["collector"] for f in d13["foreign"]} <= set(d13["coverage"]), "every foreign item names a collector that publishes coverage")
check(not any("label" in f for f in d13["foreign"] if not f["declared"]), "no undeclared item carries a label (Augur rule 3)")

bad = copy.deepcopy(d13); bad["coverage"]["mux"]["unknown"] = "read_failed"
check(bool(errors(CONTRACT, bad)), "control: a coverage stamp with both unknown and scopes is rejected")
bad = copy.deepcopy(d13); bad["foreign"][0]["terminal"] = {"outcome": "finished"}
check(bool(errors(CONTRACT, bad)), "control: a terminal outcome outside exited|failed|interrupted is rejected")
bad = copy.deepcopy(d13); del bad["foreign"][1]["collector"]
check(bool(errors(CONTRACT, bad)), "control: a foreign item with no collector is rejected")
print("FAILED" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
