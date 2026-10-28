# Glossary

Terms used across the registry and skills, defined once here so the skills can
stay terse. Where a term traces to a specific source, the source ID is noted.

## Force levels (how strongly a principle binds)
- **MUST** — hard constraint. Violation makes the artifact *invalid*; the QA gate
  must reject it (QA-02). Not a matter of taste.
- **AVOID** — hard negative constraint. The named construction is invalid unless a
  listed exception fires.
- **SHOULD** — strong weighted preference. Deviate only for a stated, defensible
  reason; deviation costs points but does not fail a gate.
- **MAY** — permitted technique; use when it helps.
- **ESCALATE** — a decision the agent must surface (to the user, or resolve against
  explicit intent) rather than settle silently. Reserved for genuinely
  context-dependent calls (e.g. UNC-01).

The MUST/AVOID vs SHOULD/MAY split is the "hard constraint vs soft weighted
preference" distinction from Draco (S10, QA-01).

## Evidence tiers (how well-supported a principle is)
- **Tier A** — empirical / peer-reviewed (controlled perception studies, replicated
  findings). Highest confidence. e.g. S01, S02, S05, S09, S10, S15, S16.
- **Tier B** — mature institutional design practice (Nature, IBM, FT, Esri, NASA
  SVS, Datawrapper). Well-tested convention, not always experimentally isolated.
- **Tier C** — canonical expert synthesis (widely-taught principles without a
  single controlled study behind the specific claim).
- **Tier D** — examples / inspiration (blogs, individual practitioners). Corroborating
  only; never sole basis for a MUST.

## Core concepts
- **Encoding channel** — a visual variable that carries data: position, length,
  angle/slope, area, color hue, color value/intensity, shape, texture, motion.
- **Channel accuracy ranking** — the empirically ordered decoding accuracy of
  channels (position > length > angle/slope > area > color-intensity), from
  graphical-perception work (S15) and summarized in S02. Basis for ENC-01.
- **Perceptually uniform color map** — a color map where equal steps in the data
  produce equal perceived steps in color (e.g. the scientific color maps of S05).
  Contrast with rainbow/jet, which are non-uniform.
- **Sequential / diverging / categorical palette** — palette classes matched to
  ordered magnitude / data centered on a midpoint / nominal groups respectively
  (COLOR-04).
- **CVD** — color-vision deficiency. "CVD-safe" palettes remain distinguishable to
  color-blind viewers (ACCESS-02).
- **Figure-ground** — the perceptual separation of subject (figure) from context
  (ground); a precondition for a readable composition (LAYOUT-03, S11).
- **Small multiples** — a grid of small charts sharing scales/encoding, used to add
  data without overloading one panel (LAYOUT-02).
- **Direct labeling** — placing series labels on the marks instead of in a detached
  legend, removing a look-up round trip (ANNO-01).
- **Data-ink / non-data ink** — ink that encodes data vs. ink that does not; the
  guidance to remove non-data ink is bounded by reader-serving scaffolding
  (LAYOUT-01, conflicts.md #1).
- **Hard constraint vs soft (weighted) constraint** — from Draco (S10): hard
  constraints define validity and reject; soft constraints are weighted preferences
  resolved by minimizing total cost (QA-01/02/03).
- **Nested model levels** — Munzner's four design levels: domain problem, data/task
  abstraction, visual encoding + interaction, algorithm. Failures cascade downward;
  validate at the matching level (S01, INTENT-01/02, CRIT-02).
- **Medium profile** — the legibility and format constraints of the delivery medium
  (projected slide, read-ahead deck, print figure, technical report, infographic,
  dashboard, spatiotemporal science viz). Governs MEDIA-01/02/03.
- **Analytic relationship** — the structure the chart is meant to reveal
  (deviation, correlation, ranking, distribution, change-over-time, part-to-whole,
  magnitude, spatial, flow), used to select the chart family (SEM-01, S04).
- **Reference-only source** — a source cited for context whose full text was not
  lawfully accessible in-sandbox (e.g. S14 Jambor; Cleveland & McGill 1984). Its
  ideas are asserted only where an accessible Tier-A source corroborates them.

## Family codes (registry `class`)
INTENT · SEM · ENC · PERC · HIER · LAYOUT · COLOR · ANNO · SCI · UNC · DIAG · NET ·
MAP · MEDIA · QA · ACCESS · CRIT — expanded in `principles.yaml` `meta.families`.
