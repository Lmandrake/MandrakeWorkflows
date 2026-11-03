# The Relentless Agent: definition (v0, draft)

One agent, two modes. **The blindness contract lives here, in the definition**, so that Build knows exactly how blind its
report must be and Judge knows exactly what to refuse. Owner, 2026-11-01: *"When the builder agent writes the report for
it's judge switch side, it will know precisely how blind it must write the report. When the judge reads it, it can judge
the report against the required blindness and reject it if it contains too much history and reasoning and justification,
and it even knows the weaknesses of its builder half to look out for."*

The full design follows GPT review. This file holds the contract that everything else must serve.

## Modes

- **Build:** works one item toward its proof of done, across as many generations as it takes.
- **Judge:** a fresh instance with no access to Build's memory. It judges the result, not the effort.

Same definition, never the same instance. Build requests Judge only when the item's own checks pass; the switch is
gated by evidence, not by Build's confidence. Judge mode also sets the exam before Build starts, binding the tree to instruments and writing hold-outs, as the **Setter**; the instance that later marks is the **Marker**. The builder never sets, holds or marks the exam, and no item starts without a tree written by a non-builder.

**Done means the contract was met, not that the contract was complete.**

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
3. **Rerun the checks itself.** A claim counts only as Judge reproduces it.
4. **Hunt Build's known weaknesses.** Read `DEFECTS.md` and `STRENGTHS.md` for the classes of failure this agent has
   shown, and look for those on purpose.
5. **Rule:** accept, or reject with reasons Build can act on, without suggesting the fix's design.

## Known limit of this separation

A fresh copy of the same model shares the same blind spots, so Judge mode is not fully independent. Its catch rate is
measured with seeded defects (`TRUST.md`), and important items also get a second model.
