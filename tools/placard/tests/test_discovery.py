from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import discovery  # noqa: E402


class TargetPathLookup(unittest.TestCase):
    """Sidecar lookup must key on the TARGET ARTIFACT's path, not the session's
    cwd. A session that began elsewhere must still find the digest sitting next
    to the file it is opening."""

    def test_finds_the_sidecar_beside_the_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "sub" / "deck.pdf"
            art.parent.mkdir()
            art.write_bytes(b"%PDF")
            side = art.with_name("deck.pdf.placard.md")
            side.write_text("---\nsource: deck.pdf\n---\n", encoding="utf-8")
            found = discovery.sidecars_for(art)
        self.assertEqual(found.entry, side)
        self.assertTrue(found.exists)

    def test_reports_absence_rather_than_raising(self):
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "lonely.pdf"
            art.write_bytes(b"%PDF")
            found = discovery.sidecars_for(art)
        self.assertFalse(found.exists)
        self.assertIsNone(found.body)

    def test_finds_the_declared_external_body(self):
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "deck.pdf"
            art.write_bytes(b"%PDF")
            body = art.with_name("deck.pdf.placard.abc123.body.md")
            body.write_text("[p.1]\nbody", encoding="utf-8")
            art.with_name("deck.pdf.placard.md").write_text(
                "---\nsource: deck.pdf\nbody_layout: external\n"
                "body_path: deck.pdf.placard.abc123.body.md\n---\n",
                encoding="utf-8")
            found = discovery.sidecars_for(art)
        self.assertEqual(found.body, body)

    def test_an_undeclared_body_file_is_not_adopted(self):
        """A body's presence on disk never makes it authoritative; only the
        entry file selects one."""
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "deck.pdf"
            art.write_bytes(b"%PDF")
            art.with_name("deck.pdf.placard.stray.body.md").write_text(
                "stray", encoding="utf-8")
            art.with_name("deck.pdf.placard.md").write_text(
                "---\nsource: deck.pdf\nbody_layout: inline\n---\n",
                encoding="utf-8")
            found = discovery.sidecars_for(art)
        self.assertIsNone(found.body)


class Gaps(unittest.TestCase):
    """A third of PDFs fleet-wide have no digest. The failure mode measured in
    1,089 sessions was 'never digested', not 'digested and bypassed' -- so what
    is MISSING has to be visible."""

    def _tree(self, d):
        root = Path(d)
        (root / "a.pdf").write_bytes(b"%PDF a")
        (root / "b.pdf").write_bytes(b"%PDF b")
        (root / "a.pdf.placard.md").write_text(
            "---\nsource: a.pdf\n---\n", encoding="utf-8")
        (root / "notes.txt").write_text("not digestible", encoding="utf-8")
        return root

    def test_reports_the_undigested_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._tree(d)
            report = discovery.gaps(root)
        names = {p.name for p in report.undigested}
        self.assertIn("b.pdf", names)
        self.assertNotIn("a.pdf", names)

    def test_ignores_non_digestible_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._tree(d)
            report = discovery.gaps(root)
        self.assertNotIn("notes.txt", {p.name for p in report.undigested})

    def test_never_counts_a_generated_body_as_an_artifact(self):
        """A generated body must never acquire a digest of its own (M4)."""
        with tempfile.TemporaryDirectory() as d:
            root = self._tree(d)
            (root / "a.pdf.placard.deadbeef.body.md").write_text(
                "[p.1]\nbody", encoding="utf-8")
            report = discovery.gaps(root)
        for path in report.undigested:
            self.assertNotIn(".body.md", path.name)
            self.assertNotIn(".placard.md", path.name)

    def test_coverage_is_reported_as_a_fraction_with_a_real_denominator(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._tree(d)
            report = discovery.gaps(root)
        self.assertEqual(report.total, 2)
        self.assertEqual(report.digested, 1)

    def test_empty_tree_reports_zero_not_complete(self):
        """0/0 must never read as full coverage."""
        with tempfile.TemporaryDirectory() as d:
            report = discovery.gaps(Path(d))
        self.assertEqual(report.total, 0)
        self.assertIsNone(report.coverage_frac,
                          "coverage of an empty tree is undefined, not 100%")



class MapHonesty(unittest.TestCase):
    """A map that lists only what it covers makes an undigested file look
    uninteresting, so the access that would digest it never happens. GPT's
    review named this the self-perpetuating omission in fix-forward."""

    def test_map_names_the_undigested_artifact(self):
        import placard as pl
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "covered.pdf").write_bytes(b"%PDF a")
            (root / "covered.pdf.placard.md").write_text(
                "---\nsource: covered.pdf\ntier: standard\n---\n\n"
                "## What this is\nCovered.\n", encoding="utf-8")
            (root / "forgotten.pdf").write_bytes(b"%PDF b")
            pl.cmd_map(root)
            text = (root / "PROJECT.placard.md").read_text(encoding="utf-8")
        self.assertIn("Not digested here", text)
        self.assertIn("forgotten.pdf", text)
        self.assertIn("UNKNOWN", text,
                      "the map must say unknown, not imply coverage")

    def test_map_omits_the_section_when_everything_is_digested(self):
        import placard as pl
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "covered.pdf").write_bytes(b"%PDF a")
            (root / "covered.pdf.placard.md").write_text(
                "---\nsource: covered.pdf\ntier: standard\n---\n\n"
                "## What this is\nCovered.\n", encoding="utf-8")
            pl.cmd_map(root)
            text = (root / "PROJECT.placard.md").read_text(encoding="utf-8")
        self.assertNotIn("Not digested here", text)

    def test_a_generated_body_is_never_listed_as_undigested(self):
        import placard as pl
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.pdf").write_bytes(b"%PDF")
            (root / "a.pdf.placard.md").write_text(
                "---\nsource: a.pdf\n---\n\n## What this is\nx\n",
                encoding="utf-8")
            (root / "a.pdf.placard.feed0001.body.md").write_text(
                "[p.1]\nbody", encoding="utf-8")
            pl.cmd_map(root)
            text = (root / "PROJECT.placard.md").read_text(encoding="utf-8")
        self.assertNotIn(".body.md", text)

if __name__ == "__main__":
    unittest.main()
