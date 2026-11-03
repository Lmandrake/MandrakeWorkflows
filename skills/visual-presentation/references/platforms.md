# Platform notes: what each medium can do with motion

Described by capability, not by library. Facts marked **[vendor]** were read on the vendor's own
help page (sources P22, P23, P41 in `~/dev/MandrakeWorkflows/visualize/sources/SOURCES.md`; summary in
`~/dev/MandrakeWorkflows/visualize/presentation/TOOLING.md`). Facts marked **[unverified]** are
background knowledge nobody has checked in an app yet; the owner's manual slide-app check (brief
Q10) is still open. The per-principle verdicts (holds / partial / unsupported / unverified) are in
each entry's `platforms:` field in `~/dev/MandrakeWorkflows/visualize/principles/principles.yaml`.

## The capability that matters most: matching an object across two slides

A transition that keeps marks identifiable (motion.02, motion.29) needs the app to know that a shape
on slide A is the same shape on slide B. Ask that first (motion.26, ESCALATE); everything else is
detail.

| Capability | PowerPoint | Keynote | Google Slides | HTML |
|---|---|---|---|---|
| Matched-object transition between slides | yes, Morph [vendor]; matches Objects, Words or Characters | yes, Magic Move [vendor]; Match By Object, Word or Character | none found; absence is [unverified] | yes; the builder controls mark identity directly |
| Native charts survive that transition as moving marks | no (charts do not Morph; motion.26) | [unverified] | n/a | yes |
| Per-object builds (enter, emphasis, exit) | yes [unverified detail] | yes, builds and actions [vendor: covered by separate guides] | yes, from a drop-down [vendor] | yes |
| Triggers | on click, with/after previous [unverified] | on click or automatic with delay [vendor] | On click, After previous, With previous [vendor] | anything; use the step contract |
| Easing control | partial (motion.08) [unverified] | Acceleration: none, ease in, ease out, both [vendor] | a speed slider only; easing [unverified] | full |
| Duration control | yes [unverified] | Duration [vendor] | speed slider [vendor] | full |
| Line-by-line text build | yes [unverified] | yes [unverified] | "By paragraph" [vendor] | yes |
| Honours the OS reduced-motion setting | not mentioned on vendor pages | not mentioned | not mentioned | must, by code (motion.17) |

## What to do on each

- **PowerPoint.** For a chart that must change view, draw the marks as shapes so Morph can match
  them, or step through static slides with matched labels (motion.26). Keep per-object effects to
  the data's job (motion.14 cuts the rest).
- **Keynote.** Magic Move is the nearest slide-app equivalent of a data transition. Set Acceleration
  to ease in and out for tracked marks (motion.08). Turn off the fade of unmatched objects when it
  would show marks appearing without a datum (motion.05).
- **Google Slides.** Plan for cuts and simple builds. A view change that needs identity becomes a
  stepped static sequence with the same labels in the same places (motion.26, motion.04).
- **HTML.** Everything is possible, which is the risk. Implement the step contract and pass the
  gates (SKILL.md, quality gate); honour reduced motion (motion.17); keep scroll pieces tied to the
  reader's scroll and never take it over (motion.25); give a pause control to anything that plays
  by itself for over five seconds beside other content (motion.18).

## Slides have no per-viewer motion setting

A projected talk is one shared screen. The slide form of reduced motion is motion.16: the deck must
make its point with motion off, and the PDF or recording posted afterwards is checked as a
motion-off artifact (`~/dev/MandrakeWorkflows/visualize/principles/conflicts.md` section 15).
