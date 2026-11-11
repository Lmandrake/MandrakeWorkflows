# Placard

*A placard is the small card beside a museum exhibit. You read the placard first, and lean in
to the artwork only if it earns your attention.*

## The problem

Projects are full of artifacts an agent cannot read cheaply: slide decks, PDFs, spreadsheets,
transcripts. Every new session that needs one pays again, by re-running a PDF parser, rendering
slides to images, or loading a whole workbook into context, and often loses what matters on the
way: speaker notes, footnotes, the one table that carries the number.

## The idea

Extract once, read many. Beside each expensive artifact Placard writes a plain markdown sidecar:

```
quarterly-review/
  PROJECT.placard.md                  <- the map: one line per file, read this first
  field-trial-report.pdf
  field-trial-report.pdf.placard.md   <- summary + the cleaned full text
  review-deck.pptx
  review-deck.pptx.placard.md         <- slides AND speaker notes, chart described
  sensor-log.xlsx
  sensor-log.xlsx.placard.md          <- every sheet, as markdown tables
```

Each digest carries a short authored summary, a `## Full text` section holding the faithful
extraction, and machine fields a script can check: the original's `source_sha256` (so a changed
original makes the digest visibly stale), the extraction profile, and counts of pages, tables
and figures. An **escalation contract**, "Open the original if…", says when the text is not
enough (pixels, exact layout). The originals are never modified.

The work splits on what can be trusted to what:

- **Deterministic, stdlib-only** (`placard.py`): hashing, staleness, the read protocol, the
  text cleaner, crash-safe publishing, map building, and `verify --deep`, which checks each
  digest's claims about itself against its own fields.
- **Extraction** (`placard.py digest`, needs Docling): PDF, PPTX, DOCX and XLSX into text and
  tables, plus speaker notes and identifiers in margins. Figures are described by a vision
  model only when a gate says the picture carries content, so logos cost nothing.
- **Meaning** (an LLM, through `SKILL.md`): the summary and the map's one-line hooks.

## The measured result

On the shipped example (a synthetic five-page report, a seven-slide deck with speaker notes and
a chart, and a two-sheet workbook), the same model answered the same 14 factual questions under
six conditions, three runs each. Answers are fixed by the generator and scored mechanically
(whole-number and whole-word checks, with wrong answers pinned in
`tests/test_example_scorer.py`); no model grades another. Token counts are the endpoint's own
`input_tokens`.

| What the model was given | Passed checks (3 runs) | Input tokens |
|---|---|---|
| The originals as native document input (deck and workbook rendered to PDF, deck with its notes pages) | 14, 14, 14 | 37,738 |
| A plain text dump, no Placard (pypdf, python-pptx with notes, openpyxl cells) | 13, 13, 13 | 2,927 |
| **The map and the three digests** | **14, 14, 14** | **7,088** |
| **The extracted bodies alone** (no authored summary, no map) | **14, 14, 14** | **3,675** |
| The map and digests *without* their bodies (authored summaries only) | 12, 12, 12 | 3,852 |
| Nothing (control) | 0, 0, 0 | 393 |

What this shows, and what it does not:

- **Against native document input, digests cost 81% fewer input tokens with no loss on these
  questions.** That ratio is about representation as much as about Placard: a careful plain
  text dump is cheaper still. What the dump lost was the chart: the only question it failed
  (`q03`, which site fell below the target drawn on the chart) is answered by the digest's
  figure description.
- **The bodies carry the result, not the summaries.** The same person wrote the questions and
  the summaries, and the summaries contain 12 of the 14 answers, so the summaries-only row is
  contaminated by construction. The bodies-only row is not: it is what `placard digest`
  extracted mechanically, and it scored 14/14 at half the cost of the full digests.
- Three questions (`q06`, `q09`, `q12`) are answerable only from speaker notes, which the
  extractor reads from the package because Docling drops them.
- One small, synthetic folder, one model (`claude-sonnet-5-5`, default temperature), questions
  not written blind. It demonstrates the workflow end to end; it is not a general compression
  ratio or an independent accuracy benchmark. The extraction and figure-description cost is
  paid once per file and is not in these numbers. Data: `examples/results.json`; harness:
  `examples/eval_qa.py`.

## 60-second quickstart

Needs only Python 3.9+; nothing to install.

```sh
git clone https://github.com/Lmandrake/Placard.git placard && cd placard
sh examples/quickstart.sh
```

