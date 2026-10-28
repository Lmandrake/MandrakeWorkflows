# Ideogram block registry

The evolving library of ideogram blocks, graded by **whether each one left a visible trace in
what came back** — not by how often it was used. This is the feedback loop described in
`lifecycle.md`.

**Why fingerprint and not use-count.** A use-count measures the author's habits; it cannot tell
a load-bearing block from a decorative one. The `Fingerprint` column asks the discriminating
question: *did the response show a sign of this block?* Values:

- `yes` — a trace is identifiable in what came back (a followed structure, an adopted convention);
- `no` — the response shows no sign of it;
- `no signal` — nothing came back yet, or there was no way to tell. Itself a finding, and the
  reason the mold now carries a self-check receipt (SKILL.md §3, "The mold").

**What counts as a deployment.** Only **real, grounded** ideograms — authored for an actual
purpose, pointing at a real directory, handed to real people. The illustrative teaching examples
under `examples/` do **not** count (see `examples/README.md`); they exist to show a shape.

**How to maintain it** (`lifecycle.md`, in brief):
- *On authoring:* add a row per block used, `Fingerprint` blank. Add the shape if new.
- *On close:* when the final § WHERE I'VE BEEN entry is written, set each fingerprint
  from what actually arrived. **This is the step that makes the registry worth keeping.**
- *Never gate authoring on the registry.* An absent fingerprint means "unproven," not "don't
  use it here."

> **Kill condition.** If after two further deployments this registry has not changed a single
> block choice, retire it and let the per-ideogram ledgers carry the lessons. A feedback loop
> that cannot fail to justify itself is not a feedback loop.
> *Deployments observed since this condition was set: 3 of 2 — condition met, registry retained. It changed a choice again later: the `no`-fingerprint persona row forced the question for a multi-contributor solicitation, where the answer was yes, keep it, because contributors were being asked to spend their own time and a consent-seeking opening did real work.*
> **It has already changed one choice.** The decision record kept the persona *because*
> the registry's `no`-fingerprint row forced the question "is a live collaboration genuinely
> expected here?" — and for a document its recipient works through with their own assistant, the answer was
> yes. Without the fingerprint column, the persona would have been included by habit (as in
> the report-out) or cut by the new doctrine's default. That is the registry doing its job.

**Deployments counted so far:** 5 (labelled by shape and a sequence number; the documents
themselves were real work and are not part of this skill)

1. **Report-out** — status / report-out shape, two contributors with their own tracks.
2. **Decision record** — decision-record shape; first deployment under the revised doctrine.
3. **Planning request** — decision-focused, single recipient.
4. **Agenda input** — **first multi-contributor solicitation.** Asks several people what they
   need from one meeting and collects the answers into one document.
5. **Workshop gather** — multi-contributor status / report-out ask with per-person tracks
   (settled · open · deep questions) and an evidence-tag bar. First deployment with the required
   orientation box. A synthetic negative fixture of the gatekeeping failure it surfaced is in
   `docs/deployments/example_gather/`.

---

## The four invariants and how they were realized

Every ideogram must satisfy all four (SKILL.md §3). These rows track *which realization* was
used, per shape, and whether it showed up in the response.

