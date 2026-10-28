---
name: knowledge-registry
description: >
  Design the structure holding admitted knowledge: registry entries with stable family-scoped ids,
  a force from a fixed vocabulary, a testable check, versions, a decision log, open questions, a
  failure taxonomy. Use whenever building or maintaining a knowledge base, principle registry,
  rubric, ruleset, style guide or policy set others cite; ids churn and citations dangle; rules
  are graded by adjectives; rationale lives only in your head; open questions get dropped; or an
  orchestrator re-implements a specialist's rule. Not claim-provenance or validity-floors.
---

# Knowledge Registry

A registry is the load-bearing structure the rest of a system cites. When it is built
casually the failures are slow and systemic, not loud: ids get renumbered and every rubric,
eval, and skill that cited the old number now points at nothing or — worse — at the wrong
entry. Rules graded "important" and "very important" can't be enforced, because no gate can
act on an adjective. A principle with no check is a slogan no reviewer can run. A decision
whose reasoning was never written down freezes into dogma the moment the person who made it
forgets why. An open question that was never recorded becomes an invisible assumption. And a
failure that is only lamented, never routed, never becomes anyone's assignment to fix.

None of these show up the day you build the registry. They show up months later, as drift,
dangling citations, and arguments nobody can settle. This skill is the discipline that keeps
the structure auditable so those failures can't accumulate silently.

## When this fires

Any time you are laying down structure that other things will point at: authoring or editing
a principle registry, a rubric, a ruleset, a controlled vocabulary, a policy set, or a
knowledge base — and any time you are about to renumber ids, grade a rule by adjective, ship
an entry with no check, make a non-obvious call, drop an open question, or have one component
re-implement a rule another already owns.

It also fires **on maintenance**: when you inherit a registry and need to add an entry,
version a snapshot, adjudicate a conflict between two entries, or audit whether every cited
id still resolves.

## The protocol

**1. Give every entry a stable, family-scoped id.**
Assign a fixed prefix per family plus a number (`ENC-02`, `SCI-07`) and treat it as
permanent once published. Ids are the join key across skills, rubrics, evals, and the failure
taxonomy — the registry's schema comment states it plainly: *"stable family-scoped identifier
(e.g. ENC-01). Skills cite these."*

*Why:* every citation elsewhere is a foreign key into this id space. If an id churns, every
reference to it dangles or, worse, silently repoints. The property worth protecting is that a
one-command audit can confirm *"all 90 principle IDs cited across the skills and eval docs
exist in the registry — zero dangling references"* — which is only meaningful if ids never
move. Tidiness is not worth breaking that guarantee; retire an id, never reuse or renumber it.

**2. Make force an explicit vocabulary, not adjectives.**
Adopt a fixed, small set of force levels and define each once — e.g. `MUST`/`AVOID` for hard
constraints that gate validity, `SHOULD`/`MAY` for soft weighted preferences, `ESCALATE` for
a decision that must be surfaced rather than resolved silently. Publish the semantics table so
the words mean exactly one thing.

*Why:* a downstream gate acts on force *mechanically* — `MUST` means "reject if violated",
`SHOULD` means "cost points, don't block". "Important" and "very important" carry no such
contract; no validator can enforce an adjective. The hard-vs-soft split is what lets validity
gating and quality ranking be different operations instead of one muddled weighted score.

**3. Attach a `checks` list to every entry.**
Each entry names the concrete, testable condition a validator or reviewer actually runs to
tell whether it is honoured. No check, no entry.

*Why:* *"A rule you can't check is a preference."* The check is the operationalization — it is
what converts a principle from prose into something a QA step or a human can evaluate the same
way twice. Writing the check also stress-tests the rule: a principle you cannot phrase as a
check is usually not yet crisp enough to publish.

**4. Version and date the registry.**
Stamp the whole registry with a version and a generation date, and treat each release as an
immutable snapshot you can diff against the next.

*Why:* a dated snapshot lets you answer "what did we believe on this date, and on what basis"
and diff two states to see exactly what changed. An undated living document cannot be
audited — you can never reconstruct what was true when a downstream artifact was built against
it.

**5. Log each decision with its rationale and a reversal condition.**
For every non-obvious call, record three things: the decision, the reasoning, and *what
evidence would reopen it*. The reversal condition is not optional.

*Why:* the rationale defends the decision against relitigation and lets a later reader
challenge it on the merits. The reversal condition is what makes the decision *revisitable
instead of frozen* — it turns "we decided this" into "we decided this, and here is exactly
what would change our mind." State it and it can feed a benchmark, so decisions are *"testable,
not permanent."* Omit it and the decision quietly hardens into dogma.

**6. Register open questions instead of dropping them.**
When a genuine uncertainty surfaces and you resolve it by default, record it as an open
question — tagged by kind (evidence gap, design decision, scope, tooling) — rather than
letting the default pass unmarked.

*Why:* an unrecorded open question does not disappear; it becomes an invisible assumption
baked into the structure, indistinguishable from a deliberate choice. Recording it *"so they
are not silently resolved by default"* keeps the difference between "we decided" and "we
defaulted" visible to the next person.

**7. Build a failure taxonomy that ROUTES.**
Enumerate the ways the system fails, and for each failure name the stage or component that
*owns the fix* and the entries that guard against it. A defect at one level cannot be fixed by
working at another.

*Why:* routing turns a defect into an assignment instead of a lament. When each failure names
its owner, the response to a defect is "locate it at the correct level and route it to the
component that owns that level," not a diffuse complaint that something is wrong. A taxonomy
that only *describes* failures, without assigning them, produces no action.

**8. Separate the orchestrator from the specialists, and forbid duplication.**
One component decides and delegates; specialists own their rules; the orchestrator *invokes*
them and must not re-implement what a specialist owns. The registry is the single source of
truth; each component cites ids, none copies rule text.

