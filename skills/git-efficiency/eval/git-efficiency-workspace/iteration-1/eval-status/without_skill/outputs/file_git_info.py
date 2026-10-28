import subprocess
from pathlib import Path


def get_file_git_info(paths, repo_dir="."):
    """
    For each path in `paths` (relative to `repo_dir` or absolute within it),
    return the most recent commit hash that touched it and whether it
    currently has staged changes.

    Returns: dict[str, dict] mapping the ORIGINAL input string to
        {"commit": str | None, "staged": bool}
    A file with no commit history yet (e.g. newly added, untracked) gets
    commit=None.
    """
    repo_dir = str(repo_dir)

    # Normalize inputs to paths relative to repo_dir, since that's what
    # `git log`/`git diff` will report back.
    repo_path = Path(repo_dir).resolve()

    def to_rel(p):
        p = Path(p)
        if p.is_absolute():
            try:
                return str(p.resolve().relative_to(repo_path)).replace("\\", "/")
            except ValueError:
                return str(p).replace("\\", "/")
        return str(p).replace("\\", "/")

    rel_to_orig = {to_rel(p): p for p in paths}
    wanted = set(rel_to_orig.keys())

    result = {p: {"commit": None, "staged": False} for p in paths}

    # --- Most recent commit per file: ONE `git log` walk over the whole
    # history (not one `git log` per file), which matters a lot on a slow
    # drvfs mount where each git subprocess has real fixed overhead.
    # `git log --name-only` prints commits newest-first, so the first time
    # a path is seen is its most recent touching commit; stop early once
    # every wanted path has been resolved.
    log_proc = subprocess.Popen(
        ["git", "log", "--name-only", "--format=commit\t%H"],
        cwd=repo_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    remaining = set(wanted)
    current_hash = None
    try:
        for line in log_proc.stdout:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("commit\t"):
                current_hash = line.split("\t", 1)[1]
                continue
            if line in remaining:
                result[rel_to_orig[line]]["commit"] = current_hash
                remaining.discard(line)
                if not remaining:
                    break
    finally:
        log_proc.stdout.close()
        log_proc.terminate()
        log_proc.wait()

    # --- Staged changes: ONE `git diff --cached --name-only` call,
    # intersected with the wanted set, instead of `git status`/`git diff`
    # per file.
    diff_proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    staged_files = {
        line.strip() for line in diff_proc.stdout.splitlines() if line.strip()
    }
    for rel in wanted:
        if rel in staged_files:
            result[rel_to_orig[rel]]["staged"] = True

    return result
