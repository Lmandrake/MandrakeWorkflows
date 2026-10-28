from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import read  # noqa: E402

PROFILE = "docling-2.115.0/text-v1/soffice-present"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def entry(**over) -> str:
    fm = {
        "source": "paper.pdf",
        "source_sha256": "SRC",
        "placard_version": "2",
        "profile_id": PROFILE,
        "body_layout": "inline",
        "authoring_status": "current",
    }
    fm.update(over)
    lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    return (f"---\n{lines}\n---\n\n## What this is\nA paper.\n\n"
            "## Full text\n[p.1]\nhello\n")


def resolve(entry_text, *, source="SRC", profile=PROFILE, bodies=None):
    bodies = bodies or {}
    return read.resolve(
        entry_text,
        source_sha256=source,
        current_profile_id=profile,
        load_body=lambda name: bodies.get(name),
        sha256_of_text=sha,
    )


class States(unittest.TestCase):
    def test_ok_inline(self):
        r = resolve(entry())
        self.assertEqual(r.state, "ok")
        self.assertIn("hello", r.body)

    def test_legacy_v1_is_usable(self):
        r = resolve(entry(placard_version="1"))
        self.assertEqual(r.state, "legacy")
        self.assertIn("hello", r.body, "a legacy digest must still return its body")

    def test_source_stale_when_hash_differs(self):
        r = resolve(entry(), source="DIFFERENT")
        self.assertEqual(r.state, "source-stale")

    def test_extraction_stale_when_profile_differs(self):
        r = resolve(entry(), profile="docling-9.9.9/text-v2/soffice-absent")
        self.assertEqual(r.state, "extraction-stale")

    def test_source_staleness_outranks_profile_staleness(self):
        r = resolve(entry(), source="DIFFERENT", profile="other")
        self.assertEqual(r.state, "source-stale")

    def test_external_body_ok_when_hash_matches(self):
        body = "[p.1]\nexternal hello"
        r = resolve(
            entry(body_layout="external", body_path="b.body.md",
                  body_sha256=sha(body)),
            bodies={"b.body.md": body})
        self.assertEqual(r.state, "ok")
        self.assertEqual(r.body, body)

    def test_body_missing_when_external_target_absent(self):
        """On Drive the entry can become visible before its body. That is a
        retryable condition, not a corrupt digest."""
        r = resolve(entry(body_layout="external", body_path="b.body.md",
                          body_sha256="X"),
                    bodies={})
        self.assertEqual(r.state, "body-missing")

    def test_body_mismatch_is_body_missing_not_ok(self):
        r = resolve(
            entry(body_layout="external", body_path="b.body.md",
                  body_sha256="EXPECTED"),
            bodies={"b.body.md": "different bytes"})
        self.assertEqual(r.state, "body-missing")
        self.assertIsNone(r.body,
                          "a mismatched body must never be returned as content")

    def test_never_substitutes_a_similarly_named_body(self):
        body = "[p.1]\nwrong generation"
        r = resolve(
            entry(body_layout="external", body_path="b.abc.body.md",
                  body_sha256=sha(body)),
            bodies={"b.def.body.md": body})
        self.assertEqual(r.state, "body-missing")

    def test_unavailable_when_body_is_an_extraction_error(self):
        """v1 wrote '[extraction error: ...]' into the body and still flagged
        body: full. That must never read as usable content."""
        text = entry().replace("[p.1]\nhello", "[extraction error: no such reader]")
        r = resolve(text)
        self.assertEqual(r.state, "unavailable")

    def test_unavailable_when_no_full_text_section_and_body_claimed(self):
        text = entry(body_layout="inline").replace(
            "\n\n## Full text\n[p.1]\nhello\n", "\n")
        r = resolve(text)
        self.assertEqual(r.state, "unavailable")

    def test_states_tuple_is_the_documented_set(self):
        self.assertEqual(set(read.STATES), {
            "ok", "legacy", "source-stale", "extraction-stale",
            "body-missing", "unavailable", "needs-source-inspection"})


class AuthorizesOriginal(unittest.TestCase):
    def test_unavailable_authorizes_opening_the_original(self):
        """Owner decision D5: the access trap is closed by making this explicit."""
        self.assertTrue(read.authorizes_original("unavailable"))
        self.assertTrue(read.authorizes_original("needs-source-inspection"))

    def test_ok_does_not_authorize_opening_the_original(self):
        self.assertFalse(read.authorizes_original("ok"))
        self.assertFalse(read.authorizes_original("legacy"))


if __name__ == "__main__":
    unittest.main()
