# S01 — Munzner, "A Nested Model for Visualization Design and Validation" (IEEE TVCG / Proc. InfoVis 2009)

## Authority / evidence type
Tier A. Peer-reviewed IEEE TVCG paper (Proc. InfoVis 2009, 15(6):921–928) by Tamara Munzner, a foundational figure in information visualization; awarded the InfoVis 2019 Ten-Year Test-of-Time award (per the fetched UBC page). Full paper text is present in the files. It is a conceptual/prescriptive framework paper rather than an empirical study, so its authority is as a widely-adopted design-and-validation model, not as a source of measured effect sizes. Not reference_only — full text available.

## Scope
A process model for designing AND evaluating visualization systems. Splits the design of a visualization into four nested layers and prescribes which validation/evaluation method matches each layer. Framed for information visualization (infovis); the author explicitly notes scientific visualization (scivis) would need adaptation because spatial position is often intrinsic to the data there. Covers the whole lifecycle: domain understanding, abstraction, encoding/interaction, algorithm — plus how to claim contributions and report assumptions in papers.

## Central claims
- Visualization design decomposes into four nested levels, where each level's output feeds the level below: (1) characterize the domain problem and data, (2) abstract into generic operations and data types, (3) design the visual encoding and interaction, (4) design the algorithm to execute it efficiently.
- Because the levels are nested, an error at an upstream level cascades to and invalidates all downstream levels — perfect encoding and algorithms cannot rescue a wrong abstraction. This is expressed via four "threats to validity": wrong problem, wrong abstraction, wrong encoding/interaction, slow (or incorrect) algorithm.
- Each level has its own appropriate validation methods, split into "immediate" (available at that level) and "downstream" (require the inner levels to be implemented first). Choosing a validation method from the wrong level is a common flaw ("mismatch") — e.g., you cannot validate a new encoding with wall-clock timings, nor validate a task characterization with a lab study where the designers dictated the task.
- Encoding and interaction are treated together because they are mutually interdependent.
- The abstraction level is the one most often skipped or done implicitly, and is often the hardest to get right; designers tend to jump straight to encoding assuming it is the only real design problem.
- The design process is iterative in practice, not strictly linear; the value of the model is analytic — you can check whether each level was addressed correctly regardless of the order taken. Rapid/low-fidelity prototypes (paper prototypes, wizard-of-oz) let downstream validation happen sooner.
- Three authorial recommendations: distinguish which level each contribution sits at; explicitly state assumptions made for levels upstream of the paper's focus; and the community should publish more problem-characterization papers.

## Operationalizable rules
- Before designing an encoding, explicitly state the problem in terms of generic operations (e.g., compare, sort, find anomalies, correlate, find extremum, characterize distribution) and abstract data types (table with quantitative/ordered/categorical columns; node-link graph/tree; field of values in space).
- Validate a domain-problem claim by observing and interviewing real target users (qualitative, e.g., ethnographic field studies, semi-structured interviews) — not by introspection or designer assumption.
- Validate an abstraction claim by having target users do their own real work with the deployed tool (field study of the deployed system / anecdotal insight), not an abstract task the study designers invented.
- Validate an encoding/interaction claim by (immediate) justifying it against known perceptual/cognitive principles via heuristic evaluation or expert review, and (downstream) by a controlled lab study measuring time and error, and/or qualitative or quantitative analysis of result images.
- Validate an algorithm claim by (immediate) complexity analysis and (downstream) benchmark timing/memory measurement.
- Match the validation method to the level of the claim; do not validate an upstream claim with a downstream method or vice versa.
- When a result image or video is used as validation, explicitly point out the desirable properties in it rather than assuming the reader will infer them.
- Do usability testing (informal, non-target users allowed, but not the designer) upstream of any formal validation study; an unusable system yields no useful validation conclusions — but do not count usability testing itself as validation.
- In write-ups, state upstream assumptions (even a sentence with a citation suffices) and label which level each contribution belongs to.

