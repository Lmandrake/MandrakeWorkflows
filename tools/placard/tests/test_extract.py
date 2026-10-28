from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import extract  # noqa: E402

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "quarterly-review"


class LazyImport(unittest.TestCase):
    def test_module_imports_without_docling(self):
        """placard.py must keep running under the system python the hook falls
        back to, which has no docling. Importing this module must not require
        it."""
        self.assertTrue(hasattr(extract, "extract"))
        self.assertTrue(hasattr(extract, "profile_id"))

    def test_availability_is_reported_not_raised(self):
        self.assertIn(extract.docling_available(), (True, False))


class ProfileIdentity(unittest.TestCase):
    def test_profile_id_names_versions_and_options(self):
        pid = extract.profile_id(versions={"docling": "2.115.0"},
                                 option_profile="text-v1", soffice=True)
        self.assertIn("docling-2.115.0", pid)
        self.assertIn("text-v1", pid)
        self.assertIn("soffice-present", pid)

    def test_soffice_absence_changes_the_profile(self):
        """LibreOffice presence changes what gets extracted (EMF/WMF figures),
        so it must change the profile identity -- otherwise two different
        extractions share an id."""
        a = extract.profile_id(versions={"docling": "2.115.0"},
                              option_profile="text-v1", soffice=True)
        b = extract.profile_id(versions={"docling": "2.115.0"},
                              option_profile="text-v1", soffice=False)
        self.assertNotEqual(a, b)

    def test_option_profile_changes_the_profile(self):
        a = extract.profile_id(versions={"docling": "2.115.0"},
                              option_profile="text-v1", soffice=True)
        b = extract.profile_id(versions={"docling": "2.115.0"},
                              option_profile="ocr-v1", soffice=True)
        self.assertNotEqual(a, b)


class MarginUnion(unittest.TestCase):
    """Measured: Docling drops margin and footnote identifiers that the raw
    text layer retains -- arXiv:2310.01798, NTR #1, NTR #2, IJCAI,
    LPSC. The union pass recovers exactly those."""

    def test_recovers_identifiers_absent_from_the_structured_body(self):
        body = "Technical Highlights. Change detection is robust."
        raw = ("Technical Highlights.\n2. NTR #1\n"
               "3. A. Author, et al. 43rd LPSC. 2012.\n"
               "B. Writer et al. IJCAI. 2016.")
        found = extract.margin_identifiers(body, raw)
        joined = " ".join(found)
        self.assertIn("NTR #1", joined)
        self.assertIn("LPSC", joined)
        self.assertIn("IJCAI", joined)

    def test_does_not_duplicate_identifiers_already_present(self):
        body = "see NTR #1 for details"
        raw = "see NTR #1 for details"
        self.assertEqual(extract.margin_identifiers(body, raw), [])

    def test_arxiv_stamp_is_recovered(self):
        found = extract.margin_identifiers("A paper about self-correction.",
                                           "arXiv:2310.01798v2 [cs.CL]")
        self.assertTrue(any("2310.01798" in f for f in found))

    def test_returns_nothing_when_raw_adds_nothing(self):
        self.assertEqual(extract.margin_identifiers("prose", "prose"), [])

    def test_ignores_bare_prose_differences(self):
        """Only identifier-shaped tokens are recovered. The union pass is not a
        licence to re-add arbitrary text Docling deliberately dropped."""
        found = extract.margin_identifiers("the body", "the body and some "
                                           "running header prose")
        self.assertEqual(found, [])


class TypedUnits(unittest.TestCase):
    """Spec 3.4: pages_total is not a universal denominator."""

    def test_pdf_unit_is_a_page(self):
        self.assertEqual(extract.units_kind_for("a.pdf"), "page")

    def test_deck_unit_is_a_slide(self):
        self.assertEqual(extract.units_kind_for("deck.pptx"), "slide")

    def test_spreadsheet_unit_is_a_worksheet(self):
        self.assertEqual(extract.units_kind_for("book.xlsx"), "worksheet")

    def test_csv_unit_is_a_record(self):
        """A line count is not a record count: RFC 4180 permits newlines inside
        quoted fields."""
        self.assertEqual(extract.units_kind_for("rows.csv"), "record")

    def test_image_unit_is_an_asset(self):
        self.assertEqual(extract.units_kind_for("figure.png"), "asset")

    def test_unknown_extension_gets_a_neutral_unit_not_page(self):
        self.assertEqual(extract.units_kind_for("thing.weird"), "unit")


class _FakeProv:
    def __init__(self, page_no):
        self.page_no = page_no


class _FakeTableItem:
    """Duck-types the one shape `_pages_from` must handle: no `.text`
    attribute, content only reachable via `export_to_markdown()`."""

    def __init__(self, page_no, markdown):
        self.prov = [_FakeProv(page_no)]
        self._markdown = markdown

    def export_to_markdown(self, doc):
        return self._markdown


class _FakeTextItem:
    def __init__(self, page_no, text):
        self.prov = [_FakeProv(page_no)]
        self.text = text


