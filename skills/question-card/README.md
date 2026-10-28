# QuestionCard

A Claude Code skill defining how a choice gets put to a human.

A **Question Card** is a set of genuinely different options, each carrying its
trade-offs in both directions, with no internal jargon or opaque identifiers as
labels, the least framing needed to decide, and — always — a line the reader can
type on, so disagreeing with the frame is no harder than accepting it.

The skill lives in [`SKILL.md`](SKILL.md). The rulings behind each rule, with the
reasons and the refuted theories, are in
[`references/DECISIONS.md`](references/DECISIONS.md).

## Install

```sh
ln -s "$(pwd)/skills/question-card" ~/.claude/skills/question-card   # from the repo root
```

## Why it exists

Multiple-choice questions quietly assert that the frame is right. Often it is not,
and a menu with no write-in makes disagreeing with the frame more work than
accepting it. The card format exists to keep that door open, and to stop options
from being labelled with identifiers only the asker understands.

## The one mechanical fact worth knowing up front

The write-in line is drawn by the client, not authored by the asker. Two ways it
gets lost, both observed and both recorded in `references/DECISIONS.md`:

- **Authoring your own option labelled `Type:`.** A label is not a text field —
  selecting it submits the label. This is worse than omitting it, because it looks
  like a write-in and isn't.
- **Putting a `preview` on any option.** This flips the client to a side-by-side
  layout that does not draw the write-in line, leaving only "Chat about this",
  which aborts rather than answers. Option count is not the variable; previews are.
  So the skill declines previews outright and puts mockups above the card instead.

## Growing it

Corrections get appended to `references/DECISIONS.md` as dated rulings with the
user's own wording and the reason attached, then folded into the rules in
`SKILL.md`. Reversals are marked superseded rather than deleted — a deleted mistake
just gets re-derived by the next reader.
