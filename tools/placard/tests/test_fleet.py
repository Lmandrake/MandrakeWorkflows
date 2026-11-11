from __future__ import annotations

import contextlib
import hashlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import placard  # noqa: E402
from placardlib import extract, fleet  # noqa: E402


def _git(d: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    return d


def _cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = placard.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def _current_digest(art: Path):
    sha = hashlib.sha256(art.read_bytes()).hexdigest()
    art.with_name(art.name + ".placard.md").write_text(
        f"---\nsource: {art.name}\nsource_sha256: {sha}\n"
        f"profile_id: {extract.current_profile_id()}\n"
        "authoring_status: current\n---\n\n## Full text\nx\n")


class Allowlist(unittest.TestCase):
    def test_no_allowlist_refuses_with_reason(self):
        rc, _out, err = _cli("fleet")
        self.assertEqual(rc, fleet.EXIT_REFUSED)
        self.assertIn("opt-in", err)

    def test_missing_file_glob_nonrepo_and_empty_refused(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "plain").mkdir()
            cases = {"missing": None, "glob": f"{d}/*\n",
                     "nonrepo": f"{d / 'plain'}\n", "gone": f"{d / 'nope'}\n",
                     "empty": "# only a comment\n\n"}
            for name, body in cases.items():
                f = d / f"{name}.txt"
                if body is not None:
                    f.write_text(body)
                with self.assertRaises(fleet.Refused, msg=name):
                    fleet.load_allowlist(f)
            rc, _o, _e = _cli("fleet", "--allowlist", str(d / "glob.txt"))
            self.assertEqual(rc, fleet.EXIT_REFUSED)

    def test_comments_and_tilde(self):
        with tempfile.TemporaryDirectory() as d:
            r = _git(Path(d) / "a")
            f = Path(d) / "list.txt"
            f.write_text(f"# approved 2026-11-10\n{r}   # inline note\n\n{r}\n")
            self.assertEqual(fleet.load_allowlist(f), [r.resolve()])


class Plan(unittest.TestCase):
    def _tree(self, d: Path):
        a = _git(d / "a")
        (a / "new.pdf").write_bytes(b"%PDF new")
        (a / "done.pdf").write_bytes(b"%PDF done")
        _current_digest(a / "done.pdf")
        (a / "old.pdf").write_bytes(b"%PDF old")
        _current_digest(a / "old.pdf")
        (a / "old.pdf").write_bytes(b"%PDF changed")
        (a / "node_modules").mkdir()
        (a / "node_modules" / "x.pdf").write_bytes(b"%PDF")
        s = _git(d / "s")
        (s / ".placard-skip").write_text("")
        (s / "secret.pdf").write_bytes(b"%PDF")
        u = _git(d / "u")
        (u / ".lodestar-untracked").write_text("")
        (u / "x.pdf").write_bytes(b"%PDF")
        off = _git(d / "off")
        (off / "never.pdf").write_bytes(b"%PDF")
        f = d / "list.txt"
        f.write_text(f"{a}\n{s}\n{u}\n")
        return f, a.resolve(), s.resolve(), u.resolve()

    def test_dry_run_counts_and_digests_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            f, a, s, u = self._tree(Path(d))
            rc, out, _e = _cli("fleet", "--allowlist", str(f))
            self.assertEqual(rc, 0)
            self.assertIn("dry run", out)
            self.assertIn("to digest 2 (missing 1, stale 1); unchanged 1", out)
            self.assertIn(".placard-skip 1", out)
            self.assertIn(".lodestar-untracked 1", out)
            self.assertNotIn(str((Path(d) / "off").resolve()), out)
            self.assertIn("TOTAL to digest 2", out)
            self.assertFalse((a / "new.pdf.placard.md").exists())

    def test_force_includes_current(self):
        with tempfile.TemporaryDirectory() as d:
            f, a, *_ = self._tree(Path(d))
            rep = fleet.plan_repo(a, placard, force=True)
            self.assertEqual(len(rep["todo"]), 3)

    def test_go_digests_only_todo(self):
        with tempfile.TemporaryDirectory() as d:
            f, a, s, u = self._tree(Path(d))
            seen = []
            orig = placard.cmd_digest
            placard.cmd_digest = lambda root, art, prof, describe_figures=True, **kw: (
                seen.append((art.name, describe_figures)) or 0)
            try:
                rc, out, _e = _cli("fleet", "--allowlist", str(f), "--go",
                                   "--no-figures")
            finally:
                placard.cmd_digest = orig
            self.assertEqual(rc, 0)
            self.assertEqual(sorted(seen), [("new.pdf", False), ("old.pdf", False)])
            self.assertIn("TOTAL digested 2, failed 0, unchanged 1", out)

    def test_go_is_one_batch_per_repo(self):
        with tempfile.TemporaryDirectory() as d:
            f, a, s, u = self._tree(Path(d))
            calls = []
            orig = placard.digest_many
            placard.digest_many = lambda root, arts, prof, **kw: (
                calls.append([x.name for x in arts]) or
                (0, {"digested": len(arts), "unchanged": 0, "failed": 0}))
            try:
                _cli("fleet", "--allowlist", str(f), "--go", "--no-figures")
            finally:
                placard.digest_many = orig
            self.assertEqual(calls, [["new.pdf", "old.pdf"]])

    def test_profile_change_is_not_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            f, a, *_ = self._tree(Path(d))
            rep = fleet.plan_repo(a, placard, profile="docling-0/other/x")
            self.assertEqual(rep["unchanged"], 0)
            self.assertEqual(len(rep["todo"]), 3)


if __name__ == "__main__":
    unittest.main()
