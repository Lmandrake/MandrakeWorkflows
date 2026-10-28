"""Conservation check from SKILL.md, executed on fake data.

Original guidance: requested = succeeded + terminally_failed + still_pending (counts).
Corrected guidance: identity conservation (set equality, each id exactly once, duplicates reported).
"""
from collections import Counter


def numeric_conservation(requested, completed_ids, failed_ids, pending_ids):
    """SKILL.md as originally stated: counts only."""
    return len(requested) == len(completed_ids) + len(failed_ids) + len(pending_ids)


def identity_conservation(requested, completed_ids, failed_ids, pending_ids):
    """SKILL.md as corrected: set equality, exactly-once accounting."""
    accounted = list(completed_ids) + list(failed_ids) + list(pending_ids)
    counts = Counter(accounted)
    duplicates = sorted(i for i, n in counts.items() if n > 1)
    missing = sorted(set(requested) - set(counts))
    unexpected = sorted(set(counts) - set(requested))
    ok = not duplicates and not missing and not unexpected and len(set(requested)) == len(requested)
    return ok, {"duplicates": duplicates, "missing": missing, "unexpected": unexpected}


def test_numeric_check_is_fooled_by_AA():
    # Documents the original defect: it balances while B is lost.
    assert numeric_conservation(["A", "B"], ["A", "A"], [], [])


def test_identity_check_catches_AA():
    ok, rep = identity_conservation(["A", "B"], ["A", "A"], [], [])
    assert not ok
    assert rep["duplicates"] == ["A"] and rep["missing"] == ["B"]


def test_identity_check_passes_clean_run():
    ok, rep = identity_conservation(["A", "B", "C"], ["A"], ["B"], ["C"])
    assert ok and not any(rep.values())


def test_identity_check_flags_unexpected_id():
    ok, rep = identity_conservation(["A", "B"], ["A", "X"], [], [])
    assert not ok and rep["unexpected"] == ["X"] and rep["missing"] == ["B"]
