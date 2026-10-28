from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import frontmatter, refresh  # noqa: E402

ENTRY = (
    "---\n"
    "source: paper.pdf\nsource_sha256: OLD\nplacard_version: 2\n"
    "body_layout: inline\nbody_sha256: OLDBODY\n"
    "summary_basis: body-gen\nsummary_basis_sha: OLDBODY\n"
    "authoring_status: current\n"
    "---\n"
    "\n## What this is\nHand-written summary that must survive.\n"
    "\n## Gaps / uncertainties\nFigures not rendered.\n"
    "\n## Full text\n[p.1]\nold extraction\n"
)


def _do(new_body, disk=None, new_fields=None):
    disk = {} if disk is None else disk
    fm = refresh.refresh_body(
        entry_text=ENTRY,
        sidecar_path=Path("/t/paper.pdf.placard.md"),
        original_name="paper.pdf",
        new_body=new_body,
        new_fields=new_fields or {},
        write_text=lambda p, t: disk.__setitem__(str(p), t),
    )
    return fm, disk


class ProseExtraction(unittest.TestCase):
    def test_prose_excludes_the_full_text_section(self):
        _, md = frontmatter.split(ENTRY)
        prose = refresh.prose_of(md)
        self.assertIn("Hand-written summary that must survive.", prose)
        self.assertIn("## Gaps / uncertainties", prose)
        self.assertNotIn("old extraction", prose)
        self.assertNotIn("## Full text", prose)


class ProsePreservation(unittest.TestCase):
    def test_authored_prose_survives_a_body_refresh(self):
        _, disk = _do("[p.1]\nbrand new extraction")
        written = disk["/t/paper.pdf.placard.md"]
        self.assertIn("Hand-written summary that must survive.", written)
        self.assertIn("Figures not rendered.", written)

    def test_new_body_replaces_the_old_one(self):
        _, disk = _do("[p.1]\nbrand new extraction")
        written = disk["/t/paper.pdf.placard.md"]
        self.assertIn("brand new extraction", written)
        self.assertNotIn("old extraction", written)

    def test_source_hash_is_updated(self):
        fm, _ = _do("[p.1]\nnew", new_fields={"source_sha256": "NEW"})
        self.assertEqual(fm["source_sha256"], "NEW")


class DiffGate(unittest.TestCase):
    """`materially_different` ranks how much a body changed (D6). Since
    2026-10-26 it no longer gates the review flag: any non-whitespace change
    marks a current summary needs-review."""

    def test_whitespace_change_is_not_material(self):
        material, _ = refresh.materially_different(
            "[p.1]\nhello  world", "[p.1]\nhello world")
        self.assertFalse(material)

    def test_new_identifier_is_material(self):
        material, why = refresh.materially_different(
            "[p.1]\nsee the report", "[p.1]\nsee NTR #1")
        self.assertTrue(material)
        self.assertIn("identifier", why.lower())

    def test_recovered_table_is_material(self):
        material, why = refresh.materially_different(
            "[p.1]\nResults follow",
            "[p.1]\nResults follow\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
        self.assertTrue(material)
        self.assertIn("table", why.lower())

    def test_large_text_delta_is_material(self):
        material, why = refresh.materially_different(
            "[p.1]\nshort", "[p.1]\n" + "word " * 500)
        self.assertTrue(material)
        self.assertIn("delta", why.lower())

    def test_material_change_sets_needs_review(self):
        fm, _ = _do("[p.1]\nsee NTR #1")
        self.assertEqual(fm["authoring_status"], "needs-review")

    def test_whitespace_only_change_leaves_authoring_status_alone(self):
        fm, _ = _do("[p.1]\nold  extraction")
        self.assertEqual(fm["authoring_status"], "current")

    def test_a_changed_number_sets_needs_review(self):
        """Review finding, 2026-10-26: `$61,400` -> `$91,400` is not material by
        the ranking above, yet the summary that quotes it is now wrong."""
        material, _ = refresh.materially_different("[p.1]\nTotal: $61,400",
                                                   "[p.1]\nTotal: $91,400")
        self.assertFalse(material, "the ranking cannot see it...")
        fm, _ = _do("[p.1]\nold extraction, Total: $91,400")
        self.assertEqual(fm["authoring_status"], "needs-review", "...so it may not gate it")

    def test_refresh_never_widens_summary_basis(self):
        """The review's correction: a body refresh records what was extracted
        and must not change what the summary claims to have been authored
        from."""
        fm, _ = _do("[p.1]\nsee NTR #1")
        self.assertEqual(fm["summary_basis"], "body-gen")
        self.assertEqual(fm["summary_basis_sha"], "OLDBODY",
                         "summary_basis_sha must keep pointing at the generation "
                         "the human actually read")



class FigureFieldsAreReplaced(unittest.TestCase):
    def test_a_run_that_describes_nothing_drops_the_old_model(self):
        entry = ENTRY.replace("placard_version: 2\n",
                              "placard_version: 2\nfigure_model: old-model\nfigures_described: 1\n", 1)
        fm = refresh.refresh_body(
            entry_text=entry, sidecar_path=Path("/t/paper.pdf.placard.md"),
            original_name="paper.pdf", new_body="[p.1]\nnew",
            new_fields={"figures_described": "0", "figures_described_known": "false"},
            write_text=lambda p, t: None)
        self.assertNotIn("figure_model", fm)
        self.assertEqual(fm["figures_described"], "0")


if __name__ == "__main__":
    unittest.main()
