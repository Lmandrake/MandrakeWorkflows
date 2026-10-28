from __future__ import annotations

import contextlib
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import placard  # noqa: E402


def run_cli(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = placard.main(list(argv))
    return rc, out.getvalue()


class RefreshCommand(unittest.TestCase):
    def _tree(self, d):
        art = Path(d) / "paper.pdf"
        art.write_bytes(b"%PDF-1.4 original")
        (Path(d) / "paper.pdf.placard.md").write_text(
            "---\nsource: paper.pdf\nsource_sha256: WRONGHASH\n"
            "placard_version: 2\nbody_layout: inline\nauthoring_status: current\n"
            "---\n\n## What this is\nPrecious hand-written summary.\n"
            "\n## Full text\n[p.1]\nthe extraction\n",
            encoding="utf-8")
        return art

    def test_refresh_clears_staleness_without_destroying_prose(self):
        with tempfile.TemporaryDirectory() as d:
            art = self._tree(d)
            rc_before, _ = run_cli("--root", d, "verify")
            self.assertNotEqual(rc_before, 0, "digest starts stale")

            rc, _ = run_cli("--root", d, "refresh", str(art))
            self.assertEqual(rc, 0)

            text = (Path(d) / "paper.pdf.placard.md").read_text(encoding="utf-8")
            self.assertIn("Precious hand-written summary.", text)
            self.assertIn("the extraction", text)
            self.assertIn(hashlib.sha256(art.read_bytes()).hexdigest(), text)

            rc_after, _ = run_cli("--root", d, "verify")
            self.assertEqual(rc_after, 0, "digest is current after refresh")

    def test_init_force_warns_that_it_destroys_prose(self):
        with tempfile.TemporaryDirectory() as d:
            art = self._tree(d)
            _, out = run_cli("--root", d, "init", str(art), "--force")
        self.assertIn("refresh", out.lower(),
                      "init --force must point at the non-destructive remedy")



class RetiredWriter(unittest.TestCase):
    """Spec 7: data migration may lag, a writer may not. The script that
    falsified the corpus must refuse rather than quietly still work."""

    def test_backfill_bodies_refuses_and_names_the_replacement(self):
        import subprocess
        script = Path(__file__).resolve().parents[1] / "contrib" / "backfill_bodies.py"
        proc = subprocess.run([sys.executable, str(script)],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0, "it must not exit 0")
        self.assertIn("RETIRED", proc.stderr)
        self.assertIn("placard.py", proc.stderr)
        self.assertIn("digest", proc.stderr)


class ScaffoldStatus(unittest.TestCase):
    """status_of must recognise an unfilled scaffold in BOTH schema versions:
    v1 used confidence: TODO, v2 uses authoring_status: unknown."""

    def test_v2_unknown_authoring_status_reads_as_scaffolded(self):
        import placard as pl
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "x.pdf"
            art.write_bytes(b"%PDF")
            sha = hashlib.sha256(art.read_bytes()).hexdigest()
            art.with_name("x.pdf.placard.md").write_text(
                f"---\nsource: x.pdf\nsource_sha256: {sha}\n"
                "placard_version: 2\nauthoring_status: unknown\n---\n",
                encoding="utf-8")
            self.assertEqual(pl.status_of(art), "scaffolded")

    def test_v1_todo_confidence_still_reads_as_scaffolded(self):
        import placard as pl
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "y.pdf"
            art.write_bytes(b"%PDF")
            sha = hashlib.sha256(art.read_bytes()).hexdigest()
            art.with_name("y.pdf.placard.md").write_text(
                f"---\nsource: y.pdf\nsource_sha256: {sha}\n"
                "placard_version: 1\nconfidence: TODO\n---\n",
                encoding="utf-8")
            self.assertEqual(pl.status_of(art), "scaffolded")

if __name__ == "__main__":
    unittest.main()
