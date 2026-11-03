---
name: visual-intent
description: >
  The front door of the visual-reasoning stack. Use FIRST, before any chart is
  drawn, whenever the task is to communicate data visually (a chart, figure, slide
  graphic, map, diagram, or infographic). Establishes communication intent,
  audience, the abstract data + task, and selects a chart family from the analytic
  relationship — so downstream encoding/composition choices are derivable, not guessed.
  By default hands off to both the CLEAR and the BEAUTIFUL family (visual-beautiful).
---

# Visual Intent

## Purpose
Fix *what the visual must accomplish and for whom* before deciding *how it looks*.
Most serious visualization failures originate upstream of the encoding — solving
the wrong problem or mis-abstracting the data — and no amount of styling repairs
them (S01). This skill produces the intent contract every other skill consumes.

## When to invoke
- At the start of any request to make a chart, figure, map, diagram, or data slide.
- When a draft "looks fine" but you cannot state its one-sentence takeaway.
- When someone asks which chart type to use.
Do not skip it because the request seems simple; an unexamined default is where the
wrong-problem failure hides.

## Inputs
- The data (or a description: fields, types, size, provenance).
- The audience and the delivery medium.
- What decision or understanding the visual should enable.

## Required intermediate representation
Produce an **intent record** before proposing any chart:
```
takeaway:        <one sentence the reader should leave with>
audience:        <who; graphical literacy / numeracy / domain knowledge>
medium:          <one of the medium profiles below>
data_abstraction: <fields as quantitative | ordinal | categorical | relational | spatial | temporal>
reader_task:     <compare | rank | correlate | locate | trend | part-to-whole | distribution | flow | deviation>
analytic_relationship: <the structure to reveal>
candidate_families: <1-3 chart families that fit the relationship + task>
```

## Procedure
1. Characterize the domain problem, users, data, and task abstraction (INTENT-01,
   INTENT-02). Name the reader task explicitly.
2. Name the audience and its literacy; tailor complexity and framing (INTENT-03).
3. Write the takeaway sentence — for a captioned figure, draft the caption first
   (INTENT-04).
4. Map the reader task to an analytic relationship, then to candidate chart
   families using the intent→family table (SEM-01). Treat this as completing a
   spec given data + task, not free invention (SEM-02).
5. Prefer conventional/familiar mappings and chart types unless a reason to break
   them is recorded (SEM-03). Use a map only when geography is the message (SEM-05).
6. Hand the intent record to `visual-encoding`. Do not choose channels or colors here.
7. **Family handoff.** Default, when the request names neither pole: a CLEAR version
   (step 6), a BEAUTIFUL version and one combined candidate (`visual-beautiful`). An
   explicit "clear" narrows to CLEAR; "beautiful", art or exhibition to `visual-beautiful`.
   Exact values or a decision: CLEAR is always included; "beautiful" adds alongside it.
   Record any `modes:` the destination implies (`principles/modes.md`); none is default.

### Intent → chart family (SEM-01, S04)
deviation → diverging bar / surplus-deficit · correlation → scatter / connected
scatter · ranking → sorted bar / dot plot · distribution → histogram / box / violin
/ strip · change-over-time → line / area / slope · magnitude → bar / lollipop ·
part-to-whole → stacked bar / treemap (avoid pie for many parts, ENC-04) · spatial
→ choropleth / proportional-symbol map (ENC-06) · flow → Sankey / chord / network.

### Medium profiles
- **deck_projected** — read at distance, seconds of attention: one idea per view,
  large type, high contrast, minimal detail.
- **deck_read_ahead** — read on a screen up close: moderate density allowed.
- **scientific_publication** — dense, self-contained figure + caption, print sizes.
- **technical_report** — explanatory, moderate density, reference-quality.
- **infographic** — lay audience, narrative, heavier scaffolding.
- **dashboard_or_exploratory** — interactive; key message visible before interaction.
  Live, long, many-series or drill-down time streams: a dashboard over a time-series store
  exists; `~/dev/MandrakeWorkflows/visualize/principles/time-series-and-dashboards.md` says when it beats a figure.
- **ambient_overlay** — always on, peripheral, glanced at rather than read (a desktop
  companion, a status creature). No labels by default: hover slows the mark and shows
  its name (owner, Visitors 2026-10-31; earlier studies: make the rest discoverable on
  hover). Idle near still, every motion a datum (motion.14, motion.15); a datum the
  reader cares about is never the subtlest thing on screen (HIER-01). *Provisional*,
  invented by the Visitors builders and untested: no end frame, all-day tolerance as a
  criterion, avoid the focused window, a screen-area budget.
- **scientific_spatiotemporal** — spatial/temporal science data (hand to
  `scientific-visualization`).

## Hard constraints
- INTENT-01, INTENT-02, INTENT-03, INTENT-04 are MUST: no encoding is proposed
  until the intent record exists and names task, audience, and takeaway.

## Strong heuristics
- SEM-01, SEM-03, SEM-05 (SHOULD): select by analytic relationship; respect
  convention; reserve maps for geographic messages.

## Context-dependent guidance
- For exploratory dashboards the single-takeaway rule relaxes (INTENT-04 exception),
  but a primary question per view is still required.
- For expert analytical audiences, higher density and less scaffolding are
  acceptable (INTENT-03).

## Failure modes
- Wrong problem: the visual answers a question no one asked (missing INTENT-01).
- Wrong abstraction: continuous data treated as categorical, or vice versa.
- Chart chosen by habit/aesthetics rather than relationship (violates SEM-01).
- No decided takeaway → nothing to optimize downstream.

## Validation checks
- The intent record is complete (all fields filled).
- The candidate families actually express the named analytic relationship.
- The takeaway is a claim, not a topic.

## Repair strategies
- If you cannot write a takeaway, the request is under-specified — ask the user one
  focused question rather than guessing.
- If two chart families tie, pass both to `visual-encoding` and let channel-accuracy
  (ENC-01) break the tie.

## Output contract
A completed intent record + 1–3 candidate chart families, handed to `visual-encoding`.

## Source basis
INTENT-01/02/03/04 (S01 Munzner nested model; S02 Franconeri; S03 Rougier; S14
Jambor, reference_only). SEM-01/02/03/05 (S04 FT Visual Vocabulary; S10 Draco;
S02). See ~/dev/MandrakeWorkflows/visualize/principles/principles.yaml.

## Known open questions
- How to auto-detect audience literacy when the user does not state it.
- A crisper decision rule for map-vs-chart when geography is partially relevant.
