"""Tests for `waypoint layout`: layouts.md round trip, profile rendering, window parsing.

Run:  python3 -m unittest discover -s ~/dev/Waypoint/tests
Stdlib only. Nothing here talks to iTerm2 or writes outside a tempdir.
"""
import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
_loader = importlib.machinery.SourceFileLoader("waypoint_layout_mod", str(HERE / "waypoint"))
_spec = importlib.util.spec_from_loader("waypoint_layout_mod", _loader)
assert _spec is not None
wp = importlib.util.module_from_spec(_spec)
_loader.exec_module(wp)


class LayoutDbTest(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            wp.LAYOUT_DB_PATH = Path(d) / "layouts.md"
            wp.save_layouts([wp.Layout("ATLAS", "WORK-LAPTOP", 2, 972, 33, 570, 483, "2026-10-12 18:16"),
                             wp.Layout("ORBIT", "work-laptop", 3, -10, 0, 600, 400)])
            rows = {l.name: l for l in wp.load_layouts()}
            self.assertEqual(rows["ATLAS"].machine, "work-laptop")
            self.assertEqual((rows["ATLAS"].space, rows["ATLAS"].x, rows["ATLAS"].height), (2, 972, 483))
            self.assertEqual(rows["ORBIT"].x, -10)
            self.assertEqual(rows["ATLAS"].saved, "2026-10-12 18:16")


class SpaceProfilesTest(unittest.TestCase):
    def test_dynamic_base_is_copied_with_only_space_added(self):
        base = {"Name": "Claude", "Guid": "G", "Rewritable": True,
                "Dynamic Profile Parent Name": "Default", "Show Status Bar": True}
        profs = json.loads(wp.render_space_profiles(4, "Claude", base))["Profiles"]
        self.assertEqual([p["Name"] for p in profs], [f"Claude-Space{n}" for n in range(1, 5)])
        self.assertEqual([p["Space"] for p in profs], [1, 2, 3, 4])
        self.assertEqual(len({p["Guid"] for p in profs}), 4)
        for p in profs:
            self.assertNotIn("Rewritable", p)
            self.assertEqual(p["Dynamic Profile Parent Name"], "Default")
            self.assertTrue(p["Show Status Bar"])

    def test_plist_base_is_inherited_by_name(self):
        profs = json.loads(wp.render_space_profiles(2, "Default", None))["Profiles"]
        self.assertEqual(profs[1], {"Name": "Claude-Space2", "Guid": "WAYPOINT-SPACE-PROFILE-2",
                                    "Space": 2, "Dynamic Profile Parent Name": "Default"})


class WindowParseTest(unittest.TestCase):
    def test_parse(self):
        raw = "295 ||| Claude: Lodestar (claude) ||| /dev/ttys004\n\nbad line\n301 ||| -zsh ||| /dev/ttys010\n"
        self.assertEqual(wp.parse_iterm_windows(raw),
                         [(295, "Claude: Lodestar (claude)", "/dev/ttys004"), (301, "-zsh", "/dev/ttys010")])


class LayoutApplyPlanTest(unittest.TestCase):
    def _run(self, only=None):
        L = lambda n: type("L", (), {"name": n})()
        plan = [{"launch": L(n), "action": a, "matched": [f"x ||| {t}"]} for n, a, t in
                [("A", "skip-open", "/dev/t1"), ("B", "skip-open", "/dev/t2"), ("C", "skip-open", "/dev/t3"),
                 ("D", "skip-open", "/dev/t4"), ("E", "open", ""), ("F", "skip-open", "/dev/t6")]]
        windows = [(1, "", "/dev/t1"), (2, "", "/dev/t2"), (3, "", "/dev/t3"), (4, "", "/dev/t4")]
        W = lambda wid, sp, x: {"wid": wid, "space": sp, "x": x, "y": 0, "width": 100, "height": 50}
        probe = {"displays": [], "windows": {1: W(1, 1, 0), 2: W(2, 2, 5), 3: W(3, 2, 0), 4: W(4, 1, 0)}}
        lay = lambda n, sp, x: wp.Layout(n, "m", sp, x, 0, 100, 50)
        layouts = {"A": lay("A", 2, 0), "B": lay("B", 2, 0), "C": lay("C", 2, 0), "E": lay("E", 1, 0),
                   "F": lay("F", 1, 0)}
        steps = wp.plan_layout_apply(plan, layouts, windows, probe, only)
        return {s["name"]: s["action"] for s in steps}

    def test_actions(self):
        self.assertEqual(self._run(), {"A": "move", "B": "resize", "C": "ok", "D": "skip-nolayout",
                                       "E": "skip-closed", "F": "skip-nowin"})

    def test_only(self):
        self.assertEqual(self._run({"B"}), {"B": "resize"})


if __name__ == "__main__":
    unittest.main()
