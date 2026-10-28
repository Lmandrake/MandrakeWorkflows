---
name: blind-evaluation
description: >
  Design and run a head-to-head comparison whose result you can actually believe —
  blinding, balanced position assignment, a control that could plausibly have won,
  and honest reading of a small sample. Use this whenever you are about to claim one
  approach beats another: A/B-ing two prompts or configs, comparing a new pipeline
  against the old one, benchmarking a library or model against an alternative, testing
  whether a change actually helped, or judging which of two outputs is better. Also use
  it when someone hands you a comparison result and asks whether it holds up, when a
  result looks suspiciously clean, or when you notice you are about to declare a winner
  after looking at the outputs unblinded. Not for checking that your own work is finished
  (use verification-before-completion) and not for wording the claim once evidence is in
  (use falsifiable-claims).
---

# Blind Evaluation

A comparison is only worth what its design is worth. If you look at two outputs, notice
that one is yours, and pick it, you have measured your own expectations. The protocol
below exists because that failure is invisible from the inside — the reasoning feels
sound either way, so the only defense is arranging things so your preference cannot
reach the verdict.

The expensive failures are rarely "I was biased." They are structural: a control that
never could have won, an arm that always sat in the same slot, a defect in one arm that
you scored as if both were sound.

## When this fires

Any moment you are about to say *this one is better* on the strength of a comparison —
or about to build the comparison that will let you say it. Two configs, two prompts,
two libraries, old pipeline vs new, model A vs model B, with-the-thing vs without.

It also fires **backwards**: when a comparison already exists and you are asked whether
the result holds, run its design through this and report what the design can and cannot
support.

## The protocol

**1. Fix the question and the arms before you build anything.**
Write down what differs between the arms and confirm it is exactly one thing. Both arms
get an identical brief — same goal, same audience, same inputs, same budget. If the arms
differ in two ways you will not be able to attribute the result to either.

*Why:* attribution is the whole point. An "ablation" that ablates two things at once
produces a number with no owner.

**2. Build a control that could have won.**
Two questions decide whether your control is honest. Could a competent practitioner have
produced it, working in good faith without your treatment? And does it clear the same
validity floor you require of the treatment arm?

The second question is the one people skip, and it is the one that bites. If the control
is *defective* — not merely narrower, but broken — then a win tells you the control was
broken. It does not tell you your approach is better. See the worked example below, where
exactly this happened and the claim had to be retracted.

**3. Blind the judge, and balance rather than randomize at small n.**
Strip anything that identifies which arm an output came from, including filenames,
ordering artifacts, and stylistic tells. Then assign arms to slots so that each arm
appears in each slot across the case set. When the unit under comparison is a *set* —
a portfolio, a triptych, a suite, not a single output — the slot is the set's position
in the pair and the verdict is a per-axis set-level score; balance and decode the whole
set as one unit. (The worked example below is exactly this: Set 1 vs Set 2, set position
balanced across cases.)

*Why balance instead of randomize:* at n=3 or n=6, a fair coin will hand you a perfectly
confounded assignment often enough to matter. Randomization only buys you independence
in expectation, and you do not get expectation — you get one draw. Balance is cheap in
advance and impossible to retrofit.

**4. Keep the key in a separate file the judge does not read, and decode only after
every score is written down.**
Not "after I've formed an impression." After the scores exist as text. Once you know
which is which, you cannot un-know it, and every subsequent judgment is contaminated in
a direction you cannot measure.

**5. Make the judge write reasoning, not just a verdict.**
A bare preference is unfalsifiable and teaches you nothing. Written reasoning tells you
*what* drove the win — and it is your only way to catch a judge that latched onto
something irrelevant, like output length or apparent effort.

**6. After decoding, inspect the actual artifacts yourself.**
Do not trust the scoring pass to have noticed everything. This is the step that catches a
defect you had assumed away, and it is where a claimed floor-pass gets falsified.

