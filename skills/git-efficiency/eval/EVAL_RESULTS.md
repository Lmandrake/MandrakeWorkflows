# git-efficiency skill — evaluation (iteration 1, 2026-09-13)

Method: three realistic git tasks, each run by an independent subagent **with**
the skill and **without** it (baseline), outputs graded by direct reading against
objective assertions. Sonnet on both arms.

## Results

| eval | task | with-skill | baseline | verdict |
|---|---|---|---|---|
| eval-rename | write a batch-rename-and-stage script (~50 dirs, slow mount, shared repo) | `os.replace` moves + **one** batched `git add`, lock taken once at end | **`git mv` per rename** (~50 spawns + 50 lock cycles on the shared repo) | **skill wins decisively** — flips the exact S1+E2 anti-pattern to the batched fix |
| eval-status | last-commit-hash + staged-state for ~200 files | single `git log --name-only` walk + one `git diff --cached`; rev-parse once; stderr unsuppressed | single `git log --name-only` walk + one `git diff --cached` | **tie (non-discriminating)** — baseline already knew the batched pattern; skill neutral, no regression |
| eval-audit | find git defects in a deliberately-bad script (7 planted) | **7/7** planted defects, correctly prioritized, names the shared-repo **entanglement** danger 3× | found the 7 but reframed the most dangerous (bare commit = whole-index sweep) as a cosmetic "non-descriptive message" issue; entanglement named only 1×; padded to "11" with minor/stylistic items | **skill wins on quality** — count inflated by noise; skill prioritizes the cross-agent safety risk correctly |

## Conclusion

The skill **measurably improves git code where it matters** — it converts the
single most impactful real-world case (per-row `git mv` → filesystem-move +
batched add) and makes reviews correctly weight cross-agent entanglement over
cosmetic findings — and is **harmless where the model already knows the batched
pattern** (the status task). That is the ideal profile for a machine-wide
reference skill: helps on the failure modes, neutral otherwise. **Cleared for
activation.**

Raw outputs under `git-efficiency-workspace/iteration-1/`.

## Grader validity (2026-10-15)

`git-efficiency-workspace/grade.py` greps source for keywords; it does not
execute outputs. Its rename checks were tightened (per-file `add` loops and safe
`commit -m ... -- paths` are now graded correctly, see
`../tests/test_review_2026_10_15.py`), but **`grade_audit` verdicts are
unvalidated**: a review that denies every defect still scores 7/7. The audit
verdict above rests on direct reading, not the grader.
