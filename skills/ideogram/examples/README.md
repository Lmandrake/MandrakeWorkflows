# Example ideograms

This folder holds two very different kinds of thing, and the distinction matters — the block
registry (`./references/block_registry.md`) counts **real deployments**
only, so illustrative teaching examples must never be mistaken for them.

- **Real ideograms** are grounded deployments: authored for an actual ask, pointing at a real
  directory's artifacts, and handed to real recipients. These are what the block registry counts.
- **Illustrative examples** are teaching artifacts: authored *to demonstrate a shape* of ideogram.
  Their scenarios are realistic but invented, every fabricated specific is tagged `[EXAMPLE]`, and
  each carries an "Illustrative example" banner at the top. **They do NOT count as real deployments**
  and must be excluded from any registry deployment tally.

---

## Real ideograms (grounded deployments)

These live in their own project folders (an ideogram is grounded in a specific directory's
artifacts), so they are described here rather than copied. They were real work and are not
published; the block registry records what each one taught.

| Ideogram | Shape | Location |
|---|---|---|
| Report-out | Status / report-out request (+ a software handoff track for one contributor) | project folder (not published) |

_Add new real entries here as you author them — and only these increment the block registry counts._

---

## Illustrative examples (one per shape, for teaching)

One worked example per remaining shape from SKILL.md §2, authored to show how block **selection**
differs by shape. Each is clearly marked illustrative and is **not** a live deliverable, so none
of them count toward the block registry's real-deployment tally.

| Example | Shape | Location | Block subset it demonstrates |
|---|---|---|---|
| GraderKit handoff [EXAMPLE] | Software / capability handoff | `examples/handoff_example/handoff_ideogram.md` | Adds situational **§ RUN ARCHITECTURE · § REPRODUCTION MECHANISM · § DELIVERED INFRASTRUCTURE** on top of the near-universal three + § HOW I'LL HELP + § ADDITIONAL CONTEXT; **omits** § WHY THIS EXISTS (self-evident), narrative-spine, premise-to-challenge, response-skeletons, known-gap |
| Prompt-ablation capture [EXAMPLE] | Experiment capture | `examples/experiment_capture_example/experiment_capture_ideogram.md` | Adds situational **§ DEFINITION FILES & DATASETS · § CONTROLLING NOTEBOOKS & SCRIPTS · § RESULTS · § CONCLUSIONS** + a brief § WHY THIS EXISTS + capture skeleton; **omits** § HOW I'LL HELP/persona (a record, not a live collaboration), cover notes, narrative-spine, premise-to-challenge |
| Certified tacit-knowledge concept brief [EXAMPLE] | Concept brief | `examples/concept_brief_example/concept_brief_ideogram.md` | Carries almost no machinery: near-universal three + **heavy § WHY THIS EXISTS + heavy § ADDITIONAL CONTEXT** + § HOW I'LL HELP; success = reader can restate the idea and its boundaries; **explicitly omits** all run/reproduction/infrastructure and all definition/results/conclusion blocks, plus narrative-spine, known-gap, and response-skeletons |

Each file states its own `Blocks used / Deliberately omitted` line near the top so a reader can
see the shape's selection at a glance. The three shapes deliberately use **different** block
subsets — that divergence is the lesson.

> **Note (2026-09-09):** these three examples predate the doctrine revision that replaced the
> fixed "near-universal three" with the three *invariants* (SKILL.md §3), promoted the mold,
> demoted the persona, split I2 for solicitation shapes, and added § WHAT CAME BACK. They remain
> **correct in spirit** — the concept brief and capture examples independently arrived at
> choices the revision later made doctrine (dropping the persona from the capture shape while
> keeping its self-check is exactly why self-check is now an invariant and persona is not).
> Where an example spends a criterion on "nothing fabricated," that slot is now redundant: the
> guarantee is a global authoring invariant (SKILL.md §1). Read them as worked shapes, not as
> canonical structure; `templates/ideogram_template.md` is the current palette.

---

## Real deployment #2 — scope decisions (decision-record shape)

| Ideogram | Shape | Location |
|---|---|---|
| Decision record: scope decisions & forward plan | **Decision record** — first deployment under the revised doctrine | project folder (not published) |

Worth reading as the worked example of a **non-solicitation** shape: it carries a meeting's
decisions as an alternative to the full transcript. It realizes I1 as `§ WHAT THIS RECORDS`,
keeps I2 as a **single undivided bar** (nothing is solicited as a graded delivery), splits
`§ DECISIONS` from `§ WHAT WAS NOT DECIDED` so a raised-and-qualified item cannot read as
settled, and **keeps the persona on purpose** — its recipient works through it with their own
assistant, which is exactly the condition SKILL.md §5 reserves the persona for.
