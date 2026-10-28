# Ideogram block catalogue

The library behind SKILL.md §3. Pull what the ask needs; keep the library name of any block
you use. Invariant-carrying blocks (front door, orientation box, menu, I2 halves, mold) are
specified in SKILL.md itself.

**Header / identity** *(near-universal; metadata, not an invariant).* Title; author; intended
recipient(s) and their role/angle; date; version. One or two lines each. The scope cutoff is
not part of the header by default: it belongs only to re-run shapes (`lifecycle.md`).

**§ WHY THIS EXISTS** *(common).* Why the document exists, what the author needs it *for*, and
the background a reader needs to aim well: the decision served, the deadline, the stakeholder,
the honest "why now". It shapes judgment on edge cases; it is not a deliverable. For a concept
brief or design-intent brief it is usually the substance, not the preamble.

**The mold** *(common; strongest block).* A fill-in outline that shapes what comes back:
numbered sections, one per facet of I2, in the author's reading order. It also transmits
conventions (e.g. evidence tags) better than stating them as criteria. Generalize past
requests: a capture skeleton for a record, an outline for a design brief. Ends with the
self-check receipt line; without it the author never learns whether I3 was used, and the
registry cannot tell a load-bearing block from a decorative one.

**§ WHERE I'VE BEEN — the running log** *(part of I0; near-universal).* Append a new entry at
the top on every hop; never overwrite. Each entry: version · who holds it · date · what just
changed · why it's in front of this reader · what it's waiting on · the self-check receipt.
- The **head entry is the arrival state**: what the front door reads out as "where I am right
  now"; for a round-tripped document it is how a recipient sees what changed.
- The **last entry ever written is the closure ledger** (`lifecycle.md`).
Keep the two newest entries inline and move older ones to an appendix; never delete them.

**§ HOW I'LL HELP** *(common for live collaborations).* Assemble from:
- **Engagement policy** — how a reader starts, how they point Claude at sources, and the rule
  that Claude searches only where invited and says where it looks.
- **Do's & Don'ts** (below) — full set for solicitation shapes, light or none otherwise.
- **Self-check protocol** (I3, SKILL.md §5) — required; only its placement is optional.
- **Persona** (SKILL.md §5) — situational: only where someone else's files or time are at stake.

**§ ADDITIONAL CONTEXT** *(common).* History, prior artifacts, related efforts, known risks,
links. Separate so it can grow without diluting the purpose. New context from a reader is always
welcome here.

**Appendices** *(situational).* Ready-to-forward cover notes; the mold; a runnable self-check
block; use-case sections (e.g. a DAAC/next-steps section for a status ideogram); older log
entries. Include only those the document earns.

**Other blocks** *(situational).*
- **Known gap / next step** — a real weakness with an owner and a first move.
- **Premise to challenge** — invites the reader to push back on the author's framing.
- **Narrative spine** — the story the deliverable will tell, so source material lands usefully.
- **Decisions and non-decisions** — what was settled and what was explicitly left open (the
  spine of a decision record).
- **Open questions** — for design-intent briefs, so settled is distinguishable from moving.

A new block you expect to want again goes into `block_registry.md` so it can earn its place.

## Default Do's & Don'ts (solicitation shapes; tune per use case)

Etiquette lives here, never in I2: "don't build competing slides" is a request, not a
measurement.

**Do:**
- Send anything you think is relevant; over-exposure beats under-exposure, the author would
  rather prune than miss something.
- Render your own **markdown** response with supporting **imagery** (plots, diagrams,
  screenshots) as raw material.
- Give the **whole set**, not one representative example, when the ask is about a set.
- Attach **context** to every datum: what it is, where it came from, why it matters.
- Pair every problem or blocker with at least one **reasonable potential solution**.

**Don't:**
- Hand over one example to stand in for a whole set.
- Hand over data without context.
- Give generic responses ("a bunch of good work happened").
- Flood the response with material irrelevant to the ask.
- Produce finished slides or representations that could conflict with what the author will
  build.

State the apparent tension plainly to the contributor: *your own markdown and figures are wanted
as source material; a competing finished deck is not, because the author owns the final
composition.*
