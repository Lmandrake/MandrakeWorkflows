# S03 — Rougier, Droettboom & Bourne, "Ten Simple Rules for Better Figures" (PLOS Comput Biol, 2014)

## Authority / evidence type
Tier B (with some A-adjacent content). Peer-reviewed editorial/practitioner guidance in a reputable journal (PLoS Computational Biology, 2014; DOI 10.1371/journal.pcbi.1003833; CC0 public domain). Highly cited (100+ citations per the CSL metadata). It is expert distilled best-practice rather than an original controlled study — many rules are asserted with illustrative figures and cite foundational sources (Tufte, Borland & Taylor's "Rainbow color map (still) considered harmful", Okabe & Ito color-universal-design). So it is authoritative as consensus craft guidance (Tier B), and the color/perception claims it borrows lean on Tier-A primary work but are presented here secondhand.

## Scope
General guidance for designing scientific figures across media (journal article, poster, oral presentation, general public). Covers audience/message framing, medium adaptation, captions, defaults, color, honest representation, chartjunk, prioritizing message over aesthetics, and tool selection. Not domain-specific; examples drawn from computational biology / general science.

## Central claims
- Scientific visualization is a "graphical interface between people and data"; problems arise when perception diverges from the conveyer's intent.
- Design must be driven by (1) the audience and (2) a single clearly identified message, decided before building the figure.
- A figure must be adapted to its support medium; the same figure should not be lifted unchanged from an article into a talk.
- Captions are mandatory and must anticipate reader questions; numeric values needed for interpretation must be given explicitly, not read off bar heights.
- Software defaults are "good enough for any plot but best for none" and require manual tuning.
- Color should be used deliberately and sparingly; default rainbow/jet colormaps should be avoided unless explicitly justified; too many similar colors harm colorblind readers.
- Figures must not mislead — both implicit (auto-rescaling, radius-vs-area encoding) and explicit (pie charts, 3-D charts, truncated axes) choices can create false perceptions.
- Avoid chartjunk (non-data-ink) but recognize context-dependence (an element that is junk in one figure can be justified in another).
- Message and readability outweigh beauty in science.
- Use the right dedicated tool; visualization tooling can differ from analysis tooling.

## Operationalizable rules
- Identify audience and the single message before designing the figure; let intent drive the design.
- Produce a distinct figure per medium: for talks/projection, thicken lines, enlarge points/text, use strong contrast, avoid vertical text, remove detail.
- Always include a caption that explains how to read the figure and supplies what cannot be shown graphically; point out the point-of-interest in the caption too.
- Do not rely on plotting-library defaults (size, font, colors, ticks, markers) — tune them.
- Default to black; only add color for a reason ("Is there any reason this plot is blue and not black?" — if unknown, keep it black). Use color to highlight one element while keeping others gray/black.
- Match colormap class to data: sequential (low→high quantitative), diverging (deviation from a median), qualitative (categorical). Do not use jet/rainbow default unless explicitly justified.
- Avoid too many similar colors (colorblind discernibility).
- Encode quantity by area correctly — do not map value to radius when area is perceived (produces false ratios).
- Show the full/true value range; truncated axes exaggerate differences even when labeled.
- Avoid pie charts and 3-D charts for comparing quantities; use the simplest plot type that conveys the message with labels, ticks, and title.
- Remove non-data-ink (excess gridlines, colored backgrounds, redundant labels, overlapping ticks, three-digit precision that carries no information) unless it adds information.
- Ask colleagues to interpret your figure to catch misreadings.

## Important caveats
- These are heuristics/editorial rules, not empirically tuned thresholds — no numeric specs given.
- Chartjunk is explicitly context-dependent (background box justified when it encodes a range).
- "Message trumps beauty" is a value stance for science, not a claim that aesthetics never matter.
- Tool list (matplotlib, R, Inkscape, TikZ/PGF, GIMP, ImageMagick, D3.js, Cytoscape, Circos) is 2014-era and non-exhaustive.

## Conflicts with other guidance
- The rainbow/colormap advice is directionally consistent with S05 (Crameri) but far less rigorous — S03 says "avoid unless justified" whereas S05 argues rainbow is essentially never scientifically defensible. Treat S05 as the stronger authority on colormaps.
- "Default to black, add color only with reason" is a stylistic minimalism that can under-serve categorical encoding; reconcile with S06/S05 accessible-palette guidance where multiple colors are needed.
- No direct conflicts with WCAG (S16); complementary.

## Useful examples
- Fig 1 (NYT cancer remake): audience-driven layout trades numeric precision for a clear public message — acceptable for general audience, not for a scientific claim without numbers elsewhere.
- Fig 5: same signal under rainbow (qualitative), seismic (diverging), and a sequential purple map — rainbow and diverging both hide high-frequency detail; sequential reveals it.
- Fig 6: disc area vs radius encoding of {30,20,15,10} produces very different perceived ratios; truncated y-axis (80–100 vs 0–100) makes similar values look very different.
- Fig 7: seven overlapping series (bad) vs small-multiples with light background series (good) in same footprint.
- Fig 8 ("uncanny valley," xkcd sketch style): deliberately rough aesthetic signals that data are approximate — message over beauty.

## Candidate principle IDs
- [INTENT] Identify the audience and the single intended message before designing a figure, and let that intent drive every design choice. | force: MUST | tier: B | contexts: all figures | rationale: perception diverging from conveyer intent is the root failure mode | source: S03
- [MEDIA] Produce a medium-specific version of a figure (thicker lines, larger text/points, stronger contrast, less detail for projection/talks) rather than reusing an article figure unchanged. | force: SHOULD | tier: B | contexts: talks, posters, print | rationale: each medium imposes different viewing time, size, and distance | source: S03
- [ANNO] Always accompany a figure with a caption that explains how to read it and supplies information (e.g., exact numeric values) that cannot be shown graphically. | force: MUST | tier: B | contexts: articles, posters | rationale: readers should not estimate load-bearing values from bar heights | source: S03
- [ENC] Do not accept plotting defaults; deliberately tune size, fonts, colors, ticks, and markers to the specific plot and message. | force: SHOULD | tier: B | contexts: all tool-generated figures | rationale: defaults are general-purpose and optimal for no specific plot | source: S03
- [COLOR] Use color only for a deliberate reason (e.g., to highlight); default to black/gray and match colormap class (sequential/diverging/qualitative) to the data, avoiding rainbow/jet unless explicitly justified. | force: SHOULD | tier: B | contexts: all figures | rationale: color is either the greatest ally or worst enemy; rainbow hides detail | source: S03
- [CRIT] Do not mislead: show the full/true value range, encode magnitude by the perceived channel (area not radius), and avoid pie and 3-D charts for quantity comparison. | force: MUST | tier: B | contexts: quantitative figures | rationale: implicit and explicit encoding choices can create perceptions absent from the data | source: S03
- [ENC] Use the simplest plot type that conveys the message, with labels, ticks, and title present. | force: SHOULD | tier: B | contexts: all figures | rationale: simpler encodings reduce misreading | source: S03
- [LAYOUT] Remove non-data-ink (excess gridlines, decorative backgrounds, redundant labels, over-precise ticks) unless the element itself carries information. | force: SHOULD | tier: B | contexts: all figures | rationale: chartjunk adds confusion; but junk is context-dependent | source: S03
- [QA] Have colleagues interpret a draft figure to detect misreadings before publication. | force: SHOULD | tier: B | contexts: pre-submission | rationale: catches perception/intent gaps | source: S03
```
