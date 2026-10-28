---
name: git-efficiency
description: >-
  Use git efficiently and safely from scripts and agents, on slow mounts (WSL
  drvfs, network) or in repos several agents share. Use when writing, reviewing
  or auditing code that shells out to git, when git is slow or hits
  `index.lock`, or when one agent's commit sweeps up another's files.
---

# Engaging git efficiently and safely

Every `git ...` is a **process spawn** (fork, load binary, read config). On a
slow mount that costs tens to hundreds of ms, so a per-file loop scales linearly
with file count. And every command that **writes the index** (`add`, `commit`,
`mv`, `rm`, `checkout`, `reset`, `merge`, `stash`) takes `.git/index.lock`
exclusively; in a shared repo serial per-file writes thrash that lock and other
agents fail with *"Unable to create '.../index.lock': File exists"*. Pure reads
(`log`, `show`, `cat-file`, `rev-parse`) take no lock; `status` refreshes the
index only opportunistically and does not fail on a held lock.

So: **do the fewest git invocations that accomplish the task, scope every one
explicitly, and never hold the lock across a loop.**

## Batch

**Stage many paths in one call:** `git add a b c`, not a loop of `git add "$f"`.
In a script, collect paths and pass them together (`git add -- "${paths[@]}"`,
`subprocess.run(["git","add","--",*paths])`). Thousands of pathspecs in one call
are far faster than thousands of calls.

⚠️ **zsh does not word-split an unquoted variable.** `paths="a b c"; git add
$paths` passes ONE pathspec and fails. Use a real array (`"${paths[@]}"`) or
`${=paths}`, not a per-path loop.

**Ask about many things in one call:**
- `git status --porcelain` once and parse, never `git status <path>` per path.
- `git log --name-only` / `--name-status` for files-per-commit in one walk.
- `git cat-file --batch` for many objects, not `git show <rev>:<path>` each.
- `git diff --cached --name-only` once for the staged set.

**Bound history walks** (`-n 1`, `--max-count`, `--since`) when you don't need
all of it. **Read constants once** (`rev-parse HEAD`, `config`,
`--show-toplevel`); don't re-shell them in a loop.

## Trust the exit code for success, not for scope

A `git add` / `commit` / `mv` that exits 0 did what you asked; don't re-run
`status` or `log` to "make sure". Exit 0 does not prove you asked for the right
scope, so check state only where scope can silently differ from intent: the
partial-commit and lock-retry cases flagged below.

## Safety on a shared worktree

**Never bare `git commit` / `commit -a`, never `git add -A` / `git add .`.** A
bare commit takes the whole index, including files another agent staged; `-A`
stages the whole tree (a full-tree stat on a slow mount, and it sweeps up others'
work). Name files, not directories: a directory pathspec commits everything under
it, including what a daemon or peer wrote there since.

**Default commit form: `git commit -m "msg" -- <paths>`.** It commits only the
named paths whatever else is staged, which is why it is the default in a shared
index. **`-m` must come before `--`**, or the message is read as a pathspec.

🔴 **A pathspec commit takes each named file's WORKING-TREE content, not its
staged content.** Paths isolate files, not hunks or authors: an unrelated unstaged
edit to a named file is committed too. So:
- Before `git commit -m "msg" -- <paths>`, check `git diff -- <path>` (unstaged
  changes) shows nothing, or only changes you mean to commit.
- If you staged hunks deliberately (`add -p`) and the file has other unstaged
  edits, commit the staged content with plain `git commit -m "msg"` (no
  pathspec), right after confirming `git diff --cached --name-only` lists only
  your paths.

