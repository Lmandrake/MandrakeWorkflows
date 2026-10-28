---
name: evaluation-independence
description: >
  Use when a result could be contaminated because the thing being judged had contact with its
  own answer key. Fires on: an eval or test suite that keeps passing and feels suspiciously
  circular, and you want to know if it's testing anything real; being tempted to peek at a held-out
  or test set "just to calibrate" a threshold or rubric; scoring a model's output using that
  same model's own prior generations as the answer key; having written the reference, gold, or
  expected answers yourself and now also judging against them; or assembling training/design
  data alongside eval data in the same pass with no wall between them. This governs the
  standing, project-wide separation between what builds a thing and what grades it — not a
  single judging session. Not for blinding one head-to-head comparison at judging time (use
  blind-evaluation), and not for defining what counts as admissible in the first place (use
  validity-floors).
---

# Evaluation Independence

Left alone, every builder quietly recruits the judge. You reach for the best examples you
have, use them to shape the thing, and then reach for those same examples to prove the thing
works — and it does, because you built it to. The grade is real; it just measures nothing.
This is train/test leakage, self-review, and benchmark contamination, and all three share one
shape: the knowledge that produced the artifact also scored it, so a pass only confirms the
artifact agrees with itself. The failure is invisible from inside because each step felt
reasonable. The only defense is a standing boundary — declared in writing, enforced by the
filesystem — between what may build and what may judge, held for the life of the project.

## When this fires

Any time the same project both *builds* something and *measures* whether it is good, and the
inputs to those two activities could touch. Assembling design principles and a reference set
together. Curating training data next to a benchmark. Letting your own judgment tune a rubric
that then grades outputs. Pointing a model at its own generations as ground truth. Reporting
"it matched the exemplars N/N" when you chose the exemplars. It fires *forward* while you are
still deciding what goes where, and *backward* when a result already exists and you are asked
whether the evaluation was independent of the build.

## The protocol

The steps below are written *forward*, for the builder still deciding what goes where. To audit
an existing result *backward*, read each as a question the record must answer: was the non-input
declared in writing before the build (1–2), was the grade non-circular and free of laundered
taste (2–3), was the held-out set enforced unreachable and provably unopened while building
(4–5), was divergence investigated rather than tuned away (6), and is each corpus's role labelled
on the record (7)? A "no" anywhere is where independence broke.

**1. Declare your non-inputs in writing, before you build.**
Name the material you will NOT let shape the thing you are building, and say so on disk where a
later reader will find it. In this repo that declaration is a whole file: the held-out corpus
is *"a **NON-INPUT** to principle-derivation"* and principles are *"derived only from the
published visualization literature."*

*Why:* an undeclared boundary is one you cross without noticing. Writing it down converts a
private intention into an auditable commitment, and forces you to decide the split while you
still have no stake in the outcome.

**2. Refuse circular evaluation on principle.**
If the same knowledge that built the system also judges it, a passing grade only proves the
system agrees with itself. State the firewall's own reason: *"If the exemplars that trained the
system are also the exemplars that score it, a high score proves nothing."*

*Why:* the number you most want to report — "it works" — is exactly the one circularity
fakes most convincingly. Knowing *why* circularity is empty lets you spot it in forms you did
not anticipate: a metric tuned on its own test set, a model graded by a copy of itself.

**3. Watch for preference laundered as fact.**
When your own taste becomes the training signal and then also the test, you have measured your
taste twice and called the second pass validation. Letting a personal corpus rewrite the rules
would *"quietly convert 'the author likes this' into 'this is empirically correct.'"*

*Why:* taste is legitimate as one held-out reference to converge against; it is illegitimate as
the definition of correctness. The laundering is silent — the same aesthetic on both ends
returns a confident, meaningless agreement.

**4. Enforce the boundary mechanically, not by intention.**
Make the held-out set structurally unreachable by the builder: git-ignore it, keep it
*"local-only ... and never pushed,"* put the reference behind a file the build process never
opens. Do not rely on remembering.

