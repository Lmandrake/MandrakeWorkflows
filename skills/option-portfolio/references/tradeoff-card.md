# Trade-off card — characterizing ONE option in a portfolio

Contents:
- [The template](#the-template)
- [Why each field](#why-each-field)
- [Worked card (non-visualization)](#worked-card-a-latency-mitigation-option)

A portfolio's payload is not the options; it is the *arguments* about them. One card per selected
member turns a set of choices into a set of reasoned trade-offs the decision-maker can weigh. A
member with an empty "unique contribution" field is not a member — drop it (option-portfolio rule 6).

## The template

- **Question answered** — the single decision-axis / question this option addresses. If it shares
  this with another member, one of them is redundant.
- **Best at** — what this option is strongest on; the perceptual/practical reason it fits its question.
- **Costs / when NOT to use it** — what it suppresses, its downside, and the conditions under which a
  careless chooser would pick it wrongly.
- **Unique contribution (that no other member gives)** — the material thing the set loses if this
  option is dropped. Must be non-empty and non-dominated, or the option is cut.
- **Validity status** — does it clear the hard floor for this decision (pass/fail), and which
  constraints it puts under tension. Passing earns no rank; failing disqualifies.

## Why each field

The first four fields make the option *comparable* to its siblings on the axis that matters (the
question), not on surface polish. The last field keeps the floor separate from the ranking: an
option can be the most interesting in the set and still be inadmissible, and the card must say so
plainly rather than let interestingness launder a fatal flaw.

## Worked card: a latency-mitigation option

Decision: cut p99 checkout latency without regressing correctness. The portfolio holds three
options answering distinct questions — reduce repeated work, reduce work on the hot path, reduce
work per request. This card characterizes **one** member.

**Option: add a read-through cache in front of the pricing service**

- **Question answered:** *reduce repeated work* — how much of the latency is recomputation of
  answers we already produced?
- **Best at:** collapsing p99 on hot, read-heavy keys; cheap to add; reversible. Directly attacks
  the sub-question no other member touches (the parallelize-the-hot-path and slim-the-payload
  options do not address recomputation).
- **Costs / when NOT to use it:** introduces a staleness window and an invalidation burden; helps
  nothing on cold keys or write-heavy paths; a careless chooser sees "cache = faster" and reaches
  for it even where the hot set is tiny, buying complexity for no p99 gain.
- **Unique contribution:** the only member that removes latency by *not computing at all*. Drop it
  and the set loses the entire "repeated-work" axis — the other two both assume the work must run.
- **Validity status:** clears the floor (correctness preserved *iff* invalidation is provably
  bounded); puts the correctness constraint under tension — admissible only with a stated,
  enforceable staleness bound, otherwise it fails the floor and is out regardless of its speed win.
