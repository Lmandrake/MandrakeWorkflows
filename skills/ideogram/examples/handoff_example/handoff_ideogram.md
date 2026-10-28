> **Illustrative example** — authored to demonstrate the *software / capability handoff* shape of an ideogram. Scenario is realistic but not a live project deliverable; specifics marked [EXAMPLE].

**Blocks used:** Header · § THE ASK · § HOW SUCCESS IS MEASURED · § RUN ARCHITECTURE · § REPRODUCTION MECHANISM · § DELIVERED INFRASTRUCTURE · § HOW I'LL HELP · § ADDITIONAL CONTEXT · Appendix A (cover note) · Appendix C (self-check)
**Deliberately omitted:** § WHY THIS EXISTS (self-evident — I have to run your tool); narrative-spine (no deck to feed); premise-to-challenge (not a persuasion doc); Appendix B response-skeletons (single recipient); known-gap/next-step (belongs to a status ask, not a handoff)

---

# GraderKit Handoff — Make It Run on My Machine [EXAMPLE]

**Author:** the receiving engineer [EXAMPLE] (picking up the eval harness for the next study)
**Recipient:** the building engineer [EXAMPLE] — original author of `GraderKit` [EXAMPLE], the LLM-solver evaluation harness
**Date:** 2026-08-26  ·  **Version:** 0.1
**Scope cutoff:** everything in the current `GraderKit/` [EXAMPLE] working tree as of handoff; if you have local, uncommitted pieces, those count too — name them.

> **This is an ideogram.** It's a request you can talk to. Read **§ THE ASK** and
> **§ HOW SUCCESS IS MEASURED** to know what "handed off" means here, and **§ HOW I'LL
> HELP** for how we'll work together. You can (a) run it — "Claude, satisfy this from the
> files in the `GraderKit` [EXAMPLE] directory"; (b) respond to it yourself; or (c) ask it
> *"Is this sufficient to answer the ask?"* for a neutral, criterion-by-criterion read.
> **It guides; it does not decide what goes in your handoff. That's yours.** Send more than
> you think I need — I'd rather prune than be stuck on a missing config file.

---

## § THE ASK  *(read in under a minute)*

You built `GraderKit` [EXAMPLE] and it works on your machine. I'm taking it over for the
next study and I need it to work on **mine** — not a description of it, the *running thing*.
Hand me three things, in markdown plus the actual files:

1. a **reproduction mechanism** — a documented, finite sequence of steps that stands the
   tool up on a fresh machine via Claude Code and ends in a run I can verify;
2. the **run architecture** — the inventory of what the tool actually is: entrypoints,
   config, the control flow of a single grading run, and every external dependency;
3. the **grown infrastructure** — the skills, prompt templates, harness code, and any
   config/secrets scaffolding that grew up around the tool and that it silently needs.

I don't need polish. I need to type the documented commands and watch it produce the same
kind of output you get. Send the whole set; I'd rather prune than discover a missing file at
run time.

---

## § HOW SUCCESS IS MEASURED  *(the bar — this is what the self-check grades against)*

A handoff is sufficient when:

1. **It runs on a clean machine in a documented, finite number of steps.** Starting from a
   fresh checkout with no prior state, I can follow the reproduction markdown top-to-bottom
   and reach a completed grading run. Target: **≤ [AUTHOR TO CONFIRM] steps**, no
   undocumented manual fixes.
2. **The first run is verifiable.** The doc names an **expected output** (a metric, a file,
   a console signature) and how I know the run succeeded vs. silently no-op'd. On the sample
   input, the grader should report roughly **0.9x [EXAMPLE]** so I can confirm parity.
3. **The run architecture is fully enumerated, by path.** Every entrypoint (e.g. the
   `solver_harness.py` [EXAMPLE] CLI), every config file, and every external dependency
   (model endpoint, API key, data mount) is named — nothing "you just have to know."
4. **Nothing the tool needs is missing from the delivery.** All grown infrastructure ships:
   the harness code, the prompt/skill assets it loads, and a template for any secrets/config
   (with real secrets redacted). If a piece isn't in the shared tree, it's called out
   explicitly as "obtain separately from X."
5. **Assumptions are stated, not implied.** Python version, OS, model access, rate limits,
   and any machine-specific paths are written down rather than baked into your shell history.
6. **Nothing fabricated.** No invented version number, path, or benchmark result — every
   claim points to a real file or is flagged as assumption.

---

## § RUN ARCHITECTURE  *(the inventory — name the parts, by path)*

Give me the anatomy of a single grading run, concretely:

- **Entrypoints.** What do I actually invoke? (e.g. `solver_harness.py` [EXAMPLE] as the CLI;
  `grade_batch.py` [EXAMPLE] for the sweep.) Include the exact command line with flags.
- **Config.** Every file that shapes a run — the run config (e.g. `graderkit.toml`
  [EXAMPLE]), the model/endpoint config, and any environment variables the code reads.
- **Control flow of one run.** In a few lines: input → solver call → oracle/grader call →
  score → artifact. Where does each step write? What's cached?
- **External dependencies.** Model endpoint(s) and required access; any data mount or fixture
  directory; Python/runtime version; third-party packages (a lockfile is ideal).
- **State & outputs.** Where results land (e.g. `runs/<timestamp>/` [EXAMPLE]), what's
  overwritten, and what I should `.gitignore` vs. keep.

---

## § REPRODUCTION MECHANISM  *(rebuild it on my machine — the finite recipe)*

A markdown I can hand to Claude Code that walks a fresh machine to a verified run:

