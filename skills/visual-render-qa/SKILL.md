---
name: visual-render-qa
description: >
  Renderer-independent quality gate. Inspects the ACTUAL rendered artifact at final
  size in its real medium, applies the hard-constraint gates and accessibility
  checks, detects visual defects (collisions, clipping, contrast, color-only cues),
  and prescribes repairs. Use as the last step before any visual is shipped,
  regardless of what tool produced it.
---

# Visual Render QA

## Purpose
A specification that is never viewed is never verified. This skill looks at the
real output — not the intent, not the code — at the exact final dimensions and
medium, and refuses to pass artifacts that lie, that cannot be read, or that fail
accessibility. It is renderer-independent: the same checks apply to plotting-library output,
a slide, an SVG, a PDF figure, or a screenshot.

## When to invoke
Last, before declaring any visual done, and again after every repair. Also when
auditing an existing figure you did not build.

## Inputs
- The rendered artifact at final size/medium (image or the artifact itself).
- The intent record, encoding table, and composition/fidelity plans (to check the
  render against what was intended).

## Required intermediate representation
A **QA report**:
```
gates:        [pass/fail per hard constraint checked]
defects:      [collision | clipping | contrast | color-only | illegible | distortion] with locations
soft_score:   aggregate of SHOULD deviations (for ranking, not gating)
verdict:      SHIP | REPAIR (with prescribed fixes) | ESCALATE
```

## Procedure
1. **Render and view at final size in the real medium** (MEDIA-02, QA-08). For a
   deck, view at projected scale; for print, at print size. Do not judge from a
   zoomed-in editor view.
