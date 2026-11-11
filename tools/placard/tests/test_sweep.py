from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import placard  # noqa: E402
from placardlib import publish, refresh, sweep  # noqa: E402

BIG = "word " * 3000          # over BODY_SPLIT_THRESHOLD: external layout


def _w(p, t):
    Path(p).write_text(t, encoding="utf-8")


def _publish(d, body):
    side = Path(d) / "a.pdf.placard.md"
    return publish.publish_digest(
        sidecar_path=side, original_name="a.pdf", body_text=body,
        frontmatter_fields={"source": "a.pdf"}, prose_markdown="## What\nhi\n",
        write_text=_w)


def _old(path):
    os.utime(path, (1, 1))


def run_cli(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = placard.main(list(argv))
    return rc, out.getvalue()


class RefreshRemovesSuperseded(unittest.TestCase):
    def test_old_body_gone_new_body_kept(self):
        with tempfile.TemporaryDirectory() as d:
            fm1 = _publish(d, BIG)
            old = Path(d, fm1["body_path"])
            side = Path(d, "a.pdf.placard.md")
            fm2 = refresh.refresh_body(
                entry_text=side.read_text(), sidecar_path=side,
                original_name="a.pdf", new_body=BIG + " changed",
                new_fields={}, write_text=_w,
                remove_superseded=sweep.remove_superseded)
            self.assertNotEqual(fm1["body_path"], fm2["body_path"])
            self.assertFalse(old.exists())
            self.assertTrue(Path(d, fm2["body_path"]).exists())

    def test_same_body_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            fm1 = _publish(d, BIG)
            side = Path(d, "a.pdf.placard.md")
            fm2 = refresh.refresh_body(
                entry_text=side.read_text(), sidecar_path=side,
                original_name="a.pdf", new_body=BIG, new_fields={},
                write_text=_w, remove_superseded=sweep.remove_superseded)
            self.assertEqual(fm1["body_path"], fm2["body_path"])
            self.assertTrue(Path(d, fm2["body_path"]).exists())

    def test_never_deletes_a_non_body_name(self):
        with tempfile.TemporaryDirectory() as d:
            victim = Path(d, "precious.txt")
            victim.write_text("x")
            self.assertFalse(sweep.remove_superseded(
                Path(d, "a.pdf.placard.md"), "precious.txt", "n"))
            self.assertFalse(sweep.remove_superseded(
                Path(d, "a.pdf.placard.md"),
                "../a.pdf.placard.aaaaaaaaaaaa.body.md", "n"))
            self.assertTrue(victim.exists())


class SweepCommand(unittest.TestCase):
    def _orphan(self, d, name="a.pdf.placard.aaaaaaaaaaaa.body.md"):
        p = Path(d, name)
        p.write_text("orphaned")
        _old(p)
        return p

    def test_dry_run_lists_and_keeps_then_apply_deletes(self):
        with tempfile.TemporaryDirectory() as d:
            fm = _publish(d, BIG)
            kept = Path(d, fm["body_path"])
            _old(kept)
            orphan = self._orphan(d)
            rc, out = run_cli("--root", d, "sweep")
            self.assertEqual(rc, 0)
            self.assertIn(orphan.name, out)
            self.assertIn("1 orphan", out)
            self.assertTrue(orphan.exists())
            rc, out = run_cli("--root", d, "sweep", "--apply")
            self.assertFalse(orphan.exists())
            self.assertTrue(kept.exists(), "a referenced body is never deleted")

    def test_referenced_by_a_second_sidecar_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            fm = _publish(d, BIG)
            kept = Path(d, fm["body_path"])
            _old(kept)
            Path(d, "b.pdf.placard.md").write_text(
                f"---\nbody_layout: external\nbody_path: {kept.name}\n---\n\nx\n")
            Path(d, "a.pdf.placard.md").unlink()
            run_cli("--root", d, "sweep", "--apply")
            self.assertTrue(kept.exists())

    def test_young_body_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "a.pdf.placard.bbbbbbbbbbbb.body.md")
            p.write_text("in flight")
            rc, out = run_cli("--root", d, "sweep", "--apply")
            self.assertTrue(p.exists())
            self.assertIn("1 too young", out)

    def test_unparseable_entry_makes_the_directory_untouchable(self):
        with tempfile.TemporaryDirectory() as d:
            orphan = self._orphan(d)
            Path(d, "z.pdf.placard.md").write_bytes(b"---\nx\n")
            real = sweep.schema.load_digest

            def boom(text):
                raise ValueError("cannot parse")
            sweep.schema.load_digest = boom
            try:
                rc, out = run_cli("--root", d, "sweep", "--apply")
            finally:
                sweep.schema.load_digest = real
            self.assertTrue(orphan.exists())
            self.assertIn("1 dir(s) skipped", out)

    def test_nested_dirs_found_and_map_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            sub = Path(d, "sub")
            sub.mkdir()
            orphan = self._orphan(sub)
            _w(Path(d, "PROJECT.placard.md"), "---\n---\nmap\n")
            run_cli("--root", d, "sweep", "--apply")
            self.assertFalse(orphan.exists())
            self.assertTrue(Path(d, "PROJECT.placard.md").exists())


if __name__ == "__main__":
    unittest.main()
