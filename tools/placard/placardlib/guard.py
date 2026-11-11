"""Paths Placard must never read: git-crypt paths and `.placard-skip` trees.

Encrypted at rest is not private to an LLM: the working tree is plaintext, so
digesting reads it. Owner, 2026-11-09: "I don't think you should have
placarded the Vault."
"""
from __future__ import annotations

import subprocess
from pathlib import Path

SKIP_MARKER = ".placard-skip"


def _repo_root(path: Path):
    for d in [path] + list(path.parents):
        if (d / ".git").exists():
            return d
    return None


def _uses_git_crypt(repo: Path) -> bool:
    cands = [repo / ".gitattributes", repo / ".git" / "info" / "attributes"]
    cands += list(repo.glob("**/.gitattributes"))[:200]
    for c in cands:
        try:
            if "git-crypt" in c.read_text(errors="replace"):
                return True
        except OSError:
            pass
    return False


def skip_marker_dir(path):
    """The nearest ancestor directory holding a .placard-skip file, or None."""
    p = Path(path).resolve()
    for d in ([p] if p.is_dir() else []) + list(p.parents):
        if (d / SKIP_MARKER).exists():
            return d
    return None


def git_crypt_paths(paths):
    """The subset of `paths` whose git `filter` attribute is git-crypt."""
    by_repo: dict = {}
    for p in paths:
        p = Path(p).resolve()
        repo = _repo_root(p.parent)
        if repo is not None:
            by_repo.setdefault(repo, []).append(p)
    hits = set()
    for repo, files in by_repo.items():
        if not _uses_git_crypt(repo):
            continue
        rels = [str(f.relative_to(repo)) for f in files]
        try:
            out = subprocess.run(
                ["git", "-C", str(repo), "check-attr", "-z", "--stdin", "filter"],
                input="\0".join(rels) + "\0", capture_output=True, text=True,
                timeout=120).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        f = out.split("\0")
        for i in range(0, len(f) - 2, 3):
            if f[i + 2].strip() == "git-crypt":
                hits.add(repo / f[i])
    return hits


def refusal_reason(path):
    """Why Placard must not read `path`, or None. Fails closed per file."""
    path = Path(path).resolve()
    d = skip_marker_dir(path)
    if d is not None:
        return f"{SKIP_MARKER} in {d}"
    if path in git_crypt_paths([path]):
        return "git-crypt path (filter=git-crypt): the working tree is plaintext"
    return None


def partition(paths):
    """(allowed, [(excluded_path, reason)]) in one batched pass."""
    paths = [Path(p) for p in paths]
    crypt = git_crypt_paths(paths)
    allowed, excluded = [], []
    for p in paths:
        d = skip_marker_dir(p)
        if d is not None:
            excluded.append((p, f"{SKIP_MARKER} in {d}"))
        elif p.resolve() in crypt:
            excluded.append((p, "git-crypt path"))
        else:
            allowed.append(p)
    return allowed, excluded
