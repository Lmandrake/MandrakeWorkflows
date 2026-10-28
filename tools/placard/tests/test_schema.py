from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import schema  # noqa: E402

V1 = (
    "---\n"
    "source: paper.pdf\n"
    "source_sha256: aaaa\n"
    "tier: standard\n"
    "placard_version: 1\n"
    "confidence: high\n"
    "body: full\n"
    "trim_notes: de-hyphenated line wraps; collapsed whitespace\n"
    "---\n"
    "\n## What this is\nA paper.\n\n## Full text\n[p.1]\nhello\n"
)

V2_EXTERNAL = (
    "---\n"
    "source: paper.pdf\n"
    "source_sha256: aaaa\n"
    "placard_version: 2\n"
    "extractor: docling\n"
    "extractor_version: 2.115.0\n"
    "profile_id: docling-2.115.0/text-v1/soffice-present\n"
    "body_layout: external\n"
    "body_path: paper.pdf.placard.abc123def456.body.md\n"
    "body_sha256: bbbb\n"
    "body_bytes: 57139\n"
    "summary_basis: body-gen\n"
    "summary_basis_sha: bbbb\n"
    "authoring_status: current\n"
    "---\n"
    "\n## What this is\nA paper.\n"
)


class LegacyTolerance(unittest.TestCase):
    def test_v1_loads_and_is_marked_legacy(self):
        v = schema.load_digest(V1)
        self.assertEqual(v.schema_version, 1)
        self.assertTrue(v.is_legacy)

    def test_v1_body_is_inline(self):
        v = schema.load_digest(V1)
        self.assertEqual(v.body_layout, "inline")
        self.assertIsNone(v.body_path)
        self.assertIn("hello", schema.inline_body(v.markdown))

    def test_v1_has_unknown_authoring_status(self):
        """v1 never recorded what the summary was authored from. 'unknown' and
        'current' must not be the same value -- that conflation is the defect."""
        v = schema.load_digest(V1)
        self.assertEqual(v.authoring_status, "unknown")
        self.assertIsNone(v.summary_basis_sha)


class SchemaV2(unittest.TestCase):
    def test_external_body_fields_parse(self):
        v = schema.load_digest(V2_EXTERNAL)
        self.assertEqual(v.schema_version, 2)
        self.assertFalse(v.is_legacy)
        self.assertEqual(v.body_layout, "external")
        self.assertEqual(v.body_path, "paper.pdf.placard.abc123def456.body.md")
        self.assertEqual(v.body_sha256, "bbbb")
        self.assertEqual(v.profile_id, "docling-2.115.0/text-v1/soffice-present")

    def test_summary_basis_is_separate_from_body(self):
        v = schema.load_digest(V2_EXTERNAL)
        self.assertEqual(v.summary_basis, "body-gen")
        self.assertEqual(v.summary_basis_sha, "bbbb")
        self.assertEqual(v.authoring_status, "current")

    def test_body_and_summary_field_sets_are_disjoint(self):
        self.assertEqual(set(schema.BODY_FIELDS) & set(schema.SUMMARY_FIELDS), set())

    def test_missing_optional_fields_are_none_not_empty_string(self):
        v = schema.load_digest("---\nsource: x.pdf\nplacard_version: 2\n---\n\nbody\n")
        self.assertIsNone(v.body_sha256)
        self.assertIsNone(v.profile_id)



class InlineBodyRunsToTheEnd(unittest.TestCase):
    """`digest` writes `## Figures` and `## Margin and footnote text` INSIDE the
    body. Stopping at the next `## ` heading dropped both while `read` said ok;
    found by the shipped example deck, whose body_sha256 then failed verify."""

    def test_sections_written_by_digest_stay_in_the_body(self):
        from placardlib import schema as _s
        md = ("# x\n\n## Gaps / uncertainties\nnone\n\n## Full text\n[p.1]\nslide"
              "\n\n## Figures\n\n[figure p.1]\na chart\n\n## Margin and footnote text\n- NTR #1\n")
        body = _s.inline_body(md)
        self.assertIn("## Figures", body)
        self.assertIn("a chart", body)
        self.assertIn("NTR #1", body)
        self.assertTrue(body.startswith("[p.1]"))

    def test_a_fenced_example_heading_does_not_start_the_body(self):
        from placardlib import schema as _s
        from placardlib import refresh as _r
        md = ("## Key contents\nThe format looks like:\n```\n## Full text\n[p.1]\n```\n"
              "more prose\n\n## Full text\n[p.1]\nreal body\n")
        self.assertEqual(_s.inline_body(md), "[p.1]\nreal body")
        self.assertIn("more prose", _r.prose_of(md))

    def test_no_full_text_is_empty(self):
        from placardlib import schema as _s
        self.assertEqual(_s.inline_body("# x\n## Key contents\nhi\n"), "")


if __name__ == "__main__":
    unittest.main()