2. **Apply hard gates first (QA-01, QA-02).** Reject before any aesthetic scoring if
   any hard constraint is violated:
   - Truncated bar baseline (ENC-02); distorted magnitude / hidden truncation /
     3-D quantity (SCI-02); missing color bar on a color scale (ANNO-04); missing
     axis units (ANNO-05); missing data source (ANNO-06) where required.
   - **Small multiples on independent (auto-scaled) axes (SCI-02).** Faceted/panel
     figures MUST share a common quantitative scale so panels are directly
     comparable, unless a per-panel scale is *prominently* labelled on every panel.
     A per-panel free scale that draws a small series as tall as a large one is a
     magnitude lie even though each panel is internally correct — reject it.
     *(Fold from the 2026-09-02 triptych inspection: an auto-scaled panel drew a
     ~250k series as tall as a ~3M series.)*
   - Text contrast below the floor the active modes set (ACCESS-03); under
     `colorblind_safe`, color as the sole cue (ACCESS-01) or red/green at equal
     luminance (ACCESS-02). Gate-by-mode table: ~/dev/MandrakeWorkflows/visualize/principles/modes.md.
   - Undisclosed exaggeration/simulation in science viz (UNC-03); rainbow colormap
     on data (COLOR-03); undocumented diagram vocabulary (DIAG-01/ANNO-11).
   - No visual hierarchy — no identifiable primary element (HIER-01).
   - A headline/annotation claim in a different reference frame than the encoding —
     its baseline, units, or scope differ from what the marks encode and that frame
     is not shown on the figure (SCI-06, gate G12).
   - **Aggregation dishonesty (SCI-07, gate G13).** A pooled summary or fit — one
     mean, trend, or regression line drawn over combined groups — presented as if it
     described each subgroup, or a decomposition variable that does not actually vary
     used to explain a difference. The within-group pattern can weaken or reverse
     (Simpson's paradox), so a pooled fit asserting a per-group story is a
     structure lie even when no single mark is drawn dishonestly. Reject unless the
     figure shows the disaggregated view (small multiples / per-group fits / raw
     grouped points) or explicitly discloses the summary as pooled. *(Fold from the
     2026-09-01 bake-off: pooled fit passed off as group description, cases 05/33.)*
3. **Scan for rendered defects.** Inspect for text/text, text/mark, text/connector,
   legend/plot, and annotation/annotation **collisions**; clipped or cut-off legends,
   labels, or titles; overlapping marks that hide data. Any unintended collision or
   clip is a blocking defect.
   - **Multi-series clutter → `illegible` (blocking).** On a multi-series line/time
     plot, judge line-count × volatility: when many noisy series overplot so that
     individual series cannot be traced (a "hairball"), flag `illegible`. The fix is
     upstream — reduce/emphasize series, facet, or aggregate (see the generate-side
     lesson in `scientific-visualization`) and re-render; do not ship the hairball.
     *(Fold from the 2026-09-02 triptych inspection and the 2026-09-03 dogfood naive
     control: a linear all-series price plot crushed 8 of 10 series onto the baseline.)*
4. **Accessibility pass (QA-06), per the active modes.** Always measure text
   contrast (ACCESS-03). `colorblind_safe`: run a CVD simulation — do categories stay
   distinct (ACCESS-02)? `print_grayscale`: do all distinctions survive (ACCESS-05)?
5. **Perception pass (QA-07).** Check that chart size and gridline spacing support
   reading at final size; gridlines subtler than data (PERC-01).
6. **Read-back test (QA-05).** State the takeaway you would derive from the render
   alone. If it does not match the intent record's takeaway, that is a communication
   defect even if every gate passed.
6b. **Claim-frame check (SCI-06, gate G12).** For every number and comparison in the
   title, annotations, and stated takeaway, name the baseline/units/scope it implies,
   then confirm that is the same frame the marks encode. A "change since X" number
   must be computed against X — not silently borrowed from the axis's own baseline.
   If the claim's frame differs, either recompute it in the encoded frame or draw the
   claim's reference (a line/label) on the same axis so a reader can verify it.
7. **Verdict.** SHIP only if all hard gates pass and no blocking defect remains.
   Otherwise REPAIR (list prescribed fixes) or ESCALATE genuinely context-dependent
   calls (e.g. UNC-01 baseline) to the user.

## Hard constraints
- QA-08 (MUST): inspect the actual render at final size before shipping.
- QA-01, QA-02 (MUST): gate on validity before ranking; a hard-constraint violation
  is an automatic fail. All the hard constraints enumerated in step 2 are enforced here.

## Strong heuristics
- QA-05, QA-06, QA-07 (SHOULD): naive-reader read-back, mechanical accessibility
  check, size/gridline inspection.

## Context-dependent guidance
- QA-04 (SHOULD): soft-constraint weights used for the soft_score should trace to
  perceptual evidence and are versioned, not invented per-run.
- ESCALATE items (UNC-01) are surfaced, not auto-resolved.

## Failure modes
- Passing an artifact judged only from code or a zoomed editor view (violates QA-08).
- Treating a hard-constraint violation as a deduction rather than a rejection
  (violates QA-02).
- Missing collisions/clipping that appear only at final render size.
- Declaring success without a read-back test.

## Validation checks
- The render was viewed at final size/medium (evidence: the QA report exists).
- All hard gates pass; zero unresolved blocking defects.
- Measured contrast meets the mode's floor; the mode-required CVD/grayscale views hold.
- Read-back takeaway == intended takeaway.

## Repair strategies
- Collisions/clipping: enlarge canvas, reposition labels, switch to direct labels,
  reduce series, or split into small multiples (LAYOUT-02).
- Contrast/color-only: raise contrast, add redundant channel (ACCESS-01/04).
- Distortion: fix baseline/scale (ENC-02, UNC-01) and re-render.
- Re-run this skill after every repair until SHIP.

## Output contract
A QA report with a verdict (SHIP / REPAIR+fixes / ESCALATE). On REPAIR, hand the
prescribed fixes back to the relevant skill and re-QA the new render.

## Source basis
QA-01..08 (S10, S03, S06, S15, S16, S05). Enforced hard constraints drawn from
ENC-02, SCI-02, SCI-06, SCI-07, ANNO-04/05/06/11, ACCESS-01/02/03, UNC-03, COLOR-03,
DIAG-01, HIER-01, MEDIA-02, PERC-01. See principles.yaml.

## Known open questions
- How much of the collision/contrast scan can be automated vs. needs a rendered-image
  vision check.
- Calibrated soft-score weights (depends on QA-04 perceptual data).
