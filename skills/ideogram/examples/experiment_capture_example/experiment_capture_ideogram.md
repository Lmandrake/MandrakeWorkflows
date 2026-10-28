> **Illustrative example** — authored to demonstrate the *experiment capture* shape of an ideogram. Scenario is realistic but not a live project deliverable; specifics marked [EXAMPLE].

**Blocks used:** Header · § THE ASK · § HOW SUCCESS IS MEASURED · § DEFINITION FILES & DATASETS · § CONTROLLING NOTEBOOKS & SCRIPTS · § RESULTS · § CONCLUSIONS · § WHY THIS EXISTS (brief) · § ADDITIONAL CONTEXT · Appendix B (capture skeleton) · Appendix C (self-check)
**Deliberately omitted:** § HOW I'LL HELP / persona (a record, not a live collaboration — no consent-to-search dance); Appendix A cover notes (no external recipient to forward to); narrative-spine (no deck); premise-to-challenge (this captures facts, it doesn't argue); § REPRODUCTION MECHANISM as a *separate* block (folded into the capture — reproduction here means "a third party could rebuild from what's recorded," not "stand up someone else's tool")

---

# Prompt-Ablation Experiment — Capture the Setup and the Findings [EXAMPLE]

**Author:** the study lead [EXAMPLE] (needs the run recorded before context evaporates)
**Recipient / who fills this in:** the experimenter who ran it [EXAMPLE] — possibly future-you
**Date:** 2026-08-26  ·  **Version:** 0.1
**Scope cutoff:** the specific experiment run identified as `ablation_2026-08 [EXAMPLE]` — its
definition, its inputs, its outputs, its conclusions. Not the whole research line; this one run.

> **This is an ideogram.** It's a request you can talk to — here it captures an experiment so
> a third party could rebuild it. Read **§ THE ASK** and **§ HOW SUCCESS IS MEASURED** to know
> what a complete capture is. You can run it — "Claude, fill this in from the `ablation_2026-08`
> [EXAMPLE] run directory" — or fill it in yourself, then ask *"Is this sufficient to answer the
> ask?"* for a neutral read. **It guides; it does not decide what goes in the record. That's
> yours.** Over-record rather than under-record — an un-captured detail is a run nobody can repeat.

---

## § THE ASK  *(read in under a minute)*

Record **exactly** how the `ablation_2026-08` [EXAMPLE] experiment was set up and what it found —
enough that a competent third party who never saw the run could rebuild it and reach the same
conclusions. Capture five things, in markdown plus the actual files:

1. the **definition files** that specify the experiment (what varied, what was held fixed);
2. the **datasets** — the input set and the "truth"/reference set, with **sizes**;
3. the **controlling notebooks and scripts** — by name — that actually drove each run;
4. the **results** — metrics and artifacts, not a summary of them;
5. the **conclusions** — what the run established, with each tied to a result.

This is a record, not a pitch. Precise beats polished.

---

## § HOW SUCCESS IS MEASURED  *(the bar — this is what the self-check grades against)*

A capture is sufficient when:

1. **A third party could rebuild the run from the record alone** — no tacit "you had to be
   there" step. Target: the setup is reconstructable in **≤ [AUTHOR TO CONFIRM] documented
   steps** from the named files.
2. **Every varied factor and every fixed control is written down.** The ablation is legible:
   what was removed/changed per condition, and what was held constant across all of them.
3. **Dataset sizes are stated as numbers.** Input set: **N = [AUTHOR TO CONFIRM]** items;
   "truth"/reference set: **N = [AUTHOR TO CONFIRM]** items. Any split (train/held-out) is
   named with its counts and how the split was drawn.
4. **The controlling code is named by path and version.** The notebook(s) and script(s) that
   drove the run are listed (e.g. `run_ablation.ipynb` [EXAMPLE], `score.py` [EXAMPLE]),
   including the exact config/seed used, so a re-run is not a guessing game.
5. **Results are delivered, not described.** The metric table and output artifacts ship with
   the record; a headline like "condition C dropped the score by 0.1x [EXAMPLE]" is traceable
   to the file it came from.
6. **Each conclusion is tied to a result.** No conclusion floats free of the evidence that
   supports it; where a finding is inference rather than measurement, it's flagged as such.
7. **Nothing fabricated.** No invented metric, count, seed, or filename — every number points
   to a real artifact or is marked `[AUTHOR TO CONFIRM]`.

---

## § DEFINITION FILES & DATASETS  *(what was varied, what was held, over what data)*

- **Experiment-definition files.** The file(s) that specify the conditions — e.g. a config
  such as `ablation_conditions.yaml` [EXAMPLE] enumerating each prompt-component removed, and
  the fixed scaffolding shared across conditions. Give the path and paste the relevant excerpt.
- **The ablation grid.** In a short table: condition name · what changed · what stayed fixed.
  A leave-one-out over prompt components is fine to describe as such — but list the components.