class _FakeDoc:
    def __init__(self, items):
        self._items = items

    def iterate_items(self):
        for item in self._items:
            yield item, 0


class TablesContributeToPageText(unittest.TestCase):
    """A table item has no `.text`, so a page whose entire content is one
    table (every worksheet of a spreadsheet) used to leave that page's
    bucket empty -- `pages=[]` with `tables_detected` nonzero. 16
    real xlsx digests had an empty `## Full text` section this
    way."""

    def test_table_only_page_is_not_dropped(self):
        doc = _FakeDoc([_FakeTableItem(1, "| a | b |\n|---|---|\n| 1 | 2 |")])
        pages = extract._pages_from(doc)
        self.assertEqual(len(pages), 1)
        self.assertIn("| a | b |", pages[0])

    def test_table_and_text_items_share_a_page_in_order(self):
        doc = _FakeDoc([
            _FakeTextItem(1, "Sheet1"),
            _FakeTableItem(1, "| a |\n|---|\n| 1 |"),
            _FakeTableItem(2, "| b |\n|---|\n| 2 |"),
        ])
        pages = extract._pages_from(doc)
        self.assertEqual(len(pages), 2)
        self.assertIn("Sheet1", pages[0])
        self.assertIn("| a |", pages[0])
        self.assertIn("| b |", pages[1])

    def test_a_table_whose_markdown_export_raises_is_skipped_not_fatal(self):
        class _Broken(_FakeTableItem):
            def export_to_markdown(self, doc):
                raise RuntimeError("simulated export failure")

        doc = _FakeDoc([_FakeTextItem(1, "still here"), _Broken(1, "")])
        stats = {}
        pages = extract._pages_from(doc, stats)
        self.assertEqual(pages, ["still here"])
        self.assertEqual(stats.get("export_failed"), 1,
                         "a failed export must be counted, not reported as exported")

    def test_item_with_neither_text_nor_markdown_export_is_skipped(self):
        doc = _FakeDoc([_FakeTextItem(1, "   "), object()])
        pages = extract._pages_from(doc)
        self.assertEqual(pages, [])


class RawLayerFailureIsVisible(unittest.TestCase):
    """An earlier version swallowed a missing pypdf and returned "", which made
    the whole margin-union pass inert while still reporting success. The reason
    must travel with the result."""

    def test_missing_pypdf_returns_a_reason_not_silence(self):
        import builtins
        real_import = builtins.__import__

        def no_pypdf(name, *a, **k):
            if name == "pypdf":
                raise ImportError("simulated: pypdf absent")
            return real_import(name, *a, **k)

        builtins.__import__ = no_pypdf
        try:
            raw, reason = extract._raw_text_layer("/nonexistent.pdf")
        finally:
            builtins.__import__ = real_import
        self.assertEqual(raw, "")
        self.assertIsNotNone(reason, "a silent inert feature is the defect")
        self.assertIn("pypdf", reason)
        self.assertIn("uv pip install", reason,
                      "the error must name the remedy")

    def test_unreadable_file_returns_a_reason(self):
        raw, reason = extract._raw_text_layer("/definitely/not/a/pdf")
        self.assertEqual(raw, "")
        self.assertIsNotNone(reason)


@unittest.skipUnless(extract.docling_available(),
                     "docling not importable in this interpreter")
class ExampleExtraction(unittest.TestCase):
    """Against the synthetic example that ships in examples/: real files, real
    Docling, no private fixtures."""

    def test_report_table_lands_in_the_body(self):
        result = extract.extract(EXAMPLE / "field-trial-report.pdf")
        self.assertEqual(result.units_total, 5)
        self.assertGreater(result.tables_detected, 0)
        self.assertIn("15,380", "\n".join(result.pages))

    def test_deck_body_carries_speaker_notes_and_no_image_bytes(self):
        result = extract.extract(EXAMPLE / "review-deck.pptx")
        body = "\n".join(result.pages)
        self.assertIn("Tallis Supply", body, "a fact that lives only in the notes")
        self.assertNotIn("base64", body)
        self.assertEqual(result.units_kind, "slide")

    def test_spreadsheet_body_is_not_empty(self):
        result = extract.extract(EXAMPLE / "sensor-log.xlsx")
        self.assertEqual(result.tables_detected, 2)
        self.assertIn("61400", "\n".join(result.pages))


class SpeakerNotes(unittest.TestCase):
    """Stdlib only, so it runs without Docling."""

    def test_notes_are_read_in_slide_order(self):
        notes = extract.pptx_speaker_notes(EXAMPLE / "review-deck.pptx")
        self.assertEqual(sorted(notes), list(range(1, 8)))
        self.assertIn("Tallis Supply", notes[4])
        self.assertIn("2028", notes[6])

    def test_data_uri_images_become_markers(self):
        md = "Results\n![Image](data:image/png;base64,AAAA)\n![chart](data:image/png;base64,BB)"
        out = extract._DATA_URI_IMAGE.sub(extract._image_placeholder, md)
        self.assertEqual(out, "Results\n[picture]\n[picture: chart]")


if __name__ == "__main__":
    unittest.main()
