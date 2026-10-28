# Failure taxonomy

Visualization failures are not one kind of thing. They occur at distinct levels,
and — following Munzner's nested model (S01) — a defect at one level cannot be fixed
by working at another. Restyling a chart cannot cure a wrong-abstraction error; a
better colormap cannot cure a wrong-problem error. The critic's job is to locate
each defect at the *correct* level and route it to the skill that owns that level.

For each level: what it is, how it shows up, which skill owns it, and the registry
principles that guard against it.

## Level 1 — Wrong problem
**What.** The visualization answers a question no one needed answered, or misframes
the user's actual goal.
**Symptoms.** Stakeholders say "interesting, but that's not what I asked"; the
figure has no decision it supports.
**Owner.** `visual-intent`. **Guards.** INTENT-01, INTENT-02, CRIT-06.
**Note.** This is the most expensive failure and the least visible in the render —
the chart can be beautiful and still wrong here.

## Level 2 — Wrong abstraction
**What.** The data or task is modeled incorrectly: continuous treated as
categorical, a ranking task served as a distribution, relational data forced into a
table.
**Symptoms.** The chart type cannot express the real relationship; readers do the
mental arithmetic the chart should have done.
**Owner.** `visual-intent` (data_abstraction, reader_task). **Guards.** INTENT-02,
SEM-01, SEM-02, SEM-05.

## Level 3 — Wrong encoding
**What.** Correct data/task, but channels chosen poorly: key quantity on a
low-accuracy channel, truncated bars, pie for many categories, rainbow colormap,
color as the only cue.
**Symptoms.** Values are systematically misread; magnitudes look wrong; CVD or
grayscale readers lose information.
**Owner.** `visual-encoding` (color/accessibility) + `scientific-visualization`
(colormaps, science). **Guards.** ENC-01..10, COLOR-01..06, PERC-01/02,
ACCESS-01/02/04/05.

## Level 4 — Wrong composition
**What.** Honest encodings arranged badly: no visual hierarchy, competing focal
points, detached legends, clutter, poor figure-ground, missing labels/units.
**Symptoms.** The eye lands arbitrarily; readers cannot find the takeaway; the
figure feels busy or flat.
**Owner.** `visual-composition`. **Guards.** HIER-01..04, LAYOUT-01..05,
ANNO-01..10.

## Level 5 — Wrong scientific representation
**What.** Domain-specific integrity failures: features with no data referent,
undisclosed exaggeration/simulation, node-link hairballs, undocumented diagram
vocabulary, illegible maps, misrepresented uncertainty.
**Symptoms.** The figure is misleading to a domain expert; it asserts structure the
data does not support.
**Owner.** `scientific-visualization`. **Guards.** SCI-01..05, UNC-01/02/03,
NET-01..04, DIAG-01..05, MAP-01/02, SEM-04.

## Level 6 — Physical rendering defect
**What.** The intent was right but the actual render is broken: overlapping/clipped
text, cut-off legends, occluded marks, insufficient contrast, illegible-at-final-size
type, colors that shifted in export.
**Symptoms.** Only visible when you look at the real output at final size in the
real medium.
**Owner.** `visual-render-qa`. **Guards.** QA-05..08, MEDIA-01/02/03, ACCESS-03,
PERC-01.

## Level 7 — Wrong communication strategy
**What.** Everything is technically correct but the artifact does not persuade or
inform the intended audience: wrong medium, wrong density, uncertainty framed
un-intuitively, aesthetics that mislead, no clear narrative for a lay audience.
**Symptoms.** The read-back takeaway differs from the intended takeaway even though
all gates pass.
**Owner.** `visual-critic` (with `visual-intent`). **Guards.** INTENT-03, INTENT-04,
UNC-02, MEDIA-04/05, CRIT-03/05.

---

## Using the taxonomy
1. When a defect is found, name its level (1–7) before proposing a fix.
2. Route the fix to the owning skill; do not fix at a lower level than the defect.
3. Re-run `visual-render-qa` after any Level 3–6 change; re-run `visual-intent`
   after any Level 1–2 change.
4. Levels 1, 2, and 7 are easy to miss because they are invisible in the render —
   the read-back test (QA-05) is the main safeguard.
