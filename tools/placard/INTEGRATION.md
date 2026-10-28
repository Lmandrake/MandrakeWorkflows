# Making sessions Placard-aware

A Placard tree only pays off if a fresh LLM session **looks at the digests before
opening the originals**. The digests explain themselves once found (every
`PROJECT.placard.md` opens with a "navigation plane" note), so there are two
problems, not one: *discovery* (getting a session to check for
`PROJECT.placard.md` at all) and *compliance* (a session that knows the digest
is there and opens the 200 KB original anyway).

Four layers, cheapest first. **Layers 1–3 are all nudges** — they put text in
front of a model and hope, and none of them can stop a Read. Layer 4 is the only
one that does not depend on a session choosing to care, because it is the only
one that costs the model its tool call.

## 1. The skill (what Placard is + how to read/build digests)

The packaged `placard` skill sits in the always-present skill roster and carries
both the *reading protocol* (map → digest → original) and the *digesting
protocol*. Its description must cue **consumption first** — a description that
only describes creation gets the skill invoked when someone says "digest this
folder" and never when a session walks into an already-digested one. The shipped
description therefore leads with `USE WHEN READING`, and names the concrete
trigger: a folder already contains `PROJECT.placard.md` or `*.placard.md`.

Necessary but not sufficient: a skill only shapes behavior once the model decides
it is relevant.

## 2. An always-loaded instruction (the reliable "look first")

Add a standing rule to whatever context every session loads:

- **Claude Code** → `~/.claude/CLAUDE.md` (global) and/or per-repo `CLAUDE.md`.
- **Cowork / other agents** → the equivalent always-loaded memory/system note.

Two things matter in the wording, and the obvious draft gets both wrong:

- **Scope it to artifact folders, not "any folder."** An unconditional "check for
  sidecars before reading files" fires in source trees, where placards will never
  live. Placard's unit is the heavy artifact.
- **Say that finding none is not a reason to make them.** This is the important
  one. A session told to look for digests, finding none, has a live incentive to
  go create them — expensive work that writes files into the user's folders,
  unasked. State the brake explicitly.

The block installed in a global `~/.claude/CLAUDE.md` reads:

```markdown
# Reading a folder of artifacts — check for Placard digests first

**Placard (`/path/to/Placard`) gives heavy artifacts (decks, PDFs, spreadsheets, transcripts,
image-heavy docs) a sidecar digest that lives beside the original.** When a folder holds
artifacts like those, look for the sidecars before opening the originals:

- **`PROJECT.placard.md` in a directory is the map — read it first.** It lists that
  directory's files with a one-line hook, and for each subdirectory a "why descend"
  summary. Follow those down through the child maps; you pay only summary-sized tokens
  until you commit to a file.
- **A `<file>.placard.md` digest's `## Full text` section *is* the content.** It holds the
  cleaned, faithful extraction of the original. Read it instead of re-running
  pypdf / python-pptx / OCR on the source.
