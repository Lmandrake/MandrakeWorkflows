# parallel-agent-worktrees

A Claude Code skill: **run several coding agents against one repository without them
corrupting each other's work.**

`git worktree` gives each agent filesystem and index isolation. The point of this skill is
that isolation still leaks through channels that are not git at all — the wording of a
brief, a `rglob` that cannot tell a clone from the original, an import path that resolves to
the wrong checkout.

Every rule is traceable to a measured incident from a wave of six agents building modules in
parallel in one repository, where the coordination produced more defects than the work did.

## Install

Symlink the repo root into the skills directory:

```sh
ln -s "$(pwd)/skills/parallel-agent-worktrees" ~/.claude/skills/parallel-agent-worktrees
```

## Neighbours

- `git-efficiency` — git's own performance and safety mechanics from scripts. This skill
  assumes it and does not repeat it.
- `superpowers:dispatching-parallel-agents` — whether to fan work out at all.
- `superpowers:using-git-worktrees` — creating an isolated workspace for yourself.
