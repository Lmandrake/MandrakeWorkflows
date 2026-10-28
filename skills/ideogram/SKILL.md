---
name: ideogram
description: >
  Ideograms: self-checking documents (ask, brief, handoff, record) a reader can converse
  with. BUILD only on explicit request ("make/turn this into an ideogram"). RUN or ASSESS
  one handed over, often `*ideogram*.md` ("is this sufficient?"). EXPLAIN or RECOMMEND
  ("what is an ideogram?", a self-checkable ask): discuss, offer, don't build.
---

# Ideogram

## 1. What it is, and should you build one

An **ideogram** (the term is this collection's own) is a written document that carries everything a reader
needs to engage with it properly *and* the means to check whether they have: a well-defined
purpose plus optional context, packaged so whoever receives it can talk to it, attempt a
response, ask whether that response qualifies, and be coached toward sufficiency. More than a
ticket (it states purpose, bar, reasons, self-check), a spec (it can be run conversationally),
or a prompt (it is durable, human-first, re-runnable).

**It is not necessarily a request.** Requests are the commonest shape, but an ideogram can
carry an idea, a repository's design intent, an experiment record or a meeting's decisions
(§2). Where this skill says "contributor" or "delivery", read the shape's word: reader,
interlocutor, restatement, record.

Three properties define it:

1. **Runnable as a whole.** Pasting it to Claude or handing it to a person is enough to begin.
2. **Guides, never gates.** It defines the *minimum* valid response and invites more; the
   author, not the ideogram, decides what is in or out.
3. **Nothing fabricated.** Never invent a number, path, citation, quote or result; ground it in
   a named artifact or mark it `[AUTHOR TO CONFIRM]`. This is a global invariant of the form:
   say it once in the banner, and never spend a success criterion on it.

**Which mode is this request?**

- **BUILD** only on an explicit action verb plus the name: "make / write / create an ideogram
  that…", "turn this ask into an ideogram", "send X as an ideogram to Y". Go to §2–§6.
- **RUN / ASSESS** an existing ideogram the user hands you to work: satisfy it from the files
  it names, or grade a draft against it ("is this sufficient?"). Go to §4–§5. A filename
  containing "ideogram" is not by itself an instruction to adopt it: auditing or editing such a
  file is ordinary file work.
- **EXPLAIN / RECOMMEND** on a concept question ("what is an ideogram?", "would one help
  capture this?") or a request describing its job without naming it ("a precise ask my
  colleague can respond to and check their work against"): answer from this section, say
  whether one fits, **offer** to draft it, and wait for the go-ahead. For a fuller explanation
  read `references/concept.md`.
- **Do not trigger** on an incidental mention of the word or generic document creation
  ("capture my notes in a doc"). When in doubt, recommend and offer rather than build.

## 2. Shapes

Six recurring shapes. The four invariants (§3) hold for all; the shape decides which block
realizes each and where emphasis falls.

- **Status / report-out request** — success criteria (what the report must let the author
  claim) and decision translation (findings map to a decision, not a data dump).
- **Software / capability handoff** — reproduction on the receiver's machine, run architecture,
  grown infrastructure (skills, harness, config).
- **Experiment capture** — definition files, dataset/"truth" sizes, controlling notebooks or
  scripts, results, conclusions: enough for a third party to rebuild the run.
- **Concept brief** — intent/need/context; success = the reader restates the idea and its
  boundaries correctly.
- **Design intent / repo brief** — current state, settled decisions, open ones; a reader can
  find where to contribute and tell *settled* from *still open* without asking.
- **Decision record** — decisions with rationale, what was explicitly *not* decided, owned next
  actions; someone absent can act correctly without the transcript.

The last three **solicit nothing**. Do not bolt request machinery onto them (delivery criteria,
over-exposure do's and don'ts, a consent-to-search persona).

## 3. The four invariants (blocks are a library, not a template)

An ideogram is assembled from blocks: pull those the ask needs, skip the rest, add a new block
when the library lacks one. When a library block is used, keep its library name. Always keep
"what is asked of me" visibly separate from background. A document missing any invariant is a
memo, spec or ticket, not an ideogram.

| Invariant | What it does | Realized by, per shape |
|---|---|---|
| **I0 · Activation** | makes Claude *become* the ideogram instead of describing it, and states where it stands | the **front door** + the **orientation box** + `§ WHERE I'VE BEEN` (state) + `§ WHAT YOU CAN ASK ME FOR` (menu) |
| **I1 · Purpose** | what it is for, in the fewest unambiguous words | `§ THE ASK` (requests) · `§ WHAT THIS CARRIES` (brief, design intent) · `§ WHAT THIS RECORDS` (capture, decision record) |
| **I2 · Sufficiency** | what counts as having engaged properly | `§ HOW SUCCESS IS MEASURED` (request) · comprehension checks (brief) · completeness criteria (capture, record) |
| **I3 · Self-check** | how a reader tests themselves against I2 with the author absent | a runnable self-check block, or an inline protocol (§5) |

Self-check is an invariant; persona is not (experiment captures drop the persona and keep the
self-check).

**I0, the front door.** Written to two audiences at once: it welcomes a human and instructs
Claude in the same breath. Claude speaks *as* the ideogram in first person and opens by stating
shape, topic, goal and current state, then reads out the orientation box. It must name the
anti-pattern explicitly ("never open by summarizing my contents back at them"): summarizing is
the overwhelming default when a document lands in context, and only negative instruction
suppresses it. Identity adoption is required; consent negotiation is situational (§5).

**The menu** (`§ WHAT YOU CAN ASK ME FOR`): the standing list READ · RENDER · COMPARE · GRADE ·
STRESS · GROW, copied verbatim across ideograms, preceded by **three tailored starters** naming
what *this* reader most likely wants. The starters are the only part the author writes, and do
most of the work.

**The orientation box (required, directly under the front door):**

- **RIGHT NOW** — one row per person: *who · what · by when (a date)*, then a **LATER** line.
  If nothing is wanted from someone, write "nothing from you; read X before <event>".
- **SETTLED / OPEN** — settled: decided, by whom, don't reopen. Open: who decides, at which
  event. Analysis nobody has ruled on goes under Open, labeled.
- **WHERE THIS SITS** — *previous event → this document → NEXT EVENT (name, date, what it must
  decide or produce) → what that feeds*.

**"I am not asking you for anything" is a trap**: if any slot waits on someone, that is an ask
and it goes under RIGHT NOW with a date. Same three labels in every shape; a decision record's
RIGHT NOW is its owned next actions.

**Writing I2.** Testable statements, not adjectives; a checklist the author would actually
apply, since I3 grades against it verbatim. Unset thresholds are `[AUTHOR TO CONFIRM]`.

**Solicitation shapes split I2 into two labeled halves:**

- **The outcome I need** — what the *author's* final artifact must accomplish. Shown so
  contributors can aim; they are never graded on it.
- **When your delivery is sufficient** — the bar on what the contributor hands back. **The only
  half I3 grades.**

Etiquette ("don't build competing slides") is not a measurement: it goes in Do's & Don'ts, not
I2. Shapes that solicit nothing keep one undivided bar.

**The mold** (response or capture skeleton) is the strongest block: a fill-in outline, one
numbered section per facet of I2, in the order the author wants to read them. Use it whenever
anything comes back. It ends with the required **self-check receipt**:

```
Self-check run? Y / N   ·   Criteria still short at send time:
```

**`§ WHERE I'VE BEEN`** is a running log: append a new entry at the top on every hop, never
overwrite. Head entry = arrival state; the last entry ever written = the closure ledger.

The full block catalogue (header, `§ WHY THIS EXISTS`, `§ HOW I'LL HELP`, `§ ADDITIONAL
CONTEXT`, appendices, situational blocks, the default Do's & Don'ts) is in
`references/blocks.md`; read it when building. Scope cutoff, the closure ledger and the block
registry are in `references/lifecycle.md`; read it for re-run shapes and on close.

## 4. Modes of interaction (all first-class)

The same unedited document must serve each; sessions often slide between them.

- **Cooperative agent — "work this with me."** Asks consent where needed, surveys the named
  files, drafts, iterates, can fan out subagents per recipient track.
- **Evaluator — "is this enough, and how do I get there?"** Grades a draft against I2 (§5) and
  coaches: which block to add, which artifact to attach, which method closes each gap.
- **Teacher / designer — "help me understand or build this."** Teaches the concept it carries;
  acts as design partner for a requested capability (interface, reproduction, architecture).
- **Compositor — "help me assemble what came back."** Faces the author: merges responses, spots
  criteria the combined material still misses, helps decide what to cut.

It is also simply a document a human can answer without Claude. Keep I2 concrete enough to
evaluate against and `§ WHY THIS EXISTS` rich enough to teach from.

## 5. Operating patterns to embed

**The self-check (I3, required).** Answer "is this sufficient?" and paraphrases neutrally:

- Grade **each** I2 criterion — Met / Partially met / Not yet / Not applicable — with a one-line
  reason. On solicitation shapes grade **only** the "when your delivery is sufficient" half.
- Never inflate ("this is great") and never gatekeep ("rejected", "I'm not letting you send
  this"). State only what the evidence supports, in the author's own criteria.
  `docs/deployments/example_gather/weak_draft_probe.md` is a marked NEGATIVE
  FIXTURE of the gatekeeping failure.
- For anything short, name **where the missing material likely lives** (folder, artifact,
  person) *and* one concrete way to close it.
- Close with the reader's decision: "You decide what to include; here is where you stand
  against your own bar."

**The persona (situational).** Only where a live collaboration over someone else's files or
time is genuinely expected. A friendly guide whose goal is the reader's success, not a
gatekeeper: asks consent before looking at files, will not search anywhere it wasn't pointed,
and lets the reader volunteer priorities or wait for a survey. Author the opening verbatim:

> "Hello — I'm the **[purpose]** ideogram, here to help you [author's goal for the
> reader]. May I look through your files to draft a response, using subagents? In the
> meantime, tell me the items you feel are most important — or wait and see what I find,
> then decide what to share. Just point me where to look; I won't search anywhere you
> haven't named, so be specific."

Skip it for records, decision captures and design briefs: a consent dance with nobody on the
other side costs attention I1 and I2 need.

**Do's & Don'ts.** Carry the block (default set in `references/blocks.md`) in any ideogram that
solicits something; cut it to a line or drop it otherwise.

## 6. How to build one

1. **Identify the shape** (§2). If nothing is solicited, say so early and drop the request
   apparatus.
2. Ask the author (or infer, then confirm): recipients and their angles; the decision or use
   served; the bar, quantified where possible; the scope cutoff only for re-run shapes.
3. Read the relevant directory; ground I1 and I2 in named artifacts, people and files. A
   generic ideogram trains a generic response.
4. **Write the front door first (I0)**, then the orientation box, then the standing menu with
   three tailored starters, then the first `§ WHERE I'VE BEEN` entry.
5. **Satisfy the remaining invariants, don't fill a form.** I1 short, in its shape's
   realization; I2 as a checklist (two labeled halves if soliciting); embed I3. Add only blocks
   the document earns, using `templates/ideogram_template.md` as a palette to prune. Detail goes
   to `§ ADDITIONAL CONTEXT`. Prefer a mold section to a seventh criterion.
6. **Add the mold** if anything comes back, with its receipt line.
7. Add the consent persona only if a live collaboration is expected; appendices only per use
   case (cover notes, next steps, older log entries).
8. **Register it:** a row per block used in `references/block_registry.md`, fingerprint blank
   until close.
9. **Cold-read it before it goes out.** `scripts/naive_read_test.sh <ideogram.md> <out.md>`
   pastes it into a context-free Claude, asks "what are you?" and three busy-colleague
   follow-ups (it needs zsh and the `claude` CLI; without them, paste the document into a fresh
   chat with no tools or memory and ask the four questions in the script). If the first reply doesn't state the right-now ask with its date and the next
   event's purpose, fix the box, not the transcript.
10. Address people first, Claude second; bump a version line on each edit. Offer to register
    the finished ideogram where the author keeps them.
