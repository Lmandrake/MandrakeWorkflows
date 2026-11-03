"""Pilot-2 per-project counts: tickets_open, waiting, open, merged with burning (lodestar_counts)."""

import json
import os
import time

import pytest

from augur import core
from augur.collectors.base import Collector
from augur.lodestar import burning, tickets

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("_augur_burning_fixtures",
                                     os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_lodestar_burning.py"))
_fx = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_fx)
FEED, NOW, make_home = _fx.FEED, _fx.NOW, _fx.make_home

jsonschema = pytest.importorskip("jsonschema")
SCHEMA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema",
                      "snapshot.schema.json")


def ticket(d, tid, status):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, tid + ".md"), "w") as fh:
        fh.write("---\nid: %s\ntitle: \"t\"\nstatus: %s\n---\n\nbody\n" % (tid, status))


def setup(tmp_path, feed=FEED, whatnow=True, homes=True, homes_at=NOW):
    home, lod = make_home(tmp_path, feed)
    heat = os.path.join(home, "dev", "Ember28", "tickets")
    over = os.path.join(home, "dev", "private-store", "projects", "Ember28", "tickets")
    lodt = os.path.join(lod, "tickets")
    ticket(heat, "EMBER_BUILD_ONE_THING", "open")
    ticket(heat, "EMBER_FIX_TWO_THINGS", "active")
    ticket(heat, "EMBER_WAIT_ON_THEM", "blocked")
    ticket(heat, "EMBER_DONE_ALREADY_X", "done")
    ticket(over, "EM28-12", "open")
    ticket(lodt, "LODE-5", "open")
    open(os.path.join(heat, "README.md"), "w").write("not a ticket")
    tdir = os.path.join(home, "dev", ".lodestar", "tickets")
    os.makedirs(tdir, exist_ok=True)
    if homes:
        hs = [["Ember28", "ember28", "EM28", "repo", heat, "", os.path.join(home, "dev", "Ember28"), False],
              ["Ember28", "ember28", "EM28", "overlay", over, "", os.path.join(home, "dev", "Ember28"), False],
              ["Lodestar", "lodestar", "LODE", "repo", lodt, "", lod, False],
              ["Quiet", "quiet", "QUIET", "repo", os.path.join(home, "nowhere"), "", os.path.join(home, "dev", "Quiet"), False]]
        json.dump({"stamp": [0, 0], "at": homes_at, "homes": hs}, open(os.path.join(tdir, "homes-cache.json"), "w"))
    if whatnow:
        wn = {"built_at": "2026-10-31T19:00:00-07:00", "projects": [{"key": "ember28", "repo": os.path.join(home, "dev", "Ember28")}],
              "items": [{"project": "ember28", "repo": "", "ref": "mail"},
                        {"project": "ember28", "repo": "", "ref": {"path": heat + "/EMBER_BUILD_ONE_THING.md"}},
                        {"project": "", "repo": ""},
                        {"project": "privatestore", "repo": ""}]}
        json.dump(wn, open(os.path.join(home, "dev", ".lodestar", "whatnow.json"), "w"))
    return home, lod


def test_ticket_counts_by_status_and_overlay(tmp_path):
    home, lod = setup(tmp_path)
    t = tickets.TicketReader().counts(home, lod, NOW)
    assert t["ember28"] == {"tickets_open": 3, "waiting": 1}       # repo 2 + overlay 1; blocked 1
    assert t["lodestar"] == {"tickets_open": 1, "waiting": 0}
    assert t["quiet"] == {"tickets_open": 0, "waiting": 0}         # home with no dir: real zero


def test_status_cache_rereads_only_changed_files(tmp_path):
    home, lod = setup(tmp_path)
    r = tickets.TicketReader()
    r.counts(home, lod, NOW)
    calls = []
    real = tickets._status
    tickets._status = lambda p: calls.append(p) or real(p)
    try:
        r.counts(home, lod, NOW)
        assert calls == []
        p = os.path.join(home, "dev", "Ember28", "tickets", "EMBER_WAIT_ON_THEM.md")
        ticket(os.path.dirname(p), "EMBER_WAIT_ON_THEM", "open")
        os.utime(p, (time.time() + 5, time.time() + 5))
        assert r.counts(home, lod, NOW)["ember28"] == {"tickets_open": 4, "waiting": 0}
        assert calls == [p]
    finally:
        tickets._status = real


def collect(home, lod, now=NOW):
    class Ctx(object):
        pass
    c = Ctx()
    c.home, c.lodestar, c.now = home, lod, now
    return burning.CountsCollector().collect(c)["projects.counts"]


