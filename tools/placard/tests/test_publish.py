from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import BODY_SPLIT_THRESHOLD, publish  # noqa: E402


class ContentAddressing(unittest.TestCase):
    def test_name_embeds_the_body_hash(self):
        name = publish.body_filename("paper.pdf", "hello body")
        self.assertTrue(name.startswith("paper.pdf.placard."))
        self.assertTrue(name.endswith(".body.md"))
        self.assertIn(publish.sha_of("hello body")[:12], name)

    def test_different_bodies_get_different_names(self):
        a = publish.body_filename("paper.pdf", "one")
        b = publish.body_filename("paper.pdf", "two")
        self.assertNotEqual(a, b, "a fixed body filename is race S4")

    def test_same_body_is_stable(self):
        self.assertEqual(publish.body_filename("p.pdf", "x"),
                         publish.body_filename("p.pdf", "x"))


class Threshold(unittest.TestCase):
    def test_small_body_stays_inline(self):
        self.assertEqual(publish.choose_layout("x" * (BODY_SPLIT_THRESHOLD - 1)),
                         "inline")

    def test_body_at_threshold_goes_external(self):
        self.assertEqual(publish.choose_layout("x" * BODY_SPLIT_THRESHOLD),
                         "external")

    def test_body_just_over_threshold_goes_external(self):
        self.assertEqual(publish.choose_layout("x" * (BODY_SPLIT_THRESHOLD + 1)),
                         "external")

    def test_threshold_measures_encoded_bytes_not_characters(self):
        """A multibyte body must be judged on its encoded length. Judging
        characters would split inconsistently across languages."""
        multibyte = "é" * (BODY_SPLIT_THRESHOLD - 10)   # 2 bytes each
        self.assertEqual(publish.choose_layout(multibyte), "external")

    def test_layout_is_a_pure_function_of_the_body(self):
        """Hysteresis guard: the decision must never consult the entry file's
        size, or splitting shrinks the entry and the next run re-inlines it."""
        body = "x" * (BODY_SPLIT_THRESHOLD + 500)
        for _ in range(5):
            self.assertEqual(publish.choose_layout(body), "external")


class FakeDisk:
    def __init__(self):
        self.files: dict = {}

    def write(self, path, text):
        self.files[str(path)] = text

    def names(self):
        return sorted(Path(p).name for p in self.files)


def do_publish(disk, body, *, after_body=None, prose="\n## What this is\nx\n"):
    return publish.publish_digest(
        sidecar_path=Path("/t/paper.pdf.placard.md"),
        original_name="paper.pdf",
        body_text=body,
        frontmatter_fields={"source": "paper.pdf", "source_sha256": "SRC",
                            "placard_version": "2"},
        prose_markdown=prose,
        write_text=disk.write,
        after_body=after_body,
    )


class PublishOrder(unittest.TestCase):
    def test_external_body_is_written_before_the_entry(self):
        order = []
        disk = FakeDisk()

        def spy(path, text):
            order.append(Path(path).name)
            disk.write(path, text)

        publish.publish_digest(
            sidecar_path=Path("/t/paper.pdf.placard.md"),
            original_name="paper.pdf",
            body_text="x" * (BODY_SPLIT_THRESHOLD + 1),
            frontmatter_fields={"source": "paper.pdf"},
            prose_markdown="\n## What this is\nx\n",
            write_text=spy,
        )
        self.assertTrue(order[-1].endswith(".placard.md"),
                        "the entry file must be published LAST")
        self.assertEqual(len(order), 2)

    def test_s1_crash_after_body_leaves_no_entry_pointing_nowhere(self):
        """S1: publish the pointer, crash before finishing the body. Writing the
        entry last makes the opposite failure the only possible one: an
        unreferenced body, which a reader never sees."""
        disk = FakeDisk()

        def boom(*_a):
            raise RuntimeError("crash between body and entry")

        with self.assertRaises(RuntimeError):
            do_publish(disk, "x" * (BODY_SPLIT_THRESHOLD + 1), after_body=boom)
        self.assertNotIn("paper.pdf.placard.md", disk.names(),
                         "no entry file may exist after a mid-publish crash")
        self.assertEqual(len(disk.names()), 1, "only the orphan body exists")

    def test_entry_records_the_body_hash_and_path(self):
        disk = FakeDisk()
        body = "x" * (BODY_SPLIT_THRESHOLD + 1)
        fm = do_publish(disk, body)
        self.assertEqual(fm["body_layout"], "external")
        self.assertEqual(fm["body_sha256"], publish.sha_of(body))
        self.assertEqual(fm["body_path"], publish.body_filename("paper.pdf", body))
        self.assertEqual(fm["body_bytes"], str(len(body.encode("utf-8"))))

    def test_inline_publish_writes_one_file_with_the_body_in_it(self):
        disk = FakeDisk()
        fm = do_publish(disk, "[p.1]\nshort body")
        self.assertEqual(fm["body_layout"], "inline")
        self.assertEqual(disk.names(), ["paper.pdf.placard.md"])
        self.assertIn("short body", disk.files["/t/paper.pdf.placard.md"])
        self.assertIn("## Full text", disk.files["/t/paper.pdf.placard.md"])

    def test_inline_publish_records_no_body_path(self):
        disk = FakeDisk()
        fm = do_publish(disk, "[p.1]\nshort")
        self.assertNotIn("body_path", fm)

    def test_s2_inlining_does_not_delete_the_old_external_body(self):
        """S2/S6: an old external body must be RETAINED, not deleted during a
        publish. Deleting it is a separate sweep; deleting it here races a
        reader that already resolved the old pointer."""
        disk = FakeDisk()
        disk.write(Path("/t/paper.pdf.placard.oldhash12.body.md"), "old body")
        do_publish(disk, "[p.1]\nnow short")
        self.assertIn("paper.pdf.placard.oldhash12.body.md", disk.names(),
                      "a publish must never delete a superseded body")

    def test_published_entry_round_trips_through_the_reader(self):
        """End-to-end: what publish writes, read must resolve as ok."""
        from placardlib import read
        disk = FakeDisk()
        body = "x" * (BODY_SPLIT_THRESHOLD + 1)
        do_publish(disk, body)
        entry_text = disk.files["/t/paper.pdf.placard.md"]
        bodies = {Path(p).name: t for p, t in disk.files.items()
                  if p.endswith(".body.md")}
        r = read.resolve(entry_text, source_sha256="SRC", current_profile_id=None,
                         load_body=lambda n: bodies.get(n),
                         sha256_of_text=publish.sha_of)
        self.assertEqual(r.state, "ok")
        self.assertEqual(r.body, body)

    def test_prose_is_written_verbatim(self):
        disk = FakeDisk()
        prose = ("\n## What this is\nAuthored by a human.\n\n"
                 "## Gaps / uncertainties\nFigures.\n")
        do_publish(disk, "[p.1]\nshort", prose=prose)
        written = disk.files["/t/paper.pdf.placard.md"]
        self.assertIn("Authored by a human.", written)
        self.assertIn("## Gaps / uncertainties", written)


if __name__ == "__main__":
    unittest.main()
