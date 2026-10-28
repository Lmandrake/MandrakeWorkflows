---
name: scientific-visualization
description: >
  Specialist skill for scientific and technical visuals where fidelity to real
  data or models is paramount: scientific figures, spatiotemporal / remote-sensing
  visualizations, networks, technical diagrams, and maps. Use alongside
  visual-encoding and visual-composition whenever the subject is scientific data,
  a physical phenomenon, a network, a diagram, or a map.
---

# Scientific Visualization

## Purpose
Uphold scientific and quantitative integrity while making complex, often
invisible, phenomena perceptible. This skill carries the domain rules that general
charting does not: fidelity, uncertainty disclosure, diagram grammar, network
layout, and cartographic legibility.

## When to invoke
When the data is scientific/physical/model-derived; when building a network figure,
a technical diagram, or a map; or when a figure will appear in a scientific
publication. Runs in parallel with `visual-encoding`/`visual-composition`, adding
domain constraints and gates.

## Inputs
- The intent record and encoding table.
- The scientific context: what is measured/modeled, units, known uncertainty, and
  any transformation applied to the data.

## Required intermediate representation
A **fidelity + domain record**:
```
data_provenance:   <measured | modeled | simulated | illustrative>
transformations:   <log/exaggeration/normalization/non-scale sizing> -> disclosed? (Y/N)
colormap:          <name; perceptually uniform? monotonic lightness? documented?>
domain_form:       <chart | network | diagram | map | volumetric/spatiotemporal>
uncertainty:       <how represented; audience-appropriate?>
```

## Procedure
1. **Fidelity first.** Every visible feature must correspond to a data or model
   quantity (SCI-03). Plot the raw distribution before trusting summaries (SCI-01).
   Do not distort magnitude — area by area not radius, no hidden truncation, no 3-D
   for quantity comparison (SCI-02).
1b. **Noisy / multi-scale time series: aggregate or rescale before shipping a
   multiline (SHOULD; SCI-02, MEDIA-05, disclose per UNC-03).** When many volatile
   series would overplot into an untraceable hairball, or values span orders of
   magnitude, do not ship the raw multiline. Prefer a coarser honest cadence
   (year-end / rolling mean) and/or a log or growth-of-base rescaling so the trend
   is legible and equal proportional moves read equally — then disclose the
   aggregation/transform in the caption. This does not override SCI-01 (show the raw
   distribution when the *spread itself* is the point); it applies when the reader's
   question is trend/comparison and raw sampling noise is only obscuring it. The
   render-QA floor rejects the un-aggregated hairball as `illegible`, so make this
   choice at generate time. *(Fold from the 2026-09-03 dogfood: monthly linear
   all-series prices → year-end log growth-of-$1.)*
