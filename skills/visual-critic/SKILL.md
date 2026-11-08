---
name: visual-critic
description: >
  Orchestrator and judge for the visual-reasoning stack. Use to run an end-to-end
  visualization task (routing through intent → encoding → composition →
  scientific-visualization → render-qa) OR to critique/grade an existing visual
  against the failure taxonomy and rubric. Invokes the other skills; it does not
  duplicate their rules.
---

# Visual Critic (orchestrator)

## Purpose
Drive the whole reasoning sequence and adjudicate the result. The critic decides
which skills to invoke and in what order, holds the shared artifact state, applies
the failure taxonomy and the scoring rubric, and owns the final SHIP decision. It
is the single place where the hard-vs-soft discipline (QA-01) is enforced across
skills.

## When to invoke
- For any nontrivial "make me a good visualization of X" request (end-to-end mode).
- To review, grade, or repair an existing figure/slide/diagram (critique mode).

## Inputs
- The user request and data, plus medium/audience if known.
- In critique mode, the existing artifact (rendered) to evaluate.

## Required intermediate representation
A **case file** that accumulates each skill's output:
```
intent_record        (from visual-intent)
encoding_table       (from visual-encoding)
fidelity_record      (from scientific-visualization, if scientific)
composition_plan     (from visual-composition)
qa_report            (from visual-render-qa)
failure_scan         (which of the 7 levels are implicated)
rubric_score         (100-pt, with hard-gate result)
verdict
```

## Procedure
1. **Route.** Always start with `visual-intent`. Then `visual-encoding`. If the
   subject is scientific/spatial/network/diagram/map, invoke
   `scientific-visualization` in parallel with encoding/composition. Then
   `visual-composition`. Then `visual-render-qa`. Do not re-implement their rules
   here — call them and collect their outputs into the case file.
2. **Follow the reasoning sequence** (do not skip levels): intent → abstraction →
   task → representation → encoding → hierarchy → composition → annotation → style →
   render → inspect → repair (S01 nested-model discipline; CRIT-01/02/06).
3. **Failure scan.** Locate any defect at the correct of the seven failure levels:
   (1) wrong problem, (2) wrong abstraction, (3) wrong encoding, (4) wrong
   composition, (5) wrong scientific representation, (6) physical-rendering defect,
   (7) wrong communication strategy. Fixing a defect at the wrong level wastes
   effort (CRIT-06).
4. **Gate then score.** Take the `qa_report`. If any hard gate failed (QA-02),
   the verdict is REPAIR regardless of rubric score — route the prescribed fix to
   the owning skill and re-run render-qa. Only once all hard gates pass, compute the
   soft rubric score to choose among valid alternatives (QA-01/03).
5. **Justify** each nontrivial choice against a principle or evidence (CRIT-01), and
   when presenting a result as good, say what makes it work (CRIT-03).
6. **Escalate** genuinely context-dependent decisions (UNC-01 baseline; contested
   rules per CRIT-04) to the user rather than resolving silently.
7. **Verdict:** SHIP / REPAIR (with the level + owning skill named) / ESCALATE.

### Rubric (100 pts; soft ranking only — hard gates are pass/fail and override)
Semantic fidelity 25 · Scientific/quantitative integrity 20 · Perceptual
effectiveness 15 · Layout/render integrity 15 · Communication hierarchy 10 ·
Accessibility 5 · Medium fitness 5 · Aesthetic coherence 5. A hard-gate failure
(see `visual-render-qa` step 2) blocks SHIP no matter the score.

## Hard constraints
- QA-01, QA-02 (MUST): validity gate precedes and overrides scoring.
- CRIT-02 (MUST): the evaluation method must match the level of the claim.
- CRIT-06 (AVOID): do not fixate on encoding while ignoring upstream levels.
- The critic MUST NOT ship an artifact whose `qa_report` verdict is not SHIP.

## Strong heuristics
- CRIT-01, CRIT-03, CRIT-05 (SHOULD): justify choices, explain what works,
  subordinate aesthetics to understanding.

## Context-dependent guidance
- CRIT-04 (MAY): model contested rules (axis-zero off-bars) as weighted, not
  absolute; expose the trade-off.
- In critique mode with no editable source, downgrade REPAIR actions to prioritized
  recommendations.

## Failure modes
- Orchestrator re-implementing a child skill's rules → drift and inconsistency.
- Scoring an artifact that failed a hard gate as if points could redeem it.
- Diagnosing a defect at the wrong failure level (e.g. restyling to fix a
  wrong-abstraction problem).
- Shipping without a render-qa SHIP verdict.

## Validation checks
- Every principle a child skill cited exists in `principles.yaml` (registry integrity).
- The case file contains outputs from every skill the route required.
- No SHIP verdict coexists with an unresolved hard-gate failure.
- Each defect is filed at exactly one of the seven levels with an owning skill.

## Repair strategies
- Route each defect to the skill that owns its level and re-run `visual-render-qa`.
- Iterate gate → repair → re-render until SHIP or an ESCALATE decision is returned
  to the user.

## Output contract
The case file + a verdict. On SHIP: the artifact plus a short justification (what
works, which principles were honored). On REPAIR: the ranked defects with owning
skills. On ESCALATE: the specific decision needing the user.

## Source basis
Orchestration + gating: QA-01/02/03 (S10). Reasoning discipline and critique:
CRIT-01..06 (S01, S10, S12). Rubric weighting per the project brief §11; failure
levels per §9. Child-skill principles live in their own SKILL.md Source basis and
in principles.yaml.

## Known open questions
- Calibrating rubric weights against the `visualize/` validation set (later track).
- Whether critique-mode should output a machine-readable defect list for tooling.
