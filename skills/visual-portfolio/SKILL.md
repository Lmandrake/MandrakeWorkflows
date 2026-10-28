---
name: visual-portfolio
description: >
  Divergent orchestrator: given one problem, produce a small portfolio of
  genuinely-different visualizations — each answering a DIFFERENT analytical
  question about the same data, each individually valid, each shipped with a
  trade-off card. Use when the ask is "show me the alternatives / what are the
  ways to look at this / a few views of X", or whenever a single figure would
  hide legitimate competing readings. Runs generate → validate → select →
  characterize. It sits ON TOP OF visual-critic (which validates and scores each
  member); it does not replace or duplicate the single-figure machinery.
---

# Visual Portfolio (divergent orchestrator)

## Purpose
Turn one problem into a **Pareto set of distinct, valid views** rather than one
"best" figure. Where `visual-critic` converges to the single strongest honest
figure, this skill diverges: it enumerates the analytical questions the data can
honestly answer, builds the best figure for each, keeps only the valid ones, and
selects the few that together give the reader the most complete, non-redundant
understanding of the stated decision. Each member ships a trade-off card, so three
pictures become three arguments.

The single failure mode this skill exists to prevent: **variety without
contribution** — three chart-form swaps of the *same* question masquerading as a
portfolio. Diversity here is defined over **analytical questions**
(`principles/analytical_questions.yaml`), never over chart types.

## When to invoke
- The user asks for alternatives, options, "a few ways to see this," or an
  exploration rather than a single verdict.
- A single figure would suppress a legitimate competing reading (multiple
  decision-relevant questions live in one dataset).
- Building an exploratory panel, a "choose-your-view" page, or a section that must
  serve more than one audience/question at once.
- NOT for a single-figure deliverable with one clear question — use `visual-critic`
  directly (this skill would just wrap it and add overhead).

## Inputs
- The user request and data, plus the **stated decision/context** (what does the
  reader need to decide?) and medium/audience if known. The decision is required —
  Coverage cannot be judged without it; if absent, elicit it or state the
  assumption explicitly.
- Data shape: variables, types, cardinality, and whether temporal / spatial /
  relational / grouped fields exist.

## Required intermediate representation
A **portfolio file** that accumulates each stage's output:
```
decision_frame       (the stated decision + the questions it makes relevant)
question_slate       (supportable analytical-question ids + why each is supportable)
candidate_views      (per question: best-encoding proposal, from visual-critic route)
member_case_files    (per candidate: the full visual-critic case file + verdict)
valid_pool           (candidates whose visual-critic verdict is SHIP — the floor)
selection            (the chosen members + the diversity/coverage reasoning)
tradeoff_cards       (one per selected member)
portfolio_score      (4-axis PORTFOLIO_RUBRIC result + per-axis breakdown)
verdict
```

## Procedure — generate → validate → select → characterize
1. **Frame the decision (Coverage anchor).** From the brief, list the
   decision-relevant analytical questions and mark the single most decision-relevant
   one. This is the yardstick for Axis 3 (Coverage) and guards against a diverse set
   that misses the obvious question.
2. **Enumerate supportable questions (generate, part 1).** Walk
   `analytical_questions.yaml`; for each question test its `data_prereqs` against the
   data shape (a RANKING needs a categorical key + a measure; CHANGE_OVER_TIME needs
   a time field; FLOW needs edges; SPATIAL needs geography). Keep only questions the
   data can *honestly* answer. UNCERTAINTY is a cross-cutting overlay, not a
   standalone member — do not let it fill a slot.
   - **Measure-comparability / common-support check (MUST, before a question is
     kept).** `data_prereqs` only tests whether a question is *askable*, not whether
     the naive measure is *comparable across the entities being compared*. For any
     question that compares or orders entities (RANKING, RELATIONSHIP, DEVIATION,
     COMPARISON_ACROSS_GROUPS), verify the measure rests on common support: equal
     exposure windows, the same denominator/normalization, the same population
     (no survivorship), the same units. If it does not, either (a) reconstruct the
     measure so it is comparable (e.g. annualize to a rate, per-capita, index to a
     shared base) **or** (b) disclose the differing basis on the figure per entity.
     A naive raw measure over unequal bases is a reference-frame lie even when every
     mark is drawn honestly (extends SCI-06; ENC-05 common-baseline). Record the
     comparability basis in the candidate's case file. *(Dogfood 2026-09-03: ranking
     stocks by raw growth multiple was dishonest because listing windows differ —
     fixed by ranking on CAGR with each bar's window disclosed.)*
