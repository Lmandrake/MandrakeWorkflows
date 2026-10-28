> **Illustrative example** — authored to demonstrate the *concept brief* shape of an ideogram. Scenario is realistic but not a live project deliverable; specifics marked [EXAMPLE].

**Blocks used:** Header · § THE ASK · § HOW SUCCESS IS MEASURED · § WHY THIS EXISTS (heavy — this is the spine) · § ADDITIONAL CONTEXT (heavy) · § HOW I'LL HELP · Appendix A (cover note) · Appendix C (self-check)
**Deliberately omitted:** § RUN ARCHITECTURE / § REPRODUCTION MECHANISM / § DELIVERED INFRASTRUCTURE (no software to stand up); § DEFINITION FILES / § RESULTS / § CONCLUSIONS (no experiment to record); narrative-spine (nothing to feed); known-gap-with-owner (not a status ask); Appendix B response-skeleton (the "delivery" is the reader's own restatement, not a mergeable artifact)

*The point of this example: a concept brief carries almost none of the machinery a status or handoff ideogram uses. It lives or dies on § WHY THIS EXISTS and § ADDITIONAL CONTEXT, and its success is measured by whether the reader can restate the idea and its boundaries — not by a file, metric, or run.*

---

# Certified Tacit-Knowledge Entries — What the Idea Is, for a Colleague [EXAMPLE]

**Author:** a data-science-forward researcher [EXAMPLE]
**Recipient:** a colleague on a more traditional science team [EXAMPLE] — deep domain expertise, less day-to-day LLM exposure
**Date:** 2026-08-26  ·  **Version:** 0.1
**Scope cutoff:** N/A — a concept brief isn't re-run against "new material since last time." It's
re-read when the idea needs explaining again; edit it when the idea itself changes.

> **This is an ideogram.** It's a request you can talk to — here it exists to *transfer an idea*.
> Read **§ THE ASK** and **§ HOW SUCCESS IS MEASURED**; the real substance is in **§ WHY THIS
> EXISTS**. You can run it — "Claude, explain this concept to me and check my understanding" —
> respond to it in your own words, or ask *"Is my restatement sufficient?"* for a neutral read.
> **It guides; it doesn't decide whether you've "got it." You do.** There's nothing to build
> here — the deliverable is *your accurate understanding*, including where the idea stops.

---

## § THE ASK  *(read in under a minute)*

I want you to come away able to **explain, in your own words, what a "certified tacit-knowledge
entry" [EXAMPLE] is — and, just as important, what it is *not*.** Concretely, the ask is that you
can:

1. state the idea in one or two sentences to a third colleague;
2. name what problem it solves and why existing options don't;
3. draw its **boundaries** — the two or three things people will assume it is that it isn't.

There is no file to produce and no run to reproduce. The "delivery" is your restatement. If
you want to write it down so I can check it, great — but the target is understanding, not an
artifact.

---

## § HOW SUCCESS IS MEASURED  *(the bar — what "the reader got it" means)*

Understanding is sufficient when the reader can:

1. **Restate the idea correctly and unprompted** — a one-to-two-sentence version that a third
   colleague would find accurate, without leaning on my exact phrasing.
2. **Name the problem it solves and why the obvious alternatives fall short** — i.e. why not
   just a wiki page, a code comment, or a fine-tuned model.
3. **Draw the boundaries correctly** — correctly identify at least **2 of the 3** common
   misconceptions in § ADDITIONAL CONTEXT as things the idea is *not* (e.g. it's not a chatbot,
   not a code snippet, not a replacement for peer review).
4. **Apply it to one new case** — given an example from the reader's own domain, correctly
   judge whether it would or wouldn't qualify as a certified tacit-knowledge entry, and say why.

These are checks on comprehension, not deliverables to grade for completeness. `[AUTHOR TO
CONFIRM]` whether "2 of 3 boundaries" is the right bar or it should be all three.

---

## § WHY THIS EXISTS  *(intent, need & context — the heart of a concept brief)*

**The problem.** On a science team, the most valuable knowledge is often *tacit*: the "you have
to know that this retrieval goes wrong over bright surfaces" kind of insight that lives in one
expert's head and leaves when they do. We normally transfer it through apprenticeship — slow,
unscalable, and lossy. Documentation half-solves it: wikis rot, and a paragraph of prose isn't
something a downstream tool (or a new hire, or an LLM) can reliably *act on*.

**The idea, stated plainly.** A **certified tacit-knowledge entry** [EXAMPLE] is a small,
text-only, human-authored unit of hard-won domain insight that has been (a) written in a form a
machine or a newcomer can act on, (b) **certified** — checked against a concrete failure it's
supposed to prevent — and (c) **owned** by the team that holds the expertise, not by a tool
vendor. Think "a durable, testable note that captures what an expert knows and why it matters,"
distinct from both a code snippet and a wiki paragraph.

**Why it's worth a new name.** The novelty isn't "write things down." It's the **certification**
step — an entry only counts once you can point to the failure it prevents (a bad result it would
have caught) — and the **ownership** stance: the knowledge stays mission-owned and text-first, so
it survives tool changes and can be audited. That combination is what existing options miss:

- a **wiki page** isn't certified (nobody tested that it prevents a specific failure) and rots;
- a **code comment** is certified-ish but bound to one implementation and invisible outside it;
- a **fine-tuned model** absorbs the knowledge but hides it — you can't read, audit, or correct
  a single fact, and it's owned by whoever holds the weights.

**Why I'm telling *you* specifically.** You hold exactly the kind of tacit expertise this is
meant to capture, and you're on a team that (reasonably) hasn't lived inside the LLM tooling
world. If the idea only makes sense to people already fluent in that world, it has failed. So
this brief is also a test of the idea: if I can't get *you* to restate it accurately and spot
its boundaries, the concept isn't ready.

---

## § HOW I'LL HELP  *(mechanisms & policies)*

**My persona.** When you run me conversationally, I open like this:

> "Hello — I'm the **certified tacit-knowledge entry** [EXAMPLE] concept brief, here to help you
> come away able to explain this idea in your own words and know where it stops — not to quiz
> you or sell you anything. Want me to walk the idea in one paragraph and then check your
> restatement against a couple of common misconceptions? Or ask me anything, in any order. I
> won't assume you share the LLM-tooling background — tell me where a term lands as jargon and
> I'll ground it."

**How to engage.** Read § WHY THIS EXISTS; then either restate the idea back to me and ask "did
I get it?", or hand me a case from your own work and ask "would this qualify?" I'll meet you at
your vocabulary, not mine.

**Do's & Don'ts** (light, for a concept brief).
*Do:* push back where the idea sounds like hand-waving; bring an example from *your* domain to
test it against; tell me which sentence is jargon so I can reground it.
*Don't:* feel you owe me an artifact — your accurate restatement is the whole point; and don't
accept the idea just because it's written down (challenging it is welcome, see below).

**A premise worth challenging (mine).** I believe the certification step is what makes this more
than "documentation with a fresh coat of paint." If, after reading, you think it's *not*
meaningfully different from a good wiki with tests — tell me. That's the most useful thing you
could hand back.

**Self-check.** Ask me *"Is my restatement sufficient?"* and I'll grade your understanding
against the four checks above — Met / Partially / Not yet / N/A — with a one-line reason each,
and name the misconception most worth revisiting. You decide when you've got it.

---

## § ADDITIONAL CONTEXT  *(informs, but is not itself a deliverable — add freely)*

**The three boundaries (what it is *not*)** — these are the misconceptions success criterion 3
checks against:

1. **Not a chatbot / not a model.** A certified entry is a *readable, ownable fact*, not a
   trained system. You can point at it, edit one line, and audit it. A model can't be corrected
   fact-by-fact; an entry can.
2. **Not a code snippet.** Code is bound to an implementation and a language; a certified entry
   is the *reason* behind the code — the domain fact — stated so it stays true when the code is
   rewritten.
3. **Not a replacement for peer review or expertise.** It captures and transmits insight; it
   doesn't manufacture it. The expert is still the source; certification just makes the insight
   testable and portable.

**Where the idea comes from** (so you can place it): it generalizes the ordinary science-team
practice of "lessons learned" notes, but adds two disciplines borrowed from software — *a test
per claim* (the failure it prevents) and *ownership/versioning* (it lives with the team, in
text, under change control).

**What this brief deliberately leaves out.** No architecture, no code, no experiment, no metrics
— because none of that is what needs to transfer. If we later decide to *build* a store for these
entries, that's a **handoff** or **experiment-capture** ideogram, not this one. Keeping those out
is the point: a concept brief that drags in machinery buries the idea it's trying to plant.

---

## Appendix A — Cover note (ready to forward)

> Hi — I want to try explaining an idea I think is genuinely useful to your team, and I care more
> that *you* can restate it than that I sound clever. There's a short ideogram at
> `examples/concept_brief_example/concept_brief_ideogram.md` — read **§ WHY THIS EXISTS** (that's
> the whole thing) and, if you like, the three boundaries at the bottom. The idea is "certified
> tacit-knowledge entries" [EXAMPLE]. When you've read it, tell me the one-sentence version in
> your own words and whether an example from your work would qualify — and push back hard if it
> sounds like a wiki with extra steps. If you'd rather, ask Claude to walk you through it and
> then check your restatement. No artifact needed; your understanding is the deliverable. Thanks.

## Appendix C — Runnable self-check block

Paste this to Claude alongside your restatement to get a neutral comprehension read:

```
You are the certified tacit-knowledge entry [EXAMPLE] concept-brief ideogram acting as a neutral reviewer.
Read: (1) this ideogram's "§ HOW SUCCESS IS MEASURED" section and "§ ADDITIONAL CONTEXT", and
(2) the reader's restatement / applied example that I provide.
Produce a table:
  Check | Verdict (Met / Partially met / Not yet / N/A) | One-line reason | The misconception most worth revisiting
The four checks are: (1) accurate unprompted one-to-two-sentence restatement; (2) names the problem
and why alternatives fall short; (3) correctly draws >=2 of the 3 boundaries; (4) correctly judges a
new case as qualifying or not, with a reason.
Rules: grade only comprehension against the stated checks; never inflate, never gatekeep; if a
boundary is blurred, say which one and why. This is not a completeness audit of an artifact.
Close with: "You decide when you've got it — here is where your understanding stands against the bar."
Do not rewrite the reader's restatement; only assess it.
```

---
*Illustrative example authored with the `ideogram` skill (`skills/ideogram` in MandrakeWorkflows). Not a live deliverable. Bump the version line on each edit.*
