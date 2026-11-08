---
name: review-sheets
description: Use when a human must keep/cut, rank, grade or assign dozens to hundreds of items (sprites, defs, rows, files); when handing over an HTML page to WORK in; when decisions must outlive chat as data; when a generated page is unusable; or when a decisions file may hold agent guesses.
---

# Sheets a human can actually decide with

**The agent decides, the human disagrees.** Hundreds of calls cannot happen in chat, and a wall of
prose hides what the human is agreeing to. The contract is: **generate -> validate -> serve -> review ->
freeze**, then consume only what a human ruled.

## 1. Generate. Do not hand-roll the page.

```bash
cp assets/sheet_template.html mysheet.html     # a COMPLETE sheet. Fill in two JSON blocks.
python3 make_prefill.py                        # your generator: writes decisions.json
python3 assets/check_sheet.py mysheet.html --decisions decisions.json   # the gate
python3 assets/serve_sheet.py --sheet mysheet.html --decisions decisions.json   # the delivery
```

Fill in exactly `<script id="CONFIG">` (brief, posture, criterion, invented, options) and
`<script id="ITEMS">` (rows), plus an optional `window.itemBody` renderer. Never write the chrome
yourself; rebuilt pages drop a required piece every time.

🔴 **The optional `<script id="RENDER">` hook ships INSIDE an HTML comment.** Filled in place it
stays inert text and the sheet silently shows only the default row. Put a live `<script>` outside
the comment.

**Pre-fill every row** against the project's brief. A blank sheet is a chore handed back.

- State the brief IN the page; the sheet outlives the conversation.
- 🔴 **Flag every rule you invented** in `CONFIG.invented` (required; `[]` on purpose, never by
  omission). An invented premise presented as a finding is this format's most expensive mistake.
- Mark contested calls with their own marker and filter. Leave genuinely open calls undecided on
  purpose, with a note saying why.
- **Each row says what the item DOES**, under ~20 words, mined from the data
  ("halves plants, doubles junk, blocks siege raids"), not what it is. Prefix inferences and give
  them a filter. "No mechanical effect, appearance only" is a real answer. For an image the
  picture is the consequence.
- A measured value (size, count) prints its SOURCE; verify one row against the raw data before
  serving a batch.
- Name your sort criterion in one line (`CONFIG.criterion`), including what it cannot rank: a
  metric ranks quality, never worth.
- Make the note field the most inviting control. Never make the sheet nag for a reason.
- Make the list tractable: show which items actually occur, group by source (not alphabet),
  bulk actions per group, filters, search over the effect line.

Read **`references/content.md`** when mining effect lines or sizes from raw defs/XML, choosing a
criterion, or adding any marker or badge (count it against real rows first). Read
**`references/throughput.md`** past a few hundred rows (keyboard, undo, grid mode).

**Things with a real size** (sprites in cells, tiles, parts in mm, UI in px): show each at true
scale beside a reference figure, on its real background. One row field does it:

```json
"trueSize": {"w": 1.5, "h": 1.5, "unit": "cell", "source": "where the size was measured",
             "pxPerUnit": 64, "bg": "#5d4c3e", "img": "optional (default: the thumb)",
             "ref": {"label": "person", "w": 1, "h": 1.8, "img": "optional"}}
```

or `"trueSize": {"none": "why this row has no real size"}`. Set `CONFIG.trueSize: "required"`
whenever pictures have real sizes; the gate then FAILs any picture row without an entry.

**Posture is explicit, in the page AND in the decisions file** (`"posture": "whitelist"`). A
sparse file otherwise cannot tell "strip these few" from "keep only these few". Show a live
counter of both sides (options carry `"counts": "in"|"out"`), and keep **rejected** (looked, said
no) distinct from **undecided** (never looked).

⛔ **Never remove an option from a control to enforce policy.** Grey it, badge its cost, sort it
last. The picker is the human's.

**The generator writes `reviewStatus` at birth** (see §5): `state="prefill"`, never `"ruled"`,
never omitted.

A project may layer a stricter `<domain>-review-sheets` overlay on this skill; where stricter, it
wins.

More traps for this section: [references/traps.md](references/traps.md) § 1. Generate. Do not hand-roll the page..

## 2. Validate

