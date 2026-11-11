# Relentless Pipeline

RimMandrake workers support `"runner": "codex"` in `relentless_rules.json` (default `claude`), with existing lease, proof and verdict validation.
See [runner setup](../tools/RUNNERS.md); quota/auth failures stop without a Claude fallback.

A fire-and-forget pipeline: point it at a modest goal and trust it to get all the way there. Owner, 2026-11-01: *"Let's
finally solve this once and for all: a fire-and-forget agent you can point at a modest goal and trust it will get all
the way there."*

**Two parts, named apart so one can change without the other.** Owner, 2026-11-03: *"I would like to adopt the naming
convention: this is a Relentless Pipeline, and each worker is a Relentless-style Builder/Judge from MandrakeWorkflows.
That way we could swap in new workers later but the pipeline remains the same design."*

- **The Relentless Pipeline** (this page): a Ralph-style loop run as a service. The item lives on disk, a supervisor with
  no AI keeps going, and it staffs a fixed number of **places**. A place is one running slot, held by one worker.
- **The workers** that sit in those places: today, **Relentless-style Builders and Judges**, defined in
  [`workers/`](workers/README.md). A Builder works an item across as many disposable generations as it takes; a blind
  Judge, a fresh instance that never saw the work, decides done. A different worker style can take the places later;
  the pipeline's design stays the same.

## What the pipeline does

- Holds each item's state on disk, so a lost or replaced worker loses nothing the next one needs.
- Keeps its places filled from the queue, one item per Builder, in a private clone.
- Fences stale workers: a worker whose lease has gone cannot report, finish or push.
- Sends an item to a blind Judge only when the Builder's own checks pass, and closes it only on the Judge's verdict.
- Forces a change of approach after repeated failures of one class, and escalates what no worker can finish.

What a worker must do in its place, and the blindness contract between Builder and Judge, live in the worker definition,
not here.

First target and proving ground: RimMandrake (`Lmandrake/RimMandrake`), where the pipeline runs as
`rimflow/relentless.py` from `rm-relentless.timer`, its Builders as the `rm-builder` agent and its Judges as `rm-judge`.
Reuse is extraction only. Owner, 2026-11-01: generalization means "only extracting out RimMandrake-specific items, not
changing its design for re-use in any way." The design serves RimMandrake; project specifics sit in an adapter.

| File | What it holds |
|---|---|
| [`workers/README.md`](workers/README.md) | The workers: what a Relentless-style Builder/Judge is, and how another style could take its place |
| [`workers/BUILDER_JUDGE.md`](workers/BUILDER_JUDGE.md) | The worker definition: both modes and the blindness contract between them |
| [`DEFECTS.md`](DEFECTS.md) | Known defects of the pipeline and its workers, each with evidence and status. Judges read this |
| [`STRENGTHS.md`](STRENGTHS.md) | Known strengths and weaknesses, measured where possible |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |
| [`TRUST.md`](TRUST.md) | The numbers that say whether it can be trusted yet |

The lessons from running it are in the `relentless-pipeline` skill (`../skills/relentless-pipeline/SKILL.md`).

Rule for this folder: a claim about the pipeline or its workers carries its evidence, or says UNMEASURED.
