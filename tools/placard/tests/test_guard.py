from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import placard  # noqa: E402
from placardlib import guard  # noqa: E402


def _repo(d):
    subprocess.run(["git", "init", "-q", d], check=True)
    (Path(d) / ".gitattributes").write_text(
        "vault/** filter=git-crypt diff=git-crypt\n.gitattributes !filter\n")
    (Path(d) / "vault").mkdir()
    (Path(d) / "vault" / "tax.pdf").write_bytes(b"%PDF")
    (Path(d) / "open.pdf").write_bytes(b"%PDF")


class Guard(unittest.TestCase):
    def test_git_crypt_path_refused_and_open_path_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            _repo(d)
            self.assertIn("git-crypt", guard.refusal_reason(Path(d) / "vault" / "tax.pdf"))
            self.assertIsNone(guard.refusal_reason(Path(d) / "open.pdf"))

    def test_marker_in_ancestor_refused(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a" / "b").mkdir(parents=True)
            (Path(d) / "a" / ".placard-skip").write_text("")
            f = Path(d) / "a" / "b" / "x.pdf"
            f.write_bytes(b"%PDF")
            self.assertIn(".placard-skip", guard.refusal_reason(f))

    def test_scan_excludes_and_digest_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            _repo(d)
            root = Path(d).resolve()
            names = [p.name for p in placard.iter_artifacts(root)]
            self.assertEqual(names, ["open.pdf"])
            self.assertEqual([p.name for p, _ in placard.iter_excluded(root)], ["tax.pdf"])
            self.assertEqual(placard.cmd_digest(root, root / "vault" / "tax.pdf", "text-v1"), 6)


if __name__ == "__main__":
    unittest.main()