- **Open the original only when the digest says to** — its "Open the original if…"
  contract fires (pixels, exact layout, a figure's real content), or its `source_sha256`
  no longer matches the file on disk (stale → re-digest before trusting it).
- **Finding none is not a reason to make them.** Digesting is real work that writes files
  into the user's folders. Do it when asked, or after offering and hearing yes — the
  `placard` skill covers creating and refreshing.

**Why:** extraction is the expensive step and its result doesn't change. A digest is that
result cached beside the file; re-chewing the same PowerPoint every session buys nothing.
```

The gap this layer cannot close: it is loaded at session start, but the check it
asks for happens later, in whatever directory the work lands in. That is what
layer 3 is for.

## 3. The session-start hook (announce presence, silently)

`contrib/placard_sessionstart_hook.sh` runs at session start, and injects a
"placards are present here" note as `additionalContext` — or says nothing at all.

Install it in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/Placard/contrib/placard_sessionstart_hook.sh",
            "timeout": 15,
            "statusMessage": "Checking for Placard digests"
          }
        ]
      }
    ]
  }
}
```

It fires on the *next* session start, not the one that installs it.

### Why it calls `announce`, not `verify`

The obvious implementation — `placard.py verify | tail -1` — is wrong on two
counts, both measured on a real tree:

- **`verify` counts what is *missing*.** At a large shared-drive root that is
  thousands of missing digests. At session start a number like that
  reads as a to-do list, and pushes a session straight into unsolicited
  digesting. Absence of digests is not news; presence is.
- **`verify` hashes every original** to detect staleness — several times slower
  than `announce` on that tree, and it grows with the size of the artifacts, not
  their count. A hook that reads every deck in a project to start a session is a
  hook that gets uninstalled.

`announce` therefore counts only what exists, never hashes, caps its walk depth
(default 6), prints **nothing** when a tree holds no digests, and always exits 0.
The tradeoff is explicit: it does not check staleness, and its output says so —
the per-digest `source_sha256` and the "Open the original if…" contract are where
staleness is caught, plus `verify` on demand.

### Verified behavior

| Condition | Result |
|---|---|
| Placarded tree (18 digests) | announces, valid JSON `additionalContext` |
| Source repo with no digests | silent, exit 0 |
| Tree with 72 digestible artifacts, 0 digests | silent, exit 0 |
| No stdin / no `cwd` in payload | falls back to `$PWD`, exit 0 |
| Large shared-drive root | well under a second |

The hook is read-only by construction: it only ever runs `announce`, which walks
and prints. It never writes a sidecar, never opens an original, and never fails a
session.

## 4. The Read guard (the only layer that enforces anything)

`contrib/placard_read_guard.py` is a **PreToolUse** hook on `Read`. When a
session tries to read a heavy original that has a digest reporting it *can*
answer, the Read is refused and the reason names the digest, the body, and the
override.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/Placard/contrib/placard_read_guard.py",
            "timeout": 35,
            "statusMessage": "Checking for a Placard digest"
          }
        ]
      }
    ]
  }
}
```

Like the session-start hook, it takes effect on the *next* session, not the one
that installs it.

### It delegates the verdict rather than recomputing it

`placard.py read` already owns the state machine, and `cmd_read` encodes the
answer in its exit status: **0 for `ok`/`legacy`, non-zero for everything else.**
The guard keys on that exit code and never names a state, so it cannot drift out
of agreement with `placardlib/read.py`. That is deliberate — the characteristic
defect here is a gate comparing against a vocabulary it *assumed* instead of
*measured*, which is how the figure-class gate shipped inert with green tests. A guard that names no states cannot have that bug.

### What it does not block

| Case | Why it passes |
|---|---|
| Regeneration (`digest`, `refresh`) | those open originals from inside `placard.py` under **Bash**; a `Read`-matched hook never sees them. Extraction is not a Read. |
| No sidecar beside the file | nothing to read instead — and staying silent avoids nudging a session into unsolicited digesting |
| `source-stale` / `extraction-stale` | the digest describes a different file; re-digest is the remedy, not a block |
| `unavailable` / `needs-source-inspection` | `placardlib/read.py:authorizes_original` defines these as the two states that *permit* the original |
| Images, and any non-heavy extension | a Read of an image is a *visual* read a text body cannot serve |
| Anything unexpected | **fails open** — no payload, no `placard.py`, no python, a timeout, any exception all allow the Read |

### What this layer still does not guarantee

It covers `Read`, which is how an agent reads a file — not every possible route
to the bytes. A deliberate `cat`, `pdftotext` or `pypdf` call under Bash is
**not** blocked, and cannot be without blocking regeneration, which runs by
exactly that route. So this is enforcement of the normal path, not a sandbox:
it removes the silent default (open the 200 KB original because nothing stopped
you) and leaves the deliberate act available. Claiming more than that would
repeat the error this layer was added to correct.

### The override is a token, not an env var

A `Read` call carries no environment, so a `PLACARD_ALLOW_ORIGINAL=1` escape
hatch would read as an escape hatch while being unreachable from the thing being
blocked — the exact class of dead promise this layer exists to remove. Instead:

```bash
python3 contrib/placard_read_guard.py --allow-once <file>
```

writes a single-use token, keyed by resolved path, that the next Read of that
file consumes. One Bash call, agent-actionable, and the override lands as a
deliberate act rather than a silent default.

### Why exit 2 rather than `permissionDecision: deny`

A session running `defaultMode=bypassPermissions`, where permission decisions
are skipped entirely but a blocking exit code is still honoured.

Tests: `tests/test_read_guard.py`, deliberately weighted toward the
**false-block** cases. A syntactic guard fails closed, so its cost lands on
legitimate work rather than showing up as a miss.

## Discovery cheatsheet

```bash
python3 placard.py --root . announce      # is this tree covered at all? (cheap, quiet)
find . -name PROJECT.placard.md           # the maps (navigation plane)
find . -name '*.placard.md'               # every digest (maps included)
python3 placard.py --root . verify        # are digests current? (hashes originals)
python3 placard.py --root . map           # (re)build the recursive maps
```

Note that `PROJECT.placard.md` itself ends in `.placard.md`, so the second glob
is a subset of the third — `announce` reports the two counts separately.
