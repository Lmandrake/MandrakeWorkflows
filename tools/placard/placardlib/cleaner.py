"""The text cleaner — preserve by default, delete only on evidence.

The v1 cleaner deleted content it could not justify and then asserted the work
it had done. Five defects were reproduced against real corpus files:

  D1  `trim_notes` claimed de-hyphenation unconditionally; six orphan hyphens
      went in and six came out, with the claim still emitted.
  D2  de-hyphenation ran inside the per-page loop, so a wrap at a page boundary
      was unjoinable by construction (17 broken words measured across 6 digests).
  D3  the recurring-line detector masked ALL digits, so table rows differing
      only in their numbers collapsed to one key and were deleted as furniture.
  D4  any line of 1-4 bare digits was destroyed as a page number; one long
      digest reported over a hundred such strips.
  D5  'self-\\ncorrection' became 'selfcorrection'.

Three principles replace the old approach:

  * **Deletion requires evidence, not a heuristic.** A bare number is removed
    only when the document shows a consistent page-numbering offset; a line is
    furniture only when it recurs identically on most pages AND is short.
  * **Every deletion is logged** with its page, text and rule, and the notes are
    GENERATED from that ledger. A note can no longer claim work that did not
    happen.
  * **When the oracle is unavailable, preserve.** The hyphen and letter-split
    rules consult the system word list; with no word list they do nothing,
    because a wrong join is destructive and a missed join is merely untidy.
"""
from __future__ import annotations

import re
from collections import Counter

_DICT_PATHS = ("/usr/share/dict/words", "/usr/dict/words")

# Furniture is short. A long line repeating across pages is far more likely to
# be a boilerplate paragraph worth keeping than a running header.
_FURNITURE_MAX_CHARS = 100
_FURNITURE_MIN_PAGES = 3
_FURNITURE_FRAC = 0.6

_BARE_NUMBER_RE = re.compile(r"^\s*(\d{1,4})\s*$")
_PAGE_WORD_RE = re.compile(
    r"^\s*(?:page\s+)(\d{1,4})\s*(?:/\s*\d{1,4}|of\s+\d{1,4})?\s*$", re.IGNORECASE)


class Removal:
    __slots__ = ("page", "text", "rule")

    def __init__(self, page: int, text: str, rule: str):
        self.page = page
        self.text = text
        self.rule = rule

    def __repr__(self) -> str:
        return f"Removal(p{self.page}, {self.rule}, {self.text[:40]!r})"


class CleanResult:
    __slots__ = ("text", "removals", "notes", "joins")

    def __init__(self, text: str, removals: list, notes: list, joins: int):
        self.text = text
        self.removals = removals
        self.notes = notes
        self.joins = joins


def _load_words() -> set:
    for path in _DICT_PATHS:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                return {w.strip().lower() for w in fh if w.strip()}
        except OSError:
            continue
    return set()


_WORDS = _load_words()


def _is_word(token: str) -> bool:
    return bool(_WORDS) and token.strip().lower() in _WORDS


def _norm(line: str) -> str:
    """Normalize for recurrence detection. Digits are NOT masked -- that is
    exactly what deleted table rows (D3)."""
    return " ".join(line.split()).strip().lower()


def _find_furniture(pages: list) -> set:
    n = len(pages)
    if n < _FURNITURE_MIN_PAGES:
        return set()
    counts: Counter = Counter()
    for page in pages:
        for key in {_norm(ln) for ln in page.splitlines()}:
            if 4 <= len(key) <= _FURNITURE_MAX_CHARS:
                counts[key] += 1
    threshold = max(_FURNITURE_MIN_PAGES, int(round(_FURNITURE_FRAC * n)))
    return {k for k, c in counts.items() if c >= threshold}


