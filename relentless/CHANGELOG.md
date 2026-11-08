# Version history

## v0.3 (2026-11-06): the exam is set before Build and validated before it counts

- `workers/BUILDER_JUDGE.md`: Setter writes the exam at the base sha; the pipeline VALIDATEs it (assertion reds only, no
  existence-only behavioural checks, no deleting breaks, item-sentence maps, exam_hash over named files); hold-outs move
  to the Marker at mark time. RimMandrake ships it in shadow (`relentless_exam.py`, WP-03 of the 2026-11-06 redesign).

## v0.2 (2026-11-03): pipeline and workers named apart

- Owner, 2026-11-03: the system is the **Relentless Pipeline**; each worker in its places is a **Relentless-style
  Builder/Judge** from MandrakeWorkflows, so workers can be swapped later while the pipeline keeps its design.
- README split: `README.md` is the pipeline; `workers/README.md` and `workers/BUILDER_JUDGE.md` (was
  `agent/RELENTLESS_AGENT.md`) are the workers.

## v0.1 (2026-11-01): designed and attacked

- Full design in RimMandrake `design/RimMandrake/relentless_agent_design_2026-11-01.md`; GPT attacked it; the Conductor judged each finding.
- Movement redefined: only contract clauses going green count. Setter and Marker named. Marker plans before reading Build's route.
- Tried rows prohibit nothing; a repeat must state what differs.

## v0 (2026-11-01): named and given a home

- Live in RimMandrake since 2026-10-31 as `rm-relentless.timer`: item on disk, replaceable workers, filler staffing,
  blind check at the end.
- Named the Relentless Agent by the owner, 2026-11-01. This folder created to track its growth.
- Blindness contract written into the definition.
- Memory design recorded: result cache by hash, tried-and-failed table, capped rewritten state.
- Reuse ruled to be extraction only, never a design change.
- 2026-11-01: step 0 partly landed: seed bank, counting rules, `relentless trust`; E1 picked (42 cases), no baseline yet. Step 1: wall profile and box published report-only, proved live by probe (d18b79dc77, 06fd8dece7, 7f620fdee0).
