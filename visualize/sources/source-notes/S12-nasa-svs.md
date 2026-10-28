# S12 — NASA Scientific Visualization Studio, "The Curious World of Scientific Visualization" / Visualization Principles (gallery, 2017)

## Authority / evidence type
Curatorial gallery essay from NASA Goddard's Scientific Visualization Studio (SVS, gallery ID 40339, released Nov 2017). Authoritative as institutional practice from a leading science-visualization outfit, expressed as a PHILOSOPHY organized into six thematic galleries with worked examples, not as a numbered rule set or empirical study. Principles must be inferred from the section framings and the overview; the page is descriptive/exemplary rather than prescriptive. Award context cited (2013 NSF SciVis Challenge winner "Dynamic Earth"; multiple SIGGRAPH Computer Animation Festival selections) supports credibility.

## Scope
Scientific visualization of real Earth- and space-science data (and knowledge-driven simulation) for both research insight and public outreach. Medium is primarily animation/video and high-resolution/hyperwall stills. Covers: making invisible phenomena visible, fusing heterogeneous datasets and long records, manipulating time and space scales, situating data in place/time, and knowledge-driven depiction where data is absent. Strong outreach/accessibility mandate alongside research use.

## Central claims
- Visualization is not a mere translation of numbers into pictures; shapes and colors "breathe life into real scientific data," revealing patterns once invisible or unknown, and the visualization itself becomes a vehicle for scientific inquiry.
- Beauty and scientific truth are compatible: "visualizations are beautiful because the story they tell is real"; understanding enhances appreciation, and realness is the point, not decoration.
- A core function is making the invisible visible — showing phenomena outside human vision (non-visible wavelengths, ocean currents, atmospheric ozone/CO2, rainfall inside clouds).
- Complex systems are explained by fitting heterogeneous data together — multiple datasets or long-term records combined into one coherent picture.
- Changing scales of time and space brings out hidden relationships (speeding up slow processes, spanning years or global extents).
- Anchoring data in its place and time (context in space/time) enhances the viewer's understanding.
- Knowledge and imagination can simulate reality where direct data is absent ("From the Mind of the Scientist"), still in service of understanding.
- The work is a collaboration: scientists work alongside artists to extend research into the visual space, serving both the research community and the widest possible public audience.

## Operationalizable rules
- Preserve scientific fidelity: base visuals on real data/models; treat the visualization as a tool of inquiry, not illustration that departs from the science (e.g., GEOS-5 Nature Run CO2; ECCO2 ocean currents; eclipse shadow re-rendered as an accurate polygon from LRO lunar terrain rather than a stylized oval).
- Make invisible phenomena perceptible by mapping non-visible properties (wavelength bands, flows, concentrations) to visible color/motion (Landsat band combinations; SDO multi-wavelength; stratospheric ozone intrusion filaments).
- Integrate heterogeneous sources and long records into a single coherent visualization when explaining complex systems (Hurricane Matthew fusing GOES, GPM, MERRA-2, IMERG, soil moisture, SST; 20-year biosphere; IMERG precipitation build-up).
- Manipulate time and space scales deliberately to expose relationships (seasonal CO2 drawdown; accelerated sea-ice minima; multi-year magnetic-field change).
- Add spatial/temporal context (place and time cues) to orient the viewer (Earthrise reconstruction with precise timing; cryosphere tour; area-graph overlays on sea-ice animations).
- When data is unavailable, use scientifically-informed simulation/imagination but keep it grounded in known physics (black-hole tidal disruption; exoplanet renderings; Phobos charging).
- Pair scientists and visual artists throughout, and design simultaneously for the research community and a broad general audience (dual insight + outreach purpose).
- Support fidelity honestly by disclosing method and, where scale is altered, noting exaggeration (e.g., topographic 20x / bathymetric 40x exaggeration stated for Perpetual Ocean).