⛔ **`check_sheet.py` must exit 0 before handover.** Zero FAILs, not "warnings I judged fine";
read the warnings out loud. `assets/test_check_sheet.py` and `assets/test_review_2026_10_15.py`
prove the gate and the sidecar bite.

⭐ **Then serve it, click one control of each kind in a real browser, and read the console.**
Enabled-and-inert passes every scripted check. Check the whole consequence: on disk, on the row,
in the header count, after a reload, and that any error banner came down after a successful retry.
Details: **`references/chrome-and-layout.md`** (also: what the chrome must do).

🔴 **Before any sheet that asks the human for ground truth, run the row audit (a
sheet once shipped with duplicate pairs and rows already done; the gate passed, because
the gate checks the page, not the rows).** Do all four, mechanically, and tell the human the counts:

1. **Duplicates.** Group rows by normalized title AND by event (same thing reported many times);
   keep one per group, or none if the repeat IS the test. Re-run after any edit.
2. **Already done or dropped.** For every row, look up what the system already knows (closure
   evidence, ticket status, a completion mail, a tracker state, a thread reply you can see). A row
   with such evidence is not a question; settle it yourself and, if you are unsure the evidence is
   right, ask the ONE question "I think this is done, is it?" rather than the open question.
3. **Whose is it.** Drop rows that belong to the agent or to someone else (an engineering ticket the
   agent filed under the owner's name is not the owner's to-do).
4. **Controls that can fail.** A repeat row must not sit on a title that is already duplicated, or it
   tests nothing. Pick repeats from rows that survived steps 1 to 3.

The gate (`check_sheet.py`) cannot do this for you and a green gate says nothing about it.

⭐ **Then read it yourself before the human does.** Look at every row you can judge — or have a naive judge do it
(a fresh agent that did not make the sheet) — and fix or drop what is obviously broken: does not render, is not
recognisable as what it is, contradicts itself or the brief, repeats something already ruled. Tell them in one line
what was caught. If their first comment is something you could have seen, the sheet was not ready. (A project may
enforce this with a record its serve tool checks — for example a `prereview.py` record.)

More traps for this section: [references/traps.md](references/traps.md) § 2. Validate.

## 3. Serve. Serving IS the delivery.

🔴 **Run `assets/serve_sheet.py` every time; it is the standing default.** It opens the human's browser on
a tokened URL; that URL is the delivery. Never hand over a file path, a path to paste, or a picker.
The `file://` fallback is only for a machine where a sidecar genuinely cannot run, and you say so
out loud. `localStorage` is not storage: per-browser, wiped by clearing data, and shared across
every `file://` page on the machine.

🔴 **Never restart a sidecar after handing over its URL.** The port is part of the origin, so a
restart orphans their tab and strands whatever is in that origin's `localStorage`. To recover,
re-bind the exact same port with `--no-token`; do not tell them to reopen the sheet.

The sidecar merges per row, carries unknown keys through, refuses truncating writes (409),
refuses frozen files (423), stamps `savedBy`/`savedAt`/`writeCount`, and holds a cross-process
lock so two sidecars, or a sidecar and `merge_artifact_db.py`, cannot lose each other's rows.
Always show link state and last-write time. Protocol, fallback and picker options:
**`references/persistence.md`**. macOS and WSL-with-Windows-browser: **`references/cross-platform.md`**.

**Remote (claude.ai artifact) sittings, optional:** only if you publish the sheet as a claude.ai
artifact whose storage writes one db document per touched row (input schema in
`assets/merge_artifact_db.py`). Dump that db with the artifact's own `read_db out_dir`, then
`python3 assets/merge_artifact_db.py --dump DIR --decisions FILE` (report) and `--apply` (write).
It refuses an empty dump, duplicate rowIds and a frozen file.

⚠️ **If a decision spawns an artifact, build the read side in the same change.** The row shows a
state ("drafted", with a way to open it) or says where the result landed. A persisted request with
an invisible result looks lost.

More traps for this section: [references/traps.md](references/traps.md) § 3. Serve. Serving IS the delivery..

## 4. Review: prove the sheet actually wrote

⚠️ **"They said they finished" is not evidence the file changed.** Before consuming a decisions file:

```bash
python3 assets/serve_sheet.py --decisions decisions.json --status

More traps for this section: [references/traps.md](references/traps.md) § 4. Review: prove the sheet actually wrote.
# "touchedBySheet": false  ->  still the pre-fill. Nothing landed.
```