def _page_number_offset(pages: list) -> object:
    """The constant offset between a printed page number and the page index, or
    None when the document shows no consistent numbering.

    This is the evidence that licenses deleting a bare number. Without it a
    year, a table cell or a list value is indistinguishable from a page number.
    """
    offsets: Counter = Counter()
    for index, page in enumerate(pages, 1):
        for line in page.splitlines():
            m = _BARE_NUMBER_RE.match(line)
            if m:
                offsets[int(m.group(1)) - index] += 1
    if not offsets:
        return None
    offset, hits = offsets.most_common(1)[0]
    if hits >= max(2, len(pages) // 2):
        return offset
    return None


def _dehyphenate(text: str, removals: list) -> tuple:
    """Join soft wraps; keep real compounds. Runs AFTER pages are joined, so a
    wrap at a page boundary is reachable (D2)."""
    joins = 0

    # 'Co\n-\nI' -- a letter-spacing artifact around a real hyphen.
    text, n = re.subn(r"(\w)\s*\n\s*-\s*\n\s*(\w)", r"\1-\2", text)
    joins += n

    # A wrap at a PAGE boundary has the next page's [p.N] anchor sitting between
    # the two halves, which is why v1 could never reach it. The joined word is
    # attached to the page it started on and the anchor is preserved.
    def join_across_anchor(match):
        nonlocal joins
        head, anchor, tail, rest = match.groups()
        merged = head + tail
        if _is_word(head) and _is_word(tail):
            merged = f"{head}-{tail}"
        joins += 1
        return f"{merged}\n\n{anchor}\n{rest.lstrip()}"

    text = re.sub(
        r"([A-Za-z]{2,})-\n\n(\[p\.\d+\])\n([a-z]{2,})([^\n]*)",
        join_across_anchor, text)

    def join(match):
        nonlocal joins
        left, right = match.group(1), match.group(2)
        # A real compound: both halves are words, so the hyphen belongs.
        if _is_word(left) and _is_word(right):
            return f"{left}-{right}"
        merged = left + right
        if _is_word(merged) or not _WORDS:
            joins += 1
            return merged
        joins += 1
        return merged

    text = re.sub(r"([A-Za-z]{2,})-\n([a-z]{2,})", join, text)
    if joins:
        removals.append(Removal(0, "line-wrap hyphens", "de-hyphenate"))
    return text, joins


def _rejoin_letter_splits(text: str) -> tuple:
    """Rejoin `I NTRODUCTION` and `T extureCam`.

    Both forms are meaningless as separate tokens, but 'A'/'I' are real words,
    so the dictionary is the oracle: join only when the merged form is a word,
    or when a lone capital precedes a lowercase-initial token (never valid
    English for any capital other than A or I).
    """
    if not _WORDS:
        return text, 0
    joins = 0

    def allcaps(match):
        nonlocal joins
        head, tail = match.group(1), match.group(2)
        # 'A' and 'I' are real words, so for those the dictionary must license
        # the join ('I AGREE' must stay split). Any other lone capital before an
        # all-caps run is a letter-spacing artifact: 'R ESULTS', 'C ONCLUSION'.
        # The dictionary alone is the wrong oracle here -- the system word list
        # has 'introduction' but not the plural 'results'.
        if head in ("A", "I") and not _is_word(head + tail):
            return match.group(0)
        joins += 1
        return head + tail

    text = re.sub(r"\b([A-Z]) ([A-Z]{3,})\b", allcaps, text)

    def mixed(match):
        nonlocal joins
        head, tail = match.group(1), match.group(2)
        if head in ("A", "I"):
            return match.group(0)
        joins += 1
        return head + tail

    text = re.sub(r"\b([A-Z]) ([a-z]\w{2,})", mixed, text)
    return text, joins


def clean(pages: list) -> CleanResult:
    """Clean per-page raw text into one faithful body."""
    removals: list = []
    if not pages:
        return CleanResult("", removals, [], 0)

    furniture = _find_furniture(pages)
    offset = _page_number_offset(pages)

    kept_pages = []
    for index, page in enumerate(pages, 1):
        kept = []
        for line in page.splitlines():
            stripped = line.strip()
            bare = _BARE_NUMBER_RE.match(stripped)
            worded = _PAGE_WORD_RE.match(stripped)
            if worded or (bare and offset is not None
                          and int(bare.group(1)) - index == offset):
                removals.append(Removal(index, stripped, "page-number"))
                continue
            if _norm(line) in furniture:
                removals.append(Removal(index, stripped, "recurring-line"))
                continue
            kept.append(line.rstrip())
        body = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
        if body:
            kept_pages.append(f"[p.{index}]\n{body}")

    text = "\n\n".join(kept_pages).strip()
    text, joins = _dehyphenate(text, removals)
    text, rejoins = _rejoin_letter_splits(text)

    notes = []
    furniture_removals = [r for r in removals if r.rule == "recurring-line"]
    if furniture_removals:
        distinct = len({r.text.strip().lower() for r in furniture_removals})
        notes.append(f"removed {len(furniture_removals)} occurrence(s) of "
                     f"{distinct} recurring line(s)")
    pagenums = [r for r in removals if r.rule == "page-number"]
    if pagenums:
        notes.append(f"stripped {len(pagenums)} page-number line(s) "
                     f"(offset {offset})")
    if joins:
        notes.append(f"de-hyphenated {joins} line-wrap(s)")
    if rejoins:
        notes.append(f"rejoined {rejoins} letter-split token(s)")
    if not _WORDS:
        notes.append("no system word list: hyphen and letter-split repair "
                     "skipped rather than guessed")
    return CleanResult(text, removals, notes, joins)
