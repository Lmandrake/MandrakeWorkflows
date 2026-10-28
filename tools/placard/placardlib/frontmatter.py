"""Round-trip-safe flat-scalar frontmatter.

v1 wrote `key: value` raw, so a value containing a newline or a bare `---`
corrupted the file — and because the staleness gate reads this frontmatter, a
mis-parse presented as `stale`, whose v1 remedy destroyed authored prose.

Values that cannot survive as plain text are JSON-encoded. A leading `"` is the
unambiguous marker, because a plain value that genuinely starts with a quote is
itself JSON-encoded on the way out.
"""
from __future__ import annotations

import json

DELIM = "---"


def _needs_quoting(value: str) -> bool:
    return (
        value == ""
        or value != value.strip()
        or "\n" in value
        or "\r" in value
        or value.startswith('"')
        or value.lstrip().startswith(DELIM)
    )


def dump(fm: dict) -> str:
    lines = [DELIM]
    for key, raw in fm.items():
        value = "" if raw is None else str(raw)
        if _needs_quoting(value):
            value = json.dumps(value, ensure_ascii=False)
        lines.append(f"{key}: {value}")
    lines.append(DELIM)
    return "\n".join(lines) + "\n"


def parse(text: str) -> dict:
    fm, _ = split(text)
    return fm


def split(text: str) -> tuple:
    """Return (frontmatter dict, the markdown after the closing delimiter)."""
    if not text.startswith(DELIM):
        return {}, text
    lines = text.split("\n")
    if lines[0].strip() != DELIM:
        return {}, text
    fm: dict = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == DELIM:
            return fm, "\n".join(lines[i + 1:])
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith('"'):
            try:
                value = json.loads(value)
            except ValueError:
                pass
        fm[key.strip()] = value
    return fm, ""          # unterminated frontmatter: no body, not a crash
