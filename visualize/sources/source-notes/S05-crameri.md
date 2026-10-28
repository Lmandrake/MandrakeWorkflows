# S05 — Crameri, Shephard & Heron, "The misuse of colour in science communication" (Nature Communications, 2020)

## Authority / evidence type
Tier A. Peer-reviewed Perspective in Nature Communications (vol 11, art. 5444, 2020; DOI 10.1038/s41467-020-19160-7; CC BY 4.0; ~1099 citations reported on the page). Grounded in established colour science (CIELAB UCS, CIECAM02-UCS, ΔE_CIEDE2000) and quantitative colormap diagnostics; author (Crameri) is the creator of the Scientific colour maps and StagLab diagnostics. Claims are quantified (e.g., visual error) and tied to standard colour-difference metrics, making this the strongest authority in this cluster on colormap choice. (It is a Perspective, not an experimental study, so recommendations are argued from colour-science principles and diagnostics rather than a new user experiment.)

## Scope
The scientific use of colour maps (colour scales/colour bars) in data visualization and science communication. Covers perceptual uniformity, perceptual order, colour-vision-deficiency (CVD) friendliness, grey-scale readability, colormap classes/types, the failure modes of rainbow/jet and red–green maps, and process recommendations for community/publishers/press. Focused on quantitative colour-encoded data (maps, heatmaps, fields), not general chart layout.

## Central claims
- The accurate representation of data is essential; colour maps with uneven colour gradients or that are unreadable to CVD readers distort data and remain prevalent (rainbow-like and red–green maps).
- A perceptually uniform colour map weights the same data variation equally across the data space; non-uniform maps (rainbow/jet) make the colormap — not the author — perform a "blind interpretation."
- Perceptual non-uniformity introduces measurable visual error: a colour-introduced blind interpretation can diverge from an objective representation by more than seven percent of the displayed data variation.
- Rainbow's yellow is the brightest band and attracts the eye though it is neither at the end nor centre; greenish shades form a wide low-contrast band — so rainbow both fabricates artificial boundaries and hides small-scale variation.
- Perceptual uniformity is necessary but not sufficient; perceptual order (monotonic lightness) is also required so colours can be sequenced without consulting the colour bar and so the map survives grey-scale conversion.
- Roughly 0.5% of women and 8% of men have CVD (higher in some populations); red–green maps at similar luminosity are unreadable to a large fraction of readers. This makes CVD-friendliness a requirement, not an option.
- Colour map class/type must match data nature: sequential, diverging, multi-sequential, cyclic classes; continuous, discrete, categorical types. Only sequential colour maps can be faithfully applied to categorical data.
- "Improved" rainbows (e.g., Google Turbo) still fail: Turbo meets perceptual order but not perceptual uniformity (non-uniform lightness).
- The colour bar must always be included; omitting it is equivalent to dropping axis labels/ticks.
- Scientifically derived colour maps (e.g., batlow, and the Scientific colour maps; plus toolkits Colorbrewer, Matplotlib viridis/magma/plasma/inferno, cividis, cmocean, CET) are freely available, so there is no legitimate reason to keep using distorting maps.

## Operationalizable rules
- Use a perceptually uniform colour map so equal data increments map to equal perceived colour differences (diagnosable via constant ΔE_CIEDE2000 along the bar).
- Require perceptual order: lightness/brightness should increase monotonically so colours can be ranked without the colour bar and remain readable in grey scale.
- Never use rainbow/jet for data visualization ("there is not a single rainbow colour map ... that comes close to being scientific").
- Do not pair red and green at similar luminosity; such maps cannot be read by a large fraction of readers.
- Match colour-map class and type to data nature: use diverging (or multi-sequential) maps for data centred on a meaningful value (e.g., zero); use only sequential maps for categorical data.
- Always include the colour bar on any figure using a colour scale.
- Do not deform a scientific colour map (squeeze/elongate/truncate segments) — this distorts data like unevenly spaced axis ticks.
- Avoid graph/plot types that alter local colour perception: heatmaps with directly connected (touching) colour tiles can shift perceived colours; use gaps between tiles.
- Attend to background lightness/colour, which changes the contrast against displayed data.
- Recognition heuristic: discard any colour map not documented as "scientifically derived" (not perceptually uniform + CVD-friendly).
- Prefer versioned, citable colour-map packages for reproducibility; apply scientific maps during early data diagnosis, not only at publication.