- **Prerequisites** — runtime version, model access/keys, OS assumptions, disk/network needs.
- **Files to obtain** — everything not already in the shared tree, each with where to get it.
- **Step-by-step** — checkout/place → configure (fill the config template) → install →
  run the **sample/baseline** → read the expected output → run the real target.
- **"How I know it worked"** — the concrete success signature (see success criterion 2), plus
  the two or three most common failure modes and their fixes.
- **Finite and documented** — no "and then just tweak until it works." If a step is fiddly,
  say so and give the known-good values.

---

## § DELIVERED INFRASTRUCTURE  *(ship the parts, not descriptions of them)*

Please deliver the **actual** artifacts, not a write-up about them:

- the **harness code** (`solver_harness.py` [EXAMPLE], `grade_batch.py` [EXAMPLE], helpers);
- the **prompt / skill assets** the tool loads at run time (templates, system prompts, any
  bundled skill directory);
- a **config template** for secrets and machine-specific settings, with real secrets redacted
  and a comment on where each value comes from;
- a **lockfile or pinned dependency list** so my environment matches yours;
- if any piece can't be shared (proprietary data, a private endpoint), say so explicitly and
  name the smallest stand-in that still lets me verify a run.

---

## § HOW I'LL HELP  *(mechanisms & policies)*

**My persona.** When you run me conversationally, I open like this:

> "Hello — I'm the **GraderKit handoff** [EXAMPLE] ideogram, here to help you hand this off
> cleanly so it runs on the receiving engineer's machine and you get credit for a tool that
> travels well. May I look through the `GraderKit` [EXAMPLE] directory to draft the
> reproduction doc and inventory, using subagents? In the meantime, tell me the parts you
> know are fiddly or machine-specific — or just point me at the entrypoint and let me trace
> it. I won't search anywhere you haven't named, so please be specific."

**How to engage.** Three modes: hand me to Claude to trace the code and draft the
reproduction markdown; write the handoff yourself; or draft it and ask me "is this
sufficient?" I read only where you point me — the `GraderKit` [EXAMPLE] tree is the natural
start, but you name it.

**Do's & Don'ts.**
*Do:* send the whole running set, not one file; attach context to each artifact (what it is,
why the tool needs it); pair any "this part is flaky on some machines" with the known-good
workaround; over-expose rather than under-expose.
*Don't:* hand me a prose description in place of the code; give me a config with values
elided but not marked; assume I share your shell environment; skip the sample run because
"it obviously works."

**Self-check.** Ask me *"Is this sufficient to answer the ask?"* and I'll grade the handoff
against each success criterion — Met / Partially met / Not yet / N/A — with a one-line reason
each, and name where any missing piece most likely lives. You decide what to include.

---

## § ADDITIONAL CONTEXT  *(informs, but is not itself a deliverable — add freely)*

- **Why this is a handoff and not a status ask.** I'm not asking how the project is going or
  what to tell a stakeholder — I'm asking for a *capability* to change hands. That's why this
  ideogram skips § WHY THIS EXISTS (the need is self-evident: I have to run your tool) and the
  decision-translation / known-gap machinery a report-out would carry.
- **What I already have** (so you don't re-send it — point me at it instead): whatever is in
  the shared `GraderKit/` [EXAMPLE] tree. What I most expect to be **missing**: the secrets/
  config template, the pinned dependency list, and any prompt assets that live outside the
  repo.
- **Distinguish evidence from assumption.** If you're *sure* a step works on a clean machine,
  say so; if you're *guessing* it'll port, flag it — I'd rather debug a flagged guess than a
  confident wrong step.

---

## Appendix A — Cover note (ready to forward)

> Hi — I'm picking up `GraderKit` [EXAMPLE] for the next study and I'd love a clean handoff so
> it runs on my machine, not just yours. There's an ideogram at
> `examples/handoff_example/handoff_ideogram.md` — read **§ THE ASK** (it's short) and the
> Do's/Don'ts. In brief: a reproduction markdown that gets a fresh machine to a verified run,
> the run-architecture inventory (entrypoints, config, dependencies, by path), and the actual
> grown infrastructure (harness code, prompt assets, a redacted config template, a lockfile).
> Send more than you think I need. If you want, point Claude at the `GraderKit` [EXAMPLE] tree
> and let it draft the reproduction doc, then ask it "is this sufficient?" — it'll grade
> against exactly what I need to stand it up. Thank you.

## Appendix C — Runnable self-check block

Paste this to Claude alongside a draft handoff to get a neutral sufficiency read:

```
You are the GraderKit handoff [EXAMPLE] ideogram acting as a neutral reviewer.
Read: (1) this ideogram's "§ HOW SUCCESS IS MEASURED" section, and (2) the draft handoff I provide
(reproduction markdown + run-architecture inventory + delivered files).
Produce a table:
  Criterion | Verdict (Met / Partially met / Not yet / N/A) | One-line reason | Where the missing piece likely lives
Pay special attention to: does the reproduction recipe actually run on a CLEAN machine in a
finite, documented number of steps, and is the expected-output signature stated?
Rules: grade only against the stated criteria; never inflate, never gatekeep; state only what
the evidence supports; for anything short, name the specific file or step to fix next.
Close with: "You decide what to include — here is where the handoff stands against your own bar."
Do not edit the delivery; only assess it.
```

---
*Illustrative example authored with the `ideogram` skill (`skills/ideogram` in MandrakeWorkflows). Not a live deliverable. Bump the version line on each edit.*
