# Observation contract (foreign work, build plan step 1, 2026-11-08)

What an observation of another Mac means, and when Sprites may conclude that something has stopped. Source:
`~/dev/MandrakeWorkflows/sprites/docs/design/2026-11-06-foreign-work/03-merged.md` ("Corrections",
"Build plan and gates", "Rulings"). Owner rulings it builds on (2026-11-08): **live view only**, so no durable store
and no store-ready schema work; build order contract, then D (local scan), then A (pull), then C (declared runs);
undeclared jobs drawn as **kind unknown**; scope is **the two Macs only** (`mt-BBBBBB`, `mt-AAAAAA`).

This step has **no collectors and no transport**. The contract is code that nothing feeds yet, plus fixtures:

| piece | path |
|---|---|
| reducer (the one reader of fetch outcomes) | `~/dev/MandrakeWorkflows/sprites/app/observe.js` |
| 1.3 additions as a schema (proposal for Augur) | `~/dev/MandrakeWorkflows/sprites/tests/fixtures/observation/contract.schema.json` |
| fixtures: a 1.3 Desktop, a 1.2 Laptop | `~/dev/MandrakeWorkflows/sprites/tests/fixtures/observation/` |
| contract tests (acceptance 1, 2, 3, 5, 6) | `~/dev/MandrakeWorkflows/sprites/tests/node/test_observation_contract.js` |
| fixtures pass both schemas | `~/dev/MandrakeWorkflows/sprites/tests/test_observation_fixtures.py` |
| unknown drawn on the stage | `~/dev/MandrakeWorkflows/sprites/tests/node/test_unknown_drawn.js` |

## The invariant

> **An object is removed only by a newer, authoritative observation that covers its scope and does not contain it.**
> Everything else (a failed fetch, a refused file, a failed or partial collector, a 1.2 producer, a restart still
> warming up) may only make it **unknown**, and an unknown object stays drawn, with its age, until the host answers.

Absence is not success: a removal is recorded as `absence_observed`, never as an exit status. Only a **terminal
record** written by the execution host (`exited` / `failed` / `interrupted`, optional `exit_code`) says how a run
ended, and a terminal record is final (a later non-terminal record does not revive it; an older one does not
overwrite it).

## One delivery, four failure classes

The transport (step A) hands the reducer one delivery per fetch: `{mono, outcome, reason, source_now, snapshot}`.

| class | when | effect |
|---|---|---|
| `connection` | no route, timeout, refused | every object of that host unknown; retry at the pull cadence, doubling to at most 120 s |
| `auth` | the key is refused | unknown; **backoff 300, 600, 1200, then 3600 s**: no rapid retry loop (acceptance 5) |
| `producer` | the file arrived but is unusable: unparseable, other schema or major, `off`, malformed, names another machine, has no source clock, or is past its own `valid_until` (its Augur is dead or asleep) | unknown; retry at the cadence |
| `collector` | the snapshot is fine but a collector's coverage is failed, stale, not published (1.2), or a scope is `partial`/`failed`/missing | only that collector's objects go unknown, with `why = collector:<reason>` or `scope:<status>` |

## Coverage, incarnation, sequence

- **Coverage** (1.3, top-level `coverage`): one stamp per foreign collector, `{observed_at, valid_until, scopes}`
  where `scopes` maps each scope it looked at (a tmux socket, a Docker socket, a model server, `*`) to `complete`,
  `partial` or `failed`; or `{observed_at, valid_until, unknown: <reason>}` with no scopes. Claude sessions use the
  existing `sessions_at` (1.1): `unknown` or past `valid_until` means the `[]` Augur publishes is unmeasured, not empty.
  **A 1.2 producer publishes no coverage, so no foreign scope is ever authoritative and nothing departs** (acceptance 2).
- **Incarnation** = `producer.pid @ producer.started_at`. A new one (a restart; `seq` drops) is accepted; a snapshot
  from an *older* start time is a replay and ignored.
