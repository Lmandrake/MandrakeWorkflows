# C1 — Singh, "Data Visualization Best Practices (Matplotlib/Seaborn/Plotly)"

## Authority / evidence type
Medium blog post (Abhavya Singh, 4-min read, Oct 2024), companion source. Self-published, no citations, tool-tutorial framing, author has ~1 follower. TIER D — low weight. Use ONLY as weak corroboration of already-established conventions; never as sole basis for a MUST.

## Scope
Introductory Python plotting guide. Covers (1) picking a chart type for common data situations, (2) library-specific tips for Matplotlib, Seaborn, and Plotly, and (3) general aesthetic tips (color, gridlines, annotations, interactive vs static). Implementation-oriented; not a design-theory source.

## Central claims
- Choose the chart type to match the data question (compare categories, trend over time, relationship, distribution, correlation).
- Reduce clutter: subtle gridlines, fewer ticks/labels.
- Use accessible, colorblind-friendly palettes.
- Annotate key points; always include axis labels and a title.
- Match delivery format: interactive (Plotly) for exploration/dashboards; static high-resolution (Matplotlib/Seaborn) for reports/publications.

## Operationalizable rules
- Bar chart for comparing discrete categories; line chart for time series / continuous trends; scatter for relationship between two continuous variables; histogram/box plot for distributions and outliers; heatmap for correlations among many variables.
- Keep gridlines subtle; use fewer axis ticks and labels to reduce clutter.
- Use colorblind-friendly / accessible palettes (Seaborn and Plotly ship built-in ones).
- Always include axis labels and a title; use annotations to draw attention to key points/trends.
- Use interactivity (zoom/pan/hover) for exploratory analysis and dashboards; use static Matplotlib/Seaborn for clean high-resolution reports and publications.
- (Library mechanics, low relevance: prefer `plt.subplots()` for layout control; use Seaborn themes/palettes and high-level functions; use Plotly `update_layout`/`hover_data` and export options.)

## Important caveats
- Tier D throughout: unsourced, introductory, some typos; treat every claim as corroborating-only, not independent evidence.
- Chart-selection list is a coarse subset of FT's (S04) and adds nothing beyond it.
- Do not elevate any item here to MUST; the strongest role is reinforcing conventions that stronger sources already establish.

## Conflicts with other guidance
- No substantive conflicts; a weaker restatement of FT (chart selection), IBM (subtle grid, accessible color, annotate), and Datawrapper (titles/labels, interactive-vs-static delivery). Where it overlaps, defer to the higher-tier source.

## Useful examples
- Iris pairplot (Seaborn `sns.pairplot(hue="species")`) for exploring pairwise relationships.
- Plotly Express scatter with color-by-category and hover data for interactive exploration.

## Candidate principle IDs
- [SEM] Match chart type to the data question (categories→bar, trend→line, relationship→scatter, distribution→histogram/box, correlations→heatmap) | force: MAY | tier: D | contexts: quick chart selection | rationale: Singh restates common conventions; corroborates S04 at low weight | source: C1
- [PERC] Keep gridlines subtle and reduce tick/label count to limit clutter | force: SHOULD | tier: D | contexts: any chart with grid/axes | rationale: Singh general tips; corroborates IBM S07 grid-density guidance | source: C1
- [COLOR] Use accessible, colorblind-friendly palettes | force: SHOULD | tier: D | contexts: categorical/quantitative color; accessibility | rationale: Singh general tips; weak corroboration of IBM S07 redundant-encoding/accessibility | source: C1
- [ANNO] Include axis labels and a title, and annotate key data points/trends | force: SHOULD | tier: D | contexts: explanatory charts | rationale: Singh general tips; corroborates S07/S13 annotation guidance | source: C1
- [MEDIA] Use interactivity for exploration/dashboards and static high-resolution output for reports/publications | force: MAY | tier: D | contexts: choosing delivery format | rationale: Singh interactive-vs-static tip; corroborates IBM S07 interaction context | source: C1
