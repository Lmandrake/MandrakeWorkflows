---
name: "waypoint"
description: "Manage Waypoint, the user's shell navigation-and-launch shortcut system (the `waypoint` CLI, tables in ~/.config/waypoint). Use whenever the user wants to add, remove, block, list, or change a project shortcut ('add a waypoint for X', 'make $FOO point to...', 'stop tracking Y', 'what shortcuts do I have'); OR to manage a launch alias that cds into a project and runs a command ('add a launch for X', 'make `launch notes` start claude', 'change the default launch command', 'what can I launch'); when a $VAR shortcut, the `wp` jump, or the `launch` command isn't working in their shell; or when their ~/.zshrc shortcuts broke after an edit. Waypoint renders $VAR exports plus a `wp <name>` cd-jump and a parallel `launch <name>` runner from markdown databases that are the single source of truth."
---

# Waypoint — shell navigational shortcuts

Waypoint lets the user refer to active project roots by name: as environment
variables (`$NOTES`, `$THESIS`) and as a one-word jump command (`wp thesis`).
The CLI is a single self-documented Python 3 script (stdlib only, no
dependencies), `tools/waypoint/waypoint` in its repo, linked as
`~/.config/waypoint/waypoint`. Its tables live in the data directory,
`$WAYPOINT_DATA` or `~/.config/waypoint` (often a symlink into a private
synced repo); `waypoint path` prints every location.

## The one idea that governs everything

**The database is the source of truth; the shell file is a rendered copy.**

- Database: `~/.config/waypoint/waypoints.md` — a GFM table
  (`Name | Path | Added | Status | Notes | Machine`). Editing this table (by hand
  or via commands) then running `sync` is how the system changes.
- Rendered output: a single fenced block in the user's `~/.zshrc`, between
  `# >>> waypoint (managed …) >>>` and `# <<< waypoint (managed) <<<`, holding the
  `export` lines and the `wp()` function. Waypoint owns this block exclusively and
  rewrites it wholesale; nothing outside the block is touched.

Everything flows database → shell via `sync`, except the one recovery command
`import`, which rebuilds the database from the shell block. So the two back each
other up: lose the shell block → `sync` rebuilds it; lose the database →
`import` rebuilds it.

## Access constraint (check — don't assume)

Whether you can touch the user's real `~/.zshrc` is **environment-dependent**;
verify before assuming either way. Run `ls -l ~/.zshrc` and
`grep -c '>>> waypoint (managed' ~/.zshrc` up front. Match the sentinel
precisely like that: the looser `'>>> waypoint'` also matches the
`waypoint-launch` sentinel, so it reports 2 on a perfectly healthy file.

- Sometimes the bash tool runs in a VM whose `$HOME` isn't the user's, so
  `~/.zshrc` is invisible and `sync` is the user's to run. But in other setups
  (`$HOME=/Users/<user>`) you *can* read and even write it —
  don't reflexively claim you can't.
- You can **always** read `~/.config/waypoint/waypoints.md` and the
  `backups/` folder beside it. Lean on these to diagnose.
- Editing the user's live login file is a **confirm-first** action even when you
  can. `sync` is safe (it backs the file up first and only rewrites the sentinel
  block), but get the user's go-ahead rather than silently editing their shell,
  and don't claim a change is live in *their* running shell — they still need a
  new terminal or `source ~/.zshrc`.
- **The confirm gate belongs on `add`/`remove`/`block`/`unblock`, not just on
  `sync`.** Those four auto-sync, so on a machine where you *can* write
  `~/.zshrc` there is no such thing as a database-only `add` — running it edits
  the login file immediately, before you've asked. If you want the DB change now
  and the shell change on the user's say-so, hand-edit `waypoints.md` (always
  safe, it's just a Drive file) and confirm before syncing. Don't resolve this by
  asking permission for every `list` and `doctor` — those are read-only.
- **Run `doctor` before `sync`, so you can tell the user everything `sync` will
  do.** `sync` rewrites *both* managed blocks, so if the launch block is missing
  or stale it gets created/updated in the same pass — a change the user didn't
  ask for and shouldn't discover afterward. `doctor` names both blocks' states up
  front; mention any second change when you ask.
- To exercise the tool without risk, target a throwaway file with
  `--shell-file /tmp/whatever`.

## Commands

Invoke as `~/.config/waypoint/waypoint <command>` (or just `waypoint …` if
the user has aliased it). Add/remove/block/unblock auto-run `sync` afterward —
which means they write `~/.zshrc`, so they inherit the confirm-first rule above.
`list`, `doctor`, `path`, and `machine` are read-only; use them freely.

