# Benchmark plan

How to tell whether the skill stack actually produces better visuals — and whether
changes to it are improvements or regressions.

## Goal
Turn the rubric and taxonomy into a repeatable measurement, so v0.2+ edits are
judged against evidence rather than taste.

## v0.1 scope (now)
- **6 behavioral test cases** (TEST_CASES.md), each pinned to specific hard gates.
  Pass criterion: the expected gate(s) fire and the final SHIP artifact meets the
  stated correct outcome. This validates that the *gates and routing work*, not
  aesthetic quality.
- Run manually through `visual-critic`; record route, gates fired, verdict, and
  read-back match in a results table.

## v0.2 scope (planned)
- Expand to the **full 12-case suite** with dedicated cases for G2, G7, G10 and for
  Level 1/2/7 failures (which the render cannot catch — tested via read-back).
- **Ablation:** run each case with the stack vs. a naive "just make a chart" baseline;
  compare hard-gate pass rates and rubric scores.
- **Inter-rater reliability:** have the rubric scored by the critic and by a human on
  the same artifacts; measure agreement. Low agreement flags an ambiguous rubric line.
- **Regression harness:** freeze the 12 cases + expected verdicts; any skill/registry
  edit must not regress a previously-passing case without a recorded rationale.

## Validation set (later, cross-track)
A set of accepted exemplar decks is the
**held-out validation set**, not training input. Use them to check that the stack's
judgments do not contradict a designer's validated work: score a sample of exemplar
slides with the rubric and investigate any that the stack would REPAIR. A systematic
conflict is a signal to revisit a principle's force/tier or add a context exception —
not automatically to overrule the exemplar (see README separate-track rationale).

## Metrics
- Hard-gate precision/recall: does the stack fire gates when it should and not when
  it should not? (False positives are as costly as misses — they erode trust.)
- Rubric-score delta vs. baseline on matched cases.
- Read-back match rate (proxy for Level 7 communication success).
- Repair convergence: number of gate→repair→re-render cycles to SHIP.

## What would falsify a principle's placement
- A hard MUST/AVOID that fires on artifacts domain experts judge correct → downgrade
  to SHOULD or add a context exception (log in conflicts.md / DECISIONS.md).
- A SHOULD that never affects outcomes → candidate for removal as noise.
- A gate with poor inter-rater agreement → rewrite its check to be mechanical.

## Cadence
Run the 6 cases before every tagged version. Run the full v0.2 suite + ablation at
each minor version. Re-score the validation-set sample when any Tier-A principle's
force changes.
