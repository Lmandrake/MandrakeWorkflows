# MandrakeWorkflows

A working collection for people who build with AI agents: 39 Claude Code skills (methods an agent
loads and follows), three tools that those methods lean on (two of them also ship a skill), and four
larger agent-system projects.
It is for anyone running Claude Code or a similar agent on real work who wants practices that
have already failed once and been rewritten, rather than advice written from first principles.

The collection is evidence-first. A skill says what it rests on, what was measured and on how many
cases, and where it has not been tested. Where a rule came from a measured incident, the skill
keeps the number.

## What is distinctive here

- **Rules that kept their incident.** `confident-wrong-numbers` is a catalogue of query shapes that
  return a plausible wrong number with no error (`grep -c` as an entry count, an all-None field from
  a misspelled key), each with the honest instrument. `claude-remote-control` records a measured 0%
  success rate for the tempting "please resume remote control" recovery and gives the procedure that
  works instead.
- **Evaluation you can believe.** `blind-evaluation`, `evaluation-independence`, `falsifiable-claims`
  and `validity-floors` are one connected discipline: blind the comparison, keep the builder away from
  the answer key, write the refutation condition first, gate on hard constraints before ranking.
- **Cheap context for agents.** Placard measured 14 of 14 factual questions answered at 7,088 input
  tokens against 37,738 for the original documents (one small synthetic folder, one model; see
  [`tools/placard/README.md`](tools/placard/README.md)).
- **Honesty gates for charts.** The visualization stack runs every candidate through 13 gates before
  anything is ranked, over a registry of about 90 principles from the visualization literature.
- **Modality** separates visible modes from mixture components and reports that they diverge on 15 of
  its 44 ground-truth cases ([`tools/modality/README.md`](tools/modality/README.md)).

Every skill is a directory under `skills/` with a `SKILL.md` (the instructions an agent loads) and,
where it has them, references, scripts, evals and tests.

## Catalogue

### Tools

| Folder | What it is |
|---|---|
| [`tools/placard/`](tools/placard/README.md) | Placard: a `*.placard.md` digest beside each deck, PDF or spreadsheet plus a recursive project map, so an agent reads the digest instead of the original. Skill: [`tools/placard/SKILL.md`](tools/placard/SKILL.md). |
| [`tools/waypoint/`](tools/waypoint/README.md) | Waypoint: project roots named once in a markdown table and rendered into the shell as `$NAME` variables, a `wp <name>` jump and a `launch <name>` runner (cd and start an agent session), with per-machine rows. Tables live in `$WAYPOINT_DATA` (default `~/.config/waypoint`); starters are in `tools/waypoint/examples/`. Skill: [`tools/waypoint/.claude/skills/waypoint/SKILL.md`](tools/waypoint/.claude/skills/waypoint/SKILL.md). |
| [`tools/modality/`](tools/modality/README.md) | Modality: estimates how multimodal a distribution is, from an analytic description or samples, reporting visible modes and BIC-selected mixture components separately. A Python package (`pip install -e tools/modality`). |

### Projects

| Folder | What it is |
|---|---|
| [`designer/`](designer/README.md) | **The Designer** (name provisional): a Socratic agent that argues a design into shape with its owner before anything is built, then writes what must be true so a builder and a judge cannot misread it. Definition, defects, version history. |
| [`relentless/`](relentless/README.md) | **Relentless Pipeline**: a fire-and-forget pipeline for modest goals, and the **Relentless-style Builder/Judge** workers that fill its places ([`relentless/workers/`](relentless/workers/README.md)): definition, blindness contract, known defects, version history. |
| [`artisan/`](artisan/README.md) | **Artisan** (experimental): one agent takes one whole piece of work to something it would show its owner. It is given the experience in the owner's words, told to be creative, and sent back when he looks and says no. Findings, policies, templates and field records, agnostic to any project. |
| [`whittle/`](whittle/README.md) | **Whittle** (untested): Artisan's finish line in one interactive session, for work of about a person-day. A frozen statement, evidence per line, a fresh judge and a broaden call, enforced by a Stop hook instead of a shell loop. |
| [`augur/`](augur/DESIGN.md) | **Augur**: one small macOS background producer that measures the machine once (load, network, VPN, agent sessions, projects) and writes one versioned snapshot file that several consumers read instead of each measuring on its own. Design, JSON schema, LaunchAgent plists, tests. |
| [`sprites/`](sprites/README.md) | **Sprites**: luminous desktop creatures, one per Claude Code session, that encode session and machine load. Prototypes, gallery, spec. |

