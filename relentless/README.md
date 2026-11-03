# Relentless Agent

A fire-and-forget agent: point it at a modest goal and trust it to get all the way there. Owner, 2026-11-01: *"Let's
finally solve this once and for all: a fire-and-forget agent you can point at a modest goal and trust it will get all
the way there."*

It is a Ralph-style loop run as a service. The item lives on disk, workers are disposable, a supervisor keeps going, and
a blind Judge decides done. First target and proving ground: RimMandrake (`Lmandrake/RimMandrake`, where it runs as
`rimflow/relentless.py`). Reuse is extraction only. Owner, 2026-11-01: generalization means "only extracting out RimMandrake-specific
items, not changing its design for re-use in any way." The design serves RimMandrake; project specifics sit in an adapter.

| File | What it holds |
|---|---|
| [`agent/RELENTLESS_AGENT.md`](agent/RELENTLESS_AGENT.md) | The definition: both modes and the blindness contract between them |
| [`DEFECTS.md`](DEFECTS.md) | Known defects, each with evidence and status. Judge mode reads this |
| [`STRENGTHS.md`](STRENGTHS.md) | Known strengths and weaknesses, measured where possible |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history of the agent's growth |
| [`TRUST.md`](TRUST.md) | The numbers that say whether it can be trusted yet |

Rule for this folder: a claim about the agent carries its evidence, or says UNMEASURED.
