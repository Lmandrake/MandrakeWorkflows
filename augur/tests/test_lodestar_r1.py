"""Lodestar count defects from review R1 (findings 6, 9, 10, 11). Truth is the fixture the test
writes: what the Companion last evaluated, what each file says, which directory is unreadable."""
import json
import os
import stat

import pytest

from augur.lodestar import burning, tickets

import importlib.util as _ilu

_here = os.path.dirname(os.path.abspath(__file__))
_spec = _ilu.spec_from_file_location("_r1_burn_fx", os.path.join(_here, "test_lodestar_burning.py"))
_fx = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_fx)
_spec2 = _ilu.spec_from_file_location("_r1_count_fx", os.path.join(_here, "test_lodestar_counts.py"))
_cx = _ilu.module_from_spec(_spec2)
_spec2.loader.exec_module(_cx)
FEED, NOW, make_home = _fx.FEED, _fx.NOW, _fx.make_home
BUILT = "2026-10-31T22:30:28-07:00"
LATER = "2026-10-31T23:30:31-07:00"


def companion(checked_at, total=36, state="ok", age=10):
    return {"generated_epoch": NOW - age,
            "plots": {"burning": {"total": total, "checked_at": checked_at, "state": state}}}


# --------------------------------------------------------------------------- finding 6

def test_frozen_feed_with_alive_companion_and_failed_refresh_is_stale(tmp_path):
    # the Companion still regenerates now.json, but its burning view is old (refresh failing):
    # totals agree because both are frozen. Not fresh.
    home, lod = make_home(tmp_path, FEED, feed_age=3 * 3600,
                          now_json=companion(BUILT, total=36, state="stale"))
    assert burning.read(home, lod, NOW) == {"unknown": "stale"}


def test_redistribution_with_equal_total_is_stale(tmp_path):
    # an item moved Ember28 -> KestrelWorks in a newer evaluation the file missed: same total
    home, lod = make_home(tmp_path, FEED, feed_age=3600, now_json=companion(LATER, total=36))
    assert burning.read(home, lod, NOW) == {"unknown": "stale"}


def test_unchanged_feed_matching_the_latest_evaluation_is_fresh(tmp_path):
    home, lod = make_home(tmp_path, FEED, feed_age=3600, now_json=companion(BUILT, total=36))
    assert "by_key" in burning.read(home, lod, NOW)


def test_freshness_does_not_depend_on_the_total(tmp_path):
    # pilot2_check compares the sum with now.json's total: freshness must not already require
    # that equality, or the check is circular (R1 finding 6)
    home, lod = make_home(tmp_path, FEED, feed_age=3600, now_json=companion(BUILT, total=99))
    assert "by_key" in burning.read(home, lod, NOW)


def test_same_instant_in_another_zone_or_with_microseconds_is_fresh(tmp_path):
    # CONSUMERS_REVIEW_R1 n1: the handshake compares instants, not ISO strings
    for same in ("2026-11-01T05:30:28+00:00", "2026-10-31T22:30:28.000000-07:00"):
        home, lod = make_home(tmp_path / same[-6:].replace(":", ""), FEED, feed_age=3600,
                              now_json=companion(same))
        assert "by_key" in burning.read(home, lod, NOW), same


def test_a_different_instant_in_iso_form_is_stale(tmp_path):
    home, lod = make_home(tmp_path, FEED, feed_age=3600, now_json=companion("2026-10-31T22:30:29-07:00"))
    assert burning.read(home, lod, NOW) == {"unknown": "stale"}
    home, lod = make_home(tmp_path / "bad", FEED, feed_age=3600, now_json=companion("not a time"))
    assert burning.read(home, lod, NOW) == {"unknown": "stale"}


# --------------------------------------------------------------------------- finding 9

def test_row_without_burning_key_leaves_it_absent(tmp_path):
    feed = json.loads(json.dumps(FEED))
    del feed["projects"]["Ember28"]["burning"]
    home, lod = make_home(tmp_path, feed)
    c = burning.read(home, lod, NOW)["by_key"]["ember28"]["counts"]
    assert "burning" not in c and c["burning_red"] == 1


def test_feed_without_lodestar_row_fabricates_no_zeros(tmp_path):
    # the contract (section 4) requires a lodestar row: without one the whole feed is invalid,
    # so no Lodestar burning is fabricated (absent, never 0)
    feed = json.loads(json.dumps(FEED))
    del feed["projects"]["lodestar"]
    home, lod = make_home(tmp_path, feed)
    assert burning.read(home, lod, NOW) == {"unknown": "invalid"}


