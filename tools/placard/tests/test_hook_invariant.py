"""The SessionStart hook runs `placard.py --root <dir> announce` on EVERY
Claude Code session where it is installed. These tests pin its contract."""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import placard  # noqa: E402


def run_cli(*argv: str) -> tuple:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = placard.main(list(argv))
    return rc, out.getvalue()


class AnnounceContract(unittest.TestCase):
    def test_silent_and_zero_on_unplacarded_tree(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "notes.txt").write_text("plain file", encoding="utf-8")
            rc, out = run_cli("--root", d, "announce")
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "",
                         "announce must print NOTHING when no digests exist")

    def test_speaks_when_a_digest_exists(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "deck.pdf").write_bytes(b"%PDF-1.4 fake")
            (Path(d) / "deck.pdf.placard.md").write_text(
                "---\nsource: deck.pdf\ntier: standard\n---\n\n"
                "## What this is\nA deck.\n",
                encoding="utf-8")
            rc, out = run_cli("--root", d, "announce")
        self.assertEqual(rc, 0)
        self.assertIn("1", out, "announce must report the digest count")

    def test_does_not_hash_originals(self):
        """A hook that reads every deck to start a session is a hook people
        uninstall. Prove announce never opens the artifact's bytes."""
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "big.pdf"
            art.write_bytes(b"x" * 4096)
            (Path(d) / "big.pdf.placard.md").write_text(
                "---\nsource: big.pdf\n---\n\n## What this is\nx\n",
                encoding="utf-8")
            opened: list = []
            real_path_open = Path.open

            def spy(self_path, *a, **k):
                opened.append(str(self_path))
                return real_path_open(self_path, *a, **k)

            with unittest.mock.patch.object(Path, "open", spy):
                rc, _ = run_cli("--root", d, "announce")
        self.assertEqual(rc, 0)
        self.assertNotIn(str(art), opened,
                         "announce must not read the original's bytes")


if __name__ == "__main__":
    unittest.main()


class HomeShortCircuitTest(unittest.TestCase):
    def test_hook_silent_and_instant_at_home(self):
        import json, subprocess, time, pathlib, tempfile, os
        hook = pathlib.Path(__file__).resolve().parents[1] / "contrib" / "placard_sessionstart_hook.sh"
        with tempfile.TemporaryDirectory() as h:
            (pathlib.Path(h) / "x.pdf.placard.md").write_text("x")
            env = dict(os.environ, HOME=h)
            t = time.monotonic()
            r = subprocess.run(["bash", str(hook)], input=json.dumps({"cwd": h}),
                               capture_output=True, text=True, env=env)
            self.assertEqual((r.returncode, r.stdout), (0, ""))
            self.assertLess(time.monotonic() - t, 2)
