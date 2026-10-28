# S09 — Marai, Pinaud, Bühler, Lex & Morris, "Ten simple rules to create biological network figures for communication" (PLOS Comput Biol, 2019)

## Authority / evidence type
Peer-reviewed editorial ("Ten simple rules" genre) in PLOS Computational Biology, DOI 10.1371/journal.pcbi.1007244, published 26 Sep 2019, CC-BY 4.0 open access. Five authors from information-visualization and bioinformatics labs; product of Dagstuhl Seminar 18161. Evidence type: expert-consensus best practices grounded in perception science and viz literature (Munzner, Tufte, Ware, ColorBrewer, controlled studies e.g. Ghoniem 2005 on node-link vs matrix readability). Citation metadata verified in fetched CSL-JSON (34 refs, ISSN 1553-7358). Not itself an experiment.

## Scope
STATIC network figures for scientific PUBLICATION communication (explicitly NOT dynamic/interactive/exploratory tools). Framed for biological networks but authors state the rules follow the general visualization design process and benefit any researcher handling networks — generalizes beyond biology. Covers purpose-setting, representation choice, layout, labels/captions, level of detail, color, marks/channels, layering/separation, multi-figure decomposition, and 3D.

## Central claims
- Rule 1 (most important): determine figure PURPOSE and assess the network (scale, type, structure) before drawing; write the caption first; the intended message dictates data included, focus, and encoding sequence.
- Node-link is the default but not always appropriate; adjacency matrices suit dense networks and readable labels; fixed layouts (maps, Circos), and implicit layouts (icicle/sunburst/treemap) suit trees.
- Spatial arrangement carries meaning via Gestalt grouping even when unintended; proximity/centrality/direction are read as relatedness/importance/flow — wrong layout misleads.
- Labels and captions must be legible and self-contained; figure and caption should each stand alone.
- Reduce to the right level of detail via aggregation (item- or edge-level) and locally varying detail.
- Use color responsibly: get it right in grayscale first; avoid red-green; luminance for ordinal, hue for categorical, saturation sparingly for emphasis.
- Marks and channels have semantics: arrows imply function/sequence; no-arrows imply structure; identity channels (position/color/shape) vs magnitude channels (size/area/volume).
- Use layering and separation to raise key information above clutter; split into multiple figures when >3 non-redundant visual mappings compete.
- Avoid unjustified 3D; depth is justified only when the task is inherently 3D (e.g., molecular structure).

## Operationalizable rules
- Write the target caption/message before drawing; place salient content centrally, larger, or annotated.
- If the network is dense or labels clutter a node-link view, switch to an adjacency matrix (with an optimized row/column reordering algorithm); use implicit layouts for trees.
- Encode intended relatedness through proximity/centrality/direction deliberately; use force-directed for attraction-by-similarity, MDS for cluster detection; don't let an arbitrary layout imply structure.
- Set label font >= caption font size; keep all text horizontal; ensure high text/background contrast (black-on-white or white-on-black); use direct labeling over numeric legend pointers when uncluttered; provide a zoomable high-res version when labels can't grow.
- Make caption tell the reader what to notice and define all unusual markers, channels, and colormaps.
- Aggregate periphery/less-relevant structure (dimensionality reduction, spatial grouping, edge bundling) to cut clutter while keeping context.
- Get the figure right in grayscale first; avoid red-green encodings; use luminance progressions for ordinal/quantitative data and qualitative hue sets only for categories; use saturated color sparingly on small marks for attention; use transparency to push elements to the background.
- Use arrows only for asymmetric/functional relations; omit them for structural relations; match identity vs magnitude channels to categorical vs quantitative attributes.
- Layer by weight/color/opacity/size/shading: de-emphasize context, emphasize key nodes/edges.
- Count visual properties mapping data; if >3 and non-redundant and their interaction isn't the point, split into multiple figures (overview+detail, or search-/details-first).
- Use 3D only when the task requires 3D shape understanding; otherwise map the extra attribute to a 2D channel (e.g., marker size) to avoid occlusion/foreshortening errors.

## Important caveats
- Rules are for STATIC publication figures; interactive/dynamic tools may license different choices (e.g., 3D with navigation, occlusion mitigated by motion parallax at a cost).
- Rules are "tightly interconnected" and deliberately not a decision tree; they trade off against each other and even the paper's own example figures may violate some rule while illustrating another.
- The ">3 visual properties" heuristic is a rule of thumb, not a hard threshold; redundant mappings for emphasis and intentional interactions are exempt.
- Biology-specific examples (PPI, GBM, Cytoscape) — abstract the perceptual principle from the domain.

