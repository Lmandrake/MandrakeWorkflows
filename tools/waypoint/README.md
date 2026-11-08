# Waypoint

A tiny navigational-shortcut manager for the shell. It lets you refer to your
active project roots by name — as environment variables (`$NOTES`, `$THESIS`)
and as a one-word jump command (`wp thesis`) — and it owns a single, clearly
labelled block in your shell login file so those shortcuts are always defined.

The tool and its data live apart: the code is here, your tables live in a data
directory of your own.

```
tools/waypoint/
├── waypoint           # the executable (Python 3, stdlib only)
├── examples/          # starter tables: waypoints.md, launches.md, layouts.md
├── bin/term-bg-launch # helper: run commands in minimized Terminal windows
└── README.md          # this file

$WAYPOINT_DATA/        # default ~/.config/waypoint
├── waypoints.md       # THE DATABASE — authoritative source of truth (editable)
├── launches.md        # launch-alias database (the parallel `launch` block)
├── layouts.md         # per-machine window Space and bounds (focus launches)
├── waypoint           # symlink to the executable, made by `install`
└── backups/           # timestamped copies of your shell file, made before edits
```

To share one set of tables across machines, keep the data directory in a
private synced repo and symlink `~/.config/waypoint` to it (or set
`WAYPOINT_DATA`). The backups hold copies of your shell file, so keep them out
of any repo (gitignore `backups/`).

## The one idea to remember

**The database (`waypoints.md`) is the source of truth. The block in your shell
file is a rendered copy of it.** Everything flows one direction — database →
shell — except the explicit `import` recovery command, which goes the other way.

This gives you two independent backups of the same information:

- Shell file corrupted or wiped? → `waypoint sync` rebuilds the block from the database.
- Database lost or damaged? → `waypoint import` rebuilds it from the shell-file block.

As long as *either* survives, you can regenerate the other.

## Install (one time)

```sh
mkdir -p ~/.config/waypoint
cp tools/waypoint/examples/*.md ~/.config/waypoint/   # then edit the rows to your own
tools/waypoint/waypoint install   # links the CLI into the data dir, writes the managed block (backed up first)
source ~/.zshrc                   # or just open a new terminal
```

Put the tool on your `PATH` with one line *outside* the managed block:

```sh
alias waypoint="$HOME/.config/waypoint/waypoint"
```

## Everyday use

```sh
waypoint list                     # show everything tracked, with an existence check
wp                                # print the list of jump names
wp notes                          # cd to the Notes root
echo $THESIS                      # the same root as an env var

waypoint add PROPOSAL ~/Drive/Projects/Proposal --note "mission proposal"
waypoint remove PROPOSAL             # stop tracking it
waypoint sync                     # re-render the shell block from the database
waypoint doctor                   # health check: db, block-in-sync, and every path
```

Any command that adds or removes a waypoint automatically re-syncs your shell
file, so you rarely call `sync` by hand — it's there for recovery and for when
you've hand-edited `waypoints.md`.

After any change, open a new terminal or run `source ~/.zshrc`.

**Careful with paths through a symlink.** `add`/`block` resolve the path you give
them (`Path.resolve()`), which follows symlinks to their real target. If you `add`
a waypoint via `~/Drive/...` and `~/Drive` is itself a symlink, the path that
lands in the database is the *resolved* target (e.g. `/home/you/My Drive/...`),
not `~/Drive/...` — breaking the one-convention-everywhere portability this tool
exists for. Prefer editing `waypoints.md` by hand (then `waypoint sync`) when you
want to keep every row on the same `~/Drive/...`-style convention across machines.

## Multi-machine scoping

If the data directory is synced, the database is shared and visible from every machine you
use — but a path, or even a whole project, doesn't always exist in the same place
(or at all) on every machine. Each row has an optional trailing **Machine**
column:

- **Blank** = universal fallback. Used by any machine that has no more specific
  row for that Name. All pre-existing rows are blank, so nothing changes for you
  unless you opt in.
- A **Name** may have more than one row, as long as each has a distinct Machine
  (at most one of which is blank). Resolution, per Name: an exact match on this
  machine's identity wins; otherwise the blank/universal row is used; otherwise
  the Name simply isn't tracked on this machine (not an error).

This machine's identity is its (normalized) hostname by default —
`waypoint machine` prints it. Corporate-imaged Macs often have an asset-tag
hostname (e.g. `MT-ABC123`) rather than something readable; set
`export WAYPOINT_MACHINE="whatever-you-want"` **outside** the managed block in
your shell rc to pin a friendly, IT-reimage-proof name instead.

