#!/usr/bin/env python3
"""
Rename ~50 mod directories per a CSV mapping (columns: old,new) and stage the
renames in git.

git-efficiency choices (see git-efficiency SKILL.md):
- All ~50 moves are done with the filesystem (os.replace), NOT `git mv` per
  row: on a slow WSL drvfs mount, one git spawn + index.lock cycle per file
  would be ~50 lock acquisitions, each a collision window against other
  agents sharing this repo.
- Git is invoked exactly twice, both with explicit pathspecs collected up
  front: one `git add` naming every old+new path together (git detects the
  renames from content), then one `git status --porcelain=v1` over that same
  path list to confirm staging succeeded. No bare `git add -A`/`.`, no
  suppressed stderr, no per-file git calls, no unbounded history reads.
- The lock is only taken for that single batched `git add`, at the very end,
  after every filesystem move has already happened outside git entirely —
  minimizing the window in which this script can contend with a concurrent
  agent's git command.
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path


def load_mapping(csv_path: Path) -> list[tuple[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or {"old", "new"} - set(reader.fieldnames):
            raise SystemExit(f"CSV must have 'old' and 'new' columns, got {reader.fieldnames}")
        rows = [(row["old"].strip(), row["new"].strip()) for row in reader if row["old"].strip()]
    if not rows:
        raise SystemExit("No rows found in CSV")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", type=Path, help="CSV file with old,new columns")
    ap.add_argument("--repo-root", type=Path, default=Path("."),
                     help="Repo root that old/new paths are relative to (default: cwd)")
    ap.add_argument("--dry-run", action="store_true", help="Print planned moves, do nothing")
    args = ap.parse_args()

    repo_root = args.repo_root.resolve()
    mapping = load_mapping(args.csv_path)

    # Validate everything up front so a bad row doesn't leave a half-renamed tree.
    planned: list[tuple[Path, Path]] = []
    for old, new in mapping:
        old_path = (repo_root / old).resolve()
        new_path = (repo_root / new).resolve()
        if not old_path.is_dir():
            raise SystemExit(f"Source directory does not exist: {old_path}")
        if new_path.exists():
            raise SystemExit(f"Destination already exists: {new_path}")
        planned.append((old_path, new_path))

    if args.dry_run:
        for old_path, new_path in planned:
            print(f"{old_path.relative_to(repo_root)} -> {new_path.relative_to(repo_root)}")
        print(f"\n{len(planned)} renames planned (dry run, nothing moved or staged).")
        return 0

    # 1) Do every move with the filesystem. No git involved yet, so no lock
    #    is held or contended while this loop runs.
    touched_paths: list[str] = []
    for old_path, new_path in planned:
        new_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.replace(new_path)  # os.replace: atomic on same filesystem
        touched_paths.append(str(old_path.relative_to(repo_root)))
        touched_paths.append(str(new_path.relative_to(repo_root)))

    # 2) One batched `git add` over every old+new path, explicit pathspecs,
    #    stderr NOT suppressed. This is the only lock acquisition in the
    #    whole script.
    add_cmd = ["git", "-C", str(repo_root), "add", "--"] + touched_paths
    result = subprocess.run(add_cmd)
    if result.returncode != 0:
        raise SystemExit(f"git add failed (exit {result.returncode}); see stderr above")

    # 3) One `git status`, scoped to the same paths, to report what got
    #    staged. Not a re-verification of the add's exit code (already
    #    trusted) — just a summary for the caller.
    status_cmd = ["git", "-C", str(repo_root), "status", "--porcelain=v1", "--"] + touched_paths
    status = subprocess.run(status_cmd, capture_output=True, text=True, check=True)
    print(status.stdout, end="")
    print(f"\n{len(planned)} directories renamed and staged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
