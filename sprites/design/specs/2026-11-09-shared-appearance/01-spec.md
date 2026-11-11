# Sharing Sprite appearance across machines

Written 2026-11-09 on the Work Desktop (`mt-BBBBBB`) by Claude Opus 5.
Ticket: `MANDRAKEWORKFLOWS_SHARE_SPRITE_LOOKS_GEMMA_WRITES_IT`.
Measurement ticket: `DISPATCH_PROVE_TOKEN_FREE_BUILD_ONE_PROMPT_PAID_FOR`.

🔴 **This spec is an input to a token-free generation experiment.** The implementation is written by
`gemma-4-31b-it-8bit` running its own loop with no Anthropic model in the loop. This document and
the acceptance tests are the only Anthropic-authored artifacts. Do not "helpfully" implement the
code described here by hand: doing so destroys the measurement. If you are a Claude session reading
this before the run has been scored, read `../../../../../Dispatch/tickets/DISPATCH_PROVE_TOKEN_FREE_BUILD_ONE_PROMPT_PAID_FOR.md`
first.

---

## 1. The problem

The same agent looks like a different creature on the Desktop and the Laptop.

Sprites stores a project's appearance in two files under `~/agent-storage/sprites/config/`:

| file | holds | syncs today? |
|---|---|---|
| `cast.json` | per-project `{concept, iv, hex, short, visibility}` — species, symbol variant, colour, short-name override, hide flag | **no** |
| `behaviors.json` | ~30 global universe sliders (density, temperature, drift, stirring, …) | **no** |

Neither syncs, because `~/agent-storage` is deliberately **not** a git repo (owner's agent-storage
rule, 2026-10-19: agent-made non-repo state lives there and nowhere else).

Two appearance settings *already* share, by a different route: **per-project colour and Focus** live
in Waypoint's `launches.md` (colour as the `]10;#RRGGBB` marker inside the launch Command, Focus as
its own column), and Waypoint's data directory is a symlink into `~/dev/private-store/waypoint/`,
which Lodestar's hourly sweep pulls and pushes. `Config.swift` already carries the
Waypoint-present / Waypoint-absent switch those two settings need, and `projects.js`'s `mergeLocal`
already implements the merge for them.

So the architecture is settled. What is missing is a home for the settings that are *not* colour or
Focus.

## 2. Owner's rulings (question card, 2026-11-09)

| question | ruling |
|---|---|
| Where does the shared copy live? | **A new JSON file in Waypoint's data folder.** |
| What becomes shared? | Per-project **species and symbol**, per-project **colour**, and the **universe sliders**. |
| Conflict resolution? | **Last writer wins, via the hourly sweep.** No machine-override rows. |
| No Waypoint / no Lodestar? | Nothing changes; local settings prevail (owner's original brief). |

### Two judgments recorded against those rulings

**Colour is not migrated.** The owner asked for colour to be shared; it already is. `launches.md`'s
hex has two independent consumers — the shell launch command that sets the iTerm2 foreground, and
Lodestar's `colorboard.py` — so moving it would break things outside Sprites for no new capability.
The shared file therefore **may override** a project's colour, and `launches.md` remains the
fallback. Nothing currently working is moved. This satisfies the ruling's intent (colour is
shareable from one place) without touching a live path.

**The sliders are display-dependent.** `density`, `particleSize`, `brightness` and the thermal
fields are tuned against a specific screen. Last-writer-wins will sometimes deliver a value that is
wrong on the receiving machine, and the owner chose that knowing it. No warning mechanism is in
scope; re-tuning is the remedy.

## 3. The store

**Path:** `$WAYPOINT_DATA/sprites.json`, else `~/.config/waypoint/sprites.json` — resolved exactly
as `Config.swift`'s `Paths.waypointData` already does, so a test can redirect it with one env var.

**Why there and not in `launches.md`:** a markdown table is a poor home for thirty floats, and
`launches.md` has consumers outside Sprites that must not learn a new column. A sibling JSON file in
the same synced folder gets the sync for free and keeps Sprites' data in Sprites' own shape.

**Why there and not in MandrakeWorkflows:** the owner picked Waypoint's folder. Noting the
consequence once, since it is not obvious: Waypoint's data lives in a **Lab-internal** repo scoped
`desktop,laptop`, so this shares Desktop↔Laptop and will never reach Archmagi. That matches the
stated problem ("across Waypoint-managed computers") exactly.