| Invariant | Realization used | Shape | Fingerprint | Deployment |
|---|---|---|---|---|
| I1 · Purpose | `§ THE ASK` (with per-recipient tracks) | status / report-out | **yes** — both deliveries addressed their own track and nothing else | Report-out |
| I2 · Sufficiency | `§ HOW SUCCESS IS MEASURED` (undivided; **should have been split**) | status / report-out | **yes** — both deliveries are structured to the per-track facets | Report-out |
| I3 · Self-check | Appendix C runnable block | status / report-out | **no signal** — no receipt existed at the time, so adoption was unobservable | Report-out |
| I1 · Purpose | `§ WHAT THIS RECORDS` | decision record | *(pending)* | Decision record |
| I2 · Sufficiency | `§ HOW SUCCESS IS MEASURED` (single undivided bar — nothing solicited as a graded delivery) | decision record | *(pending)* | Decision record |
| I3 · Self-check | Appendix C runnable block | decision record | *(pending — receipt line now exists, so this is observable)* | Decision record |
| I0 · Activation | front door + orientation box (RIGHT NOW per person, LATER, SETTLED/OPEN, WHERE THIS SITS) | status / report-out, multi-contributor | | Workshop gather |
| I1 · Purpose | `§ THE ASK` with per-person tracks, each split *settled / open / deep questions* | status / report-out, multi-contributor | | Workshop gather |
| I2 · Sufficiency | two halves; delivery bar built on evidence tags [M]/[D]/[B]/[P], gate claims must be [M]/[D] | status / report-out, multi-contributor | | Workshop gather |
| I3 · Self-check | inline protocol + Appendix C + "interview before drafting" directive | status / report-out, multi-contributor | | Workshop gather |
| I0 · Activation | welcome-to-the-form front door + "why I put this together" + orientation box | concept brief | | Concept brief |
| I1 · Purpose | `§ WHAT THIS CARRIES` (one idea plus its evidence) | concept brief | | Concept brief |
| I2 · Sufficiency | `§ HOW YOU'LL KNOW YOU'VE GOT IT` (six restate-without-looking checks) | concept brief | | Concept brief |
| I3 · Self-check | inline "quiz me" protocol | concept brief | | Concept brief |
| I0 · Activation | front door + orientation box (RIGHT NOW with dates to confirm, SETTLED/OPEN, WHERE THIS SITS) + menu with three adoption-focused starters | design intent / repo brief | | Repo brief |
| I1 · Purpose | `§ WHAT THIS CARRIES` (design intent of a repo, for an adopt/not-adopt decision) | design intent / repo brief | | Repo brief |
| I2 · Sufficiency | `§ HOW YOU'LL KNOW YOU'VE GOT IT` (six restate-without-looking checks, incl. settled vs open) | design intent / repo brief | | Repo brief |
| I3 · Self-check | inline "quiz me" protocol in § HOW I'LL HELP | design intent / repo brief | | Repo brief |

**Lesson already banked:** I2 was written as one list mixing the author's outcome bar ("the deck
lets me make my claims to the sponsor") with the contributor's delivery bar. Contributors cannot
satisfy the former. SKILL.md §3 now requires solicitation shapes to split it into two labeled
halves, with only the delivery half graded by I3.

## Common blocks

| Block | Purpose (one line) | Shape(s) | Fingerprint | Deployment |
|---|---|---|---|---|
| The mold (response / capture skeleton) | Fill-in outline that shapes what comes back; carries the self-check receipt | status; any shape expecting a response | **yes** — strongest in the library: both recipients followed their skeleton section-for-section, one inside 24h | Report-out |
| Evidence tags (`[E]/[I]/[A]/[S]`) | Force each claim to declare evidence vs. inference vs. speculation | any | **yes** — both deliveries adopted the convention; one inline per claim, one per section | Report-out |
| § WHY THIS EXISTS | Intent, need, decision served, background for aiming well | status; brief; design intent | **yes** — both deliveries argue toward the stated decision rather than reporting neutrally | Report-out |
| § ADDITIONAL CONTEXT | Informing material (history, artifacts, links); additive, not a deliverable | most | **no signal** — informs authoring; hard to detect in a response | Report-out |
| § WHERE I'VE BEEN (running log) | Arrival state at the head, closure ledger at the tail; one entry per hop | all (part of I0) | *(pending — first real deployments)* | Planning request; Agenda input |
| Front door (activation + welcome) | Makes Claude become the ideogram, not describe it; states shape, topic, goal, state | all (I0) | *(pending — first real deployments)* | Planning request; Agenda input |
| § WHAT YOU CAN ASK ME FOR (menu) | Standing boilerplate menu + 3 tailored starters; teaches the form across ideograms | all (I0) | *(pending — first real deployments)* | Planning request; Agenda input |
| Orientation box (right now · settled/open · where this sits) | Dated per-person asks, settled vs open, next event and its purpose, readable in 30 s | all (I0) | *(pending)* | added 2026-10-07 after a cold-read test of the agenda-input ideogram |
| Header / identity | Title, author, recipient(s)+angle, date, version | all | n/a — metadata | Report-out |

## Situational blocks

