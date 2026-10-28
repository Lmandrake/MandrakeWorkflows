"""Internal-consistency checks for `verify --deep`.

`verify` compared bytes and nothing else, and reported 19/19 current over a
corpus carrying two false sentences per digest. These checks read the digest
against itself. Byte-level staleness stays in plain `verify`; this function
deliberately takes no source hash, so it cannot imply a check it does not make.

Deliberately NOT checked, because the external review refuted both:
  * escalation contract vs `body: full` -- a complete text extraction can still
    justify opening the original for figures, layout or cell relationships.
  * `tier` vs body size -- a skim-level summary beside a complete body is a
    coherent combination. Cost is read from size fields, not from `tier`.
"""
from __future__ import annotations

import hashlib
import re

from . import schema

_ERROR_MARKER = "[extraction error:"

# Prose that asserts how much of the document was covered. Coverage belongs in
# machine fields, where a checker can contradict it; this catches the claim
# surviving in prose where it cannot be checked.
_COVERAGE_CLAIM_RE = re.compile(
    r"only the (?:first page|abstract)"
    r"|abstract was read"
    r"|were not digested"
    r"|interior sections?.{0,40}not",
    re.IGNORECASE,
)
_COVERAGE_CLAIM_MIN_BODY_WORDS = 2000

_COUNT_FIELDS = ("figures_detected", "tables_detected", "pages_extracted")


class Finding:
    __slots__ = ("code", "message")

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def __repr__(self) -> str:
        return f"Finding({self.code!r}, {self.message!r})"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _section(markdown: str, heading: str) -> str:
    out, capturing = [], False
    for line in markdown.split("\n"):
        if line.strip().lower() == f"## {heading}".lower():
            capturing = True
            continue
        if capturing and line.startswith("## "):
            break
        if capturing:
            out.append(line)
    return "\n".join(out).strip()


def check_digest(view: schema.DigestView, *, body_text: str) -> list:
    findings: list = []
    fm = view.fm

    if view.body_sha256 and _sha(body_text) != view.body_sha256:
        findings.append(Finding(
            "BODY_HASH_MISMATCH",
            f"body_sha256 {view.body_sha256[:12]} does not match the body on disk"))

    # A body refresh may not silently widen the summary's basis. If the summary
    # was authored against a different body generation, it is needs-review.
    if (view.summary_basis == "body-gen" and view.summary_basis_sha
            and view.body_sha256 and view.summary_basis_sha != view.body_sha256
            and view.authoring_status == "current"):
        findings.append(Finding(
            "SUMMARY_BASIS_STALE",
            "summary was authored against a different body generation but is "
            "still marked authoring_status: current"))

    if _ERROR_MARKER in body_text:
        findings.append(Finding(
            "EXTRACTION_ERROR_AS_BODY",
            "the body records an extraction error and must not claim a usable body"))

    gaps = _section(view.markdown, "Gaps / uncertainties")
    if gaps and _COVERAGE_CLAIM_RE.search(gaps):
        words = len(body_text.split())
        if words >= _COVERAGE_CLAIM_MIN_BODY_WORDS:
            findings.append(Finding(
                "COVERAGE_CLAIM_IN_PROSE",
                "the Gaps section asserts coverage in prose while the body holds "
                f"{words:,} words; coverage belongs in fields"))

    for key in _COUNT_FIELDS:
        if key in fm:
            known = str(fm.get(f"{key}_known", "true")).strip().lower()
            if known in ("false", "no", "0") and str(fm[key]).strip() == "0":
                findings.append(Finding(
                    "UNKNOWN_RENDERED_AS_ZERO",
                    f"{key} is 0 while {key}_known is false; an unknown total "
                    "must never be rendered as zero"))
    return findings
