# S13 — Datawrapper Academy: "Annotating your visualization in the Annotate tab"

## Authority / evidence type
Vendor documentation / practitioner guidance (Datawrapper Academy). Datawrapper is a widely used newsroom charting tool; this is its house guidance on annotation and chart framing text. Expert convention, not experiment. Tier B (product-specific but reflects strong dataviz-journalism norms). Last updated 2024-04-08.

## Scope
How to use the Annotate tab's text elements — title, description, notes, byline, data source (+ link), and alternative description (screen-reader) — and recommendations for what each should contain. Focused on the textual/annotation and transparency/accessibility layer around a chart, not chart-type selection or encoding.

## Central claims
- The title is one of the first things a reader sees and strongly shapes comprehension; the best titles state the single key takeaway.
- Every chart should carry supporting text: a descriptive subtitle/description, footnote-style notes for caveats, a cited data source (name + URL), a byline, and a screen-reader alternative description.
- Transparency (naming and linking the data source) signals trustworthiness and lets readers dig deeper.
- Accessibility (alternative descriptions) is strongly recommended so vision-impaired readers get the main statements.

## Operationalizable rules
- Prefer a title that highlights the most interesting aspect / the one key statement you want readers to remember (insight title) over a bare descriptive label or a vague question.
- Give even a hidden chart a title (aids findability in the chart library) — you may hide it when surrounding text already makes the subject clear.
- Use the description (below title) to pack in context: what exactly is shown, when (time span), where, why, how the data was recorded, sample size.
- Use notes (below chart) as footnotes to flag data abnormalities/exclusions (e.g., "California rates from Jan/Feb 2016 not included").
- Always provide source name AND source URL to increase transparency; for multiple sources, list them in notes with HTML links.
- Add a byline to attribute the chart's author/organization (helps when shared on social media).
- Always add an alternative description for screen readers conveying the main statements.

## Important caveats
- Tier B and tool-specific: the mechanics (Annotate tab, HTML/CSS in notes, checkbox to hide title) are Datawrapper-specific, but the underlying principles (insight titles, cite sources, footnote caveats, alt text) are general.
- This article does NOT cover direct-labeling vs legends, label-collision avoidance, or legend reduction in its own text — those Datawrapper topics live in other Academy articles; do not attribute label-collision specifics to this file (flag as not-in-source). The special guidance's "direct labels / label-collision / reduce detached legends" is only weakly supported here (general annotation ethos), so keep those as low-confidence unless corroborated by another source.

## Conflicts with other guidance
- Fully consistent with IBM (insight-bearing titles) and FT (annotate patterns readers should see). No conflicts within the cluster. Adds a transparency/accessibility layer (source citation, alt text) not emphasized by FT/IBM basics.

## Useful examples
- Title styles: descriptive ("Cranes at Lake Hornborga, 2014-2021") vs question ("When are the most cranes...?") vs recommended insight ("In the last seven years, most cranes have been at Lake Hornborga between March 20 and April 8").
- Description example: "Unemployment rates in % in all US states, March 2016."
- Notes example: "California unemployment rates from Jan and Feb 2016 not included in the calculation."
- Source example: "US Bureau of Labour Statistics, August 2017."

## Candidate principle IDs
- [ANNO] Write the title to state the single key takeaway you want the reader to remember, not merely to label the subject | force: SHOULD | tier: B | contexts: explanatory/editorial charts | rationale: Datawrapper's core title recommendation; title dominates comprehension | source: S13
- [ANNO] Provide a description that supplies full data context — what, when (time span), where, why, how recorded, sample size | force: SHOULD | tier: B | contexts: published/shared charts | rationale: Datawrapper description guidance | source: S13
- [ANNO] Use footnote-style notes to disclose data caveats, exclusions, and abnormalities | force: SHOULD | tier: B | contexts: any chart with data quirks | rationale: Datawrapper notes guidance; caveats belong near the chart | source: S13
- [ANNO] Always cite the data source by name and, whenever possible, link to it | force: MUST | tier: B | contexts: published charts; transparency-critical work | rationale: Datawrapper: source signals trustworthiness and enables verification | source: S13
- [ANNO] Provide an alternative text description conveying the main statements for screen-reader / vision-impaired readers | force: SHOULD | tier: B | contexts: web-delivered charts; accessibility | rationale: Datawrapper strongly recommends alt descriptions | source: S13
- [ANNO] Attribute the chart with a byline (author and/or organization) | force: MAY | tier: B | contexts: charts shared publicly/socially | rationale: Datawrapper byline guidance | source: S13
