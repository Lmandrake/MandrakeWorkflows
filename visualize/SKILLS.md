# Skills authored in this repo

Two families live here (a third, Family B, moved out on 2026-10-26). They are not one stack, and a session that
treats them as one will draw wrong conclusions about what depends on what.

| Family | Authored under | Count | Depends on the principle registry? |
|--------|----------------|-------|------------------------------------|
| A — visualization domain stack | `skills/v0.1/<name>` | 7 | **Yes** — meaningless without it |
| C — BEAUTIFUL visualization pole | `skills/beautiful/<name>` | 1 | Yes, plus `principles/modes.md` and `registry/renderers.yaml` |

## Family A — the visualization domain stack (`visual-*`, `scientific-visualization`)

Seven skills implementing a convergent critic plus a divergent portfolio layer for
visual communication. They cite stable principle ids that resolve in
`principles/principles.yaml`, and they are meaningless without that registry.
Evaluated by a 6-case ablation and a 36-case blind bake-off; `visual-portfolio`
was the exception and has since been dogfooded end to end once (n=1,
`evaluation/runs/2026-09-03-dogfood/DOGFOOD.md`). 

`visual-intent` is the stack's **mandatory front door** — the others assume the
audience, decision, and single takeaway have already been fixed.

## Family B — the epistemic method (moved out)

The ten domain-independent method skills once authored here (blind-evaluation, falsifiable-claims,
validity-floors and others) are not about visualization and live in separate repositories.

## Family C — the BEAUTIFUL pole (`visual-beautiful`)

The sibling of Family A: communication plus beauty, where Family A is communication plus
clarity. `visual-intent` hands off to it. It shares Family A's truth floor and gates
through `principles/modes.md`, and asks for renderers by property through
`registry/renderers.yaml`. Its style rules come from rated rounds of the DataArt studies;
they are formative, not validated by blind readers.

## Rules for anything added here

- `SKILL.md` stays under 250 lines; the frontmatter `description` is ≥100 chars and
  the `name` matches its directory.
- Cite repo files by absolute `~/dev/MandrakeVisualize/...` path — these skills fire
  from other projects, so relative paths break.
- Cite **only git-tracked files**. Never local-only or ignored directories. This is enforced mechanically.
- Never name a renderer or toolkit; ask for the capability by property (D6, D9).
- Run `python3 tools/check_skills.py` before committing. With no arguments it checks
  **every** family; pass explicit roots to narrow it.

## Install

Clone the repo to `~/dev/MandrakeVisualize` (the skills cite their principle files by that path)
and symlink each skill directory into `~/.claude/skills/`:

    for d in ~/dev/MandrakeVisualize/skills/v0.1/* ~/dev/MandrakeVisualize/skills/beautiful/*; do
      ln -s "$d" ~/.claude/skills/"$(basename "$d")"
    done

New skills are only discovered at session start, so open a fresh session to confirm they load.
