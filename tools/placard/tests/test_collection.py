from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import collection, figures  # noqa: E402


def names(n=60, stem="ab_north_xy_feature"):
    return [f"{stem}_{i:03d}.png" for i in range(n)]


class Sampling(unittest.TestCase):
    def test_samples_are_spread_not_taken_from_the_front(self):
        got = collection.sample_paths(names(60))
        self.assertEqual(len(got), 3)
        self.assertNotEqual(got, sorted(names(60))[:3],
                            "generated output is ordered; the first few look "
                            "alike, so sampling the front learns nothing")

    def test_small_sets_are_fully_sampled(self):
        self.assertEqual(len(collection.sample_paths(["a.png", "b.png"])), 2)

    def test_sampling_is_deterministic(self):
        self.assertEqual(collection.sample_paths(names(40)),
                         collection.sample_paths(names(40)))


class VaryingTokens(unittest.TestCase):
    def test_reports_what_distinguishes_members(self):
        ns = ["run_north_alpha_tccon.png", "run_south_alpha_tccon.png",
              "run_north_beta_tccon.png", "run_south_beta_tccon.png"] * 6
        verdict = figures.classify_directory(ns)
        varying = collection.varying_tokens(ns, verdict.shared_tokens)
        self.assertTrue(set(varying) & {"north", "south", "alpha", "beta"},
                        "a reader needs to know what DIFFERS across the family")

    def test_shared_tokens_are_not_reported_as_varying(self):
        ns = names(40)
        verdict = figures.classify_directory(ns)
        varying = collection.varying_tokens(ns, verdict.shared_tokens)
        for token in verdict.shared_tokens:
            self.assertNotIn(token, varying)


class Rendering(unittest.TestCase):
    def _render(self, n=415, described=2):
        ns = names(n)
        verdict = figures.classify_directory(ns)
        samples = [(ns[i], f"A plot of feature {i}." if i < described else None)
                   for i in range(3)]
        return collection.render(Path("/tmp/sample_dir"), ns, verdict, samples)

    def test_states_how_many_were_actually_looked_at(self):
        text = self._render(415, described=2)
        self.assertIn("2 of 415 files were actually looked at", text)

    def test_names_the_inference_as_an_inference(self):
        """'We looked at 3 of 415' and 'we looked at 415' must never read
        alike."""
        text = self._render(415, described=2)
        self.assertIn("inference", text.lower())
        self.assertIn("not an observation", text.lower())

    def test_carries_an_escalation_contract(self):
        text = self._render()
        self.assertIn("Open an individual file if", text)

    def test_includes_the_sampled_descriptions(self):
        text = self._render(415, described=2)
        self.assertIn("A plot of feature 0.", text)

    def test_lists_members_but_caps_the_listing(self):
        text = self._render(900, described=1)
        self.assertIn("more)_", text, "a 900-file listing must be capped")

    def test_reports_the_count_and_the_shared_stem(self):
        text = self._render(415)
        self.assertIn("415 generated image files", text)
        self.assertIn("feature", text)


class DirectoryScan(unittest.TestCase):
    def test_classify_finds_a_collection_on_disk(self):
        with tempfile.TemporaryDirectory() as d:
            for name in names(40):
                (Path(d) / name).write_bytes(b"\x89PNG")
            found, verdict = collection.classify(d)
        self.assertEqual(len(found), 40)
        self.assertTrue(verdict.is_collection)

    def test_generated_sidecars_are_not_counted_as_members(self):
        with tempfile.TemporaryDirectory() as d:
            for name in names(25):
                (Path(d) / name).write_bytes(b"\x89PNG")
                (Path(d) / (name + ".placard.md")).write_text("x",
                                                              encoding="utf-8")
            (Path(d) / "x.png.placard.deadbeef.body.md").write_text(
                "x", encoding="utf-8")
            found, _ = collection.classify(d)
        self.assertEqual(len(found), 25)
        for name in found:
            self.assertFalse(name.endswith(".placard.md"))
            self.assertFalse(name.endswith(".body.md"))

    def test_a_heterogeneous_directory_is_not_a_collection(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("logo.png", "headshot.jpg", "diagram.png"):
                (Path(d) / name).write_bytes(b"\x89PNG")
            _, verdict = collection.classify(d)
        self.assertFalse(verdict.is_collection)



class FamilyOnlyIsEnforced(unittest.TestCase):
    """Owner's ruling: describe a generated plot family ONCE, never file by
    file. The per-file path must be blocked, not merely untaken -- a sweep over
    a tree would otherwise spend 415 vision calls with nobody deciding to."""

    def test_a_member_of_a_collection_is_recognised(self):
        with tempfile.TemporaryDirectory() as d:
            for name in names(40):
                (Path(d) / name).write_bytes(b"\x89PNG")
            member, verdict = collection.member_of_collection(
                Path(d) / names(40)[0])
        self.assertTrue(member)
        self.assertEqual(verdict.count, 40)

    def test_a_lone_figure_is_not_a_member(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("architecture.png", "logo.png", "headshot.jpg"):
                (Path(d) / name).write_bytes(b"\x89PNG")
            member, _ = collection.member_of_collection(
                Path(d) / "architecture.png")
        self.assertFalse(member)

    def test_a_pdf_is_never_treated_as_a_collection_member(self):
        with tempfile.TemporaryDirectory() as d:
            for name in names(40):
                (Path(d) / name).write_bytes(b"\x89PNG")
            (Path(d) / "paper.pdf").write_bytes(b"%PDF")
            member, _ = collection.member_of_collection(Path(d) / "paper.pdf")
        self.assertFalse(member, "a document is not a plot family member")

    def test_digest_refuses_a_collection_member_and_names_the_alternative(self):
        import contextlib
        import io as _io

        import placard as pl
        with tempfile.TemporaryDirectory() as d:
            for name in names(40):
                (Path(d) / name).write_bytes(b"\x89PNG")
            err = _io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = pl.cmd_digest(Path(d), Path(d) / names(40)[0],
                                   "text-v1", describe_figures=True)
        self.assertEqual(rc, 4, "it must refuse, not proceed")
        message = err.getvalue()
        self.assertIn("collection", message)
        self.assertIn("--no-figures", message,
                      "the refusal must name the escape hatch")

    def test_no_figures_is_not_blocked(self):
        """Digesting one file's TEXT costs no vision call, so it stays allowed."""
        import placard as pl
        import inspect
        src = inspect.getsource(pl.cmd_digest)
        self.assertIn("if describe_figures:", src,
                      "the block must be gated on the vision pass, not on "
                      "digesting at all")

if __name__ == "__main__":
    unittest.main()
