---
name: visual-encoding
description: >
  Turn an intent record into concrete visual encodings: which data field maps to
  which channel (position, length, angle, area, color), the exact chart mechanics,
  and the color strategy. Use after visual-intent and before visual-composition,
  whenever channel or chart-type choices must be made honestly and legibly.
---

# Visual Encoding

## Purpose
Choose the visual channels that carry each data field so the reader decodes the
most important quantities most accurately, without distortion. Encoding is where
perceptual accuracy and quantitative honesty are won or lost.

## When to invoke
After `visual-intent` has produced an intent record and candidate chart families;
before layout/annotation. Also when reviewing an existing chart's channel choices.

## Inputs
- The intent record (takeaway, audience, medium, data abstraction, reader task,
  candidate families) from `visual-intent`.

## Required intermediate representation
An **encoding table**:
```
field -> channel -> justification
e.g.  revenue (quantitative, key) -> position on common y -> accuracy-critical (ENC-01)
      region  (categorical)       -> hue + direct label   -> nominal; color not sole (ACCESS-01)
color_role per use: categorical | sequential | diverging | highlight | accessibility-redundancy | decorative
baseline decisions, scale transforms, and any escalations noted.
```

## Procedure
1. Rank the data fields by decision-importance. Put the most accuracy-critical
   field on the highest-precision channel available: position > length >
   angle/slope > area > color-intensity (ENC-01).
2. Choose the chart type from the candidate families that best honors that ranking;
   align compared items on a common scale/baseline (ENC-05).
3. Set baselines: bars and columns MUST anchor at zero (ENC-02). For line/point
   charts, decide baseline by ratio-vs-difference intent and **surface it as an
   explicit choice** (UNC-01, ESCALATE) — do not silently truncate.
4. Reject low-accuracy encodings where precision matters: no area/intensity for
   precise magnitudes (ENC-03); no pie/donut for many-category comparison (ENC-04);
   pictograms only for whole counts (ENC-07); avoid 3-D unless the phenomenon is
   spatial (ENC-10).
5. Classify every use of color as categorical / sequential / diverging / highlight
   / accessibility-redundancy / decorative. Match palette class to data (COLOR-04);
   for continuous data use a perceptually uniform, monotonic-lightness map
   (COLOR-01, COLOR-02); never rainbow/jet (COLOR-03); never deform a map (COLOR-05);
   give every color a reason (COLOR-06).
6. Apply the accessibility the active modes ask for (~/dev/MandrakeWorkflows/visualize/principles/modes.md).
   `colorblind_safe` (journal, public web): color never the sole cue (ACCESS-01), no
   red/green at equal luminance (ACCESS-02), lightness differences (ACCESS-04).
   `print_grayscale`: make it read in grayscale first (ACCESS-05). Default: neither.
7. Keep the encoding simple (ENC-08) and set style deliberately rather than
   accepting library defaults (ENC-09), following the shared style rules in
   `~/dev/MandrakeWorkflows/visualize/principles/style.md`. Control gridline/label density (PERC-01);
   separate touching color cells (PERC-02).
8. Hand the encoding table to `visual-composition`. If the data is spatial/physical
   or carries a scientific colormap, also route through `scientific-visualization`.

## Hard constraints
- ENC-02 (zero baseline for bars). ENC-03, ENC-04, ENC-07, ENC-10 (AVOID the named
  distorting encodings). COLOR-01, COLOR-02, COLOR-04 (MUST, continuous color).
  COLOR-03, COLOR-05 (AVOID). ACCESS-01, ACCESS-02 (MUST when `colorblind_safe`).

## Strong heuristics
- ENC-01, ENC-05, ENC-08, ENC-09 (SHOULD). COLOR-06, ACCESS-04, ACCESS-05,
  PERC-01, PERC-02 (SHOULD).

## Context-dependent guidance
- UNC-01 (ESCALATE): non-bar baseline is a message-dependent decision; state ratio
  vs difference and disclose any crop.
- ENC-01 relaxes when magnitude reading is not required (gestalt/overview only).
- ENC-10's exception: inherently spatial phenomena and animated science viz.

## Failure modes
- Key quantity placed on a weak channel (area/color) → misread magnitudes.
- Truncated bar baseline → lies about ratio.
- Rainbow/jet or non-uniform colormap → false gradients and CVD failure.
- Color as the only distinction → invisible to CVD readers and in grayscale.
- Too many simultaneous encodings → decoding overload (see MEDIA-05).

## Validation checks
- The most decision-critical field is on position/length where feasible (ENC-01).
- Every bar/column axis includes zero (ENC-02).
- `print_grayscale`: grayscale render preserves ordering (COLOR-02) and distinctions (ACCESS-05).
- Each distinct color maps to a distinct intended meaning (COLOR-06).
- `colorblind_safe`: CVD simulation keeps categories distinct (ACCESS-02).

## Repair strategies
- Re-map the key field to a stronger channel; demote the decorative one.
- Swap rainbow → a documented perceptually-uniform map; swap pie → sorted bar.
- Add a redundant non-color channel (direct label, shape, lightness) to satisfy
  ACCESS-01 without new clutter.

## Output contract
A justified encoding table (field→channel→reason, color roles, baseline/scale
decisions, escalations), handed to `visual-composition`.

## Source basis
ENC-01/05 (S02, S15); ENC-02/03/04/06/07 (S04, S15); ENC-08/09 (S03, C1); ENC-10 (S09).
PERC-01/02 (S07, C1, S05). COLOR-01..05 (S05, S09, S07, S03); COLOR-06 (S03, S07).
ACCESS-01/02/04/05 (S16, S05, S06, S09). UNC-01 (S02, S10). See principles.yaml.

## Known open questions
- Default weights for trading channel accuracy against clutter (needs QA-04 data).
- Automatic selection among documented perceptually-uniform maps by data semantics.
