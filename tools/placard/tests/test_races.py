"""The two races I had deferred, now closed.

S7: on a synchronising mount the entry file can become visible before the body
it names. Locally-correct write ordering cannot prevent that, because the
ordering that matters is the mount's delivery order.

The prose race: extraction takes seconds to minutes, which is ample time for a
human or another agent to improve the summary. "Preserve prose" must not mean
"overwrite a newer edit with the copy I read at the start".
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import read, refresh  # noqa: E402


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def entry(**over) -> str:
    fm = {"source": "paper.pdf", "source_sha256": "SRC",
          "placard_version": "2", "body_layout": "external",
          "authoring_status": "current"}
    fm.update(over)
    lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    return f"---\n{lines}\n---\n\n## What this is\nA paper.\n"


class S7_BodyArrivesLate(unittest.TestCase):
    def test_body_appearing_on_the_second_attempt_resolves_ok(self):
        body = "[p.1]\narrived late"
        store: dict = {}
        slept: list = []

        def load(name):
            return store.get(name)

        def wake(seconds):
            slept.append(seconds)
            store["b.body.md"] = body       # the mount catches up

        r = read.resolve_with_retry(
            entry(body_path="b.body.md", body_sha256=sha(body)),
            source_sha256="SRC", current_profile_id=None,
            load_body=load, sha256_of_text=sha, sleep=wake)
        self.assertEqual(r.state, "ok")
        self.assertEqual(r.body, body)
        self.assertEqual(len(slept), 1, "it must not sleep more than needed")

    def test_a_body_that_never_arrives_becomes_unavailable(self):
        r = read.resolve_with_retry(
            entry(body_path="b.body.md", body_sha256="X"),
            source_sha256="SRC", current_profile_id=None,
            load_body=lambda _n: None, sha256_of_text=sha,
            sleep=lambda _s: None)
        self.assertEqual(r.state, "unavailable",
                         "exhausted retry must authorize opening the original")
        self.assertTrue(read.authorizes_original(r.state))
        self.assertIn("attempts", r.detail)

    def test_a_stale_entry_is_re_read_between_attempts(self):
        """The entry itself may be mid-publish; retrying the same stale pointer
        would never converge."""
        good = "[p.1]\nright generation"
        store = {"new.body.md": good}
        fresh = entry(body_path="new.body.md", body_sha256=sha(good))

        r = read.resolve_with_retry(
            entry(body_path="old.body.md", body_sha256="OLD"),
            source_sha256="SRC", current_profile_id=None,
            load_body=lambda n: store.get(n), sha256_of_text=sha,
            reread_entry=lambda: fresh, sleep=lambda _s: None)
        self.assertEqual(r.state, "ok")
        self.assertEqual(r.body, good)

    def test_non_transient_states_are_not_retried(self):
        slept: list = []
        body = "[p.1]\nfine"
        r = read.resolve_with_retry(
            entry(body_path="b.body.md", body_sha256=sha(body)),
            source_sha256="DIFFERENT",          # source-stale, a fact
            current_profile_id=None,
            load_body=lambda _n: body, sha256_of_text=sha,
            sleep=lambda s: slept.append(s))
        self.assertEqual(r.state, "source-stale")
        self.assertEqual(slept, [], "a fact about the files must not be retried")

    def test_retry_is_bounded(self):
        slept: list = []
        read.resolve_with_retry(
            entry(body_path="b.body.md", body_sha256="X"),
            source_sha256="SRC", current_profile_id=None,
            load_body=lambda _n: None, sha256_of_text=sha,
            sleep=lambda s: slept.append(s), attempts=3)
        self.assertEqual(len(slept), 2, "3 attempts means 2 sleeps")


ENTRY_WITH_PROSE = (
    "---\nsource: p.pdf\nsource_sha256: OLD\nplacard_version: 2\n"
    "body_layout: inline\nauthoring_status: current\n---\n"
    "\n## What this is\nThe ORIGINAL hand-written summary.\n"
    "\n## Full text\n[p.1]\nold body\n"
)
ENTRY_PROSE_EDITED = ENTRY_WITH_PROSE.replace(
    "The ORIGINAL hand-written summary.",
    "A BETTER summary somebody wrote while we were extracting.")


class ProseEditedDuringExtraction(unittest.TestCase):
    def test_a_changed_prose_aborts_rather_than_overwriting(self):
        disk: dict = {}
        with self.assertRaises(refresh.ProseConflict):
            refresh.refresh_body(
                entry_text=ENTRY_WITH_PROSE,
                sidecar_path=Path("/t/p.pdf.placard.md"),
                original_name="p.pdf", new_body="[p.1]\nnew body",
                new_fields={}, write_text=lambda p, t: disk.__setitem__(str(p), t),
                reread_entry=lambda: ENTRY_PROSE_EDITED)
        self.assertEqual(disk, {}, "nothing may be written on a conflict")

    def test_the_error_says_nothing_was_written_and_what_to_do(self):
        try:
            refresh.refresh_body(
                entry_text=ENTRY_WITH_PROSE,
                sidecar_path=Path("/t/p.pdf.placard.md"),
                original_name="p.pdf", new_body="[p.1]\nnew",
                new_fields={}, write_text=lambda p, t: None,
                reread_entry=lambda: ENTRY_PROSE_EDITED)
        except refresh.ProseConflict as exc:
            self.assertIn("Nothing was written", str(exc))
            self.assertIn("Re-run", str(exc))
        else:
            self.fail("expected ProseConflict")

    def test_unchanged_prose_proceeds(self):
        disk: dict = {}
        refresh.refresh_body(
            entry_text=ENTRY_WITH_PROSE,
            sidecar_path=Path("/t/p.pdf.placard.md"),
            original_name="p.pdf", new_body="[p.1]\nnew body",
            new_fields={}, write_text=lambda p, t: disk.__setitem__(str(p), t),
            reread_entry=lambda: ENTRY_WITH_PROSE)
        self.assertTrue(disk)
        self.assertIn("ORIGINAL hand-written summary",
                      disk["/t/p.pdf.placard.md"])

    def test_whitespace_only_prose_change_is_not_a_conflict(self):
        """Otherwise a trailing-newline difference aborts every refresh."""
        disk: dict = {}
        wobbled = ENTRY_WITH_PROSE.replace(
            "## What this is\nThe ORIGINAL",
            "## What this is\n\nThe  ORIGINAL")
        refresh.refresh_body(
            entry_text=ENTRY_WITH_PROSE,
            sidecar_path=Path("/t/p.pdf.placard.md"),
            original_name="p.pdf", new_body="[p.1]\nnew",
            new_fields={}, write_text=lambda p, t: disk.__setitem__(str(p), t),
            reread_entry=lambda: wobbled)
        self.assertTrue(disk)
        self.assertIn("## What this is\n\nThe  ORIGINAL", disk["/t/p.pdf.placard.md"],
                      "the newer whitespace is published, not the stale copy")

    def test_no_reread_means_no_check_and_no_crash(self):
        disk: dict = {}
        refresh.refresh_body(
            entry_text=ENTRY_WITH_PROSE,
            sidecar_path=Path("/t/p.pdf.placard.md"),
            original_name="p.pdf", new_body="[p.1]\nnew",
            new_fields={}, write_text=lambda p, t: disk.__setitem__(str(p), t))
        self.assertTrue(disk)


if __name__ == "__main__":
    unittest.main()