It copies the example to a temporary folder, then: lists every artifact and its digest state,
runs `verify --deep`, reads one digest through the read protocol (state first, then body), and
appends a byte to the workbook to show the digest turn `source-stale` and `verify` exit 1.

To try it by hand:

```sh
python3 placard.py --root examples/quarterly-review scan
python3 placard.py --root examples/quarterly-review read examples/quarterly-review/review-deck.pptx
pip install pytest && python3 -m pytest -q   # 250+ tests; the code under test is stdlib
                                             # only, and Docling-backed tests skip without it
```

## Digesting your own folder

```sh
pip install docling pypdf        # extraction only; everything else is stdlib
python3 placard.py --root <folder> gaps                  # what has no digest
python3 placard.py --root <folder> digest <folder>/deck.pptx <folder>/*.pdf   # one Docling load
python3 placard.py --root <folder> map                   # build the PROJECT.placard.md maps
```

**Several repos at once is opt-in.** `python placard.py fleet --allowlist approved.txt` reads a
file of repo roots, one per line, and prints a dry-run plan; `--go` digests, in one process,
only files whose digest is not current. With no allowlist it refuses (exit 7), and there is no "everything under a
directory" mode: an exclusion list or a `.placard-skip` marker is a second fence, not the scope.

`digest` skips a file whose digest is current (same source sha, the current extraction
profile, and its figures described unless `--no-figures`); `--force` re-digests it.
`digest` writes the body and leaves the summary sections for an LLM to author (`SKILL.md` is
the protocol, written as a Claude Code skill). Run it again after the original changes: the
body is refreshed and authored prose is carried through, flagged for review if the body moved
materially.

**Figure descriptions are optional** (`--no-figures` turns them off) and use any Anthropic
Messages API endpoint. Everything is read from the environment when called, never defaulted:
`ANTHROPIC_BASE_URL`, a model id (`PLACARD_DESCRIBE_MODEL`, else
`ANTHROPIC_DEFAULT_SONNET_MODEL`), and a credential (`ANTHROPIC_API_KEY`, or
`ANTHROPIC_AUTH_TOKEN`, or a key-helper command in `PLACARD_API_KEY_HELPER`;
`PLACARD_USE_CLAUDE_CODE_HELPER=1` opts in to Claude Code's own `apiKeyHelper`). A missing
value is a refusal that names the variable, and the digest records the figures as not
described rather than silently empty. A description cut off by its token budget is counted as
failed, not described.

**Two more describer paths** use what is already installed: `claude` (the Claude Code CLI,
`claude -p` with only `Read`, on the machine's own account; `--bare` when an `apiKeyHelper` or key
exists) and `codex` (`codex exec -i`, natively or in the `chatgpt-consult` skill's container).
`PLACARD_DESCRIBER=api|claude|codex|auto` picks one; `auto` (the default) tries them in that
order. Haiku is refused. The digest records the route as `figures_describer`.

Dependencies, by use: none to read, verify and map digests; `docling` and `pypdf` to extract;
`pytest` to run the suite; `python-pptx`, `openpyxl` and `Pillow` to regenerate the example;
`soffice` (LibreOffice) for the evaluation's originals condition.

## Making agents use the digests

A digest only pays off if a session reads it instead of the original. `INTEGRATION.md`
describes four layers, cheapest first: the skill, an always-loaded instruction, a session-start
hook that announces a digested tree (and stays silent everywhere else), and a `Read` guard
(`contrib/placard_read_guard.py`) that refuses an original while its digest can answer, with a
one-shot override for when pixels really are needed.

## Layout of this repo

| Path | What it is |
|---|---|
| `placard.py`, `placardlib/` | the CLI and its modules (read, publish, refresh, checks, extract, figures, describe) |
| `schema/digest.template.md` | the digest format |
| `SKILL.md` | the reading and digesting protocol for an LLM |
| `INTEGRATION.md` | making sessions Placard-aware: skill, instruction, hooks |
| `PRIOR_ART.md` | the nearest neighbours (OKF, llms.txt) and what is new here |
| `docs/specs/` | the v2 design, written after an adversarial review of v1 |
| `examples/` | the synthetic folder, its generator, the questions and the QA harness |
| `contrib/` | the session hooks, an OKF conformance checker, the retired v1 writer |
| `tests/` | the suite |

## Credit

Please credit me if you find this work useful.
