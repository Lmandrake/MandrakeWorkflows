---
name: measuring-large-artifacts
description: Get trustworthy numbers from files too large to read (def dumps, savegames, logs, DB exports, giant CSV/JSON). Use before grep/strings/wc on one, when a count decides something, when designing a dump format, when a 0, empty result or disagreeing sources need trusting, or a derived artifact may be stale.
---

# Measuring large artifacts

An artifact you cannot read whole is a **measuring problem**. Get a number you can
bet on, and say out loud, in the answer, when you cannot.

## The chain that produces a wrong number

```
the artifact is too large to READ
        ↓
so you reach for a SCANNING tool (grep, strings, wc)
        ↓
the scanner does not understand the artifact's ENCODING
        ↓
it returns a NUMBER, plausibly shaped, with no error
        ↓
that number decides something expensive
```

The scanner is not broken: it answered "how many lines contain this byte
sequence" correctly, and you read it as the answer to a different question.
**Size is what makes people reach for the wrong tool**, so a fix that does not make
the correct path *cheaper* than the scan will be routed around.

## The three answers

| answer | means | what `0` would have hidden |
|---|---|---|
| `MEASURED 612` | the number is real, and it says what it was measured against | — |
| `UNMEASURED` | the artifact does not carry the evidence | "not captured" reading as "none exist" |
| `REFUSED` | this instrument cannot judge this question | "cannot tell" reading as "none exist" |

**`0` must mean only one thing: measured zero.** Ignorance and inability get their
own words.

- **`if count:` is the bug.** A measured `0` is falsy, `Unmeasured` has no value, and the
  answer objects themselves are always truthy, so neither test says what you meant.
  Test the *kind* of answer, never the truthiness of the number.
- **A refusal that does not name the right instrument is an obstacle**, and gets
  bypassed. Every `UNMEASURED` and `REFUSED` carries a remedy.
- **A positive count over slices that could not be searched is a floor**, not a
  census: it reads `UNMEASURED at least N`, never `MEASURED N`.

## Using it

`measure` is `bin/measure` in this skill. It is **not on `PATH` by default**:
add `bin/` to `PATH`, or call the CLI directly:

```bash
python3 ~/.claude/skills/measuring-large-artifacts/scripts/measure/cli.py count <Type>
```

```bash
measure count <Type>          # MEASURED 24904  /  UNMEASURED + why
measure coverage              # what the artifact did NOT capture
measure get <name>            # does this exist, and as what
measure find <literal>        # does this exact string occur, and where
measure explain <path>        # what IS this file, and what may read it
measure csv <path> --where col=value
measure build                 # (re)build the queryable form
measure verify                # re-parse the source, check per-slice counts
```

Exit status carries the tri-state: `0` measured, `2` unmeasured, `3` refused, and
**`64` for a malformed command**, outside the measurement codes so a typo can never
read as a finding. One line per question; `--rows N` adds detail **without changing
the verdict or the exit code**.

**Before scanning anything big, run `measure explain <path>`.** It answers from the
same registry the guard rail uses, so advice and enforcement cannot drift apart.

Full command reference and the Python API: **`references/api.md`**.

## Building one

Designing the dump, export or cache rather than reading one? Read
**`references/building.md`** before choosing a layout (unique keys, per-slice
coverage, provenance, pruning; SQLite vs JSONL vs JSON). The short version:

- **Key on something that cannot collide.** A simple name is not unique. The same
  holds for a **comparator or scorer's** identity key (a section number, an
  enumerator letter): a collision there reads as agreement, duplication or
  fabrication, depending on which direction it hides.
- **Record what you did NOT capture**, per slice, as a first-class field.
- **Stamp what the artifact is an answer ABOUT**: the input set, a fingerprint, a
  capture time.
- **Prune, or mark, what accumulates.**

## Watching one

