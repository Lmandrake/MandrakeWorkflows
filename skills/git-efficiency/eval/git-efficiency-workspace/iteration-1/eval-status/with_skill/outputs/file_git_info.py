"""
Given ~200 file paths in a git repo, return each file's most recent commit
hash and whether it currently has staged changes.

git-efficiency choices (see git-efficiency/SKILL.md):
- Exactly THREE total git invocations for the whole batch, independent of
  path count: one `rev-parse --show-toplevel` (read once, not re-shelled per
  path), one `git log --name-only -- <all paths>` to get the most recent
  commit touching each path, and one `git diff --cached --name-only --
  <all paths>` for staged status. No per-file git spawn — critical on a slow
  WSL drvfs mount, where each spawn costs tens-to-hundreds of ms.
- All paths are passed as a single scoped pathspec (`--` followed by every
  path) rather than looped one-by-one, and as an argv list via subprocess
  (no shell), so there's no quoting risk and no ARG_MAX concern at this
  scale (~200 short paths).
- `git log` with a pathspec restricts the per-commit `--name-only` diff to
  just those paths, so history is not walked further than needed to find
  each file's latest touch; there is no unbounded/global log walk.
- This is a read-only audit (no add/commit/mv), so the shared-worktree
  entanglement risks (bare commit, `-A`, suppressed stderr, index.lock
  contention) don't apply here — but stderr is still left unsuppressed on
  both calls (`check=True`, no `2>/dev/null`) so a git failure raises
  instead of silently reporting empty/wrong results.
"""

import subprocess
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional


class FileGitInfo(NamedTuple):
    last_commit: Optional[str]  # None if never committed / not tracked
    staged: bool                # True if it has staged (index) changes


def get_file_git_info(
    paths: List[str], repo_dir: str = "."
) -> Dict[str, FileGitInfo]:
    """
    For each path in `paths` (relative or absolute, may be inside or outside
    `repo_dir`'s cwd as long as they're under the repo), return a
    FileGitInfo(last_commit, staged).

    Uses exactly 3 git invocations total, however many paths are given
    (tested against ~200) — see module docstring for why.
    """
    if not paths:
        return {}

    # Read the repo root once; never re-derive it per path.
    toplevel = subprocess.run(
        ["git", "-C", repo_dir, "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    repo_root = Path(toplevel)

    # Normalize every input to a path relative to the repo root, since that's
    # the form git log/diff --name-only report back in their output.
    rel_paths: List[str] = []
    orig_by_rel: Dict[str, str] = {}
    for p in paths:
        pp = Path(p)
        abs_p = pp if pp.is_absolute() else (Path.cwd() / pp)
        try:
            rel = str(abs_p.resolve().relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            # Wasn't resolvable under repo_root as given (e.g. caller already
            # passed a repo-relative string while cwd != repo_root) — use it
            # as-is and let git report it unmatched rather than erroring.
            rel = str(p).replace("\\", "/")
        rel_paths.append(rel)
        orig_by_rel[rel] = p

    result: Dict[str, FileGitInfo] = {
        p: FileGitInfo(last_commit=None, staged=False) for p in paths
    }

    # --- one call: most recent commit touching each path ---
    # \x01 prefix on the hash line keeps it unambiguous against file-path
    # lines in the --name-only listing that follows each commit.
    log_proc = subprocess.run(
        ["git", "-C", repo_dir, "log", "--format=\x01%H", "--name-only",
         "--", *rel_paths],
        check=True,
        capture_output=True,
        text=True,
    )
    current_commit = None
    found = set()
    for line in log_proc.stdout.splitlines():
        if line.startswith("\x01"):
            current_commit = line[1:].strip()
            continue
        rel = line.strip()
        if not rel or rel not in orig_by_rel or rel in found:
            continue
        found.add(rel)
        orig = orig_by_rel[rel]
        result[orig] = result[orig]._replace(last_commit=current_commit)

    # --- one call: which of these paths currently have staged changes ---
    diff_proc = subprocess.run(
        ["git", "-C", repo_dir, "diff", "--cached", "--name-only",
         "--", *rel_paths],
        check=True,
        capture_output=True,
        text=True,
    )
    staged_rel = {line.strip() for line in diff_proc.stdout.splitlines() if line.strip()}
    for rel, orig in orig_by_rel.items():
        if rel in staged_rel:
            result[orig] = result[orig]._replace(staged=True)

    return result