*Why:* discipline that depends on willpower fails precisely under deadline, when the shortcut
is most tempting and least examined. A boundary the filesystem enforces holds when your
attention does not.

**5. Never open held-out material while building.**
Not even "just to calibrate." The bake-off harness states the rule flatly — *"Never open
`held-out/`"* — and orders the work so the naive pass is written *"FIRST ... before you read
the skill stack,"* so knowledge cannot leak backward into it.

*Why:* looking converts a test set into a training set silently and irreversibly. You cannot
un-see it, and you cannot afterward prove your later choices were uninfluenced. One glance
retires the reference permanently.

**6. Treat convergence as corroboration and divergence as a flag, not a target.**
When your system and an independent reference agree, that is evidence. When they differ,
*investigate* the difference — do not tune the system until it matches. The two are meant to
*"inform each other — convergence is corroboration, divergence is a flag worth examining."*

*Why:* the moment you adjust the system to match the reference, the reference has become an
input and its independence is gone. Divergence is where you learn something; erasing it to
score higher throws away the only informative signal the held-out set can give.

**7. Say which role each body of material plays, on the record.**
Label every corpus as input, control, or held-out validation, so a later reader can audit the
separation. MandrakeVisualize labels its holdout *"a declared NON-INPUT to principles; validation set
only,"* and marks exemplars *"used ONLY at the analysis stage."*

*Why:* roles drift as a project grows and a set quietly gets reused for a second purpose.
Written role labels are what let anyone — including future you — check that the wall still
stands rather than take it on faith.

## Failure modes

**Silent role creep.** A set declared held-out gets consulted "once" for a design decision and
is thereafter an input, though nothing in writing changed. Prevented by rule 1, caught by rule 7.

**Calibration leakage.** Peeking at the test set to "understand the task" — rule 5. The set is
spent the instant it is read.

**Self-grading models.** A model (or a copy of it, or the same rubric that shaped it) scores
its own output and unsurprisingly approves. This is rule 2 wearing a machine-learning costume.

**Convergence-chasing.** Tuning the system toward the reference until they agree, then citing
the agreement as validation — rule 6. You built the match; it proves nothing.

**Remote exposure.** A held-out or sensitive set that is merely *intended* to be private leaks
because nothing enforced it. Rule 4: git-ignore and never push, verified, not remembered.

## Independence has axes, and they are not interchangeable

A reference set is not simply "independent" or not. Ask which axis it is independent *on*
before you credit it:

- **Mechanism-independent.** A different extraction path or tool reading the *same* source
  document. This can catch your own parser losing or inventing an item, because a second
  mechanism run over identical content will disagree with a bug in the first. It structurally
  **cannot** catch the source itself being internally inconsistent — both mechanisms are
  reading the same publisher's same words, so if the publisher contradicts itself, both
  mechanisms reproduce the contradiction identically and agreement looks clean.
- **Content-independent.** A genuinely different document, or a different part of the source
  that was never used to build the extraction, asserting the same fact. This is the only axis
  that can catch the source contradicting itself, because it is not reading the same words.
- **Publisher-independent.** A different issuing authority asserting the same fact through
  its own separate publication. Strongest for catching a single publisher's internal error,
  weakest for volume — one publisher's five formats are not five independent checks.

*Why this matters:* a mechanism-only check standing in for a content-independent one reports
false confidence about exactly the failure it cannot see. Label which axis a given reference
is independent on before you cite it as validation, and do not let a pile of mechanism-only
checks substitute for the one content-independent check that would actually test the source.

## Repeats are not a measurement, for a deterministic component

Running a non-stochastic layer three times and reporting "3/3 identical" measures determinism,
not correctness — a deterministic function will of course return the same wrong answer every
time you call it with the same input. One such layer was run three times and returned
byte-identical output on all three runs, while making thousands of decisions against only two
known-correct answers; the repeats said nothing about the rest.

*Why:* characterizing a deterministic component needs many **labelled** items — cases with a
known-correct answer to compare against — plus deliberate input perturbation to probe its edge
behavior, not a higher run count against unchanged input. Re-running it is asking the same
question of the same answer key and getting the same reply; it is not a second opinion.

