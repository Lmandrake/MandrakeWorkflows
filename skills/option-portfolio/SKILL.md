---
name: option-portfolio
description: >
  Answer "give me a few options" with a Pareto set that covers genuinely different
  questions — not three near-duplicates. Enumerate the distinct questions the decision
  can be interrogated for FIRST, build the best option per question, hold each to a
  validity floor, then select for distinct coverage instead of top-N by score. Use when
  asked for alternatives, options, "a few ways to approach this," a shortlist, a set of
  research directions, product-strategy bets, or mitigation choices — or whenever a single
  recommendation would hide a trade-off the decision-maker is entitled to make. Not for
  running the head-to-head once the set exists (blind-evaluation), not for the per-member
  admissibility test itself (validity-floors), and not for wording the final claim
  (falsifiable-claims). Its visualization-specific ancestor is visual-portfolio.
---

# Option Portfolio

Asked for "a few options," the easy move is to generate three things that look different and
call it a set. But surface variety is not contribution. Three framings of the same idea, three
candidates with the same strength, three mitigations that all buy the same property — these
answer *one* question three ways. The decision-maker learns nothing they could not have learned
from one, and the illusion of choice is worse than a single honest recommendation, because it
launders a non-choice as a deliberation. The failure is invisible if you only check that the
members differ; it is visible only if you ask what distinct question each one answers.

## When this fires

Any moment someone wants **more than one** and the decision has more than one legitimate axis:
"show me the alternatives," "what are our options," "give me a shortlist," "a few directions we
could take." Also when you are about to hand back a single best pick but you can feel a real
trade-off underneath it — a second axis the person is entitled to weigh themselves. And it fires
**backwards**: when a set already exists and you are asked whether it is a real portfolio or just
padding, run it through the protocol and report which members earn their slot.

## The protocol

**1. Frame the decision and name its legitimate axes — offer a Pareto set, not a point estimate.**
Write down what is being decided and the distinct considerations that could each reasonably drive
it. Mark the single most decision-relevant one.
*Why:* when a decision has multiple legitimate axes, a single "best" answer silently picks which
axis matters and hides the trade-off the decision-maker is entitled to make. The Pareto set makes
the choice theirs; a point estimate makes it yours.

**2. Enumerate the answerable questions FIRST, before generating any option.**
List the questions this decision can *honestly* be interrogated for — the ones the situation
actually supports — and prune the rest. Only then generate.
*Why:* if you generate options first and label their questions afterward, selection becomes a
beauty contest among near-duplicates. Enumerating the question space up front makes selection
coverage-driven: you are filling distinct slots, not ranking look-alikes.

**3. Define diversity over the QUESTION each option answers, not its surface form.**
Two options are "the same" if they answer the same question, however different they look. Build
the strongest single option per question; never seat two options that share a question.
*Why:* this is the one failure mode the whole skill exists to kill — *variety without
contribution*. Cosmetic difference (different vendor, different framing, different wrapper) over
one question is variety the reader cannot act on differently.

**4. Apply the validity floor to each member — per member, not filter-to-one.**
Each option must independently clear the hard admissibility bar for this decision. If no
`validity-floors` bar is pre-defined for this domain, state the floor explicitly *before* testing
any member — the minimum property below which an option is broken, not merely weaker — so the gate
is fixed before you have a favourite to protect. A member that fails is out, regardless of how much
coverage it would have added.
*Why:* the floor gates; it does not rank (that distinction is `validity-floors`). An inadmissible
option is not a cheaper trade-off — it is broken, and no amount of unique contribution redeems it.
One invalid member does not just lose points; it disqualifies itself.

**5. Select for distinct coverage — MMR-style — not top-N by score.**
From the valid pool, greedily add the member that covers the most *new* decision-relevant question,
not the next-highest individual score.
*Why:* top-N collapses onto the highest-scoring question and re-answers it, because the best options
cluster where the strongest signal is. Maximizing marginal distinct coverage is the only selection
rule that resists that collapse.

**6. Require a non-empty unique contribution from every member.**
For each selected option, state what it reveals that no other member does. If dropping it loses no
decision-relevant coverage, drop it.
*Why:* a member with an empty or dominated contribution is padding wearing the costume of choice.
The contribution field is the test: if you cannot name what is lost by removing it, nothing is.

**7. Degrade gracefully — honesty over quota.**
Ship two if only two answer distinct questions well. Never pad to a requested or habitual count,
and never exceed the number the decision actually needs.
*Why:* a manufactured third re-introduces exactly the variety-without-contribution failure the set
was built to avoid. "They asked for three" is a format, not a reason a third distinct question
exists.

**8. Hold each surviving member to individual excellence — diversity is necessary but not sufficient.**
Clearing the floor is not enough; drive each selected option to be individually strong on its own
axis before shipping.
*Why:* a distinct-question set can still tie or lose to a same-question set whose members are simply
executed better. The floor is pass/fail; craft is separate and still owed on every member.

## Failure modes

- **Variety without contribution** — several options that differ only cosmetically over one
  question. Killed by rules 3 and 6.
- **Diverse but off-decision** — a set of exotic options that misses the question the decision
  actually turns on. Killed by the Coverage anchor in rule 1.
