# S08 — IBM Design Language: Technical Diagrams (Design + Usage)

## Authority / evidence type
Enterprise design-system guidance from IBM's official Design Language site (technical-diagrams Design and Usage pages, last updated 24 Aug 2026). Prescriptive brand/design standard backed by a component library and starter kits, not empirical study. Authoritative as an internally-consistent design grammar; claims are conventions and accessibility rules rather than tested findings.

## Scope
Creation of technical diagrams for documentation, presentations, and collateral that appear OUTSIDE product screens (for in-product diagrams IBM redirects to Carbon components). Covers node/connector vocabulary, iconography, typography, grid/spacing, color, and supplemental elements (legends, line styles, indicator badges, multiple-instance markers). Diagram types named: tree/dendrogram, network, swimlane, org chart, flow/process, IT architecture.

## Central claims
- A technical diagram is a defined visual GRAMMAR of nodes (bullet/small/large) and connectors (links/edges) chosen before drawing; node meaning depends on diagram type and use case.
- Clarity and legibility are paramount and must never be sacrificed to tool limitations.
- Accessibility requires redundant encoding: never rely on color alone; pair it with labels, line styles, or icons.
- A legend is always required, even when using a predefined color set, documenting color/line/style/shape conventions.
- Node types should be distinguished only when they carry a real semantic difference; redundancy across shape/style/color/badges is discouraged.
- Structural discipline (8px grid, orthogonal routing, consistent artboards, monochromatic nodes) produces orderly, interpretable diagrams.

## Operationalizable rules
- Define the node/connector vocabulary (types, shapes, line styles, endings) before drawing; publish it in a legend.
- Choose node size by information load: bullet (dense trees/networks, no long text), small (concept/overview, always with icon), large (long text, columns/rows, swimlanes/org charts).
- Do not mix node types unless they carry a semantic difference that cannot be expressed otherwise.
- Route connectors orthogonally on the grid with straight or rounded elbows by default; use straight or bezier only where legibility benefits.
- Snap all nodes and connectors (and connector endpoints) to an 8px grid; align elements; use 48px default node size / 48px overlay for alignment.
- Keep endpoints unambiguous; use defined ending styles to mark relationship types.
- Never rely on color alone; add label, line style, or icon; for unlabeled connectors add line-style differentiation on top of color.
- Never use an icon by itself to convey essential information — always include words.
- Keep nodes monochromatic; don't mix colors within a node; don't use transparent backgrounds for nested elements; alternate background fills to aid nesting readability.
- Use primary colors (>=3:1 contrast) for outlines/sidebars/color-blocks/connectors, secondary colors for fills only; text stays Black (light) or White (dark) — don't recolor text.
- Keep label text short; move long descriptions outside the diagram; don't use all caps except acronyms; don't alter type size/alignment specs (Plex Sans 14/18 semibold primary, 12/16 connector/badge).
- Use each indicator-badge system for one reason at a time and add it to the legend.
- For repeated elements, show exactly two offset lines and put the instance count in parentheses after the name.
- If a diagram can't display at 100% scale, provide download or zoom.
- Explain nonstandard syntax (unusual line styles, badges, colors) in the legend; for standardized domains (IT architecture) follow the established visual vocabulary so the model is interpreted correctly.

## Important caveats
- Guidance is IBM-brand-specific (Plex Sans, IBM color palette, Carbon) — exact type/color/grid values are house-style, not universal; abstract the principle, not the pixel value.
- Explicitly NOT for in-product diagrams (use Carbon) and NOT for interactive/exploratory tools.
- Some resources (Figma libraries, IT-architecture stencils) are gated to internal/IBM users; not independently verifiable here.
- Standard artboard sizes/aspect ratios are recommendations "be intentional" allows deviation.

## Conflicts with other guidance
- Largely convergent with S09 (Marai): both demand purpose-first grammar, legends/labels, no color-alone encoding, distinct node types only when semantically warranted. IBM is more prescriptive about grid/routing; Marai is more evidence-based on perception. No direct contradiction.
- Convergent with S11 (Esri) on legend/legibility/hierarchy and with S12 (NASA) on accessibility-plus-accuracy.

## Useful examples
- Three node sizes mapped to use cases (bullet=dense trees, small=overviews, large=swimlanes/org charts).
- Four connector routings (square elbow, rounded elbow, straight, bezier) with default = orthogonal rounded/square.
- Multiple-instance offset marker: always two offset lines + "(n)" in the name.
- IT architecture vocabulary (Target IT system, Actor, Node, Component, Deployment unit, Location, Zone, Subsystem) as an example of a domain-standard grammar (IBM Unified Method Framework).

## Candidate principle IDs
- [DIAG] Define the node-and-connector visual vocabulary (types, shapes, line/ending styles, colors) before drawing and publish it in a legend | force: MUST | tier: A | contexts: technical diagrams, architecture, flows, networks | rationale: a diagram is only interpretable if its grammar is fixed and disclosed | source: S08
- [DIAG] Introduce a distinct node/connector type only when it carries a semantic difference that cannot be expressed otherwise, and avoid redundant shape/style/color/badge encodings | force: SHOULD | tier: B | contexts: any diagram | rationale: gratuitous type variety reads as meaningful and misleads; redundancy adds clutter | source: S08
- [DIAG] Route connectors cleanly (orthogonal grid elbows by default), snap nodes and endpoints to a consistent grid, and keep endpoints unambiguous | force: SHOULD | tier: B | contexts: node-link, swimlane, org, flow diagrams | rationale: orderly routing and clear endpoints prevent misread relationships | source: S08
- [ANNO] Always include a legend documenting every color, line style, shape, and badge convention used | force: MUST | tier: A | contexts: diagrams with any non-obvious encoding | rationale: undocumented conventions are not decodable by the reader | source: S08
- [PERC] Never rely on color alone to convey meaning; pair it with a label, line style, or icon (and add line-style differentiation on unlabeled colored connectors) | force: MUST | tier: A | contexts: all diagrams, color-blind accessibility | rationale: ~8% of males cannot distinguish some hues; redundant channels make meaning accessible | source: S08
- [SEM] Never use an icon by itself to carry essential information — always accompany it with words | force: MUST | tier: A | contexts: node/label iconography | rationale: icons are ambiguous and unfamiliar icons require a legend | source: S08
- [COLOR] Keep nodes monochromatic, reserve high-contrast primary colors (>=3:1) for structural strokes and light fills for backgrounds, and never recolor label text | force: SHOULD | tier: B | contexts: node styling, light/dark themes | rationale: preserves contrast and prevents accidental categorical meaning from fills | source: S08
- [LAYOUT] Keep labels short and move long descriptions outside the diagram; provide zoom or download when the diagram cannot render at 100% | force: SHOULD | tier: B | contexts: dense diagrams, documentation | rationale: crowded long labels destroy legibility; scaled-down diagrams become unreadable | source: S08
- [DIAG] When a standardized domain vocabulary exists (e.g., IT-architecture element types), follow it so the model is interpreted correctly | force: SHOULD | tier: B | contexts: architecture and other convention-governed diagrams | rationale: shared vocabularies enable correct interpretation across readers | source: S08
