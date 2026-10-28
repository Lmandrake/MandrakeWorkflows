---
name: meeting-postbrief
description: Write a Meeting Postbrief, a one-page findings sheet sent after a technical meeting - the shared vocabulary the discussion needed, what was proposed and what it will and will not deliver against the real need, and concrete ways forward with named techniques and workday estimates. Use whenever someone asks for "a postbrief", "a findings sheet", "a cheat sheet from the meeting", "my notes with ways forward", "something to send the team after the call", or wants to turn a meeting (transcript, chat, slides, live notes) into a decision-ready one-pager for attendees; also offer one after any technical meeting where people talked past each other on terms, a plan was presented, or options were left open. Not for minutes or a full meeting summary (relevant-transcripts conventions) or a pre-meeting brief.
---

# Meeting Postbrief

A **Meeting Postbrief** is the one page you send attendees after a technical meeting. Minutes
record what was said; a postbrief records **what it means and what we could do next**. Write
one when people are using terms interchangeably, a plan is being taken as the answer to a
different question, or a lead needs to decide where to spend. An illustrative example, with
its rendered page, is `references/example-postbrief.md` and `assets/example-postbrief.pdf`.

It earns its place when the meeting had at least one of: words used loosely, a plan
presented, a decision left open. If it had none, send a summary instead.

## Inputs, gather all of them first

- The raw transcript (Teams/Plaud) and its summary, if one exists.
- The meeting chat (links, papers, code and data people pasted are often the real content).
- Slides or screenshots shown, and any live notes taken during the call.
- The project's own record: what the program actually needs (requirements, success criteria,
  the larger system this piece sits in). The postbrief judges the plan against *that*, not
  against what the presenter said it was for.

Quote people only with words the transcript shows. Mark anything from your own knowledge
(figures, product accuracies, method claims) as unverified unless you checked a source.

## The three sections, always in this order

Open with a title naming the topic, a subtitle (meeting, date, attendees, "Draft for
discussion"), and **two or three sentences of "why this matters"**: where this piece sits in
the larger system, and the one or two questions that decide what the project does next.

**1. Words we use, and when to ask for each.** A table: *Term* (with the precise technical
name in parentheses) · *Plain meaning* (one or two sentences a non-specialist reads cold) ·
*Ask for it when…* (one concrete question from THIS project that only that concept answers).
Pick the 6-10 terms the meeting actually blurred or needed, not a glossary of the field. Close
with two or three bold "rules of thumb" naming the confusions directly (e.g. "Sensitivity ≠
uncertainty"), and say which term the stakeholder's real question is.

**2. The proposed plan.** Four short labelled paragraphs, each its own paragraph (a blank line
between them in the markdown, or they run together into one block on the page): **Does** (what
will be run, in plain words, technique names in parentheses, timeline and dependencies) ·
**Will measure** · **Will not measure** · **Against the need** (an honest fraction, "about a
third of the way", plus the stakeholder's actual worry in their own words). Lead with what is
strong; this goes to the person who made the plan.

**3. Quick ways forward.** A table: *Add-on (technique)* lettered A, B, C… with a bold plain
name, then the precise method in parentheses · *What it gives* (the decision or answer it
unlocks) · *Workdays* (a range; "0 if X already exists" is fine; dependencies like "½ after
A"). Cheap and incremental beats grand: each should extend the existing plan, not replace it.
End with one bold **Shortest useful path** line: which letters, in what order, how long, and
what that buys the decision-maker.

## Style

- **Technical terms correct, everything else very plain.** The parenthesis carries the jargon
  so the sentence doesn't have to.
- Constructive, never a takedown: the presenter will read it. Credit first, gaps second.
- One page, letter size. If it doesn't fit, cut terms or add-ons; don't shrink below the
  script's floor.
- No em dashes in prose. Absolute dates. Names spelled as the team spells them.

## Build and deliver

1. Write the markdown in the project (e.g. `<project>/working/<topic>/<PROJECT>_<topic>_postbrief.md`),
   with `title:` and `subtitle:` YAML front matter as in `references/example-postbrief.md`.
2. Render: `sh ~/.claude/skills/meeting-postbrief/scripts/build_pdf.sh <file.md>` (pandoc +
   headless Chrome, `assets/postbrief.css`; steps the zoom down until it is one page). Then
   look at the rendered page (`pdftoppm -r 110 -png -singlefile <pdf> /tmp/pb` and view the
   PNG): a page count says nothing about a section that ran together, a clipped table or a
   row that wrapped into a wall of text, and the reader sees only the page.
3. Show the owner the PDF. Only on his word: copy it to the team's shared drive and email it to
   the attendees (as a draft first).
4. Commit the markdown and PDF; note in the meeting's notes file where it went.

In the meeting-transcripts workflow this is an optional fifth step after the summary: offer it
when the meeting fits the "earns its place" test above.