1. ⭐ A key only the plumbing writes (`savedBy`, `writeCount`, `savedAt`). The consumer refuses
   to run if absent.
2. `git diff` the decisions file. No diff means no review landed.
3. Compare decision counts with the pre-fill. Identical totals are suspicious.

If nothing landed, the work is usually still in `localStorage`. Hand back this recovery:

> *Reopen the sheet from the same browser profile. In the brief, next to **"Not saving to a
> file"**, click **copy JSON**; that is the whole decisions doc; paste it over the decisions
> file.* (If the clipboard is blocked, the JSON appears in a box below the button.)

🔴 **Never hand back a recovery you have not clicked yourself.**

Read overrides as a group (`--overrides`) before acting on any, and report the override rate
honestly: zero overrides looks the same whether the criterion was right or disagreeing was too
hard.

## 5. "Touched" is not "ruled": `reviewStatus`

A written-to file could be a real review or an agent smoke-testing the wiring. Every sidecar
carries one key:

```json
"reviewStatus": {
    "state":    "ruled" | "prefill" | "unknown",
    "by":       "<who ruled — a name, or null>",
    "at":       "<ISO 8601 date/datetime, or null>",
    "evidence": "<one line: which fact makes this true>"
}
```

- Whoever records a real ruling (sidecar session, a transcribed verbal ruling, a freeze) sets
  `"ruled"` and fills `by`/`at`/`evidence`. A blanket ruling counts, but say so in `evidence` and
  stamp the route it took (for example the script that applied it), never as a row-by-row sitting.
- ⛔ **Never infer `"ruled"` from row content**: an all-keep ruling and an unopened pre-fill are
  byte-identical. Ambiguous provenance is `"unknown"`, with why.
- No `reviewStatus` key at all = UNREVIEWED.

Every consumer reads it through `assets/review_status.py`. It **returns** `"prefill"` and
**raises** on unknown, so the consumer must also check the returned value:

```python
from review_status import get_review_status, UnreviewedSheetError
try:
    state = get_review_status("Transient/some_sheet.decisions.json")   # "ruled" | "prefill"
except UnreviewedSheetError:
    state = None
if state != "ruled":
    ...refuse. Do not treat this sheet's rows as decisions...
```

`check_sheet.py` WARNs (not yet FAILs) when `reviewStatus` is missing or malformed.

## 6. Freeze, and make the freeze real

When the human says they are done:

- Commit their decisions file as the source of truth.
- Write `"frozen": true` with `frozenOn` and `frozenMeaning`. The sidecar and the merger then
  refuse every write and the sheet goes read-only. In `file://` mode the page re-reads the file
  before each write, so a freeze applied mid-session bites on the next keystroke.
- 🔴 **Make the generator that produced your guesses refuse to run** unless given
  `--i-know-this-overwrites-the-owners-decisions`, gated on a key only the sheet writes
  (`demo/make_demo.py` does this). A "do not run" comment is not a guard.
- ⭐ **Separate the two generators.** Regenerating the SHEET stays safe (it renders from the
  decisions file); only the DECISION generator is locked.
- ⚠️ Name what freezing costs: under whitelist posture, undecided rows are stripped.

More traps for this section: [references/traps.md](references/traps.md) § 6. Freeze, and make the freeze real.

## What to ask the human

Ask for the posture before generating, a ruling on invented rules, and what the decision will
drive (so you know whether "undecided" is safe). Do NOT ask the routine calls.

🔴 **Ask only for judgments this person can make from available evidence or their own authority
(owner, 2026-10-26; reviewed by GPT the same day).** The agent needing a label does not make the
human able to supply it. Routine calls stay with the agent.

Before building, record this contract briefly for each question type, and check every row
against it:

1. **Purpose and meaning.** State what decision the answer changes. Define the criterion, whose
   perspective and which time, in plain language. Ask for an observable judgment, preference or
   ruling; translate internal scores and invented categories into that. Never substitute a
   visible proxy for the fact you need.
2. **Respondent and evidence.** Name who can answer and what establishes the answer. Do not assume
   old events are remembered. Fetch missing evidence yourself; otherwise narrow the question, find
   another source, or drop it.
