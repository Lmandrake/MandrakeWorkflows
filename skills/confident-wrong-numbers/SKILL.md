---
name: confident-wrong-numbers
description: Catch a query whose shape returns a confident wrong number (a count, zero, empty list, all-None field) before you report it. Use before stating any number from grep, wc, ls, glob, regex, getattr, dict key, API call or census script; when a result is 0, empty, all-None, round or alarming; and before writing any census, sweep, audit or checker script.
---

# Confident wrong numbers

A query's **shape** can guarantee a plausible answer to a question you did not
ask. The instrument does not error or warn; it returns an integer that looks
like a right one. The wrongness is in the construction, not the output.
Instances: `references/instances.md` (read when you need a worked example).

## The tells: shapes of query that lie

Every entry below returned a real number for a real question — just not the
question the author had in mind. Learn the shapes, not the incidents; the next
one will wear a different filename.

| the shape you wrote | what it actually measures | the honest instrument |
|---|---|---|
| **A line count as an entry count.** `grep -c`, `wc -l` on structured text | lines *containing* the pattern — one element per line is an assumption, and a stack trace is 30 of them | parse the format (XML, JSON, the log's own record boundaries) and count records |
| **An existence test as an identity test.** `[ -e dir ]`, `ls dir \| wc -l`, "the file is there" | that a *path* resolves — a folder of `__pycache__` passes, a misspelled path yields `0` with no error | test the file that *identifies* the thing (`dir/About.xml`, the key inside it); glob a pattern that errors on a bad path; list the parent |
| **A fixed index as a field.** line 2, `hits[0]`, `cols[3]`, an id read as a position | whatever sits at that position *today* — silently the wrong thing when one file differs or filesystem order changes | read by key: the first line *matching* `subject:`, the entry whose id equals N, the column by its header |
| **A pattern wider or narrower than the thing.** `*south*` also hits `_southm`; a backtick-only regex misses the bare form; `alpha > 0` admits a halo; bare names resolve against something else too | the pattern's population, which overlaps yours | enumerate what the pattern matched on a sample; check a known positive AND a known negative before trusting the count |
| **A key that does not exist.** `getattr(dict, "x")`, `row["defName"]` where the field is `def`, `<def>` where the schema says `<defName>`, `defName` where the column is `def_name` | nothing — every lookup returns `None`, `0` or an error, uniformly, for every record | discover the vocabulary first (one record printed whole, the schema, the tool's inputSchema); an all-None or all-zero result is a key mismatch until shown otherwise |
| **An error swallowed as empty.** a query whose failure prints a line your script then greps for rows; a tool leaf that does not exist and returns nothing | that the query *failed* — "0 of 109" is the shape of an exception | check the exit status / error channel before reading a result as empty |
| **A record read as the thing it records.** an exported CSV, a snapshot pool, an index table, a config file, a backup byte-identical to live | the world at the record's export time, which may be days old and edited since | the live system, stated as such; the record is evidence only about its own date |
| **A source read as the effective state.** the def alone, the roster, the base XML | a *lower bound* — patches, padding, overrides and load order add to it | the post-load view (dump, running process, resolved object); presence in the source is safe to assert, absence is not |
| **A scope that drifted.** the current map after a switch; a tool run without the flag that widens its view; a checker comparing two derived files and never the artifact | a different population than the one in your sentence | state the scope in the report; if the tool has a scope parameter, name the value you used |
| **A proxy set as the population.** a 2-name spot check subtracted as if it were the whole gated set | the proxy | count the population directly; a spot check is a smoke test, never an operand |
| **A text scan that ignores grammar.** defNames inside XML comments; `[Tool(` and its name on separate lines scanned line by line | tokens the parser would discard, or would join | strip comments / match the region as text / parse; whatever the consumer does, do that |
| **An uncalibrated zero.** "no fire started" on ground that cannot burn; "not found" from a tool that cannot see that kind | the instrument's blind spot | run it on a case where the answer is known to be non-zero first |
| **A membership test as a cardinality test.** "is X present in the expected set" checked once per item | whether the item occurs at all — a DUPLICATED item still reads as present, so repetition is invisible | compare multisets/counts, not set membership, whenever the failure mode you care about is repetition |
| **A truthiness default as a presence default.** jq `.k // "absent"`, Python `or`, JS `\|\|` | whether the value is *truthy*, and the three differ: jq `//` falls back on `false`/`null` only (keeps `0`, `""`); Python `or` on all falsy (`0`, `""`, `None`, `False`, `[]`); JS `\|\|` on all falsy, JS `??` on `null`/`undefined` only. A legitimate `false`/`0`/`""` reports as MISSING | `has("k")` for presence; `if has("k") then .k else "absent" end`; in JS `??` or an explicit key test |
| **A conclusion printed unconditionally beside its evidence.** `grep ... ; echo "(none above = X)"` | nothing: the `echo` runs regardless, so the verdict is independent of the result | branch on exit status, all three outcomes: `grep -q ... f; rc=$?; case $rc in 0) FOUND;; 1) NONE;; *) ERROR;; esac` (grep exits 2 on a missing file, which a two-way `if/else` reports as NONE); or print the count and infer in prose |

Two asymmetries fall out of the table and are worth carrying separately:

- **Presence is cheaper to trust than absence.** A hit proves the thing exists
  in *some* form; a miss proves only that your query did not find it.
- **Agreement is not corroboration when the instruments share a premise.** Two
  passes that both count lines, or both read the same export, will agree on the
  same wrong number. Independence means a different *shape*, not a second run.

## Before you report a number

Run this on every number that is about to leave your hands — into a reply, a
doc, an item, a decision. It takes seconds; the wrong number costs hours.

1. **Name the instrument.** Not "I checked" — the exact command, key, pattern or
   tool call. If you cannot write it down, you cannot be sure what it measured.

2. **Name the other world that returns this same number.** Ask: *if the thing I
   care about were completely different, what would still make this query say
   exactly this?* A missing directory says `0`. A wrong key says `None`
   everywhere. An error line says "no rows". A mask says "saturated". If such a
   world exists and you have not ruled it out, the number is a hypothesis.

3. **Cross-measure when it is round, zero, empty, uniform or alarming.** Use an
   instrument with a different shape — a parser instead of a scan, a listing of
   the parent instead of the child, the live system instead of the record, one
   record printed whole instead of a field extracted from all of them. A second
   run of the same query is not a cross-measure.

4. **Calibrate before you trust a zero.** Point the instrument at a case whose
   answer you already know to be non-zero. If it cannot find the known
   positive, its zero on the unknown means nothing.

5. **Report it as MEASURED or UNMEASURED, with scope.** "MEASURED 631 active
   mods, parsed from `ModsConfig.xml` `activeMods`, on this machine, now." Or
   "UNMEASURED — the instrument cannot see this from here." Never a bare
   integer, and never `0` standing in for "I could not tell."

The heuristic that compresses all five: **a count that is conveniently or
alarmingly round is a query bug until proven otherwise.**

## The alarming direction

Alarming numbers ("all four checklists have 0 bars", "0 of N carry the trait")
are the *more* suspect direction: alarm feels like rigour, so they go
unchecked and travel fastest. Re-run them with a different-shaped instrument.

## When a hook already enforces it

If a hook refuses a query shape (e.g. `grep`/`wc` on a file whose encoding the
scanner cannot read), read the refusal as a worked example of this skill: do not
route around it with a synonym tool; ask which row of the table it protects you
from, and apply that row to queries no hook can see (`getattr` on a dict, `ls`
on a guessed path).

## Neighbours

- **`measuring-large-artifacts`** — the artifact is too big to read, so you
  reached for a scanner that does not understand its encoding. Here the
  artifact is small and the query is the bug.
- **`verify-before-you-escalate`** — someone *wrote* a claim and it decayed.
  This skill is about a claim you are about to generate yourself.
- **`calibrating-binary-formats`** — the bytes are opaque and you are guessing
  the encoding. Here the text is perfectly readable and you asked it the wrong
  question.
- **`grader-validation`** — the lying instrument is a scorer, oracle, guard, or
  witness you built to grade your own work, not a one-off query. Use that skill
  when the wrong number is itself a correctness verdict — "0 lost", "0
  violations", "all tests pass" — rather than a fact about the world.

Catalogue of instances, generalized shape first and a concrete example second:
`references/instances.md`.
