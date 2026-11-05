#!/usr/bin/env python3
"""Pilot-2 count checks against Lodestar itself (DESIGN.md section 12), on the LIVE snapshot.

    /usr/bin/python3 augur/bin/pilot2_check.py tickets   # tickets_open / waiting == `ticket list`
    /usr/bin/python3 augur/bin/pilot2_check.py burning   # sum of burning == now.json total

Exit 0 pass, 1 fail, 2 not enough data (counts absent or unknown). AUGUR_HOME as pilot1_check.
"""
import collections
import json
import os
import subprocess
import sys
import time

HOME = os.path.expanduser("~")


def snapshot():
    root = os.environ.get("AUGUR_HOME") or os.path.join(HOME, "agent-storage", "augur")
    with open(os.path.join(root, "live", "snapshot.json")) as fh:
        s = json.load(fh)
    if time.time() > s["valid_until"]:
        raise SystemExit("snapshot is stale: is the producer running?")
    return s


def fresh_counts(s):
    out = {}
    for p in s.get("projects", []):
        c = p.get("counts")
        if c and "unknown" not in c and time.time() <= c["valid_until"]:
            out[p["key"]] = c
    return out


def cmd_tickets():
    counts = fresh_counts(snapshot())
    have = {k: c for k, c in counts.items() if "tickets_open" in c}
    if not have:
        print("tickets: no project carries tickets_open yet")
        return 2
    rows = json.loads(subprocess.run(
        ["python3", os.path.join(HOME, "dev", "Lodestar", "bin", "ticket.py"), "list", "--all", "--json"],
        capture_output=True, text=True, timeout=120).stdout)
    cli = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r.get("status") in ("open", "active"):
            cli[r.get("project") or ""][0] += 1
        elif r.get("status") == "blocked":
            cli[r.get("project") or ""][1] += 1
    bad = 0
    for k, c in sorted(have.items()):
        a, b = (c["tickets_open"], c.get("waiting", 0)), tuple(cli.get(k, [0, 0]))
        ok = a == b
        bad += not ok
        print("%-20s augur open+active=%d blocked=%d  cli %d/%d  %s" % (k, a[0], a[1], b[0], b[1], "ok" if ok else "MISMATCH"))
    print("tickets: %d projects in the snapshot compared, %d mismatches" % (len(have), bad))
    return 1 if bad else 0


def freshness_path(home=HOME, now=None):
    """Which rule made burning-projects.json fresh: "mtime", "evaluation" or None (Augur's own
    rule, augur/lodestar/burning.py freshness)."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from augur.lodestar.burning import freshness
    comp = os.path.join(home, "dev", ".lodestar", "companion")
    p = os.path.join(comp, "burning-projects.json")
    with open(p) as fh:
        d = json.load(fh)
    return freshness(comp, d, os.path.getmtime(p), time.time() if now is None else now)


def cmd_burning(home=HOME):
    """Sum vs now.json total. Freshness no longer uses that equality (R1 finding 6), so the check
    is independent on both paths; it is still reported which path held, and only a pass on an
    mtime-fresh file counts as evidence of a CURRENT match (an evaluation-fresh file is one the
    Companion confirmed unchanged)."""
    counts = fresh_counts(snapshot())
    if not any("burning" in c for c in counts.values()):
        print("burning: no burning counts in the snapshot (feed absent or stale)")
        return 2
    ours = sum(c.get("burning", 0) for c in counts.values())
    with open(os.path.join(home, "dev", ".lodestar", "companion", "now.json")) as fh:
        total = (json.load(fh).get("plots") or {}).get("burning", {}).get("total")
    path = freshness_path(home)
    ok = ours == total
    print("burning: augur sum %s, now.json total %s: %s (freshness path: %s%s)" % (
        ours, total, "ok" if ok else "MISMATCH", path,
        "" if path == "mtime" else "; not counted as evidence of a current match"))
    if not ok:
        return 1
    return 0 if path == "mtime" else 2


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"tickets": cmd_tickets, "burning": cmd_burning}.get(cmd, lambda: print(__doc__) or 2)())
