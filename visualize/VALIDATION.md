# Visualization stack validation record

MandrakeVisualize was folded into MandrakeWorkflows on 2026-10-27 by `git subtree add` (history
kept) from `Lmandrake/MandrakeVisualize` at commit `5b0c221`. Its eight skills moved to
`../skills/`. The suite was not re-run to prove the move; these are the records it already had.

- **Docker smoke of the public export** (python:3.12-slim: `pytest -q`, `tools/check_skills.py`),
  measured 2026-10-26 on MandrakeVisualize `1c77da1`: pass. Scan 0 blocking.
- **Export scan**: `publish.py scan MandrakeVisualize` passed on 2026-10-28T01:27:06Z (108 files).
- **Behavioral evals it already ships**: `evals/behavior/v2/DEV_RESULTS.md` and
  `evals/behavior/v2/CONFIRM_RESULTS.md` (validity-floors, 120 tasks x 3 arms, pre-registered in
  `confirm/PREREG.md`); `evals/behavior/viz-gates/PREREG.md` with its runs; the bake-off and
  triptych records under `evaluation/runs/`.
- **Registry**: `principles/principles.yaml` holds 92 principles; `evaluation/RUBRIC.md` defines 13
  honesty gates (G1 to G13).

After the move, `tools/check_skills.py` (its default roots), `tests/test_check_skills.py` and
`evals/behavior/viz-gates/run.py` (skill source paths) changed. On 2026-10-27, `tests/` passed 19 of
19 and `tools/check_skills.py` passed all 8 skills.
