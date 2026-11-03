"""Per-project burning counts, read from Lodestar (ticket AUGUR_WIRE_LODESTAR_BURNING_COUNTS).

Lodestar attributes burning items to projects (BURNING_WIRE_TO_PROJECTS); Augur only copies the
counts and never re-attributes. Source: <home>/dev/.lodestar/companion/burning-projects.json,
{built_at, unmapped_burning, projects: {<routing name>: {burning, red, amber, verify}}}, written
by the Companion only when it changes, with every watched project (zeros included) and
`lodestar` always present.

Freshness. The file is rewritten only on change, so an old mtime alone does not mean stale. It is
fresh when its mtime is under FRESH_S old, OR the Companion is alive (now.json generated_epoch
under FRESH_S old), its burning view is current (plots.burning.state "ok") and the file was built
from the Companion's latest evaluation (its built_at == plots.burning.checked_at; the Companion
made built_at part of the file's change key, so the two move together). Review R1 finding 6: the
earlier rule (per-project sum == plots.burning.total) passed a frozen feed as fresh, missed a
redistribution with an unchanged total, and made pilot2_check's sum-vs-total check circular.
Otherwise burning is unmeasured: counts read {"unknown": "stale"} (or "read_failed" when the file
is missing or unparseable), never 0. A row with no `burning` key leaves that key absent, and no
Lodestar row means no Lodestar burning (absent, never a fabricated 0; finding 9).
Lodestar not installed: no counts at all (absent).

Names. Keys are Lodestar ROUTING names (priority/routing.md: KestrelWorks, Ember28). Each maps to
Augur's project key through the routing row's dir: the sync/registry.md row with that path gives
the Id and Name (the same key a session in that checkout gets). A routing dir that is not itself a
registry row maps to the registry row that CONTAINS it (Expenses -> ~/dev/private-store/...); a
row whose Id is private-store or Hestia folds into the Lodestar entry, as tickets do (C7). Only a
dir inside no registry row keys on its lowercased name, flagged registered=False, and the core
never draws such a key as a `managed` ghost. `lodestar` stays `lodestar`.

Data age (C4): `observed_at` on the counts is when Augur READ the sources; `as_of` is how old the
data is: the burning view's built_at (and, in the merged counts, the oldest of it, the
homes-cache time and whatnow's built_at).
"""

import json
import math
import os
import re

from augur.collectors.base import Collector

FRESH_S = 300.0
LODESTAR = "lodestar"
KEY_RE = re.compile(r"[^a-z0-9._-]+")
_ROUTE_RE = re.compile(r"^\|\s*(?P<project>[^|]+?)\s*\|\s*(?P<dir>[^|]+?)\s*\|")


def safe_key(name):
    k = KEY_RE.sub("-", name.strip().lower()).strip("-._")
    return k or "unnamed"


