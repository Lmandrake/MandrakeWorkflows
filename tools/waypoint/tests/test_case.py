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


class FoldAndFuzzyTest(unittest.TestCase):
    TABLE = wp.match_keys([("MYNOTES", "/x/my-notes"), ("ATLAS", "/x/Atlas"),
                           ("MYSEARCH", "/x/My_Search"), ("ORBIT9", "/x/Orbit9")])

    def test_separators_and_case_fold(self):
        for t in ("my-notes", "MY_Notes", "myNotes", "My.Notes"):
            self.assertEqual(wp.norm_key(t), "mynotes")

    def test_block_arm_is_normalised(self):
        block = wp.render_block([wp.Waypoint(name="MY_NOTES", path="/x/my-notes")], "")
        self.assertIn("mynotes) _wp_target='/x/my-notes'", block)
        self.assertIn("tr -cd 'a-z0-9'", block)

    def test_fuzzy(self):
        self.assertEqual(wp.fuzzy_pick("atlsa", self.TABLE), ("ATLAS", []))
        self.assertEqual(wp.fuzzy_pick("note", self.TABLE), ("MYNOTES", []))
        self.assertEqual(wp.fuzzy_pick("orb", self.TABLE), ("ORBIT9", []))

    def test_ambiguous_lists_candidates(self):
        name, near = wp.fuzzy_pick("my", self.TABLE)
        self.assertIsNone(name)
        self.assertEqual(near, ["MYNOTES", "MYSEARCH"])

    def test_nonsense_finds_nothing(self):
        self.assertEqual(wp.fuzzy_pick("zzzqqq", self.TABLE), (None, []))


if __name__ == "__main__":
    unittest.main()