| Command | Purpose |
|---------|---------|
| `add NAME PATH [--note ...] [--force]` | Add or update a shortcut. `~`/`$VARS` accepted; an absolute path is stored. `--force` overrides a blocked name. |
| `remove NAME` | Stop tracking a shortcut. |
| `block NAME [PATH] [--note ...]` | Record a deliberate exclusion — kept in the DB but never exported, and protected from accidental re-add. Machine-independent. |
| `unblock NAME` | Lift a block, making the name active again. |
| `list` | Show shortcuts with an `ok`/`MISS`/`block`/`other` status and a MACHINE column. |
| `sync` | Regenerate the shell block from the database (idempotent, self-healing), resolved for this machine. |
| `doctor` | Health check: DB present, block in sync for this machine, no duplicate `(name, machine)` rows, every resolved path exists. |
| `import [--force]` | Rebuild the database from the shell block (recovery). Recovered rows are always universal. |
| `install` | Ensure the managed block exists (creates an empty DB if needed). |
| `uninstall` | Remove the managed block (keeps the database). |
| `path` | Print resolved shell-file, database, and backup locations. |
| `machine` | Print this machine's resolved identity key. |
| `launch add NAME (--waypoint WP \| --path DIR) [--cmd ...] [--note ...]` | Add/update a launch alias, then sync. `--waypoint` preferred; `--cmd` overrides the default template. |
| `launch remove NAME` | Remove a launch alias, then sync (global `--machine` drops one machine's row). |
| `launch list` | Show launch aliases with resolved dir, effective command, machine. |
| `launch template ["..."]` | Print or set the default command template. |

Names must be valid shell identifiers (letters/digits/underscore, not starting with
a digit); they are exported as `$UPPERCASE`, also defined (unexported) as `$lowercase` and `$Capitalized`, and matched case-insensitively by `wp`/`launch` (`wp` also accepts the target folder's name).

## Multi-machine scoping

The database is shared across every machine (it lives on Drive), but a row's
optional trailing **Machine** column can pin it to just one. Blank = universal
fallback, used by any machine with no more specific row for that Name. A Name
can have several rows (one per machine) as long as each has a distinct Machine.
Resolution per Name: exact machine match wins, else the blank/universal row, else
the Name simply isn't tracked here — that's not an error.

**The canonical reason to scope: mount-root divergence.** DB paths are absolute,
but the *same* Drive project can sit at a different absolute path on each machine
because Google Drive Desktop mounts at a different root — one Mac at `~/GDrive`,
another at `~/My Drive`. A universal `~/GDrive/...` row is correct on the first
machine but *misses entirely* on the second. Fix: a machine-scoped row for the
odd machine that swaps only the mount prefix (`~/GDrive/...` ↔ `~/My Drive/...`);
everything below the mount is identical because it's the same synced Drive, so you
don't need to inspect the other machine to get the folder names right. Keep the
universal row on whichever convention matches the machine you're on, and scope the
other. Local, non-Drive paths (e.g. `~/dev/foo`, a repo cloned on only one
machine) are inherently single-machine and belong scoped to that machine, with no
universal row at all.

**Never resolve another machine's paths on this machine.** A row scoped to a
different machine points at a path that doesn't (and shouldn't) exist locally;
`list`/`doctor` mark it `other` and deliberately skip the existence check — `other`
is not a `MISS` and not a bug. So when you author or edit a row for another machine
you *cannot* confirm it by `ls` here; derive the path from the mount-root transform
above, and never "correct" a scoped row to a path that merely happens to exist
locally. Verify only the rows that resolve for the machine you're on.

The global `--machine NAME` flag (must appear **before** the subcommand, e.g.
`~/.config/waypoint/waypoint --machine work-laptop list`) overrides which
machine's perspective `list`/`doctor`/`sync` resolve for, or which machine-scoped
row `add`/`remove` act on (omitted = universal, same as before this feature
existed). Machine identity defaults to the (normalized, lowercased) hostname,
overridable by `$WAYPOINT_MACHINE`; `waypoint machine` prints what this machine
resolves to. Corporate-imaged Macs often report an asset-tag hostname (e.g.
`mt-abc123`) rather than a friendly name.

**Caveat — check for a symlinked mount root before you `add` anything.** `add`
resolves the path through any symlinks (`Path.resolve()`) and stores the *target*,
not the path you typed. So on a machine where the Drive root is reached via a
symlink, `add` cannot produce a `~/GDrive/...` universal row at all — it will
silently store the resolved `~/My Drive/...` path and break the
`~/GDrive/...`-everywhere convention this tool relies on for portability. One
command decides it:

```sh
ls -ld ~/GDrive ~/"My Drive"     # is either one a symlink to the other?
```

- **If `~/GDrive` is a symlink** (common: `~/GDrive -> ~/My Drive`), don't use
  `add` for the universal row — **hand-edit `waypoints.md`**, writing the path
  yourself. Note the Path column stores an *expanded absolute* path, so the
  universal row reads `/Users/<user>/GDrive/...`, not `~/GDrive/...`. Then confirm
  and `sync`. Checking after the fact is wasted effort here: the check is
  guaranteed to fail every time.
- **If neither is a symlink**, `add` is fine; still glance at the stored path.

The machine-scoped row is unaffected either way, since it's supposed to hold this
machine's real mount path — which is exactly what `add` resolves to.

## Launch aliases (the second managed block)

Waypoint manages a **second** block in the shell file — sentinels
`# >>> waypoint-launch (managed …) >>>` / `# <<< waypoint-launch (managed) <<<` —
defining a `launch <name>` function that cds into a directory and runs a command
(e.g. `cd $NOTES && claude -n Notes`). Its
source of truth is `launches.md`, beside `waypoints.md`.

- A launch's directory comes from a **waypoint reference** (preferred — inherits
  that waypoint's per-machine resolution, so it follows `~/GDrive`↔`~/My Drive`
  automatically) or an **explicit path** fallback. Exactly one is set per row.
