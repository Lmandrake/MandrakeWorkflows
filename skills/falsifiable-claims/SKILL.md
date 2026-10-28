---
name: falsifiable-claims
description: >
  Bracket a comparative or causal claim so the words you publish match the evidence you
  actually have — write the refutation condition and the pass bar before you run anything,
  then state the n and word the result once the evidence is in. Use this whenever you are
  about to say one thing beats, causes, or improves another and want the claim to survive
  scrutiny: pre-registering what outcome would sink a hypothesis, setting a threshold before
  judging, deciding how strongly to phrase a finding at small n, retracting a claim that
  turned out wrong, or narrowing a claim to the cases that actually hold. Also fires when a
  result reads cleaner than its sample can support, when you catch yourself about to move a
  bar after seeing outcomes, or when you are tempted to fix sloppy wording quietly in a
  summary. Not for building or running the comparison itself (use blind-evaluation) and not
  for checking that your own work is finished and passing (use verification-before-completion).
---

# Falsifiable Claims

A claim you cannot lose is a claim you cannot test. If no outcome would have made you abandon
the hypothesis, then running the experiment only illustrated a belief you already held — you
learned nothing, but you now feel entitled to assert it. The protocol below exists because
that failure is invisible in the write-up: the sentence "our approach wins" reads identically
whether it rests on a pre-registered bar cleared at honest n or on a bar quietly slid to
wherever the results landed.

The expensive failures here are rarely a bad number. They are a true number stated as more
than it is: a small-n consistency reported as a general effect, an aggregate kept intact after
some of its cases proved confounded, a wrong claim edited away so the record no longer shows it
was ever believed.

## When this fires

The moment before you write down a comparative or causal claim — *A beats B*, *X caused Y*,
*the change helped* — and the moment before you run the thing that will let you write it. It is
the bookend around `blind-evaluation`: set the bar *before* that protocol runs, word the result
*after* it returns.

It also fires **backwards**: when a finished claim is handed to you and you are asked whether it
holds up, reconstruct the bar that was (or was not) set in advance and report what the sample
can actually support.

## The protocol

