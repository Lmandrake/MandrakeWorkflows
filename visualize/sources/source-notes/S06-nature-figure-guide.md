# S06 — Nature Research Figure Guide ("Preparing figures — our specifications" + "Building and exporting figure panels")

## Authority / evidence type
Tier B. Publisher (Springer Nature) house specification for figures — authoritative and normative *for Nature-family submissions*, and a strong de facto standard for scientific publishing generally. Not peer-reviewed research; it is a production/style requirement document. It explicitly grounds its accessibility stance in external standards (WCAG 2.1 level AA) and cites Wong (Nat. Methods 2011) for its colour-blind-safe palette, so the accessibility content inherits stronger backing. Treat numeric specs (sizes, dpi, formats) as authoritative-but-venue-specific rather than universal perceptual thresholds.

## Scope
Concrete production specifications for preparing, building, and exporting scientific figure panels: graph requirements, colour space, image resolution, scale bars, typography, panel sizing/arrangement, accessibility (colour + contrast), decorative-element policy, image integrity, and accepted file formats. Aimed at final publication-ready artwork.

## Central claims
- Clear data presentation is imperative; certain features are required and others avoided to maximize interpretability.
- Figures should be accessible: use colour-blind-safe palettes, avoid red/green and rainbow scales, and provide keys/keylines rather than colour descriptions in captions.
- Text must be legible, editable, and in standard sans-serif fonts sized to the final output.
- Figures should be submitted at (or near) final print size; production may downscale further.
- Panels should be arranged neatly, alphabetically, minimizing white space, with size driven by content/legibility.
- Vector artwork (editable text/lines) is required for main figures; raster images need sufficient resolution.
- Image integrity policies apply to all digital images.

## Operationalizable rules
Graphs — require: axis lines and tick marks present; all axes labelled with units in parentheses, e.g. "Data (unit)"; an accessible colour palette (cites Wong 2011); legible text (minimum 5 pt); standard fonts (Arial/Helvetica). Avoid: background gridlines, superfluous/decorative icons, drop shadows, patterns (use solid colours to differentiate sectors), text on busy/hard-to-read backgrounds, overlapping text, coloured text (use keylines/keys with black text instead).

Typography: sans-serif (Helvetica or Arial preferred); maximum text size 7 pt, minimum 5 pt; panel labels 8-pt bold, upright, lowercase a, b, c; amino-acid sequences in Courier one-letter code, lines of 50 or 100 characters; Symbol font for Greek/glyphs; do not outline text; embed fonts (TrueType 2 or 42, not TrueType 3). For matplotlib set `Matplotlib.rcParams['pdf.fonttype']=42` to keep text editable.

Colour & contrast: supply artwork in RGB (wider gamut than CMYK; print converts to CMYK automatically); use accessible/CVD-safe combinations and distinctive hues; avoid red/green and rainbow scales; use high-contrast text with contrast ratio > 4.5 (black or white text on high-contrast background); prefer keys/keylines pointing to black text over coloured text/colour descriptions. Wong palette (hex/RGB/CMYK given): Black #000000, Orange #e69f00, Sky blue #56b4e9, Bluish green #009e73, Yellow #f0e442, Blue #0072b2, Vermillion #d55e00, Reddish purple #cc79a7.

Sizing: print widths 89 mm (single column) and 183 mm (double column); max Nature figure height 170 mm (leaving room for legend); submit at the smallest appropriate size with fonts between 5–7 pt.

Images/resolution: photographic images minimum 300 dpi (online proof max 450 dpi; 450+ recommended for highest quality; for export min 450 dpi); artificially upsampling does not improve quality. Extended Data images supplied at max 300 dpi. Scale bars: keep on a separate editable layer (do not flatten); use scale bars, not magnification factors.

Decorative icons: replace with simple text labels; remove superfluous icons (they can be misinterpreted, e.g., mouse vs rat, ambiguous male/human); simple context-adding icons are acceptable.

Export/formats: main figures require vector files with editable layers — preferred .ai, .eps, .pdf (retain editing); acceptable: layered PSD (no text effects/flattening), PowerPoint (save to PDF first), plain SVG (not Inkscape SVG), Excel, .ps. Not accepted: .jpeg, .tiff, .png, Canvas, DeltaGraph, Tex, ChemDraw, SigmaPlot, Coreldraw. Limit files to ~50 MB; embed (do not link) components. Extended Data: RGB, max 300 dpi, ≤10 MB, export as .jpeg (preferred)/.tiff/.eps; single-page sizing; naming CorrespondingAuthorSurname_EDfig1.jpg / _EDtable1.jpg.

