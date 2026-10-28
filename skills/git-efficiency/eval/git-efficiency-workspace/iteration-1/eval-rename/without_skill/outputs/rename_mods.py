#!/usr/bin/env python3
"""Rename mod directories per a CSV mapping (columns: old,new) and stage the
renames in git.

Usage:
    python3 rename_mods.py mapping.csv [--repo /path/to/repo] [--dry-run]

The CSV is read relative to the current directory unless it is absolute.
Paths in the CSV are treated as relative to --repo (default: cwd), which
should be the repo root or the directory containing the mod folders.

Because this repo lives on a slow WSL drvfs mount and other agents may be
committing concurrently, this script:
  - never runs `git add -A` / `-a` / `.` — only ever stages the exact
    src/dst paths it just renamed;
  - uses `git mv` (one process per rename) so the rename is staged
    atomically with the move, with no separate add step to fall out of
    sync on a slow filesystem;
  - checks each source/destination immediately before acting, since a
    concurrent agent may have already moved, deleted, or created either
    path since this script started.
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path


def load_mapping(csv_path: Path) -> list[tuple[str, str]]:
    pairs = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or {"old", "new"} - set(reader.fieldnames):
            sys.exit(f"error: {csv_path} must have 'old' and 'new' columns")
        for row in reader:
            old = (row["old"] or "").strip()
            new = (row["new"] or "").strip()
            if not old or not new:
                continue
            pairs.append((old, new))
    return pairs


def git_mv(repo: Path, old: str, new: str) -> tuple[bool, str]:
    old_path = repo / old
    new_path = repo / new

    if not old_path.exists():
        return False, f"skip: source missing (already moved by another agent?): {old}"
    if new_path.exists():
        return False, f"skip: destination already exists: {new}"

    new_path.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["git", "mv", "--", old, new],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, f"FAILED: git mv {old} -> {new}: {result.stderr.strip()}"
    return True, f"ok: {old} -> {new}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="CSV with old,new columns")
    parser.add_argument(
        "--repo", type=Path, default=Path.cwd(),
        help="repo root the old/new paths are relative to (default: cwd)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="print the planned renames without touching the working tree",
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        sys.exit(f"error: {repo} does not look like a git repo root (no .git)")

    pairs = load_mapping(args.csv_path)
    if not pairs:
        sys.exit(f"error: no usable rows in {args.csv_path}")

    print(f"{len(pairs)} rename(s) to process in {repo}")

    ok_count = 0
    skip_count = 0
    fail_count = 0

    for old, new in pairs:
        if args.dry_run:
            print(f"would rename: {old} -> {new}")
            continue

        ok, msg = git_mv(repo, old, new)
        print(msg)
        if ok:
            ok_count += 1
        elif msg.startswith("FAILED"):
            fail_count += 1
        else:
            skip_count += 1

    if args.dry_run:
        return

    print(f"\nstaged {ok_count}, skipped {skip_count}, failed {fail_count}")
    if fail_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