## Conflicts with other guidance
- Convergent with S08 (IBM): purpose-first, legends/captions, no color-alone/no red-green, semantic use of arrows/line styles, distinct encodings only when meaningful.
- Convergent with S11 (Esri) on visual hierarchy/figure-ground (layering & separation ~ figure-ground; centrality ~ visual center) and with general perception guidance.
- Tension with S12 (NASA SVS), which embraces 3D globe/volumetric renderings: Marai's "avoid unjustified 3D" is reconcilable because NASA's 3D depicts inherently spatial phenomena (the justified-3D exception) and is often interactive/animated rather than static.

## Useful examples
- Fig 1: same GBM proteins shown two ways — data-flow arrows + quantitative (yellow-green) colormap for a functional message vs undirected edges + divergent (red-blue) colormap for a structural message. Encoding follows purpose.
- Fig 2: adjacency matrix reveals an exosome-complex cluster that is buried by clutter in the equivalent node-link diagram.
- Fig 4: enlarging labels by improving layout use of space; provide zoomable hi-res when impossible.
- Fig 5: four-step aggregation (>400-protein hairball -> collapsed complex cores) to reach a legible figure.
- Fig 6: bad vs good color — saturated non-colorblind-safe scheme with low-contrast gray text vs ColorBrewer sequential maps and black text.
- Fig 8: layering — de-weight non-key edges, enlarge key nodes, make non-key nodes transparent, subtle shading behind key nodes.
- Fig 9: split one cluttered 51-node view into three focused views (degree / MCODE / neighbors).
- Fig 10: 3D cylinder heights misread as perspective foreshortening — 2D marker size would be clearer.

## Candidate principle IDs
- [INTENT] Determine the figure's purpose and message (write the caption first) and assess the network before choosing any encoding | force: MUST | tier: A | contexts: network figures, any explanatory graphic | rationale: message dictates data shown, focus, and encoding sequence; skipping this violates downstream best practices | source: S09
- [NET] Do not default to node-link; switch to an adjacency matrix for dense networks (with optimized reordering) or implicit layouts for trees when node-link clutters | force: SHOULD | tier: B | contexts: dense/large networks, hierarchies | rationale: matrices show every edge and readable labels where node-link produces hairballs | source: S09
- [NET] Treat spatial position as meaningful (proximity=relatedness, centrality=importance, direction=flow) and choose a layout that reinforces the true structure, not an incidental one | force: MUST | tier: A | contexts: node-link layouts | rationale: Gestalt grouping makes readers infer relationships from position even when unintended | source: S09
- [ANNO] Make labels legible (>= caption font, horizontal, high contrast) and make figure and caption each stand alone, defining every unusual marker and colormap | force: MUST | tier: A | contexts: publication figures, network figures | rationale: illegible or dependent captions block comprehension; direct labeling lowers cognitive load | source: S09
- [HIER] Reduce to the right level of detail via aggregation and locally varying detail to cut clutter while preserving context | force: SHOULD | tier: B | contexts: large networks, complex figures | rationale: excess detail obscures the relationship the figure is meant to convey | source: S09
- [COLOR] Get the figure right in grayscale first; avoid red-green, encode ordinal data by luminance and categories by hue, and use saturation sparingly for emphasis | force: SHOULD | tier: A | contexts: any colored figure, colorblind accessibility | rationale: luminance is the strongest perceptual channel and ~8% of males confuse red-green | source: S09
- [ENC] Match marks and channels to data semantics — arrows for asymmetric/functional relations only, identity channels for categories, magnitude channels for quantities | force: SHOULD | tier: B | contexts: network and diagram encoding | rationale: arrows are read as function/sequence and mismatched channels mislead | source: S09
- [HIER] Use layering and separation (weight, luminance, opacity, size, shading) to raise key information above clutter | force: SHOULD | tier: B | contexts: cluttered figures | rationale: de-emphasizing context and emphasizing key elements directs attention to the message | source: S09
- [MEDIA] If more than three non-redundant visual properties map data, split the figure into multiple focused figures (overview+detail) | force: SHOULD | tier: C | contexts: information-dense figures | rationale: too many competing mappings prevent readers from finding the point | source: S09
- [ENC] Avoid 3D unless the task inherently requires 3D shape understanding; otherwise map the extra attribute to a 2D channel | force: AVOID | tier: B | contexts: static network/data figures | rationale: depth causes occlusion, perspective distortion, and foreshortening misreads | source: S09