def _table_rows(path):
    """Rows of the first markdown table as dicts keyed by lowercased header (mdtable's shape)."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    def cells(line):
        s = line.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        return [c.strip() for c in re.split(r"(?<!\\)\|", s)]
    for i in range(len(lines) - 1):
        a, b = lines[i].strip(), lines[i + 1].strip()
        if a.startswith("|") and b.startswith("|") and set(b.replace("|", "").strip()) <= set("-: "):
            hdr = [h.lower() for h in cells(a)]
            out = []
            for line in lines[i + 2:]:
                if not line.strip().startswith("|"):
                    break
                c = cells(line)
                out.append({h: (c[j] if j < len(c) else "") for j, h in enumerate(hdr)})
            return out
    return []


def _expand(path, home):
    """`~` against the given home (the reader's, not the process's: tests use a fixture home)."""
    if path == "~" or path.startswith("~/"):
        path = home + path[1:]
    return os.path.realpath(path)


class Names(object):
    """routing name -> (project_key, display name, in_registry), cached by the two files' mtimes."""

    def __init__(self, lodestar, home):
        self.lodestar, self.home = lodestar, home
        self._key = None
        self.map = {}

    def _paths(self):
        return (os.path.join(self.lodestar, "priority", "routing.md"),
                os.path.join(self.lodestar, "sync", "registry.md"))

    def refresh(self):
        rp, gp = self._paths()
        try:
            key = (os.path.getmtime(rp), os.path.getmtime(gp))
        except OSError:
            key = None
        if key == self._key and self.map:
            return self.map
        self._key = key
        by_path = {}
        try:
            for r in _table_rows(gp):
                p = r.get("path", "").strip("`")
                if p and r.get("name"):
                    by_path[_expand(p, self.home)] = (
                        r.get("id", "").strip("`") or safe_key(r["name"]), r["name"].strip("`"))
        except OSError:
            pass
        m = {}
        try:
            with open(rp, encoding="utf-8") as fh:
                for line in fh:
                    g = _ROUTE_RE.match(line.rstrip("\n"))
                    if not g:
                        continue
                    name, d = g.group("project"), g.group("dir")
                    if name.lower() == "project" or set(name) <= {"-"}:
                        continue
                    m[name] = self._row_for(by_path, _expand(d, self.home), name)
        except OSError:
            pass
        self.map = m
        return m

    @staticmethod
    def _row_for(by_path, d, name):
        """The registry row at `d`, else the deepest row containing it; private-store and Hestia
        fold to Lodestar (C7). (key, display, in_registry)."""
        from augur.lodestar.tickets import FOLD_TO_LODESTAR
        hit = by_path.get(d)
        if hit is None:
            best = None
            for p, row in by_path.items():
                if d.startswith(p.rstrip(os.sep) + os.sep) and (best is None or len(p) > len(best[0])):
                    best = (p, row)
            hit = best[1] if best else None
        if hit is None:
            if safe_key(name) in FOLD_TO_LODESTAR:
                return LODESTAR, "Lodestar", True
            return safe_key(name), name, False
        if hit[0] in FOLD_TO_LODESTAR:
            return LODESTAR, "Lodestar", True
        return hit[0], hit[1], True

    def resolve(self, name):
        if name.lower() == LODESTAR:
            return LODESTAR, "Lodestar", True
        return self.refresh().get(name) or (safe_key(name), name, False)


FIELDS = (("burning", "burning"), ("burning_red", "red"), ("burning_amber", "amber"),
          ("burning_verify", "verify"))


def _int(v):
    """A count as the contract allows it: a non-negative integer, else None (absent). No
    coercion: "5", 2.7, 1e309 and -1 are not counts (G5; validate() already refused them)."""
    if isinstance(v, int) and not isinstance(v, bool) and v >= 0:
        return v
    return None


def _instant(iso):
    """An ISO-8601 time with offset as epoch seconds, else None. built_at and checked_at are
    compared as instants (review R1 n1): the Companion may render the same time in another
    zone or with microseconds."""
    from datetime import datetime
    if not isinstance(iso, str):
        return None
    try:
        t = datetime.fromisoformat(iso)
    except ValueError:
        return None
    return t.timestamp() if t.tzinfo is not None else None


def freshness(comp, d, mtime, now):
    """"mtime" (file younger than FRESH_S), "evaluation" (an unchanged file the Companion's latest
    burning evaluation was built from), or None (stale). pilot2_check reports which path held."""
    if now - mtime < FRESH_S:
        return "mtime"
    try:
        with open(os.path.join(comp, "now.json"), encoding="utf-8") as fh:
            nj = json.load(fh)
        alive = now - float(nj.get("generated_epoch") or 0) < FRESH_S
        pb = (nj.get("plots") or {}).get("burning") or {}
        built = _instant(d.get("built_at"))
        if alive and pb.get("state") == "ok" and built is not None \
                and _instant(pb.get("checked_at")) == built:
            return "evaluation"
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


# The contract's reference validator, vendored so Augur's reader and Lodestar's writer judge a
# document by the SAME code (consumers R4 G4, G5, G10; R4-8). Drift is checked by
# tests/test_vendored_drift.py against Lodestar at the sha below.
# from Lodestar bin/lib/burnproject.py@d9a43e22 SCHEMA
SCHEMA = "lodestar.burning-projects"
# from Lodestar bin/lib/burnproject.py@d9a43e22 VERSION
VERSION = 1
# from Lodestar bin/lib/burnproject.py@d9a43e22 TIERS
TIERS = ("red", "amber", "verify")
# from Lodestar bin/lib/burnproject.py@d9a43e22 STATES
STATES = ("ok", "unmeasured", "stale")
# from Lodestar bin/lib/burnproject.py@d9a43e22 COUNT_FIELDS
COUNT_FIELDS = ("burning",) + TIERS
from typing import Dict, Optional  # noqa: E402,F401 - the vendored signatures use them

# from Lodestar bin/lib/burnproject.py@d9a43e22 _aware_iso
def _aware_iso(v) -> bool:
    """An ISO-8601 time WITH an offset (contract section 2)."""
    from datetime import datetime
    if not isinstance(v, str):
        return False
    try:
        return datetime.fromisoformat(v).tzinfo is not None
    except ValueError:
        return False

