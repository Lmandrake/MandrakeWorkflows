"""Figure handling: observations, occurrences, gating, and collections.

The fixtures here come from the external review's counterexample list plus the
typical shape of a corpus dominated by matplotlib output under one tree.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import figures  # noqa: E402


class Gating(unittest.TestCase):
    def test_logo_is_skipped_with_a_reason(self):
        d = figures.decide(docling_class="logo", area_frac=0.02, caption=None)
        self.assertEqual(d.depth, "skip")
        self.assertIn("logo", d.reason.lower())

    def test_icon_is_skipped(self):
        self.assertEqual(
            figures.decide(docling_class="icon", area_frac=0.01,
                           caption=None).depth, "skip")

    def test_flow_chart_gets_a_full_description(self):
        d = figures.decide(docling_class="flow_chart", area_frac=0.4, caption=None)
        self.assertEqual(d.depth, "full")

    def test_line_chart_gets_a_full_description(self):
        self.assertEqual(
            figures.decide(docling_class="line_chart", area_frac=0.3,
                           caption=None).depth, "full")

    def test_photograph_gets_a_brief_description(self):
        d = figures.decide(docling_class="photograph", area_frac=0.3, caption=None)
        self.assertEqual(d.depth, "brief")

    def test_an_informative_caption_downgrades_a_photograph_to_caption_only(self):
        """Caption-first: the document's own caption is free and authoritative."""
        d = figures.decide(docling_class="photograph", area_frac=0.3,
                           caption="Figure 2: HiRISE image ESP_011426_1380 of "
                                   "recurring slope lineae in Garni crater.")
        self.assertEqual(d.depth, "caption-only")

    def test_an_uninformative_caption_does_not_downgrade(self):
        d = figures.decide(docling_class="photograph", area_frac=0.3,
                           caption="Figure 2.")
        self.assertNotEqual(d.depth, "caption-only")

    def test_a_caption_never_downgrades_a_chart(self):
        """A caption saying 'Performance across datasets' does not close the
        visual gap -- the information is in the axes and the curves."""
        d = figures.decide(docling_class="line_chart", area_frac=0.3,
                           caption="Figure 4: Performance across datasets over "
                                   "two rounds of self-correction.")
        self.assertEqual(d.depth, "full")

    def test_unknown_class_is_not_silently_skipped(self):
        d = figures.decide(docling_class=None, area_frac=0.3, caption=None)
        self.assertNotEqual(d.depth, "skip")
        self.assertIn("unclassified", d.reason.lower())

    def test_a_tiny_unclassified_image_is_skipped_but_counted(self):
        d = figures.decide(docling_class=None, area_frac=0.0005, caption=None)
        self.assertEqual(d.depth, "skip")
        self.assertTrue(d.reason, "every skip carries its reason")


class MeasuredVocabulary(unittest.TestCase):
    """Pinned against docling 2.115.0 on a real deck. The first version of the
    gate compared Title Case names against these snake_case ones, so every
    comparison missed and the gate was inert -- while its tests passed, because
    the fixtures used the same wrong vocabulary the code did."""

    REAL = ("photograph", "flow_chart", "logo", "icon", "full_page_image",
            "screenshot_from_computer", "line_chart", "engineering_drawing",
            "other")

    def test_every_measured_class_routes_somewhere_deliberate(self):
        for name in self.REAL:
            d = figures.decide(docling_class=name, area_frac=0.3, caption=None)
            self.assertIn(d.depth, ("skip", "brief", "full", "caption-only"),
                          f"{name} must route deliberately")
            self.assertTrue(d.reason)

    def test_the_measured_furniture_classes_are_skipped(self):
        for name in ("logo", "icon", "full_page_image"):
            self.assertEqual(
                figures.decide(docling_class=name, area_frac=0.3,
                               caption=None).depth, "skip",
                f"{name} is furniture and must not cost a call")

    def test_the_measured_structural_classes_get_full(self):
        for name in ("flow_chart", "line_chart", "engineering_drawing",
                     "screenshot_from_computer"):
            self.assertEqual(
                figures.decide(docling_class=name, area_frac=0.3,
                               caption=None).depth, "full", name)

    def test_title_case_is_normalized_so_either_form_works(self):
        for a, b in (("Logo", "logo"), ("Flow chart", "flow_chart"),
                     ("Full page image", "full_page_image")):
            self.assertEqual(figures.normalize_class(a), b)
            self.assertEqual(
                figures.decide(docling_class=a, area_frac=0.3, caption=None).depth,
                figures.decide(docling_class=b, area_frac=0.3, caption=None).depth)

    def test_an_unrecognised_class_is_not_silently_skipped(self):
        d = figures.decide(docling_class="some_new_docling_class",
                           area_frac=0.3, caption=None)
        self.assertNotEqual(d.depth, "skip")


