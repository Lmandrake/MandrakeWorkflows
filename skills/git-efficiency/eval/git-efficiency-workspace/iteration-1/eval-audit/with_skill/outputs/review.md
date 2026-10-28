# Review: bad_git_script.py

Target: `eval/evalinputs/bad_git_script.py`

## Problems found

1. **Lines 5-6 — `git add` per file in a loop.**
   ```python
   for f in changed_files:
       subprocess.run(["git", "add", f], check=True)
   ```
   One spawn + one index-lock cycle per file (N spawns for N files). Batch into a single call:
   ```python
   subprocess.run(["git", "add", *changed_files], check=True)
   ```

2. **Lines 7-8 — `git log -1 --format=%H <file>` per file in a loop.**
   ```python
   for f in changed_files:
       subprocess.run(["git", "log", "-1", "--format=%H", f])
   ```
   N history walks instead of one. If a per-file last-commit mapping is truly needed, walk once with `git log --name-status --format=%H` (or similar) and derive the per-file answer from that single output, rather than spawning git once per path.

3. **Line 9 — `git add -A` stages the whole tree.**
   ```python
   subprocess.run(["git", "add", "-A"], stderr=subprocess.DEVNULL)
   ```
   Unscoped staging: on a slow mount it's a full-tree stat, and in a shared repo it sweeps up files other agents/processes have staged but not committed — entanglement, not just slowness. Also redundant with the per-file adds in step 1. Fix: stage only the explicit changed set, e.g. `subprocess.run(["git", "add", *changed_files], check=True)`.

4. **Line 9 — stderr suppressed on `git add`.**
   ```python
   stderr=subprocess.DEVNULL
   ```
   If any single path is bad/ignored/rejected, git can fail the whole `add` — with stderr swallowed the script proceeds believing everything staged when nothing (or only part) did. Remove the redirect and let staging errors surface (and check the return code).

5. **Line 10 — bare `git commit` with no pathspec.**
   ```python
   subprocess.run(["git", "commit", "-m", "deploy"])
   ```
   Commits the *entire* staged index, including anything another agent/process staged and hasn't committed yet — a cross-agent collision risk in a shared repo. Name explicit paths:
   ```python
   subprocess.run(["git", "commit", *changed_files, "-m", "deploy"], check=True)
   ```

6. **Line 11 — unnecessary `git status` after a successful commit.**
   ```python
   subprocess.run(["git", "status"])
   ```
   The preceding `commit` already reports success via its exit code; re-checking with `status` is a second spawn that buys nothing given the code doesn't branch on its output. Drop it (or check the commit's own return code if verification is truly needed).

7. **Lines 14-15 — `git rev-parse HEAD` re-run inside a loop.**
   ```python
   def head():
       for i in range(len(os.listdir("."))):
           subprocess.run(["git", "rev-parse", "HEAD"])
   ```
   `HEAD` doesn't change across the loop (nothing in the loop body mutates it, and the loop variable `i` is unused) — it's a constant value re-fetched N times (N = directory entry count), an arbitrary and unrelated bound. Read it once and reuse:
   ```python
   def head():
       result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
       return result.stdout.strip()
   ```

## Count

**7 distinct problems.**
