---
name: visual-presentation
description: >
  Front door for slide decks and animated HTML pages made to present or communicate: slides in
  PowerPoint, Keynote, Google Slides, markdown outlines or HTML, builds and transitions, Morph or
  Magic Move, animated charts for a talk, scrollytelling and stepped explainer pages. Use whenever
  the user says "make slides", "draft the deck in markdown", "fix my titles", calls a deck cryptic
  or too mathy, asks whether a transition or build should be animated, wants a chart animated for
  a talk, or is building a scroll-driven story page. Decides first whether motion earns its place
  (default: static), then applies the claim-title slide rules and the motion.* principles.
---

# Visual Presentation

## Purpose
A deck or a stepped web page is an argument delivered over time. This skill owns two things:
the **static-slide core** (every slide makes a claim and defends it) and the **motion decision**
(whether anything should move, and if so how). The motion evidence is mostly negative, so the
skill's core is knowing when not to animate.

## When to use
- Building, outlining, rewriting or critiquing slides, titles, subtitles or speaker notes.
- Any question of builds, transitions, Morph, Magic Move, or "should this animate".
- An animated chart for a talk, a data video, a scrollytelling or stepped explainer page.
- `visual-intent` handed off with a medium of `deck_projected`, `deck_read_ahead`, or an
  animated or scroll-driven web page.

**Not for:** a static figure for a paper or report, a dashboard, a poster or wall display, data
art (route to `visual-intent`, `visual-beautiful`, or `scientific-visualization`). A chart that
sits on a slide still gets its encoding from `visual-encoding`; this skill decides how the slide
and its steps carry it.

## The static-slide core
Read `~/dev/MandrakeWorkflows/skills/visual-presentation/references/slides.md` for every deck. Its
rules came over unchanged from technical-presentation: title = the takeaway, subtitle = what the
slide holds; primary bullets are spoken, secondary text is for the eye; no arithmetic in titles or
bold; open with where we stand, then the plan; examples, plain words, no colleagues' names; draft
in markdown first when speed is asked for; and its self-check before showing a deck.

## The motion decision (make it before any animation is designed)

**1. Default: static.** A static view or a stepped static sequence (hard cuts between steps) is
the default (motion.01). A sequence of views is not by itself a reason to move anything.

**2. The owner's rule (motion.28).** Animate, or reveal progressively, only when **the change
itself is the message** and **its moment lands with the narration** (or the caption, when there
is no speaker). If the final frame already carries all the meaning, a build that withholds parts of
it has no point per step: it conceals rather than communicates. In the owner's blind viewing, a
ranking reshuffle animated onto a slope chart was "just fluff", because the slope lines already
showed which item went where; a timed reveal of a sharp drop, landing as the narration named it,
was the piece he valued.

**3. The jobs motion does well.** Name the job in one sentence, and record why the static
alternative does it worse (motion.01 checks). The named jobs:
- **Keep marks identifiable across a change of view** of the same data: filter, sort, rescale,
  regroup, step in time (motion.02), unless the end frame already links start to end (motion.04).
- **Draw attention to one change**, one target at a time (motion.15), stopping on the claim
  (motion.22).
- **Show a process that is itself change** in time or space: a physical process, a procedure, a
  spatial phenomenon (motion.24), with a key-frame static beside it (motion.16).
- **Morph between chart types** only when marks map one to one (motion.29).
- **A build** only when each step carries its own stated point (motion.23 under motion.28).

**4. When not to animate, even with a job.**
- Many trajectories, or any reading that compares several frames: small multiples or traces
  (motion.03). Before-and-after comparison: keep both on screen (motion.04).
- Nearly everything would move at once and tracking individuals is not the task: cut (motion.04).
- Decoration with no data or argument (entrance flourishes, bounces, spins, animated titles,
  parallax): cut it (motion.14).
- The slide app cannot match the objects across slides: stepped static sequence (motion.26).
- "People liked it" is not evidence it communicates (motion.20).

Write the decision down before building:
```
motion_decision: static | animated
job:             <one sentence, or "none">
static_rival:    <the best static version, and why it loses (or wins)>
lands_with:      <the narration line or caption the change lands on>
final_frame:     <does it carry all the meaning? if yes, why move at all?>
```

## How to animate (when the decision is "animated")
The principles live in `~/dev/MandrakeWorkflows/visualize/principles/principles.yaml` (ids
`motion.01` to `motion.29`). Read the entries you apply; do not work from this summary alone. Each
entry carries `checks`, `exceptions`, `platforms` and a `validation` line saying how far it has
been tested.

