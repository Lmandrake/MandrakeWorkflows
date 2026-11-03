"""Lodestar per-project burning counts (AUGUR_WIRE_LODESTAR_BURNING_COUNTS): fresh, stale, missing,
routing-name mapping, the always-present Lodestar entry, and ghost projects with no session."""

import json
import os

import pytest

from augur import core
from augur.collectors.base import Collector
from augur.lodestar import burning

jsonschema = pytest.importorskip("jsonschema")
SCHEMA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema",
                      "snapshot.schema.json")
NOW = 1793500000.0

ROUTING = """# Project routing

| project | dir | keywords | senders |
|---|---|---|---|
| Ember28 | ~/dev/Ember28 | ember28 | |
| KestrelWorks | ~/dev/KestrelWorks_Mandrake | kestrel | |
| Orphan Row | ~/dev/NoSuchRepo | x | |
| Hestia | ~/dev/Hestia | | |
"""

REGISTRY = """# Sync participation registry

| Name | Path | Branch | Send | Receive | Machines | Id | Former | Remote | State | Mirror | Notes |
|------|------|--------|------|---------|----------|------|------|------|------|------|-------|
| Ember28 | {home}/dev/Ember28 | main | on | on |  | ember28 |  | x | active |  |  |
| KestrelWorks_Mandrake | {home}/dev/KestrelWorks_Mandrake | main | on | on |  | kestrel |  | x | active |  |  |
"""


def make_home(tmp_path, feed=None, feed_age=0.0, now_json=None):
    home = tmp_path / "home"
    lod = home / "dev" / "Lodestar"
    (lod / "priority").mkdir(parents=True)
    (lod / "sync").mkdir(parents=True)
    (lod / "priority" / "routing.md").write_text(ROUTING)
    (lod / "sync" / "registry.md").write_text(REGISTRY.format(home=str(home)))
    comp = home / "dev" / ".lodestar" / "companion"
    comp.mkdir(parents=True)
    if feed is not None:
        p = comp / "burning-projects.json"
        p.write_text(json.dumps(feed))
        os.utime(str(p), (NOW - feed_age, NOW - feed_age))
    if now_json is not None:
        (comp / "now.json").write_text(json.dumps(now_json))
    return str(home), str(lod)


FEED = {"schema": "lodestar.burning-projects", "version": 1, "state": "ok",
        "built_at": "2026-10-31T22:30:28-07:00", "unmapped_burning": 20,
        "projects": {"Ember28": {"burning": 8, "red": 1, "amber": 7, "verify": 0},
                     "KestrelWorks": {"burning": 0, "red": 0, "amber": 0, "verify": 0},
                     "Orphan Row": {"burning": 2, "red": 0, "amber": 2, "verify": 0},
                     "lodestar": {"burning": 26, "red": 0, "amber": 26, "verify": 0}}}


def test_fresh_feed_maps_routing_names_to_registry_keys(tmp_path):
    home, lod = make_home(tmp_path, FEED)
    r = burning.read(home, lod, NOW)
    by = r["by_key"]
    assert by["ember28"]["counts"]["burning"] == 8 and by["ember28"]["counts"]["burning_red"] == 1
    assert by["kestrel"]["name"] == "KestrelWorks_Mandrake"      # routing name -> registry row
    assert by["kestrel"]["counts"]["burning"] == 0               # zeros are carried, not dropped
    assert by["orphan-row"]["counts"]["burning"] == 2                # no registry row: its own key
    assert by["lodestar"]["counts"]["burning"] == 26
    assert by["lodestar"]["counts"]["unmapped_burning"] == 20
    assert "unmapped_burning" not in by["ember28"]["counts"]


def test_missing_feed_is_unknown_not_zero(tmp_path):
    home, lod = make_home(tmp_path, None)
    assert burning.read(home, lod, NOW) == {"unknown": "read_failed"}


def test_corrupt_feed_is_read_failed(tmp_path):
    home, lod = make_home(tmp_path, None)
    p = os.path.join(home, "dev", ".lodestar", "companion", "burning-projects.json")
    open(p, "w").write("{not json")
    assert burning.read(home, lod, NOW) == {"unknown": "read_failed"}


def test_old_feed_with_dead_companion_is_stale(tmp_path):
    home, lod = make_home(tmp_path, FEED, feed_age=3600,
                          now_json={"generated_epoch": NOW - 3600,
                                    "plots": {"burning": {"total": 36}}})
    assert burning.read(home, lod, NOW) == {"unknown": "stale"}


def test_old_feed_still_current_while_companion_alive(tmp_path):
    # written only on change: an old mtime is fine while the Companion's latest evaluation
    # (plots.burning.checked_at) is the one the file was built from
    home, lod = make_home(tmp_path, FEED, feed_age=3600,
                          now_json={"generated_epoch": NOW - 10,
                                    "plots": {"burning": {"total": 36, "state": "ok",
                                                          "checked_at": FEED["built_at"]}}})
    assert "by_key" in burning.read(home, lod, NOW)


def test_old_feed_behind_companion_build_is_stale(tmp_path):
    home, lod = make_home(tmp_path, FEED, feed_age=3600,
                          now_json={"generated_epoch": NOW - 10,
                                    "plots": {"burning": {"total": 40, "state": "ok",
                                                          "checked_at": "2026-10-31T23:31:00-07:00"}}})
    assert burning.read(home, lod, NOW) == {"unknown": "stale"}