## Rationalizations that mean stop

| Thought | What is actually true |
|---|---|
| "I'll just peek at the holdout to calibrate" | The peek spends the set. It is a training input the moment you read it, and you cannot prove otherwise afterward. |
| "My own judgment is the best signal I have" | Then hold it out as a reference to converge against. As both the signal and the test it measures your taste twice and validates nothing. |
| "The model agreeing with itself is still a signal" | It is a signal that the system is internally consistent, not that it is correct. Circular pass, empty grade. |
| "I'll remember not to use it as an input" | Discipline that depends on memory fails under deadline. Git-ignore it so the builder structurally cannot reach it. |
| "The human and the system disagree, so let me tweak until they match" | Tuning to match makes the reference an input and destroys its independence. Investigate the divergence; do not erase it. |
| "It's obviously private, I don't need to enforce that" | Intended-private and enforced-private differ exactly when it costs you. Ignore-and-verify, not assume. |
| "I ran it three times and got the same answer, so it's robust" | A deterministic component gives the same answer every time by construction. That measures nothing; you need labelled cases and input perturbation, not repeat counts. |
| "A second oracle agrees, so the source checks out" | Only if that oracle is independent on the CONTENT axis. Two mechanisms reading the same words will agree on the same publisher error every time. |

## Worked example: a project-long build/judge firewall

MandrakeVisualize is one instance of the general rule — a literature-grounded system whose
principles must never be shaped by the very exemplars used to validate them. Read it as an
example, not as the subject; the same structure applies to any train/test split or benchmark.

The firewall is declared as its own tracked file, then restated at the top of the project
README, then made concrete in two evaluation harnesses that must not cross it, then recorded in
the living status. Read, in order (paths are under this repository's `visualize/` directory):

- `visualize/HOLDOUT.md` — the firewall itself: what is held out, that it is a
  NON-INPUT to principle-derivation, and the two failure modes (circular evaluation, encoding
  taste as fact) it exists to prevent.
- `visualize/README.md` — the same separation stated at the top level: principles
  from published literature, personal corpus *"usable only as a held-out validation set."*
- `visualize/evaluation/runs/2026-08-28-ablation/held-out/EXEMPLARS.md` — the
  reference exemplars marked *"DO NOT feed to plotters or the blind judge,"* used only at the
  analysis stage after everyone else has finished.
- `visualize/evaluation/runs/2026-09-01-bakeoff/harness/PROTOCOL.md` — the blind
  protocol enforcing it in code: the A/B mapping is held from the judges, the naive pass is
  written before the skill stack is read, and the held-out set is never opened.
- `visualize/STATUS.md` — the standing record: the holdout is *"a declared
  NON-INPUT to principles; validation set only,"* verified git-ignored.

The independence is not one clever step; it is a wall declared once and re-stated at every
layer, so no single lapse can quietly demolish it.

## Boundaries with neighbouring skills

- **`blind-evaluation`** — blinds a *single comparison* at judging time: position balance, a
  hidden key, decode-after-scoring. This skill governs the *standing* separation of what may
  build from what may judge across a whole project. A perfectly blind protocol run on
  contaminated material is still circular.
- **`validity-floors`** — defines what counts as *admissible* — the floor an output must clear.
  This skill defines *independence* — that the judge did not learn from the builder's inputs.
  Different axes: one is about quality thresholds, the other about who is allowed to grade.
- **`claim-provenance`** — if you cite a success rate against a reference, provenance discipline
  records where that reference came from; independence is what makes the rate mean anything.

## Provenance of this skill

This comes from one project's evaluation discipline — a literature-grounded viz stack that held
its personal-deck corpus out of principle-derivation and used it only to validate. It is
engineering practice that survived that project's own scrutiny, not an established empirical
finding. The rules generalize to any train/test split, self-review, or benchmark, but they were
learned in a single domain, at small n, by taking the firewall seriously rather than by proving
it optimal.