**1. Pre-register the refutation condition before you run anything.**
Write the outcome that would make you abandon the claim — concretely, in the plan file, before
any data exists. The triptych run did this: `PLAN.md` names its killers ("Judge prefers the
control, or is indifferent") under a heading "What would falsify the claim," and states the run
"is designed so that outcome is *possible* — the control is competent, not a strawman."

*Why:* a hypothesis with no refutation condition cannot be tested, only illustrated. If you
cannot say in advance what result would sink the claim, you are not measuring it — you are
arranging a demonstration and calling it an experiment.

**2. State the pass bar in advance and do not move it.**
Fix the numeric threshold before judging and leave it fixed. The triptych bar — refutation
requires "a control win *or* tie on **≥2 of 3** cases" — was written in `PLAN.md` and then
checked, unchanged, in `RESULTS_BALANCED.md` ("Observed: 1 tie, 0 control wins. **Not
refuted**"). `BENCHMARK_PLAN.md` states the same discipline at the suite level: cases and
expected verdicts are frozen so "v0.2+ edits are judged against evidence rather than taste."

*Why:* moving a bar after seeing results converts an experiment into a demonstration. The bar
is the only thing that makes a pass mean something; a bar you adjust to fit the outcome certifies
nothing but your preference.

**3. Always state the n alongside the result.**
Never publish "principled 2 / tie 1 / control 0" without "n=3" in the same breath. Attach the
sample size to the tally every time the tally appears, in the summary as well as the body.

*Why:* a bare tally invites the reader to assume a general effect. "2 / 1 / 0" reads like a law;
"2 / 1 / 0 on n=3 cases" reads like what it is. The reader cannot calibrate a result whose
denominator you withheld, and the omission always flatters the claim.

Even the exemplar `RESULTS_BALANCED.md` lapses here: its headline line "**Preference:
principled 2, tie 1, control 0**" carries no n (the n=3 appears only paragraphs later). Copy
the rule this section states, not that headline — the lapse is the failure mode, caught in the
wild in the very file that otherwise models the discipline.

**4. Prefer "corroborated" to "proven" at small n.**
When a handful of cases agree, say the claim is *corroborated, not proven* and name the honest
next step. `RESULTS_BALANCED.md` does exactly this — "Combined n is still small ... treat as
**corroborated, not proven**. A wider case set is the honest next step if a stronger claim is
ever needed."

*Why:* consistency across three cases is encouraging and is not evidence of generality. "Proven"
is a promise about cases you have not seen; at small n you cannot keep it, and a reader who
acts on the stronger word inherits a risk you never measured.

**5. Retract in place — never edit a wrong claim away.**
When a claim turns out false, leave the original wording standing and attach a correction
directly beneath it. `ASSESSMENT.md` keeps its "**Floor: PASS for both arms in all three
cases**" line and hangs a "**CORRECTION ... The claim above is wrong for case B**" block under
it, rather than deleting the sentence.

*Why:* editing the claim away destroys the record of what was believed and why — the most
useful thing the document holds for a later reader is the shape of the mistake. An in-place
retraction lets the next person see both the error and its cause; a silent edit teaches nothing
and quietly pretends the belief never happened.

**6. Narrow to the load-bearing evidence and name it.**
When some cases prove confounded, restate the claim over the clean ones and say which those
are, rather than keeping the original aggregate. `INSPECTION.md` does this: after case B's
control is found defective, "Cases A and C are the load-bearing evidence ... The aggregate
(principled 2 / tie 1 / control 0) stands, but on 2 clean cases."

*Why:* a confounded case does not just weaken the aggregate, it changes what the aggregate
*means*. Restating over the clean cases keeps the claim true and tells the reader precisely
what it now rests on. Quietly retaining the original tally keeps a number that no longer
measures the thing you named.

## Failure modes and confounds

**The moving bar.** The commonest way a claim goes soft is a threshold adjusted after the fact —
"well, a *near*-tie still counts as a win." Writing the bar in the plan file, dated, is the only
defense; memory reliably relocates the bar to wherever the result landed.

**The bare tally.** A result quoted without its n travels — into a slide, an abstract, a Slack
message — and each hop strips more context until "2 / 1 / 0" is read as a general finding. State
the n *inside* the sentence that states the result, so the two cannot be separated in transit.

**The surviving aggregate.** When one case is thrown out for confounding, the tempting move is to
keep the headline number and footnote the exception. The number then overstates the clean
evidence. Narrow the headline itself.

**The retroactive claim.** "We always expected X" written after seeing X is unfalsifiable by
construction. If the expectation is not in a file that predates the data, it is not a prediction.

## Rationalizations that mean stop

| Thought | What is actually true |
|---|---|
| "The trend is obvious, I don't need to state a bar" | If it is obvious, the bar costs nothing and buys you a claim you can defend. An unstated bar is a bar you will move. |
| "n is small but they all agree" | Consistency is not generality. Report it as corroborated, state the n, and name the wider set that would prove it. |
| "I'll fix the wording in the summary later" | The summary is the artifact that outlives the caveat. Word it right now, or the loose version is the one that travels. |
| "The result is right even if the design was sloppy" | A right answer from a design that could not have shown you wrong is not evidence — it is a coincidence you cannot distinguish from a finding. |
| "Nobody will read the caveat anyway" | Then the caveat is doing its job wrong: fold it into the claim itself, don't drop it. The record is written for the reader who does read it. |
| "I'll just delete the claim that turned out wrong" | Deleting it destroys the most instructive part of the record. Retract in place so the mistake and its cause both survive. |
| "One bad case doesn't change the story" | It changes what the aggregate measures. Narrow the claim to the clean cases and say which they are. |

## Worked example: a bar held and a claim retracted

This repository's `visualize/` directory contains a real instance of the whole arc — bar set in advance, cleared without
moving it, and a false sub-claim retracted in place and narrowed. Read, in order:

- `visualize/evaluation/BENCHMARK_PLAN.md` — success criteria stated ahead of the
  work: cases and expected verdicts frozen so edits are "judged against evidence rather than taste."
- `visualize/evaluation/runs/2026-09-02-triptych/PLAN.md` — the pre-registered
  design and its refutation condition ("What would falsify the claim"), with a control built so
  the claim *could* lose.
- `visualize/evaluation/runs/2026-09-02-triptych/RESULTS_BALANCED.md` — the bar
  checked unchanged (≥2 of 3), the halt not triggered, and the result worded "corroborated, not
  proven" with the n stated.
- `visualize/evaluation/runs/2026-09-02-triptych/ASSESSMENT.md` — a false
  floor-PASS claim left standing with a `CORRECTION` block attached beneath it, not edited away.
- `visualize/evaluation/runs/2026-09-02-triptych/INSPECTION.md` — the narrowing to
  "Cases A and C are the load-bearing evidence," aggregate restated over the clean cases.

The point of reading these rather than paraphrasing: the retraction is worth copying exactly.
The wrong sentence stays visible; the correction sits under it; the conclusion narrows to the
cases that survived. A later reader sees what was believed, why it was wrong, and what still holds.

## Boundaries with neighbouring skills

- **`blind-evaluation`** — constructs and runs the comparison: blinding, balanced position
  assignment, an honest control, decode-after-scoring. This skill brackets that one: it sets the
  refutation bar *before* the protocol runs and words the result *after* it returns. Different
  moments in the same investigation.
- **`superpowers:verification-before-completion`** — asks whether your work is finished and
  passing. This asks whether a comparative or causal *claim* is warranted by the evidence. A task
  can be complete and its accompanying claim still overstated; these are different questions.
- **`validity-floors`** — defines what a validity floor is and how gating differs from ranking.
  Rule 5's floor-PASS retraction is an instance of a floor claim going wrong, but this skill words
  the retraction; it does not teach the floor.
- **`option-portfolio`** — governs whether a set of options is worth comparing at all. This skill
  starts once you have a comparison to make a claim about.

## Provenance of this skill

These practices come from one project's evaluation work — chiefly a single three-case portfolio
comparison (n=3, position-balanced across a re-run) reported as *corroborated, not proven*, in
which a false floor-PASS claim was retracted in place and the conclusion narrowed to two clean
cases. That is engineering practice that held up under one project's own scrutiny, in one domain,
not an established empirical finding. The retract-in-place and narrow-to-clean-cases lessons in
particular were learned by getting the original claim wrong first, on the record, and having to
correct it where it stood.
