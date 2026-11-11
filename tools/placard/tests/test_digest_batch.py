"""digest skips current digests (one shared check with fleet) and takes many
paths in one process. Runs without Docling: the skip comes before the probe."""
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

PROFILE = "docling-9.9/text-v1/soffice-absent"


def _cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = placard.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def _digest(art: Path, profile=PROFILE, **extra):
    sha = hashlib.sha256(art.read_bytes()).hexdigest()
    lines = [f"source: {art.name}", f"source_sha256: {sha}",
             f"profile_id: {profile}", "authoring_status: unknown_prose"]
    lines += [f"{k}: {v}" for k, v in extra.items()]
    art.with_name(art.name + ".placard.md").write_text(
        "---\n" + "\n".join(lines) + "\n---\n\n## Full text\nx\n")


class DigestCurrent(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.d = Path(self._d.name)
        self.art = self.d / "a.pdf"
        self.art.write_bytes(b"%PDF a")

    def tearDown(self):
        self._d.cleanup()

    def cur(self, **kw):
        return placard.digest_current(self.art, current_profile=PROFILE, **kw)

    def test_missing_stale_and_no_profile(self):
        self.assertEqual(self.cur(), (False, "missing"))
        _digest(self.art, profile="")
        self.assertFalse(self.cur()[0])
        _digest(self.art)
        self.art.write_bytes(b"%PDF changed")
        self.assertEqual(self.cur(), (False, "stale"))

    def test_profile_change_is_not_current(self):
        _digest(self.art, profile="docling-1.0/text-v1/soffice-absent")
        ok, why = self.cur()
        self.assertFalse(ok)
        self.assertIn("profile", why)

    def test_unknown_profile_here_is_not_compared_but_said(self):
        _digest(self.art, profile="docling-1.0/text-v1/soffice-absent")
        ok, why = placard.digest_current(
            self.art, current_profile="docling-unknown/text-v1/soffice-absent")
        self.assertTrue(ok)
        self.assertIn("not compared", why)

    def test_figures_undescribed_only_matters_when_figures_wanted(self):
        _digest(self.art, figures_detected="3", figures_described="0")
        self.assertEqual(self.cur(), (False, "figures not described"))
        self.assertTrue(self.cur(describe_figures=False)[0])
        _digest(self.art, figures_detected="3", figures_described="2",
                figures_described_known="true", figures_description_failed="1")
        self.assertFalse(self.cur()[0])
        _digest(self.art, figures_detected="3", figures_described="3",
                figures_described_known="true", figures_description_failed="0")
        self.assertTrue(self.cur()[0])

    def test_no_figures_detected_is_current(self):
        _digest(self.art, figures_detected="0")
        self.assertTrue(self.cur()[0])


class DigestCli(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.d = Path(self._d.name)
        self.arts = []
        for n in "abc":
            a = self.d / f"{n}.pdf"
            a.write_bytes(f"%PDF {n}".encode())
            self.arts.append(a)
        from placardlib import extract
        self.extract = extract
        self._cp = extract.current_profile_id
        extract.current_profile_id = lambda *a, **k: PROFILE

    def tearDown(self):
        self.extract.current_profile_id = self._cp
        self._d.cleanup()

    def test_current_digest_is_skipped_without_docling(self):
        _digest(self.arts[0])
        rc, out, _e = _cli("--root", str(self.d), "digest", "--no-figures",
                           str(self.arts[0]))
        self.assertEqual(rc, 0)
        self.assertIn("unchanged: a.pdf.placard.md", out)

    def test_force_goes_past_the_skip(self):
        _digest(self.arts[0])
        avail = self.extract.docling_available
        self.extract.docling_available = lambda: False
        try:
            rc, out, err = _cli("--root", str(self.d), "digest", "--no-figures",
                                "--force", str(self.arts[0]))
        finally:
            self.extract.docling_available = avail
        self.assertEqual(rc, 3)                 # reached the Docling probe
        self.assertNotIn("unchanged", out)

    def test_many_paths_one_call_counts_each(self):
        for a in self.arts:
            _digest(a)
        rc, out, _e = _cli("--root", str(self.d), "digest", "--no-figures",
                           *map(str, self.arts))
        self.assertEqual(rc, 0)
        self.assertEqual(out.count("unchanged:"), 3)
        self.assertIn("TOTAL digested 0, unchanged 3, failed 0", out)

    def test_one_failure_is_named_and_fails_the_batch(self):
        _digest(self.arts[0])
        _digest(self.arts[1])
        gone = self.d / "gone.pdf"
        rc, out, err = _cli("--root", str(self.d), "digest", "--no-figures",
                            str(self.arts[0]), str(gone), str(self.arts[1]))
        self.assertEqual(rc, 1)
        self.assertIn("FAILED rc=2 gone.pdf", err)
        self.assertIn("TOTAL digested 0, unchanged 2, failed 1", out)

    def test_single_path_keeps_its_own_exit_code(self):
        rc, _o, _e = _cli("--root", str(self.d), "digest", "--no-figures",
                          str(self.d / "gone.pdf"))
        self.assertEqual(rc, 2)

    def test_batch_reads_profile_once(self):
        calls = []
        self.extract.current_profile_id = lambda *a, **k: (
            calls.append(1) or PROFILE)
        for a in self.arts:
            _digest(a)
        _cli("--root", str(self.d), "digest", "--no-figures",
             *map(str, self.arts))
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