3. **Generate one best candidate per question (generate, part 2).** For each
   supportable question, invoke `visual-critic` in end-to-end mode to produce the
   single best encoding *for that question*, choosing channels by perceptual
   effectiveness (position > length > angle > area > color; PERC family). One
   question may yield more than one candidate encoding; the within-question winner is
   picked by the 100-pt rubric inside `visual-critic`.
4. **Validate each candidate against the honesty gates (validate — the FLOOR).**
   Each candidate carries its `visual-critic` verdict. **Only SHIP-verdict members
   are eligible** (QA-01/02: gates precede and override scoring). A candidate that
   fails a hard gate is repaired and re-run, or dropped if it cannot be made valid. A
   member that cannot be made valid is not eligible — no diversity or beauty redeems
   it (PORTFOLIO_RUBRIC Axis 1: one invalid member fails the whole portfolio).
5. **Select for maximum distinct contribution (select — MMR-style, NOT top-N).**
   From the valid pool, pick the set that maximizes coverage of *distinct* questions
   and relevance to the decision — diversity-aware selection in the spirit of
   maximal-marginal-relevance (Carbonell & Goldstein 1998, verified in
   `sources/lineage-analytical-questions.md`): greedily add the member that adds the
   most new decision-relevant question coverage, not the next-highest single score.
   **Enforce: no two members share a primary question id; each member must have a
   non-empty, true "reveals that the others don't."** Target three, but this is a
   ceiling, not a quota — see graceful degradation.
6. **Characterize each with a trade-off card (characterize).** Emit one card per
   selected member (fields below). The "Reveals" and "Hides/can mislead" fields are
   the payload — they turn the set into an argued comparison, and they are what
   Axis 4 scores.
7. **Score the set** with `evaluation/PORTFOLIO_RUBRIC.md`: Axis 1 validity floor
   (pass/fail) → Diversity (40) + Coverage (30) + Contribution (30). Report the
   per-axis breakdown and the question-id map — never just the total.
8. **Verdict:** SHIP (the portfolio + its cards + score), REPAIR (a member failed
   the floor or a slot is redundant/off-decision — name it and its owning skill), or
   ESCALATE (the decision frame is genuinely ambiguous and changes which questions
   matter — surface it, do not resolve silently).

### Graceful degradation (honesty over quota)
If the data and decision genuinely support only two strong, non-redundant questions,
**ship two** with an explicit note. Do not manufacture a contributionless third — a
padded third member reintroduces the exact failure mode this skill fights, and
Axis 4 does not penalize a well-justified two-view set. (Empirically motivated: in
the triptych eval the time-dominated disaster case tied, because a third question
added variety but no decision value — `evaluation/runs/2026-09-02-triptych/`.) The
converse also holds: never exceed the set the decision needs to look thorough.

