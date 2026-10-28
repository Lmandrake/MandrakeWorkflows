# Test cases (v0.1)

Six scenarios chosen to exercise the hard gates and the routing between skills.
Each states the input, the trap, the expected reasoning path, the gate(s) it must
trigger, and the correct outcome. These are behavioral specs for the skill stack:
run the stack on each and confirm the expected verdict and routing.

Full 12-case benchmark deferred to v0.2 (see BENCHMARK_PLAN.md).

---

## TC-01 — Truncated bar chart (Level 3 / G1)
**Input.** "Make a bar chart of these four regional sales totals" — values 98, 99,
101, 102 (thousands).
**Trap.** A tool default (or a request to "make the differences pop") truncates the
y-axis to 95–105, exaggerating tiny differences.
**Expected path.** visual-intent (task=compare magnitudes) → visual-encoding (bars →
ENC-02 zero baseline) → render-qa.
**Gate.** G1 must FAIL if the baseline is truncated.
**Correct outcome.** Bars anchored at zero; if the small differences are the actual
message, escalate to a different encoding (e.g. dot plot of differences) rather than
truncating — REPAIR then SHIP.

## TC-02 — Rainbow heatmap of a physical field (Level 3+5 / G5, G3)
**Input.** "Plot this sea-surface-temperature grid as a heatmap."
**Trap.** Default `jet`/rainbow colormap; adjacent tiles touch.
**Expected path.** visual-intent → visual-encoding + scientific-visualization
(continuous field → COLOR-01/02/03; PERC-02) → render-qa.
**Gates.** G5 FAIL (rainbow) and G3 FAIL (grayscale ordering lost).
**Correct outcome.** Swap to a documented perceptually-uniform, monotonic-lightness
map; add the color bar (ANNO-04); separate touching cells (PERC-02) — SHIP.

## TC-03 — Pie chart of 9 categories, color-only legend (Level 3 / G3, and soft)
**Input.** "Show the market-share split across our nine product lines."
**Trap.** 9-slice pie with a detached color-only legend.
**Expected path.** visual-intent (task=rank/part-to-whole) → visual-encoding
(ENC-04 avoid pie for many; ANNO-01 direct labels; ACCESS-01 not color-only) →
composition → render-qa.
**Gate.** G3 FAIL (color is the sole cue). Soft: heavy penalty on semantic fidelity
for the pie.
**Correct outcome.** Sorted bar or lollipop with direct labels; color redundant with
position/label — SHIP.

## TC-04 — Undocumented architecture diagram (Level 5 / G9)
**Input.** "Diagram our data pipeline: sources, queue, workers, store, API."
**Trap.** Multiple box shapes and line styles with no legend; a couple of connector
crossings with ambiguous endpoints.
**Expected path.** visual-intent → scientific-visualization (DIAG-01 declare + legend
vocabulary; DIAG-03 clean routing; ANNO-11) → composition → render-qa.
**Gate.** G9 FAIL (undocumented vocabulary).
**Correct outcome.** A declared node/connector legend; only semantically-distinct
shapes; orthogonal routing, minimized crossings, unambiguous endpoints — SHIP.

## TC-05 — Simulated future scenario shown as data (Level 5/7 / G6, G11)
**Input.** "Show projected glacier extent in 2100 over the satellite basemap."
**Trap.** Model projection rendered identically to observed data, no disclosure.
**Expected path.** visual-intent → scientific-visualization (UNC-03 disclose
simulation; SCI-03 fidelity) → composition (annotation) → render-qa.
**Gates.** G6 FAIL (undisclosed simulation); likely G11 read-back mismatch (reader
thinks it is measured).
**Correct outcome.** Clear "modeled projection" labeling, distinct styling from
observations, caption disclosure — SHIP.

## TC-06 — Correct data, unreadable projected slide (Level 6 / G8, G4)
**Input.** "Put this multi-series line chart on a conference slide."
**Trap.** A publication figure pasted onto a slide: 8-pt axis text, a legend that
runs off the panel, overlapping series labels — fine in print, illegible projected.
**Expected path.** visual-intent (medium=deck_projected) → composition (MEDIA-01
medium version; ANNO-01 direct labels) → render-qa (view at projected size).
**Gates.** G8 FAIL (clipped legend / label collisions) and G4 FAIL (contrast/size
too low at projected scale).
**Correct outcome.** Medium-specific redraw: larger type, direct labels, fewer
series or small multiples, no clipping — SHIP.

---

## Coverage map (gate → cases)
G1: TC-01 · G3: TC-02, TC-03 · G4: TC-06 · G5: TC-02 · G6: TC-05 · G8: TC-06 ·
G9: TC-04 · G11: TC-05. G2, G7, G10 are covered incidentally (each case's figure
must still pass them) and get dedicated cases in the v0.2 12-case suite.

## How to run (v0.1, manual)
For each case, drive the stack via `visual-critic`, record: the route taken, which
gates fired, the verdict, and whether the read-back takeaway matched intent. A pass
= the expected gate(s) fired AND the final SHIP artifact satisfies the correct
outcome. Log results in a results table (add when first executed).
