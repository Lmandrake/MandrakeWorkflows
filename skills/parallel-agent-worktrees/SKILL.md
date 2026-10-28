---
name: parallel-agent-worktrees
description: >
  Run several coding agents against one repository without cross-contamination. Use when
  dispatching agents into git worktrees, writing a worktree agent's brief, auditing a repo
  after parallel agents built in it, or writing a tool that counts "real callers" while
  worktrees exist. Not git's own mechanics (git-efficiency) nor whether to parallelize
  (superpowers:dispatching-parallel-agents).
---

# Parallel agents, one repository

> **Example, one multi-seat setup (skip if yours differs):** each seat writes only its own clone; a subagent's worktree is a pool slot handed out by a WorktreeCreate hook, and the helper pushes a per-seat submission branch for the seat to land, never `main`. The rules below still apply inside a slot..

**A worktree isolates the filesystem and the index. It does not isolate anything you say, write, import, or share (config, hooks, ports, databases, caches, external services).** Knowing a rule is not a habit; prefer command forms that make the mistake impossible.

## A bare `git commit` sweeps the whole index

`git add <paths>` followed by a bare `git commit` commits everything staged in that checkout, including another agent's staged files. It has landed unrelated multi-file work inside a small commit, pushed, twice.

Scope the commit: `git commit -m "msg" -- <paths>` (`-m` before `--`, or git reads the message as a pathspec). Qualifier: a pathspec commit takes the file's whole working-tree content, including unrelated unstaged hunks. So name paths AND check the file has no unrelated unstaged hunks (`git diff -- <path>`); or, to commit deliberately staged hunks, use plain `git commit` after `git diff --cached --name-only` shows only your paths. Details: `git-efficiency`.

A wrongly described commit already pushed: annotate it (`git notes add -m "..." <sha>`), do not rewrite shared history.

## An absolute path in the brief puts the agent in the main checkout

An agent given a worktree and a brief naming the project's absolute path may write to that path instead. A running agent usually cannot be corrected mid-task (depends on the harness), so prevent it in the brief: use worktree-relative terms, state that the agent's current working directory is the workspace, and never put the main checkout's absolute path in the instructions, even for orientation.

Preflight in the agent: assert `git rev-parse --show-toplevel` equals the assigned worktree before the first write.

## A clone of the repository is not a caller of it

A filesystem-walking tool that counts real usage must exclude other checkouts of the same repo. (`ROOT.rglob("*.py")` over `.claude/worktrees/` over-counted importers several-fold.) Do not rely on a list of known directory names: linked worktrees can live anywhere. Enumerate them with `git worktree list --porcelain` and exclude those roots, plus `.git/worktrees` and any other clone directory the project uses. State the scope explicitly.

## `sys.path[0]` is the script's own directory, not your worktree

A script run by path imports its package from wherever it is installed (in an editable install, the main checkout), not from the worktree it sits in. `python -c` resolves from the current directory, so two tools in one worktree can disagree. If tools that should agree disagree, check this first.

Run tools as modules (`python -m pkg.tool`) or have the tool insert its own repo root on `sys.path`. Neither is a guarantee (CWD, `PYTHONPATH`, editable installs and namespace packages can still select another checkout), so assert the imported module's resolved `__file__` is under the worktree.

## Never merge in a checkout other agents are editing

With autostash on (`merge.autoStash`/`rebase.autoStash`, or a wrapper that stashes), a refused merge ("local changes would be overwritten") makes git stash, hard-reset and re-apply; if a peer holds `index.lock` the re-apply fails and all uncommitted edits are gone with nothing in the reflog. Merge in a private, disposable worktree and push from there. Recovery: `git-efficiency`.

## Dispatch hygiene

- **Disjoint file surfaces per agent.** Overlap is what makes the leaks above bite.
- **Shared checkout: agents write files, one session commits.** Commits are the operation that reaches outside the writer's own paths.
- **Isolate non-git shared resources too.** Ports, databases, caches, git config/hooks and external services are shared unless the brief assigns each agent its own.
- **Push branches before they can be lost.** Deleting a worktree directory loses its uncommitted changes (committed work survives on the branch ref); a bad `reset --hard` loses more.
- **Before believing "everything is pushed":** `git worktree list`, then check each branch has an upstream.