- The command is a shared **default template** (stored in `launches.md`,
  e.g. `claude --dangerously-skip-permissions -n {NAME}`) unless the row sets its
  own. Tokens `{NAME}` (alias name, verbatim) and `{DIR}` (resolved dir) are
  substituted. Command text is embedded literally in the shell block (no `eval`);
  the directory is single-quoted.
- Launch rows carry the same optional **Machine** column. A launch whose
  referenced waypoint doesn't resolve here is simply skipped — not an error.
- **Unified lifecycle:** `sync` rewrites BOTH blocks, `doctor` checks both,
  `install`/`uninstall`/`import` operate on both. Entry management is under the
  `launch` subcommand; waypoint management stays top-level.

When adding a Claude launcher for a project that already has a waypoint, that's
just `waypoint launch add <Name> --waypoint <WP>` — the default template does the
rest. Use `--cmd` for anything else (`jupyter lab --dir {DIR}`, `npm run dev`, …).

## Window layouts (Space + bounds per focus window)

`waypoint layout save` records, for every open focus window on this machine, its
macOS Space and bounds into `layouts.md` (keyed Name + Machine; never universal).
`waypoint focus launch` then reopens a missing window on that Space at those
bounds; a project with no row opens exactly as before. `waypoint layout` shows
the table, `layout forget NAME` drops a row, `focus launch --only NAME` opens one.

- **Space placement is iTerm2's own per-profile Space setting**, through
  `Claude-Space1..N` profiles Waypoint writes to
  `~/Library/Application Support/iTerm2/DynamicProfiles/waypoint-spaces.json`
  (each a copy of the default profile plus `"Space": N`; N = desktop count,
  max 9). Regenerated by `layout save` / `layout profiles`; never edit it in
  iTerm2's Settings.
- **Prerequisite per machine:** Mission Control's "Switch to Desktop N"
  shortcuts must be enabled (System Settings > Keyboard > Keyboard Shortcuts >
  Mission Control). iTerm2 switches Space by invoking them; without them the
  window silently opens on the current Space.
- Opening on another Space **switches the display to that Space** (iTerm2 does
  it); a bulk launch ends on the last window's Space.
- Space reading is a read-only `windowspaces` helper (`$WAYPOINT_WINDOWSPACES`;
  private SkyLight calls); iTerm2's AppleScript window `id` is its CG window number.

## Common requests → what to do

**"Add a waypoint for <project>" / "make $FOO point to <dir>".**
First confirm the real path exists (search the user's Drive projects folder and `~/dev`
for local code repos — project roots often sit inside a parent folder). If the path is ambiguous, ask
which folder rather than guessing.

Then **read `waypoints.md` and match the pattern already there** rather than
inventing one. For a Drive project the established shape is *two* rows — a
universal `~/GDrive/...` row plus a machine-scoped row holding this machine's real
mount path — so a new project usually means adding both, not one. A local
non-Drive path gets a single machine-scoped row and no universal row.