### Skills

#### Evaluation and judgment

| Skill | What it does |
|---|---|
| [`blind-evaluation`](skills/blind-evaluation/SKILL.md) | Run a head-to-head comparison you can believe: blinding, balanced positions, a control that could have won, honest small-n reading. |
| [`evaluation-independence`](skills/evaluation-independence/SKILL.md) | Keep what builds a thing apart from what grades it, so a result is not contaminated by contact with its own answer key. |
| [`falsifiable-claims`](skills/falsifiable-claims/SKILL.md) | Write the refutation condition and pass bar before running, then word the result to match the evidence. |
| [`defeat-recitation`](skills/defeat-recitation/SKILL.md) | Rule out recitation before crediting a model's correct answer about material it may have memorised. |
| [`incomplete-ground-truth`](skills/incomplete-ground-truth/SKILL.md) | Score against a reference that asserts some answers and denies none, without reading its silence as a negative. |
| [`mutate-your-checker`](skills/mutate-your-checker/SKILL.md) | Before trusting a new test, grader or gate, plant faults and must-stay-green cases and watch it go red and stay green. |
| [`validity-floors`](skills/validity-floors/SKILL.md) | Gate on hard constraints before ranking on soft criteria, so a beautiful invalid option cannot win. |
| [`option-portfolio`](skills/option-portfolio/SKILL.md) | Answer "give me a few options" with a set that covers genuinely different questions, not three near-duplicates. |
| [`knowledge-registry`](skills/knowledge-registry/SKILL.md) | Structure admitted knowledge: stable ids, a fixed force vocabulary, testable checks, versions, a decision log. |
| [`search-when-words-differ`](skills/search-when-words-differ/SKILL.md) | Find relevant passages when the question and the sources use different words, before reporting "nothing found". |
| [`confident-wrong-numbers`](skills/confident-wrong-numbers/SKILL.md) | Catch a query whose shape returns a plausible wrong number (a count, a zero, an empty list, an all-None field) before it leaves your hands. |
| [`measuring-large-artifacts`](skills/measuring-large-artifacts/SKILL.md) | Take a number from a file too large to read whole (dumps, logs, exports) with a parser, not grep and wc. |

#### Agent coordination and long-running work

| Skill | What it does |
|---|---|
| [`deep-design-3x2`](skills/deep-design-3x2/SKILL.md) | Harden a design: three real options, a second model answering blind before it critiques, a re-measure of the claims the pick rests on. |
| [`parallel-agent-worktrees`](skills/parallel-agent-worktrees/SKILL.md) | Run several coding agents against one repository without cross-contamination. |
| [`git-efficiency`](skills/git-efficiency/SKILL.md) | Use git from scripts and agents cheaply and safely: batched calls, no whole-index sweeps, lock-aware. |
| [`artisan`](skills/artisan/SKILL.md) | Set up, guide, watch and judge a shell-loop agent on one whole piece of work the owner can look at. Early: no acceptances yet. |
| [`whittle`](skills/whittle/SKILL.md) | Size a job (too small, Whittle, or Artisan) and set up one interactive session that may not stop until evidence per line, a fresh judge and a broaden call say it's done. Untested. |
| [`resumable-batch-jobs`](skills/resumable-batch-jobs/SKILL.md) | Make long batch jobs safe to resume, so a retry never silently skips failed items or duplicates done ones. |
| [`claude-remote-control`](skills/claude-remote-control/SKILL.md) | Keep a multi-window Claude Code fleet reachable from the phone (Remote Control): why windows drop off, why a peer relay cannot fix it, and recovery without losing work. |

#### Human decision interfaces

| Skill | What it does |
|---|---|
| [`question-card`](skills/question-card/SKILL.md) | Put a choice to a human: genuinely different options, trade-offs both ways, plain labels, always a write-in line. |
| [`review-sheets`](skills/review-sheets/SKILL.md) | Hand a human an HTML sheet to keep/cut, rank or grade hundreds of items, with decisions captured as data. |
| [`ideogram`](skills/ideogram/SKILL.md) | Write self-checking documents (an ask, a brief, a handoff, a record) a reader can converse with and test a response against. |

