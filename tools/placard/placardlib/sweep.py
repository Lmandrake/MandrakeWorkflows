"""Sweep: remove external bodies that no sidecar references.

publish_digest never deletes a superseded body (a reader may have resolved it
already), so orphans accumulate; refresh_body removes the one it just
superseded, and this sweep catches the rest (crashes, older runs).

Safety, in order of importance:
  * A body is deleted only if NO entry in its own directory names it.
  * A directory holding an entry that cannot be parsed is skipped whole: an
    unreadable entry might be the one that references the body.
  * A body younger than `min_age` seconds is kept: a digest in flight has
    written its body but not yet published the entry that names it.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

from . import discovery, schema

BODY_RE = re.compile(r"^.+\.placard\.[0-9a-f]{12}\.body\.md$")
ENTRY_SUFFIX = discovery.SIDECAR_SUFFIX


def is_body_name(name: str) -> bool:
    return bool(BODY_RE.match(name))


def find_orphans(root, min_age: float = 300.0, now: float = None) -> dict:
    """{'orphans': [Path], 'referenced': int, 'young': [Path],
    'skipped_dirs': [(Path, why)]}"""
    now = time.time() if now is None else now
    out = {"orphans": [], "referenced": 0, "young": [], "skipped_dirs": []}
    for dirpath, dirnames, filenames in os.walk(Path(root)):
        dirnames[:] = [d for d in dirnames if d not in discovery.SKIP_DIRS]
        d = Path(dirpath)
        bodies = [n for n in filenames if is_body_name(n)]
        if not bodies:
            continue
        refs, bad = set(), None
        for n in filenames:
            if not n.endswith(ENTRY_SUFFIX) or n == discovery.MAP_NAME:
                continue
            try:
                view = schema.load_digest(
                    (d / n).read_text(encoding="utf-8", errors="replace"))
                if view.body_path:
                    refs.add(view.body_path)
            except Exception as exc:      # any failure: cannot judge this dir
                bad = f"{n}: {exc}"
                break
        if bad:
            out["skipped_dirs"].append((d, bad))
            continue
        for n in sorted(bodies):
            if n in refs:
                out["referenced"] += 1
            elif now - (d / n).stat().st_mtime < min_age:
                out["young"].append(d / n)
            else:
                out["orphans"].append(d / n)
    return out


def remove_superseded(sidecar_path, old_body_name, new_body_name) -> bool:
    """Delete the body a refresh just replaced. Only a same-directory body-shaped
    name is ever touched, and never the one the new entry names."""
    if not old_body_name or old_body_name == new_body_name:
        return False
    if os.sep in old_body_name or not is_body_name(old_body_name):
        return False
    target = Path(sidecar_path).with_name(old_body_name)
    try:
        target.unlink()
        return True
    except FileNotFoundError:
        return False