class ObservationsVersusOccurrences(unittest.TestCase):
    """The review's sharpest figure point: hash-dedup may reuse the pixel
    OBSERVATION but must never collapse two occurrences, because the same
    bitmap can appear as 'input' and as 'reconstruction'."""

    def test_identical_bitmaps_share_one_observation(self):
        inv = figures.Inventory()
        a = inv.add(page=1, image_bytes=b"PIXELS", caption="Figure 1: input")
        b = inv.add(page=4, image_bytes=b"PIXELS", caption="Figure 7: reconstruction")
        self.assertEqual(a.observation_key, b.observation_key)
        self.assertEqual(len(inv.observations), 1)

    def test_identical_bitmaps_keep_separate_occurrences(self):
        inv = figures.Inventory()
        inv.add(page=1, image_bytes=b"PIXELS", caption="Figure 1: input")
        inv.add(page=4, image_bytes=b"PIXELS", caption="Figure 7: reconstruction")
        self.assertEqual(len(inv.occurrences), 2)
        captions = {o.caption for o in inv.occurrences}
        self.assertIn("Figure 1: input", captions)
        self.assertIn("Figure 7: reconstruction", captions)

    def test_a_repeated_letterhead_is_described_once(self):
        inv = figures.Inventory()
        for page in range(1, 13):
            inv.add(page=page, image_bytes=b"LETTERHEAD", caption=None)
        self.assertEqual(len(inv.observations), 1,
                         "one description for twelve appearances")
        self.assertEqual(len(inv.occurrences), 12)

    def test_different_bitmaps_are_different_observations(self):
        inv = figures.Inventory()
        inv.add(page=1, image_bytes=b"ONE", caption=None)
        inv.add(page=2, image_bytes=b"TWO", caption=None)
        self.assertEqual(len(inv.observations), 2)

    def test_no_perceptual_dedup(self):
        """Near-identical charts differing in one curve must NOT collapse."""
        inv = figures.Inventory()
        inv.add(page=1, image_bytes=b"CHART-A" + b"\x00" * 100, caption=None)
        inv.add(page=2, image_bytes=b"CHART-B" + b"\x00" * 100, caption=None)
        self.assertEqual(len(inv.observations), 2)


class Accounting(unittest.TestCase):
    """Never render an unknown total as zero, and never let 0/0 read as
    complete coverage."""

    def test_counts_report_skips_with_reasons(self):
        inv = figures.Inventory()
        inv.add(page=1, image_bytes=b"L", caption=None, docling_class="logo")
        inv.add(page=2, image_bytes=b"C", caption=None, docling_class="flow_chart")
        counts = inv.accounting()
        self.assertEqual(counts["figures_detected"], 2)
        self.assertEqual(counts["descriptions_skipped"], 1)
        self.assertIn("logo", str(counts["skip_reasons"]))

    def test_unknown_detection_is_marked_not_zeroed(self):
        counts = figures.accounting_unknown("picture detection unavailable")
        self.assertEqual(counts["figures_detected_known"], "false")
        self.assertIn("unavailable", counts["figures_detection_note"])

    def test_zero_detected_is_distinguishable_from_unknown(self):
        inv = figures.Inventory()
        counts = inv.accounting()
        self.assertEqual(counts["figures_detected"], 0)
        self.assertEqual(counts["figures_detected_known"], "true")


class CollectionDetection(unittest.TestCase):
    """Hundreds of near-identical plots in one run-output directory. A
    directory of homogeneous generated output needs ONE digest, not one per file."""

    def test_many_similar_names_is_a_collection(self):
        names = [f"ab_north_xy_feature_{i:03d}.png" for i in range(60)]
        verdict = figures.classify_directory(names)
        self.assertTrue(verdict.is_collection)
        self.assertGreaterEqual(verdict.count, 60)

    def test_a_handful_of_distinct_images_is_not_a_collection(self):
        names = ["logo.png", "headshot.jpg", "architecture_diagram.png"]
        self.assertFalse(figures.classify_directory(names).is_collection)

    def test_the_shared_stem_is_reported_so_the_digest_can_name_the_family(self):
        names = [f"dominant_feature_graph_{i}.png" for i in range(40)]
        verdict = figures.classify_directory(names)
        self.assertTrue(verdict.is_collection)
        self.assertIn("dominant_feature_graph", verdict.shared_stem)

    def test_mixed_directory_below_threshold_is_not_a_collection(self):
        names = [f"plot_{i}.png" for i in range(5)] + ["readme_figure.png"]
        self.assertFalse(figures.classify_directory(names).is_collection)

    def test_empty_directory_is_not_a_collection(self):
        self.assertFalse(figures.classify_directory([]).is_collection)


if __name__ == "__main__":
    unittest.main()
