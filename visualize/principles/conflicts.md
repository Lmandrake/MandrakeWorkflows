# Documented conflicts between good sources

These are real disagreements among authoritative sources. A mature system does
not pretend they resolve cleanly; it records the tension, states which force
governs by default, and names the context that flips it. Each entry references
the registry IDs it touches.

## 1. Minimalism vs. scaffolding
**Tension.** "Remove non-data ink" (LAYOUT-01, S03/S06, echoing Tufte's
data-ink ethos) vs. the finding that novices and lay audiences often need
explanatory scaffolding — reference lines, redundant labels, framing text
(INTENT-03, ANNO-01/03, S02).
**Default.** Remove ink that serves no reader (LAYOUT-01).
**Flip.** When the audience is non-expert or the chart type is unfamiliar,
scaffolding that measurably aids comprehension is *information*, not clutter, and
is retained. The test is reader-serving purpose, not ink minimization for its own
sake.

## 2. Direct labels vs. clutter
**Tension.** Prefer direct labels over legends (ANNO-01, S02/S07/S13) vs. clutter
reduction (LAYOUT-01/02) and legibility (ANNO-10). With many series, direct
labels collide and *become* clutter.
**Default.** Direct-label (ANNO-01).
**Flip.** When series density makes in-place labels collide, fall back to a
compact legend or selective labeling of only the highlighted series (HIER-03).

## 3. Zero baseline: hard for bars, soft elsewhere
**Tension.** "Always start the axis at zero" is stated absolutely by many style
guides, but is genuinely context-dependent. Bars encode magnitude by length, so
truncation lies (ENC-02, hard MUST). Line/point charts encode by position, where
a difference-focused message may legitimately crop the axis (UNC-01).
**Resolution.** Split by encoding: hard constraint for bars (ENC-02); an
escalated, ratio-vs-difference decision for non-bar charts (UNC-01), modeled as a
weighted constraint per Draco (CRIT-04, S10). This is the cleanest example of the
hard-vs-soft discipline (QA-01).

## 4. Density vs. simplicity (Tufte-style data density vs. Few/Franconeri clarity)
**Tension.** Maximize legitimate data density and small multiples (LAYOUT-02) vs.
limit simultaneous encodings and split figures (MEDIA-05, S09) and reduce clutter
for fast reading (S02).
**Default.** Simplicity per figure; use small multiples to add data without
overloading a single panel (LAYOUT-02 + MEDIA-05 together).
**Flip.** For expert analytical audiences doing exploration, higher density in one
view can be warranted (INTENT-03).

## 5. Rainbow color: "never" vs. "avoid unless justified"
**Tension.** Crameri et al. (S05, Tier A) treat rainbow/jet as essentially never
acceptable for data; Rougier et al. (S03, Tier A but design-guidance) phrase it as
"avoid unless justified."
**Resolution.** The registry adopts the stronger, more specific authority: COLOR-03
is AVOID (hard). S05's perceptual-uniformity argument is mechanistic and leaves no
data-encoding case where rainbow is correct. Rare non-data decorative uses fall
outside the scope of "encoding a data dimension."

## 6. Standard vs. bespoke notation (and familiar vs. novel chart types)
**Tension.** Follow standardized/ familiar vocabularies (DIAG-04, SEM-03) vs. the
freedom to invent a better-fitting custom encoding when the standard is a poor fit.
**Default.** Use the standard/familiar form (lower learning cost, fewer misreads).
**Flip.** When a standard form genuinely cannot express the relationship, a custom
encoding is allowed *if* its grammar is declared and explained (DIAG-01/05) — the
cost of novelty is paid down with an explicit legend and rationale (CRIT-01).

## 7. WCAG thresholds: web norm vs. figures/slides
**Tension.** WCAG 2.2 contrast minimums and text-size categories (ACCESS-03, S16)
are written for web UI. Print figures (Nature's 5–7 pt ceiling, S06) and projected
slides live under different constraints and viewing distances.
**Resolution.** Keep the *principle* of a measured contrast floor and color
redundancy (ACCESS-01/03/04), but translate the specific numeric thresholds and
font sizes to the medium (MEDIA-01/02) rather than transferring web pixel values
literally. Do not carry Nature's small print-font ceiling onto slides or posters.

## 8. Patterns vs. solid color for redundancy
**Tension.** Nature figure guidance (S06) leans toward solid colors plus keys and
away from busy patterns; WCAG technique G111 accepts color+pattern as a valid
redundant cue (both serve ACCESS-01).
**Resolution.** Both satisfy the no-color-alone requirement by different means.
Prefer the mechanism that adds least clutter for the medium (LAYOUT-01): a second
non-color channel that is also low-noise (position, direct label, lightness) is
usually better than dense fill patterns, but patterns are acceptable when other
channels are unavailable.

## 9. 3-D: avoid vs. NASA SVS routine use
**Tension.** Avoid 3-D for data (ENC-10, S09) vs. NASA SVS's routine, effective 3-D
(S12).
**Resolution.** The exception is built into ENC-10: 3-D is justified when the
phenomenon itself is spatial/volumetric and, typically, when motion/animation
resolves the depth ambiguity that harms static 3-D. It remains AVOID for
non-spatial quantitative comparison.