class OneSession(Collector):
    name, tier, signals = "sessions", "agents", ("sessions",)

    def __init__(self, key="kestrel", managed=True):
        self.key, self.managed = key, managed

    def collect(self, ctx):
        return {"sessions": [{"id": "7@1793400000", "pid": 7, "started_at": 1793400000.0,
                              "project": "KestrelWorks_Mandrake", "project_key": self.key,
                              "managed": self.managed}]}


def run_core(tmp_path, home, lod, sessions):
    c = core.Core([sessions, burning.BurningCollector()], str(tmp_path / "aug"), home=home,
                  clock=lambda: NOW, mono=lambda: 5000.0, lodestar=lod,
                  cpu_reader=lambda: (0.0, 0.0, 1000))
    c.tick()
    with open(c.snapshot_path) as fh:
        snap = json.load(fh)
    with open(SCHEMA) as fh:
        errs = list(jsonschema.Draft202012Validator(json.load(fh)).iter_errors(snap))
    assert not errs, errs[:2]
    return {p["key"]: p for p in snap["projects"]}


def test_ghost_projects_and_lodestar_entry(tmp_path):
    home, lod = make_home(tmp_path, FEED)
    ps = run_core(tmp_path, home, lod, OneSession())
    assert ps["lodestar"]["kind"] == "lodestar" and ps["lodestar"]["counts"]["unmapped_burning"] == 20
    assert ps["ember28"]["sessions"] == 0 and ps["ember28"]["counts"]["burning"] == 8   # ghost
    assert ps["kestrel"]["sessions"] == 1 and ps["kestrel"]["counts"]["burning"] == 0
    assert "orphan-row" not in ps                  # C7: no registry row, never a managed ghost
    v = ps["ember28"]["counts"]
    assert v["valid_until"] - v["observed_at"] == pytest.approx(150.0)


def test_unmanaged_session_never_carries_counts(tmp_path):
    home, lod = make_home(tmp_path, FEED)
    ps = run_core(tmp_path, home, lod, OneSession(key="ember28", managed=False))
    assert ps["ember28"]["kind"] == "unmanaged" and "counts" not in ps["ember28"]


def test_stale_feed_reads_unknown_on_every_entry(tmp_path):
    home, lod = make_home(tmp_path, None)
    ps = run_core(tmp_path, home, lod, OneSession())
    assert ps["lodestar"]["counts"]["unknown"] == "read_failed"
    assert "burning" not in ps["lodestar"]["counts"]
    assert ps["kestrel"]["counts"]["unknown"] == "read_failed"
    assert "ember28" not in ps                     # no evidence of burning: no ghost


def test_lodestar_absent_counts_absent(tmp_path):
    home, _lod = make_home(tmp_path, FEED)
    ps = run_core(tmp_path, home, None, OneSession())
    assert "counts" not in ps["lodestar"] and list(ps) == ["lodestar", "kestrel"]


# --------------------------------------------------------------------------- CONTRACT R1 C7, C4

def _add_rows(home, lod, routing_extra, registry_extra):
    rp = os.path.join(lod, "priority", "routing.md")
    gp = os.path.join(lod, "sync", "registry.md")
    open(rp, "a").write(routing_extra)
    open(gp, "a").write(registry_extra.format(home=home))


def test_c7_dir_inside_private_store_folds_to_lodestar(tmp_path):
    feed = json.loads(json.dumps(FEED))
    feed["projects"]["Expenses"] = {"burning": 3, "red": 1, "amber": 2, "verify": 0}
    home, lod = make_home(tmp_path, feed)
    _add_rows(home, lod, "| Expenses | ~/dev/private-store/expenses | expenses | |\n",
              "| private-store | {home}/dev/private-store | main | on | on |  | private-store |  | x | active |  |  |\n")
    by = burning.read(home, lod, NOW)["by_key"]
    assert "expenses" not in by and "private-store" not in by
    assert by["lodestar"]["counts"]["burning"] == 26 + 3          # hand sum: Lodestar's 26 + expenses' 3
    assert by["lodestar"]["counts"]["burning_red"] == 0 + 1


def test_c7_dir_inside_a_project_row_takes_that_rows_key(tmp_path):
    feed = json.loads(json.dumps(FEED))
    feed["projects"]["Heat sub"] = {"burning": 1, "red": 0, "amber": 1, "verify": 0}
    home, lod = make_home(tmp_path, feed)
    _add_rows(home, lod, "| Heat sub | ~/dev/Ember28/sub/dir | x | |\n", "")
    by = burning.read(home, lod, NOW)["by_key"]
    assert by["ember28"]["counts"]["burning"] == 8 + 1 and by["ember28"]["registered"] is True
    assert "heat-sub" not in by


def test_c7_unregistered_key_is_flagged_and_never_managed(tmp_path):
    home, lod = make_home(tmp_path, FEED)
    by = burning.read(home, lod, NOW)["by_key"]
    assert by["orphan-row"]["registered"] is False and by["ember28"]["registered"] is True
    ps = run_core(tmp_path, home, lod, OneSession())
    assert all(p["kind"] != "managed" or p["key"] != "orphan-row" for p in ps.values())


def test_c4_counts_carry_the_feeds_own_age(tmp_path):
    home, lod = make_home(tmp_path, FEED)
    ps = run_core(tmp_path, home, lod, OneSession())
    from datetime import datetime
    built = datetime.fromisoformat(FEED["built_at"]).timestamp()
    c = ps["ember28"]["counts"]
    assert c["as_of"] == pytest.approx(built) and c["observed_at"] == pytest.approx(NOW)
