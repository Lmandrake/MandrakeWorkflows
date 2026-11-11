"""Tests for `waypoint focus`: session matching and the open/skip plan.

Run:  python3 -m unittest discover -s ~/dev/MandrakeWorkflows/tools/waypoint/tests
Stdlib only. Nothing here talks to iTerm2 or writes the shell file.
"""
import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
_loader = importlib.machinery.SourceFileLoader("waypoint_mod", str(HERE / "waypoint"))
_spec = importlib.util.spec_from_loader("waypoint_mod", _loader)
assert _spec is not None
wp = importlib.util.module_from_spec(_spec)
_loader.exec_module(wp)


class SessionMatchTest(unittest.TestCase):
    def test_exact_with_job_suffix(self):
        self.assertTrue(wp.session_matches("Claude: ATLAS (claude)", "/x/ATLAS"))

    def test_exact_without_suffix(self):
        self.assertTrue(wp.session_matches("Claude: ATLAS", "/x/ATLAS"))

    def test_other_job_suffix(self):
        self.assertTrue(wp.session_matches("Claude: ATLAS (node)", "/x/ATLAS"))

    def test_no_prefix_or_superstring_match(self):
        for name in ("Claude: ATLAS2 (claude)", "Claude: XATLAS (claude)",
                     "Claude: ATLAS (claude) (claude)", "Claude: atlas (claude)", "ATLAS",
                     "Claude:ATLAS (claude)", "-zsh", "Python"):
            with self.subTest(name=name):
                self.assertFalse(wp.session_matches(name, "/x/ATLAS"))

    def test_basename_with_space(self):
        d = "/g/Some Group/Alpha Emulators"
        self.assertTrue(wp.session_matches("Claude: Alpha Emulators (claude)", d))
        self.assertFalse(wp.session_matches("Claude: Alpha (claude)", d))

    def test_trailing_slash(self):
        self.assertTrue(wp.session_matches("Claude: Notes (claude)", "/u/dev/Notes/"))

    def test_spinner_titled_session_is_not_a_match(self):
        self.assertFalse(wp.session_matches(
            "◐ Cosmograph and artistic data visualization repos (claude)", "/u/dev/MandrakeVisualize"))

    def test_bare_title_needs_claude_job(self):
        self.assertTrue(wp.session_matches("Notes (claude)", "/u/dev/Notes"))
        self.assertFalse(wp.session_matches("Notes (-zsh)", "/u/dev/Notes"))
        self.assertFalse(wp.session_matches("Notes2 (claude)", "/u/dev/Notes"))
        self.assertFalse(wp.session_matches("Notes", "/u/dev/Notes"))

    def test_parse_sessions(self):
        raw = "Claude: Lodestar (claude) ||| /dev/ttys005\n-zsh ||| /dev/ttys003\n\n"
        self.assertEqual(wp.parse_iterm_sessions(raw),
                         [("Claude: Lodestar (claude)", "/dev/ttys005"), ("-zsh", "/dev/ttys003")])


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for d in ("ATLAS", "ATLAS2", "Notes", "Fetcher"):
            (root / d).mkdir()
        self.root = root
        self.wps = [wp.Waypoint("ATLAS", str(root / "ATLAS")),
                    wp.Waypoint("ATLAS2", str(root / "ATLAS2")),
                    wp.Waypoint("NOTES", str(root / "Notes")),
                    wp.Waypoint("FETCHER", str(root / "Fetcher")),
                    wp.Waypoint("GONE", str(root / "nope"))]

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, launches, sessions, machine="m1"):
        p = wp.plan_focus_launch(launches, self.wps, machine, wp.DEFAULT_LAUNCH_TEMPLATE, sessions)
        return {e["launch"].name: e["action"] for e in p}

    def test_open_only_what_is_missing(self):
        launches = [wp.Launch("ATLAS", waypoint="ATLAS", focus=True),
                    wp.Launch("ATLAS2", waypoint="ATLAS2", focus=True),
                    wp.Launch("Fetcher", waypoint="FETCHER", focus=False)]
        got = self.plan(launches, [("Claude: ATLAS2 (claude)", "/dev/ttys1")])
        self.assertEqual(got, {"ATLAS": "open", "ATLAS2": "skip-open"})

    def test_unfocused_rows_never_planned(self):
        got = self.plan([wp.Launch("Fetcher", waypoint="FETCHER")], [])
        self.assertEqual(got, {})

    def test_machine_row_wins_and_its_focus_counts(self):
        launches = [wp.Launch("Notes", waypoint="NOTES", focus=False),
                    wp.Launch("Notes", waypoint="NOTES", focus=True, machine="m1")]
        self.assertEqual(self.plan(launches, []), {"Notes": "open"})
        self.assertEqual(self.plan(launches, [], machine="m2"), {})

    def test_missing_dir_skipped(self):
        got = self.plan([wp.Launch("Gone", waypoint="GONE", focus=True),
                         wp.Launch("Untracked", waypoint="NOSUCH", focus=True)], [])
        self.assertEqual(got, {"Gone": "skip-nodir", "Untracked": "skip-nodir"})

    def test_two_rows_same_dir_open_once(self):
        launches = [wp.Launch("A", waypoint="ATLAS", focus=True),
                    wp.Launch("B", waypoint="ATLAS", focus=True)]
        self.assertEqual(self.plan(launches, []), {"A": "open", "B": "skip-dup"})

    def test_cwd_signal_counts_as_open(self):
        launches = [wp.Launch("ATLAS", waypoint="ATLAS", focus=True),
                    wp.Launch("ATLAS2", waypoint="ATLAS2", focus=True)]
        p = wp.plan_focus_launch(launches, self.wps, "m1", wp.DEFAULT_LAUNCH_TEMPLATE,
                                 [("Something else (claude)", "/dev/ttys9")],
                                 [("/dev/ttys9", str(self.root / "ATLAS"))])
        self.assertEqual({e["launch"].name: e["action"] for e in p}, {"ATLAS": "skip-open", "ATLAS2": "open"})

    def test_restored_idle_window_is_reused(self):
        launches = [wp.Launch("ATLAS", waypoint="ATLAS", focus=True),
                    wp.Launch("ATLAS2", waypoint="ATLAS2", focus=True)]
        sessions = [("Claude: ATLAS (-zsh)", "/dev/ttys4"), ("Claude: ATLAS2 (-zsh)", "/dev/ttys5")]
        p = wp.plan_focus_launch(launches, self.wps, "m1", wp.DEFAULT_LAUNCH_TEMPLATE, sessions,
                                 [("/dev/ttys5", str(self.root / "ATLAS2"))])
        got = {e["launch"].name: (e["action"], e.get("tty")) for e in p}
        self.assertEqual(got, {"ATLAS": ("reuse", "/dev/ttys4"), "ATLAS2": ("skip-open", None)})

    def test_live_session_beats_idle_twin(self):
        p = wp.plan_focus_launch([wp.Launch("ATLAS", waypoint="ATLAS", focus=True)], self.wps, "m1",
                                 wp.DEFAULT_LAUNCH_TEMPLATE,
                                 [("Claude: ATLAS (-zsh)", "/dev/ttys4"), ("Claude: ATLAS (claude)", "/dev/ttys6")])
        self.assertEqual(p[0]["action"], "skip-open")

    def test_command_is_the_rendered_launch(self):
        p = wp.plan_focus_launch([wp.Launch("ATLAS", waypoint="ATLAS", focus=True)], self.wps, "m1",
                                 wp.DEFAULT_LAUNCH_TEMPLATE, [])
        self.assertEqual(p[0]["command"], "claude --dangerously-skip-permissions -n ATLAS")


class FocusColumnRoundTripTest(unittest.TestCase):
    def test_round_trip_and_legacy_8_column_rows(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "launches.md"
            old = wp.LAUNCH_DB_PATH
            wp.LAUNCH_DB_PATH = path
            try:
                path.write_text(
                    "Default launch template: x {NAME}\n\n"
                    "| Name | Waypoint | Path | Command | Added | Status | Notes | Machine |\n"
                    "|---|---|---|---|---|---|---|---|\n"
                    "| Old | OLD |  |  | 2026-01-01 | active |  |  |\n", encoding="utf-8")
                rows = wp.load_launches()
                self.assertEqual([(r.name, r.focus) for r in rows], [("Old", False)])
                rows.append(wp.Launch("New", waypoint="NEW", added="2026-10-11", focus=True))
                wp.save_launches(rows, "x {NAME}")
                again = {r.name: r.focus for r in wp.load_launches()}
                self.assertEqual(again, {"Old": False, "New": True})
                self.assertIn("| Machine | Focus |", path.read_text(encoding="utf-8"))
            finally:
                wp.LAUNCH_DB_PATH = old


if __name__ == "__main__":
    unittest.main()
