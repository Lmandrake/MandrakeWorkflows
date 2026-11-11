"""Regression: .ipynb is read with json (Docling refuses it), and a standalone
image is described from its own bytes (Docling's picture items carry none)."""
from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import extract  # noqa: E402

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg==")


def write_nb(d: Path) -> Path:
    nb = {"nbformat": 4, "metadata": {"language_info": {"name": "python"}},
          "cells": [
              {"cell_type": "markdown", "source": ["# Title\n", "prose"]},
              {"cell_type": "code", "source": "print('hi')", "outputs": [
                  {"output_type": "stream", "name": "stdout", "text": ["hi\n"]},
                  {"output_type": "display_data", "data": {
                      "text/plain": "<Figure>",
                      "image/png": base64.b64encode(PNG).decode()}}]}]}
    p = d / "nb.ipynb"
    p.write_text(json.dumps(nb))
    return p


class Notebook(unittest.TestCase):
    def test_extracted_without_docling(self):
        with tempfile.TemporaryDirectory() as t:
            p = write_nb(Path(t))
            with mock.patch.object(extract, "docling_available",
                                   return_value=False):
                r = extract.extract(p)
        text = "\n".join(r.pages)
        self.assertIn("# Title", text)
        self.assertIn("print('hi')", text)
        self.assertIn("```output\nhi\n```", text)
        self.assertEqual((r.units_kind, r.units_total), ("cell", 2))
        self.assertEqual(r.figures_detected, 1)
        self.assertEqual(r.figures, [])

    def test_png_output_becomes_figure_with_bytes(self):
        with tempfile.TemporaryDirectory() as t:
            r = extract.extract(write_nb(Path(t)), want_figures=True)
        self.assertEqual(len(r.figures), 1)
        self.assertEqual(r.figures[0][0], 2)
        self.assertEqual(r.figures[0][1], PNG)


class StandalonePng(unittest.TestCase):
    def test_own_bytes_replace_docling_picture_without_crop(self):
        class Pic:
            prov = []
            annotations = []

            def get_image(self, doc):
                return None          # what Docling does for a bare image

        class Doc:
            pictures = [Pic()]
            tables = []
            pages = {1: object()}

            def iterate_items(self):
                return iter([])

        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "chart.png"
            p.write_bytes(PNG)
            with mock.patch.object(extract, "docling_available",
                                   return_value=True), \
                 mock.patch.object(extract, "_convert", return_value=Doc()):
                r = extract.extract(p, want_figures=True)
        self.assertEqual(r.figures_detected, 1)
        self.assertEqual(len(r.figures), 1)
        self.assertEqual(r.figures[0][1], PNG)


class MediaType(unittest.TestCase):
    def test_sniffed_from_bytes(self):
        import placard
        self.assertEqual(placard._sniff_media_type(PNG), "image/png")
        self.assertEqual(placard._sniff_media_type(b"\xff\xd8\xff\xe0x"),
                         "image/jpeg")


if __name__ == "__main__":
    unittest.main()
