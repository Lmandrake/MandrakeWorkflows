"""Refresh, as three independent concerns.

`init --force` rewrote the whole sidecar from an empty scaffold, so the
documented remedy for a stale digest destroyed the authored prose -- the one
expensive thing in the system. That made the correct response to staleness
economically irrational, so corpora rotted stale instead of being refreshed.

Here the concerns are separable: frontmatter, body, prose. A body refresh
rewrites the body and the body's provenance, carries the prose through
verbatim, and NEVER widens what the summary claims to have been authored from.
"""
from __future__ import annotations

import re

from . import publish, schema

# Identifier shapes whose appearance means the new extraction recovered
# something the summary's author never saw.
_IDENTIFIER_RE = re.compile(
    r"\bNTR\s*#?\s*\d+\b"
    r"|\barXiv:\s*\d{4}\.\d{4,5}\b"
    r"|\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b"
    r"|https?://\S+",
)
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.M)
_LARGE_DELTA_WORDS = 200


def prose_of(markdown: str) -> str:
    """Everything except the `## Full text` section, verbatim."""
    lines = markdown.split("\n")
    i = schema.full_text_line(lines)
    out = lines if i is None else lines[:i]
    return "\n".join(out).rstrip("\n") + "\n"


_FIGURE_FIELD_PREFIXES = ("figure", "descriptions_", "skip_reasons", "unique_images",
                          "captions_associated")


def _norm(text: str) -> str:
    return " ".join(text.split())


def materially_different(old_body: str, new_body: str) -> tuple:
    """(is_material, reason). D6's gate: a rare flag is a meaningful flag, so
    whitespace and cosmetic churn must not fire it."""
    if _norm(old_body) == _norm(new_body):
        return False, "no change beyond whitespace"

    new_ids = (set(_IDENTIFIER_RE.findall(new_body))
               - set(_IDENTIFIER_RE.findall(old_body)))
    if new_ids:
        return True, f"new identifier(s) recovered: {sorted(new_ids)[:3]}"

    old_rows = len(_TABLE_ROW_RE.findall(old_body))
    new_rows = len(_TABLE_ROW_RE.findall(new_body))
    if new_rows > old_rows:
        return True, f"table structure recovered ({old_rows} -> {new_rows} rows)"

    delta = abs(len(new_body.split()) - len(old_body.split()))
    if delta >= _LARGE_DELTA_WORDS:
        return True, f"large text delta ({delta} words)"

    return False, "change is not material"


class ProseConflict(RuntimeError):
    """Someone edited the authored prose while we were extracting.

    "Preserve prose" must not mean "overwrite a newer edit with the copy I read
    ten seconds ago". Extraction takes seconds to minutes, which is ample time
    for a human or another agent to improve the summary; writing our stale copy
    back would silently destroy that improvement while reporting that prose was
    preserved.
    """


def refresh_body(*, entry_text, sidecar_path, original_name, new_body,
                 new_fields, write_text, load_body=None,
                 reread_entry=None, remove_superseded=None) -> dict:
    """Replace the body and its provenance; carry the prose through untouched.

    When `reread_entry` is supplied it is called immediately before publishing
    and the prose is compared; a change raises ProseConflict rather than
    overwriting it.
    """
    view = schema.load_digest(entry_text)
    prose = prose_of(view.markdown)

    if view.body_layout == "external" and view.body_path and load_body:
        old_body = load_body(view.body_path) or ""
    else:
        old_body = schema.inline_body(view.markdown)

    fm = dict(view.fm)
    # The figure pass owns these fields. Merging a new run over an old one kept
    # `figure_model` from a run that described the figure after a later run
    # described nothing, so a re-digest replaces the whole family.
    for key in [k for k in fm if k.startswith(_FIGURE_FIELD_PREFIXES)]:
        if key not in new_fields:
            del fm[key]
    fm.update(new_fields)

    # Any change to the body text puts a current summary up for review. The
    # materiality test ranks HOW MUCH it changed, but it cannot see a changed
    # number ($61,400 -> $91,400) or a reversed conclusion, so it may not be
    # the permission to keep `current` (found in review, 2026-10-26).
    if (_norm(old_body) != _norm(new_body)
            and fm.get("authoring_status", "unknown") == "current"):
        fm["authoring_status"] = "needs-review"
    # summary_basis / summary_basis_sha are deliberately NOT touched: they
    # record what the human read, which a re-extraction cannot change.

    # Last check before we commit: did the prose move under us while we were
    # extracting? Aborting is the only honest option -- we hold a stale copy.
    if reread_entry is not None:
        fresher = reread_entry()
        if fresher:
            current = prose_of(schema.load_digest(fresher).markdown)
            if current != prose and _norm(current) == _norm(prose):
                # A whitespace-only edit (indentation, a hard break) can carry
                # markdown meaning: publish the NEWER prose rather than writing
                # back the copy read at the start.
                prose = current
            elif current != prose:
                raise ProseConflict(
                    "the authored prose changed while this extraction was "
                    "running, so writing the copy read at the start would "
                    "destroy that edit. Nothing was written. Re-run `digest` "
                    "to pick up the newer prose.")

    published = publish.publish_digest(
        sidecar_path=sidecar_path,
        original_name=original_name,
        body_text=new_body,
        frontmatter_fields=fm,
        prose_markdown=prose,
        write_text=write_text,
    )
    # The new entry is on disk and names the new body: only now is the old one
    # safe to drop. Skipped when `remove_superseded` is not supplied.
    if remove_superseded is not None and view.body_layout == "external":
        remove_superseded(sidecar_path, view.body_path,
                          published.get("body_path"))
    return published
