# Ideogram

A small system for writing **ideograms** — living, self-contained documents that behave like
a brief a person (or Claude) can converse with, respond to, and check their response against.

An ideogram is more than a ticket, a spec, or a prompt. It carries its purpose, the bar for
"done," the reasons behind it, and the means to self-verify — and it can be run several ways
without editing: as an ask to Claude, as a brief to a human, as a neutral judge of a draft
("Is this sufficient?"), or as a compositor helping the author merge what came back.

**An ideogram is not necessarily a request.** That's the most common shape, but one can
equally carry an idea to be understood, a repository's design intent, an experiment's record,
or a meeting's decisions and forward plan. What every ideogram has is three things — a
purpose, a bar for having engaged with it, and a way to self-check against that bar.

## Layout

```
skills/ideogram/
├── README.md
├── SKILL.md            # the doctrine: what an ideogram is, its anatomy, how to author one
├── templates/ideogram_template.md
├── references/block_registry.md
├── evals/  scripts/    # trigger evals, cold-read test script
├── examples/           # illustrative ideograms, one per shape
└── docs/               # preserved deployment probes (negative fixtures)
```

## Using it

- **Write a new ideogram:** invoke the `ideogram` skill (or copy
  `./templates/ideogram_template.md`) and fill each section, grounded
  in real, named artifacts.
- **Run one:** hand the finished ideogram to Claude — "satisfy this from the relevant files
  in my directory since the last cutoff" — or to a human contributor.
- **Check a draft:** ask the ideogram "Is this sufficient?" for a criteria-by-criteria read.

The skill is the source of truth. To make it available across sessions (in the slash menu),
register it as a user skill; otherwise it is active whenever this repo is the working project.

## Anatomy (quick reference)

There is no required section list — there are **four invariants**, and the shape decides
which block realizes each one.

| Invariant | What it does | Realized by |
|---|---|---|
| **I0 · Activation** | makes Claude *become* the ideogram rather than describe it, and says where the document stands right now | the front door + `§ WHERE I'VE BEEN` + the standing menu |
| **I1 · Purpose** | what this document is for | `§ THE ASK` · `§ WHAT THIS CARRIES` · `§ WHAT THIS RECORDS` |
| **I2 · Sufficiency** | what counts as having engaged with it properly | `§ HOW SUCCESS IS MEASURED` · comprehension checks · completeness criteria |
| **I3 · Self-check** | how a reader grades themselves with the author absent | runnable self-check block, or an inline protocol |

Everything else is optional and shape-dependent:

| Block | Holds | Tier |
|---|---|---|
| Header / identity | title, author, recipients + angles, date, version | near-universal (metadata) |
| The mold (response / capture skeleton) | the outline that shapes what comes back, plus the self-check receipt | **common — strongest evidence** |
| § WHY THIS EXISTS | intent, need, context, the decision served | common |
| § WHERE I'VE BEEN | running log: arrival state at the head, closure ledger at the tail | near-universal (part of I0) |
| Front door + menu | activation directive, current state, and the standing interaction menu | near-universal (I0) |
| § ADDITIONAL CONTEXT | everything that informs but isn't a deliverable; grows freely | common |
| § HOW I'LL HELP | engagement policy, do's & don'ts, self-check placement | common |
| Persona | consent-seeking conversational guide | **situational** — skip for records and briefs |
| Scope cutoff | the temporal window for a re-run | situational |
| Cover notes, known-gap, premise-to-challenge, narrative spine, … | see the block registry | situational |

_First ideogram authored with this skill: a project report-out (see
`examples/README.md`). Its lessons are what promoted the mold and demoted the persona — see
`references/block_registry.md`._

> Moved to MandrakeWorkflows/skills/ideogram on 2026-10-15; the standalone Ideogram repo is archived.
