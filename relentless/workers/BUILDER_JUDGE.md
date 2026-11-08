# Relentless-style Builder/Judge: the worker definition (v0, draft)

The workers that sit in the [Relentless Pipeline](../README.md)'s places. One worker definition, two modes. **The blindness contract lives here, in the definition**, so that Build knows exactly how blind its
report must be and Judge knows exactly what to refuse. Owner, 2026-11-01: *"When the builder agent writes the report for
it's judge switch side, it will know precisely how blind it must write the report. When the judge reads it, it can judge
the report against the required blindness and reject it if it contains too much history and reasoning and justification,
and it even knows the weaknesses of its builder half to look out for."*

The full design follows GPT review. This file holds the contract that everything else must serve.

## Modes

- **Build:** works one item toward its proof of done, across as many generations as it takes.
- **Judge:** a fresh instance with no access to Build's memory. It judges the result, not the effort.

Same definition, never the same instance. Build requests Judge only when the item's own checks pass; the switch is
gated by evidence, not by Build's confidence. Judge mode also sets the exam before Build starts, as the **Setter**; the instance that later marks is the **Marker**, and the Marker writes the hold-outs at mark time, so none exists during the build. The builder never sets, holds or marks the exam.

**Done means the contract was met, not that the contract was complete.**

## The exam: set before Build, validated before it counts

Owner, 2026-11-05: *"So how are we ever going to overcome this failure of our testing apparatus, weak evidence, poorly
specified tests, etc?"* A builder that writes its own exam writes one that agrees with its own reading of the item, and
both pass together. So (RimMandrake `RELENTLESS_BUILD_EXAM_BEFORE_BUILDER`, redesign of 2026-11-06, G3/G4):

- **Setter** (Judge mode, fresh, never the builder) reads the item's words at its base sha and writes the exam: clauses,
  each with a check (an argv), a declared assertion red (exit codes, marker) and a break. Every clause is mapped from a
  sentence copied verbatim from the item; every done-when bullet is mapped. Outcomes only, never how.
- **VALIDATE** (the pipeline, no agent) runs every check in the Marker's box: a `base_red` check must fail on the base
  sha, a `patch` check must pass on the base and fail under the Setter's planted break. A red counts only as an
  assertion failure; an ImportError, a missing file or tool, a SyntaxError or a timeout is not a red. A behavioural
  clause may not be checked by existence or grep alone; `artifact` only where the item asks for one. A break that
  deletes the file the check names is refused. A refused exam gets one resumed Setter turn; a second refusal goes to an
  arbiter, which classes it setter, environment or bar: never an automatic bar.
- `exam_hash` covers the clauses, the item text and every file a check names, so changing a named test moves it.
- **Build** sees the exam and may not edit it. **Marker** checks the done-when mapping and adds its hold-outs.
- In RimMandrake it runs in **shadow** first: the exam is set and validated beside the old flow, never gating a close,
  and run at every candidate a Marker returned to count the returns it would have caught. Shadow ends at 30 items with
  a Marker verdict, a sample count, not a date.

## Memory between generations

Each Build generation starts in a fresh context, so what it needs must be on disk. Owner, 2026-11-01: *"How might we
propagate that efficiently to the next Ralph loop, keeping only to cogent bits?"* The answer is three small stores with
different lifetimes, not one memory.

### 1. Result cache (no agent involved)

Records test, hash of everything it depends on, result and runtime. Same inputs return the stored answer and nothing runs.

- Dependencies are measured from what the test actually reads, never guessed.
- Anything unobserved or external (network, live game, clock, git state, another machine) is never cached.
- A forced rerun must say why.
- A sampled audit reruns cached tests to catch false hits; a mismatch is an alarm.

This answers *"testing things I already knew again"* without relying on anyone's memory. A false "unchanged" is far worse
than a rerun, so the store fails toward running.

### 2. Tried-and-failed table

One row per approach: what was tried, the evidence, why it failed, and the condition under which it is worth retrying.
Negative results are the most expensive thing to lose. A new attempt must state how it differs from a row or what evidence overturns it, because a row proves where a reading came from, not that it is right. Rows carry evidence, not conclusions, because a misread failure otherwise
passes on with confidence.

### 3. Current state, rewritten every time

What is true now, the leading idea, the next step. A strict size cap, about 40 lines. It is replaced, never appended to,
so going over the cap forces a choice about what matters.

### Rules that keep it cogent

- **Hash-bound facts.** A claim is tied to the file contents it was true for, and expires when they change. Stale memory
  can be worse than none.
- **Rewrite at handoff.** The outgoing worker writes it while it still has the context; the supervisor refuses a handoff
  over the cap.
- **Judge never sees any of it.** Memory steers Build. It must never influence the grading.

Unsolved: deciding what is cogent is judgment, and bad memory compounds. That is why the no-agent store comes first.

## The Judge Packet: what Build must write

**Allowed:**

1. The goal and proof of done, copied unchanged from the item.
2. What exists: the diff range, the artifacts, where they are.
3. How to check: exact commands and what each should show.
4. **Unverified:** what was not or could not be checked, stated flat, with no reason given.

**Forbidden:**

- History: attempts, generations, what failed before, how long it took.
- Reasoning, justification, design defence, why a choice was right.
- Confidence or advocacy: "works well", "robust", "should pass", "I believe".
- Pre-emptive framing of a flaw, or telling Judge what to skip or what matters most.
- Anything from Build's memory stores.

Withholding is not the goal. Rule 4 exists because a report blinded of its gaps would mislead. Build must disclose every
limit as a fact; it may not explain them.

## What Judge does

1. **Check the packet first.** Any forbidden content means a rejection for contamination, before the work is read. That
   rejection says what broke the contract, and it is not a verdict on the work. A contaminated packet returns to Build
   and spends a fresh Judge instance, because the first one has read it.
2. **Plan before reading Build's route.** Write its own check plan from the tree alone, then read `how to check`.
3. **Rerun the checks itself, at the exact sha.** A claim counts only as Judge reproduces it, in an isolated checkout of
   the commit under judgment, never Build's working tree. Evidence is whatever Judge can produce there: the paths and
   commands Build cites are a starting point, not a boundary, and a gap they do not mention is still a gap.
4. **Hunt Build's known weaknesses.** Read `DEFECTS.md` and `STRENGTHS.md` for the classes of failure these workers have
   shown, and look for those on purpose.
5. **Rule:** accept, or reject with reasons Build can act on, without suggesting the fix's design. Each reason names
   its cause class, because each goes to a different fixer: **module** (the work is wrong: back to Build), **check**
   (the test or instrument is wrong, the work may be fine: to whoever owns the proof), **environment** (machine, host,
   account, game load: to operations, no new code), **bar** (the contract or proof of done is wrong or incomplete: to
   the Setter). A reason Judge cannot class is unknown and goes to diagnosis, never to Build.

Judge never sees token, account or resource figures, the item's cost so far, or why it was picked: none of them bears on
whether the contract was met, and each pulls toward passing work that was expensive or urgent.

## Known limit of this separation

A fresh copy of the same model shares the same blind spots, so Judge mode is not fully independent. Its catch rate is
measured with seeded defects (`TRUST.md`), and important items also get a second model. Seeds measure misses; they do
not measure false accepts on real work. So a sample of accepted items is re-judged by a fresh instance from the same
sha, and the rate at which a re-check rejects a pass is the Judge's false-accept rate, kept beside the catch rate.