def test_merged_counts(tmp_path):
    home, lod = setup(tmp_path)
    by = collect(home, lod)["by_key"]
    h = by["ember28"]["counts"]
    assert h["burning"] == 8 and h["tickets_open"] == 3 and h["waiting"] == 1
    assert h["open"] == 3 + 1                  # one mail item; the ticket-item is not double counted
    lo = by["lodestar"]["counts"]
    assert lo["open"] == 1 + 2                 # LODE-5 + the unprojected and privatestore items
    assert lo["unmapped_burning"] == 20
    assert h["basis"] == "waiting=tickets-only,burning=lodestar-attribution"


def test_burning_stale_tickets_ok(tmp_path):
    home, lod = setup(tmp_path, feed=None)
    by = collect(home, lod)["by_key"]
    h = by["ember28"]["counts"]
    assert "burning" not in h and h["tickets_open"] == 3
    assert "burning=read_failed" in h["basis"]


def test_no_whatnow_open_absent(tmp_path):
    home, lod = setup(tmp_path, whatnow=False)
    h = collect(home, lod)["by_key"]["ember28"]["counts"]
    assert "open" not in h and h["tickets_open"] == 3 and "open=no-whatnow" in h["basis"]


def test_both_fail_unknown(tmp_path):
    home, lod = setup(tmp_path, feed=None, homes=False)
    assert collect(home, lod) == {"unknown": "read_failed"}


def test_stale_homes_list_is_unmeasured(tmp_path):
    home, lod = setup(tmp_path, homes_at=NOW - 7 * 3600)
    h = collect(home, lod)["by_key"]["ember28"]["counts"]
    assert "tickets_open" not in h and "tickets=unmeasured" in h["basis"] and h["burning"] == 8


class Sess(Collector):
    name, tier, signals = "sessions", "agents", ("sessions",)

    def collect(self, ctx):
        return {"sessions": [{"id": "7@1793400000", "pid": 7, "started_at": 1793400000.0,
                              "project": "Lodestar", "project_key": "lodestar", "managed": True}]}


def test_snapshot_entries_and_schema(tmp_path):
    home, lod = setup(tmp_path)
    c = core.Core([Sess(), burning.CountsCollector()], str(tmp_path / "aug"), home=home,
                  clock=lambda: NOW, mono=lambda: 5000.0, lodestar=lod, cpu_reader=lambda: (0.0, 0.0, 1000))
    c.tick()
    snap = json.load(open(c.snapshot_path))
    errs = list(jsonschema.Draft202012Validator(json.load(open(SCHEMA))).iter_errors(snap))
    assert not errs, errs[:2]
    ps = {p["key"]: p for p in snap["projects"]}
    assert ps["lodestar"]["sessions"] == 1 and ps["lodestar"]["counts"]["tickets_open"] == 1
    assert ps["ember28"]["sessions"] == 0 and ps["ember28"]["counts"]["burning"] == 8   # ghost
    assert "quiet" not in ps            # tickets only, no burning, no session: no entry
    assert "kestrel" not in ps      # burning 0, no session: no entry


def test_lodestar_absent(tmp_path):
    class Ctx(object):
        home, lodestar, now = str(tmp_path), None, NOW
    assert burning.CountsCollector().collect(Ctx()) == {}


# --------------------------------------------------------------------------- CONTRACT R1 C4

def _counts(home, lod):
    class Ctx(object):
        pass
    c = Ctx()
    c.home, c.lodestar, c.now = home, lod, NOW
    return burning.CountsCollector().collect(c)["projects.counts"]["by_key"]


def test_c4_as_of_is_the_oldest_input(tmp_path):
    from datetime import datetime
    home, lod = setup(tmp_path, homes_at=NOW - 7000.0)
    built = datetime.fromisoformat(FEED["built_at"]).timestamp()
    wn = datetime.fromisoformat("2026-10-31T19:00:00-07:00").timestamp()
    truth = min(built, NOW - 7000.0, wn)                         # the three ages, hand-listed
    by = _counts(home, lod)
    assert by["ember28"]["counts"]["as_of"] == pytest.approx(truth)
    assert by["lodestar"]["counts"]["as_of"] == pytest.approx(truth)


def test_c4_as_of_absent_when_an_inputs_age_is_unknown(tmp_path):
    home, lod = setup(tmp_path)
    p = os.path.join(home, "dev", ".lodestar", "whatnow.json")
    d = json.load(open(p))
    d["built_at"] = "2026-10-31T19:00:00-07:00"
    json.dump(d, open(p, "w"))
    by = _counts(home, lod)
    assert "as_of" in by["ember28"]["counts"]
    os.remove(os.path.join(home, "dev", ".lodestar", "tickets", "homes-cache.json"))
    by = _counts(home, lod)                                      # tickets unmeasured: burning only
    from datetime import datetime
    assert by["ember28"]["counts"]["as_of"] == pytest.approx(datetime.fromisoformat(FEED["built_at"]).timestamp())
