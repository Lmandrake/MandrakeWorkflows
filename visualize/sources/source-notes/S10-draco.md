# S10 — Draco: "Formalizing Visualization Design Knowledge as Constraints"

## Authority / evidence type
Peer-reviewed academic research (Moritz, Wang, Nelson, Lin, Smith, Howe, Heer). IEEE TVCG / Proc. InfoVis 2019, Best Paper Award. DOI 10.1109/TVCG.2018.2865240. Backed by an open-source reference implementation (github.com/uwdata/draco; superseded by draco2 at cmudig/draco2). Tier A — primary methodological contribution grounded in the graphical-perception literature and formal (Answer Set Programming) methods.

## Scope
A formal FRAMEWORK for representing visualization design knowledge and a system that recommends designs. Bridges the gap between empirical design guidelines and automated tools. Models design knowledge as constraints over visualization specifications (Vega-Lite), splits knowledge into inviolable rules and weighted preferences, and learns preference weights from graphical-perception experiment data. Also documents the practical API (validity checking, recommendation via constraint solving, translation to/from Vega-Lite).

## Central claims
- Visualization design knowledge can be expressed as a collection of CONSTRAINTS, giving theoretical guidelines a concrete, extensible, and testable form.
- Constraints divide into HARD constraints (must never be violated — define validity) and SOFT constraints (weighted preferences that express degrees of "better/worse").
- Visualization recommendation = constraint solving: compile the dataset + partial specification + analytic task into an ASP program, combine with the knowledge base, and solve (Clingo) for the minimum-cost (optimal) design.
- The weights on soft constraints are LEARNABLE directly from the results of graphical-perception experiments (learning-to-rank), rather than hand-set.
- The model is extensible: new constraints or updated weights can be added without redesigning the system; results across studies can be integrated into one knowledge base.

## Operationalizable rules
- Separate design knowledge into two tiers: hard constraints (validity — infinite cost if violated) and soft constraints (preferences — finite weighted cost). This split directly informs a registry's MUST/AVOID (hard) vs SHOULD/MAY (soft, heuristic) distinction.
- A visualization is "valid" iff it violates no hard constraint; use `is_valid` semantics to gate candidate designs before ranking.
- Rank competing valid designs by total weighted soft-constraint cost; the recommended design is the one of minimum cost.
- Prefer weights grounded in perceptual experiment data over intuition when available; keep weights as data, updatable as new evidence arrives.
- Represent the input as (data schema + partial spec + task); a recommender should complete the partial spec rather than invent from scratch (`run` returns a completion; `relax_hard` lets hard constraints be relaxed at infinite cost for debugging).
- Keep knowledge modular and testable (ASP `.lp` files; `hard.lp` for hard constraints) so guidelines can be audited and extended.

## Important caveats
- The paper contributes a FRAMEWORK and method, not a fixed canonical list of "the right" constraints; the specific hard/soft rules live in the (evolving) knowledge base, and the original repo warns "There Be Dragons!" (active development, superseded by Draco 2).
- Learned weights are only as good as the perception experiments they are trained on; generalization beyond studied conditions is not guaranteed.
- Targets single-view Vega-Lite-style encodings; multi-view/complex-composition coverage is limited in the original system.
- The fetched sources (abstract page + repo README) describe the method and API; detailed individual constraints are not enumerated here — do not fabricate specific Draco constraints from these files.

## Conflicts with other guidance
- Methodologically complements rather than conflicts with FT/IBM/Datawrapper: those provide human-readable guidelines; Draco provides the formal scaffold to encode them as hard vs soft and to resolve conflicts by cost minimization.
- Draco reframes "rules with exceptions" (the FT/IBM stance) as soft weighted constraints — this gives a principled way to handle the axis-zero-type debates that other sources leave unresolved.

## Useful examples
- Pipeline: user query (dataset + partial spec + task) → ASP rules + knowledge base → Clingo solve → optimal answer set → translated to Vega-Lite spec.
- API: `is_valid(query)` checks hard-constraint satisfaction; `run(query, relax_hard=...)` returns an optimal Result convertible via `as_vl()`; `vl2asp`/`asp2vl` translate between Vega-Lite and ASP facts.
- draco-learn runs learning-to-rank on perception-experiment results to set soft-constraint weights.

## Candidate principle IDs
- [QA] Split visualization design knowledge into hard constraints (validity, never violate) and soft weighted preferences (better/worse), and treat them differently | force: MUST | tier: A | contexts: building/validating a rule registry; automated recommendation | rationale: Draco's central formalization; underpins the MUST/AVOID vs SHOULD/MAY split | source: S10
- [QA] Treat a design as invalid (reject before ranking) iff it violates any hard constraint | force: MUST | tier: A | contexts: candidate filtering; spec validation | rationale: Draco hard-constraint / is_valid semantics; validity gates ranking | source: S10
- [CRIT] Resolve competition among valid designs by minimizing total weighted soft-constraint cost (recommendation as constraint solving) | force: SHOULD | tier: A | contexts: choosing among multiple acceptable encodings | rationale: Draco recommendation model via Clingo cost minimization | source: S10
- [QA] Ground preference weights in graphical-perception experiment data rather than intuition, and store them as updatable data | force: SHOULD | tier: A | contexts: setting/tuning heuristic priorities | rationale: Draco learns soft-constraint weights from perception experiments | source: S10
- [QA] Keep design knowledge modular, extensible, and testable so new rules/weights can be added and integrated across studies without redesign | force: SHOULD | tier: A | contexts: maintaining a living guideline registry | rationale: Draco's extensibility and testability claim | source: S10
- [SEM] Frame recommendation as completing a partial specification given data schema and analytic task, not inventing a design from nothing | force: SHOULD | tier: A | contexts: assisted/automated chart construction | rationale: Draco query = data + partial spec + task | source: S10
- [CRIT] Encode contested guidelines (e.g., axis-zero) as soft weighted constraints so trade-offs are made explicit rather than absolute | force: MAY | tier: A | contexts: guidelines with legitimate exceptions | rationale: soft-constraint model gives principled handling of "rules with exceptions" | source: S10