1c. **Grouped or regression data: do not let aggregation misrepresent subgroups
   (MUST; SCI-07, gate G13).** Before fitting or summarizing across groups, confirm
   the decomposition/explanatory variable actually varies across the units shown,
   and never draw one pooled mean/trend/regression line over combined groups and
   label it as a per-group result — the within-group relationship can weaken or
   reverse (Simpson's paradox). Prefer per-group fits, small multiples, or the raw
   grouped points; if a pooled summary is genuinely wanted, disclose it as pooled.
   *(Fold from the 2026-09-01 bake-off: pooled fit passed off as group description.)*
2. **Disclose transformations.** Any departure from literal fidelity — vertical
   exaggeration, non-scale sizing, simulated/illustrative content — MUST be labeled
   (UNC-03). Use labeled scale bars, not magnification factors, on a separate layer;
   obey image-integrity policy (SCI-04).
3. **Make the invisible visible, honestly.** Map non-visible properties to visible
   channels with a stated, defensible mapping (SCI-05). For continuous fields use a
   perceptually uniform, monotonic-lightness, documented colormap; never rainbow
   (COLOR-01/02/03/05); always show the color bar (ANNO-04).
4. **Uncertainty.** Represent it; for lay audiences prefer discrete outcome examples
   and absolute natural frequencies over bare error bars (UNC-02).
5. **If a network:** define its purpose before layout (NET-01); do not default to
   node-link — use matrices for dense graphs, implicit layouts for trees (NET-02);
   make position meaningful (NET-03); aggregate to the right detail (NET-04); match
   marks to semantics — arrows only for directional relations (SEM-04).
6. **If a diagram:** declare the node/connector vocabulary up front and legend it
   (DIAG-01, ANNO-11); add a visual type only when semantics differ (DIAG-02); route
   connectors cleanly, minimize crossings, unambiguous endpoints (DIAG-03); follow a
   standard notation if one exists (DIAG-04); explain nonstandard syntax and prevent
   accidental meaning (DIAG-05).
7. **If a map:** ensure legibility at scale with familiar symbols (MAP-01); mute
   basemap/context so the theme dominates (MAP-02); choropleth for rates,
   proportional symbols for counts (ENC-06).
8. **Split when overloaded:** more than ~3 non-redundant encodings → multiple
   focused figures (MEDIA-05). Keep aesthetics subordinate to accuracy (CRIT-05).
9. Return to `visual-composition` for annotation, then `visual-render-qa`.

### Medium profile
Primary target is **scientific_spatiotemporal** and **scientific_publication**:
print sizes, self-contained caption, scale bars, editable vector export (MEDIA-03).

## Hard constraints
- SCI-02, SCI-03, SCI-04, SCI-07 (MUST). UNC-03 (MUST). COLOR-01/02 (MUST), COLOR-03/05
  (AVOID). ANNO-04, ANNO-11 (MUST). NET-01, NET-03 (MUST). DIAG-01 (MUST). MAP-01 (MUST).

## Strong heuristics
- SCI-01, SCI-05, UNC-02, NET-02/04, DIAG-02/03/04/05, MAP-02, ENC-06, MEDIA-05,
  CRIT-05, SEM-04 (SHOULD).

## Context-dependent guidance
- 3-D is permitted for inherently spatial/volumetric phenomena, especially animated
  (ENC-10 exception; conflicts.md #9).
- COLOR-02 exception: diverging maps with an intentionally light center.
- UNC-02 relaxes for expert audiences who expect confidence intervals.

## Failure modes
- Decorative features with no data referent (violates SCI-03).
- Undisclosed exaggeration/simulation presented as data (violates UNC-03).
- Rainbow colormap on a physical field → false boundaries (violates COLOR-03).
- Node-link hairball for a dense graph (violates NET-02).
- Undocumented diagram vocabulary → reader guesses meaning (violates DIAG-01).

## Validation checks
- Every visible feature maps to a quantity; transformations are labeled.
- Colormap is documented perceptually-uniform (grayscale survival only in `print_grayscale`).
- Networks: task stated, representation matches density, position is meaningful.
- Diagrams: a legend documents every color/line/shape convention.
- Maps: symbols/labels legible at intended scale; theme outranks basemap.

## Repair strategies
- Replace non-uniform colormap; add the color bar; add a disclosure label for any
  exaggeration.
- Convert dense node-link → adjacency matrix or aggregated view.
- Add the missing diagram legend and standardize connector routing.

## Output contract
A fidelity+domain record and domain-correct artifact, returned to
`visual-composition` for annotation and then to `visual-render-qa`.

## Source basis
SCI-01..07 (S02, S03, S12, S06). UNC-02/03 (S02, S12). COLOR-01/02/03/05 (S05, S09).
NET-01..04 + SEM-04 (S09). DIAG-01..05 + ANNO-11 (S08). MAP-01/02 + ENC-06 (S11, S04).
MEDIA-03/05 (S06, S09). CRIT-05 (S12). See principles.yaml.

## Known open questions
- Standard disclosure vocabulary for vertical exaggeration across domains.
- When matrix vs. node-link crossover happens as a function of density (needs data).
