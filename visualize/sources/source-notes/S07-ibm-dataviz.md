# S07 — IBM Design Language: Data Visualization (Design → Basics + Usage)

## Authority / evidence type
Corporate design-system authority (IBM Design Language / Carbon Design System). Codified house guidelines for a large product portfolio; expert consensus and enterprise convention rather than experimental evidence. Tier B. Two pages: Basics (chart anatomy, color, interaction, motion) and Usage (product/dashboard vs marketing applications, consistency across related charts).

## Scope
Design guidance for building distinctive, functional, accessible data visualizations across IBM product UI and marketing contexts. Covers: chart anatomy (title, labels, legend, axes/ticks/grid), restrained semantic color, texture/markers as color substitutes, interaction (overview→zoom/filter→details-on-demand), motion, and consistency across a set of related charts. Focused on communication clarity and readability, not chart-type selection.

## Central claims
- A chart's title should carry the main insight the data reveals, not merely name the dataset.
- Every visual element (including every color) must earn its place; restraint and contrast direct attention to the message.
- Direct labels on the chart are preferable to detached legends where possible.
- Related charts in a dashboard should be designed as a consistent set that works together, not independently.
- Color choice affects recognition speed, accessibility, and meaning — and even the absence of color conveys information.

## Operationalizable rules
- Write the title to reflect the main insight; avoid long/over-descriptive titles ("Concise title" good vs "Long and too descriptive title" bad).
- Use labels directly on the chart to avoid long legends; keep all text concise and easy to understand.
- Legend must define the association of each visual property (color, shape, size) to its data meaning.
- Use the correct density of gridlines and labels; do not fill the chart frame with too many elements (it impairs interpretation).
- Every color should have a reason for being there; use greys to keep non-focal data visible without distracting, and reserve strong/consistent colors for key metrics.
- Create sharp contrast between elements to focus attention; ensure contrast is sufficient to read on-screen in low light / with light greys (accessibility).
- Use categorical palettes to maximize contrast between unrelated data; use sequential palettes for ordered relationships/hierarchies and sequential/diverging palettes to represent quantity.
- Reinforce color meaning with a second visual channel (shape, line, pattern) so the focal point is recognizable and so charts work when color is unavailable (patterns, marker shapes, varying line weights, element density).
- Interaction: present crucial points clearly up front; follow "overview first, zoom and filter, then details on demand"; do not hide important information behind interaction.
- Motion: use entrance/exit motion to reinforce hierarchy/orientation; do not let different transitions communicate contradicting information.
- Consistency: in complex monitoring/decision environments, design a set of charts that work together rather than independently.

## Important caveats
- Tier B corporate guideline; some items (motion, interaction) are UI/product-specific and may not apply to static publication or scientific figures.
- Guidance is qualitative ("correct density", "sharp contrast") without numeric thresholds — needs local calibration.
- Color psychology/cultural-context advice is stated at a high level without specifics.

## Conflicts with other guidance
- Broadly aligns with Datawrapper (direct labels over legends; insight-bearing titles) and with FT (restrained semantic color, rates on maps not covered here). No direct conflicts within the cluster. The "reinforce color with a second channel" rule reinforces colorblind-safety points echoed weakly in C1.

## Useful examples
- Title contrast: "Concise title" (good) vs "Long and too descriptive title" (bad).
- Grid density: "Use the correct density of grid lines and labels" vs "Don't use too many elements or the chart will be difficult to read."
- Greys for background data + one accent color for the key metric.
- "Animation emphasizes changes" (good) vs "Animation hides connections" (bad).

## Candidate principle IDs
- [ANNO] Write the chart title to state the main insight the data reveals, not just to name the dataset | force: SHOULD | tier: B | contexts: explanatory charts; dashboards | rationale: IBM "title should reflect the main insight"; insight-titles improve takeaway | source: S07
- [ANNO] Prefer direct labels on the chart over a detached legend whenever placement allows | force: SHOULD | tier: B | contexts: multi-series charts where labels fit | rationale: IBM "use labels directly on the chart to avoid long legends"; reduces lookup cost | source: S07
- [PERC] Control gridline and label density so the frame is not overfilled with elements | force: SHOULD | tier: B | contexts: any chart with axes/grid | rationale: IBM axes/ticks/grid guidance; clutter impairs interpretation | source: S07
- [COLOR] Give every color a reason; use greys for non-focal data and reserve strong/consistent color for key metrics | force: SHOULD | tier: B | contexts: categorical and emphasis coloring | rationale: IBM restrained-semantic-color guidance; contrast directs attention | source: S07
- [COLOR] Match palette type to data type — categorical for unrelated categories, sequential for ordered/quantity, diverging for signed quantity | force: SHOULD | tier: B | contexts: encoding a variable to color | rationale: IBM color-palette guidance | source: S07
- [COLOR] Reinforce color-encoded meaning with a second channel (shape, pattern, line weight) so charts remain legible without color | force: SHOULD | tier: B | contexts: accessibility; print/grayscale; color-blind readers | rationale: IBM texture/markers section; redundant encoding preserves meaning when color fails | source: S07
- [HIER] Design a set of related charts (e.g., a dashboard) to be consistent and work together rather than independently | force: SHOULD | tier: B | contexts: dashboards; multi-panel figures | rationale: IBM Usage: consistent chart sets for monitoring/decision environments | source: S07
- [MEDIA] For interactive views, show crucial points up front and follow overview→zoom/filter→details-on-demand; never hide important information behind interaction | force: SHOULD | tier: B | contexts: interactive/exploratory visualizations | rationale: IBM interaction guidance (Shneiderman mantra) | source: S07
- [PERC] Ensure contrast is sufficient to read on-screen in low light and with light greys | force: SHOULD | tier: B | contexts: screen-delivered charts; accessibility | rationale: IBM readability/hierarchy guidance | source: S07
