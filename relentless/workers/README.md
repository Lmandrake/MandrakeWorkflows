# Relentless-style workers: Builder and Judge

The workers that fill the [Relentless Pipeline](../README.md)'s places. Owner, 2026-11-03: *"each worker is a
Relentless-style Builder/Judge from MandrakeWorkflows. That way we could swap in new workers later but the pipeline
remains the same design."*

One definition, two modes, never the same instance:

- **Builder:** works one item toward its proof of done. Each generation starts in a fresh context and reads what it
  needs from disk.
- **Judge:** a fresh instance with no access to the Builder's memory. It judges the result, not the effort.

The definition, with the blindness contract that binds both modes, is [`BUILDER_JUDGE.md`](BUILDER_JUDGE.md).

## What any worker in a place must honour

These are the pipeline's terms. A new worker style may change everything else.

- It works one item, and only while its lease holds; a refused report means the lease has gone and it stops at once.
- Everything it knows is on disk when it stops: the next worker in the place starts from that, not from it.
- It reports through the pipeline's verbs only and never sets the item's final state; the Judge's verdict closes it.
- A Builder never sets, holds or marks its own exam.

In RimMandrake the Builder runs as the `rm-builder` agent and the Judge as `rm-judge` (named by `worker_agent` and
`checker_agent` in `rimflow/relentless_rules.json`). Swapping in another worker means pointing those names at it.