## Important caveats
- Perceptual uniformity is necessary but not sufficient — order and CVD-friendliness are separate required properties; a data-specific custom map does not guarantee uniformity.
- CIECAM02-UCS is described as the current gold standard for perceived colour difference; ΔE_CIEDE2000 (CIELAB UCS) is the metric used here — thresholds/measures are model-dependent.
- The ">7% of displayed data variation" figure is a maximum-type error magnitude cited from the authors' related work (ref 30), not a universal constant for all maps.
- CVD prevalence numbers are population-dependent (near-zero in some sub-Saharan populations; higher in some Scandinavian populations).
- Grey-scale readability assumes "no complicated grey-scale filter is used."
- Two published reader comments push back: one argues equidistant contouring is the most unbiased presentation and that nonlinear maps can add information linear maps cannot; another notes extracting quantitative values from any published colour map is error-prone. These are comments, not peer-reviewed rebuttals, but flag that "always perceptually uniform linear" is contested at the margins for some use cases.

## Conflicts with other guidance
- Strengthens and sharpens S03 (Rougier): both say avoid rainbow, but S05 elevates it from "avoid unless justified" to "essentially never scientific."
- Consistent with S06 (Nature guide): both recommend accessible/CVD-friendly palettes and avoiding rainbow and red–green; S06 endorses the Wong palette for categorical, which aligns with S05's "sequential/categorical" framing.
- Consistent with WCAG 1.4.1 (S16) on not relying on colour that CVD readers cannot distinguish; S05 is about the encoding map itself while WCAG is about redundant cues — complementary, not conflicting.
- Reader-comment tension (see caveats): equidistant contouring vs linear colour maps as the "most unbiased" representation — an edge-case disagreement.

## Useful examples
- Fig 1: familiar images (Curie photo, Earth from space, an apple) shown under jet vs batlow — distortion is obvious for known images, revealing what unknown scientific data suffers invisibly.
- Fig 2: perceptually uniform maps vs rainbow/jet simulated under deuteranopia, protanopia, tritanopia and grey-scale — rainbow fails to give a meaningful smooth gradient; others remain universally readable.
- Fig 3: ΔE_CIEDE2000 (flat for uniform maps), cumulative lightness difference, and resulting visual error (>7% for jet); a flat line looks flat under batlow but becomes unrecognisable under jet.
- Fig 4: jet cannot be sequentially ordered without the colour bar; batlow can, thanks to constant lightness gradient.
- Fig 5/6: colour-map classes (sequential, diverging, multi-sequential, cyclic) and types (continuous, discrete, categorical); user guide matching data nature to map choice.
- Toolkit inventory (Box 2): Colorbrewer, Matplotlib (viridis/magma/plasma/inferno), cividis, cmocean, CET, Scientific colour maps — with properties/limitations.

## Candidate principle IDs
- [COLOR] Encode quantitative data with a perceptually uniform colour map so equal data increments produce equal perceived colour steps. | force: MUST | tier: A | contexts: colour-mapped fields, maps, heatmaps | rationale: non-uniform maps introduce visual error (>7% of data variation) and perform a blind interpretation | source: S05
- [COLOR] Use a colour map with monotonic lightness (perceptual order) so colours can be ranked without the colour bar and survive grey-scale conversion. | force: MUST | tier: A | contexts: sequential/quantitative colour encodings, print | rationale: order enables intuitive reading and B&W robustness | source: S05
- [COLOR] Never use rainbow/jet colour maps for data. | force: AVOID | tier: A | contexts: all data visualization | rationale: no rainbow map is perceptually uniform; it fabricates boundaries and hides detail | source: S05
- [ACCESS] Do not pair red and green at similar luminosity; use CVD-friendly colour maps so data are readable by colour-vision-deficient readers (~8% of men, ~0.5% of women). | force: MUST | tier: A | contexts: any colour-encoded figure | rationale: red–green-at-equal-lightness maps exclude a large fraction of readers | source: S05
- [COLOR] Match colour-map class and type to the data's nature — diverging/multi-sequential for data centred on a meaningful value, and only sequential maps for categorical data. | force: MUST | tier: A | contexts: choosing a colour scale | rationale: mismatched class distorts or misleads | source: S05
- [ANNO] Always include the colour bar on any figure that uses a colour scale. | force: MUST | tier: A | contexts: colour-encoded figures | rationale: omitting it is like dropping axis labels and ticks | source: S05
- [COLOR] Do not deform, truncate, squeeze, or elongate segments of a scientific colour map. | force: AVOID | tier: A | contexts: applying/exporting colour maps | rationale: deforming the colour axis distorts data as unevenly spaced ticks would | source: S05
- [ENC] Avoid plot types that alter local colour perception, e.g., heatmaps with directly touching colour tiles; separate tiles with gaps. | force: SHOULD | tier: A | contexts: heatmaps, tiled colour displays | rationale: adjacent tiles shift perceived individual colours | source: S05
- [QA] Verify a colour map is documented as scientifically derived (perceptually uniform + CVD-friendly) and prefer versioned, citable colour-map packages. | force: SHOULD | tier: A | contexts: colour-map selection, reproducibility | rationale: undocumented maps are likely distorting; versioning aids reproducibility | source: S05
```
