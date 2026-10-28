# Placard v2 — design spec

Status: approved for implementation 2026-10-06. Supersedes nothing; `placard_version: 1`
digests remain readable and are upgraded on access.

Evidence base: `docs/2026-10-06-redesign-consult.md` (findings + option space, and the
external review's corrections) and two comparison experiments against a Docling-based converter.

## 0. Hard invariants

1. **`announce` must work at every commit.** `placard.py` is invoked by a SessionStart hook on
   every Claude Code session on a machine where it is installed. A broken `announce` breaks every session. It must
   keep exiting 0, staying silent on unplacarded trees, and never hashing in bulk.
2. **Never edit an original.** Placard only adds sidecars.
3. **No Drive-hostile behaviour.** No `.git` in Drive folders, no lockfiles that outlive a
   process, no assumption that two files become visible in the order they were written.
4. **`placard_version: 1` digests stay readable** for as long as any exist.

## 1. What the external review changed

Three corrections are load-bearing and the design is shaped by them.

**Extraction is not authoring.** *"The summary was written from only the abstract"* can remain
true after a script appends the full body. The original diagnosis — that backfilling falsified
the Gaps sentences — was too strong. The real defect is that Placard cannot distinguish **text
that is available** from **evidence used to author the summary**. Coverage fields added without
that distinction would restate the same overclaim more convincingly.

**Two proposed `verify` checks were wrong and are dropped.** Escalation-contract-vs-`body: full`
cannot be validated generically: a complete text extraction can still justify opening the
original for figures, layout, or cell relationships. And `tier: skim` beside a full body is a
coherent combination; cost must be read from size fields, not `tier`.

**The read path is the centre, not the write path.** Mixed *data* is manageable; a mixed
population of ad-hoc *readers* is not.

## 2. Decisions (owner, 2026-10-06)

| # | Decision |
|---|---|
| D1 | Docling is a first-class dependency. One extraction path, no fallback converter. |
| D2 | Split the sidecar above a body-size threshold; small digests stay one file. The skill states that before reading any heavy file, BOTH sidecars are sought; the original is opened only if neither is present. |
| D3 | Images: caption-first, class-gated, dedup. |
| D4 | Fix forward — upgrade a digest on access or when its source changes. No bulk re-digest. |
| D5 | An `unavailable` / `needs-source-inspection` result explicitly authorizes opening the original (resolves the access trap in D2). |
| D6 | Diff-gated re-authoring: a body refresh flags the summary `needs-review` only when the change is material. |
| D7 | Bulk generated-output directories get a collection digest, not per-file digests. |

## 3. Architecture

### 3.1 `placard read <original>` — the canonical read

The only sanctioned way to consume a digest. `<original>.placard.md` is always the
authoritative entry point. An external body is selected *by* the entry file; its mere presence
on disk never makes it authoritative.

Resolves, in order: entry exists → schema version → declared layout → body integrity
(`body_sha256`) → source freshness (`source_sha256`) → extraction freshness (`profile_id`).

Returns exactly one state:

| State | Meaning | Reader action |
|---|---|---|
| `ok` | entry and body consistent, source current, profile current | use it |
| `legacy` | `placard_version: 1` | usable; upgrade offered |
| `source-stale` | source hash differs | refresh body; summary per D6 |
| `extraction-stale` | profile_id differs from current | refresh body; summary per D6 |
| `body-missing` | entry declares an external body that is absent or mismatched | re-read entry, bounded retry, then `unavailable` |
| `unavailable` | cannot produce a usable body | **open the original (D5)** |
| `needs-source-inspection` | body is fine but cannot answer a visual/layout question | **open the original (D5)** |

`body-missing` must never be satisfied by a similarly-named body file. Bounded retry exists
because on Drive the entry can become visible before its body (§3.3, S7).

### 3.2 Two derivation records

The schema separates the body's provenance from the summary's basis.

```yaml
# --- body provenance: what was extracted
extractor: docling
extractor_version: "2.115.0"
profile_id: "docling-2.115.0/text-v1/soffice-present"
extracted_at: 2026-10-06T15:40:00-07:00
source_sha256: <hash of the original>
body_sha256: <hash of the body bytes>
body_layout: inline | external
body_path: <name of the external body, when external>
body_bytes: 57139

# --- summary basis: what the author actually read
summary_basis: abstract | selected-sections | body-gen
summary_basis_sha: <body_sha256 the summary was authored against, or null>
authoring_status: current | needs-review | unknown
authored_at: 2026-10-06
```

Rules:

- A body refresh **may not** widen `summary_basis`. It may only set `authoring_status`.
- A frontmatter-only refresh may never rebind an old body or old prose to a new source hash.
- Coverage claims leave the prose entirely. `## Gaps / uncertainties` may describe only
  genuine gaps (pixels, layout, an unreadable scan) — never what was or wasn't read.
- `profile_id` includes the Docling version, the option profile, and whether LibreOffice was
  present, because that changes what gets extracted (§3.5).

This closes the failure the review found: source limit changes 20 → 12, body and
`source_sha256` refresh, prose preserved, and an obsolete claim ends up wrapped in fresh
validation metadata. `summary_basis_sha` no longer matches, so `authoring_status` moves.

**Acceptance test.** Append a complete body to an abstract-basis digest. Validation accepts the
two scopes as compatible and refuses to report that the summary now covers the document.

### 3.3 Publication protocol (D2)

The dangerous event is an entry pointing at a body from a different generation.

1. Extract from a stable snapshot of the source.
2. Write the external body to a **content-addressed** name: `<original>.placard.<sha12>.body.md`.
3. Finish and hash it.
4. Publish the entry file **last**, naming `body_layout`, `body_path`, `body_sha256`.
5. Retain superseded bodies; remove them in a separate, later sweep.
6. On missing or mismatched target: re-read the entry, bounded retry, then `unavailable`.

Threshold is measured on the **canonical body's encoded byte length**, never the entry file's
size — otherwise splitting shrinks the entry, the next run inlines it, and it oscillates.
Threshold: 8192 bytes of body.

Concurrency: before publishing, re-read the entry and abort if the source or the authored prose
changed during extraction. "Preserve prose" must not mean "overwrite a newer prose edit with
the copy I read ten seconds ago."

### 3.4 Honest denominators

The highest-`[p.N]`-anchor check is **dropped**: a 125-page PDF emitting only `[p.1]` and
`[p.125]` passes it while 123 pages are missing, and emitting all anchors before extraction
defeats even the complete-set version.

Instead, typed source units with per-unit outcomes:

| Format | Unit | Declared scope |
|---|---|---|
| PDF | physical page | attempted / extracted / failed per page |
| Deck | slide identity | hidden slides, speaker notes, embedded objects |
| Spreadsheet | worksheet identity | hidden sheets, formulas vs cached values, charts |
| CSV | parsed record under a declared dialect | header policy; line count is NOT a record count (RFC 4180 permits newlines inside quoted fields) |
| Image | asset, or frame/page | explicitly chosen |

Figure fields are reported as separate facts, never as a completeness claim:
`figures_detected`, `captions_associated`, `descriptions_completed`,
`descriptions_skipped` (with reasons), `tables_detected`, `tables_exported`.

Two absolute rules: **never render an unknown total as 0**, and **never let 0/0 read as
complete coverage**.

### 3.5 Extraction and the cleaner — preserve, don't delete

Docling replaces pypdf. The global deletion heuristics are **removed**, not improved:

- The recurring-line detector's digit masking (`re.sub(r"\d+", "#", ...)`) is deleted. It
  collapsed table rows differing only in numbers and deleted them as furniture.
- Bare-number line stripping is deleted. It destroyed data years and table cells.
- De-hyphenation is rewritten to run **after** pages are joined (so cross-page wraps are
  reachable) and only where the joined form is a plausible single token; a hyphen that is
  part of a real compound is preserved.
- A **letter-split rejoin** rule is added, with real fixtures: `1 I NTRODUCTION` →
  `1 INTRODUCTION`, `T extureCam` → `TextureCam`.
- Furniture is identified from Docling's body/furniture distinction, not from text statistics.

**Margin and footnote text is kept.** Measured: Docling drops `arXiv:2310.01798`,
`NTR #1`, `NTR #2` (invented examples), `IJCAI`, `LPSC`, while the raw text layer retains all five. A
union pass recovers them into a `## Margin and footnote text` section. These five become
regression fixtures.

**Every destructive edit is logged** — original span, source location, rule — and `trim_notes`
is *generated from that ledger*. It can no longer assert work that did not happen. A report may
say "removed 4 occurrences of 2 recurring lines"; it may not say "removed 4 headers" without a
separate basis for the classification.

The body is written **fenced/escaped** so a source line beginning `## ` cannot corrupt the
digest or cause a later run to split at the wrong boundary. The serializer must round-trip
arbitrary source headings, delimiter-like text, multiline metadata and Unicode. Ambiguous
legacy boundaries are preserved and reported, never reconstructed confidently.

### 3.6 Images (D3, D7)

Three distinct records:

- **Image observation** — facts about the rendered pixels, plus the model/profile used.
  Reusable across occurrences, keyed by content hash.
- **Figure occurrence** — source location, crop, panel/group context, associated source
  caption, and role.
- **Generated description** — always labelled as generated; never presented as the document's
  own caption.

Rules:

- Caption-first: use the document's own caption when one is associated.
- Hash-dedup reuses the **observation only**, never the occurrence. The same bitmap appearing
  as "input" and as "reconstruction" is one observation and two occurrences.
- **No perceptual dedup.** It would collapse two near-identical charts differing in one curve.
- Class-gating controls effort and must preserve evidence of exclusion: "skipped as logo",
  "classification uncertain", "description failed" may not collapse into "figures complete".
- `classification_min_confidence` and `picture_area_threshold` **silently shrink the set of
  described pictures** (verified in docling 2.115.0: pictures below the threshold are skipped).
  Both values are recorded in `profile_id`, and anything skipped is counted with its reason.

**Collection digests (D7).** Generated analysis output can dominate a tree, with
large concentrations of near-identical plots. A directory of homogeneous generated
output gets **one collection digest** describing the family, its generator, and its axes of
variation — with per-file digests only for images that are referenced elsewhere or visually
distinct. The remaining per-image vision backlog is therefore a fraction of the total.

### 3.7 Discovery

- Sidecar lookup is keyed on the **target artifact path**, not the session's cwd. A session
  that began elsewhere must still find a digest next to the file it is opening.
- Maps expose **undigested children** and distinguish *unknown* from *known-irrelevant*. An old
  "why descend" line whose basis is unknown must not support a strong exclusion decision — this
  is the self-perpetuating omission the review identified, where a wrong map prevents the access
  that would have corrected it.
- Reading a map never converts its descendants. Conversion scope stays with the selected
  artifact.
- Original-artifact enumeration excludes all generated bodies, temp files and migration
  backups, so a generated body can never acquire a digest of its own.
- **Availability is decoupled from authoring.** An artifact may carry extracted content with
  `authoring_status: unknown` and no summary yet, honestly exposed in the map. Coverage stops
  being gated on an expensive prose pass.

## 4. CLI surface

| Command | Purpose |
|---|---|
| `announce` | unchanged behaviour, unchanged speed (invariant 1) |
| `scan` | inventory + status, no bulk hashing of originals beyond what it already does |
| `read <artifact>` | §3.1 — resolve and return state + content |
| `digest <artifact>` | the single write path: extract, publish, stamp provenance |
| `refresh <artifact>` | frontmatter and/or body refresh that **never** destroys authored prose |
| `verify [--deep]` | bytes as today; `--deep` adds internal-consistency checks |
| `map` | as today, plus undigested children and status honesty |
| `gaps` | what is undigested in this tree (addresses the undigested-PDF gap) |

`init --force` stops being the remedy for staleness; `refresh` is. The three write concerns —
frontmatter, body, prose — become independently runnable.

## 5. Test plan

The repo currently has **zero tests**. Every item below is a test, not a principle.

**Preservation fixtures** (oracles written from the original, never recomputed by the cleaner):
Round 1 ↔ 62.5 / Round 2 ↔ 64.1 / Round 3 ↔ 70.9 survive *with their row association*; data
years survive; `self-correction` keeps its hyphen; a wrapped `evaluation` becomes searchable;
a table value stays under the right column and beside the right row label; the five margin
identifiers survive; an extraction failure cannot produce `body: full`.

Preserving the multiset of numbers is **not** sufficient — every value can shift one row up
and still pass. Assertions are on relationships.

**Meaning-preserving perturbations:** add unrelated pages (substantive lines must not vanish
because a threshold moved); repeat a legitimate data row on another page (repetition alone is
not furniture); move a paragraph across a page boundary; put repeated numeric lines on one page
(occurrence vs recurrence); run the output through a second pass (must not remove more prose or
reinterpret source headings as Placard sections).

**Mutation tests:** remove an interior page, swap two captions, shift table cells, delete a
minus sign. Record which gate catches which. A runtime structural check may not be credited
with detecting mutations for which only a fixture's independent answer is the oracle.

**Mixed-state tests (M1–M6):** old reader meets split digest; retired writer finishes late and
rewrites with the old parser; source unchanged but extraction profile obsolete; map advertises
a generated body; reading a map triggers bulk conversion; corrupt legacy syntax misread as
staleness.

**Publication races (S1–S7):** inline→external and external→inline crash interleavings; reader
overlapping a shrink; fixed-name body overwrite; orphan body preferred; stale external body
preferred after inlining; and **entry visible before body via Drive sync**.

**Threshold:** T−1, T, T+1 bytes; multibyte text; repeated unchanged runs; the full
inline→external→inline→external cycle with every obsolete body retained.

**Figure association fixtures:** two columns / two figures / two captions; caption above and
caption below; caption spanning columns or pages; panels A and B under one caption; a caption
that says nothing useful; one bitmap in two roles; bitmap plus differing overlays; a small
ambiguous chart excluded by threshold (its skip reason must remain visible).

**Offline/degraded acceptance test:** packages installed, model cache empty, network
unavailable, sidecar stale. The attempt must end in an explicit `unavailable` / refresh-failed
state, leave the existing sidecar intact, not hang, not write an error string as the body, and
not claim freshness.

## 6. Runtime posture (D1 mitigation)

The strongest dissent against a hard Docling dependency is not GPU — Docling runs on CPU — but
that fix-forward moves conversion onto the **live read path** just as conversion acquires model
initialization and first-use model downloads. The first useful access becomes the least
reliable one.

Mitigations, keeping one extraction path:

- One pinned environment per machine, models **prefetched** to a local artifacts path.
- Environment and model cache **off** the Drive mount.
- Ordinary map and metadata reads must not initialize Docling models.
- One prescribed conversion profile; its identity includes dependency and model revisions,
  option values, and LibreOffice presence.
- Convert a local snapshot with bounded resources; on failure, preserve the previous committed
  generation and expose the failure separately.
- A persistent worker only if measured startup cost justifies it.

## 7. Migration (D4)

Fix forward. `placard_version: 1` digests are readable indefinitely; `read` upgrades one when
it is accessed, its source changes, or its extraction profile is obsolete.

Two things cannot be deferred:

- **Writers must be retired on deployment.** Data migration can lag; a program still allowed
  to write the old shape cannot. `contrib/backfill_bodies.py` is absorbed into `digest` and
  removed as an independent entry point.
- **Legacy bytes are preserved** when a migration cannot unambiguously find a section boundary.
  Ambiguous syntax is reported separately from source staleness and never confidently
  reconstructed.

## 8. Dropped

- `confidence` — self-assessed and empirically meaningless (defective digests said
  `high`). Removed, or derived from the new fields.
- `deep` tier — code-identical to `standard`. Collapsed unless it is made mechanically real.
- `[figure p.N: …]` — documented in three places and emitted by nothing. Now either emitted for
  real by the figure pass, or deleted from the scaffold, schema and skill.
- `graph_refs` (a knowledge-graph cross-reference) — documented with no writer or reader.

## 9. Implementation order

1. Read semantics: `read`, the state machine, the two derivation records, `verify --deep`,
   and the test harness the repo has never had.
2. Safe publication and refresh: threshold transitions, prose-edit concurrency, legacy byte
   preservation, failed-refresh preservation.
3. Pinned Docling profile plus the preservation fixtures, margin-text union pass, and the
   deletion ledger.
4. Discovery: target-path lookup, maps exposing undigested children, `gaps`, collection
   digests for bulk output directories.

Open questions deliberately left open: whether a persistent Docling worker is needed (decide
from measurement), and the materiality rule for D6's diff gate (first version: identifiers
appearing, tables recovered, or a large text delta).