*Why:* *"Duplicated rules drift out of sync."* The moment two places state the same rule, they
begin to diverge on the next edit and you have two answers to one question. Keeping the rule in
exactly one place — with everyone else citing its id — is what makes the id-as-join-key
discipline (rule 1) actually pay off.

## Failure modes

- **Id churn.** Renumbering "to tidy up" silently repoints every citation. Ids are permanent;
  retire, never renumber.
- **Adjective force.** Grading by "important/critical" leaves nothing a gate can enforce; the
  hard-vs-soft contract collapses into taste.
- **Checkless entries.** Principles with no check accumulate as unenforceable slogans that
  inflate the registry's apparent authority.
- **Undated living doc.** Edits with no version boundary make it impossible to say what was
  believed when, or to diff two states.
- **Rationale in your head.** Decisions with no logged reasoning get relitigated; decisions
  with no reversal condition freeze into dogma.
- **Dropped questions.** Uncertainties resolved by default and never recorded become invisible
  assumptions.
- **Lamenting taxonomy.** A failure list with no owner per failure generates complaints, not
  fixes.
- **Orchestrator drift.** A coordinator that re-implements a specialist's rule creates a second
  copy that diverges on the next edit.

## Rationalizations that mean stop

| Thought | What is actually true |
|---|---|
| "I'll renumber the ids to make them tidy" | Every id is a foreign key elsewhere. Tidy ids buy you nothing and dangle every citation that pointed at the old number. |
| "'important' is clear enough, I don't need a force level" | No gate can act on "important". A fixed force vocabulary is the only thing a validator can enforce mechanically. |
| "the principle is obviously right, it doesn't need a check" | A rule you can't check is a preference. If it is obvious, the check is cheap; write it and the rule becomes runnable. |
| "I'll remember why we decided this" | You won't, and neither will the next person. An unlogged rationale is a decision that will be relitigated from zero. |
| "that question isn't resolved, I'll leave it out" | An unrecorded open question becomes an invisible assumption. Register it so "defaulted" stays distinct from "decided". |
| "the orchestrator can just do this check itself" | Then the rule lives in two places and drifts. The orchestrator invokes the specialist that owns the rule; it never copies it. |

## Worked example: MandrakeVisualize's registry

MandrakeVisualize is itself an instance of the pattern — a machine-readable principle registry with a
force vocabulary and per-entry checks, a companion controlled vocabulary, a conflict ledger, a
dated snapshot, a decision log with reversal conditions, a registered open-questions list, a
routing failure taxonomy, and an orchestrator that delegates rather than duplicates.

Read, in order (paths are in the companion MandrakeVisualize repository):

- `MandrakeVisualize/principles/principles.yaml` — the entry schema in the header comment
  (id / class / principle / force / evidence_tier / contexts / exceptions / sources / rationale /
  checks — note the rule-statement field is named `principle` here, the field `references/registry-schema.md`
  calls `statement` generically), the `force_semantics` table, and the `families` namespace. This
  is rules 1–3 made concrete.
- `MandrakeVisualize/principles/glossary.md` — the shared vocabulary so each id means one
  thing across every consumer.
- `MandrakeVisualize/principles/analytical_questions.yaml` — a second registry with its
  own stable ids, anchored to an external controlled vocabulary (the FT "Visual Vocabulary").
- `MandrakeVisualize/principles/conflicts.md` — how two good entries that disagree are
  *adjudicated, not deleted*: record the tension, state the governing force, name the flip.
- `MandrakeVisualize/synthesis/v0.1-summary.md` — the dated, versioned snapshot of what
  the registry held at v0.1 (rule 4).
- `MandrakeVisualize/synthesis/DECISIONS.md` — each non-obvious call with its reasoning
  and a "Reverses if" condition (rule 5).
- `MandrakeVisualize/synthesis/OPEN_QUESTIONS.md` — uncertainties registered and tagged
  rather than silently defaulted (rule 6).
- `MandrakeVisualize/evaluation/FAILURE_TAXONOMY.md` — seven failure levels, each routed
  to an owning skill and the ids that guard it (rule 7).
- `MandrakeVisualize/skills/v0.1/visual-critic/SKILL.md` — the orchestrator that invokes
  the specialist skills and explicitly "does not duplicate their rules" (rule 8).

The full field-by-field schema, id-namespace conventions, force-semantics table, a worked
entry template, and an add/version checklist live in `references/registry-schema.md`.

## Boundaries with neighbouring skills

- **`claim-provenance`** decides whether a claim is *entitled to be encoded at all* — that its
  source is real and says what you think. This skill governs the *structure* that holds the
  claim once admitted. Provenance is the gate at the door; the registry is the shelving.
- **`validity-floors`** *consumes* the force vocabulary this skill defines: it separates the
  hard (MUST/AVOID) constraints that gate admissibility from the soft (SHOULD/MAY) criteria
  that rank. This skill defines that vocabulary; validity-floors applies it.
- **`option-portfolio`** and **`blind-evaluation`** are downstream consumers of a well-formed
  registry (they cite its ids and forces), not overlapping concerns. Neither designs the
  structure.

## Provenance of this skill

Generalized from a single project's registry: at time of writing, **92 principles across 17
families** in `principles.yaml`, a **12-question** analytical-question taxonomy anchored to an
external vocabulary, and a **7-level** failure taxonomy that routes each level to an owning
component. The eight rules above are the practices that kept that registry auditable and its
citations from dangling. They are engineering practice from one project, not an established
empirical finding — the id-churn and orchestrator-duplication lessons in particular are
generalizations of specific calls logged in `synthesis/DECISIONS.md`, not results from a
controlled study.
