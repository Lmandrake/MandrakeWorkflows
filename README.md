# MandrakeWorkflows

Methods for working with AI agents, written as [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills),
plus two tools those methods lean on: **Placard**, sidecar digests that make a folder of decks,
PDFs and spreadsheets cheap for a model to read, and a **visualization stack** of eight skills
grounded in the published literature.
Each one is a practice that was used on real work, failed somewhere first, and was rewritten until
the failure could not recur. The collection is evidence-first: a skill says what it rests on, what
was measured and on how many cases, and where it has not been tested. Where a rule came from a
measured incident, the skill keeps the number.

Every skill is a directory under `skills/` with a `SKILL.md` (the instructions an agent loads) and,
where it has them, references, scripts, evals and tests.

## Projects

| Folder | What it is |
|---|---|
| [`designer/`](designer/README.md) | **The Designer** (name provisional): a Socratic agent that argues a design into shape with its owner before anything is built, then writes what must be true so a builder and a judge cannot misread it. Definition, defects, version history. |
| [`relentless/`](relentless/README.md) | **Relentless Pipeline**: a fire-and-forget pipeline for modest goals, and the **Relentless-style Builder/Judge** workers that fill its places ([`relentless/workers/`](relentless/workers/README.md)): definition, blindness contract, known defects, version history. |
| [`augur/`](augur/DESIGN.md) | **Augur**: one small macOS background producer that measures the machine once (load, network, VPN, agent sessions, projects) and writes one versioned snapshot file that several consumers read instead of each measuring on its own. Design, JSON schema, LaunchAgent plists, tests. |
| [`sprites/`](sprites/README.md) | **Sprites**: luminous desktop creatures, one per Claude Code session, that encode session and machine load. Prototypes, gallery, spec. |

## The skills

### Evaluation and judgment

| Skill | What it does |
|---|---|
| [`blind-evaluation`](skills/blind-evaluation/SKILL.md) | Run a head-to-head comparison you can believe: blinding, balanced positions, a control that could have won, honest small-n reading. |
| [`evaluation-independence`](skills/evaluation-independence/SKILL.md) | Keep what builds a thing apart from what grades it, so a result is not contaminated by contact with its own answer key. |
| [`falsifiable-claims`](skills/falsifiable-claims/SKILL.md) | Write the refutation condition and pass bar before running, then word the result to match the evidence. |
| [`defeat-recitation`](skills/defeat-recitation/SKILL.md) | Rule out recitation before crediting a model's correct answer about material it may have memorised. |
| [`incomplete-ground-truth`](skills/incomplete-ground-truth/SKILL.md) | Score against a reference that asserts some answers and denies none, without reading its silence as a negative. |
| [`validity-floors`](skills/validity-floors/SKILL.md) | Gate on hard constraints before ranking on soft criteria, so a beautiful invalid option cannot win. |
| [`option-portfolio`](skills/option-portfolio/SKILL.md) | Answer "give me a few options" with a set that covers genuinely different questions, not three near-duplicates. |
| [`knowledge-registry`](skills/knowledge-registry/SKILL.md) | Structure admitted knowledge: stable ids, a fixed force vocabulary, testable checks, versions, a decision log. |
| [`search-when-words-differ`](skills/search-when-words-differ/SKILL.md) | Find relevant passages when the question and the sources use different words, before reporting "nothing found". |

### Agent coordination and long-running work

| Skill | What it does |
|---|---|
| [`deep-design-3x2`](skills/deep-design-3x2/SKILL.md) | Harden a design: three real options, a second model answering blind before it critiques, a re-measure of the claims the pick rests on. |
| [`parallel-agent-worktrees`](skills/parallel-agent-worktrees/SKILL.md) | Run several coding agents against one repository without cross-contamination. |
| [`git-efficiency`](skills/git-efficiency/SKILL.md) | Use git from scripts and agents cheaply and safely: batched calls, no whole-index sweeps, lock-aware. |
| [`resumable-batch-jobs`](skills/resumable-batch-jobs/SKILL.md) | Make long batch jobs safe to resume, so a retry never silently skips failed items or duplicates done ones. |

### Human decision interfaces

| Skill | What it does |
|---|---|
| [`question-card`](skills/question-card/SKILL.md) | Put a choice to a human: genuinely different options, trade-offs both ways, plain labels, always a write-in line. |
| [`review-sheets`](skills/review-sheets/SKILL.md) | Hand a human an HTML sheet to keep/cut, rank or grade hundreds of items, with decisions captured as data. |
| [`ideogram`](skills/ideogram/SKILL.md) | Write self-checking documents (an ask, a brief, a handoff, a record) a reader can converse with and test a response against. |

### Communication

| Skill | What it does |
|---|---|
| [`visual-presentation`](skills/visual-presentation/SKILL.md) | Slide decks and animated HTML pages: claim titles, and when motion earns its place. Replaces technical-presentation. |
| [`meeting-postbrief`](skills/meeting-postbrief/SKILL.md) | Turn a technical meeting into a one-page findings sheet: the terms it needed, the plan against the real need, ways forward with workday estimates. |
| [`engaging-survey`](skills/engaging-survey/SKILL.md) | Design surveys busy people want to answer: decisions first, honest length, neutral questions, energy in the framing. |

