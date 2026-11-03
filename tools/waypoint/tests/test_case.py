"""Tests for case-insensitive waypoint names.

Run:  python3 -m unittest discover -s ~/dev/Waypoint/tests
"""
import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
_loader = importlib.machinery.SourceFileLoader("waypoint_mod", str(HERE / "waypoint"))
_spec = importlib.util.spec_from_loader("waypoint_mod", _loader)
assert _spec is not None
wp = importlib.util.module_from_spec(_spec)
_loader.exec_module(wp)


class CaseAliasTest(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(wp.case_aliases("Thesis"), ["thesis", "Thesis"])
        self.assertEqual(wp.case_aliases("RimMaster"), ["rimmaster", "Rimmaster", "RimMaster"])
        self.assertEqual(wp.case_aliases("THESIS"), ["thesis", "Thesis"])

    def test_reserved_skipped(self):
        self.assertEqual(wp.case_aliases("PATH"), [])

    def test_block_exports_upper_and_folder_name(self):
        w = wp.Waypoint(name="RimMaster", path="/x/RimMandrake")
        block = wp.render_block([w], "")
        self.assertIn("export RIMMASTER='/x/RimMandrake'", block)
        self.assertIn("rimmaster='/x/RimMandrake'", block)
        self.assertIn("rimmaster|rimmandrake)", block)


if __name__ == "__main__":
    unittest.main()
