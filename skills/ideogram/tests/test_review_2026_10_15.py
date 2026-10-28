"""Preserved deployment outputs must not model gatekeeping unless marked as negative fixtures.

SKILL.md's self-check rule: never inflate, never gatekeep. A preserved output that gatekeeps is
only acceptable as evidence if its header marks it NEGATIVE FIXTURE, so no reader copies it.
"""
import pathlib
import re

DEPLOYMENTS = pathlib.Path(__file__).resolve().parents[1] / "docs" / "deployments"
GATEKEEPING = re.compile(
    r"not going to let you|can'?t go out like this|\brejected\b|you may not send|not allowed to send",
    re.IGNORECASE,
)
NEGATIVE_MARK = "NEGATIVE FIXTURE"


def is_negative(text: str) -> bool:
    return NEGATIVE_MARK in "\n".join(text.splitlines()[:5])


def outputs():
    return sorted(DEPLOYMENTS.rglob("*.md"))


def test_deployment_outputs_exist():
    assert outputs(), f"no preserved outputs under {DEPLOYMENTS}"


def test_no_unmarked_gatekeeping_output():
    bad = [p.name for p in outputs()
           if GATEKEEPING.search(p.read_text()) and not is_negative(p.read_text())]
    assert not bad, f"gatekeeping output not marked {NEGATIVE_MARK}: {bad}"


def test_negative_marks_are_earned():
    # A marker on a clean file would hide nothing and mislabel good evidence.
    stale = [p.name for p in outputs()
             if is_negative(p.read_text()) and not GATEKEEPING.search(p.read_text())]
    assert not stale, f"marked {NEGATIVE_MARK} but no gatekeeping found: {stale}"


def test_checker_on_synthetic(tmp_path):
    good = "Here is where you stand against your own bar. You decide what to include."
    bad = "No, I'm not going to let you send it yet."
    assert not GATEKEEPING.search(good)
    assert GATEKEEPING.search(bad) and not is_negative(bad)
    assert is_negative(f"> {NEGATIVE_MARK}: gatekeeping example\n\n{bad}")