**A pathspec commit refuses an untracked path** ("did not match any file(s)
known to git"). `git add` a new file first.

**A rename stages a deletion and a creation: name both ends.** Committing only
the new path leaves the old-path deletions staged.

**A staged path left out of a multi-path `git commit -- <paths>` stays staged,
silently, and rides into later commits.** After such a commit, `git status
--short -- <every path you touched>` must be clean.

**Stage and commit back to back.** Between a separate `add` and `commit`, another
agent's commit can sweep your staged files under their message. If a commit says
"no changes added to commit" right after a successful `add`, check whether your
change already landed in HEAD before re-adding.

**Never suppress stderr on `add`/`commit`.** One bad path can reject the whole
`add`; with `2>/dev/null` you commit nothing while believing you staged
everything.

**Never stash, `pull --rebase --autostash`, rebase or merge in a tree others are
editing**, nor while your own subagents are mid-edit. Each can drop someone's
uncommitted work, and a refused `git merge` can hard-reset the tree. Merge in a
private worktree and push `HEAD:<branch>` from there. Commit and push the moment
work exists. If work looks lost, or you must publish from a tree that is never
clean, or a pushed commit tells the wrong story, read
[references/shared-tree-recovery.md](references/shared-tree-recovery.md).

**Cherry-picking onto a file someone has since reformatted** (e.g. JSON
re-serialized in a different key order) conflicts with context that looks
unrelated. Don't fight the textual merge:
1. `git show <sha> -- <file>` to read the small semantic change.
2. `git checkout --ours <file>` to take the current-format file.
3. hand-apply the semantic change onto it.
4. `git add <file>` to mark it resolved.
5. `git cherry-pick --continue`.

**Handle `index.lock`; don't fight it.**
- Assume a **live** git first: `pgrep -f 'git '`, `fuser .git/index.lock`, the
  lock's age. If something is mid-write, wait.
- **On WSL, also check Windows** (`tasklist.exe | grep -i '^git'`): a Windows
  git.exe holding the lock is invisible to Linux `pgrep`.
- Remove it (`rm -f .git/index.lock`) only when stale: no live git on either side
  and older than any plausible command. A retry loop that re-checks liveness
  (~15-20 tries at 2 s) clears real contention safely.
- Never wrap git calls in a blind `rm -f index.lock`; it corrupts a live writer.
- **After a contention retry succeeds, `git log --stat -1` what landed.** A
  failed `add` can leave stale staged content that a later commit ships.

**Don't hold the lock across a loop.** Do per-item work without git (moves,
building a list), then one batched git call at the end.

**Structural fix: per-agent worktrees.** Agents sharing one worktree share one
index, so batching can't remove all contention; `git worktree add` gives each its
own. Worktrees don't isolate brief wording, globs or import paths; see
`parallel-agent-worktrees`.

## Filesystem operations beat git plumbing

**Renames:** move with the filesystem (`os.replace`, `mv`), then one batched
`git add -- <old paths> <new paths>`; git detects renames from content. Where a
guard blocks `git add -A`, `git rm -r --cached --quiet -- <old paths>` then
`git add -- <new paths>` stages a batch of renames in two calls; `git status`
should show `R` entries.

**Test fixtures: build the repo once** per test file (template repo with a base
commit), then copy the tree or reset it per case, instead of `init` + `config` +
`add` + `commit` in every case.

## Auditing existing code

- **Grep for `git` over-reports**: most hits are comments, help text and print
  strings. Read the call site (in a loop? what bound?) before flagging.
- **Impact = loop bound** x git commands per iteration.
- **Don't flag a single batched call.** Flag per-item loops, unbounded walks, and
  safety holes (bare commit, `-A`, suppressed stderr, pathspec commit over
  unrelated unstaged hunks).
- **Separate slowness from entanglement.** Per-case `git init` in a temp repo is
  only spawn cost; a per-row `git mv` in the shared repo is also a collision risk
  and outranks it even at smaller N.

## Checklist

- [ ] No mutating git command per file where one batched call would do.
- [ ] `status` / `log` / object reads are one call over many items.
- [ ] Every `commit` and `add` names explicit files: no bare commit, no `-A`/`.`.
- [ ] Pathspec commits only over files with no unrelated unstaged hunks.
- [ ] No `2>/dev/null` on `add`/`commit`.
- [ ] History walks bounded when you don't need all of it.
- [ ] Constants (`rev-parse HEAD`, config) read once.
- [ ] Per-item work outside the lock; git taken once at the end.
- [ ] Stale-lock handling tells a live git from a dead one before removing.
- [ ] Many agents still colliding: consider worktrees.