```sh
waypoint machine                                    # what does this machine call itself?
waypoint --machine work-laptop add FOO ~/other/path # add a row scoped to work-laptop only
waypoint --machine work-laptop list                 # preview resolution as if you were elsewhere
waypoint --machine work-laptop remove FOO           # drop just that machine's row, keep the fallback
```

`--machine` must appear **before** the subcommand (it's a global option, like
`--shell-file`). For `list`/`doctor`/`sync`/`install` it overrides which
machine's perspective to resolve; for `add`/`remove` it instead selects which
machine-scoped row to write or delete (omit it and you get/affect the universal
row, same as before this feature existed).

## Launch aliases

Beyond jumping to a directory, Waypoint can *launch* something there. A launch
alias binds a name to a directory + a command and renders a **second managed
block** into your shell file, defining a `launch <name>` function (parallel to
`wp`). The classic use is starting a Claude session in a project root:

```sh
launch                            # list launch aliases
launch notes                      # cd $NOTES && claude -n Notes
```

Aliases live in their own database, `launches.md`, with a configurable default
command template so adding one is usually a single reference:

```sh
waypoint launch add Notes --waypoint NOTES         # dir follows the NOTES waypoint
waypoint launch add Notebook --path ~/scratch --cmd "jupyter lab --dir {DIR}"
waypoint launch list                               # show dir + effective command
waypoint launch template                           # print the default template
waypoint launch template "claude -n {NAME}"        # change it, then re-sync
```

- **Directory:** `--waypoint NAME` (preferred — the launcher cds to whatever that
  waypoint resolves to on *this* machine, so it follows your per-machine
  scoping automatically) or `--path DIR` as a fallback.
- **Command:** the default template unless `--cmd` overrides it. `{NAME}` (the
  alias name, verbatim) and `{DIR}` (the resolved directory) are substituted.
- **Multi-machine:** launch rows take the same optional Machine column. A launch
  whose referenced waypoint isn't tracked on this machine is simply not rendered
  here — not an error.
- **Project colours (two markers in the Command cell):** the **text** colour is
  `printf '\033]10;#RRGGBB\007'` (iTerm2 foreground, and the colour Lodestar's
  dashboards can read). An optional **LED** colour for
  SidePulse follows it as `: led=#RRGGBB;` — a shell no-op, so the rendered
  `launch` arm is unchanged in behaviour. No `led=` means the LED uses the text
  hex.
- **One colour per project** (owner, 2026-11-05): the sprite, the iTerm2 text and
  the SidePulse LED all read the text hex, so it lives in exactly one place.
  `launch colour NAME '#RRGGBB'` rewrites only the six digits inside the `]10;`
  escape — the `claude` invocation, its flags, `{NAME}`/`{DIR}`, quoting, any
  `/color` argument and any `: led=` marker are preserved byte for byte, and a
  hex-looking string elsewhere in the cell (a note, a `/color #ABCDEF`) is never
  touched. A row that sets no colour yet GAINS the `printf` ahead of its existing
  command; a blank Command (meaning "use the default template") has the template
  spelled out, since a row holding only a `printf` would start no session.

Both blocks share one lifecycle: `sync` rewrites both, `doctor` checks both,
`install`/`uninstall`/`import` operate on both.

## What the managed block looks like

Waypoint replaces **only** the text between these two sentinels, and backs up the
whole file first. Everything else in your `~/.zshrc` is left untouched.

```sh
# >>> waypoint (managed — do not edit by hand) >>>
# Generated by waypoint. ...
export NOTES='/home/you/dev/Notes'
export THESIS='/home/you/Drive/Projects/Thesis'
...
thesis='/home/you/Drive/Projects/Thesis'   # case variants, not exported
Thesis='/home/you/Drive/Projects/Thesis'
...
wp() { ...case statement... }
# <<< waypoint (managed) <<<
```

