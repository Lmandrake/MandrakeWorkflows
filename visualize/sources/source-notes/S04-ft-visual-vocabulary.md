# S04 — Financial Times "Visual Vocabulary" (chart-doctor repo README)

## Authority / evidence type
Practitioner/newsroom authority. Produced by the Financial Times Visual Journalism Team as a chart-literacy training resource for designers and journalists; inspired by Schwabish & Ribecca's "Graphic Continuum." Codifies editorial best practice rather than controlled experiment, but the README annotates each family with links to empirical and expert sources (Cleveland & McGill, Kosara, Few, etc.). Tier B — expert consensus / house style, not primary perceptual research.

## Scope
A chart-SELECTION resource. Maps analytic intent (what you want the data to say) to candidate chart families and specific chart types within each family. Covers nine analytic-intent categories: Deviation, Correlation, Ranking, Distribution, Change over Time, Part-to-whole, Magnitude, Spatial, Flow. (Uncertainty, Animation, Interactivity, Map projections, and Colour are listed as unfinished "Todo" placeholders — no substantive content.) Explicitly NOT a how-to-build-charts guide; it teaches recognizing when a chart type fits.

## Central claims
- Chart choice should follow from the analytic relationship you want to emphasize, not from chart aesthetics.
- Each analytic intent has a family of appropriate chart types, each with trade-offs; the same data can be shown many ways depending on the story.
- Readers infer meaning (including causality) from chart form, so the designer must choose forms that support the intended reading.
- Many popular chart types (pie, stacked bar) carry known perceptual weaknesses and should be used with caution.

## Operationalizable rules
- Deviation intent (variation +/- from a reference point such as zero, a target, or a long-term average): use diverging bar, diverging stacked bar (esp. survey sentiment agree/neutral/disagree), spine chart, surplus/deficit filled line.
- Correlation intent (relationship between 2+ variables): use scatterplot, line+column (amount vs rate), connected scatterplot, bubble (3rd variable via size), XY heatmap. Warn: readers assume shown relationships are causal unless told otherwise.
- Ranking intent (position in ordered list matters more than absolute value): use ordered bar, ordered column, ordered proportional symbol, dot strip plot, slope, lollipop. Sort bars into order; highlight points of interest.
- Distribution intent (values and how often they occur): use histogram (keep column gaps small), boxplot, violin plot, population pyramid, dot strip plot, dot plot, barcode plot, cumulative curve.
- Change-over-time intent: use line (add markers if data irregular), column (usually one series only), line+column, stock price (OHLC/hi-lo), slope, area (with care), fan chart (projection uncertainty), connected scatterplot, calendar heatmap, Priestley timeline, circle timeline, seismogram. Choose the time period to give suitable context.
- Part-to-whole intent: use stacked column, proportional stacked bar, pie, donut, treemap, Voronoi, arc, gridplot, Venn, waterfall. If only component size matters, use a magnitude chart instead.
- Magnitude intent (size comparisons, usually counted quantities): use column, bar (good for long category labels / non-time-series), paired column/bar, proportional stacked bar, proportional symbol, isotype/pictogram, lollipop, radar, parallel coordinates.
- Spatial intent (only when precise location or geographic pattern matters most): use basic choropleth (rates not totals; sensible base geography), proportional symbol (totals not rates), flow map, contour map, equalised cartogram, scaled cartogram, dot density, heat map.
- Flow intent (volume/intensity of movement between states): use Sankey/river plot, waterfall, chord, network.
- Column/bar for magnitude must start the axis at 0. Isotype: whole numbers only (never slice a figure to represent a decimal). Choropleths should encode rates/ratios, not totals.

## Important caveats
- Tier B: reflects FT editorial judgment; individual "rules" are guidelines with acknowledged exceptions (the README links to debates, e.g. whether a line-chart y-axis must start at zero).
- Stacked bars and pies are flagged as perceptually weak (linked critiques by Kosara, Few) — the presence of a type in a family does NOT mean it is the best encoding.
- Uncertainty, Colour, Map projections, Interactivity, Animation sections are empty TODO stubs — do not cite this source for those topics.
- The resource lists candidate types; it does not give a deterministic single-answer recommendation (contrast with Draco).

## Conflicts with other guidance
- The axis-zero question is presented as contested (links argue both "line charts need not start at zero" and "bar charts must") — this partially conflicts with rigid "always start at zero" rules; FT itself mandates zero for columns/bars but not lines.
- Includes pie/donut/stacked bar as legitimate options where stricter perceptual sources (and Cleveland-McGill lineage) would discourage them. Aligns with IBM/Datawrapper on annotating patterns and using rates on maps.

## Useful examples
- Diverging stacked bar for survey sentiment (agree/neutral/disagree).
- Population pyramid described as "back to back histograms" for age/sex breakdown.
- Fan chart for growing uncertainty in future projections.
- Connected scatterplot for paired time series (cites Kosara).
- Cartogram for election maps (cites FT Brexit coverage).

## Candidate principle IDs
- [SEM] Choose the chart family from the analytic relationship you want to emphasize (deviation, correlation, ranking, distribution, change-over-time, part-to-whole, magnitude, spatial, flow) rather than from aesthetic preference | force: SHOULD | tier: B | contexts: chart selection; explanatory/editorial charts | rationale: FT's core intent→family mapping is the organizing principle of the whole resource | source: S04
- [SEM] For deviation from a reference point (zero, target, or average) use diverging/spine/surplus-deficit encodings that make +/- direction explicit | force: SHOULD | tier: B | contexts: signed values; survey sentiment; budget balances | rationale: FT Deviation family | source: S04
- [SEM] For part-to-whole where only component magnitude matters, prefer a magnitude chart over a part-to-whole chart | force: SHOULD | tier: B | contexts: proportion vs size decisions | rationale: FT explicitly redirects part-to-whole to magnitude when share is not the point | source: S04
- [ENC] Bars/columns encoding magnitude must have a value axis anchored at zero | force: MUST | tier: B | contexts: bar/column magnitude charts | rationale: FT magnitude notes state column "must always start at 0"; length encoding is read from baseline | source: S04
- [ENC] On maps, encode rates/ratios with choropleth and totals/counts with proportional symbols, not the reverse | force: SHOULD | tier: B | contexts: thematic maps | rationale: FT Spatial guidance; choropleth of totals misleads by area | source: S04
- [SEM] Reserve maps for when precise location or geographic pattern is the most important thing to the reader; otherwise use a non-spatial chart | force: SHOULD | tier: B | contexts: geographic data with a non-spatial story | rationale: FT Spatial preamble and "When Maps Shouldn't Be Maps" | source: S04
- [ENC] Use isotype/pictograms only for whole-number counts and never slice a figure to represent a fraction | force: AVOID | tier: B | contexts: pictogram/isotype magnitude charts | rationale: FT isotype note | source: S04
- [ANNO] When a chart shows a correlation, annotate or caption to prevent unintended causal inference by readers | force: SHOULD | tier: B | contexts: scatter/correlation charts | rationale: FT Correlation warning that readers assume causality | source: S04
- [CRIT] Treat pie and stacked-bar encodings as perceptually risky and justify their use against ranked/position alternatives | force: SHOULD | tier: B | contexts: part-to-whole with fine comparisons | rationale: FT links to critiques (Kosara "stacked bars are the worst", pie-chart debate) | source: S04