| Block | Purpose (one line) | Shape(s) | Fingerprint | Deployment |
|---|---|---|---|---|
| Persona | Friendly consent-seeking guide for live collaboration | live collaborations only | **no** — left no detectable trace in either delivery; **demoted from common 2026-09-09** | Report-out |
| Persona | *(same)* — **kept deliberately** for a document its recipient works through with their own assistant | decision record | *(pending — the deliberate re-inclusion is the test)* | Decision record |
| Decisions-and-non-decisions | `§ DECISIONS` + `§ WHAT WAS NOT DECIDED`, split so a raised-and-qualified item cannot read as settled | decision record | *(pending)* | Decision record |
| Forward plan | `§ THE FORWARD PLAN` — dates table + owned actions table | decision record | *(pending)* | Decision record |
| Status tags | `[settled] / [open] / [unverified]` — the decision-record analogue of evidence tags | decision record | *(pending)* | Decision record |
| Appendix — cover notes | Ready-to-forward note per recipient | solicitation shapes | **yes** (inferred) — both deliveries match the framing in their cover note | Report-out |
| Known-gap / next-step | State a real weakness with an owner and a first move | status | **no signal** — authored for the author's own deck, not for a response | Report-out |
| Premise-to-challenge | Invite the reader to push back on the author's framing | status; brief | **yes** — both deliveries engage the scaling/leakage premises critically rather than agreeing | Report-out |
| Narrative-spine | The story the deliverable will tell, so material lands where useful | status | **yes** — material arrived organized to feed the four-part spine | Report-out |
| Scope cutoff | Temporal window for a re-run ideogram | re-run shapes only | **no signal** — first cycle, so "since inception" was trivially satisfied | Report-out |
| Decisions-and-non-decisions | What was settled, what was explicitly left open | decision record | *(new 2026-09-09 — not yet deployed)* | — |
| Open questions | Distinguish settled design from still-moving design | design intent | *(new 2026-09-09 — not yet deployed)* | — |
| § RUN ARCHITECTURE | Inventory of definition files, notebooks/scripts, dataset sizes | handoff | folded into I2 in the real deployment, not used standalone | — (handoff example only) |
| § REPRODUCTION MECHANISM | Documented finite steps to rebuild runs on another machine | handoff | folded into I2 in the real deployment | — (handoff example only) |
| § DELIVERED INFRASTRUCTURE | The actual code/skills/harness handed over, not described | handoff | folded into I2 in the real deployment | — (handoff example only) |
| § DEFINITION FILES & DATASETS | Experiment-definition files + input/"truth" dataset sizes | capture | — | — (capture example only) |
| § CONTROLLING NOTEBOOKS & SCRIPTS | Named notebooks/scripts that drive each run | capture | — | — (capture example only) |
| § RESULTS | Metrics, artifacts, and images produced by the run | capture | — | — (capture example only) |
| § CONCLUSIONS | What the run established, honestly bounded | capture | — | — (capture example only) |
| **§ ALREADY SETTLED — don't spend the meeting here** | Table of what a prior session decided, so contributors don't re-litigate it; carries an explicit escape hatch ("say so in your block with a reason" rather than reopening live) | meeting-prep solicitation | *(new 2026-09-29)* | Agenda input |
| **Non-override merge policy** | States how multiple contributors' inputs combine: own block only, nobody edits anyone else's, conflicts surfaced as named trade-offs for the decider rather than silently reconciled | multi-contributor solicitation | *(new 2026-09-29)* | Agenda input |
| **§ THE INPUTS (collection area)** | Empty per-contributor anchors inside the ideogram itself, so the document *is* the collection surface rather than pointing at one | multi-contributor solicitation | *(new 2026-09-29)* | Agenda input |
| **Seeds-not-an-agenda disclaimer** | Open-questions block that explicitly disclaims being the agenda, to keep the author's list from anchoring contributors; pairs with "the most valuable thing you can do is add what I missed" | meeting-prep solicitation | *(new 2026-09-29)* | Agenda input |

> Blocks with no deployment are recorded because they appear in the illustrative examples or were
> added to the library by doctrine, and are worth having named. They stay *situational* until a
> real deployment reaches for them. In the report-out the run-architecture / reproduction /
> infrastructure ideas lived *inside* I2 and the software contributor's mold rather than as standalone blocks —
> which is itself a finding: for a single-recipient handoff track, folding them into the bar
> worked and cost three fewer sections.
