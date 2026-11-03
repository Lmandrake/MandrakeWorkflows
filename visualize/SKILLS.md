# Skills authored in this repo

Three families live here (Family B moved out on 2026-10-26). They are not one stack, and a session that
treats them as one will draw wrong conclusions about what depends on what.

| Family | Authored under | Count | Depends on the principle registry? |
|--------|----------------|-------|------------------------------------|
| A — visualization domain stack | `~/dev/MandrakeWorkflows/skills/<name>` | 7 | **Yes** — meaningless without it |
| C — BEAUTIFUL visualization pole | `~/dev/MandrakeWorkflows/skills/visual-beautiful` | 1 | Yes, plus `principles/modes.md` and `registry/renderers.yaml` |
| P — presentation (slides, animated pages) | `~/dev/MandrakeWorkflows/skills/visual-presentation` | 1 | Yes, the `motion.*` entries and `principles/conflicts.md` |

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

## Family P — presentation (`visual-presentation`)

The front door for slide decks and animated or scroll-driven HTML pages, added 2026-10-28
(`presentation/BRIEF.md`). It carries technical-presentation's slide rules unchanged as its
static-slide core and decides when motion earns its place from `motion.01`-`motion.29`.
`visual-intent` hands off to it when the medium is slides or an animated page. Its motion rules are
grounded in research but not yet validated: two model-judge rounds hit the ceiling and the owner's
blind rating is n=1 (`evaluation/runs/2026-10-28-motion/`). technical-presentation stays live
until the trigger test (`evals/trigger/visual-presentation.json`) has run; then it is retired.

## Rules for anything added here

- `SKILL.md` stays under 250 lines; the frontmatter `description` is ≥100 chars and
  the `name` matches its directory.
- Cite repo files by absolute `~/dev/MandrakeWorkflows/visualize/...` (or `~/dev/MandrakeWorkflows/skills/...`) path — these skills fire
  from other projects, so relative paths break.
- Cite **only git-tracked files**. Never local-only or ignored directories. This is enforced mechanically.
- Never name a renderer or toolkit; ask for the capability by property (D6, D9).
- Run `python3 tools/check_skills.py` before committing. With no arguments it checks
  **every** family; pass explicit roots to narrow it.

## Install

Clone MandrakeWorkflows to `~/dev/MandrakeWorkflows` (the skills cite their principle files under
`~/dev/MandrakeWorkflows/visualize`) and symlink each skill directory into `~/.claude/skills/`:

    for d in ~/dev/MandrakeWorkflows/skills/visual-* ~/dev/MandrakeWorkflows/skills/scientific-visualization; do
      ln -s "$d" ~/.claude/skills/"$(basename "$d")"
    done

New skills are only discovered at session start, so open a fresh session to confirm they load.
