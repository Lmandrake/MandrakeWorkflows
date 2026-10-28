# git_efficiency

A machine-wide, reusable skill for engaging `git` efficiently and safely from
scripts and agents — especially on a slow filesystem (WSL drvfs / 9p, network
mounts) and in repos that several agents or processes share at once.

The skill lives in [`git-efficiency/SKILL.md`](SKILL.md).

## Why this exists

The wisdom was distilled from an audit of a large multi-agent RimWorld modding
repo on a WSL drvfs mount, where two costs — git's per-invocation **process
spawn** and the shared **`.git/index.lock`** — turned serial, per-file git usage
into work that was both slow and *entangling* (one agent's commit sweeping
another's staged files; constant `index.lock` collisions). The fixes generalize
to any project, which is why the skill
lives in its own repo rather than inside any one project.

## Using it

- **In a project that consumes skills:** symlink or copy `git-efficiency/` into
  that project's skills directory (e.g. `~/.claude/skills/git-efficiency`), or
  point the harness's skill path here.
- **As a checklist:** read `git-efficiency/SKILL.md` before writing or reviewing
  any git-touching script.

## Scope

This is a reference/checklist skill (judgment-based output), so it ships without
an eval-benchmark harness. If it grows scripts (e.g. a git-usage linter), add
them under `git-efficiency/scripts/` and an `evals/` set at that point.

> Moved to MandrakeWorkflows/skills/git-efficiency on 2026-10-15 (github.com/Lmandrake/MandrakeWorkflows). The standalone git_efficiency repo is archived.
