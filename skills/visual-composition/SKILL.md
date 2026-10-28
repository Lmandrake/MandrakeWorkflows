---
name: visual-composition
description: >
  Arrange encoded marks into a legible artifact with an intentional visual
  hierarchy, clean layout, and complete annotation (titles, labels, captions,
  legends, sourcing, alt text). Use after visual-encoding to compose the final
  figure/slide/panel layout. For v0.1 this skill also owns annotation.
---

# Visual Composition (with annotation)

## Purpose
Given honest encodings, make the artifact *read correctly at a glance*: the
intended element is seen first, the layout supports the intended comparison, and
every mark is explained. Composition converts a correct encoding into a
comprehensible communication.

## When to invoke
After `visual-encoding`; before `visual-render-qa`. Also when a figure is "busy",
has a weak focal point, relies on a detached legend, or lacks a self-contained caption.

## Inputs
- The encoding table from `visual-encoding` and the intent record's takeaway,
  audience, and medium.

## Required intermediate representation
A **composition plan**:
```
layers:      primary=<the takeaway element> ; secondary=[..0-3] ; context=[..]
hierarchy:   how each layer earns its rank (position/size/contrast/isolation)
annotation:  title (insight) ; direct labels vs legend ; caption ; units ; source ; notes ; alt-text
layout:      grid/alignment ; figure-ground ; panel arrangement ; whitespace
```

## Procedure
1. Assign layers: exactly one **primary**, zero-to-three **secondary**, optional
   **context**. Verify the primary layer has the strongest combination of position,
   size, contrast, and isolation (HIER-01). If context competes at first glance,
   reduce its weight (HIER-04, MAP-02 for maps).
2. Set up the intended comparison with grouping cues — proximity, enclosure, shared
   color (HIER-02). Start neutral (grays) and add emphasis only to the message
   (HIER-03).
3. Lay out for figure-ground and balance: subject reads as foreground (LAYOUT-03);
   remove non-informative ink unless it serves the reader (LAYOUT-01); prefer small
   multiples over one overloaded chart (LAYOUT-02); align multi-panel figures to a
   grid, sizing by content (LAYOUT-04); balance visual weight intentionally (LAYOUT-05).
4. Annotate completely:
   - Title states the insight, not just the dataset (ANNO-02).
   - Prefer direct labels on marks over a detached legend; fall back to a legend
     only when series density forces it (ANNO-01).
   - Axis lines, ticks, and unit-bearing labels present (ANNO-05); color bar present
     wherever a color scale encodes values (ANNO-04).
   - Caption/description makes the figure self-contained (what/when/where/sample)
     (ANNO-03); cite the data source (ANNO-06); disclose caveats in a notes line
     (ANNO-07); for correlation figures, frame against causal misreading (ANNO-08).
   - For digital output, supply alt text carrying the takeaway (ANNO-09).
   - Labels legible and horizontal; figure + caption each stand alone (ANNO-10).
5. Check the shared style rules (`~/dev/MandrakeWorkflows/visualize/principles/style.md`): clarity means
   revealed structure, not fewer marks; readable type; no saturated blobs.
6. Hand to `visual-render-qa`.

### Medium adjustments
- **deck_projected**: fewer layers, larger type, direct labels mandatory, drop
  fine context.
- **scientific_publication**: full caption + units + source + scale bars; denser
  layout permitted.
- **infographic**: more scaffolding and narrative annotation for lay readers.
(See `visual-intent` for the full medium-profile list; also MEDIA-01/02.)

## Hard constraints
- HIER-01 (explicit hierarchy). ANNO-03, ANNO-04, ANNO-05, ANNO-06, ANNO-10 (MUST).

## Strong heuristics
- HIER-02/03/04, LAYOUT-01..05, ANNO-01/02/07/08/09 (SHOULD).

## Context-dependent guidance
- LAYOUT-01 exception: retain scaffolding that measurably aids novice comprehension
  (see conflicts.md #1).
- ANNO-01 fallback to legend when too many series collide (conflicts.md #2).
- ANNO-02 relaxes for neutral reference figures with no single insight.

## Failure modes
- No focal point; the eye lands arbitrarily (violates HIER-01).
- Detached legend forcing look-up round trips (violates ANNO-01).
- Missing units, source, or color bar → unquantifiable / untrustworthy figure.
- Decoration competing with data (violates LAYOUT-01).
- Caption that cannot stand alone when the figure is reused.

## Validation checks
- The intended first-read element is the most salient (HIER-01).
- Every quantitative axis has ticks + unit label; every color scale has a bar.
- Figure + caption is interpretable with the body text removed.
- Compared elements are perceptually grouped (HIER-02).

## Repair strategies
- Demote context (lower contrast/size) until the primary layer dominates.
- Convert legend → direct labels; if impossible, label only highlighted series.
- Add the missing caption/units/source/color-bar before proceeding.

## Output contract
A composed artifact + composition plan (layers, hierarchy justification, complete
annotation), handed to `visual-render-qa`.

## Source basis
HIER-01/02/03/04 (S11, S09, S02, S07). LAYOUT-01..05 (S03, S06, S11, S02).
ANNO-01..10 (S02, S07, S13, S05, S06, S03, S04, S09). MEDIA-01/02 (S03, S06).
MAP-02 (S11). See principles.yaml.

## Known open questions
- Quantitative threshold for "too many series" before legends beat direct labels.
- Whether annotation deserves its own v0.2 skill once the taxonomy grows.