To land it: either have the user run
`~/.config/waypoint/waypoint add FOO "<abs path>" --note "..."` then
`source ~/.zshrc`, or hand-edit `waypoints.md` and `sync` after confirming.
Hand-editing is the better default when the mount root is symlinked (see the
`add`-resolves-symlinks caveat) or when you want the DB updated before touching
their shell. Either way the user needs a new terminal or `source ~/.zshrc`.

**"Stop tracking X" / "never add Y again."**
Use `block` (not just `remove`) when the user signals a *lasting* exclusion —
block records the decision so neither a human nor a later `add` re-adds it silently.
Use `remove` for a simple one-off deletion.

**"What shortcuts do I have?"** → `waypoint list` (you can read `waypoints.md`
directly to answer without touching the shell).

**Scope guidance.** Waypoint is for *active* projects with clear names — the ones
touched recently. Not every folder needs a shortcut; don't over-populate it.

## Troubleshooting (this is where the skill earns its keep)

**"$FOO isn't defined in a fresh shell" or "the `wp` command isn't found."**
The shell block is stale or was never installed with that entry. Confirm the entry
is active in the database (read `waypoints.md`), then have the user run
`~/.config/waypoint/waypoint sync && source ~/.zshrc`. Adding via the tool
should already sync, so a missing entry usually means `sync` was run against a
sandbox file, or the user never ran `install`/`sync` on their own machine.

**"NONE of my shortcuts work" / "my `.zshrc` seems broken after an edit."**
This is almost always `~/.zshrc` erroring out partway and aborting the source. The
classic cause is **more than one managed block** (e.g. `install` appended a second
block on top of an existing one), giving duplicate `wp()` definitions. Ask the user
to run this decisive diagnostic and paste the result:

```sh
grep -c '>>> waypoint (managed' ~/.zshrc         # should be 1
grep -c '>>> waypoint-launch (managed' ~/.zshrc  # should be 1 (0 if never installed)
zsh -n ~/.zshrc && echo OK                       # syntax check
```

**Count each sentinel separately, and don't shorten the pattern.** Since the
launch block exists, `grep -c '>>> waypoint'` matches *both* sentinels and returns
2 on a healthy file — reading that as a duplicate block is a false alarm. The
counts above are what "exactly one of each" looks like; 2 for either single
pattern is the real duplicate.

Fix path: the hardened `sync` is self-healing — it collapses *all* managed blocks
into exactly one on the next run. So `~/.config/waypoint/waypoint sync &&
source ~/.zshrc` repairs a duplicate-block file. If the file is badly mangled,
restore a clean copy from `~/.config/waypoint/backups/` (Waypoint backs up
`~/.zshrc` there before every edit) and then `sync` once. Prefer restoring the
*pre-Waypoint* backup if the user hand-edited since, to avoid losing their edits —
confirm with them first.

**`doctor` reports duplicate blocks or out-of-sync.** Run `sync`; re-run `doctor`.

**"Why does $FOO work here but not on my other laptop?"** Almost always
mount-root divergence, not breakage — see *Multi-machine scoping*. To reason about
the other machine without touching it, read its backups: `backups/` names each
snapshot `.zshrc.<machine>.<timestamp>.bak`, and the managed block inside carries a
`Source of truth: …` and `Rendered for machine: …` header. That reveals the other
machine's identity key *and* its Drive mount root — enough to author correct
machine-scoped rows for it from here.

**`./waypoint` won't run / "permission denied".** `chmod +x "$(readlink ~/.config/waypoint/waypoint)"`.
This was routine when the repo lived on Google Drive, which strips the executable bit
on sync; since the move to local disk on 2026-08-24 the bit is preserved and a fresh
`git clone` sets it from the index, so this should now be rare.
A `git pull` can still bring in `waypoints.md` edits from another machine mid-session, so if
a hand-edit fails with "file changed," re-read the database and retry rather than
forcing it.

## Design guarantees (so you can reason about edge cases)

- **Idempotent:** re-running `sync` on an unchanged database yields a byte-identical
  block.
- **Self-healing:** `sync` finds and removes *every* managed block, leaving exactly
  one — duplicates can't accumulate.
- **Non-destructive:** the file is copied into `backups/` before every write; only
  the sentinel-fenced region is ever modified.
- **Warn-but-export:** a missing directory still gets its variable exported (so the
  name keeps working if the path returns) and is flagged by `list`/`doctor`.
- **Blocked entries** are stored but never exported.

Full documentation is in the README beside the executable (`tools/waypoint/README.md`).