| Concern | Rule | Ids |
|---|---|---|
| Frame validity | Every frame of a transition is a valid chart; a mark keeps its datum; unchanged values do not move (MUST) | motion.05 |
| Motion off | Every held frame, above all the last, is a complete static chart (MUST) | motion.16 |
| Scale | Fixed across steps; stage any rescale apart from value change | motion.06 |
| Staging | One stage, or two simple ones, per advance | motion.07, motion.21 |
| Easing | Slow-in, slow-out on tracked marks; no overshoot on data | motion.08 |
| Timing | About 1 s per data transition (0.7 to 2 s, capped near 2 s); colour or opacity 0.3 to 0.7 s; interface 100 to 500 ms | motion.09, motion.27 |
| Attention | About four things to follow; move groups together; one target at a time | motion.10, motion.11, motion.15 |
| Pacing | Short segments the speaker or reader advances, not one auto-played run | motion.12, motion.19 |
| Words | Narrate with the motion; do not caption the narration over moving marks; label the mover | motion.13 |
| Endings | Stop on the claim; motion must not imply a cause the data lack | motion.22 |
| Web | Honour reduced motion; no flashing over 3 per second; pause control for long autoplay; scroll steps tied to the reader's scroll | motion.17, motion.18, motion.25 |

The recorded tensions between these and their working defaults are sections 10 to 17 of
`~/dev/MandrakeWorkflows/visualize/principles/conflicts.md`. Two are **open**: build order versus
"a reveal is concealment" (section 16; working default: build only when each step carries a point)
and motion.05 being uncheckable mid-morph (section 17; working default: sample mid-transition
frames by eye and record that you did).

## Platform notes
Read `~/dev/MandrakeWorkflows/skills/visual-presentation/references/platforms.md` before planning
motion in a slide app. In short: PowerPoint and Keynote can match objects across slides (Morph,
Magic Move), but native charts do not Morph; Google Slides has a smaller set of builds and
transitions and no matched-object transition was found (unverified); HTML can do anything, so the
gates below are what keep it honest. Slide apps have no per-viewer reduced-motion setting, so the
deck must make its point with motion off (motion.16). Slide-app facts beyond the vendor pages are
unverified until the owner's manual check runs.

## Quality gate
**For HTML pieces:**
1. Implement the step contract in `~/dev/MandrakeWorkflows/visualize/presentation/CAPTURE.md`:
   `window.__steps` (step count) and `window.__next()` (advance one step; resolves when its motion
   has settled). Reaching the same resting state under reduced motion.
2. Capture: `python3 ~/dev/MandrakeWorkflows/visualize/tools/motion_capture.py PIECE.html RUN_DIR`,
   with RUN_DIR under agent storage (`~/ClaudeWork/mandrakevisualize/motion-test/<piece>/`), never
   a repo.
3. Gate: `python3 ~/dev/MandrakeWorkflows/visualize/tools/motion_gates.py RUN_DIR`. It fails on
   motion duration out of band, flashing, missing or blank reduced-motion frames, a final frame
   that differs from the reduced-motion final frame, and console errors.

**Always also** hand every slide and every held frame (the `step_NN_rest.png` captures for HTML;
a PDF export for a slide deck) to `visual-render-qa` at final size.

**What the gates cannot check.** They do not test comprehension: a piece can pass every gate and
still say nothing. They do not check that mid-transition frames are valid charts (motion.05 during a
morph), so that stays the builder's eye. Duration and flash detection are sampled at about
0.1 to 0.2 s, so finer timing differences are invisible to them. Slide-app builds are not captured
at all; check them by exporting to PDF and by watching the deck run.

## Evidence, honestly
The motion rules are grounded in research (animated-transition and trend-animation studies,
multimedia-learning work, accessibility standards, vendor guidance; tiers A to C in the registry).
They are not yet validated here. Two rounds of model-judge testing (14 briefs, static versus
unguided versus principled animation) hit the ceiling and could not separate static from
animated: model judges inspect frames at leisure, so transience and pacing cannot hurt them
(`~/dev/MandrakeWorkflows/visualize/evaluation/runs/2026-10-28-motion/RESULTS_ROUND1.md`,
`~/dev/MandrakeWorkflows/visualize/evaluation/runs/2026-10-28-motion/RESULTS_ROUND2.md`). The
only real-time viewing is the owner's blind rating of three animations (n=1), which motion.28
encodes. Following the principles cost no accuracy against unguided animation; whether it helps
needs human viewers in real time. Say this when asked how sure the advice is.

## Hand-offs
- **From `visual-intent`**, when the medium is slides or an animated or scroll-driven page. Take its
  intent record (takeaway, audience, medium) as given; each slide's title is a takeaway.
- **To `visual-encoding`, then `visual-composition`**, for each chart on a slide or step. This
  skill does not choose channels or colours; it decides how the chart is staged over time.
- **To `visual-render-qa`**, last, for every slide and held frame, after the motion gates.

## Self-check before showing a deck or page
- The titles, read alone in order, tell the story as conclusions (slides.md self-check).
- A `motion_decision` exists for every moving element, with its job and its static rival.
- No reveal of a chart whose final frame already says everything (motion.28).
- Every held frame and the motion-off version make the point (motion.16).
- HTML: the step contract is implemented and the gates pass; mid-morph frames were checked by eye.
- Every slide and held frame went through `visual-render-qa`.
