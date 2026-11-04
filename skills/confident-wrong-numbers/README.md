# confident-wrong-numbers

A Claude Code skill for one failure class: **a query whose shape returns a
confident wrong number.** Not a file too big to read, not an opaque encoding,
not a stale doc — a small, readable query built so that it answers a different
question from the one asked, and answers it with a clean integer. `ls dir | wc -l`
on a directory that does not exist prints `0`. `grep -c '<li>'` counts lines, not
elements. `getattr` on a dict returns `None` for every record and "0 bars" for
every checklist. `SKILL.md` gives the fifteen shapes as a table (what you wrote,
what it measured, what to use instead), a five-step protocol to run before any
number leaves your hands, and the bias that makes alarming wrong numbers travel
faster than convenient ones. `references/instances.md` is the catalogue, each
shape generalized first and then illustrated with a real case.

## Install

The skill is a directory; Claude Code finds it through `~/.claude/skills/`.
Clone or check out this repo somewhere permanent and symlink it in:

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/confident-wrong-numbers ~/.claude/skills/confident-wrong-numbers
```

Editing the checkout edits the installed skill; there is no build step. It
pairs with `measuring-large-artifacts` (files you cannot open whole) and any
project-level skill that covers written-claim verification; it does not
depend on either.

## Provenance

Extracted 2026-09-23 from a RimWorld modding project whose lessons inbox had
accumulated 57 entries under the theme "wrong number / lying instrument" with
no skill to own them, while the doctrine existed only as a `PreToolUse` hook
that refused specific scan patterns. The heuristics at the spine — *a count that
is conveniently or alarmingly round is a query bug until proven otherwise*, and
*two passes agreeing on a round number is not corroboration when both share an
instrument* — were written into that project's instruction file after repeated
incidents; this skill is where they generalize. The RimWorld paths and def names
in the catalogue are examples only.
