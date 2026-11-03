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

## 10. Staging: "do one thing at a time" vs. "minimise stages"
**Tension.** Fisher (P27, tier C) and the DynaVis design guidance (P04) say to stage
complex transitions so each change finishes before the next starts. P04's own data
showed heavily staged transitions *raised* error and drew laughter, and P14's crowd
ranking (n = 53) put single-stage designs above two- and three-stage ones at equal
total time.
**Default.** One stage, or two simple stages, typically axes then values (motion.07).
**Flip.** When the speaker clicks each stage as a separate point, each stage is a
build step under motion.12 and motion.23, not a sub-stage competing for one second.

## 11. Duration: data transitions (~1 s) vs. interface motion (100-500 ms)
**Tension.** Data-transition studies recommend about one second, or a second per
stage (P04, P05, P06; P14 viewers liked 2 s). Design systems give 70-700 ms (Carbon,
P21) and 50-600 ms with 1 s only for rare ambient motion (Material, P19) for interface
elements.
**Resolution.** Split by what moves: data marks that must be tracked follow motion.09;
interface chrome follows motion.27. Do not carry UI tokens onto data marks.

## 12. Does animation help? Positive transition studies vs. negative trend studies
**Tension.** Animated transitions beat static cuts for tracking and change estimation
(P04), animated transitions raised engagement (P13), and the instructional
meta-analysis finds d = 0.37 overall (P02, abstract only). Animated trend playback was
less accurate than small multiples (P05), and the classic review (P01, metadata only)
argues that benefits vanish once information is equated.
**Resolution.** These are different tasks. Animation helps to *bridge* two views of the
same data and to depict processes that are themselves change; it hurts when the reader
must *compare* many frames or follow many independent movers. Encoded as motion.02 and
motion.24 versus motion.03 and motion.04, with motion.01 as the default. This is the
main hypothesis the animated-vs-static test exists to check.

## 13. Redundancy effect vs. assertion headlines on narrated slides
**Tension.** Mayer and Moreno (P03): narration alone beats narration plus identical
on-screen text *over an animation* (d = 0.69). Assertion-evidence (P16, P28) puts a
full-sentence claim on screen while the speaker talks.
**Resolution.** They do not collide head-on. P03's redundancy is the *same words* in two
channels while an animation plays, and P03 itself finds that with no animation,
narration plus text helps. An assertion headline is one sentence, not a transcript.
Default: keep the assertion headline and do not caption the narration over a moving
chart (motion.13). Flip: for audiences without sound, the text *is* the narration.

## 14. Material easing curves vs. Material springs
**Tension.** Material 3's easing-and-duration system (P19: decelerate in, accelerate
out, durations by size) is marked as no longer maintained; the replacement spring
system's spatial tokens *overshoot and bounce into place*. An overshoot on a data mark
briefly shows a value the data do not have, which breaks motion.05.
**Resolution.** Springs and overshoot are allowed only for interface chrome
(motion.27). Data marks use non-overshooting ease-in-out (motion.08). Material's own
"effects" springs (opacity, colour) do not overshoot and are fine for fades.

## 15. Reduced motion: web standard vs. silent slide apps
**Tension.** WCAG 2.3.3 and MDN (P17, P18) treat removable motion as the norm on the
web. The PowerPoint, Keynote and Google Slides help pages captured (P22, P23, P41) do
not mention reduced motion at all, and a projected talk has a shared screen with no
per-viewer setting.
**Resolution.** On the web, motion.17 is a MUST. For slides, the medium-independent
form applies: the deck makes its point with motion off (motion.16), and anything
posted afterwards (PDF, recording) is checked as a motion-off artifact. Whether any
slide app honours the OS setting is unverified; the manual app check (brief Q10)
should look.

## 16. Build in argument order vs. "a reveal is concealment" (RESOLVED, 2026-10-28)
**Tension.** motion.23 (tier C, practitioner) builds a chart context-first, one click
per point, on the logic of segmenting (P03) and one-change-per-step (P11). The owner's
blind viewing (n=1, RESULTS_ROUND2.md) rated a principled build of B01 neutral and an
unguided one "just fluff": the final frame held all the meaning, so the build only hid
part of the graph. motion.28 encodes his rule.
**Working default.** Build only when each step carries its own stated point (motion.23's
new check); otherwise show the chart whole (motion.28).
**Resolution (owner ruling 2026-10-28).** The working default stands as the rule: build only
when every click lands a point the speaker states; otherwise show the chart whole and mark the
point with highlight or callout. motion.23 builds are allowed only under that condition. The
motion.* rules are calibrated to the owner's taste, with him as the sole viewer ("I'm going to
be the subject not others. This is for my tastes."); his timed viewing can revise this.

## 17. motion.05 is a MUST that no gate can check mid-morph (RESOLVED, 2026-10-28)
**Tension.** motion.05 requires every transition frame to be a valid chart, and the
chart-type exception (motion.29) requires the invariant to hold in every frame (a split's
parts sum to the total). The arm-P builder could not verify B11's line-to-stack frames;
motion_gates.py checks duration, flashing and the final frame only.
**Resolution.** A piece states its invariant as `window.__frameCheck()` and motion_gates.py
fails any sampled frame that breaks it (`mid_frame_invariant`); a generic `no_excursion`
WARN flags overshoot or off-path marks without one. Fixtures split_ok/split_bad prove a
morph with valid end states but a broken middle now fails. **Limit:** sampled at about
0.1 to 0.2 s, so a break shorter than that can be missed; a piece without `__frameCheck`
is still self-reported (the gate says SKIP), so a builder of a morph should write one.
