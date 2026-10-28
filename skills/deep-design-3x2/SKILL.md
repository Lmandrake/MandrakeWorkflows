---
name: deep-design-3x2
description: A design-hardening workflow — at least three genuinely different solutions, two independent passes (Opus designs, ChatGPT answers blind then critiques), a re-measure of the claims the pick rests on, one merge, decisions back to the user. Use when the user says "Deep-Design-3x2", "deep design", "do a 3x2 on this", or the old name "3x3" / "Deep-Design-3x3"; when they ask to "harden this design", "get a second opinion on this design" or "get multiple opinions"; or when a design or architecture decision with real cost should get independent passes before they commit to it.
---

# Deep-Design-3x2

At least three solutions, two passes, a re-measure, one merge, decisions back to the user.

Pass 1 (Opus) keeps three real options alive and writes down every claim its pick rests on.
Pass 2 (ChatGPT) answers the problem blind before it sees pass 1, so it is an independent sample,
not a critique of a framing it inherited; then it critiques. The starred claims are re-measured by
a different method. The merge is yours, not another agent's: you hold the conversation with the user
and know their rulings.

This was Deep-Design-3x3 until 2026-10-18 (a second, fresh Opus pass sat between these two). It
was cut to two passes on measured evidence, below. "3x3" still means this skill.

## Why it is shaped this way

Evidence: `providers/chatgpt/research/multi-model-eval/` in the Dispatch repository (literature, case mining, two code-review
replays, a design judgment pilot; summary in `CONCLUSIONS.md` there).

- **A third pass buys little.** Replaying 42 real escaped bugs: one Opus review caught 0.42; any
  second pass raised it to 0.51–0.55; three Opus reviews unioned reached 0.54, about +0.03 over the
  best two-pass shapes. Where one review was already near ceiling (a 97% pilot), no extra pass
  helped. The literature agrees: gains saturate after the first one or two independent samples.
- **ChatGPT is the second pass because it costs no Claude tokens and raises fewer false alarms.**
  On recall it tied a second blind Opus (+0.03, CI spans 0): the providers mostly catch and miss
  the same bugs. But a blind second Opus added ~0.9 judged false positives a run, GPT ~0.1.
- **On design, the second-provider question is closed and weak.** In a blind pairwise pilot of 7
  design questions the user preferred the Opus answer on all 6 they decided, but called them "all very
  close", and answer position was confounded. Nothing says GPT out-designs Opus; nothing says a
  second Opus beats GPT as a reviewer. GPT stays because it is cheap and independent. Do not ask
  the user to judge answers to settle this further (their ruling, 2026-10-18).
- **Checking beats arguing.** In the one real three-pass run, the decisive catch was a re-measured
  token count, off by 1.85x, not an opinion. Critique grounded in something external helps; a model
  re-reading reasoning often makes it worse. That is why the re-measure is its own step.
- **Independence before exposure.** Seeing an earlier answer shrinks diversity and anchors the
  reviewer; telling a model whose answer it is shifts its judgment. So the reviewer answers blind
  first, and is never told which model wrote what.
- **One critique, no debate rounds.** Rebuttal rounds add tokens and little else; settle a
  disagreement by measuring, not by another exchange.
- **Reviewer findings are leads, not facts.** A finding counts once something other than the
  reviewer's say-so confirms it. Union the findings, never majority-vote them.

## The procedure

Pick one working directory for the run's artifacts, in the project the question belongs to, e.g.
`<repo>/docs/design/<YYYY-MM-DD>-<slug>/`. Write each pass to its own file there and commit as
you go, so a stalled agent loses nothing.

Respect the project's privacy boundary in every pass: if the repo pushes to a public host and the
material involves private mail, colleagues' names or program details, keep real text out of the
files and the reports. Use fake examples, or put the real-text appendix in that project's private
store.

When you hand a reviewer an earlier pass's file, present it as "a design" or "a review", never as
Opus's, Claude's or GPT's: hiding authorship removes a known bias for free.

### Pass 1: deep design (Opus)

Spawn an agent with `model: opus`. Give it the problem in the user's own words, the relevant repo
paths and earlier rulings, and ask for `01-design.md` containing:

1. The problem restated, constraints, what success looks like and how it would be measured.
2. A survey of what already exists, so nothing gets rebuilt: the repo's own code, existing
   skills, and open-source tools that could be used instead of written.
3. **At least three genuinely different solutions** (different approaches, not the same one at
   three sizes). For each: how it works, cost (build effort, tokens, latency, ongoing upkeep),
   risks and failure modes, what it buys, what it costs, and **the conditions under which it
   dominates**.
4. A recommendation, defended, with what would change its mind.
5. Open decisions for the user.
6. **A claims table**: every number and every factual assertion the recommendation rests on
   ("X already exists", "Y costs ~N tokens a day", "nobody uses Z"), each marked `measured`
   (with how), `estimated`, `assumed` or `unmeasured`, and starred if the recommendation would
   change were it wrong. A non-numeric design still has claims: facts about what exists, what
   users do, what a tool can and cannot do. This table is what the re-measure checks.

### Pass 2: external review (ChatGPT), blind first, then critique

