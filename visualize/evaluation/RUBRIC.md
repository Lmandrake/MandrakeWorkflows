# Scoring rubric and hard gates

Two layers, in strict order (QA-01, QA-02, S10 Draco):

1. **Hard gates** — pass/fail. Any failure blocks SHIP regardless of score. Gates
   test *validity*: does the artifact lie, is it unreadable, is it inaccessible?
2. **Soft rubric** — 100 points, used only to *rank valid alternatives*. A high
   score never redeems a failed gate.

---

## Layer 1 — Hard gates (all must PASS)

A single FAIL → verdict REPAIR (or ESCALATE for context-dependent items). Owner
skill in brackets; enforced in `visual-render-qa` step 2.

| # | Gate | Fails if | Guard |
|---|------|----------|-------|
| G1 | Magnitude honesty | Bar/column baseline truncated; area scaled by radius; 3-D used for quantity comparison; hidden axis break | ENC-02, SCI-02 |
| G2 | Quantifiability | Color scale present with no color bar; quantitative axis with no units/ticks | ANNO-04, ANNO-05 |
| G3 | Color-accessibility *(mode-dependent, `principles/modes.md`)* | Default: a required distinction is not visible to the intended viewer. `colorblind_safe`: color is the sole cue, or red/green at equal luminance. `print_grayscale`: no grayscale survival | ACCESS-01, ACCESS-02, ACCESS-05 |
| G4 | Text contrast | Measured text contrast below the floor the active modes set (`principles/modes.md`) | ACCESS-03 |
| G5 | Colormap validity | Rainbow/jet on a data dimension; non-uniform or deformed map on continuous data | COLOR-01, COLOR-03, COLOR-05 |
| G6 | Scientific disclosure | Exaggeration/simulation/non-scale sizing undisclosed; visible feature with no data referent | UNC-03, SCI-03 |
| G7 | Hierarchy exists | No identifiable primary element; focal points compete | HIER-01 |
| G8 | Render integrity | Unintended text/mark/legend/annotation collision; clipped or cut-off element; occluded data | QA-08 (+ collision scan) |
| G9 | Diagram/network legibility | Undocumented diagram vocabulary; node-link hairball where a matrix is required; position asserts false structure | DIAG-01, ANNO-11, NET-02, NET-03 |
| G10 | Self-containment | Published figure lacks a caption/source that lets it stand alone | ANNO-03, ANNO-06 |
| G11 | Intent match (read-back) | The takeaway a naive reader derives from the render ≠ the intended takeaway | QA-05, INTENT-04 |
| G12 | Claim–encoding consistency | A stated numeric/comparative claim (title, annotation, takeaway) is in a different reference frame than the encoding — its baseline, units, or scope differ from what the marks encode, and that frame is not shown on the figure | SCI-06 |
| G13 | Aggregation honesty | A pooled summary or fit (a combined mean, trend, or regression line) is presented as if it described each subgroup, or a decomposition/explanatory variable that does not actually vary is used to explain differences — the within-group pattern can differ or reverse (Simpson's paradox / ecological fallacy), and the disaggregated view is neither shown nor the summary disclosed as pooled | SCI-07, SCI-01 |

ESCALATE (not auto-fail): the non-bar zero-baseline decision (UNC-01) — surface to
the user with the ratio-vs-difference framing rather than silently passing or failing.

---

## Layer 2 — Soft rubric (100 points; ranks valid designs only)

Per the project brief §11. Deviations from SHOULD-level principles cost points here
but do not block SHIP.

| Dimension | Pts | What it rewards | Principles |
|-----------|-----|-----------------|------------|
| Semantic fidelity | 25 | Chart family + encodings truly express the analytic relationship; key value on the strongest channel | SEM-01, ENC-01, ENC-05 |
| Scientific / quantitative integrity | 20 | Raw distribution respected; uncertainty represented well; fidelity beyond the hard minimum | SCI-01, UNC-01/02, SCI-05 |
| Perceptual effectiveness | 15 | Low clutter, subtle references, clean simultaneous-contrast handling | PERC-01/02, ENC-08, LAYOUT-02 |
| Layout / render integrity | 15 | Clean grid, alignment, figure-ground, balance beyond the collision minimum | LAYOUT-01/03/04/05 |
| Communication hierarchy | 10 | Grouping and emphasis make the intended comparison effortless | HIER-02/03/04 |
| Accessibility | 5 | Redundancy and lightness beyond the hard floor | ACCESS-04, ACCESS-05 |
| Medium fitness | 5 | Tuned to the actual medium/viewing distance and export format | MEDIA-01/02/03/04 |
| Aesthetic coherence | 5 | Restrained, consistent, aesthetics serving understanding | COLOR-06, CRIT-05 |

**Scoring procedure.** (1) Run all hard gates; if any FAIL, stop — verdict REPAIR/
ESCALATE. (2) Only for gate-passing designs, award each dimension 0..max and sum.
(3) When comparing alternatives, prefer the higher total (QA-03); record the
weighted reasoning (weights should trace to perceptual evidence per QA-04, not
be invented per run).

**Interpretation bands (guidance, not gates):** ≥85 excellent · 70–84 solid · 55–69
acceptable with noted weaknesses · <55 rework recommended even though gates passed.