- **Sequence**: within one incarnation a lower `seq` is a replay and ignored.
- **Newer**: a complete scope removes an object only if the collector's `observed_at` is later than the object's.
  A transport success carrying the same reading twice concludes nothing.

## Clocks: source-relative age

The receiver never compares its own wall clock with the producer's. The fetch reads the producer host's clock in the
same command (`source_now`); an object's age is `source_now - observed_at`, then advanced by the receiver's
**monotonic** clock. A 5 h skew changes no status and no age (tested). Freshness of the file is judged against
`source_now`, so a skewed receiver cannot call a live file stale or a dead one fresh.

## Identity

- Claude sessions: Augur's `pid@start` id (pid reuse is a new id).
- Foreign items: `run:<id>` for a declared run (fresh per execution, never the session name; a second execution under
  the same tmux name is a second object), `mux:<socket>:<pane>:<pid>@<start>`, `ctr:<immutable container id>`,
  `model:<server>:<name>`. Items carry `collector` and `scope`, which name the coverage that may remove them.
- `kind` is `remote_job`, `container`, `resident_model` or `unknown`. A kind this reader does not know is read as
  **`unknown`, never the nearest kind** (01-design §5.6). Undeclared items carry no `label` and no `attach`
  (Augur rule 3: no session names or command lines in the shared file).

## Who sees what

- **Scope** (card 9): deliveries from any host other than the two Macs are ignored: archmagi is neither drawn nor marked.
- **Visibility** (ruling 7): a screen draws what runs on it, plus what it launched elsewhere (`launched_from`), never
  a third screen's work.
- **Click** (correction 15, acceptance 6): only a live, declared `remote_job` with an `attach` target is clickable, and
  the action is attach-only with `front: false`. Unknown, ended, undeclared and resident objects launch nothing.

## Drawing unknown

Before this step the runtime filled absent fields with calm values, flagged them in `_absent`, and drew nothing
different: absent looked exactly like idle (03-merged C18). Now:

- **The mark.** A creature whose attention state, CPU or memory was filled calm (absent, failed, or past
  `valid_until`) carries **three still, neutral-grey dots in a row above its right shoulder**, an ellipsis: "no word".
  Drawn by the runtime for every species (`drawUnknown`, `prototype/visitors_runtime.js`), at the creature's own
  opacity. It takes no channel `GRAMMAR_V2.md` already uses: still (satellites orbit), grey (red is strain, hue is
  identity), not a ring (needs-you), full strength (faint is a ghost). Ghosts and departing creatures never carry it.
- **The words.** The hover label adds what is unknown and since when: `Orchard · cpu, memory unknown 2m`, or just
  `unknown 2m` when state, CPU and memory are all missing. The age runs from the last fresh reading Sprites saw; no age
  means not measured since Sprites started. Absent tasks or net alone draw no mark and add no words: their channels
  (satellites, pulses) already draw nothing when absent.
- **Not a behaviour switch.** Saying "I do not know" is not optional.

Why a mark and not 01-design §5.4's blur: the native renderer has no blur (`app/native/canvas.js` counts `filter` and
`shadowBlur` as unsupported), and a per-creature blur needs every piece's cooperation. The mark is the explicit
status mark of scheme F (GPT's "explicit status mark with the age in words"). **Cards 3 and 4 and the blind mockup
sort (build plan step 2) may replace it**; the contract (what is unknown, and that it is drawn) does not change with it.

Foreign objects themselves are not drawn yet: they arrive with step D. When they are, an `unknown` object keeps its
last position and form, carries the same mark, and says "kind unknown" / "last seen <age>" in words.

## Not here, by ruling

No durable store, no relay, no replay of missed completions, no store-ready schema fields (card 1: live view only).
If the execution host dies after a job finishes, the job stays drawn as unknown, with its age, until that host answers.
