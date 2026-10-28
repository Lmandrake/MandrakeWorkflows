---
name: "relevant-transcripts"
description: "Manage the user's meeting-transcript archive (at $TRANSCRIPTS_ROOT, else the $TRANSCRIPTS shortcut), where every raw transcript in source/ is paired with exactly one written summary in summary/ — two artifacts per meeting, never three. Use whenever the user wants to file, add, or ingest a meeting transcript or recording; write, rewrite, extend, or fix a meeting summary; ask what a past meeting decided, who attended, or what was assigned ('what did we decide about X', 'summarize the NWS meeting', 'who owns that action'); name a transcript file or ask about the naming convention; reconcile duplicate or multi-part recordings; check summary fidelity or quotation accuracy; or commit and push transcript work to the archive's git remote. Summaries are the durable artifact — raw transcripts are auto-generated and garble names, acronyms, and speakers, so the summary is where correction and attribution live; names, acronyms and project slugs are checked against a reference list when you have one."
---

> 🔴 **ARCHIVING IS PAUSED** (owner: *"turn off Relevant Transcripts keeping copies of
> transcripts from now on"*). Do not file new transcripts or summaries into the archive. Soundings
> (`meeting-transcripts`) delivers pairs to project directories instead, and this skill's naming
> and summary-writing conventions still govern those pairs. **Sensitive personal recordings never
> come here**, nor into any project dir. Reading the existing archive is fine.

# Relevant Transcripts — meeting transcripts and their summaries

A method for keeping meeting transcripts with their summaries, and an archive kept that way.

## Where the archive is (configurable)

The archive root is **configurable**: set `TRANSCRIPTS_ROOT` to any directory holding `source/`
and `summary/` (an `eval/` beside them is optional). Unset, the `$TRANSCRIPTS` shortcut is used
(a shell shortcut pointing at the owner's archive); with neither set there is no default,
so stop and say which variable is missing. If the root is absent, stop and say so by name
(`TRANSCRIPTS_ROOT: <path> has no source/`); never treat a missing archive as an empty one.
`scripts/quote_check.py` resolves the root the same way and refuses the same way.

```sh
TRANSCRIPTS="${TRANSCRIPTS_ROOT:-${TRANSCRIPTS:?set TRANSCRIPTS_ROOT to the archive root}}"
```

The archive lives in a **private** repo (see [Git](#git): the private visibility is load-bearing).
A worked, invented example of one meeting pair is in `examples/` (see [Example](#example)).

Every raw transcript in `source/` has one written summary in `summary/`. The point of keeping
them together is traceability: any claim in a summary can be checked against the words it came
from.

## The one rule that governs everything

**`source/` is immutable; `summary/` is where all interpretation lives.**

Auto-transcription mangles names, technical terms, and speaker labels — but "fixing" the source
destroys the only record of what was actually captured, and silently changes what future readers
can verify. So never edit a source file, not even for an obvious typo. Every correction,
standardization, and attribution guess belongs in the summary's **transcription note**, where it
is visible as an interpretation rather than disguised as fact.

New transcripts may arrive from a recorder-ingestion workflow: file its raw transcript as the source.

## Naming

    source/<YYYY-MM-DD>_<project>_<topic>.txt
    summary/<YYYY-MM-DD>_<project>_<topic>.md

Lowercase; hyphens within a field, underscores between fields; the date is the date of the
**meeting**, not of the writing. Example: `2031-03-12_tidewater_buoy-calibration-review`.

A summary's basename normally matches its source's exactly. Two situations break the 1:1 rule:

- **One meeting split across several recordings, or one meeting too big for a single summary.**
  Each part takes a `_part<N>-<topic>` suffix on the shared prefix; **one** summary may take the
  bare shared prefix. So `..._site-visit_part1-briefing.txt` and
  `..._part2-ops-floor.txt` are both summarized by `..._site-visit.md`. When you
  need a filename for a summary covering several parts, the shared prefix *is* the answer — don't
  invent a new suffix.
- **Two separate sessions on the same day.** Treat them as distinct meetings with distinct
  topics rather than merging into a day-level summary. A summary scoped to one room and one
  conversation stays useful; a merged one goes stale in halves.

## Before you commit: the duplicate check

The recurring failure mode is **the same transcript filed twice under two names**, usually
because one meeting got grouped into two different summary framings. It is invisible in
`git status` and permanent once committed. Always hash first:

```sh
cd "$TRANSCRIPTS/source" && md5 *.txt        # identical hashes = same recording
```

If two names share a hash, keep exactly one source file and let both summaries reference it.
Decide *which* name survives by asking what the meeting actually was, not which file is newer.

## Before you replace or rewrite a summary

Summaries are dense and represent real work. Never overwrite one without first reading **both**
it and any summary that supposedly supersedes it, then confirming section by section that
nothing unique dies. Two traps:

- A "redundant" summary often carries a **Key Dates & Action Items** section whose entries exist
  nowhere else. Carry the still-relevant ones forward.
- Coverage can be asymmetric: a broad day-level summary may be *thinner* on the morning than a
  dedicated morning summary while being the *only* record of the afternoon. Overlap is not
  redundancy.

If untracked files are the ones being dropped, prefer leaving them on disk over `rm` — an
untracked file has no git history to recover from.

## Writing a summary

Work from the **source transcripts**, not from another summary. Re-summarizing a summary
compounds its errors and silently drops whatever it omitted.

The house shape, worth following because it is what makes these searchable years later:

1. An `# H1` title naming the project and the specific session.
2. A bold **Date / time** line precise about *which* session this covers (and, if a sibling
   summary covers the other half of the day, name that file), then a **Participants** list with
   affiliations and roles — split into host org vs. visiting team when that's the structure.
3. A one-line note that the summary is **selective**, naming the transcript that holds
   everything said.
4. A **transcription note**. This is the highest-value part and the easiest to skip. Record: the
   standardized spelling of every garbled name, model, acronym, and tool; any figure the
   transcript states inconsistently (grid spacings and units are frequent offenders); and every
   **speaker attribution that is inferred rather than certain**, with the evidence. Write
   "Speaker 3 is almost certainly Tamsin, because the chair addresses her by name and Speaker 3
   answers about her product" — not a bare assertion, and not silent omission.

   **Check a reference list before finalizing the note.** If you keep a knowledge base of the
   correct spellings of the people, orgs, projects, acronyms and tools these transcripts garble,
   look up every such candidate in it, read-only.

   Record each correction as **confirmed via the reference (`<record>`)** or as **inferred**,
   with its evidence. An ambiguous result is a candidate list, not an answer — narrow it or mark
   it inferred. Use the same lookups to pick the right `<project>` slug for the filename. Never
   write to the knowledge base from here, and `source/` stays untouched.
5. The body as **prose bullets**, each a self-contained paragraph on one thread, with decisions,
   numbers, and key terms bolded. Long bullets are correct here; fragmenting a thread across
   bullets loses the argument.
6. A closing `## Key Dates & Action Items`, dates separated from owner-prefixed actions. Convert
   every relative reference to an absolute date, keeping the original phrasing in parentheses:
   `2026-09-18 ("within a month")`. Relative dates are worthless once the meeting recedes.

Capture disagreement and things that surprised the participants, not just conclusions — the
moment where someone's stated priority inverts the team's assumption is usually the most
valuable thing in the transcript, and it is exactly what a mechanical summary flattens away.

## The three rules that are not negotiable

The shape above is a house style. These three are constraints.

### 1. A summary is short: about 3:1 of the body. Substance is lost, deliberately.

**Measure source bytes ÷ body bytes**, where body excludes the transcription note and
`Key Dates & Action Items`. Those are apparatus and do not shrink with the meeting; a
heavily-garbled transcript needs a long correction note, and that must never be paid for out of
the meeting's content.

Below about 1.5:1 you are transcribing, not summarizing. Above about 8:1 fidelity collapses —
quotations start getting fabricated and attributions reversed.

A summary cannot be verbatim, complete, and short all at once. This archive picks verbatim and
short, so **some reasoning, detail, and argument will not survive.** That is the accepted cost,
not a defect to apologise for, and it is safe only because `source/` is immutable — nothing is
destroyed by leaving it out, it stays one file away, verbatim, forever.

What is *not* acceptable is silent or careless loss:

- **Say that the summary is selective**, and name the transcript that holds everything.
- **Never drop a commitment, an owner, a figure, or a date.** These are cheap in words and
  expensive to lose; they are not what compression should buy.
- **Never keep half an exchange.** If an objection's answer doesn't fit, cut both. A recorded
  objection whose rebuttal was dropped misrepresents the room.
- **Prefer cutting a whole thread to thinning every thread.** Ten topics at half depth is worse
  than six at full depth, because a half-recorded argument reads as a complete one.

If a meeting genuinely cannot be told at 3:1, **write more than one summary** using the
`_part<N>-<topic>` convention, scoped by topic. That is the escape hatch, and it beats both
padding and silent omission.

**Two artifacts per meeting, never three.** Do not add a digest, brief, delta, or index layer on
top of the summary — that has been tried here and rejected. The summary is the reading layer, and
anything derived from it goes stale the moment it is re-cut.

### 2. Quote marks mean verbatim. The writer's words go outside them.

- Inside quote marks, only words the speaker actually said, in the order they said them.
- Elision is marked `…`. Nothing else may be dropped silently.
- A word you supply goes in `[brackets]`, and brackets go **outside** the quotation wherever
  possible — never smuggled in to make a sentence read better.
- **Never build one quotation from two turns, and never attribute a quotation to two people
  jointly.** There is then no speaker it can be checked against.
- If you cannot quote it accurately, don't use quote marks. `**Lindqvist** argued for a swap` is
  honest; a tidied-up sentence in quote marks is not.

Quote generously — but on what was **load-bearing**, not merely what was quotable. A memorable
flourish in quote marks beside a paraphrased figure is the wrong way round.

### 3. Every claim names a speaker.

A reader must always be able to tell whether something is one person's view, the group's
conclusion, or your inference:

- Attribute claims to the person who made them.
- Where the group converged, say **who** said it and that others assented. Not "the team aligned
  on" — that hides whether anyone actually agreed.
- Your own synthesis is allowed and useful, but mark it as yours. A parenthetical
  `(my reading, not said in the room)` is enough.
- An inferred speaker attribution goes in the transcription note **with its evidence** — never
  asserted flatly in the body.

Ownership is what makes an error findable. An unowned sentence cannot be checked against
anything.

## Checking your work

`scripts/quote_check.py report` (in this skill) scores every pair in the archive mechanically: what share of quoted fragments are
actually verbatim, what share of body words are inside quote marks, and how much of the writer's
own prose is unowned. Run it after writing or rewriting a summary.

`scripts/quote_check.py validate` re-checks the extractor itself against the hand-labeled sample
in the archive's extractor-validation file. Its output is not trustworthy until that passes,
so don't quote a figure from a run that didn't. `--root DIR` overrides `TRANSCRIPTS_ROOT`.

The archive's findings file records what its compression measurably costs.

## Example

`examples/source/2031-03-12_tidewater_buoy-calibration-review.txt` is an invented raw transcript
(garbled names, unlabeled speakers) and `examples/summary/2031-03-12_tidewater_buoy-calibration-review.md`
its summary in the house shape: a transcription note with one inferred speaker and its evidence,
attributed prose bullets, a conceded objection kept with its answer, and absolute dates.
`python3 scripts/quote_check.py --root examples report` scores it (every quote verbatim).

## Git

The archive is versioned in whatever **private** repo holds `$TRANSCRIPTS_ROOT` (commit there with
named paths and push).
Commit source and summary together so a summary never lands without its evidence.

This skill (the method, the scorer and the invented example) lives separately, in
`MandrakeWorkflows/skills/relevant-transcripts/`, symlinked into `~/.claude/skills`. It holds no
real transcript, and none may be added to it: real pairs belong only in the archive.

Two things that matter:

- **The archive repo being private is load-bearing, not incidental.** Meeting summaries
  routinely carry material that is confidential to the people in the room. If `git -C "$TRANSCRIPTS" remote -v` ever shows a repo you have not confirmed private,
  **stop and confirm before pushing** (`gh repo view <owner/repo> --json isPrivate,visibility`
  settles it read-only in one call). Publishing this material is not undone by deleting it; it gets cached
  and indexed.
- Verify a push against the live remote (`git ls-remote origin main`) rather than trusting the
  local tracking branch, which can be stale. Don't trust this file about the remote either —
  `git remote get-url origin` costs nothing.

## Pitfalls

- Editing a source transcript to fix a name. Never; use the transcription note.
- Committing the same recording twice under two names. Hash before committing.
- Overwriting a summary without reading it. Read both, compare, then write.
- Summarizing from a summary rather than from the transcript.
- Asserting a speaker identity the transcript doesn't support. Mark it inferred.
- Guessing a name, acronym or project slug without checking the reference list first.
  Look up read-only; cite the record.
- Leaving a source with no summary. That's the one gap worth reporting proactively — the
  archive's value is the pairing.
- Compressing a big meeting into one small summary instead of writing several.
- Measuring the compression ratio on the whole file. It is the body, excluding the note and
  Key Dates.
- Tidying a quotation inside its quote marks. Verbatim or no quote marks.
- Building one quotation out of two turns, or attributing a quote to two people jointly.
- Quoting the memorable flourish and paraphrasing the number someone will need.
- Writing a sentence that names nobody.
- "The team aligned on…" — hides whether anyone actually agreed. Name who said it.
- Adding a third artifact per meeting.
