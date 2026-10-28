# S15 — Graphical Perception: Cleveland & McGill (1984) + Heer & Bostock (2010) replication

## Authority / evidence type
Tier A (for the encoding-effectiveness ordering, on the basis of the replication and cross-corroboration).

Two linked sources:
- **Cleveland & McGill (1984), "Graphical Perception: Theory, Experimentation, and Application to the Development of Graphical Methods,"** *Journal of the American Statistical Association* 79(387):531–554. This is the seminal empirical ranking of elementary perceptual tasks. **reference_only / paywalled** — its full text is NOT in the acquired files; only a search-results list of URLs (JSTOR, Taylor & Francis, and several open PDF mirrors) is present. No numbers, figures, or exact task list from the 1984 paper can be quoted from the files.
- **Heer & Bostock (2010), "Crowdsourcing Graphical Perception: Using Mechanical Turk to Assess Visualization Design,"** Proc. ACM CHI, pp. 203–212, doi:10.1145/1753326.1753357 (CHI Honorable Mention). Peer-reviewed; the fetched file contains the **abstract only** (from the UW Interactive Data Lab page), not the full results text.

Per the task instruction: the encoding-effectiveness ordering is treated as **corroborated by Heer & Bostock's replication (Tier A)** rather than asserted from the 1984 numbers directly. It is additionally cross-corroborated by S02 (Franconeri et al.), whose publisher summary states the same channel-precision ranking.

## Scope
The perceptual accuracy with which people read quantitative values from different visual encodings ("graphical perception"). Cleveland & McGill framed it as ranking "elementary perceptual tasks" by how accurately viewers judge the magnitude/ratio they encode. Heer & Bostock's contribution is twofold: (1) methodological — validating crowdsourcing (Amazon Mechanical Turk) as a platform for running graphical-perception experiments at low cost and scale; and (2) empirical — replicating prior spatial-encoding and luminance-contrast findings and adding new experiments on rectangular-area perception (as in treemaps/cartograms) and on chart size and gridline spacing.

## Central claims
- Different visual encodings of the same quantity are read with systematically different accuracy; there is a rank ordering of encoding effectiveness for magnitude judgments.
- The ordering (as corroborated by Heer & Bostock's replication and restated in S02): **position/length judgments are read most accurately, angle less so, and area (and other channels like color intensity/luminance) least accurately.** Specific just-noticeable numeric error rates from the 1984 paper are not available in the files and are not asserted here.
- Heer & Bostock (from the fetched abstract): crowdsourced perception experiments are **viable** — MTurk reproduced classic laboratory spatial-encoding and luminance-contrast results — making large-scale evaluation of the visualization design space practical.
- New H&B experimental targets (per abstract): rectangular-area perception relevant to treemaps and cartograms, and the effects of chart size and gridline spacing on perception. (The specific quantitative outcomes are in the full paper, which is not in the files.)
- Understanding perception is described as "critical to effective visualization design" — i.e., encoding choices should be grounded in measured perceptual performance, not intuition.

## Operationalizable rules
- To let viewers judge quantities accurately, prefer position- and length-based encodings (e.g., dot/bar position along a common scale) over angle-based (pie/donut) and area-based (bubbles, treemaps, cartograms) encodings.
- Treat area and color-intensity/luminance encodings as low-precision: acceptable for coarse/qualitative impressions, but avoid when accurate magnitude comparison is required.
- When accurate comparison matters, align items on a common scale/baseline (a position-along-common-scale judgment), which is the highest-accuracy task.
- Prefer crowdsourced (or otherwise scaled) perceptual pre-testing to empirically compare candidate encodings across a large design space when resources allow — H&B established this is a valid method.
- Consider chart size and gridline spacing as design variables that measurably affect perception, not just aesthetics (H&B studied both).

## Important caveats
- The precise 1984 accuracy ordering, error magnitudes, and exact task definitions cannot be verified from the acquired files (Cleveland & McGill full text is paywalled/absent); this card relies on the H&B replication and S02 cross-corroboration for the ordering, and flags that specific numbers are unverified here.
- Only the H&B abstract is in the files; the specific quantitative findings for rectangular-area perception, chart size, and gridline spacing are not available and are not stated here.
- The ranking concerns accuracy of magnitude/ratio judgments; it does not by itself dictate the best encoding when goals other than precise magnitude reading dominate (e.g., showing part-to-whole gestalt, spatial/geographic context, or aesthetic engagement).
- Perceptual accuracy is one input to encoding choice; it must be combined with task/abstraction fit (see S01) and audience/communication goals (see S02).

## Conflicts with other guidance
- Strongly consistent with S02's five-channel precision ranking (position > length > area > angle > intensity) — S15 is the empirical foundation S02 restates as prescription. (Minor ordering-detail note: S02's summary lists area ahead of angle, whereas the Cleveland-McGill tradition typically places angle/slope ahead of area; the files do not contain the exact C&M ordering to adjudicate, so this fine-grained ordering between angle and area is flagged as unverified from the files.)
- Consistent with S01: provides the "known perceptual principles" against which encoding-level design should be justified (immediate validation).
- Tension with common practice favoring pie charts and area-based infographics: S15 implies these are among the least accurate for magnitude comparison.

## Useful examples
- Bar chart / dot plot on a common scale = the high-accuracy "position along a common scale" case.
- Pie chart = angle (and area) judgment — lower accuracy for comparing slice magnitudes.
- Treemaps and cartograms = rectangular-area judgments, explicitly tested by Heer & Bostock as a lower-precision case.
- Heer & Bostock's MTurk stimulus: participants estimated "what percentage the smaller value was of the larger" — a canonical ratio-judgment task inherited from Cleveland & McGill.

## Candidate principle IDs
- [ENC/PERC] SHOULD encode quantities that must be compared accurately using position or length on a common scale, in preference to angle or area. | force: SHOULD | tier: A | contexts: any chart whose purpose includes accurate magnitude/ratio comparison | rationale: position/length are read most accurately; the ordering is corroborated by Heer & Bostock's replication and by S02 | source: S15
- [ENC/PERC] AVOID area- and intensity/luminance-based encodings when precise magnitude reading is required. | force: AVOID | tier: A | contexts: bubble charts, treemaps, cartograms, color-shaded magnitude maps used for exact comparison | rationale: area and luminance are low-precision channels for ratio judgments | source: S15
- [PERC] AVOID relying on pie/donut (angle) encodings for comparing more than a few slice magnitudes. | force: AVOID | tier: A | contexts: part-to-whole comparisons requiring accuracy | rationale: angle judgments are less accurate than position/length | source: S15
- [ENC] SHOULD align items on a common baseline/scale to enable the highest-accuracy perceptual judgment. | force: SHOULD | tier: A | contexts: multi-value comparison charts | rationale: position-along-a-common-scale is the most accurate elementary perceptual task | source: S15
- [CRIT] MAY use crowdsourced perceptual testing to empirically compare candidate encodings across a large design space. | force: MAY | tier: A | contexts: evaluating/selecting encodings when resources allow | rationale: Heer & Bostock validated crowdsourcing as a viable graphical-perception method | source: S15
- [QA] SHOULD treat chart size and gridline spacing as perception-affecting design variables, not merely cosmetic. | force: SHOULD | tier: B | contexts: sizing and gridline decisions | rationale: Heer & Bostock studied both as factors in graphical perception (specific magnitudes not verifiable from files) | source: S15
