# S11 — Esri, "Primary Design Principles for Cartography" (ArcGIS Blog, Aileen Buckley, 24 Apr 2026)

## Authority / evidence type
Excerpt from *Map Use: Map Reading and Design*, Vol. 1, 9th ed. (Esri Press), republished on the ArcGIS Blog by Dr. Aileen Buckley (cartographer, Senior Principal GIS Engineer, Esri; chair of ICA Ethics in Cartography Commission). Authoritative cartographic-design canon distilled into five principles; textbook-derived best practice, not empirical study. Illustrative figures are referenced but not present in the fetched text (image captions only).

## Scope
Cartographic design and page-layout composition, on screen or paper. Five primary principles that form a system for conveying relative importance: legibility, visual contrast, figure-ground, visual hierarchy, proportion. Explicitly distinguishes reference maps vs thematic maps. The principles are compositional and generalize to non-map layouts (decks, posters, dashboards).

## Central claims
- Five principles form a system for seeing and understanding relative importance; without them map communication fails; they act complementarily, not in isolation.
- Legibility = being both seen AND understood (size + familiarity of symbols/text).
- Visual contrast provides the basis for distinguishing features from each other and from background; high contrast = crisp/clear, low contrast = subtle (good for basemaps).
- Figure-ground organization spontaneously separates the primary area of interest (figure) from an amorphous background.
- Visual hierarchy graphically encodes relative importance; thematic layers rise, reference/base layers recede, labels stay on the highest plane.
- Proportion (symmetry, balance, harmony) gives aesthetic cohesion; visual balance pivots on the visual center (just above geometric center).

## Operationalizable rules
- Size symbols/text appropriately: geometric/simple symbols read at smaller sizes; complex or unfamiliar symbols need to be larger and/or a legend; avoid text/symbols too small to read.
- Prefer familiar or self-evident (mimetic) symbols; add a legend for unfamiliar ones.
- Create contrast by varying symbol/text size and using contrasting colors; when hues share high or low saturation, ensure hues are distinguishable, else vary saturation or value; use casings, symbol casings, or text masks to separate features from background.
- Use low overall contrast for basemaps so overlaid thematic layers stand out.
- Promote figure-ground with closed form, drop shadow, screening, illumination, or vignette (techniques can combine).
- Order reference-map layers by geographic occurrence (physiography < hydrography < vegetation < human-made < boundaries/administrative), keep labels on top; for thematic maps, minimize base content so the thematic layer occupies the highest plane.
- Balance the layout by placing the map figure at the visual center; use symmetry for formal balance or offset placement for informal balance; direct eye movement (title -> map -> other elements) via element position.
- Achieve harmony through alignment (left/center/right/top/bottom) and even distribution of elements and of parts within elements (legend items, locator map, text block).

## Important caveats
- Black/white gives best contrast between colors but is "not always the best color choice for maps" — contrast must be balanced against thematic and aesthetic goals.
- Principles are interdependent and applied together, not as a checklist in isolation.
- Reference vs thematic map distinction changes how hierarchy is applied — hierarchy rules are context-dependent.
- Figures illustrating the techniques (Botswana figure-ground, NZ reference map, US layout) are referenced but not visible in fetched text; technique names are verifiable, visual exemplars are not.

## Conflicts with other guidance
- Strongly convergent with S09 (Marai) layering/separation and centrality, and with S08/S12 on legibility and hierarchy. No contradictions.
- Complements S12 (NASA): Esri gives the compositional grammar (figure-ground, hierarchy) that NASA's accuracy+accessibility goals rely on.
- Provides the general composition vocabulary (figure-ground, visual center, balance, harmony) that transfers to slide/deck design beyond maps.

## Useful examples
- Low-contrast basemap under prominent thematic operational layers.
- Figure-ground techniques: closed form, drop shadow, screening, illumination, vignette (Botswana map).
- Reference-map layer stacking (physiography -> hydrography -> vegetation -> human-made -> boundaries; labels on top).
- Layout balance: map at the visual center (just above geometric center) as the eye's fulcrum; formal (symmetric) vs informal balance.
- Harmony via alignment and even distribution of legend, locator map, and text block (US map layout).

## Candidate principle IDs
- [MAP] Ensure legibility — everything must be both seen and understood; size symbols/text for their complexity and prefer familiar or self-evident symbols (legend for the rest) | force: MUST | tier: A | contexts: maps, layouts, decks | rationale: content that cannot be read or recognized cannot communicate | source: S11
- [PERC] Build visual contrast by varying size, color, saturation, and value, and use casings/masks so features separate from each other and the background | force: SHOULD | tier: A | contexts: maps, composition | rationale: without contrast features and background are indistinguishable | source: S11
- [LAYOUT] Establish figure-ground so the primary subject reads as foreground against a receding background (closed form, screening, drop shadow, vignette, illumination) | force: SHOULD | tier: A | contexts: maps, posters, slides | rationale: readers spontaneously focus on the figure and lose an undifferentiated field | source: S11
- [HIER] Encode relative importance with a visual hierarchy — thematic content on the highest plane, base/reference content receding, labels on top | force: MUST | tier: A | contexts: thematic maps, layered graphics, decks | rationale: hierarchy lets readers judge importance and find patterns | source: S11
- [MAP] Give basemap/context layers deliberately low contrast so overlaid thematic layers stay prominent | force: SHOULD | tier: B | contexts: thematic maps, layered dashboards | rationale: prominent basemaps compete with and bury the thematic message | source: S11
- [LAYOUT] Balance the composition around the visual center (just above geometric center) and choose formal or informal balance intentionally | force: SHOULD | tier: B | contexts: page layouts, slide layouts | rationale: the visual center is the eye's entry point and layout fulcrum | source: S11
- [LAYOUT] Create harmony through alignment and even distribution of elements and of parts within elements | force: SHOULD | tier: B | contexts: layouts, legends, multi-element compositions | rationale: aligned, evenly-spaced elements read as a cohesive whole | source: S11