def counts(home, lod):
    class Ctx(object):
        pass
    c = Ctx()
    c.home, c.lodestar, c.now = home, lod, NOW
    return burning.CountsCollector().collect(c)["projects.counts"]["by_key"]


def test_burning_key_with_no_ticket_home_has_no_ticket_zeros(tmp_path):
    home, lod = _cx.setup(tmp_path)
    c = counts(home, lod)["orphan-row"]["counts"]
    assert c["burning"] == 2
    assert "tickets_open" not in c and "waiting" not in c and "open" not in c


def test_unlistable_ticket_dir_is_unmeasured_not_zero(tmp_path):
    home, lod = _cx.setup(tmp_path)
    d = os.path.join(home, "dev", "Ember28", "tickets")
    os.chmod(d, 0)
    try:
        if os.access(d, os.R_OK):
            pytest.skip("running as a user who can read mode-0 dirs")
        c = counts(home, lod)["ember28"]["counts"]
        assert "tickets_open" not in c and "waiting" not in c
        assert c["burning"] == 8
        q = counts(home, lod)["quiet"]["counts"]   # a home whose dir does not exist: a real 0
        assert q["tickets_open"] == 0
    finally:
        os.chmod(d, stat.S_IRWXU)


# --------------------------------------------------------------------------- finding 10

def test_hestia_and_private_store_tickets_fold_to_lodestar(tmp_path):
    home, lod = _cx.setup(tmp_path)
    hdir = os.path.join(home, "dev", "Hestia", "tickets")
    pdir = os.path.join(home, "dev", "private-store", "tickets")
    _cx.ticket(hdir, "HEST-1", "open")
    _cx.ticket(pdir, "PRIV-1", "blocked")
    p = os.path.join(home, "dev", ".lodestar", "tickets", "homes-cache.json")
    d = json.load(open(p))
    d["homes"] += [["Hestia", "hestia", "HEST", "repo", hdir, "", os.path.join(home, "dev", "Hestia"), False],
                   ["private-store", "private-store", "PRIV", "repo", pdir, "", os.path.join(home, "dev", "private-store"), False]]
    json.dump(d, open(p, "w"))
    t = tickets.TicketReader().counts(home, lod, NOW)
    assert t["lodestar"] == {"tickets_open": 1 + 1, "waiting": 1}     # LODE-5 + HEST-1; PRIV-1
    assert "hestia" not in t and "private-store" not in t


# --------------------------------------------------------------------------- finding 11

def test_stale_whatnow_is_unmeasured(tmp_path):
    home, lod = _cx.setup(tmp_path)
    p = os.path.join(home, "dev", ".lodestar", "whatnow.json")
    d = json.load(open(p))
    d["built_at"] = "2026-10-28T09:00:00-07:00"          # days before NOW
    json.dump(d, open(p, "w"))
    c = counts(home, lod)["ember28"]["counts"]
    assert "open" not in c and "open=no-whatnow" in c["basis"]
    d["built_at"] = "2026-10-31T18:26:40-07:00"          # 1 h before NOW: current
    json.dump(d, open(p, "w"))
    assert counts(home, lod)["ember28"]["counts"]["open"] == 4


# --------------------------------------------------------------------------- review R2

def test_r2_8_missing_unmapped_burning_stays_absent(tmp_path):
    feed = json.loads(json.dumps(FEED))
    del feed["unmapped_burning"]
    home, lod = make_home(tmp_path, feed)
    c = burning.read(home, lod, NOW)["by_key"]["lodestar"]["counts"]
    assert "unmapped_burning" not in c and c["burning"] == 26


def test_pre_contract_guesses_are_invalid_never_zero(tmp_path):
    """R3-8 / consumers R3 F8: the R2 guesses at a marker are not the contract. Each now reads
    absent with the contract's exact reason (invalid), never 0 and never a fabricated count. The
    contract's own shapes are tested from Lodestar's fixtures below."""
    for i, feed in enumerate(({"built_at": None, "unmapped_burning": 0,
                               "projects": {"lodestar": {"burning": 0}}},
                              {"built_at": BUILT, "unmeasured": True},
                              {"unknown": "stale", "built_at": BUILT})):
        home, lod = make_home(tmp_path / str(i), feed)
        assert burning.read(home, lod, NOW) == {"unknown": "invalid"}, feed


# --------------------------------------------------------------------------- shared contract (consumers R3 F8)