- **Input dataset.** What it is, where it lives, and its size (**N = [AUTHOR TO CONFIRM]**).
  Note any filtering applied before the run.
- **"Truth" / reference dataset.** The graded-against target, its provenance, and its size
  (**N = [AUTHOR TO CONFIRM]**). Call out the leakage question explicitly: was any part of the
  reference visible to the thing being graded? If so, say where.

---

## § CONTROLLING NOTEBOOKS & SCRIPTS  *(name the drivers, by path)*

- The **notebook(s)** that orchestrated the run — e.g. `run_ablation.ipynb` [EXAMPLE] — with a
  one-line note on what each cell block does.
- The **scripts** invoked — e.g. the scorer `score.py` [EXAMPLE], any data-prep step.
- The **exact invocation**: config file used, random seed(s), model/endpoint and version,
  and how many replicates per condition (LLM stochasticity matters — say whether results are
  single-shot or averaged over K runs, and give K).
- Where outputs were written (e.g. `results/ablation_2026-08/` [EXAMPLE]).

---

## § RESULTS  *(deliver the artifacts, not a summary)*

- The **metric table** per condition (ship the CSV/JSON, don't just quote a headline).
- The **output artifacts** — plots, per-item scores, any error logs worth keeping.
- **Variance**, where measured — spread across replicates, not just a point estimate.
- If a condition failed to run, record *that* too; a missing cell in the grid is a result.

---

## § CONCLUSIONS  *(each tied to a result)*

- What the run **established** — stated as claims, each pointing to the result that backs it
  (e.g. "removing component X cost 0.1x [EXAMPLE] on the reference set — see row X of the
  metric table").
- What it **did not** establish — the questions this run leaves open.
- **Evidence vs. inference.** Mark each conclusion: measured result, reasonable inference, or
  speculation. The study lead carries that distinction forward.

---

## § WHY THIS EXISTS  *(brief — intent & need)*

We ran `ablation_2026-08` [EXAMPLE] and the interesting part is *why* certain conditions moved
the score — but that understanding lives in the experimenter's head and in a run directory that
will be hard to read in three months. This capture exists so the run survives contact with time
and with a reviewer who wasn't there. It is a **record for reproduction and audit**, not a report
to a stakeholder — which is why this ideogram skips the persona/collaboration machinery a
report-out would carry and leans entirely on definition, data, drivers, results, and conclusions.

---

## § ADDITIONAL CONTEXT  *(informs, but is not itself a deliverable — add freely)*

- **Why this shape differs from a status ideogram.** No decision is being served up a chain
  here; the "audience" is a future reproducer. So there's no narrative-spine, no known-gap-with-
  owner, and no persona consent dance — just faithful capture.
- **Reproduction, here, means "rebuild from the record."** Unlike the *handoff* shape (which
  ships someone's running tool and a stand-it-up recipe), this capture's reproduction test is
  satisfied when the recorded definition + data + drivers are enough to rerun. That's why there
  is no separate § REPRODUCTION MECHANISM block — it's folded into the success criteria.
- **The leakage caveat is worth its own line** (see § DEFINITION FILES & DATASETS): if the
  reference the run was graded against also seeded any input, note it — an un-flagged leak turns
  an impressive result into an unmeasured one.

---

## Appendix B — Capture skeleton (rename freely; prose + files welcome)

```
# ablation_2026-08 [EXAMPLE] — Experiment Capture
## 1. Definition        (conditions file path + the ablation grid: condition | changed | fixed)
## 2. Datasets          (input: what/where/N ; truth: what/where/N ; splits ; leakage note)
## 3. Drivers           (notebook + script paths ; config ; seed(s) ; model+version ; K replicates)
## 4. Results           (metric table file ; artifacts ; variance ; failed conditions)
## 5. Conclusions       (each claim -> the result backing it ; open questions)
### Evidence tags       (measured / inference / speculation)
### Attachments         (the actual files: config, notebooks, results, plots)
```

## Appendix C — Runnable self-check block

Paste this to Claude alongside a draft capture to get a neutral sufficiency read:

```
You are the ablation_2026-08 [EXAMPLE] experiment-capture ideogram acting as a neutral reviewer.
Read: (1) this ideogram's "§ HOW SUCCESS IS MEASURED" section, and (2) the draft capture I provide.
Produce a table:
  Criterion | Verdict (Met / Partially met / Not yet / N/A) | One-line reason | Where the missing piece likely lives
Pay special attention to: could a third party who never saw this run REBUILD it from the record
alone, are both dataset sizes given as numbers, and is each conclusion tied to a named result?
Rules: grade only against the stated criteria; never inflate, never gatekeep; state only what the
evidence supports; for anything short, name the specific file or field to fill next.
Close with: "You decide what to include — here is where the capture stands against your own bar."
Do not edit the record; only assess it.
```

---
*Illustrative example authored with the `ideogram` skill (`skills/ideogram` in MandrakeWorkflows). Not a live deliverable. Bump the version line on each edit.*