### Visualization

Eight skills that route a chart from intent to a checked render, over a registry of about 90
principles drawn from the visualization literature (`visualize/principles/principles.yaml`) and 13
honesty gates that every candidate must clear before anything is ranked
(`visualize/evaluation/RUBRIC.md`). Two poles share one truth floor: CLEAR (communication plus
clarity) and BEAUTIFUL (communication plus beauty). Design: `visualize/DESIGN.md`; validation:
`visualize/VALIDATION.md`.

| Skill | What it does |
|---|---|
| [`visual-intent`](skills/visual-intent/SKILL.md) | The front door: intent, audience, data and task, then a chart family chosen from the analytic relationship. |
| [`visual-encoding`](skills/visual-encoding/SKILL.md) | Map data to marks and channels by perceptual accuracy. |
| [`visual-composition`](skills/visual-composition/SKILL.md) | Layout, hierarchy, annotation and the shared style rules. |
| [`scientific-visualization`](skills/scientific-visualization/SKILL.md) | Uncertainty, scales and domain conventions for scientific figures. |
| [`visual-render-qa`](skills/visual-render-qa/SKILL.md) | Inspect the actual rendered artifact at final size against the hard gates. |
| [`visual-critic`](skills/visual-critic/SKILL.md) | Orchestrate the stack end to end, or grade an existing visual against the rubric. |
| [`visual-portfolio`](skills/visual-portfolio/SKILL.md) | Produce a set of genuinely different candidates, each over the validity floor. |
| [`visual-beautiful`](skills/visual-beautiful/SKILL.md) | The BEAUTIFUL pole: striking data visuals that keep the truth floor. |

### Media

| Skill | What it does |
|---|---|
| [`image_scaling`](skills/image_scaling/SKILL.md) | Downscale sprites and small images so they stay recognisable, measured against a calibrated human eye. |

## Placard

`tools/placard/` writes a `*.placard.md` digest beside each expensive artifact and a recursive
project map, so an agent reads the digest instead of the original. On the shipped synthetic example
(a report, a deck with speaker notes, a workbook), the same model answered the same 14 factual
questions under six conditions, three runs each, scored mechanically. The map and digests passed
**14 of 14** in every run at 7,088 input tokens, and the mechanically extracted bodies alone passed
14 of 14 at 3,675, against 37,738 for the originals as native document input. It is one small
synthetic folder and one model, a demonstration of the workflow rather than a benchmark; the
details and caveats are in [`tools/placard/README.md`](tools/placard/README.md). Its skill is
`tools/placard/SKILL.md`.

## Waypoint

`tools/waypoint/` names your project roots once, in a markdown table, and renders them into your
shell as `$NAME` variables, a `wp <name>` jump and a `launch <name>` runner (cd and start a
command, such as an agent session), with per-machine rows for paths that differ between machines.
The tables live outside the repo, in `$WAYPOINT_DATA` (default `~/.config/waypoint`); starter
tables are in `tools/waypoint/examples/`. Details in
[`tools/waypoint/README.md`](tools/waypoint/README.md); its skill is
`tools/waypoint/.claude/skills/waypoint/`.

## Install

Claude Code loads any skill directory found under `~/.claude/skills/`. Clone the repository and
symlink the skills you want:

```sh
git clone https://github.com/Lmandrake/MandrakeWorkflows.git
cd MandrakeWorkflows
mkdir -p ~/.claude/skills
for s in skills/*/; do ln -s "$(pwd)/$s" ~/.claude/skills/"$(basename "$s")"; done
```

Placard's skill is the tool directory itself: `ln -s "$(pwd)/tools/placard" ~/.claude/skills/placard`.
Or link only one: `ln -s "$(pwd)/skills/question-card" ~/.claude/skills/question-card`. A symlink
keeps the skill current when you `git pull`. Skills that ship scripts need only Python 3 and the
standard library; `deep-design-3x2` uses a second model when one is available (see below) and
says what to do when it is not.

## Check it

```sh
python3 tests/test_skills.py        # every SKILL.md has a name and description, and no dangling relative links
python3 -m pytest -q tests skills   # the same, plus each skill's own tests (needs pytest and git)
(cd tools/placard && python3 -m pytest -q)               # Placard
(cd tools/waypoint && python3 -m pytest -q tests)        # Waypoint
(cd visualize && python3 -m pytest -q tests && python3 tools/check_skills.py)   # visualization stack
```

## Related repositories

- **[EvidenceBoundPapers](https://github.com/Lmandrake/EvidenceBoundPapers)** holds the
  verification suite these skills point to: `claim-provenance`, `grader-validation`,
  `confident-wrong-numbers`, `verify-model-quotes` and `measuring-large-artifacts`.
- **[Dispatch](https://github.com/Lmandrake/Dispatch)** routes work across models and harnesses from
  measured evidence, and carries the `chatgpt-consult` second-opinion provider that
  `deep-design-3x2` uses for its blind pass.

## Credit

Please credit me if you find this work useful.
