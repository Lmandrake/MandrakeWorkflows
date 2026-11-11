---
name: placard
description: Read and write Placard sidecar digests — `*.placard.md` markdowns beside expensive artifacts (decks, PDFs, spreadsheets, transcripts, image-heavy docs) that let an LLM understand a project cheaply. USE WHEN READING - a folder already contains `PROJECT.placard.md` or `*.placard.md` sidecars, or a session was told placards are present - read the map and the digests' inline `## Full text` instead of opening the originals; open an original only when a digest's "Open the original if…" contract fires or its `source_sha256` is stale. USE WHEN CREATING - the user wants to "digest" a folder, "summarize files for later", "make a project readable to an LLM", build or refresh a project map, or check whether digests are stale. Also use proactively before deep work in a folder full of decks/PDFs/spreadsheets.
---

# Placard — per-artifact digests + recursive project maps

Placard makes a project cheap for an LLM to understand, on **two planes**:

- **Navigation plane (cheap):** every content-bearing directory gets a
  `PROJECT.placard.md` map. Each map says, for each child directory, *why you'd
  descend into it* (a one-line `dir_summary` rolled up from the child). Walk the
  tree top-down paying only summary-sized tokens until you commit to a file.
- **Content plane (heavy, on demand):** each expensive artifact gets a faithful
  **digest** beside it (`foo.pptx` → `foo.pptx.placard.md`) that carries a
  summary AND a `## Full text` section holding the **cleaned, faithful, once-
  and-for-all text extraction** of the original. Read the digest instead of
  re-ingesting the original — extract once, read many. Open the original only
  for pixels, exact layout, or a figure's actual content.

Read map → (descend maps) → digest (summary + full text) → original, opening an
original only when a digest's **escalation contract** says it is justified.

Placard is **non-destructive**: it never edits originals and never mutates a
shared store. It only adds `*.placard.md` sidecars and `PROJECT.placard.md` maps.

The CLI (`placard.py`) does the deterministic work — hashing, staleness,
extraction and cleaning (`digest`), crash-safe publishing, the read protocol and
recursive map assembly. **You** (the LLM) do what only you can: write each
digest's summary from its body, and author each directory's `dir_summary` +
Overview.

## When to use

- "Digest this folder / project", "summarize these files for later reuse".
- Before doing analysis in a folder full of decks/PDFs/spreadsheets — digest
  first, then work off the digests.
- "Build/refresh the project map", "which digests are stale?".

## Reading protocol (when consuming an already-digested project)

🔴 **Before opening ANY heavy file — `.pdf`, `.pptx`, `.docx`, `.xlsx` — look for
BOTH sidecars first:** `<file>.placard.md` (the entry) and, if the entry names
one, its `body_path`. Open the original **only if neither is present**, or if the
read returns a state that authorizes it. This is the rule the whole format exists
to serve: extract once, read many.

**This rule is enforced, not merely advised.** `contrib/placard_read_guard.py`
is a PreToolUse hook on `Read` that refuses the original when a digest beside it
reports it can answer (see `INTEGRATION.md` §4). If a Read comes back refused,
that is the guard: read the digest and body it names. It allows the original
automatically when the digest cannot answer or is stale, and regeneration is
untouched because `digest`/`refresh` run under Bash. To open the original
deliberately anyway — pixels, exact layout, a figure's actual content — arm the
one-shot override it names:
`python3 contrib/placard_read_guard.py --allow-once <file>`.

1. Read `PROJECT.placard.md` at the root; follow the "why descend" summaries
   down through child maps. A map's **"Not digested here"** section lists
   artifacts with no digest — their content is UNKNOWN, which is not the same as
   uninteresting, so never read that list as "nothing of interest here".
2. `python3 placard.py read <artifact>` resolves the digest and prints its state
   and body. Prefer it over reading the sidecar by hand: it checks that the body
   belongs to the entry that names it, which reading the file yourself does not.
3. **Act on the state it reports:**

   | State | What to do |
   |---|---|
   | `ok` | use the body; do not open the original |
   | `legacy` | usable (`placard_version: 1`); `refresh` re-stamps it, `digest` upgrades it |
   | `source-stale` | the original changed — `digest` it again |
   | `extraction-stale` | extracted by an older profile — `digest` again |
   | `body-missing` | the named body is absent or does not match; retry, then treat as `unavailable` |
   | `unavailable` | **open the original** — the digest cannot answer |
   | `needs-source-inspection` | **open the original** — e.g. a visual question a text body cannot answer |

   The last two are the only states that authorize opening the original. A
   sidecar existing is **not** evidence that it can answer your question: an
   image digest written from a filename cannot say what the image shows.
4. The entry file is deliberately small (~1 KB) and the body is a separate file
   when it is large. Read the entry to decide; read the body only when you need
   the content.
5. Never trust a coverage claim written in prose. Coverage lives in fields
   (`units_total`, `units_total_known`, `tables_detected`, `figures_detected`,
   `summary_basis`, `authoring_status`), and `verify --deep` contradicts prose
   that disagrees with them. `authoring_status: unknown` means nobody has
   authored the summary — the body may still be complete.

## Digesting protocol (when creating/refreshing digests)

🔴 **`digest` is the only way a body is written.** It needs Docling
(`pip install docling pypdf`, or a venv that has them); every other subcommand
runs under any `python3`, stdlib only.