## Important caveats
- The model deliberately oversimplifies for the sake of clear guidance; the author acknowledges the reductionist assumption that complex sensemaking decomposes into low-level components "is unlikely to be completely true."
- Layers are rarely executed in strict temporal sequence; the model is for analysis, not a rigid waterfall.
- Adoption rate is called out as a weak validation signal with many false negatives and some false positives.
- Derived from and validated on infovis exemplars; scivis and heavily data-constrained domains need adaptation.
- The visual-encoding vs. algorithm boundary can be "murky"; classifying contributions between them is sometimes ambiguous.
- The list of threats/validation methods is explicitly not exhaustive.

## Conflicts with other guidance
- No direct conflict with S02 (Franconeri) or S15 (graphical perception); rather, S01 provides the process scaffold into which S02/S15 fit — perceptual effectiveness evidence is exactly the "known perceptual and cognitive principles" Munzner says should justify encoding-level choices (immediate validation).
- Mild tension in emphasis: Munzner warns against treating the encoding level as "the only real design problem," whereas perception-centric sources (S02, S15) concentrate heavily on encoding. This is a complement, not a contradiction — S01 says encoding matters but must be preceded by correct problem/abstraction work.

## Useful examples
- Genealogical graphs (McGuffin & Balakrishnan): held up as an exemplar addressing all four levels; key insight that "family tree" is a misleading data-type label — the true type is a constrained graph (multitree/DAG).
- "Lost in hyperspace" early web visualizations: an abstraction failure — visualizing hyperlink topology added cognitive load instead of solving the real find-a-page task, no matter how well encoded.
- MatrixExplorer, Flow Maps, LiveRAC, LinLog, TopoLayout: each analyzed to show which levels were addressed and where the validation-to-claim mismatch or entanglement lies.
- Robertson et al.: animation found least effective for showing trends vs. static traces/small multiples (cited as a lab-study validation at the encoding level).

## Candidate principle IDs
- [PROCESS/CRIT] MUST establish the domain problem and an explicit data/operation abstraction before choosing a visual encoding. | force: MUST | tier: A | contexts: any new visualization or chart designed for a stated task | rationale: upstream errors cascade and cannot be fixed downstream; the abstraction level is most often skipped | source: S01
- [INTENT] MUST express the user's goal as generic operations (compare, sort, find extremum, correlate, characterize distribution) and abstract data types before encoding. | force: MUST | tier: A | contexts: design intake / spec | rationale: forces the designer to realize the real task and pick a data type whose visual form addresses it | source: S01
- [CRIT] SHOULD justify each encoding/interaction choice against known perceptual and cognitive principles (heuristic/expert review) as immediate validation. | force: SHOULD | tier: A | contexts: encoding-level design decisions | rationale: immediate check that no known guideline is violated before costly user studies | source: S01
- [CRIT] MUST match the evaluation method to the level of the claim being made. | force: MUST | tier: A | contexts: evaluating or reporting a visualization | rationale: mismatches (e.g., timing an algorithm to defend an encoding) provide no valid evidence | source: S01
- [ANNO] SHOULD, when presenting a result image as evidence, explicitly point out the properties that make it work rather than assume the viewer infers them. | force: SHOULD | tier: A | contexts: result figures, case studies, design write-ups | rationale: unassisted inspection does not reliably produce the intended inference | source: S01
- [CRIT] SHOULD state assumptions about levels upstream of the current focus (even briefly, with a citation). | force: SHOULD | tier: A | contexts: documenting a visualization or its design rationale | rationale: creates a clear foundation and prevents unexamined abstraction choices | source: S01
- [MEDIA] MAY use low-fidelity prototypes (paper, wizard-of-oz) to get abstraction/encoding feedback before building the algorithm. | force: MAY | tier: A | contexts: early iterative design | rationale: lets downstream validation happen sooner without full implementation | source: S01
- [CRIT] AVOID treating the visual encoding as the only real design problem. | force: AVOID | tier: A | contexts: design planning | rationale: skipping problem/abstraction work is the most common cause of well-encoded but useless visualizations | source: S01
