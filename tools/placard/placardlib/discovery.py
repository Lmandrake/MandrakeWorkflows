"""Discovery: find sidecars by the artifact's path, and expose what is missing.

Two measured facts drive this module.

**Lookup must key on the target artifact, not the session.** The announce hook
is cwd-scoped, so a session that starts in one tree and later opens a file
elsewhere is never told that file has a digest.

**The failure mode is "never digested", not "digested and bypassed."** Across
1,089 sessions there were zero confirmed cases of a digest existing and being
ignored -- every heavy-artifact read checked had no sidecar at all, and a third
of PDFs fleet-wide have none. So what is MISSING has to be as visible as what
is stale, which is what `gaps` is for.
"""
from __future__ import annotations

import os
from pathlib import Path

SIDECAR_SUFFIX = ".placard.md"
BODY_MARKER = ".body.md"
MAP_NAME = "PROJECT.placard.md"

DIGESTIBLE_EXTS = {
    ".pptx", ".potx", ".ppt", ".key",
    ".pdf",
    ".docx", ".doc", ".pages", ".rtf",
    ".xlsx", ".xlsm", ".xltx", ".xls", ".csv", ".tsv",
    ".ipynb",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".bmp", ".svg",
}
SKIP_DIRS = {".git", ".svn", "node_modules", "__pycache__", ".venv", "venv"}


class Sidecars:
    __slots__ = ("artifact", "entry", "body", "exists")

    def __init__(self, artifact, entry, body, exists):
        self.artifact = artifact
        self.entry = entry
        self.body = body
        self.exists = exists


def is_generated(path) -> bool:
    """Generated bodies, maps and digests are never artifacts.

    Without this a generated body acquires a digest of its own, and a map
    advertises it as content (failure M4).
    """
    name = Path(path).name
    return (name.endswith(SIDECAR_SUFFIX) or name.endswith(BODY_MARKER)
            or name == MAP_NAME)


def sidecars_for(artifact) -> Sidecars:
    """Resolve the sidecars beside a specific artifact.

    An external body is located only via the entry file's `body_path`. A body
    file sitting on disk is never adopted on the strength of its name.
    """
    artifact = Path(artifact)
    entry = artifact.with_name(artifact.name + SIDECAR_SUFFIX)
    if not entry.exists():
        return Sidecars(artifact, entry, None, False)

    body = None
    try:
        from . import schema
        view = schema.load_digest(entry.read_text(encoding="utf-8",
                                                  errors="replace"))
        if view.body_layout == "external" and view.body_path:
            candidate = entry.with_name(view.body_path)
            if candidate.exists():
                body = candidate
    except OSError:
        pass
    return Sidecars(artifact, entry, body, True)


def iter_artifacts(root):
    return _split(root)[0]


def iter_excluded(root):
    """(path, reason) for artifacts Placard must not read (guard.py)."""
    return _split(root)[1]


def _split(root):
    from placardlib import guard
    return guard.partition(_walk(root))


def _walk(root):
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if is_generated(path):
                continue
            if path.suffix.lower() in DIGESTIBLE_EXTS:
                yield path


class GapReport:
    __slots__ = ("root", "total", "digested", "undigested", "by_ext")

    def __init__(self, root, total, digested, undigested, by_ext):
        self.root = root
        self.total = total
        self.digested = digested
        self.undigested = undigested
        self.by_ext = by_ext

    @property
    def coverage_frac(self):
        """None when the denominator is zero. 0/0 must never read as complete
        coverage -- that is the denominator collapse this project has been
        bitten by before."""
        if not self.total:
            return None
        return self.digested / self.total


def gaps(root) -> GapReport:
    """What is undigested under `root`. Cheap: stats sidecar existence, never
    hashes an original."""
    root = Path(root)
    total = digested = 0
    undigested = []
    by_ext: dict = {}
    for artifact in sorted(iter_artifacts(root)):
        total += 1
        ext = artifact.suffix.lower()
        slot = by_ext.setdefault(ext, {"total": 0, "digested": 0})
        slot["total"] += 1
        if artifact.with_name(artifact.name + SIDECAR_SUFFIX).exists():
            digested += 1
            slot["digested"] += 1
        else:
            undigested.append(artifact)
    return GapReport(root, total, digested, undigested, by_ext)
