from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import frontmatter as fmlib  # noqa: E402

HOSTILE = {
    "source": "deck.pdf",
    "trim_notes": "removed 2 lines\nkept the rest",      # newline
    "dir_summary": "--- not a delimiter ---",            # looks like a fence
    "note": "key: value: value",                          # colons
    "unicode": "naïve — ‘quoted’ 日本語",
    "spaced": "  leading and trailing  ",
    "empty": "",
    "quotelike": '"already quoted"',
}


class RoundTrip(unittest.TestCase):
    def test_hostile_values_round_trip(self):
        text = fmlib.dump(HOSTILE)
        again = fmlib.parse(text)
        self.assertEqual(again, HOSTILE)

    def test_dump_output_is_parseable_twice(self):
        once = fmlib.dump(HOSTILE)
        twice = fmlib.dump(fmlib.parse(once))
        self.assertEqual(fmlib.parse(twice), HOSTILE)

    def test_split_returns_body_untouched(self):
        body = "\n# Title\n\n## Full text\nline one\n--- not a fence\n"
        text = fmlib.dump({"source": "a.pdf"}) + body
        fm, rest = fmlib.split(text)
        self.assertEqual(fm["source"], "a.pdf")
        self.assertEqual(rest, body)

    def test_reads_legacy_v1_plain_frontmatter(self):
        legacy = ("---\nsource: a.pdf\ntier: standard\nbody: full\n---\n\n"
                  "## What this is\nx\n")
        fm, rest = fmlib.split(legacy)
        self.assertEqual(fm["tier"], "standard")
        self.assertTrue(rest.startswith("\n## What this is"))

    def test_no_frontmatter_returns_empty_and_whole_text(self):
        fm, rest = fmlib.split("# Just markdown\n")
        self.assertEqual(fm, {})
        self.assertEqual(rest, "# Just markdown\n")


if __name__ == "__main__":
    unittest.main()