**Shape** (version 1):

```json
{
  "schema": "sprites.shared",
  "version": 1,
  "projects": {
    "orchard-mandrake": { "concept": "c6_night", "iv": 0, "hex": "#CB50F0" }
  },
  "behaviors": { "density": 100, "temperature": 27.5, "drift": "off" }
}
```

- Keys under `projects` are **canonical project keys** — Augur's `project_key`, which is the
  Lodestar registry `Id` (`projects.js` header documents this). Never a launch alias, never a
  display name.
- Only three per-project fields are shared: `concept` (species), `iv` (symbol variant), `hex`
  (colour). `short` and `visibility` stay local: they were not asked for, and `visibility` is a
  per-machine screen-clutter decision.
- `behaviors` is a flat subset of `behaviors.json`'s own keys, same names, same types.

## 4. What must be built

### Part one — the pure merge module (`app/shared.js`)

A UMD module in the style of `app/projects.js` and `app/behaviors.js` (an IIFE setting
`module.exports` when `module` exists, else `root.SpritesShared`), exporting three **pure**
functions. No file I/O, no `require` beyond what the existing modules use, no mutation of inputs.

```
mergeCast(localCast, shared, hasWaypoint) -> cast
mergeBehaviors(localBehaviors, shared, hasWaypoint) -> behaviors
setProject(shared, key, patch) -> shared
```

**`mergeCast(localCast, shared, hasWaypoint)`**

Returns the effective cast: the same shape as `cast.json`, `{projects: {key: {...}}}`.

- `hasWaypoint === false`, or `shared` is not a usable object → return a value deep-equal to
  `localCast` (normalised to `{projects:{}}` when `localCast` is absent or malformed). **This is the
  no-Waypoint guarantee and it is absolute.**
- Otherwise, for every key in `shared.projects`, overlay `concept`, `iv` and `hex` onto that key's
  local entry, creating the entry when the project has no local one.
- A project key present locally but absent from `shared` is **untouched**.
- Local `short` and `visibility` always survive: `shared` never carries them and must never clear
  them.
- **Per-field validation, never per-file.** One bad value is dropped and the rest of the file still
  applies. Valid: `concept` a non-empty string; `iv` an integer ≥ 0; `hex` matching
  `/^#[0-9a-f]{6}$/i`, normalised to uppercase. Anything else for that field → the local value
  stands.
- Inputs are not mutated.

**`mergeBehaviors(localBehaviors, shared, hasWaypoint)`**

- Same no-Waypoint guarantee: returns the local object's value unchanged.
- Otherwise overlay every key of `shared.behaviors` onto the local object, **but only where the
  local object already has that key and the types agree** (number over number, string over string,
  boolean over boolean). A shared key the local behaviours do not know is ignored; a type mismatch
  is ignored. This is the one place where being conservative matters: `behaviors.json` drives a live
  particle simulation, and a string where a float belongs is a crash, not a cosmetic bug.
- Inputs are not mutated.

**`setProject(shared, key, patch)`**

- Returns a NEW shared object with `patch`'s valid `concept` / `iv` / `hex` fields written under
  `projects[key]`, preserving every other key and field.
- Stamps `schema: "sprites.shared"` and `version: 1`, creating the envelope when `shared` is absent
  or malformed.
