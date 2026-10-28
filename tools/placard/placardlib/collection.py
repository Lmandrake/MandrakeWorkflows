"""Collection digests: one sidecar for a directory of generated output.

Large trees of generated analysis plots contain directories of many
near-identical files, each with its own sidecar. Reading
hundreds of descriptions of the same plot family buys nothing, and describing them cost
N vision calls.

So a homogeneous directory gets ONE digest describing the family: how many
files, what they share, how they vary, and a described sample. 23 calls instead
of 1,996.

What this is NOT: a claim that the individual files were examined. The digest
states exactly how many were sampled and names them, because "we looked at 3 of
N" and "we looked at N" must never read alike.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from . import figures

COLLECTION_NAME = "COLLECTION.placard.md"

# Enough to show the family's range without paying per file. Spread across the
# sorted order rather than taken from the front, because generated output is
# usually ordered and the first few look alike.
SAMPLE_SIZE = 3


def sample_paths(paths: list, size: int = SAMPLE_SIZE) -> list:
    """`size` paths spread evenly across the sorted set."""
    ordered = sorted(paths)
    if len(ordered) <= size:
        return ordered
    step = (len(ordered) - 1) / (size - 1) if size > 1 else 1
    return [ordered[round(i * step)] for i in range(size)]


def varying_tokens(names: list, shared: list) -> list:
    """Tokens that distinguish members of the family — its axes of variation.

    A reader deciding whether to descend needs to know what differs, not just
    what is common.
    """
    shared_set = set(shared)
    counts: dict = {}
    for name in names:
        base = os.path.splitext(name)[0].lower()
        for token in re.findall(r"[a-z]{2,}", base):
            if token in shared_set:
                continue
            counts[token] = counts.get(token, 0) + 1
    # A varying token appears on several members but not on most of them.
    low, high = 2, max(2, int(0.95 * len(names)))
    candidates = [(c, t) for t, c in counts.items() if low <= c <= high]
    candidates.sort(reverse=True)
    return [t for _c, t in candidates[:8]]


def render(directory, names: list, verdict, samples: list) -> str:
    """The collection digest. `samples` is [(filename, description_or_None)]."""
    directory = Path(directory)
    described = [(n, d) for n, d in samples if d]
    lines = [
        f"# {directory.name}/ — Placard collection digest",
        "",
        f"**{verdict.count} generated image files**, described as one family "
        f"rather than individually.",
        "",
        "## What this is",
        "",
        f"A directory of homogeneous generated output. "
        f"{verdict.reason}",
        "",
    ]
    if verdict.shared_tokens:
        lines += [f"Every member shares: `{'`, `'.join(verdict.shared_tokens)}`.",
                  ""]
    varying = varying_tokens(names, verdict.shared_tokens)
    if varying:
        lines += [f"Members vary by: `{'`, `'.join(varying)}`.", ""]

    lines += [
        "## Coverage — read this before relying on it",
        "",
        f"**{len(described)} of {verdict.count} files were actually looked at.** "
        f"The descriptions below are of those files only. The remaining "
        f"{verdict.count - len(described)} are assumed to belong to the same "
        f"family on the evidence of their filenames, which is an inference and "
        f"not an observation.",
        "",
        "## Open an individual file if…",
        "",
        "- you need a specific run, mode or band rather than the family",
        "- a sampled description below does not match what you expected, which "
        "would mean the family is less homogeneous than the filenames suggest",
        "",
    ]
    if described:
        lines += ["## Sampled members", ""]
        for name, desc in described:
            lines += [f"### {name}", "", desc.strip(), ""]
    lines += ["## All members", ""]
    for name in sorted(names)[:400]:
        lines.append(f"- {name}")
    if len(names) > 400:
        lines.append(f"- _(+{len(names) - 400} more)_")
    return "\n".join(lines) + "\n"


def image_names(directory) -> list:
    """Image files directly in `directory`, excluding anything generated."""
    exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".bmp", ".svg"}
    out = []
    try:
        entries = sorted(p for p in Path(directory).iterdir() if p.is_file())
    except OSError:
        return out
    for path in entries:
        name = path.name
        if name.endswith(".placard.md") or name.endswith(".body.md"):
            continue
        if path.suffix.lower() in exts:
            out.append(name)
    return out


def classify(directory):
    names = image_names(directory)
    return names, figures.classify_directory(names)


def member_of_collection(artifact) -> tuple:
    """(is_member, verdict) — does this image belong to a generated family?

    Owner's ruling: a directory of generated plots is described AS A FAMILY and
    never file by file. N descriptions of the same plot family is a huge waste,
    so the per-file path must be BLOCKED rather than merely not-taken: a sweep
    that digests every artifact in a tree would otherwise spend N vision calls
    without anyone deciding to.
    """
    artifact = Path(artifact)
    if artifact.suffix.lower() not in {
            ".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".bmp", ".svg"}:
        return False, None
    names, verdict = classify(artifact.parent)
    if verdict.is_collection and artifact.name in names:
        return True, verdict
    return False, verdict
