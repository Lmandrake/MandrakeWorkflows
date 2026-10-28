"""The write protocol.

The dangerous event is an entry file pointing at a body from a different
generation. Three properties prevent it:

  * Bodies are CONTENT-ADDRESSED, so a different body is a different filename
    and nothing is ever overwritten in place (race S4).
  * The entry file is published LAST, after the body is written and hashed, so
    a crash leaves an unreferenced body rather than a dangling pointer.
  * The layout decision is a pure function of the body's encoded length, never
    of the entry file's size -- otherwise splitting shrinks the entry, the next
    run re-inlines it, and the digest oscillates forever.
"""
from __future__ import annotations

import hashlib

from . import BODY_SPLIT_THRESHOLD, frontmatter, schema

BODY_SUFFIX = ".body.md"
FULL_TEXT_HEADING = schema.FULL_TEXT_HEADING


def sha_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def body_filename(original_name: str, body_text: str) -> str:
    return f"{original_name}.placard.{sha_of(body_text)[:12]}{BODY_SUFFIX}"


def choose_layout(body_text: str) -> str:
    """'inline' or 'external', decided ONLY by the body's encoded byte length."""
    if len(body_text.encode("utf-8")) >= BODY_SPLIT_THRESHOLD:
        return "external"
    return "inline"


def publish_digest(*, sidecar_path, original_name, body_text,
                   frontmatter_fields, prose_markdown, write_text,
                   after_body=None) -> dict:
    """Write a digest. The entry file is published LAST, always.

    `write_text(path, text)` and the optional `after_body()` hook are injected
    so every crash interleaving is a unit test rather than a thought experiment.
    Superseded bodies are left on disk; removing them is a separate sweep,
    because deleting one here races a reader that already resolved it.
    """
    layout = choose_layout(body_text)
    fm = dict(frontmatter_fields)
    fm["body_layout"] = layout
    fm["body_sha256"] = sha_of(body_text)
    fm["body_bytes"] = str(len(body_text.encode("utf-8")))

    if layout == "external":
        name = body_filename(original_name, body_text)
        fm["body_path"] = name
        write_text(sidecar_path.with_name(name), body_text)
        if after_body is not None:
            after_body()
        entry = frontmatter.dump(fm) + prose_markdown
    else:
        fm.pop("body_path", None)
        if after_body is not None:
            after_body()
        entry = (frontmatter.dump(fm) + prose_markdown.rstrip("\n")
                 + f"\n\n{FULL_TEXT_HEADING}\n{body_text}\n")

    write_text(sidecar_path, entry)      # LAST. Always last.
    return fm