**Staleness: fingerprint, not timestamp.** Compare content identity (capture stamp,
input-set hash, load order), not mtime. Identical bytes re-written are not stale; a
touched file is not fresh. A source that is simply gone is **not** stale: the
archived artifact is the only record left.

**Accumulation.** Capture tools often write a file per slice and never delete one
for a slice that stopped existing. Check each part was written by *this* capture;
treat leftovers as orphans, never as data.

## Appropriate uses, and the honest limits

A derived artifact answers *what was true when it was captured, about the inputs it
captured*, and nothing more.

| the question | the instrument |
|---|---|
| what exists / how many, as of a capture | the artifact |
| what is true RIGHT NOW in a running system | the live system, never the artifact |
| what a config or source file SAYS | read the source; a dump shows the result, not the intent |
| does this exact literal string occur | a scan is fine; `measure find` adds coverage |
| how many, of something structured | never a scan |

⚠️ **`measure` does not answer every artifact.** It has commands for the def dump
and for CSVs; for a savegame, a log or an assembly it classifies the file and names
the right reader (`measure explain`). Where that reader cannot count, the honest
answer is `REFUSED` plus the narrower question that *can* be answered ("did X
occur" instead of "how many X").

**A literal-string search is legitimate.** "Does the byte sequence `Foo` occur" is
a scanner's question; "how many Foos" is not, whenever Foos are indices,
compressed, encoded or spread across records. When you want the literal form, say
so and proceed.

A scan still cannot read a hit in a single-line file back to a record, and a
**miss is not an absence** (the text may be escaped, `caf\u00e9` for `café`,
compressed, or in a slice never written). `measure find` covers both. It is **not**
faster than `grep`; it adds attribution and a coverage-gated zero.

## Validating an instrument

- **Agreement between sources is not correctness when they share a failure mode.**
  A manifest, a per-file total and the parsed records can all say `0`, corrupted
  identically by one collision.
- **A guard that looks like a gap is usually a guard.** Before reporting a finding
  against something that exists, check whether it already handles the case and
  says why.
- **Calibrate on the known POSITIVE, the known NEGATIVE, the EMPTY case and the
  TRUNCATED case**, each known independently, not from another reading of the same
  artifact. An instrument shown only the answer it was built to find has been run,
  not tested. A checklist sees only the dimensions it names: where something
  WROTE, the diff is the instrument.
- **A green suite is a hypothesis until the code is broken.** Mutate the code and
  require the case named in advance to notice (`scripts/mutate_check.py`). It must
  have: a **control run** first (a crashed or red suite is not green); a mutation
  site matching **exactly once**; an undetected mutation reported as a **gap**; and
  a mutation able to **reach the branch meant to catch it**, since a branch behind
  a filter that already removed every triggering input proves nothing.
- **Measure optimisations in combination, on the axis you meant to improve.** Two
  changes that each win alone can cancel; borrowed tuning is tuned for someone
  else's workload.

Worked cases with the real numbers: **`references/incidents.md`**.

## Before you trust a number

1. **What did the number come from**: the artifact, or a scan of it?
2. **Could it be `0` because nothing was captured?** Ask for coverage.
3. **What is it an answer about?** Which capture, which inputs, which moment.
4. **Is the artifact current** by fingerprint, not by mtime?
5. **If two sources agree, are they actually independent?**
6. **Has this instrument been checked against a known answer?**
7. **Against a known NEGATIVE, an EMPTY input and a TRUNCATED one?**
8. **Did anything WRITE?** Then read the diff.
9. **Has the CHECK been shown to fail?** Break the code and require the named case
   to notice.

## Project specifics

The artifact registry and domain notes live in `references/`:

- `references/rimworld.md`: the RimWorld def dump, `.rws` savegames, `Player.log`,
  world CSVs and .NET assemblies, what each encoding does to a scanner, and which
  tool answers instead.

Adding an artifact class to the registry: recipe in `references/building.md`, so
the instrument and the guard rail learn about it at once.