# from Lodestar bin/lib/burnproject.py@d9a43e22 _count
def _count(v) -> bool:
    return v is None or (isinstance(v, int) and not isinstance(v, bool) and v >= 0)

# from Lodestar bin/lib/burnproject.py@d9a43e22 validate
def validate(doc) -> Optional[str]:
    """None when `doc` conforms to the contract (section 2-4), else why not."""
    if not isinstance(doc, dict):
        return "not an object"
    if doc.get("schema") != SCHEMA or type(doc.get("version")) is not int or doc["version"] != VERSION:
        return "schema/version"
    st = doc.get("state")
    if st not in STATES:
        return "state"
    built = doc.get("built_at")
    if built is not None and not _aware_iso(built):
        return "built_at is not ISO-8601 with an offset"
    if st != "ok":
        if "projects" in doc or "unmapped_burning" in doc:
            return "counts with state %s" % st
        if st == "stale" and not built:
            return "stale without built_at"
        return None
    if not built:
        return "ok without built_at"
    projects = doc.get("projects")
    if not isinstance(projects, dict) or LODESTAR not in projects:
        return "projects"
    for name, row in projects.items():
        if not isinstance(row, dict) or not all(_count(row.get(k)) for k in COUNT_FIELDS):
            return "row %s" % name
    if not _count(doc.get("unmapped_burning")):
        return "unmapped_burning"
    return None


def contract_check(d):
    """None when `d` carries counts to read, else the {"unknown": reason} of contract section 5.
    No transitional branch any more (G10): an envelope-less document is invalid."""
    if validate(d) is not None:
        return {"unknown": "invalid"}
    if d["state"] != "ok":
        return {"unknown": d["state"]}
    return None


def read(home, lodestar, now, names=None):
    """{"unknown": reason} or {"by_key": {key: {"name", "counts": {...}}}, "observed_at": t}."""
    comp = os.path.join(home, "dev", ".lodestar", "companion")
    path = os.path.join(comp, "burning-projects.json")
    try:
        mtime = os.path.getmtime(path)
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        if not isinstance(d, dict):
            raise ValueError("not an object")
    except (OSError, ValueError, TypeError):
        return {"unknown": "read_failed"}
    verdict = contract_check(d)
    if verdict is not None:
        return verdict
    projects = d["projects"]
    if freshness(comp, d, mtime, now) is None:
        return {"unknown": "stale"}
    names = names or Names(lodestar, home)
    out = {}
    as_of = _instant(d.get("built_at"))
    for name, row in projects.items():
        if not isinstance(row, dict):
            continue
        key, disp, reg = names.resolve(name)
        c = {"basis": "burning=lodestar-attribution"}
        for ours, theirs in FIELDS:
            v = _int(row.get(theirs))
            if v is not None:
                c[ours] = v
        prev = out.get(key)
        if prev:   # two routing names on one checkout: Lodestar's counts are summed, not re-cut
            for ours, _t in FIELDS:
                if ours in c and ours in prev["counts"]:
                    c[ours] += prev["counts"][ours]
                else:
                    c.pop(ours, None)      # one side unmeasured: the sum is unmeasured
        out[key] = {"name": disp, "counts": c,
                    "registered": bool(reg) or bool(prev and prev.get("registered"))}
    lod = out.setdefault(LODESTAR, {"name": "Lodestar", "registered": True,
                                    "counts": {"basis": "burning=lodestar-attribution"}})
    if as_of is not None:
        for v in out.values():
            v["counts"]["as_of"] = round(as_of, 3)
    um = _int(d.get("unmapped_burning"))
    if um is not None:                     # R2-8: absent when the feed does not say, never 0
        lod["counts"]["unmapped_burning"] = um
    return {"by_key": out}


