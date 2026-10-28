# DESIGN — from "the one best chart" to a portfolio of distinct, valid views

Status: partially built (2026-09). The taxonomy (`principles/analytical_questions.yaml`), the
set-level rubric (`evaluation/PORTFOLIO_RUBRIC.md`), the falsifiability eval
(`evaluation/runs/2026-09-02-triptych/`, reframe not refuted), and the pipeline skill
(`skills/v0.1/visual-portfolio/SKILL.md`) now exist. This document defines the architecture they
implement and how the mission is evaluated.

## The shift

The stack so far is a **convergent critic**: given a problem, drive to the single best honest figure,
using the 12 honesty gates to eliminate bad options and the 100-point rubric to rank. The bake-off
showed this works — informed beat naive 36/36, every decisive win on an honesty gate.

The new mission is **divergent**:

> Given a problem, produce three alternative visualizations that are *genuinely different* — each
> answering a **different analytical question** about the same data — each individually valid, and
> each shipped with a stated unique contribution and its trade-offs.

Why this is the better problem, not just a harder one:

- **It is a Pareto set, not a point estimate.** "Best" presumes one question and one audience. Real
  problems have several legitimate questions; presenting the set is more honest than pretending the
  framework can pick the one that matters to *you*.
- **It matches expert practice.** Analysts sketch several views before committing; the value is in
  the comparison, not the verdict.
- **It cleanly separates two things the single-best framing conflates:** *validity* (is this figure
  honest and legible — the gates) versus *fitness for a purpose* (which question it answers). Gates
  become a per-member **floor**; the question-fit becomes the axis of variation.

## The one failure mode to design against: variety without contribution

Three lollipop/bar/column versions of the same ranking are **not** a portfolio — they answer one
question three ways. The entire design exists to guarantee that the three alternatives differ in
*what they let the reader learn*, not merely in *how they look*. The mechanism: **diversity is defined
over analytical questions, not over chart types.**

## The analytical-question taxonomy (the diversity axis)

A working set of the questions a dataset can be interrogated for. Two views are redundant if they
answer the same one, regardless of encoding.

- **Magnitude / ranking** — how big; which is largest; put them in order.
- **Change over time / rate** — trend, growth, acceleration, inflection.
- **Composition / part-to-whole** — what makes up the total; shares; how the mix shifts.
- **Relationship / correlation** — how two or more variables co-vary; is there structure.
- **Distribution / spread** — shape, variability, modality, outliers within a variable.
- **Comparison across groups** — how subgroups differ on a measure or a distribution.
- **Anomaly / exception** — what breaks the pattern; what is unusual and where.
- **Flow / connection / network** — how entities relate, route, or move between states.
- **Spatial pattern** — geographic or layout-dependent structure.
- **Uncertainty / confidence** *(cross-cutting overlay, not a standalone view)* — how sure we are.

This taxonomy overlaps the widely used "visual vocabulary" family (deviation, correlation, ranking,
distribution, change-over-time, magnitude, part-to-whole, spatial, flow). **To validate via Fetcher
before citing as authority:** the FT/Ribecca "Visual Vocabulary" and Graphic Continuum, Mackinlay's
APT / "Show Me" automatic presentation, Munzner's what–why–how task abstraction, Wilkinson's grammar
of graphics, and the UW design-space work (Voyager, Draco). Diversity selection has a known
formalism in maximal-marginal-relevance (Carbonell & Goldstein). None of these will be encoded as a
principle or weight until the source is checked — no fabricated citations.

## The pipeline: generate → validate → select → characterize

**1. Enumerate supportable questions.** From the data shape (variables, types, cardinality,
temporal/spatial fields) and the stated context/decision, list which analytical questions the data
can *meaningfully* answer. A ranking question needs a categorical key and a measure; a trend needs a
time field; a network needs edges. This prunes the space to honest candidates.

**2. Generate candidate views.** For each supportable question, propose the encoding that best fits
it, choosing channels by perceptual effectiveness (position > length > angle > area > color) and by
the existing principle registry. One question may yield more than one candidate encoding.

**3. Validate each candidate against the honesty gates.** Reuse the existing machinery unchanged as a
per-member **floor**: any candidate that fails G1/G3/G5/G6/G9/G11/G12/G13 is dropped or repaired before
it can be selected. A member that cannot be made valid is not eligible.

**4. Select three for maximum distinct contribution.** From the valid pool, pick the set that
maximizes coverage of *distinct* analytical questions and relevance to the stated decision —
diversity-aware selection (MMR-style), **not** top-3-by-rubric-score. Enforce: no two members answer
the same question; each member adds something no other member does.

**5. Characterize each with a trade-off card** (see below). This is the deliverable's payload: it
turns three pictures into three arguments.

### Graceful degradation

If the data and context genuinely support only two strong questions, ship **two** with an explicit
note rather than manufacture a weak, redundant third. Forcing a third contributionless view would
reintroduce the very failure mode this design fights. (Honesty over quota — consistent with the
gates.)

## The trade-off card (per alternative)

- **Question answered** — the single analytical question this view addresses.
- **Encoding & why** — the chart form and the perceptual reason it fits this question.
- **Reveals** — what this view lets the reader learn that the other two do not.
- **Hides / costs / can mislead** — what it suppresses; where a careless reader could go wrong.
- **Best audience / medium** — exec glance, analyst exploration, or publication; slide vs page.
- **Gates cleared / stressed** — the honesty gates it passes and any it puts under tension.

## Evaluation redesign (portfolio judging)

The bake-off judged A-vs-B: "which single figure is better." That protocol cannot score a portfolio.
The new eval judges a **triptych**:

- **Validity floor** — every member must pass the honesty gates; a portfolio with an invalid member
  fails outright, no matter how pretty.
- **Diversity** — do the three answer *distinct* analytical questions? (Penalize same-question
  duplicates.)
- **Coverage** — do the chosen questions cover the ones that actually matter for the stated
  decision? (Did the set miss the obvious question?)
- **Non-redundancy / contribution** — is each member's "reveals that others don't" real and
  non-empty? Is any member dominated by another?

**The control that makes the claim falsifiable: arbitrary diversity.** Against each principled
triptych, generate a control of three *arbitrary* valid chart-type swaps that all answer the **same**
question. Prediction: the principled set covers more distinct questions and scores higher on
non-redundancy; the arbitrary set clusters on one question and adds little. Judged blind, on a subset
of the existing 36 cases first, before scaling. If principled diversity does **not** beat arbitrary
variety, the reframe is not yet earning its cost and the design needs rework — that is the test.

## Risks and mitigations

- **Forced diversity produces a weak third view.** → Graceful degradation to two; contribution must
  be non-empty to be selected.
- **The taxonomy is wrong or incomplete.** → It is a working hypothesis to be validated against the
  literature and against the held-out corpus; treat divergence as a flag, not a failure.
- **Judge-model bias toward "more charts = better."** → Blind protocol; the control isolates
  *distinct-question coverage* from mere chart count (both sets have three figures).
- **Circularity from the personal corpus.** → A firewall between design inputs and held-out evaluation material keeps the latter a validation set only.

## What does NOT change

The honesty gates, the principle registry, the source-grounding discipline, and the no-fabricated-
citations rule. The divergent engine is built *on top of* the convergent validator; it does not
replace it. Validity is still supreme — a diverse portfolio of dishonest figures is worthless.
