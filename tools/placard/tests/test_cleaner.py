"""Preservation fixtures for the cleaner.

Every expectation here is written from the ORIGINAL text, never recomputed by
running the cleaner -- an oracle derived from the thing under test cannot fail.

The defects these pin were reproduced against real corpus files before being
fixed: table rows deleted by digit-masked recurrence detection, bare numbers
destroyed as page numbers, de-hyphenation asserted but not performed, cross-page
wraps unjoinable by construction, and real compound hyphens destroyed.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import cleaner  # noqa: E402

# Hyphen and letter-split repair consult the system word list; without one the
# cleaner skips them and says so in its notes (tested in NoWordList below).
needs_words = unittest.skipUnless(
    cleaner._WORDS, "no system word list (/usr/share/dict/words); "
    "install a words package to run the dictionary-backed repairs")


class TableRowsSurvive(unittest.TestCase):
    """D3: the old detector masked ALL digits, so rows differing only in their
    numbers collapsed to one key and were deleted as recurring furniture."""

    def test_rows_differing_only_in_numbers_are_kept(self):
        pages = ["Round 1 scored 62.5\nRound 2 scored 64.1\nRound 3 scored 70.9"]
        out = cleaner.clean(pages)
        for value in ("62.5", "64.1", "70.9"):
            self.assertIn(value, out.text)

    def test_row_association_survives(self):
        """Preserving the multiset of numbers is not enough -- every value could
        shift one row up and still pass. Assert the pairing."""
        pages = ["Round 1 scored 62.5\nRound 2 scored 64.1"]
        out = cleaner.clean(pages)
        self.assertIn("Round 1 scored 62.5", out.text)
        self.assertIn("Round 2 scored 64.1", out.text)

    def test_a_genuine_repeated_data_row_is_not_furniture(self):
        """Repetition alone must not convert a data row into furniture."""
        pages = ["Sample A 1.0\nunique one", "Sample A 1.0\nunique two"]
        out = cleaner.clean(pages)
        self.assertEqual(out.text.count("Sample A 1.0"), 2)


class RealFurnitureStillGoes(unittest.TestCase):
    def test_identical_running_header_on_most_pages_is_removed(self):
        pages = [f"ACME CONFIDENTIAL\nbody {i}" for i in range(1, 7)]
        out = cleaner.clean(pages)
        self.assertNotIn("ACME CONFIDENTIAL", out.text)
        self.assertIn("body 1", out.text)

    def test_removal_is_recorded_with_its_reason(self):
        pages = [f"ACME CONFIDENTIAL\nbody {i}" for i in range(1, 7)]
        out = cleaner.clean(pages)
        self.assertTrue(out.removals, "every deletion must be auditable")
        kinds = {r.rule for r in out.removals}
        self.assertIn("recurring-line", kinds)
        self.assertTrue(any("ACME" in r.text for r in out.removals))

    def test_two_page_document_does_not_lose_lines_to_recurrence(self):
        """The old threshold was max(2, 0.4*n), so in a 2-page document any line
        on both pages died."""
        pages = ["Methods\nvalue 7", "Methods\nvalue 9"]
        out = cleaner.clean(pages)
        self.assertEqual(out.text.count("Methods"), 2)


class BareNumbersSurvive(unittest.TestCase):
    """D4: any line of 1-4 bare digits was destroyed as a page number."""

    def test_data_year_on_its_own_line_is_kept(self):
        pages = ["Launch year\n2023\nOutcome: success"]
        out = cleaner.clean(pages)
        self.assertIn("2023", out.text)

    def test_real_page_numbers_matching_the_page_index_are_removed(self):
        pages = [f"content {i}\n{i}" for i in range(1, 6)]
        out = cleaner.clean(pages)
        self.assertIn("content 3", out.text)
        kinds = {r.rule for r in out.removals}
        self.assertIn("page-number", kinds)

    def test_a_consistent_offset_is_detected(self):
        """Front matter means printed numbers often lead the index by a constant."""
        pages = [f"content\n{i + 4}" for i in range(1, 6)]
        out = cleaner.clean(pages)
        self.assertIn("page-number", {r.rule for r in out.removals})

    def test_inconsistent_numbers_are_treated_as_data(self):
        pages = ["a\n1984", "b\n42", "c\n7"]
        out = cleaner.clean(pages)
        for value in ("1984", "42", "7"):
            self.assertIn(value, out.text)
        self.assertNotIn("page-number", {r.rule for r in out.removals})


@needs_words
class Hyphens(unittest.TestCase):
    def test_soft_wrap_is_joined(self):
        pages = ["the evalu-\nation of results"]
        out = cleaner.clean(pages)
        self.assertIn("evaluation", out.text)

    def test_real_compound_keeps_its_hyphen(self):
        """D5: 'self-\\ncorrection' became 'selfcorrection' -- in a corpus about
        self-correction."""
        pages = ["we study self-\ncorrection in models"]
        out = cleaner.clean(pages)
        self.assertIn("self-correction", out.text)
        self.assertNotIn("selfcorrection", out.text)

    def test_cross_page_wrap_is_joined(self):
        """D2: de-hyphenation ran inside the per-page loop, so a wrap at a page
        boundary was unreachable by construction."""
        pages = ["ends with informa-", "tion begins here"]
        out = cleaner.clean(pages)
        self.assertIn("information", out.text)

    def test_orphan_hyphen_line_is_rejoined(self):
        """'Co\\n-\\nI' is a letter-spacing artifact; the hyphen is real."""
        pages = ["Co\n-\nI: Dr. Example"]
        out = cleaner.clean(pages)
        self.assertIn("Co-I", out.text)


@needs_words
class LetterSplitRejoin(unittest.TestCase):
    """Measured in the real corpus: pypdf emits small-caps headings and some
    proper nouns letter-split, which makes them unsearchable."""

    def test_small_caps_heading_is_rejoined(self):
        pages = ["1 I NTRODUCTION\nbody text"]
        out = cleaner.clean(pages)
        self.assertIn("INTRODUCTION", out.text)

    def test_split_proper_noun_is_rejoined(self):
        pages = ["A. Author, et al., T extureCam: Autonomous Image Analysis"]
        out = cleaner.clean(pages)
        self.assertIn("TextureCam", out.text)

    def test_plural_heading_is_rejoined_even_though_it_is_not_in_the_word_list(self):
        """The system word list has 'introduction' but not the plural 'results',
        so a dictionary-only rule left 'R ESULTS' split on the real corpus."""
        pages = ["3.2 R ESULTS\nthe numbers follow"]
        out = cleaner.clean(pages)
        self.assertIn("RESULTS", out.text)

    def test_all_caps_after_I_stays_split_without_dictionary_support(self):
        pages = ["I AGREE to the terms"]
        out = cleaner.clean(pages)
        self.assertIn("I AGREE", out.text)

    def test_the_pronoun_I_is_not_glued_to_the_next_word(self):
        pages = ["I believe the result holds"]
        out = cleaner.clean(pages)
        self.assertIn("I believe", out.text)

    def test_initials_are_not_glued(self):
        pages = ["The lead, A. Author, approved it"]
        out = cleaner.clean(pages)
        self.assertIn("A. Author", out.text)


class NotesAreMeasurements(unittest.TestCase):
    """D1: trim_notes asserted de-hyphenation unconditionally. Reproduced: six
    orphan hyphens in, six out, claim still emitted."""

    def test_no_claim_when_nothing_was_removed(self):
        out = cleaner.clean(["nothing to clean here"])
        self.assertEqual(out.removals, [])
        self.assertNotIn("de-hyphenated", " ".join(out.notes).lower())

    def test_notes_count_occurrences_not_distinct_keys(self):
        pages = [f"ACME CONFIDENTIAL\nbody {i}" for i in range(1, 7)]
        out = cleaner.clean(pages)
        joined = " ".join(out.notes)
        self.assertIn("6 occurrence", joined,
                      "the old note counted distinct normalized keys, not "
                      "occurrences, so it under-reported deletions")

    def test_dehyphenation_note_only_appears_when_a_join_happened(self):
        out = cleaner.clean(["the evalu-\nation of results"])
        self.assertIn("de-hyphenated", " ".join(out.notes).lower())

    def test_page_anchors_are_preserved(self):
        out = cleaner.clean(["first", "second"])
        self.assertIn("[p.1]", out.text)
        self.assertIn("[p.2]", out.text)


class IdempotenceAndSafety(unittest.TestCase):
    def test_second_pass_removes_nothing_further(self):
        pages = ["Round 1 scored 62.5\nRound 2 scored 64.1", "more prose here"]
        once = cleaner.clean(pages)
        twice = cleaner.clean([once.text])
        self.assertEqual(twice.removals, [],
                         "a second pass must not keep eating the document")

    def test_empty_input_is_safe(self):
        out = cleaner.clean([])
        self.assertEqual(out.text, "")
        self.assertEqual(out.removals, [])



class NoWordList(unittest.TestCase):
    """Without a dictionary the repairs must be skipped AND reported, never
    guessed: a container image has no /usr/share/dict/words."""

    def test_repairs_are_skipped_and_the_note_says_so(self):
        from unittest import mock
        with mock.patch.object(cleaner, "_WORDS", set()):
            out = cleaner.clean(["we study self-\ncorrection here", "1 I NTRODUCTION"])
        self.assertIn("I NTRODUCTION", out.text, "no join without the oracle")
        self.assertTrue(any("no system word list" in n for n in out.notes))


if __name__ == "__main__":
    unittest.main()