## Important caveats
- The page is a curatorial philosophy, not an operational checklist; the "principles" here are the section themes and overview statements interpreted as guidance, not verbatim rules — flag as inferred.
- Aesthetic goals ("beauty commands attention") are held in explicit tension with fidelity; the resolution asserted is that beauty derives from realness, but the page does not give a procedure for adjudicating conflicts.
- Vertical exaggeration and larger-than-scale object sizing (e.g., "larger objects used to represent satellites... for clarity" in Sentinels of the Heliosphere; land/bathymetry exaggeration) are used and disclosed — a fidelity trade-off that must be labeled, not hidden.
- Domain is heavy visualization (animation, hyperwall, high-res) with substantial rendering resources; principles transfer conceptually but not all techniques are available in lightweight static contexts.
- No quantitative accessibility standards (contrast, colorblindness) are stated on this page despite the outreach mandate — accessibility here means broad audience reach, not the specific color-safe rules of S08/S09.

## Conflicts with other guidance
- Apparent tension with S09 (Marai) "avoid unjustified 3D": SVS uses 3D globes, volumetric and depth-cued renderings freely. Reconcilable because SVS content is largely inherently spatial (planets, atmospheres, orbits) — the "justified 3D" exception — and is animated/interactive rather than static publication figures.
- Aesthetic emphasis ("beauty commands attention") could conflict with strict minimalist/fidelity-first framings, but SVS explicitly subordinates beauty to realness, aligning with the accuracy-first stance shared by S09/S11.
- Otherwise convergent: the fidelity + accessibility pairing complements S08/S09/S11 legibility and honest-encoding themes.

## Useful examples
- Eclipse-path shadow re-rendered as an accurate polygon (from LRO lunar terrain + Earth landform heights + sun angle) instead of the conventional oval — fidelity improving on convention.
- Hurricane Matthew: six+ heterogeneous datasets fused into one explanatory narrative.
- Landsat 8 "Onion Skin" / SDO multi-wavelength: mapping non-visible bands to reveal different surface/solar structures.
- Perpetual Ocean / Global Sea Surface Currents (ECCO2): making invisible ocean flow visceral; exaggeration factors disclosed.
- Seasonal CO2 and accelerated Arctic sea-ice minima: time-scale manipulation to reveal cycles/trends; area-graph overlay adds quantitative context.
- Earthrise 45th anniversary: adding precise time/space context reconstructed from stereo photos + LRO terrain.
- "From the Mind of the Scientist" (black hole, exoplanet, Phobos): physics-grounded simulation where no direct data exists.

## Candidate principle IDs
- [SCI] Preserve scientific fidelity — base the visualization on real data/models and treat it as an instrument of inquiry, not decorative illustration | force: MUST | tier: A | contexts: scientific visualization, data storytelling | rationale: the value and credibility of a science visualization is that the story it tells is real | source: S12
- [SCI] Make invisible phenomena perceptible by mapping non-visible properties (wavelengths, flows, concentrations) to visible color and motion | force: SHOULD | tier: B | contexts: physical-science and remote-sensing visualization | rationale: visualization's core purpose is to show what the eye cannot otherwise see | source: S12
- [SCI] Integrate heterogeneous datasets and long-term records into one coherent view to explain complex systems | force: SHOULD | tier: B | contexts: multi-source science visualization, model+observation fusion | rationale: complex phenomena become interpretable only when disparate data are fitted together | source: S12
- [SCI] Manipulate time and space scales deliberately to expose relationships not visible at natural scales | force: MAY | tier: C | contexts: temporal/spatial animation, trends and cycles | rationale: rescaling time and space reveals hidden processes and patterns | source: S12
- [ANNO] Anchor data in place and time — add spatial/temporal context cues to orient the viewer | force: SHOULD | tier: B | contexts: geospatial and time-series visualization | rationale: locating the visualization in space and time enhances comprehension | source: S12
- [UNC] Disclose any departure from literal fidelity (vertical exaggeration, non-scale object sizing, simulated/imagined content) rather than hiding it | force: MUST | tier: A | contexts: scientific visualization, outreach | rationale: exaggeration and simulation are legitimate only when labeled so viewers are not misled | source: S12
- [INTENT] Design simultaneously for scientific insight and broad-audience accessibility, pairing scientists with visual artists throughout | force: SHOULD | tier: B | contexts: outreach + research visualization | rationale: scientist-artist collaboration yields visuals that both advance research and reach a wide public | source: S12
- [CRIT] Let beauty serve understanding, not replace it — subordinate aesthetic choices to the realness of the underlying science | force: SHOULD | tier: B | contexts: any persuasive/outreach visualization | rationale: beauty earns attention but derives its worth from the truth it conveys | source: S12
