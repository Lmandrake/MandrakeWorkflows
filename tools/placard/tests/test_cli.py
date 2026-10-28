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


def run_cli(*argv: str) -> tuple:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = placard.main(list(argv))
    return rc, out.getvalue()


class ReadCommand(unittest.TestCase):
    def _tree(self, d: str, body="[p.1]\nhello world"):
        art = Path(d) / "paper.pdf"
        art.write_bytes(b"%PDF-1.4 bytes")
        digest = Path(d) / "paper.pdf.placard.md"
        sha = hashlib.sha256(art.read_bytes()).hexdigest()
        digest.write_text(
            "---\nsource: paper.pdf\n"
            f"source_sha256: {sha}\n"
            "placard_version: 2\nbody_layout: inline\nauthoring_status: current\n"
            f"---\n\n## What this is\nA paper.\n\n## Full text\n{body}\n",
            encoding="utf-8")
        return art

    def test_read_prints_state_and_body(self):
        with tempfile.TemporaryDirectory() as d:
            art = self._tree(d)
            rc, out = run_cli("--root", d, "read", str(art))
        self.assertEqual(rc, 0)
        self.assertIn("ok", out)
        self.assertIn("hello world", out)

    def test_read_reports_source_stale_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as d:
            art = self._tree(d)
            art.write_bytes(b"%PDF-1.4 CHANGED")
            rc, out = run_cli("--root", d, "read", str(art))
        self.assertIn("source-stale", out)
        self.assertNotEqual(rc, 0)

    def test_read_missing_digest_is_unavailable_and_authorizes_original(self):
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "lonely.pdf"
            art.write_bytes(b"%PDF-1.4")
            rc, out = run_cli("--root", d, "read", str(art))
        self.assertIn("unavailable", out)
        self.assertIn("open the original", out.lower())


class VerifyDeep(unittest.TestCase):
    def test_deep_flags_a_coverage_claim_that_plain_verify_misses(self):
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "paper.pdf"
            art.write_bytes(b"%PDF-1.4 bytes")
            sha = hashlib.sha256(art.read_bytes()).hexdigest()
            body = " ".join(["word"] * 3000)
            (Path(d) / "paper.pdf.placard.md").write_text(
                "---\nsource: paper.pdf\n"
                f"source_sha256: {sha}\n"
                "placard_version: 2\nconfidence: high\nbody_layout: inline\n"
                "authoring_status: current\n---\n"
                "\n## Gaps / uncertainties\n"
                "Only the first page / abstract was read (17pp total).\n"
                f"\n## Full text\n{body}\n",
                encoding="utf-8")
            rc_plain, out_plain = run_cli("--root", d, "verify")
            rc_deep, out_deep = run_cli("--root", d, "verify", "--deep")
        self.assertEqual(rc_plain, 0, "plain verify sees bytes only and passes")
        self.assertNotIn("COVERAGE_CLAIM_IN_PROSE", out_plain)
        self.assertIn("COVERAGE_CLAIM_IN_PROSE", out_deep)
        self.assertNotEqual(rc_deep, 0)


if __name__ == "__main__":
    unittest.main()
