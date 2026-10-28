from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import checks, schema  # noqa: E402


def view(fm_extra="", markdown="\n## What this is\nA paper.\n"):
    base = ("source: paper.pdf\nsource_sha256: SRC\nplacard_version: 2\n"
            "body_layout: inline\nauthoring_status: current\n")
    return schema.load_digest(f"---\n{base}{fm_extra}---\n{markdown}")


def codes(findings):
    return {f.code for f in findings}


class Checks(unittest.TestCase):
    def test_clean_digest_has_no_findings(self):
        f = checks.check_digest(view(), body_text="[p.1]\nhello")
        self.assertEqual(codes(f), set())

    def test_summary_basis_stale_is_caught(self):
        """The failure the review found: refresh the body, preserve the prose,
        and an obsolete claim ends up wrapped in fresh validation metadata."""
        v = view("body_sha256: NEWBODY\nsummary_basis: body-gen\n"
                 "summary_basis_sha: OLDBODY\n")
        f = checks.check_digest(v, body_text="x")
        self.assertIn("SUMMARY_BASIS_STALE", codes(f))

    def test_summary_basis_matching_body_is_clean(self):
        v = view("body_sha256: SAME\nsummary_basis: body-gen\n"
                 "summary_basis_sha: SAME\n")
        f = checks.check_digest(v, body_text="x")
        self.assertNotIn("SUMMARY_BASIS_STALE", codes(f))

    def test_abstract_basis_beside_full_body_is_NOT_a_finding(self):
        """The review's central correction: these two scopes are compatible.
        Flagging this would restate the old overclaim in the opposite
        direction."""
        v = view("summary_basis: abstract\nauthoring_status: needs-review\n")
        f = checks.check_digest(v, body_text="a full document " * 500)
        self.assertEqual(codes(f), set())

    def test_extraction_error_as_body_is_caught(self):
        f = checks.check_digest(view(), body_text="[extraction error: no reader]")
        self.assertIn("EXTRACTION_ERROR_AS_BODY", codes(f))

    def test_coverage_claim_in_prose_is_caught(self):
        md = ("\n## What this is\nA paper.\n\n## Gaps / uncertainties\n"
              "Only the first page / abstract was read (17pp total); interior "
              "sections were not digested.\n")
        f = checks.check_digest(view(markdown=md), body_text="x " * 9000)
        self.assertIn("COVERAGE_CLAIM_IN_PROSE", codes(f))

    def test_genuine_gap_prose_is_not_flagged(self):
        md = ("\n## Gaps / uncertainties\nFigures are not rendered; open the "
              "original for the engineering drawing on p.7.\n")
        f = checks.check_digest(view(markdown=md), body_text="x")
        self.assertEqual(codes(f), set())

    def test_unknown_total_rendered_as_zero_is_caught(self):
        v = view("figures_detected: 0\nfigures_detected_known: false\n")
        f = checks.check_digest(v, body_text="x")
        self.assertIn("UNKNOWN_RENDERED_AS_ZERO", codes(f))

    def test_known_zero_is_not_flagged(self):
        v = view("figures_detected: 0\nfigures_detected_known: true\n")
        f = checks.check_digest(v, body_text="x")
        self.assertEqual(codes(f), set())

    def test_body_hash_mismatch_is_caught(self):
        v = view("body_sha256: EXPECTED\n")
        f = checks.check_digest(v, body_text="actual bytes")
        self.assertIn("BODY_HASH_MISMATCH", codes(f))


class RefutedChecksAreAbsent(unittest.TestCase):
    """Two checks from the first draft were refuted by the external review and
    must NOT be reintroduced. A full text extraction can still justify opening
    the original for figures or layout, and tier: skim beside a full body is a
    coherent combination."""

    def test_no_escalation_contract_vs_body_full_check(self):
        md = "\n## Open the original if…\n- you need the exact figures\n"
        v = view("body: full\n", markdown=md)
        f = checks.check_digest(v, body_text="x " * 9000)
        self.assertEqual(codes(f), set())

    def test_no_tier_vs_body_size_check(self):
        v = view("tier: skim\nbody_bytes: 90000\n")
        f = checks.check_digest(v, body_text="x" * 90000)
        self.assertEqual(codes(f), set())


if __name__ == "__main__":
    unittest.main()
