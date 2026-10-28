"""Digest schema, v1-tolerant.

The two derivation records are the point of v2. A body refresh records what was
EXTRACTED; the summary record states what the author actually READ. Appending a
full extraction to an abstract-basis summary is a legitimate state -- what is
illegitimate is reporting that the summary now covers the whole document.
"""
from __future__ import annotations

from . import frontmatter

BODY_FIELDS = (
    "extractor", "extractor_version", "profile_id", "extracted_at",
    "source_sha256", "body_sha256", "body_layout", "body_path", "body_bytes",
)
SUMMARY_FIELDS = (
    "summary_basis", "summary_basis_sha", "authoring_status", "authored_at",
)
FULL_TEXT_HEADING = "## Full text"


def _opt(fm: dict, key: str):
    value = fm.get(key)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


class DigestView:
    __slots__ = (
        "schema_version", "fm", "markdown", "body_layout", "body_path",
        "body_sha256", "source_sha256", "profile_id", "summary_basis",
        "summary_basis_sha", "authoring_status",
    )

    def __init__(self, fm: dict, markdown: str):
        self.fm = fm
        self.markdown = markdown
        try:
            self.schema_version = int(str(fm.get("placard_version", "1")).strip() or "1")
        except ValueError:
            self.schema_version = 1
        self.source_sha256 = _opt(fm, "source_sha256")
        self.body_sha256 = _opt(fm, "body_sha256")
        self.profile_id = _opt(fm, "profile_id")
        self.body_path = _opt(fm, "body_path")
        layout = _opt(fm, "body_layout")
        # v1 had no body_layout and always inlined the body.
        self.body_layout = layout or ("external" if self.body_path else "inline")
        self.summary_basis = _opt(fm, "summary_basis")
        self.summary_basis_sha = _opt(fm, "summary_basis_sha")
        # v1 recorded nothing about the summary's basis. 'unknown' must stay
        # distinguishable from 'current'; conflating them is the whole defect.
        self.authoring_status = _opt(fm, "authoring_status") or "unknown"

    @property
    def is_legacy(self) -> bool:
        return self.schema_version < 2


def load_digest(text: str) -> DigestView:
    fm, markdown = frontmatter.split(text)
    return DigestView(fm, markdown)


def inline_body(markdown: str) -> str:
    """The text under '## Full text' to the end of the digest, or '' when there
    is no such section.

    `## Full text` is always the last section (publish writes it last, and
    `refresh.prose_of` treats everything after it as body). The body itself
    carries `## ` headings that `digest` writes -- `## Figures`, `## Margin and
    footnote text` -- so stopping at the next heading silently dropped them
    while `read` still reported `ok`.
    """
    lines = markdown.split("\n")
    i = full_text_line(lines)
    return "" if i is None else "\n".join(lines[i + 1:]).strip()


def full_text_line(lines: list):
    """Index of the line that opens the body: the first `## Full text` heading
    that is not inside a fenced code block, so authored prose can quote the
    format without starting the body early. None when there is none."""
    fence = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            mark = stripped[:3]
            fence = None if fence == mark else (fence or mark)
            continue
        if fence is None and stripped == FULL_TEXT_HEADING:
            return i
    return None
