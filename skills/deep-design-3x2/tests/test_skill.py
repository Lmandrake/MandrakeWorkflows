"""Guards for deep-design-3x2's load-bearing rules (prose checks; earlier 3x3 tests are in git history)."""
import re
from pathlib import Path

SKILL = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text()
BODY = SKILL.split("---", 2)[2]


def _section(title):
    m = re.search(rf"^#+ [^\n]*{title}[^\n]*$(.*?)(?=^#+ |\Z)", BODY, re.M | re.S | re.I)
    assert m, f"no section matching {title!r}"
    return m.group(1)


def test_old_name_still_triggers():
    front = SKILL.split("---", 2)[1]
    assert "3x3" in front and "deep-design-3x2" in front


def test_at_least_three_solutions():
    assert re.search(r"at least three genuinely different solutions", _section("Pass 1"), re.I)


def test_pass1_keeps_a_claims_ledger():
    p1 = _section("Pass 1")
    assert "claims" in p1.lower() and re.search(r"measured|estimated|assumed|unmeasured", p1)


def test_gpt_is_blind_first():
    p2 = _section("Pass 2")
    blind = p2.index("02a-gpt-blind.md")
    first_sight = p2.find("send `01-design.md`")
    assert first_sight > blind, "GPT must not see 01-design.md before its blind answer"
    assert re.search(r"commit", p2[blind:first_sight], re.I), "blind file must be committed first"
    assert "02a-gpt-blind.md" in _section("Merge")


def test_remeasure_by_a_different_method():
    rm = _section("Re-measure")
    assert "02m-remeasure.md" in rm
    assert re.search(r"different (method|way|source)", rm, re.I)
    assert "02m-remeasure.md" in _section("Merge")


def test_second_opus_is_optional_and_blind():
    op = _section("Optional")
    assert re.search(r"blind first", op, re.I) and "transcript" in op


def test_no_debate_rounds_and_hidden_authorship():
    assert re.search(r"no (debate|rebuttal) rounds?|one critique", BODY, re.I)
    assert re.search(r"authorship|which model wrote|whose answer", BODY, re.I)


def test_failure_handling_is_defined():
    text = _section("When a pass fails").lower()
    assert "incomplete" in text and "status" in text
    assert "chatgpt-consult" in text and "unavailable" in text


def test_model_and_cost_recorded():
    text = _section("Run status")
    assert "ANTHROPIC_DEFAULT_OPUS_MODEL" in text and "status.md" in text
    assert re.search(r"token", text, re.I) and re.search(r"cost", text, re.I)


def test_outcome_and_provenance():
    assert "04-outcome.md" in BODY and re.search(r"whose idea|provenance", BODY, re.I)


def test_no_preference_judging():
    assert re.search(r"do not ask\s+the user\s+to judge", BODY, re.I)