#### Communication

| Skill | What it does |
|---|---|
| [`visual-presentation`](skills/visual-presentation/SKILL.md) | Slide decks and animated HTML pages: claim titles, and when motion earns its place. Replaces technical-presentation. |
| [`meeting-postbrief`](skills/meeting-postbrief/SKILL.md) | Turn a technical meeting into a one-page findings sheet: the terms it needed, the plan against the real need, ways forward with workday estimates. |
| [`relevant-transcripts`](skills/relevant-transcripts/SKILL.md) | Pair every meeting transcript with one written summary and name them consistently; includes a summary-fidelity scorer. Filing into a shared archive is paused by its owner; the conventions and scorer still apply. |
| [`engaging-survey`](skills/engaging-survey/SKILL.md) | Design surveys busy people want to answer: decisions first, honest length, neutral questions, energy in the framing. |

#### Visualization

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

#### Media

| Skill | What it does |
|---|---|
| [`image_scaling`](skills/image_scaling/SKILL.md) | Downscale sprites and small images so they stay recognisable, measured against a calibrated human eye. |

## Install

Claude Code loads any skill directory found under `~/.claude/skills/`. Clone the repository and
symlink the skills you want:

```sh
git clone https://github.com/Lmandrake/MandrakeWorkflows.git
cd MandrakeWorkflows
mkdir -p ~/.claude/skills
for s in skills/*/; do ln -s "$(pwd)/$s" ~/.claude/skills/"$(basename "$s")"; done
```

The tool skills are linked separately: `ln -s "$(pwd)/tools/placard" ~/.claude/skills/placard` and `ln -s "$(pwd)/tools/waypoint/.claude/skills/waypoint" ~/.claude/skills/waypoint`.
Or link only one: `ln -s "$(pwd)/skills/question-card" ~/.claude/skills/question-card`. A symlink
keeps the skill current when you `git pull`. Skills that ship scripts need only Python 3 and the
standard library; `deep-design-3x2` uses a second model when one is available (see below) and
says what to do when it is not.

A few tools carry their own `*.plist` under this repo and are **not installed by cloning or
symlinking**: `augur/launchd/com.mandrake.augur.plist` and
`augur/launchd/com.mandrake.augur.check24h.plist` (installer: `augur/bin/install.sh`, label
`com.mandrake.augur` by default, `AUGUR_LABEL=com.mandrake.augur.check24h` for the 24h checker —
`com.mandrake.augur` is currently installed in `~/Library/LaunchAgents/`, the
`.check24h` variant is not), and `sprites/app/macos/com.mandrake.sprites.plist` (currently
installed as `com.mandrake.sprites`). Nothing auto-installs either; `tools/modality` is the one
component with its own `pyproject.toml` (`cd tools/modality && pip install -e .`), everything else
here needs only Python 3 and the standard library, per the Check it commands above. No
credential, token, or login layer was found in this repo's own files.

*Detected 2026-11-10, not verified by running it.*

## Check it

```sh
python3 tests/test_skills.py        # every SKILL.md has a name and description, and no dangling relative links
python3 -m pytest -q tests skills   # the same, plus each skill's own tests (needs pytest and git)
(cd tools/placard && python3 -m pytest -q)               # Placard
(cd tools/waypoint && python3 -m pytest -q tests)        # Waypoint
(cd tools/modality && pip install -e . pytest && OMP_NUM_THREADS=1 python3 -m pytest -q)   # Modality (numpy, scipy, scikit-learn)
(cd visualize && python3 -m pytest -q tests && python3 tools/check_skills.py)   # visualization stack
```

## Related repositories

- **[EvidenceBoundPapers](https://github.com/Lmandrake/EvidenceBoundPapers)** holds the
  verification suite these skills point to: `claim-provenance`, `grader-validation` and
  `verify-model-quotes`.
- **[Dispatch](https://github.com/Lmandrake/Dispatch)** routes work across models and harnesses from
  measured evidence, and carries the `chatgpt-consult` second-opinion provider that
  `deep-design-3x2` uses for its blind pass.

## Credit

Please credit me if you find this work useful.