class CountsCollector(Collector):
    """projects.counts: burning (Lodestar's attribution) merged per key with ticket and to-do
    counts (augur/lodestar/tickets.py). A part that is unmeasured leaves only its own keys absent
    and says so in `basis`; with every part unmeasured the Signal reads unknown."""
    name = "lodestar_counts"
    tier = "counts"
    signals = ("projects.counts",)

    def __init__(self):
        from augur.lodestar.tickets import TicketReader
        self.names = None
        self.tickets = TicketReader()
        self._reg = (None, {})
        self._ages = {}

    def _age(self, home, parts, field):
        """Epoch of `field` in <home>/dev/.lodestar/<parts>, re-parsed only when (mtime, size)
        changes; None when unreadable (the age is then unknown)."""
        p = os.path.join(home, "dev", ".lodestar", *parts)
        try:
            st = os.stat(p)
        except OSError:
            return None
        sig = (st.st_mtime, st.st_size)
        hit = self._ages.get(p)
        if hit is None or hit[0] != sig:
            v = None
            try:
                with open(p, encoding="utf-8") as fh:
                    raw = json.load(fh).get(field)
                if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                    v = float(raw) if math.isfinite(raw) else None
                else:
                    v = _instant(raw)
            except (OSError, ValueError, AttributeError):
                v = None
            hit = (sig, v)
            self._ages[p] = hit
        return hit[1]

    def _key_of_repo(self, ctx):
        from augur.lodestar.tickets import registry_ids
        p = os.path.join(ctx.lodestar, "sync", "registry.md")
        try:
            mt = os.path.getmtime(p)
        except OSError:
            mt = None
        if self._reg[0] != mt:
            self._reg = (mt, registry_ids(ctx.lodestar, ctx.home))
        ids, lod = self._reg[1], os.path.realpath(ctx.lodestar)

        def key(repo):
            r = _expand(repo, ctx.home)
            if r == lod:
                return LODESTAR
            return ids.get(r) or None
        return key

    def collect(self, ctx):
        from augur.lodestar.tickets import whatnow_open
        if not ctx.lodestar:
            return {}
        if self.names is None or self.names.lodestar != ctx.lodestar:
            self.names = Names(ctx.lodestar, ctx.home)
        b = read(ctx.home, ctx.lodestar, ctx.now, self.names)
        try:
            t = self.tickets.counts(ctx.home, ctx.lodestar, ctx.now)
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            t = None
        w = whatnow_open(ctx.home, ctx.lodestar, self._key_of_repo(ctx), ctx.now) if t is not None else None
        ages = []                          # C4: the age of every input these counts are made of
        if "by_key" in b:
            ages.append(next((v["counts"].get("as_of") for v in b["by_key"].values()
                              if v["counts"].get("as_of") is not None), None))
        if t is not None:
            ages.append(self._age(ctx.home, ("tickets", "homes-cache.json"), "at"))
        if w is not None:
            ages.append(self._age(ctx.home, ("whatnow.json",), "built_at"))
        as_of = min(ages) if ages and None not in ages else None
        if "by_key" not in b and t is None:
            return {"projects.counts": b}
        by = {}
        if "by_key" in b:
            for k, v in b["by_key"].items():
                by[k] = {"name": v["name"], "counts": dict(v["counts"]),
                         "registered": v.get("registered", True)}
        basis = ["waiting=tickets-only"] if t is not None else ["tickets=unmeasured"]
        if "by_key" not in b:
            basis.append("burning=%s" % b.get("unknown", "unmeasured"))
        else:
            basis.append("burning=lodestar-attribution")
        if t is not None and w is None:
            basis.append("open=no-whatnow")
        keys = set(by) | set(t or {}) | set(w or {}) | {LODESTAR}
        for k in keys:
            row = by.setdefault(k, {"name": "Lodestar" if k == LODESTAR else k, "counts": {}})
            c = row["counts"]
            c.pop("basis", None)
            c.pop("as_of", None)
            if as_of is not None:          # one input of unknown age: the age is unknown, absent
                c["as_of"] = round(as_of, 3)
            tr = (t or {}).get(k)
            if tr is not None:     # no ticket home, or an unreadable one: absent, never 0
                c["tickets_open"], c["waiting"] = tr["tickets_open"], tr["waiting"]
                if w is not None:
                    c["open"] = tr["tickets_open"] + w.get(k, 0)
            c["basis"] = ",".join(basis)
        return {"projects.counts": {"by_key": by}}


class BurningCollector(Collector):
    name = "lodestar_burning"
    tier = "counts"
    signals = ("projects.counts",)

    def __init__(self):
        self.names = None

    def collect(self, ctx):
        if not ctx.lodestar:
            return {}                     # Lodestar not here: counts absent
        if self.names is None or self.names.lodestar != ctx.lodestar:
            self.names = Names(ctx.lodestar, ctx.home)
        return {"projects.counts": read(ctx.home, ctx.lodestar, ctx.now, self.names)}


def all_collectors():
    return [CountsCollector()]
