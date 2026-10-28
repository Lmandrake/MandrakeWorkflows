# S02 — Franconeri, Padilla, Shah, Zacks & Hullman, "The Science of Visual Data Communication: What Works" (Psychological Science in the Public Interest, 2021)

## Authority / evidence type
Tier A. Peer-reviewed monograph-length review in *Psychological Science in the Public Interest* (2021, 22(3):110–161), a journal dedicated to authoritative, integrative research reviews. Five expert authors spanning perceptual/cognitive psychology, information visualization, and uncertainty communication; 291 references; NSF- and IES-funded; highly cited (300+ citations per the fetched Crossref metadata). It synthesizes empirical findings across fields, so individual guidelines inherit the evidence tier of the underlying studies it reviews.

**Verification flag:** The full article text is NOT in the acquired files. This card is built from (a) the Crossref/DOI metadata including the author-written abstract, and (b) the APS publisher summary page (`psychologicalscience.org`) which lists the authors' own "key guidelines" and the accompanying Schwabish commentary. A full-text open-access PDF exists (Iowa State faculty archive, per the search snippet) but was not fetched, so specific numbers/effect sizes cannot be quoted; guidelines below are paraphrased from the abstract and the publisher's key-guidelines list.

## Scope
Research-backed guidelines for creating effective, intuitive data visualizations aimed at communicating data to students, coworkers, policymakers, and the general public (not primarily exploratory analysis for experts). Deliberately integrates across visual perception, graph comprehension, information visualization, data-based reasoning, uncertainty representation, and health-risk communication. Organized around three guideline themes: (1) correctly mapping visualized values to real-world concepts, (2) conveying uncertainty and risk, (3) communicating clearly.

## Central claims
- The human visual system can extract broad/global statistics (e.g., means, medians, overall distribution shape) from a well-designed display within a fraction of a second, but comparing between subsets of values is slow and effortful.
- Well-designed visualizations offload work onto the fast visual system; poorly designed ones cause misperceptions, illusions, confusion, and can undermine trust — especially for viewers with low graphical literacy.
- Visualizations map numbers onto visual channels, and channels differ in the precision with which viewers can read the ratio between two values. The authors rank five channels by precision: position (most precise), then length, area, angle, and intensity/color-gradient (least precise). Each channel carries characteristic illusions.
- Effective graphics respect three cognitive constraints: they avoid taxing working memory, actively guide attention to the intended comparison, and respect familiar conventions/associations.
- Communicating uncertainty and risk requires audience-tailored formats; conventional statistical formats (error bars, relative percentages) are often misread by lay/low-numeracy audiences.
- Because effectiveness depends on the audience's graphical literacy, numeracy, and domain knowledge, designers must tailor to the audience rather than assume a universal "best" chart.

## Operationalizable rules
- Prefer higher-precision visual channels for the values you most want read accurately: position > length > area > angle > intensity/color.
- Visualize raw data (histograms, scatterplots) before trusting summary statistics — the visual system extracts distributional structure quickly and can catch what summaries hide.
- Use visual grouping cues to set up the specific comparison you want the viewer to make, because between-set comparisons are slow.
- Reduce working-memory load: convert legends into labels embedded directly in the figure; remove distracting animation and extraneous text.
- Respect conventional associations: "up" means more, "darker" means more; use chart types the audience already knows.
- Choose the graph format that guides the viewer to the intended conceptual message.
- Be deliberate about whether the y-axis starts at zero: not starting at zero can mask real patterns or manufacture illusory ones — decide based on whether ratio or difference is the message.
- When mapping continuous quantities to color, use caution — mapping to different hues can exaggerate differences; also map data to area with care (area is low-precision and distortion-prone).
- Choose color palettes that are legible to color-blind viewers.
- When communicating confidence to a lay audience, avoid error bars; instead show examples of discrete outcomes/values.
- When communicating risk to low-numeracy audiences, use absolute rates rather than relative rates, and natural-frequency framing ("3 out of 10") rather than percentages ("30%").
- Support comprehension for low-knowledge/low-numeracy/low-working-memory audiences even when you feel it is unnecessary.
- (Schwabish commentary, same issue) Show the data; reduce clutter (drop heavy gridlines, redundant ticks, 3D effects); integrate text with graphics (embedded labels/titles); use small multiples for dense data; "start everything with gray" then add color/emphasis only where you want attention. Overriding principle: know your audience.