**7. Re-run against the confound you are most worried about.**
Name the alternative explanation you would find most embarrassing, then design one
re-run that would distinguish it. If the tally survives the re-run *and* the pattern of
individual results shifts, you have real evidence: the aggregate is not an artifact of
the thing you controlled for.

## Confounds worth expecting

**Position.** Whichever arm sits first can win on placement alone. Balanced assignment
prevents it. The tell that you have actually removed it: the aggregate holds while
*individual cases move* — if every case keeps its exact verdict after you swap positions,
you may have changed nothing.

**Defect asymmetry.** Both arms are asserted to be valid; only one actually is. The
result then measures brokenness, not the variable you care about. Prevented by rule 2,
caught by rule 6.

**Surface properties the judge can see.** Count of items, length, polish, apparent
effort. If both arms are structurally identical on the irrelevant dimension, the judge
cannot use it. If they are not, assume it was used.

**Your own framing in the judge's prompt.** Language describing what a good result looks
like will be read as an instruction. Describe the criteria, not the expected winner.

**Memorised material.** Blinding which arm produced an output does not blind the judge from
recognising the underlying material itself. If either arm's content is a public standard,
statute, famous codebase, or otherwise plausibly present in a training corpus, arm-identity
blinding alone leaves a second leak wide open: the judge can recall the "right" answer from
training data rather than read it from what you gave it, and a correct-looking verdict tells
you nothing about which arm it actually used. This is a different axis from position and
requires a different defense — see `defeat-recitation`.

**Differing availability or throughput between the arms.** When the arms are different
*service providers* rather than different prompts or configs, they do not merely produce
different answers — they complete different numbers of cases. One provider's outage, rate
limit, or business-hours slowdown quietly turns a balanced experiment into two different
test sets, and the arm that completed less looks better or worse for reasons that have
nothing to do with quality.

The failure shape: arm A completes 950 of 1000 cases, arm B completes 400. **If B fails
preferentially on the hard inputs — long documents, awkward encodings, whatever strains
it — then comparing quality on B's surviving 400 against A's 950 can make B look superior
precisely because it avoided the cases it was worst at.** Nothing in the quality numbers
shows this; the sample sizes are the only tell, and a report quoting a mean per arm hides
them.

So when arms differ in provider, machine, or network path:

- Fix the **intended** evaluation population up front, and report attempted, completed,
  failed and timed-out **per arm**. Four numbers, not one.
- Analyse quality on the **common completed subset** — the cases both arms finished — and
  say so. A mean over each arm's own survivors is not a comparison.
- Treat availability and throughput as an **operational outcome reported separately**,
  never as something allowed to reshape the quality sample. "A is faster" and "A is
  better" are two findings needing two measurements.
- Keep each arm's outputs isolated until evaluation is complete, so a partial arm cannot
  be topped up from the other and nobody is tempted to compare unequal runs.
- Where an arm's shortfall came from a transient outage rather than from the work itself,
  the missing cases are **not** evidence about that arm — see `resumable-batch-jobs` for
  why a recorded failure is so easily miscounted as a completed one.

## Reading the result honestly

**Set the refutation bar before you look.** What outcome would make you abandon the
claim? Write it down first — that is `falsifiable-claims`, and it should happen before
this protocol runs, not after.

**Say what the sample supports.** At small n, the honest phrasing is *corroborated, not
proven*. A clean sweep at n=3 is encouraging and is not evidence of a general effect.
State the n every time you state the result.

**Read the pattern of margins as mechanism evidence.** If your treatment wins by the most
where the baseline was weakest and by the least where the baseline was already sound,
that pattern is what a real effect looks like. A flat margin regardless of baseline
quality suggests you are measuring something else — judge preference for a house style,
for instance.

**Name which cases are load-bearing.** If some cases turn out to be confounded, the claim
narrows to the ones that are clean. Say so explicitly rather than quietly keeping the
original aggregate.

## Rationalizations that mean stop

