# Synthesis decisions (v0.1)

The non-obvious calls made while merging ~120 candidate principles from the source
cards into a 90-principle registry and six skills. Each records the decision, the
reasoning, and what would reverse it. Reversal criteria feed the benchmark
(BENCHMARK_PLAN.md) so these are testable, not permanent.

## D1 — Zero-baseline is split, not one rule
**Decision.** Bar/column charts get a hard MUST for a zero baseline (ENC-02, gate G1);
all other encodings (lines, dot plots, ranges) get an ESCALATE, not a gate (UNC-01).
**Why.** Sources agree truncating a *bar* lies, because a bar encodes quantity by
length from zero (S02, S05, S15). They do *not* agree for lines/dots, where the mark
encodes position and a zero baseline can waste the whole panel or hide the signal
(conflicts.md #3). Collapsing both into one rule would either license truncated bars
or forbid legitimate zoomed line charts.
**Reverses if.** On real cases the ESCALATE proves to fire so often it becomes noise,
or domain experts consistently want a hard rule for a specific non-bar family.

## D2 — Rainbow/jet is a hard AVOID, not a soft preference
**Decision.** Rainbow/jet on a data dimension fails gate G5 (COLOR-03 AVOID).
**Why.** The strongest accessible source on this (S05, perceptually-uniform colormap
literature) treats rainbow as actively misleading — it manufactures false gradients
at the color transitions and collapses under CVD/grayscale. We took the stronger
"never on data" position over the softer "avoid unless justified" phrasing (conflicts.md
#5) because the justified exceptions (a few categorical hues, legacy comparison) are
not *data-dimension* uses and are handled elsewhere.
**Reverses if.** A validated exemplar uses a rainbow ramp on data that domain experts
judge correct — then downgrade to SHOULD + context exception.

## D3 — Accessibility floor is a principle, not the WCAG number
**Decision.** "Color is never the sole cue" and "measured contrast floor" are hard
(G3, G4), but the *numeric* threshold (ACCESS-03) is left medium-dependent rather than
hard-coding WCAG 4.5:1.
**Why.** WCAG ratios are web-UI norms for body text; a projected slide, a print figure,
and a poster have different viewing distances and reproduction (conflicts.md #7). We
kept the enforceable idea (there IS a measured floor, checked against the render) while
flagging the per-medium number as an open item (OPEN_QUESTIONS).
**Reverses if.** We adopt a per-medium floor table (proposed v0.2), at which point the
number becomes checkable and G4 gets mechanical.

## D4 — Annotation folded into visual-composition for v0.1
**Decision.** The ANNO-* family (11 principles) lives inside `visual-composition`
rather than a standalone annotation skill.
**Why.** Annotation and layout are decided together (direct labels vs. legend is both
an annotation and a composition choice), and a seventh skill would add orchestration
cost without a distinct intermediate representation. Kept as a documented deferral, not
a permanent merge.
**Reverses if.** The annotation rule set grows enough (captions, callouts, reference
lines, table-figure hybrids) to warrant its own intermediate representation.

## D5 — visual-critic orchestrates; it does not restate rules
**Decision.** The critic holds the case file, applies the failure taxonomy and rubric,
and owns the SHIP/REPAIR/ESCALATE verdict — but it *invokes* the other skills for the
actual principle checks rather than copying them.
**Why.** Duplicated rules drift out of sync. Single source of truth is the registry;
each skill cites registry IDs; the critic composes them. This keeps `principles.yaml`
the one place a rule is defined.
**Reverses if.** Orchestration latency becomes a problem and inlining hot checks proves
necessary (a performance decision, not a correctness one).

## D6 — Renderer independence enforced at the QA boundary
**Decision.** No skill names matplotlib/D3/PowerPoint/etc. The hard gates in
`visual-render-qa` are stated against the *rendered artifact* (collisions, contrast,
clipping, colormap identity) via QA-08 "inspect the actual render."
**Why.** The brief's core requirement is renderer independence; binding rules to a
toolkit would make the stack unportable and let tool defaults smuggle in violations.
The trade is that some checks (collision, contrast) assume a rendered-image inspection
step exists — logged as a tooling open question.

## D7 — Evidence tiers gate force, and force gates validity
**Decision.** MUST/AVOID (hard, gate validity) are reserved for Tier-A/B-backed claims
plus a few Tier-C canonical ones; SHOULD/MAY carry the rest; ESCALATE surfaces genuine
judgment calls to the user. Grounded in Draco's hard-vs-soft split (S10).
**Why.** It prevents taste from masquerading as law. A reader can see *why* a rule is
hard (its tier and source) and challenge it. Soft principles cost rubric points but
never block SHIP.

## D8 — Paywalled/unacquired sources are reference_only, never encoded from memory
**Decision.** Cleveland & McGill 1984, Tufte's books, Few, Munzner's textbook, and S14
(Jambor) are marked reference_only. Their well-known ideas are cross-checked against
accessible Tier-A/B sources; their specific unread content is NOT transcribed into
principles.
**Why.** Directly honors the standing "never manufacture citations/sources" rule.
ENC-01 states only the robust, corroborated part of the channel-accuracy ordering and
flags the exact area-vs-angle rank as an evidence gap rather than inventing it.

## D9 — Renderer capabilities live in a registry; skills ask by property
**Decision.** `registry/renderers.yaml` records each renderer's data shapes, primitives,
output modes, hidden defaults and hazards. `tools/route_renderer.py` maps properties to
renderer ids. `tools/check_skills.py` fails any SKILL.md containing a registry id or name.
**Why.** Keeps D6 true as real renderers arrive: names live in data, never in skills.
**Reverses if.** Property queries prove too coarse to pick a renderer in practice.

## D10 — Two families, poles of one space; colour-vision and grayscale rules are modes
**Decision.** CLEAR (`skills/v0.1`) and BEAUTIFUL (`skills/beautiful`) share one truth
floor and differ in style rules. `visual-intent` routes between them. G3, ACCESS-01/02/04/05
and COLOR-02's grayscale half apply only under opt-in modes (`principles/modes.md`);
`journal` = `colorblind_safe` + `archival` + print sizing, without grayscale. D2 is
amended: rainbow and turbo are allowed in BEAUTIFUL when declared, full range and keyed;
jet never.
**Why.** Owner rulings of 2026-10-07: the default contexts (office, technical meetings,
workshops) need the full colour bandwidth; truth rules never relax.
**Reverses if.** Pieces made under the default mode are misread by the audiences they
were made for.

## Coverage note (verification artifact, not a defect)
The reference-check confirmed **all 90 principle IDs cited across the skills and eval
docs exist in the registry — zero dangling references.** Two principles (QA-03,
MEDIA-04) did not match the automated per-skill token scan; this is a false positive
from compressed slash-notation in the skills ("QA-01/03", "MEDIA-04/05") that the
`\bID-\d{2}\b` regex reads as only the first ID. Both are conceptually referenced —
QA-03 in the critic's soft-ranking step, MEDIA-04 in the intent/taxonomy/rubric
dashboard guidance. Noted here rather than churned, since expanding the notation is
cosmetic; flagged for a v0.2 lint that expands slash-lists before checking.