Load the `chatgpt-consult` skill and follow it. Two consults, in this order:

1. **Blind.** Send only the problem statement and the context a reader needs, not `01-design.md`.
   Ask for its own two or three options, with trade-offs, and its pick. Save the answer as
   `02a-gpt-blind.md` and commit it before step 2.
2. **Critique.** Only then send `01-design.md` (authorship hidden, as above). Ask GPT to:
   - critique each solution, including mis-stated trade-offs and missing costs, and improve each
     where it can;
   - name options it reached blind that the design missed, and directions neither considered,
     including a fourth solution if one genuinely beats the three;
   - check the starred claims it can check from the text (arithmetic, logic, published facts,
     prices);
   - give its pick, and whether it agrees with the recommendation, and why.

   Save the answer and both consult ids as `02-gpt.md`.

One critique, no rebuttal round.

### Re-measure the starred claims (you, or a fresh Sonnet agent)

Write `02m-remeasure.md`. For every starred claim, measure it by a **different method or source**
than pass 1 used (recount from raw data, run the code, read the file, price it another way), and
measure for the first time any starred claim pass 1 left `assumed` or `unmeasured`. Add any claim
GPT disputed. Report a table: claim, pass 1's value, the new value and method, and whether it
moved. This needs repo access and tools, which the consult does not have, so it is done here
rather than inside pass 2. A fresh Sonnet agent is enough for counting and reading; give it the
claims table, not the recommendation.

### Optional: a second Opus pass

Add a fresh `model: opus` agent only when the decision is high-stakes and hard to reverse, or when
`chatgpt-consult` is unavailable. It works blind first exactly like pass 2 (`02o-opus-blind.md`,
committed, then `02o-opus-review.md`), and never sees pass 1's transcript. If GPT is unavailable,
an anchored Sonnet critic of `01-design.md` is a cheaper stand-in: in the code replay it found as
many extra bugs as a second Opus (+0.11 vs +0.09), with about as many false alarms. Say in the
merge which you ran and why.

### Merge (you)

Write `03-merged.md` from `01-design.md`, `02a-gpt-blind.md`, `02-gpt.md`, `02m-remeasure.md`
(and the optional pass's files, if run):

- the final set of options (at least three, at most four), each with the strongest version of
  its case after review, and **whose idea each element came from** (pass 1, GPT blind, GPT
  critique, re-measure, optional pass, you), so provenance can be counted later;
- the claims table after the re-measure: which claims moved, by how much, and which measurement
  you trust;
- each reviewer finding with its status: confirmed (by what), refuted, or unverified; an
  unverified finding may shape a question for the user but never decides an option by itself;
- combinations or sequences of the options where they compose (users often pick a combination),
  with what each order buys;
- where the passes disagreed, stated as a disagreement rather than smoothed over;
- your recommendation;
- the decisions for the user.

Commit and push.

### Bring it back

Present the decisions with the `question-card` skill: options in plain words with trade-offs on
every one, your recommendation marked with one line of why, the real local time above each card.
Above the cards, give only what changes the answers: the solutions in a line each, the sharpest
point the review raised, and any claim that moved. Give the full path to `03-merged.md`.

When the user answers, record their answers verbatim in `03-merged.md` under a Rulings heading, note whose
option or combination they chose, and commit.

### Outcome (after it is built)

When the chosen option has been built, or abandoned, write `04-outcome.md`: what was predicted
(the claims and the expected payoff), what happened, which review findings proved right or wrong
in practice, which moved claim mattered, and any problem that surfaced later that no pass raised.
Record the GPT consults' outcomes as the `chatgpt-consult` skill describes. This is how the
workflow learns whether its passes earn their tokens; a run without an outcome teaches nothing.

## Run status, models and cost

Keep `status.md` in the run directory, one line per step, updated and committed as each ends:
`<step> | complete/incomplete | <resolved model id> | <tokens or cost> | <note>`. Resolve the model
id by reading the env var the alias goes through (`ANTHROPIC_DEFAULT_OPUS_MODEL` for `opus`,
`ANTHROPIC_DEFAULT_SONNET_MODEL` for `sonnet`); never hardcode an id, account or region. Take tokens
from the agent's usage report, and for pass 2 whatever the consults report (write `unknown` if they
report nothing). Count the tokens spent afterwards on triage and fixes too, in `04-outcome.md`: in
our logs that cost dwarfed the reviews themselves. A typical run is one Opus agent, two ChatGPT
consults and a small re-measure.

## When a pass fails

If a pass fails or times out, or `chatgpt-consult` is unavailable, do not drop it silently:

- If a pass stalls, resume that agent rather than starting over; its pushed file is the checkpoint.
- If it cannot be completed, mark it `incomplete` in `status.md` with why (error, timeout,
  consult unavailable), and leave every earlier artifact in place and committed.
- `chatgpt-consult` unavailable: run the optional Opus pass (or the Sonnet stand-in) in its place
  and say so. GPT's critique can run without its blind step, marked so. The re-measure and the
  merge run regardless. Pass 1 failing stops the run.
- Label `03-merged.md` and what you bring back **INCOMPLETE**, naming the missing step, so the
  result is never mistaken for a full 3x2.