CONTRACT = os.path.expanduser("~/dev/Lodestar/tests/fixtures/burning_projects")


def _contract_cases():
    p = os.path.join(CONTRACT, "expected.json")
    if not os.path.exists(p):
        return []
    exp = json.load(open(p))
    return [(k, v) for k, v in exp.items() if not k.startswith("_")]


@pytest.mark.parametrize("name,want", _contract_cases())
def test_reader_conforms_to_the_lodestar_contract_fixtures(tmp_path, name, want):
    """The fixtures are Lodestar's own (read by path, never copied), so writer and reader cannot
    drift. Truth: expected.json beside them."""
    feed = json.load(open(os.path.join(CONTRACT, name)))
    home, lod = make_home(tmp_path, feed)                       # fresh by mtime
    names = burning.Names(lod, home)
    names.resolve = lambda n: (n, n, True)                      # compare by routing name
    r = burning.read(home, lod, NOW, names)
    if "unknown" in want:
        assert r == {"unknown": want["unknown"]}
        return
    got = {k: {f: v for f, v in c["counts"].items() if f in ("burning", "burning_red", "burning_amber",
                                                          "burning_verify")}
           for k, c in r["by_key"].items() if k in want["counts"]}
    ren = {"burning": "burning", "burning_red": "red", "burning_amber": "amber", "burning_verify": "verify"}
    got = {k: {ren[f]: v for f, v in c.items()} for k, c in got.items()}
    assert got == want["counts"]
    lodc = r["by_key"]["lodestar"]["counts"]
    if want.get("unmapped_burning") is None:
        assert "unmapped_burning" not in lodc
    else:
        assert lodc["unmapped_burning"] == want["unmapped_burning"]


def test_contract_fixtures_are_present():
    if not os.path.isdir(CONTRACT):
        pytest.skip("Lodestar's contract fixtures are not on this machine")
    assert len(_contract_cases()) >= 6, "Lodestar's burning_projects fixtures not found at " + CONTRACT


def test_g4_g5_malformed_rows_and_numbers_are_invalid_not_counts(tmp_path):
    """Consumers R4 G4/G5: a null alias row, a huge number, a string count, a float, a negative,
    version True/1.0. The contract's reference validator (vendored) calls each invalid."""
    if not os.path.isdir(CONTRACT):
        pytest.skip("Lodestar's contract fixtures are not on this machine")
    base = json.load(open(os.path.join(CONTRACT, "fresh.json")))
    pk = next(k for k in base["projects"] if k != "lodestar")     # any non-Lodestar routing row
    cases = []
    for name, mut in (("null_row", lambda d: d["projects"].__setitem__(pk + "-alias", None)),
                      ("huge", lambda d: d["projects"][pk].__setitem__("burning", float("inf"))),
                      ("string", lambda d: d["projects"][pk].__setitem__("burning", "8")),
                      ("float", lambda d: d["projects"][pk].__setitem__("red", 2.7)),
                      ("negative", lambda d: d["projects"][pk].__setitem__("red", -1)),
                      ("version_true", lambda d: d.__setitem__("version", True)),
                      ("version_float", lambda d: d.__setitem__("version", 1.0)),
                      ("naive_time", lambda d: d.__setitem__("built_at", "2026-11-01T08:57:55")),
                      ("no_envelope", lambda d: [d.pop(k) for k in ("schema", "version", "state")])):
        d = json.loads(json.dumps(base))
        mut(d)
        cases.append((name, d))
    for name, d in cases:
        p = tmp_path / name
        p.mkdir()
        home, lod = make_home(p, None)
        f = os.path.join(home, "dev", ".lodestar", "companion", "burning-projects.json")
        with open(f, "w") as fh:
            fh.write(json.dumps(d).replace("Infinity", "1e309"))
        assert burning.read(home, lod, NOW) == {"unknown": "invalid"}, name


def test_g5_invalid_burning_keeps_ticket_counts(tmp_path):
    """G5's blast radius: a malformed burning number must not blank the measured ticket counts."""
    home, lod = _cx.setup(tmp_path)
    f = os.path.join(home, "dev", ".lodestar", "companion", "burning-projects.json")
    d = json.load(open(f))
    d["projects"]["Ember28"]["burning"] = 1
    with open(f, "w") as fh:
        fh.write(json.dumps(d).replace('"burning": 1,', '"burning": 1e309,', 1))
    c = counts(home, lod)["ember28"]["counts"]
    assert "burning" not in c and c["tickets_open"] == 3
