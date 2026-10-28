# Portfolio rubric — scoring a set of three, not ranking to one

Status: draft 2026-09-02. This rubric governs the divergent mission
(`DESIGN.md`): given a problem, produce three alternative views that each answer a
*different analytical question* (`principles/analytical_questions.yaml`), each valid,
each carrying a stated contribution. It sits on top of — and does not replace — the
single-figure machinery in `RUBRIC.md` (12 hard gates + 100-point ranking rubric).

## How this composes with the existing rubric

The single-figure `RUBRIC.md` still runs, per member:

1. **Hard gates G1–G13** decide member *validity*. Unchanged.
2. **The 100-point soft rubric** still measures how good each individual figure is,
   and is used *within* a question to pick the best encoding for that question.

The portfolio rubric adds a **set-level** layer on top. A pretty, high-scoring trio
that answers one question three ways is a portfolio *failure* even though every member
scores well individually. The set is judged on four axes, in strict order.

## Axis 1 — Validity floor (pass/fail, not scored)

Every member must pass all applicable hard gates (G1–G13). **One invalid member fails
the whole portfolio**, regardless of diversity or beauty. Rationale: a diverse set of
dishonest figures is worthless; validity is supreme (consistent with `RUBRIC.md`).
This is a floor, not a contribution — passing earns no points, failing is fatal.

## Axis 2 — Diversity (0–40)

Do the members answer *distinct* analytical questions from the taxonomy?

- Map each member to its primary question id (`analytical_questions.yaml`).
- **Distinct-question count** is the spine of the score: 3 distinct = full marks
  available; 2 distinct = capped; all 3 on one question = near zero on this axis.
- Chart-type variety with the *same* question id earns **nothing** here. This is the
  axis that operationalizes the DESIGN.md failure mode ("variety without contribution").
- The uncertainty overlay does not count as a distinct question (it is cross-cutting);
  a portfolio cannot claim diversity by adding error bars to one view.

## Axis 3 — Coverage (0–30)

Of the questions the data and the *stated decision* actually make relevant, did the set
choose the ones that matter?

- From the brief, list the decision-relevant questions (what does the reader need to
  decide?). A set can be perfectly diverse yet miss the obvious question — e.g. three
  exotic views when the decision hinges on a simple ranking.
- Score = how well the chosen three cover the relevant question set, weighted toward
  the primary decision question. Missing the single most decision-relevant question is
  the heaviest penalty on this axis.

## Axis 4 — Non-redundancy / contribution (0–30)

Is each member's unique contribution real and non-empty?

- Each member ships a trade-off card with a **"Reveals (that the others don't)"** field
  (`DESIGN.md`). Score whether that claim is true and material for each member.
- A member whose "reveals" is empty, or is dominated by another member (answers a
  strict sub-question of another's), scores zero for its slot and should be dropped.
- **Graceful degradation is not penalized here:** a well-justified *two*-view set with
  two strong non-redundant contributions can outscore a three-view set whose third
  member is a contributionless filler. Honesty over quota.

## Aggregate

- Validity floor must PASS. Then **Total = Diversity(40) + Coverage(30) + Contribution(30) = 100**.
- Bands (guidance, not gates): ≥80 strong portfolio · 60–79 useful with a weak slot ·
  <60 rework (usually a redundant or off-decision member).
- Report the per-axis breakdown and the question-id map, never just the total.

## The falsifiability control (for the eval)

The rubric's central claim — that *principled* diversity (distinct questions) beats
*arbitrary* diversity (chart-type swaps) — must be falsifiable. For each case:

- **Principled triptych:** three members, distinct question ids, selected by the pipeline.
- **Arbitrary-diversity control:** three members that all answer the **same** (usually the
  most obvious) question in three different chart forms — all individually gate-valid.

Both are judged blind on Axes 2–4 (both trivially clear Axis 1). Prediction: the
principled set scores far higher on Diversity and Contribution and at least as high on
Coverage. **If it does not, the reframe is not earning its cost** and the taxonomy or the
selection logic needs rework. Run on a subset of the 36 bake-off cases before scaling.

## Judge-bias guard

The A/B bake-off judge could be biased toward "more charts = better." The control
neutralizes it: both sets contain three figures, so any preference for the principled
set must come from distinct-question coverage, not figure count. Keep the judge blind to
which set is principled.

## Provenance

- Analytical-question spine: FT Visual Vocabulary (verified 2026-09-02) — see
  `sources/lineage-analytical-questions.md`.
- Diversity-selection formalism: maximal-marginal-relevance (Carbonell & Goldstein,
  SIGIR 1998) — verified. Used as the selection metaphor in DESIGN.md stage 4.
- No source is cited as authority until Fetcher-verified; unverified lineage items are
  marked pending in the lineage note and are NOT encoded as weights here.