| Thought | What is actually true |
|---|---|
| "I'll peek at which is which, I can still be objective" | You cannot verify that from the inside. That is why the key lives in a separate file. |
| "The control is obviously worse, no need to blind it" | You have assumed the conclusion. If it is obvious, blinding costs you nothing and buys you the claim. |
| "The control failed the gates — that proves my point" | It proves your control was broken. Repair it or your win is unattributable. |
| "n=3 all pointed the same way, that's solid" | Consistent is not proven. Report it as corroboration and state the n. |
| "Position probably didn't matter here" | Balancing beforehand is nearly free; re-running afterward is not. |
| "The judge agreed with me, so the design was fine" | A flawed design that returns your expected answer is the hardest kind to notice. |
| "I'll write up the win now and tighten the protocol next time" | The write-up is the artifact that outlives the caveat. Fix the claim, not the follow-up. |

## Worked example: a retracted floor-pass

This repository's `visualize/` directory contains a real instance of rules 2 and 6 firing, and it is worth reading
rather than paraphrasing.

A three-case comparison judged principled portfolios against arbitrary-variety controls.
The initial assessment stated both arms cleared the validity floor in all three cases —
so any difference had to come from the variable under test. Visual inspection of the
rendered artifacts afterward showed that in one case the control had two genuine defects:
small-multiple panels with independently auto-scaled y-axes, drawing a ~2.5×10⁵ series as
tall as the ~10⁶ series beside it, and a four-series plot indexed onto a log axis spanning
six orders of magnitude where no individual series could be traced.

The floor-pass claim was therefore false for that case, and the win there partly measured
control brokenness rather than the variable under test. The response is worth copying: the
original claim was **left standing in the document with a correction block attached
directly beneath it**, rather than edited away — so a later reader sees both what was
claimed and why it was wrong. The conclusion narrowed to the two clean cases as
load-bearing, and both defects became explicit checks so the floor would catch them
mechanically next time.

Read, in order (paths are under this repository's `visualize/` directory):
- `visualize/evaluation/runs/2026-09-02-triptych/PLAN.md` — the pre-registered design
- `visualize/evaluation/runs/2026-09-02-triptych/INSPECTION.md` — what inspection found
- `visualize/evaluation/runs/2026-09-02-triptych/ASSESSMENT.md` — the retraction in place
- `visualize/evaluation/runs/2026-09-02-triptych/RESULTS_BALANCED.md` — the confound re-run

For the mechanics of blinding and balanced assignment as code, see `blind.py` and
`blind_balanced.py` in that directory, with the keys kept separately in `KEY.md` /
`KEY_BALANCED.md`. For a larger run with an independent judge and a decode-after-scoring
split, see `visualize/evaluation/runs/2026-09-01-bakeoff/harness/PROTOCOL.md`
alongside `judge/BLIND_VERDICT.md` and `judge/REVEAL.md`.

## Boundaries with neighbouring skills

- **`falsifiable-claims`** — sets the refutation bar beforehand and words the result
  afterward. This skill covers the middle: constructing and running the comparison.
- **`validity-floors`** — defines what a validity floor *is* and how gating differs from
  ranking. Rule 2 depends on that distinction but does not teach it.
- **`evaluation-independence`** — whether the material you built with and the material
  you judge against are properly separated. A blind protocol on contaminated material is
  still circular.
- **`defeat-recitation`** — whether the judge might be reciting memorised material rather
  than reading what you supplied. Arm-identity blinding and recitation-defense are separate
  leaks; a judge can be perfectly blind to which arm it is scoring and still be answering from
  training data instead of the evidence in front of it.
- **`superpowers:verification-before-completion`** — asks whether your work is actually
  done and passing. This skill asks whether a comparative claim is warranted. Different
  questions.

## Provenance of this skill

These practices come from one project's evaluation work — a 6-case ablation, a 36-case
blind bake-off, and a 3-case portfolio comparison with a balanced re-run, all in a single
domain. They are engineering practice that held up under that project's own scrutiny, not
established empirical findings. The confound and defect-asymmetry lessons in particular
were learned by getting them wrong first.