## Important caveats
- These are Nature-family submission requirements; specific numbers (5–7 pt text, 89/183/170 mm, 300/450 dpi, accepted formats) are venue-specific production constraints, not universal perceptual optima.
- The ">4.5 contrast ratio" for text and "WCAG 2.1 level AA" adherence are stated for Nature.com "wherever possible" — an aspiration for the site, applied to figures as guidance.
- The "maximum text size 7 pt" is a house ceiling; other contexts (slides, posters) demand much larger text — do not transfer the ceiling out of print-figure context.
- Extended Data accepts raster (.jpeg/.tiff) while main figures require vector — the format rule is context-split.

## Conflicts with other guidance
- Reinforces S05 (Crameri) and S16 (WCAG): avoid red/green and rainbow; provide redundant, non-colour cues (keys/keylines); CVD-safe palette. No conflict.
- The "avoid patterns" rule (use solid colours to differentiate sectors) is in mild tension with WCAG 1.4.1's endorsement of pattern-plus-colour (S16 technique G111) as a redundant cue — S06 prefers keys/keylines/solid fills over hatching, prioritizing print clarity over pattern redundancy.
- The 5-pt minimum text / 7-pt maximum is far below slide/poster legibility norms (and below typical 17-pt slide floors); strictly a print-figure spec.
- Complements S03 (Rougier) on removing decoration/chartjunk and on captions/keys.

## Useful examples
- Wong colour-blind-safe categorical palette with normal/protanopic/deuteranopic previews and hex/RGB/CMYK values (directly reusable).
- Paired avoid/recommended illustrations: missing vs present tick marks + unit labels; red/green vs contrast-retaining palette under CVD filter; coloured legend text vs coloured boxes with black text; patterns vs solid fills; overlapping labels vs rearranged labels; keylines to black text vs coloured labels; CMYK vs RGB supply; low-res vs 300 dpi; flattened vs layered scale bar; outlined vs editable text; non-standard vs standard fonts; poorly vs neatly arranged panels; low-contrast vs high-contrast text on background; ambiguous icons vs text labels.

## Candidate principle IDs
- [ACCESS] Use an accessible, colour-vision-deficiency-safe categorical palette (e.g., the Wong 8-colour palette) and avoid red/green pairings and rainbow scales. | force: MUST | tier: B | contexts: publication figures, categorical colour | rationale: ensures datasets remain distinguishable under colour blindness | source: S06
- [ACCESS] Provide keys/keylines pointing to black text rather than coloured text or colour descriptions in captions. | force: SHOULD | tier: B | contexts: legends, labels | rationale: CVD readers struggle to map colour-name descriptions to the figure | source: S06
- [ACCESS] Use high-contrast text (black or white on a high-contrast background, contrast ratio > 4.5) and avoid coloured text. | force: MUST | tier: B | contexts: text on figures | rationale: legibility for low-vision and CVD readers | source: S06
- [LAYOUT] Design figures at final output size and submit at the smallest appropriate size, keeping fonts within the venue's range (5–7 pt for Nature print). | force: MUST | tier: B | contexts: print publication figures | rationale: production downscaling can render undersized text illegible | source: S06
- [ANNO] Include axis lines, tick marks, and axis labels with units in parentheses, e.g., "Data (unit)". | force: MUST | tier: B | contexts: graphs | rationale: unlabeled/untick'd axes prevent correct interpretation | source: S06
- [LAYOUT] Arrange multi-panel figures neatly and in alphabetical order, sizing each panel by its content and legibility while minimizing white space. | force: SHOULD | tier: B | contexts: multi-panel figures | rationale: orderly arrangement aids reading and space efficiency | source: S06
- [LAYOUT] Remove decorative elements — background gridlines, drop shadows, patterns, superfluous icons — and replace ambiguous icons with text labels. | force: SHOULD | tier: B | contexts: publication figures | rationale: decoration adds no data and can be misinterpreted | source: S06
- [MEDIA] Export main figures as vector artwork with editable, embedded-font text (.ai/.eps/.pdf); do not outline text; supply raster images at sufficient resolution (≥300 dpi photos, do not upsample). | force: MUST | tier: B | contexts: figure export for publication | rationale: vector text stays editable/scalable; upsampling cannot restore detail | source: S06
- [MEDIA] Supply figure artwork in RGB colour space (print conversion to CMYK is automatic). | force: SHOULD | tier: B | contexts: figure export | rationale: RGB offers wider gamut and faithful digital reproduction | source: S06
- [CRIT] Keep scale bars (with labels) on a separate editable layer and use scale bars rather than magnification factors; comply with image-integrity policy. | force: MUST | tier: B | contexts: micrographs/photographic images | rationale: flattened scale bars pixelate and resize incorrectly; integrity is required | source: S06
```
