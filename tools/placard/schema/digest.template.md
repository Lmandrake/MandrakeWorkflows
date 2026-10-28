---
source: FILENAME.ext
source_sha256: HEX                # gate: digest is STALE if this != current file hash
source_bytes: 0
source_modified: YYYY-MM-DD
tier: standard                    # skim | standard  (`deep` is read but no longer offered)
placard_version: 1
digested_on: YYYY-MM-DD
confidence: high                  # high | medium | low
body: full                        # full (standard+ has ## Full text) | none (skim/image)
trim_notes:                       # what the cleaner removed (when body: full)
---

# FILENAME.ext — Placard

## What this is
1-3 sentences: type, purpose, author/audience, date, why it exists in this project.

## Key contents
The substantive points, faithful to the original and in its own terms, with
anchors back to the source so a reader can jump precisely
(e.g. "architecture -> slides 12-15", "FY27 budget -> slide 22", "methods -> p.4-6").

## Distinctive contribution
What this file adds that no sibling digest does. Honest overlap notes are fine
("shares the intro with kickoff.pptx.placard.md; unique part is the cost model").
Keep shallow — not a corpus-wide claim graph.

## Open the original if…
- you need the full text — read `## Full text` below first (it is the cleaned,
  faithful extraction; prose rarely needs the original)
- you need pixels / exact layout / a figure's actual content / a table that did
  not linearize
- the source_sha256 above no longer matches the file (stale — re-digest first)
Otherwise this digest + its full text are sufficient.

## Gaps / uncertainties
What the digester could not resolve, or deliberately left to the original.

## Full text
The deterministic-cleaned, faithful, verbatim extraction of the original — extract
once, read many. Page anchors [p.N] preserved; running headers/footers, page
numbers, and line-wrap hyphens removed (see `trim_notes`). Transcription, not
summary: deletions of known noise only, never paraphrase. `skim` tier or pure
images: `_(none — see description above)_`.
