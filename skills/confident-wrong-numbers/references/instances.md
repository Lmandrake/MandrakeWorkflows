# Instances: queries whose shape returned a confident wrong number

Each entry gives the **generalized shape** first, then one concrete case. The
cases come from a RimWorld modding project (paths and def names are examples,
nothing more); the shapes are not specific to it. Sections mirror the table in
`SKILL.md`.

Contents:
1. [A line count as an entry count](#1-a-line-count-as-an-entry-count)
2. [An existence test as an identity test](#2-an-existence-test-as-an-identity-test)
3. [A fixed index as a field](#3-a-fixed-index-as-a-field)
4. [A pattern wider or narrower than the thing](#4-a-pattern-wider-or-narrower-than-the-thing)
5. [A key that does not exist](#5-a-key-that-does-not-exist)
6. [An error swallowed as empty](#6-an-error-swallowed-as-empty)
7. [A record read as the thing it records](#7-a-record-read-as-the-thing-it-records)
8. [A source read as the effective state](#8-a-source-read-as-the-effective-state)
9. [A scope that drifted](#9-a-scope-that-drifted)
10. [A proxy set as the population](#10-a-proxy-set-as-the-population)
11. [A text scan that ignores grammar](#11-a-text-scan-that-ignores-grammar)
12. [An uncalibrated zero](#12-an-uncalibrated-zero)
13. [Shared-premise agreement](#13-shared-premise-agreement)
14. [A formula copied without its inputs](#14-a-formula-copied-without-its-inputs)
15. [An acceptance window that cannot fail](#15-an-acceptance-window-that-cannot-fail)
16. [A single sample of a stochastic process](#16-a-single-sample-of-a-stochastic-process)
17. [Two displayed values, two sources](#17-two-displayed-values-two-sources)
18. [A membership test as a cardinality test](#18-a-membership-test-as-a-cardinality-test)
19. [A truthiness default as a presence default](#19-a-truthiness-default-as-a-presence-default)
20. [A conclusion printed unconditionally beside its evidence](#20-a-conclusion-printed-unconditionally-beside-its-evidence)

---

## 1. A line count as an entry count

**Shape.** `grep -c` and `wc -l` count *lines*. Any file that puts several
records on one line, or one record across several lines, makes the line count
and the record count unrelated. The output is an integer either way.

- **Config with many elements per line.** `grep -c '<li>' ModsConfig.xml`
  returned **48**; parsing the XML and counting `activeMods` children returned
  **631**. The file writes many `<li>` on one line. Caught only because the
  owner pushed back on a finding built on it.
- **Log with many lines per record.** `grep -c` on a game log counted a
  30-line stack trace as 30 errors. The honest figure was 245 distinct / 329
  occurrences, from a tool that understands the log's record boundaries.

**Honest instrument:** a parser for the format. For XML that is
`ET.parse(p).find("activeMods")` and `len(...)`; for a log it is whatever tool
knows where one error ends and the next begins.

## 2. An existence test as an identity test

**Shape.** "Does the path exist" and "is the thing there" are different
questions. A path can exist and be hollow; a path can be wrong and the shell
will answer `0` rather than error.

- **`ls <dir> | wc -l` on a directory that does not exist prints `0`.** An
  agent counted `artpipe/queue/` — which does not exist — and told the owner
  the job queue was empty. The real directory was `artpipe/pending/` and held
  **182** jobs. `ls` wrote its error to stderr; `wc` counted zero lines of
  stdout; the pipeline printed `0` and nothing else.
- **`[ -e src/RimMandrake/Pits ]` passed** while the folder held only
  `__pycache__`. The mod had been merged away weeks earlier; a validation
  checklist stayed "VALIDATED, 12 binding bars" against nothing.
- **A database file at the expected path was 0 bytes.** The real dump lived
  elsewhere. Every instrument pointed at the repo path read an empty database
  and reported everything absent.

**Honest instrument:** test the file that *identifies* the thing
(`dir/About/About.xml`, a manifest, a non-empty size), or glob a pattern that
fails loudly on a bad path (`ls dir/*.json` errors; `ls dir | wc -l` does not).
Before repeating a `0` from a listing, list the parent and confirm the child is
spelled as you think.

## 3. A fixed index as a field

**Shape.** Reading position N assumes every record keeps the field at N. The one
record that does not is the one that matters, and the query cannot tell you it
skipped it.

- **`subject:` read from line 2.** 77 walk files carry it on line 2;
  `AtmosphericBase.md` carries it on line 3. A sweep reading line 2 reported
  zero failures across 78 files while missing the only broken one.
- **`glob("*south*")[0]`.** Filesystem order decided whether the first hit was
  the art or the colour mask. See also §4.
- **An id read as an index.** A savegame grid stores a feature's *uniqueID*
  (21..92); a renderer read it as an index into the features list. Every region
  got a plausible tile count and every one was wrong. An id-vs-index confusion
  never errors; it renames everything.

**Honest instrument:** read by key. The first line *matching* `subject:`; the
entry whose id *equals* N; the column by its header name.

## 4. A pattern wider or narrower than the thing

**Shape.** The glob or regex has its own population. Where it is wider than
yours, it counts things you did not mean; where it is narrower, it misses forms
you did not think of. Both produce a clean integer.

- **Wider: `*south*` also matches `_southm.png`**, the colour mask, which is
  saturated across ~99% of its pixels by convention. A "does this head carry
  baked colour" check therefore depended on which file globbed first, and
  inverted 4 of 7 decisions. Tell: male and female variants of the same species
  reading 253 vs 0 on structurally identical files.
- **Wider: `alpha > 0` as a bounding box.** A sub-visible export halo (alpha
  1–16, under 6% opacity) extended a sprite's box 80 px past its painted body,
  producing two false "clean" verdicts. Threshold at a level a viewer can see.
- **Wider: bare names as "stale".** A scan for donor-mod names in a roster
  reported **182** stale rows; the real figure was **32**. The other 150 were
  bare Star Wars names that resolved fine against an *active* donor.
- **Narrower: a backtick-only regex.** A subject packageId was backticked in
  28 files, bare in 34, absent in 16. The regex read `None` for 50 of 78.
- **Narrower: text-matching an XML tag instead of parsing it.** A review sheet
  read a donor def by matching `<ThingDef>…</ThingDef>` as text; the donor put
  `<descriptionHyperlinks><ThingDef>…</ThingDef></descriptionHyperlinks>`
  *before* the real `<plant>` block, so the match truncated early and 11 of 13
  rows read a size field as ABSENT, recording the vanilla fallback AS a
  measurement. The tell: the only 2 rows without `descriptionHyperlinks` were
  the only 2 correct ones.

**Honest instrument:** print what the pattern matched on a sample and look at
it; run it against a known positive *and* a known negative before trusting
the count. Measure `_south.png` alone, not `*south*`. Parse XML with a parser,
never a tag-shaped regex.

## 5. A key that does not exist

**Shape.** A lookup on a key the object does not have returns the same nothing
for every record. The uniformity is the tell — a real population is rarely all
zero — but uniformity in the alarming direction reads as a catastrophe rather
than a bug.

- **`getattr(dict, "must_show")`.** `northstar.parse()` returns a dict, so
  `getattr` yielded `None`, `len()` yielded `0`, and all four VALIDATED
  checklists read as "0 bars". Use `w["must_show"]`.
- **`<def>` where the schema says `<defName>`.** Counting light fixtures in a
  ship layout export by `<def>` elements returned **0**; the real answer was 11
  of 2002.
- **`row["defName"]` where the API returns `def`.** A census over a live tool's
  output read every record as nameless.
- **`defName`/`defType` where the SQL columns are `def_name`/`def_type`.** See
  §6 for what happened to the error.
- **A tool leaf that does not exist, or a parameter named wrong.**
  `jawa/pawn_detail` (no such tool) and `pawnId` (the parameter is `pawn`)
  each produced "0 of N carry the trait".

**Honest instrument:** discover the vocabulary before counting — print one
record whole, read the schema, read the tool's own inputSchema. Treat an
all-`None`/all-`0` result as a key mismatch until a known positive comes back
non-zero.

## 6. An error swallowed as empty

**Shape.** The query fails, prints its failure on stdout or stderr, and the
next stage counts rows in that output. Zero rows. The failure has become a
measurement.

- **Wrong column name → error line → "0 of 109".** The SQL query errored; the
  script grepped its output for result rows, found none, and reported a
  confident zero.
- **A nonexistent tool → empty response → "0 of N".** (§5.) No error was
  surfaced to the sentence that carried the number.

**Honest instrument:** check the exit status and the error channel *before*
interpreting an empty result. In a script, an empty result on a query that
should return something is a failure, not a finding.

## 7. A record read as the thing it records

**Shape.** An export, snapshot, index or config describes the world at the
moment it was written. Reading it later as the world *now* is a query on the
wrong object; the numbers are exact and stale.

- **A tiles CSV exported from a savegame** was read for a live tile count. A
  bridge edit after the export date was invisible to it; the live system said
  222 tiles on one biome, the CSV still said 222 on the donor.
- **A plant pool CSV (an August snapshot)** was used to count dead-temperature
  flora: 46 claimed, 6 real against the current dump.
- **A config file's mtime** was read as evidence of what a running process had
  loaded. A restore had copied the backup back with metadata preserved, so live
  and backup were byte-identical and shared the pre-swap mtime. A crash on a
  19-mod tier was filed as a 618-mod production crash.
- **An index table graded `canon` on rows the entries themselves contradicted,**
  and mapped a sprite to the wrong entry entirely. When the entry and the index
  disagree, suspect the index.

**Honest instrument:** the live system, named as such in the report — the
running process's own "loaded with mods:" line, a live read through the bridge,
the entry rather than the index. A record is evidence about its own export
date; say which direction the evidence runs.

## 8. A source read as the effective state

**Shape.** The file you can read is one input to a pipeline. Patches, padding,
overrides and load order add to it. A source read is a lower bound, and the
asymmetry matters: presence in the source is safe to assert, absence is not.

- **A biome's `wildAnimals` list** read from the def alone showed 13 animals
  and "no big silhouette". A patch layer added 12 more, 7 of them large, and
  each animal's own `wildBiomes` field added load-time padding on top. The
  authoritative instrument reads a post-patch dump.
- **A `--check` that compares roster vs. a hardcoded dict** never looked at
  the hand-authored base XML the generator overwrites at load, so a def cut at
  the design layer sat live and stale while the check reported clean — four
  times in one session across independent agents.
- **A validator run without `--defs`** saw only the current mod's `Textures/`
  and reported "missing texture" for art a *later* mod supplies. Re-adding the
  "missing" art then silently reverted the other mod's verified-live art.

**Honest instrument:** the resolved view — the running process, a post-load
dump, the validator with its full input set. When only the source is
reachable, report the number as a lower bound and say so.

## 9. A scope that drifted

**Shape.** The instrument answers about a scope other than the one in your
sentence — a different map, a narrower directory, a default that was never
widened, a default that was widened on a guess.

- **A census tool read `Find.CurrentMap`**, so after any map switch or cull it
  silently reported the wrong map.
- **`ls artpipe/queue/`** instead of `artpipe/pending/` (§2) is a scope error
  as much as an existence one.
- **An audit's `marineChecked` scope defaulted to `['Coast']`;** widening it on
  a guess flagged 313 unrelated placements and an agent auto-removed 50.
- **A whole-document substring count instead of the one key path that means
  it.** Counting every `BMT_`-prefixed string anywhere in a roster JSON
  produced "27 unreconciled names" and a filed item; every one of those
  strings actually lived under `.evictions[].def` — an array of
  ALREADY-DISPOSITIONED records, not live gaps — and the real count of
  unreconciled names was zero. Count the live collection by its key path,
  never the whole document.

**Honest instrument:** put the scope in the report — "on map X", "under
directory Y", "with scope Z". If a tool has a scope parameter, name the value
you used, and run it at its default before widening.

## 10. A proxy set as the population

**Shape.** A small set built for one purpose (a smoke test, a spot check) is
later used as an operand as though it were the whole population.

- **A build script's `GM_TOOLS`** was a 2-name check that the `#if` had fired
  at all. A selftest subtracted it as if it were the entire gated tool set, so
  a healthy 284/284 build read as "41 tools missing".

**Honest instrument:** count the population directly. A set built to answer
"did this happen at all" cannot answer "how many".

## 11. A text scan that ignores grammar

**Shape.** The consumer of a file has a grammar — it skips comments, joins
continuation lines, resolves inheritance. A scan that does not honour the same
grammar counts tokens the consumer never sees, or misses ones it assembles.

- **A naming lint counted defNames inside XML comments.** Five false positives
  survived a clean pass.
- **`[Tool(` and its name string sit on separate lines** in one codebase's
  style; a line-by-line scan of the gated region returned a false 0. Match the
  region as text.

**Honest instrument:** whatever the consumer does, do that — strip comments,
parse, or match across lines. If the consumer is a parser, use the parser.

## 12. An uncalibrated zero

**Shape.** The instrument cannot see the kind of thing you asked about, or was
pointed at a case that cannot produce a positive. Its zero is a statement about
its blind spot, not about the world.

- **"No fire started" on bare sand.** The fire instrument gates on
  flammability; sand cannot burn. Validate on a wood stack first.
- **A cell-info call returned empty `things[]`** on cells occupied by a
  building and items. The grav engine was invisible to it; a different tool
  with defName + rect was the existence instrument.
- **A texPath scan over `ThingDef` alone** reported "no art" for 79 of 84
  ported animals. Animal art hangs off `PawnKindDef.lifeStages`. The
  alarming-direction figure was believed for a while.

**Honest instrument:** before trusting a zero, run the same query on a case
you already know is non-zero. If it cannot find the known positive, its zero
means nothing.

## 13. Shared-premise agreement

**Shape.** Two measurements agree; both were built on the same wrong premise.
Agreement is corroboration only when the instruments differ in *shape*.

- Two passes counting `<li>` lines agree on 48. Two reads of the same CSV
  agree on 222. A re-run of the same `getattr` agrees on 0. None of these
  is a second measurement.

**Honest instrument:** a cross-measure changes the shape — parse instead of
scan, live instead of record, one record printed whole instead of a field
extracted from all. If you cannot name what premise the second instrument
does *not* share with the first, it is the same instrument.

## 14. A formula copied without its inputs

**Shape.** Copying a reference's formula is not the same as reproducing the
reference's result — the formula only delivers the same output on the same
distribution of inputs it was tuned against.

- **`maxDrawSizeInTiles = inradius * 2.4`**, lifted literally from vanilla,
  left 48 of 71 labels sitting at the curve floor and inverted the size
  order — an 818-tile region outranked a 2,051-tile one — because the
  inradii this project's regions actually produce are not what vanilla's own
  routine would have produced them from.

**Honest instrument:** check that the borrowed formula delivers the RULING
(the ranking, the spread, the floor/ceiling behaviour it was chosen for) on
your actual inputs before shipping it, not just that the expression matches
the source.

## 15. An acceptance window that cannot fail

**Shape.** A bar written as "wait N ticks, then require condition C" is
unfalsifiable if C can flip back to false before N — the wait outlives the
window it is meant to observe, so a genuine success reads as failure.

- **`waitTicks=600, require lastCastTickAdvanced AND onCooldown`** on an
  ability that warms up in ~460 ticks and cools down in 240: by tick 600 the
  cooldown had already finished, so `onCooldown:false` read for a cast that
  had demonstrably fired.

**Honest instrument:** binary-search the wait against the mechanism's own
timing, or assert on the transition (cooldown went true, then false) rather
than a fixed-delay snapshot.

## 16. A single sample of a stochastic process

**Shape.** A generator or spawner that is only PROBABLY correct produces a
different result each time it runs. Reading one placement as a census over-
or under-counts by however much the process varies.

- **KCSG pawn symbols:** the spawned pawn's kindDef is not reliably the
  symbol's declared `pawnKindDef` — three placements of the same layout
  yielded 4/3/5 correct kinds out of 5, the rest arriving as vanilla
  Colonist/Baseliner on the exact symbol cell, no error logged. A
  per-defName census of one placement is stochastic; it can never prove a
  symbol absent.

**Honest instrument:** count the deterministic thing (the symbol cells in the
shipped layout XML), then place more than once before trusting a defName
census of the *spawned* result.

## 17. Two displayed values, two sources

**Shape.** A display draws two fields that are meant to represent one
quantity from two different underlying sources. They will eventually
disagree, and the disagreement tends to favour the more flattering direction
rather than a random one.

- **A statusline drew its progress bar from `used_percentage` and its printed
  number from `total_input_tokens`** (the last request's uncached input,
  ~7k against a 450k context) — overstating context headroom by roughly
  440k tokens.

**Honest instrument:** derive one displayed value from the other, never both
from separate sources that can drift apart.

## 18. A membership test as a cardinality test

**Shape.** A check asks "is each expected item present" and stops there. An
item that occurs the right number of times and an item that occurs twice both
answer "present" — the check cannot distinguish them, so repetition is
invisible to it no matter how the rest of the pipeline behaves.

- **A containment scorer over a document's parent/child structure** asked only
  whether each expected child appeared under its parent. A child block that had
  been attached to its parent TWICE — a fabricated duplicate edge — passed as
  "0 lost, 0 spurious", because presence was the only thing being asked.
  Comparing multisets instead of sets surfaced the duplication directly, as its
  own reported column rather than folded into a pass/fail.

**Honest instrument:** whenever the failure mode you are actually worried about
is repetition rather than absence, compare counts or multisets, never plain set
membership. See `grader-validation` when the check doing the counting is one
you built to grade your own work.

## 19. A truthiness default as a presence default

**Shape.** An "if missing, say so" default fires on more than absence. jq `//`
falls back on `false`, `null` (and errors/empty) but keeps `0` and `""`; Python
`or` falls back on every falsy value (`0`, `""`, `None`, `False`, empty containers);
JS `||` on `0`, `""`, `null`, `undefined`, `false`, `NaN`, while JS `??` falls back
only on `null`/`undefined`. A field whose legitimate value is one of those is
reported as missing. The query reads
as a presence check and answers a truthiness check, with a clean label either way.
The inversion is worst exactly when the falsy value is the thing being measured.

- **A boolean config flag read with jq's alternative operator.**
  `jq '.projects[$p].hasTrustDialogAccepted // "absent"'` over `~/.claude.json`
  printed **absent** for precisely the entries whose stored value was `false` —
  the value under investigation. Across five config backups this produced the
  finding "the key was never written, so the flag has never been recorded",
  when the key was present and `false` in every one of them. The same session's
  `has("hasTrustDialogAccepted")` count said **0 absent**, flatly contradicting
  it; the contradiction between two readings was the only reason the first was
  caught, and the wrong one had already been reported.

**Honest instrument:** `has("key")` for presence, and
`if has("k") then .k else "absent" end` when you want to distinguish absent from
`false`. Never `//` on a field that can legitimately be `false` (nor `or`/`||` on
one that can be `0` or `""`; use `??` or an explicit key test). A default that
triggers on falsiness cannot answer a question about existence.

## 20. A conclusion printed unconditionally beside its evidence

**Shape.** A command prints evidence, then a trailing `echo` says what the
evidence means. The `echo` is a separate command joined by `;` — it runs whether
or not the search matched, so the stated conclusion is independent of the result.
Readers quote the sentence, not the output above it, so a confident negative
survives even when the evidence directly refutes it.

- **A grep for callers with its own verdict appended.**
  `grep -rn "CLAUDE\.md" bin/ tools/ lib/ ; echo "(none above = no local tool
  writes CLAUDE.md)"` printed eighteen matching lines showing two scripts
  rendering that very file — with the sentence "no local
  tool writes CLAUDE.md" immediately beneath them. It was reported as fact and
  retracted a message later. Earlier in the same session the identical pattern had
  printed "(none above = no tool touches the trust store)" under output that
  happened to agree, so the habit had already been reinforced once by luck.

**Honest instrument:** let exit status carry the verdict, branching on all three
outcomes — `grep -q ... f; rc=$?; case $rc in 0) echo FOUND;; 1) echo NONE;; *) echo
"ERROR rc=$rc";; esac`. A two-way `if grep -q; then FOUND; else NONE; fi` is not
honest: grep exits 2 on a missing file or bad pattern and the `else` reports NONE.
Or print only the count
and draw the conclusion in prose afterwards, where it is visibly your inference
rather than apparently the command's output. A label that cannot vary with the
result is decoration, not measurement.