## Important caveats
- Guidance is audience-dependent: what works for a numerate expert may fail for a low-graphical-literacy general audience, and vice versa. "Know your audience" is the master rule.
- Oriented to communication/presentation contexts; exploratory analysis for experts may weigh trade-offs differently.
- The zero-baseline guidance is explicitly two-sided (not "always start at zero" and not "never") — it depends on whether the message is about ratios or differences.
- Card is built from the abstract + publisher summary, not the full text; nuances, boundary conditions, and the specific studies behind each guideline are not captured here (see verification flag).

## Conflicts with other guidance
- The channel-precision ordering (position > length > area > angle > intensity) is consistent with and corroborated by S15 (Cleveland & McGill's elementary-perceptual-task ranking, replicated by Heer & Bostock). S02 restates it as a design prescription; S15 supplies the empirical ranking.
- Partial tension with a naive/common "always start bar and line axes at zero" rule: S02 says the zero baseline is contextual, not absolute (though for length-encoded bars a zero baseline is generally expected — S02 frames it as a judgment call about masking vs. manufacturing patterns).
- Complements S01: S02's perceptual/cognitive guidelines are the "known perceptual and cognitive principles" that S01 says should justify encoding-level decisions.

## Useful examples
- Five-channel precision ranking (position, length, area, angle, intensity) presented as a designer's tool for choosing an encoding given the data and the accuracy needed.
- "Transform legends into embedded labels" cited by both the authors and the Schwabish commentary as a concrete working-memory reduction.
- Natural-frequency risk framing ("3 out of 10" vs "30%") for health-risk communication to low-numeracy audiences.
- Schwabish's Excel-based redesign of National Center for Education Statistics data illustrating show-the-data / reduce-clutter / small-multiples / start-with-gray.

## Candidate principle IDs
- [ENC/PERC] SHOULD encode the values needing the most accurate reading on the highest-precision channel available, following position > length > area > angle > intensity/color. | force: SHOULD | tier: A | contexts: choosing an encoding for quantitative values | rationale: viewers read ratios far more precisely from position/length than from area/angle/color | source: S02
- [SCI] SHOULD plot the raw distribution (histogram/scatterplot) before relying on summary statistics. | force: SHOULD | tier: A | contexts: analysis and any figure summarizing data | rationale: the visual system extracts distributional structure fast and reveals what summaries hide | source: S02
- [HIER] SHOULD use visual grouping cues to set up the specific comparison the viewer should make. | force: SHOULD | tier: A | contexts: multi-series or multi-category charts | rationale: between-set comparisons are slow; grouping guides attention to the intended one | source: S02
- [ANNO] SHOULD replace separate legends with labels embedded next to the data they name, and remove distracting animation/extraneous text. | force: SHOULD | tier: A | contexts: any figure with a legend or annotation | rationale: reduces working-memory load and back-and-forth lookup | source: S02
- [SEM] SHOULD respect conventional associations (up = more, darker = more) and use chart types the audience already knows. | force: SHOULD | tier: A | contexts: communication to non-expert audiences | rationale: violating familiar conventions forces slow re-mapping and invites error | source: S02
- [SCI] ESCALATE the y-axis zero-baseline decision to whether the message is about ratios or differences; a non-zero baseline can mask real or manufacture illusory patterns. | force: ESCALATE | tier: A | contexts: bar/line charts of magnitudes | rationale: axis truncation is a context-dependent judgment, not a universal on/off rule | source: S02
- [COLOR] MUST choose palettes legible to color-blind viewers, and AVOID multi-hue continuous scales that exaggerate differences. | force: MUST | tier: A | contexts: any use of color to encode data | rationale: ~common color-vision deficiency; hue-based continuous scales distort perceived magnitude | source: S02
- [UNC] SHOULD, for lay audiences, convey confidence with discrete outcome examples rather than error bars, and communicate risk as absolute natural frequencies ("3 out of 10") rather than relative percentages. | force: SHOULD | tier: A | contexts: uncertainty/risk communication to non-expert or low-numeracy audiences | rationale: error bars and relative/percentage framings are frequently misread | source: S02
- [INTENT] MUST tailor the visualization to the audience's graphical literacy, numeracy, and domain knowledge. | force: MUST | tier: A | contexts: all communicative visualization | rationale: effectiveness is audience-dependent; "know your audience" is the master constraint | source: S02
- [LAYOUT] SHOULD reduce clutter (drop heavy gridlines, redundant ticks, 3D effects) and use small multiples for dense data; start neutral (gray) and add emphasis only where attention is wanted. | force: SHOULD | tier: B | contexts: chart styling and layout | rationale: Schwabish practitioner commentary in the same issue; clutter competes for attention | source: S02