Figure descriptions take one of three paths, `PLACARD_DESCRIBER=api|claude|codex|auto`
(default `auto`): a Messages API credential, else the installed Claude Code CLI (`claude -p`),
else Codex (`codex exec -i`, the `chatgpt-consult` skill's container). The digest's
`figures_describer` says which one wrote the descriptions.

```
scan      what exists, what is stale          (any python3)
gaps      what has NO digest at all           (any python3)
digest    extract + clean + publish a body    (python with docling)
refresh   re-stamp a v1 digest's provenance, keep the prose
read      resolve one digest to one state     (any python3)
verify    bytes; --deep also reads each digest against itself
map       regenerate the navigation maps
sweep     list external bodies no digest names (dry run); --apply deletes them
fleet     several repos, OPT-IN: --allowlist FILE; plan unless --go
```

🔴 **A multi-repo run is opt-in.** The only supported way to digest more than one
repo is `python placard.py fleet --allowlist FILE`: FILE names the repo roots the
owner approved, one per line (`#` comments allowed). No allowlist, a glob, or a
root that is not a git repo is refused (exit 7); there is no "all of ~/dev" mode.
Personal, health, financial, household and company repos are never in scope by
default. The default prints a dry-run plan per repo (to digest, unchanged, and
refused by reason: git-crypt, `.placard-skip`, `.lodestar-untracked`, generated
collection); `--go` digests, in one process, only files whose digest is not
current (`--force` for all),
`--no-figures` spends no model calls. The guard and markers are a second fence,
never the scope. It does not commit, push or check the VPN/load rule: do those
yourself (LESSONS: "A multi-repo run is opt-in").

1. **Survey:** `python3 placard.py --root <project> gaps` (no digest) and
   `scan` (stale digests).
2. **Extract:** `python placard.py --root <project> digest <artifact>...`.
   Many paths run in one process with one Docling load (3 small PDFs: 10 s
   batched against 28 s as separate calls), each file named on failure, and a
   `TOTAL` line. A file whose digest is current (same source sha, the current
   `profile_id`, and detected figures described, unless this run passes
   `--no-figures`) prints `unchanged:` and costs nothing; `--force` re-digests
   it. This writes the body (text, tables as markdown, speaker notes, margin
   identifiers, figure descriptions when a model is configured) and empty
   prose sections. **Never paste a body by hand**; a hand-made body has no
   provenance and `verify --deep` cannot check it.
3. **Author the prose** above `## Full text`, faithfully, from the body:
   - *What this is* — 1-3 sentences.
   - *Key contents* — the substance, in the source's own terms, with anchors
     (slide/page/section) so a reader can jump precisely.
   - *Distinctive contribution* — what is unique here vs. sibling digests; note
     honest overlap ("same intro as X except…"). Keep this shallow — do not
     build a corpus-wide claim graph (that is a knowledge graph's job; see below).
   - *Open the original if…* — concrete, file-specific triggers (pixels/layout).
   - *Gaps / uncertainties* — what you left to the original.
   Then set `summary_basis` to what you actually read (`abstract`,
   `selected-sections`, or `body-gen`), `authoring_status: current`, and
   `confidence:`.
4. **When the original changes, `digest` it again.** The body is replaced and
   your prose is carried through verbatim; any change to the body text marks a
   current summary `needs-review`, because a changed number is not visible to
   any size heuristic. Re-read the body, fix the prose, set it back to `current`.
   A body refresh never widens `summary_basis`.
5. **Faithfulness rules:** condense the SUMMARY; the BODY is a transcription.
   Never invent figures, citations, or conclusions the source lacks.
6. **Author directory summaries:** for each directory, set `dir_summary:` (the
   one-line "why descend" its parent shows) and fill the `## Overview` of its
   `PROJECT.placard.md`. These are preserved across `map` regenerations.
7. **Regenerate maps:** `python3 placard.py --root <project> map` (recursive).
   Run once to scaffold, author the summaries, run again to roll them up.
8. **Verify anytime:** `python3 placard.py --root <project> verify --deep`
   (exits non-zero if any digest is stale — good for a pre-commit hook).

⛔ **`init --force` destroys authored prose.** `init` only scaffolds a digest
for an artifact `digest` cannot read.
⛔ **`contrib/backfill_bodies.py` is retired** and refuses to run; it is what
produced the false coverage claims this schema exists to prevent.

## Tiers

`skim` (header card + no full-text body; low-signal files, exact duplicates,
vector/annotation-free variants) · `standard` (full digest **with** inline
`## Full text`). Full-text bodies are written for `standard` only.

`deep` is still READ, because existing digests carry it, but is no longer
offered: nothing ever branched on it, so it was a label that changed nothing.
How much of a document the summary was authored from is now recorded in
`summary_basis` / `authoring_status`, which `verify --deep` can contradict.

## Relationship to knowledge graphs

Placard is file-layer and read-only-safe; a knowledge graph is world-layer and
mutates shared state. Do not duplicate entity or claim extraction inside a
digest: that is the graph's job. (A `graph_refs:`-style field was once
documented here; nothing ever wrote or read it, so it was removed rather than
left as a promise.)

## Schema

Canonical digest template: `schema/digest.template.md`. Full rationale: `README.md`.