**Names are case-insensitive.** `wp`, `launch` and the variables all accept any casing:
`$THESIS` is exported, and `$thesis` / `$Thesis` (plus the database's own casing) are
defined as plain shell variables (not exported, so child processes see only the
canonical one; names zsh reserves such as `path` are skipped). Mixed casings like
`$ThEsIs` cannot work, since shell variable names are case-sensitive. `wp` also
answers to the target folder's name (`wp mygame` for a `GAME` row pointing at `.../MyGame`).

Paths are single-quoted, so roots containing spaces or parentheses are handled correctly.

## Commands reference

| Command | What it does |
|---------|--------------|
| `add NAME PATH [--note ...] [--force]` | Add or update a waypoint, then sync. Accepts `~` and `$VARS`; stores an absolute path. `--force` overrides a blocked name. Use the global `--machine` (before `add`) to scope the row; omitted = universal. |
| `remove NAME` | Stop tracking a waypoint, then sync. With a global `--machine` override, removes only that machine's row instead of every row for the name. |
| `block NAME [PATH] [--note ...]` | Record a name as a deliberate exclusion. Kept in the database but never exported, and protected against accidental re-add. Machine-independent. |
| `unblock NAME` | Lift a block, making the name active again. |
| `list` | Show tracked waypoints with an `ok`/`MISS`/`other` existence flag and a MACHINE column. |
| `sync` | Regenerate the managed block from the database (idempotent), resolved for this machine (or `--machine` override). |
| `doctor` | Verify the database exists, the block is in sync for this machine, there are no duplicate `(name, machine)` rows, and every resolved path exists. |
| `import [--force]` | Rebuild `waypoints.md` from the shell-file block (recovery). Recovered rows are always universal (blank Machine). |
| `install` | Ensure the managed block exists (creates an empty db if needed). |
| `uninstall` | Remove the managed block from the shell file. Leaves the database intact. |
| `path` | Print the resolved shell-file, database, and backup locations. |
| `machine` | Print this machine's resolved identity key (hostname, `$WAYPOINT_MACHINE`, or `--machine` override). |
| `launch add NAME (--waypoint WP \| --path DIR) [--cmd ...] [--note ...]` | Add or update a launch alias, then sync. `--waypoint` is preferred; `--cmd` overrides the default template (`{NAME}`/`{DIR}` tokens). |
| `launch remove NAME` | Remove a launch alias, then sync. Honours the global `--machine` to drop just one machine's row. |
| `launch list` | Show launch aliases with resolved directory, effective command, and machine scope. |
| `launch colour NAME ['#RRGGBB']` | Print or set the project's ONE colour — the `]10;` text hex in its Command cell. Scope follows `focus add`: with no global `--machine`, every machine row for that Name (one project, one colour); with `--machine`, only that row. Spelled `color` too. |
| `launch template ["..."]` | Print the default command template, or set it (then sync). |
| `focus add NAME` / `focus remove NAME` | Set or clear the `Focus` marker on a launch alias (all its machine rows, or only the global `--machine` row). No effect on Lodestar sync. |
| `focus list` | Show focus launches and where each resolves on this machine. |
| `focus launch [--dry-run] [--arrange]` | Start iTerm2 if it is not running (waiting for its restored windows), then open an iTerm2 window for every focus launch not already open. A restored idle window titled for the project (`Claude: <basename> (-zsh)`, no `claude` on its tty) gets the command typed into it instead of a duplicate beside it. `--arrange` then runs `layout apply`. A Desktop `.command` file running `focus launch --arrange` makes it one double-click. "Open" = an iTerm2 session titled `Claude: <dir basename>` (or `<dir basename> (claude)`), or a `claude` process on an iTerm2 tty whose cwd is the launch dir. Never opens a duplicate. Tests: `python3 -m unittest discover -s tests`. |

## Design guarantees (verified)

- **Idempotent.** Re-running `sync` with an unchanged database produces a
  byte-for-byte identical block.
- **Surgical & non-destructive.** Only the sentinel-fenced region is touched;
  the file is copied into `<data dir>/backups/` before every write.
- **Warn-but-export.** A missing directory still gets its variable exported (so
  the name keeps working if the path returns) and is flagged by `list`/`doctor`.
- **Zero dependencies.** Standard-library Python 3 only.

## Choosing which shell file

By default Waypoint targets `~/.zshrc` (the macOS default and the correct home
for the `wp` shell *function*, which — unlike exported variables — is not
inherited by child shells and so must be defined in every interactive shell's rc
file). Override per-invocation with `--shell-file PATH`, or globally by setting
`WAYPOINT_SHELL_FILE` in your environment.

## The Waypoint skill (how Claude knows this tool)

The interaction knowledge for Waypoint lives in a Claude Code skill,
`.claude/skills/waypoint/SKILL.md`. Install it globally as a symlink so it
follows every edit:

```sh
mkdir -p ~/.claude/skills
ln -sfn "$(pwd)/tools/waypoint/.claude/skills/waypoint" ~/.claude/skills/waypoint
```

## Tests

```sh
(cd tools/waypoint && python3 -m pytest -q tests)
```