- Rejects a `key` that is not a plausible project key (`/^[a-z0-9][a-z0-9._-]*$/`, as
  `projects.js`'s `KEY_RE`) by returning the input's normalised form unchanged.
- Invalid field values in `patch` are dropped; valid ones alongside them still apply.
- Inputs are not mutated.

### Part two — the host wiring (Swift)

Smaller, but it is where the feature becomes real.

1. `Config.swift`: add `Paths.shared`, resolving `$WAYPOINT_DATA/sprites.json` else
   `~/.config/waypoint/sprites.json`, overridable by `$SPRITES_SHARED` for tests (the pattern
   `Paths.cast` and `Paths.projects` already use).
2. `App.swift`: load the shared file at startup and pass it through `mergeCast` / `mergeBehaviors`
   before the cast and behaviours reach the stage. Add a `FileWatch` on it (the class already
   exists) so a sweep that pulls a change from the other machine is picked up live, exactly as
   `cast.json` is.
3. `App.swift`'s `saveCast`: when Waypoint is present, a change to a project's `concept`, `iv` or
   `hex` is also written to the shared file through `setProject`, atomically (`writeAtomically`
   exists). When Waypoint is absent, nothing is written there.
4. `saveBehaviors`: when Waypoint is present, write the slider values into the shared file's
   `behaviors`.

The no-Waypoint path must remain byte-identical to today's behaviour.

## 5. The oracle

`tests/node/test_shared.js`, run by `node`, printing one `PASS <msg>` or `FAIL <msg>` line per
check and exiting non-zero if any failed — the house style of `tests/node/test_project_keys.js`. It
is registered in `tests/run_all.sh` beside the other node tests.

**A pass is: exit 0 AND every check printed PASS AND zero FAIL lines.** Exit status alone is not a
pass: a module that calls `process.exit(0)` satisfies a naive `rc==0` rule with zero assertions run.
This rule is stated here because the harness enforces it and the generating model is told it.

The test file is written **before** the run, is hash-guarded during it, and cannot be edited by the
model. Part two's wiring is covered by the existing `python3 -m pytest` suite plus a full
`tests/run_all.sh`; a pass there is required before anything lands.

It is registered in `tests/run_all.sh` **on the implementation branch, not on `main`** — adding it
to `main` before `app/shared.js` exists would leave the whole suite red for every other agent in the
tree.

### The oracle was watched refusing broken input [measured 2026-11-09]

A guard is untested until it has rejected something it should. Run in a scratch copy
(`~/agent-storage/scratch/sprites-shared-oracle-proof/`), with the test file byte-identical:

| input | node exit | PASS | FAIL | verdict under the full rule |
|---|---|---|---|---|
| `app/shared.js` absent | 1 | 0 | 0 | refused |
| `process.exit(0);` | **0** | 0 | 0 | **refused** — a naive `rc==0` rule would have passed it |
| `{mergeCast:a=>a, mergeBehaviors:a=>a, setProject:s=>s}` | 1 | 18 | 10 | refused |

The middle row is the one worth keeping: the broken rule and the correct rule disagree on exactly
that input, so the oracle has teeth.

The bottom row is a disclosure, not a reassurance. A do-nothing passthrough already banks **18 of
28** checks, because every no-Waypoint and no-mutation check is satisfied by returning the input
unchanged. The ten checks with real teeth are the overlay, the per-field validation, the uppercase
normalisation, the behaviours type-guard, and `setProject`. Read a score on this test as "10
meaningful checks plus 18 free ones", never as 28 independent ones.

## 6. Experiment protocol

- **Model:** `gemma-4-31b-it-8bit`. Chosen on the n=10 self-harness bakeoff that closed 2026-11-09:
  10/10, median 4 calls, 65 s median wall, 0 hints, 0 format rejects, 0 protocol errors — the best
  local self-harness arm measured (`Dispatch/docs/research/2026-11-09-all-local-orchestrator/SELF_VS_SCRIPTED.md`).
- **Harness:** full self-harness (`harness.py`). The model decides when to read, write, test, retry,
  ask for a hint and stop. Python keeps only the write whitelist, the SHA-256 guard on the test
  file, and the pass oracle. `declare_done` is verified, never trusted.
- **Serialisation:** oMLX serves one model at a time and loading another silently evicts the
  resident one — one measured call took 736 s against a ~110 s baseline from exactly this, and both
  calls succeed, so the contamination is invisible at the call site. This run waits for the n=10
  queue to finish and holds the server alone.
- **Staging:** part one first, on its own branch. Part two is a second arm. Reporting which half
  landed is a result, not a failure to report.
- **What gets recorded:** paid tokens for definition / spec / tests / monitoring / review, counted
  apart from the local run; local wall time and call count; every intervention with whose fault it
  was; and whether the branch compiles and passes the **full** suite. The 2026-11-08 precedent
  failed precisely there — 16 new tests green while the tree's full build was broken — so a green on
  `test_shared.js` alone is explicitly **not** a landing.

## 7. Out of scope

Machine-override rows (ruled out: last writer wins). Sharing `short` or `visibility`. Any change to
`launches.md`'s schema. Reaching Archmagi. Warning the owner when a shared slider is wrong for the
receiving screen.