3. **Sufficient display.** Show the real item and all essential context (both sides of a
   comparison, chronology, attachments). Optional detail goes behind expansion. Ids name items;
   they are never the evidence. Check this on the rendered sheet without leaning on your own
   private context.
4. **Cheap, honest responses.** A few clear choices, or comparison or correction when easier. No
   false premises or overlapping options. Offer "can't tell", and "not applicable" or "skip for
   now" where needed; never require an explanation. Keep abstention distinct from a label and from
   an untouched row, and state each one's downstream treatment (including at freeze) before
   review. Keep agent guesses apart from human rulings; hide the guess when you need an
   independent judgment, show it when you only need approval.
5. **Bounded workload.** State scope, estimated time and stopping policy. Put consequential,
   answerable questions first, with variety; group equivalent cases for one explicitly scoped
   ruling. Stopping and resuming are always allowed. Stop at the agreed limit, when another answer
   would not change the decision, or when the questions need redesign, not merely when your
   confidence rises.
6. **Appropriate checks.** Use known-answer rows only where the answer is independently supported
   under the same criterion, and disclose them. Repeats test consistency, not truth. Investigate a
   disagreement before blaming the reviewer. Report what the answers changed.

If a row fails, fix its evidence or wording, route it elsewhere, or omit it and say what you will
do without it. Repeated "can't tell" means redesign. At handover state in one line what the person
is deciding, why they can decide it, and what their answers will change.

## Handover checklist

Do not say the sheet is ready until every line is true.

- [ ] `check_sheet.py` exits **0**.
- [ ] The row audit ran (duplicates, already-done, not-theirs, controls) and the counts were stated to the human.
- [ ] You (or a naive judge) looked at every row and fixed or dropped what was broken; they get one line of what
      was caught.
- [ ] Every row is pre-filled, or deliberately undecided with a note saying why.
- [ ] Picture rows with a real size carry `trueSize`, and `CONFIG.trueSize` is `"required"`.
- [ ] `CONFIG.invented` is set, to a real list or to `[]` on purpose.
- [ ] `CONFIG.criterion` names what you sorted by, including what it cannot rank.
- [ ] Posture is in the page **and** in the decisions file.
- [ ] The decisions file carries `reviewStatus` with `state="prefill"`.
- [ ] The sidecar is running and their browser is open on the tokened URL.
- [ ] You said in chat how many rows you decided and which you are least sure of.
- [ ] Every question passes the gate in "What to ask the human"; the brief states the judgment,
      evidence, downstream use, workload and stopping policy.
- [ ] Rendered rows were checked for sufficient evidence without relying on the maker's context.
- [ ] Guesses, human rulings, abstentions and untouched rows stay distinguishable; any blanket
      ruling has a stated scope; the treatment of abstentions and unfinished rows at freeze is
      explicit.
- [ ] Any known-answer rows have defensible provenance and are disclosed.
- [ ] You have **not** asked them to paste a path, retype a filename, or hunt for a folder.
- [ ] You clicked one control of each kind in a real browser and read the console.
- [ ] Every marker was counted against the real data first; none sits on most rows.
- [ ] Any action that produces an artifact can be read back onto the row, or the row says where
      it went.

## Red flags

| Thought | Reality |
|---|---|
| "This sheet is small, I'll build the page from scratch" | That is how the fold toggle goes missing. Copy the template. |
| "check_sheet's warnings are fine" | FAILs block. Read warnings out loud. |
| "They said they're done, so I'll commit the file" | Check `touchedBySheet` first. |
| "`get_review_status` didn't raise, so it's ruled" | It returns `"prefill"` without raising. Check `== "ruled"`. |
| "Zero overrides means I got the criterion right" | It equally means disagreeing was too hard. |
| "I'll hand them the file path to open" | Serving is the delivery. A path is the last resort, said out loud. |
| "I need this label, so I'll ask for it" | State what evidence lets this person answer and what their answer changes. Pass the gate in "What to ask the human" or redesign the question. |
| "I'll pre-fill nothing so I don't bias them" | A blank sheet is a chore handed back. |
| "The metric ranked these, so the order is the answer" | A metric ranks quality, not worth. |
| "The tests pass / the button is enabled, so it works" | Neither runs the handler. Click one, read the console. |
| "It saved, so the row is correct" | Check row, header count and reload too. |
| "This glyph is useful, I'll add it" | Count it first. On most rows it is wallpaper. |
