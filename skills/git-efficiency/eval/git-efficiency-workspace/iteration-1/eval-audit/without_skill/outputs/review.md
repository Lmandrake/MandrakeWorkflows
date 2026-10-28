# Review: bad_git_script.py

Target: `eval/evalinputs/bad_git_script.py`

## Problems

1. **Line 6 — per-file `git add` in a loop.** One subprocess spawned per file
   instead of one batched call. Fix: `subprocess.run(["git","add","--",*changed_files], check=True)`.

2. **Line 8 — per-file `git log -1 --format=%H f` in a loop, output discarded.**
   N subprocess spawns whose stdout is never captured, so the call does
   nothing useful. It also runs *before* the commit on line 10, so even if the
   output were captured it would report each file's *previous* commit, not the
   deploy commit just made — the logic can never answer the question the
   comment claims it answers. Fix: drop it, or run once after the commit with
   `capture_output=True, text=True` and batched paths.

3. **Line 9 — `git add -A` stages the entire working tree**, not just
   `changed_files`. This silently pulls in any other unrelated or in-progress
   changes present in the repo (including another process's edits, stray
   debug files, secrets) into a commit whose function signature promised to
   record only the given files. Fix: delete this line — the per-file `add` on
   line 6 already staged the intended set — or replace with explicit paths.

4. **Line 9 — `stderr=subprocess.DEVNULL` on `git add -A`.** Suppresses any
   error (bad path, permission denied, pathspec did not match) with no trace.
   Combined with problem 5 (no `check=True`), a failed add is invisible and
   the commit proceeds on whatever partial/wrong stage resulted. Fix: never
   redirect git's stderr away; let it surface and check the return code.

5. **Lines 9–11 — no `check=True` (or returncode check) on `git add -A`,
   `git commit`, or `git status`.** Every failure mode (nothing to commit, a
   failing pre-commit hook, a detached-HEAD or non-repo cwd) is silently
   swallowed; the function always returns as if it succeeded. Fix: add
   `check=True` to each call, or explicitly branch on `.returncode`.

6. **Line 10 — hardcoded, non-descriptive commit message `"deploy"`** for
   every call regardless of what changed. Destroys the provenance value of
   git history. Fix: build the message from `changed_files` or accept a
   message parameter from the caller.

7. **Line 11 — `git status` does not "confirm it worked."** Its output is
   never captured or parsed, so the comment's claim is false — this is a
   print with no verification logic attached. Fix: check the commit's
   returncode (or compare `git rev-parse HEAD` before/after) and have
   `record()` return/raise a real success/failure signal.

8. **Lines 6 + 9 contradict each other.** The deliberate, scoped per-file
   `git add` is immediately superseded by the blanket `git add -A` two lines
   later, so `record()` can never actually perform the scoped commit its name
   and docstring promise — it always sweeps the whole tree. Fix: remove the
   blanket add (see problem 3) so the scoped add is the one that sticks.

9. **Lines 14–15 (`head()`) — `git rev-parse HEAD` called once per entry in
   `os.listdir(".")`.** The count of files in the current directory has no
   relationship to HEAD, HEAD cannot change between iterations, and the
   output is discarded every time. This spawns an unbounded number of
   redundant git subprocesses (worse as the directory grows) to recompute an
   invariant value nobody uses. Fix: call once —
   `subprocess.run(["git","rev-parse","HEAD"], check=True, capture_output=True, text=True).stdout.strip()`.

10. **No repo-root/cwd guard anywhere in the file.** Every git call relies
    implicitly on the process's current working directory being the intended
    repository. If invoked from elsewhere (a caller that `chdir`'d, a nested
    submodule, a different repo entirely), `git add -A` / `git commit` would
    silently mutate the wrong repository. Fix: pass an explicit `cwd=` to
    every `subprocess.run` call, or verify
    `git rev-parse --show-toplevel` matches the expected path before any
    mutating command.

11. **Lines 6 and 8 — file paths passed with no `--` separator before them.**
    `git add f` / `git log -1 --format=%H f` will misinterpret any path that
    happens to start with `-` (e.g. a file named `-force`) as an option
    rather than a pathspec, causing unintended git behavior or a spurious
    error. Fix: always insert a `--` separator before path arguments, e.g.
    `["git","add","--",*changed_files]`.