## The trade-off card (per member)
- **Question answered** — the single analytical-question id this view addresses.
- **Encoding & why** — the chart form and the perceptual reason it fits this question.
- **Reveals (that the others don't)** — the unique, material contribution. If empty,
  the member is dropped.
- **Hides / costs / can mislead** — what it suppresses; where a careless reader errs.
- **Best audience / medium** — exec glance vs analyst exploration vs publication;
  slide vs page.
- **Gates cleared / stressed** — the honesty gates it passes and any it puts under
  tension.

## Hard constraints
- Validity floor (MUST, QA-01/02): every member must carry a `visual-critic` SHIP
  verdict before it is eligible. One invalid member fails the whole portfolio
  (PORTFOLIO_RUBRIC Axis 1).
- Distinct questions (MUST): no two selected members share a primary question id;
  chart-type variety on one question is not a portfolio.
- Measure comparability (MUST, extends SCI-06): any comparing/ordering member must
  rest on common support (equal exposure, same denominator, same population, same
  units), or disclose the differing basis on the figure. A raw measure over unequal
  bases is a reference-frame lie regardless of how honestly the marks are drawn.
- Non-empty contribution (MUST): every selected member has a true, material
  "Reveals that the others don't." A dominated or empty-contribution member is
  dropped.
- Honesty over quota (MUST): ship fewer members rather than a redundant filler; do
  not force a third question the decision does not need.
- Do NOT re-implement the child skills' rules here (CRIT-06 discipline): this skill
  routes to `visual-critic` for per-member validity and scoring and owns only the
  set-level logic.

## Strong heuristics
- Anchor Diversity to the decision, not to novelty (SHOULD): a common question
  answered well beats an exotic one that is off-decision (Coverage outranks mere
  spread).
- Prefer the perceptually strongest encoding per question (SHOULD, PERC family), so
  each member is also individually excellent, not just individually valid.
- Justify each selection against its unique contribution and say what makes it work
  (CRIT-01/03).

## Context-dependent guidance
- If the decision is under-specified, state the decision assumption you used for
  Coverage, or ESCALATE it — do not silently pick a frame (contested-frame analog of
  CRIT-04).
- For a single-question deliverable, hand back to `visual-critic`; portfolio overhead
  is not free.
- In a fixed-slot medium (e.g. a three-panel figure), let the slot count cap the set,
  but still drop to two if the third would be redundant.

## Failure modes
- **Variety without contribution** — three encodings of one question selected because
  they look different. The distinct-question and non-empty-contribution constraints
  exist to kill this.
- **Diverse but off-decision** — three exotic views that miss the question the reader
  actually needs (Coverage failure).
- **Padded quota** — a weak third member added to reach three (fix: graceful
  degradation to two).
- **Floor bypass** — selecting a member for its uniqueness despite a hard-gate
  failure (a diverse set of dishonest figures is worthless).
- **Orchestrator drift** — re-implementing encoding/gate rules here instead of
  routing to `visual-critic`.

## Validation checks
- Every selected member has a `visual-critic` SHIP verdict in its case file.
- All selected members have pairwise-distinct primary question ids.
- Each member's trade-off card has a non-empty, non-dominated "Reveals" field.
- The decision-relevant question set was written down before selection (Coverage is
  auditable, not post-hoc).
- Every comparing/ordering member records its measure-comparability basis (common
  support verified, or the differing basis disclosed on the figure).
- If fewer than three members shipped, a graceful-degradation note states why.
- Every principle id cited here exists in `principles.yaml`; every question id exists
  in `analytical_questions.yaml` (registry integrity).

## Repair strategies
- Member fails the floor → route the defect to its owning skill via `visual-critic`,
  re-render, re-validate; drop only if it cannot be made valid.
- Two members share a question id → keep the higher-scoring encoding, replace the
  other with the next uncovered decision-relevant question from the valid pool.
- A member's "Reveals" is empty or dominated → drop it; degrade gracefully if no
  distinct decision-relevant question remains.
- Coverage gap (obvious question missing) → add its best-encoding candidate even if a
  more exotic view scored higher individually.

## Output contract
The portfolio file + a verdict. On SHIP: the two-or-three figures, one trade-off card
each, and the 4-axis PORTFOLIO_RUBRIC breakdown with the question-id map. On REPAIR:
the named failing/redundant member and its owning skill. On ESCALATE: the specific
decision-frame ambiguity needing the user.

## Source basis
Set-level rubric and the four axes: `evaluation/PORTFOLIO_RUBRIC.md`. Diversity axis
and question ids: `principles/analytical_questions.yaml` (spine = FT Visual
Vocabulary, S04, verified 2026-09-02). Pipeline stages and the trade-off card:
`DESIGN.md` §"generate → validate → select → characterize". Per-member validity and
scoring are delegated to `visual-critic` (gate-then-score, QA-01/02, S10) and its
child skills. Selection metaphor: maximal-marginal-relevance, Carbonell & Goldstein
1998 (verified in `sources/lineage-analytical-questions.md`; not encoded as a weight).
Reasoning discipline: CRIT-01/03/06 (S01, S10). No source is cited as authority here
unless verified in the lineage ledger.

## Known open questions
- The taxonomy and the per-axis weights are a working hypothesis pending the
  balanced-assignment eval re-run (the triptych test had a position confound) and a
  wider case set than n=3.
- Automatic detection of "decision-relevant" questions from an under-specified brief
  is still heuristic; when in doubt the skill escalates the frame rather than guessing.
- Whether the selection stage should expose a tunable diversity/relevance trade-off
  (the MMR λ) to the user, or keep it fixed toward decision-coverage.