- **Padded quota** — a weak member added to reach a target count. Killed by rule 7.
- **Floor bypass** — seating a member for its uniqueness despite a fatal flaw. Killed by rule 4.
- **Floor-as-ceiling** — treating "it passed the bar" as "it is good," shipping merely-admissible
  members. Killed by rule 8.

## Rationalizations that mean stop

| Thought | What is actually true |
|---|---|
| "Here are three options" (that differ only cosmetically) | Three surfaces of one question is one option in three costumes. Name each one's question — if they collide, you have one. |
| "The user asked for three, so I'll pad to three" | The count is a format request, not evidence a third distinct question exists. Ship the number the decision supports. |
| "This one scores highest — ship the top three by score" | Top-N clusters on the strongest question and re-answers it. Select for distinct coverage, not rank. |
| "It's a bit redundant but more is better" | A redundant member dilutes the set and fakes choice. If removing it loses no coverage, removing it is the improvement. |
| "It passes the floor, that's enough" | The floor is admissibility, not quality. A merely-valid member can lose to a better-executed rival on another axis. |
| "They all look different, so the set is diverse" | Different-looking is not different-answering. Diversity is over the question, and only over the question. |

## Worked example: a hiring shortlist that covers distinct strengths

A team must fill one senior-engineer role and the manager asks for "a shortlist of three." The
tempting shortlist is the three highest interview scores — who all happen to be deep backend
systems specialists. That is top-N by score (rule 5) and variety without contribution (rule 3):
three answers to one question, "who is the strongest systems engineer."

Run the protocol instead. **Frame** the role's legitimate axes (rule 1): the team needs systems
depth, but also product/user judgment on an ambiguous roadmap, and mentorship for three juniors —
three distinct questions, with systems depth marked primary. **Enumerate those questions first**
(rule 2), then find the best candidate for *each* (rule 3), not the best three overall. **Apply the
floor per candidate** (rule 4): every finalist must clear the coding bar; a brilliant mentor who
fails it is out, exactly as `validity-floors` gates before it ranks — the strength does not buy past
the bar. **Select for distinct coverage** (rule 5): seed with the strongest systems candidate, then
add the one who adds the most *new* coverage (product judgment), then mentorship — not the second
and third systems specialists. **Require a non-empty contribution** (rule 6): if the "mentorship"
finalist also happens to be your second-best systems pick and adds nothing the primary doesn't, drop
them and **degrade to two** (rule 7) rather than pad. Finally, **individual excellence** (rule 8):
each finalist must be genuinely strong on their axis, not merely past the bar — the hardest lesson
below.

The method here is generalized from a visualization pipeline; read the source (in the `visualize/` tree of MandrakeWorkflows) in this order to see
the mechanism and the evidence:
- `MandrakeWorkflows/visualize/DESIGN.md` — the generate → validate → select → characterize pipeline
  and the "different analytical question" diversity axis ("It is a Pareto set, not a point estimate").
- `MandrakeWorkflows/visualize/principles/analytical_questions.yaml` — enumerating the distinct
  questions *first*, before generating, so selection fills slots rather than judging look-alikes.
- `MandrakeWorkflows/visualize/evaluation/PORTFOLIO_RUBRIC.md` — the validity floor as pass/fail per
  member, and diversity/coverage/contribution as the scored axes above it.
- `MandrakeWorkflows/skills/visual-portfolio/SKILL.md` — the domain-specific orchestrator:
  frame → enumerate → best-per-question → per-member floor → MMR-style select → trade-off card, with
  explicit graceful degradation to two.
- `MandrakeWorkflows/visualize/evaluation/runs/2026-09-02-triptych/RESULTS_BALANCED.md` — the case-C
  lesson: the judge found "Set 1 had the better questions, Set 2 had the better visualizations" and
  called it a **tie** — *diversity is necessary but not sufficient* (rule 8).

Characterize each surviving option with a trade-off card — see `references/tradeoff-card.md`.

## Boundaries with neighbouring skills

- **`visual-portfolio`** (Family A) is this pattern's concrete origin: the visualization-specific
  instance where the "questions" are analytical-question types and members are charts. This skill is
  its domain-independent generalization — same pipeline, any decision.
- **`validity-floors`** provides the per-member admissibility test rule 4 invokes. It defines what a
  floor *is* and why gating differs from ranking; this skill calls it, it does not re-teach it.
- **`blind-evaluation`** can compare two candidate portfolios head-to-head, but it does not *build*
  one. Use it after this skill has produced a set worth comparing.
- **`falsifiable-claims`** words the final recommendation and sets its refutation bar. It acts on the
  claim once the set exists; this skill constructs the set.

## Provenance of this skill

This skill was included at the user's direction, over a recommendation to defer it. It is
generalized from **one** project's `visual-portfolio` orchestrator — a visualization pipeline, not a
cross-domain study. The supporting comparison was **n=3**, position-balanced, and is reported as
*corroborated, not proven*. One honest nuance about maturity: when `visual-portfolio` was first
written it had **not** been run end to end; it has *since* been dogfooded exactly **once**
(`MandrakeWorkflows/visualize/evaluation/runs/2026-09-03-dogfood/DOGFOOD.md`, n=1), where the full
pipeline produced a genuine distinct-question set and the floor did real work. So this is engineering
practice from a single project with one end-to-end trial behind its generalization — not an
established finding. Treat the rules as reasoned defaults whose *reasons* travel, and expect the
weights and the question-enumeration step to need adaptation in any new domain.
