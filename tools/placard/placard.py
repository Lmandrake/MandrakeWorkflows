#!/usr/bin/env python3
"""Placard — deterministic bookkeeping for per-artifact digests.

Stdlib only (no external dependencies), so it runs anywhere, including
egress- and PyPI-restricted sandboxes.

Placard splits work in two:
  * This CLI does the deterministic parts: hashing, staleness detection,
    scaffolding, and map generation. It never invents content.
  * An LLM (driven by the packaged skill) does the semantic part: reading a
    heavy artifact and faithfully filling in the digest's prose sections.

Subcommands:
  scan    List digestible artifacts and their digest status (ok/missing/stale).
  init    Write a digest SCAFFOLD beside an artifact for the LLM to fill in.
  verify  Report every digest as OK / STALE / MISSING; exit 1 if any stale.
  map     (Re)generate a PROJECT.placard.md in EVERY directory that has content
          — a recursive navigation tree, each map saying why you'd descend into
          each child directory (rolled up from the child's `dir_summary`).
  announce Report coverage for a session-start hook: counts what exists, never
          hashes, and prints NOTHING when a tree has no digests.

Two planes:
  * Navigation plane (cheap): the tree of PROJECT.placard.md maps. Walk it
    top-down paying only summary-sized tokens until you commit to a file.
  * Content plane (heavy, on demand): each `foo.ext.placard.md` digest carries a
    summary AND a `## Full text` section holding the faithful, cleaned, once-and-
    for-all text extraction of the original. Read it instead of re-ingesting the
    original; open the original only for pixels / layout / exact tables.

Sidecar convention:  foo.pptx  ->  foo.pptx.placard.md
Directory map:       PROJECT.placard.md   (one per content-bearing directory)

The CLI stays stdlib-only, so it does the deterministic parts: hashing,
staleness, scaffolding, the stdlib text CLEANER (clean_text), and recursive map
assembly. Raw extraction (pypdf / python-pptx / OCR) and all prose — the
summary, the per-directory `dir_summary`/Overview, and feeding clean_text — are
the LLM/skill's job.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

from placardlib import checks as _checks
from placardlib import publish as _publish
from placardlib import read as _read
from placardlib import refresh as _refresh
from placardlib import schema as _schema

SIDECAR_SUFFIX = ".placard.md"
MAP_NAME = "PROJECT.placard.md"
PLACARD_VERSION = 1

# Heavy / expensive artifact types worth digesting.
DIGESTIBLE_EXTS = {
    ".pptx", ".potx", ".ppt", ".key",
    ".pdf",
    ".docx", ".doc", ".pages", ".rtf",
    ".xlsx", ".xlsm", ".xltx", ".xls", ".csv", ".tsv",
    ".ipynb",
    # Images: figures, posters, one-slide stories carry information locked in
    # pixels that an LLM would otherwise have to re-open and re-read every time.
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".bmp", ".svg",
}
# Directories we never descend into.
ANNOUNCE_SKIP = {"Library", "Applications", "Pictures", "Movies", "Music", "target", "build", "dist"}
ANNOUNCE_BUDGET_S = 4.0
ANNOUNCE_MAX_FILES = 50000
SKIP_DIRS = {".git", ".svn", "node_modules", "__pycache__", ".venv", "venv"}

# Tier default. Depth MUST track information value, which the CLI cannot see
# (file size is a demonstrably poor proxy — dense proposals under-tier, bulky
# boilerplate over-tiers). So the CLI assigns a neutral default and the reading
# step (LLM) sets the real tier: skim | standard.
# `deep` is still READ (existing digests carry it) but is no longer
# offered: nothing in this codebase ever branched on it, so it was a
# label that changed nothing. Depth of authoring is now carried by
# summary_basis / authoring_status, which a checker can contradict.
DEFAULT_TIER = "standard"


# --------------------------------------------------------------------------- #
# Minimal YAML-ish frontmatter (flat scalars only — sufficient for Placard).
# --------------------------------------------------------------------------- #
def parse_frontmatter(text: str) -> dict:
    """Return the frontmatter dict of a markdown string ({} if none)."""
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip()
    return fm


def dump_frontmatter(fm: dict) -> str:
    body = "\n".join(f"{k}: {v}" for k, v in fm.items())
    return f"---\n{body}\n---\n"


# --------------------------------------------------------------------------- #
# Deterministic text cleaner (stdlib) — turns raw per-page extraction into a
# faithful, cleaned body suitable for the digest's `## Full text` section.
#
# Design contract: this is a TRANSCRIPTION cleaner, not a summarizer. It only
# DELETES text it is confident is noise (running headers/footers, page-number
# lines, hard-wrap hyphenation) and normalizes whitespace. It never paraphrases,
# reorders, or invents. Substantive prose, tables, captions, and footnotes are
# preserved verbatim. Page anchors [p.N] are inserted so digest anchors resolve
# and a reader can still cite by page.
# --------------------------------------------------------------------------- #
_PAGENUM_RE = re.compile(
    r"^\s*(?:page\s+)?\d{1,4}\s*(?:/\s*\d{1,4}|of\s+\d{1,4})?\s*$",
    re.IGNORECASE,
)


def _norm_line(s: str) -> str:
    """Normalize a line for repeat-detection: drop digits (page numbers vary)
    and collapse whitespace, so 'Foo · page 3' and 'Foo · page 4' match."""
    return re.sub(r"\d+", "#", " ".join(s.split())).strip().lower()


def clean_text(pages: list[str], *, header_footer_frac: float = 0.4) -> tuple[str, list[str]]:
    """Clean a list of per-page raw text strings into one faithful body.

    Returns (cleaned_text, trim_notes). trim_notes is a short human-readable
    list of what was removed, for the digest's `trim_notes:` frontmatter.

    Steps (all deterministic, deletion-only):
      1. Detect near-boilerplate lines that recur on >= header_footer_frac of
         pages (normalized, digits masked) — running headers/footers — and drop.
      2. Drop lines that are only a page number ('12', 'Page 3', '3 / 20').
      3. De-hyphenate words split across a line wrap ('infra-\\nstructure').
      4. Collapse 3+ blank lines to one; strip trailing whitespace.
      5. Prefix each page with a [p.N] anchor.
    """
    notes: list[str] = []
    n = len(pages)
    # 1. find recurring header/footer lines
    counts: Counter[str] = Counter()
    for pg in pages:
        seen = set()
        for ln in pg.splitlines():
            key = _norm_line(ln)
            if len(key) >= 4 and key not in seen:  # ignore trivial/blank lines
                seen.add(key)
                counts[key] += 1
    threshold = max(2, int(round(header_footer_frac * n))) if n > 1 else n + 1
    boiler = {k for k, c in counts.items() if c >= threshold}
    if boiler:
        notes.append(f"removed {len(boiler)} recurring header/footer line(s)")

    dropped_pagenums = 0
    out_pages: list[str] = []
    for i, pg in enumerate(pages, 1):
        kept: list[str] = []
        for ln in pg.splitlines():
            stripped = ln.strip()
            if _PAGENUM_RE.match(stripped):
                dropped_pagenums += 1
                continue
            if _norm_line(ln) in boiler:
                continue
            kept.append(ln.rstrip())
        body = "\n".join(kept)
        # 3. de-hyphenate line-wrapped words
        body = re.sub(r"(\w)-\n(\w)", r"\1\2", body)
        # 4. collapse excessive blank lines
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if body:
            out_pages.append(f"[p.{i}]\n{body}")
    if dropped_pagenums:
        notes.append(f"stripped {dropped_pagenums} page-number line(s)")
    notes.append("de-hyphenated line wraps; collapsed whitespace")
    return "\n\n".join(out_pages).strip(), notes


# Abbreviations that end in a period but do NOT end a sentence — so the map's
# one-line hook doesn't get chopped at "Dr." or a single-letter initial.
_ABBREV = {
    "dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "vs", "eg", "ie",
    "etc", "inc", "ltd", "no", "fig", "eq", "cf", "al", "approx", "dept",
}


def first_sentence(text: str) -> str:
    """The first sentence of `text`, not breaking on common abbreviations or
    single-letter initials (e.g. 'Dr.', 'PM/CAM A.')."""
    i = 0
    while True:
        idx = text.find(". ", i)
        if idx == -1:
            return text
        word = text[:idx].rsplit(" ", 1)[-1].rstrip(".").lower()
        if word in _ABBREV or len(word) <= 1:
            i = idx + 2
            continue
        return text[:idx + 1]


def section_text(text: str, heading: str) -> str:
    """Return the prose under a '## heading' up to the next '## '."""
    lines = text.splitlines()
    out, capturing = [], False
    for line in lines:
        if line.strip().lower() == f"## {heading}".lower():
            capturing = True
            continue
        if capturing and line.startswith("## "):
            break
        if capturing:
            out.append(line)
    return "\n".join(out).strip()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sidecar_for(artifact: Path) -> Path:
    return artifact.with_name(artifact.name + SIDECAR_SUFFIX)


def is_sidecar(path: Path) -> bool:
    return path.name.endswith(SIDECAR_SUFFIX)


def tier_of(artifact: Path) -> str:
    """The tier recorded in the sidecar, or '-' if not yet digested."""
    side = sidecar_for(artifact)
    if not side.exists():
        return "-"
    fm = parse_frontmatter(side.read_text(encoding="utf-8", errors="replace"))
    return fm.get("tier", "-")


def iter_artifacts(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if is_sidecar(p) or p.name == MAP_NAME:
                continue
            if p.suffix.lower() in DIGESTIBLE_EXTS:
                yield p


def status_of(artifact: Path) -> str:
    """ok | scaffolded | stale | missing

    scaffolded = a sidecar exists and its hash is current, but the prose has not
    been authored yet. A hash match alone does not mean the digest is usable, so
    scaffolds are reported distinctly from finished ones.

    Both schema versions are recognised: v1 marked an unfilled scaffold with
    `confidence: TODO`, v2 with `authoring_status: unknown`.
    """
    side = sidecar_for(artifact)
    if not side.exists():
        return "missing"
    fm = parse_frontmatter(side.read_text(encoding="utf-8", errors="replace"))
    stored = fm.get("source_sha256", "")
    if not stored or stored != sha256_of(artifact):
        return "stale"
    if fm.get("confidence", "").strip().upper() == "TODO":
        return "scaffolded"
    if fm.get("authoring_status", "").strip().lower() == "unknown":
        return "scaffolded"
    return "ok"


def rel(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #
def cmd_scan(root: Path) -> int:
    arts = sorted(iter_artifacts(root))
    if not arts:
        print(f"No digestible artifacts under {root}")
        return 0
    counts = {"ok": 0, "scaffolded": 0, "stale": 0, "missing": 0}
    print(f"{'STATUS':11} {'TIER':9} {'SIZE':>10}  PATH")
    for a in arts:
        st = status_of(a)
        counts[st] += 1
        size = a.stat().st_size
        print(f"{st:11} {tier_of(a):9} {size:>10}  {rel(root, a)}")
    print(f"\n{len(arts)} artifacts — "
          f"{counts['ok']} ok, {counts['scaffolded']} scaffolded, "
          f"{counts['stale']} stale, {counts['missing']} missing")
    return 0


SCAFFOLD_BODY = """
# {name} — Placard

## What this is
_(1-3 sentences: type, purpose, author/audience, date, why it is in this project.)_

## Key contents
_(What is IN this file, faithful to the original, with anchors back to the source.)_

## Distinctive contribution
_(What is UNIQUE here relative to the rest of the project. Honest overlap notes OK.)_

## Open the original if…
- you need the full text — read the `## Full text` section below first (it is the
  cleaned, faithful extraction; you should rarely need the original for prose)
- you need pixels / exact layout / a figure's actual content / a table that did
  not linearize cleanly
- the source hash above no longer matches the file (digest is stale — run
  `refresh`, which re-stamps provenance without destroying this prose)
_(Add file-specific triggers. Otherwise this digest + its full text are sufficient.)_

## Gaps / uncertainties
_(What the digester could not resolve or deliberately left to the original.)_

## Full text
_(standard+ tier: the deterministic-cleaned, faithful, verbatim extraction of the
original goes here — extract once, read many. skim tier or pure images: leave as
"_(none — see description above)_". Page anchors [p.N] preserved.)_
"""


def cmd_init(root: Path, artifact: Path, tier: str | None, force: bool) -> int:
    if not artifact.exists():
        print(f"error: {artifact} does not exist", file=sys.stderr)
        return 2
    side = sidecar_for(artifact)
    if side.exists() and not force:
        print(f"exists: {rel(root, side)} (use --force to overwrite scaffold)")
        return 0
    if side.exists() and force:
        print("warning: --force overwrites the whole sidecar, including authored "
              "prose. To clear staleness without losing prose, use `refresh`.")
    stat = artifact.stat()
    fm = {
        "source": artifact.name,
        "source_sha256": sha256_of(artifact),
        "source_bytes": str(stat.st_size),
        "source_modified": _dt.date.fromtimestamp(stat.st_mtime).isoformat(),
        "tier": tier or DEFAULT_TIER,
        "placard_version": str(PLACARD_VERSION),
        "digested_on": _dt.date.today().isoformat(),
        "summary_basis": "unknown",   # abstract | selected-sections | body-gen
        "authoring_status": "unknown",  # current | needs-review | unknown
        "body": "none",        # LLM sets: full (standard+) | none (skim/image)
        "trim_notes": "",      # what the cleaner removed (set when body=full)
    }
    side.write_text(
        dump_frontmatter(fm) + SCAFFOLD_BODY.format(name=artifact.name),
        encoding="utf-8",
    )
    print(f"scaffolded: {rel(root, side)}")
    print(f"  -> read {rel(root, artifact)} and fill the prose sections faithfully")
    print(f"  -> set tier by information value (skim|standard), not file size")
    return 0


def cmd_verify(root: Path) -> int:
    arts = sorted(iter_artifacts(root))
    stale, scaffolded, missing = [], [], []
    for a in arts:
        st = status_of(a)
        if st == "stale":
            stale.append(a)
        elif st == "scaffolded":
            scaffolded.append(a)
        elif st == "missing":
            missing.append(a)
    for a in missing:
        print(f"MISSING     {rel(root, a)}")
    for a in scaffolded:
        print(f"SCAFFOLDED  {rel(root, a)}")
    for a in stale:
        print(f"STALE       {rel(root, a)}")
    ok = len(arts) - len(stale) - len(scaffolded) - len(missing)
    print(f"\n{ok}/{len(arts)} digests current; "
          f"{len(scaffolded)} scaffolded (unfilled), "
          f"{len(stale)} stale, {len(missing)} missing")
    # Non-zero if anything exists but is not a finished, current digest:
    # a stale or unfilled sidecar is a digest you cannot trust yet.
    return 1 if (stale or scaffolded) else 0


def cmd_read(root: Path, artifact: Path) -> int:
    """The canonical read. Resolve one entry file to one identified generation
    and say plainly whether the original may be opened.

    Hashes the artifact, so it is correct for a single-file read and must never
    be called from `announce` or `map` (see the hook invariant).
    """
    side = sidecar_for(artifact)
    if not side.exists():
        print(f"state: unavailable  ({rel(root, side)} does not exist)")
        print("  -> open the original; there is no digest to read")
        return 1
    entry_text = side.read_text(encoding="utf-8", errors="replace")

    def load_body(name: str):
        candidate = side.with_name(name)
        if not candidate.exists():
            return None
        return candidate.read_text(encoding="utf-8", errors="replace")

    result = _read.resolve_with_retry(
        entry_text,
        source_sha256=sha256_of(artifact) if artifact.exists() else None,
        current_profile_id=None,          # subsystem 3 supplies the real profile
        load_body=load_body,
        sha256_of_text=lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest(),
        reread_entry=lambda: (side.read_text(encoding="utf-8", errors="replace")
                              if side.exists() else None),
    )
    print(f"state: {result.state}" + (f"  ({result.detail})" if result.detail else ""))
    if _read.authorizes_original(result.state):
        print("  -> open the original; this digest cannot answer")
    if result.body:
        print()
        print(result.body)
    return 0 if result.state in ("ok", "legacy") else 1


def cmd_refresh(root: Path, artifact: Path) -> int:
    """Re-stamp provenance and re-publish through the safe protocol, without
    touching authored prose. This is the remedy for staleness; `init --force`
    is not."""
    side = sidecar_for(artifact)
    if not side.exists():
        print(f"error: no digest at {rel(root, side)} — use `init` first",
              file=sys.stderr)
        return 2
    if not artifact.exists():
        print(f"error: {rel(root, artifact)} does not exist", file=sys.stderr)
        return 2
    entry_text = side.read_text(encoding="utf-8", errors="replace")
    view = _schema.load_digest(entry_text)

    def load_body(name: str):
        candidate = side.with_name(name)
        return (candidate.read_text(encoding="utf-8", errors="replace")
                if candidate.exists() else None)

    if view.body_layout == "external" and view.body_path:
        body = load_body(view.body_path) or ""
    else:
        body = _schema.inline_body(view.markdown)

    try:
        fm = _refresh.refresh_body(
            entry_text=entry_text,
            sidecar_path=side,
            original_name=artifact.name,
            new_body=body,
            new_fields={"source_sha256": sha256_of(artifact),
                        "source_bytes": str(artifact.stat().st_size)},
            write_text=lambda p, t: Path(p).write_text(t, encoding="utf-8"),
            load_body=load_body,
            reread_entry=lambda: (
                side.read_text(encoding="utf-8", errors="replace")
                if side.exists() else None),
        )
    except _refresh.ProseConflict as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 5
    print(f"refreshed: {rel(root, side)}  "
          f"(layout {fm['body_layout']}, "
          f"authoring_status {fm.get('authoring_status')})")
    print("  -> authored prose carried through verbatim")
    return 0


def _describe_figures(result, enabled: bool) -> tuple:
    """Describe the figures that earn it; account for the ones that do not.

    Gating is the whole point. Measured over 31 real figures, an ungated pass
    sent its detailed prompt to all of them -- six were logos -- and averaged
    2,135 characters each, while ten added at most one term the text already
    carried. Here the gate in figures.py picks the depth and the skips keep
    their reasons, so a digest can never report figures complete when a third
    were quietly dropped.
    """
    from placardlib import describe as _describe
    from placardlib import figures as _figures

    records = list(getattr(result, "figures", []) or [])
    if not records:
        return {}, ""
    if not enabled:
        return {"figures_described": "0",
                "figures_description_note": "description pass not requested"}, ""

    _describe.load_env()
    ready, reason = _describe.available()
    if not ready:
        # Visibly absent, never silently empty.
        return {"figures_described": "0",
                "figures_described_known": "false",
                "figures_description_note": reason}, ""

    inv = _figures.Inventory()
    page_area = 612.0 * 792.0          # a letter page in points; area_frac only
    for page, data, caption, cls, area in records:
        frac = (area / page_area) if area else None
        inv.add(page=page, image_bytes=(data or b""), caption=caption,
                docling_class=cls, area_frac=frac)

    describer = None
    described, failed, lines = 0, 0, []
    cache: dict = {}
    for occ, (page, data, caption, cls, _area) in zip(inv.occurrences, records):
        depth = occ.decision.depth
        if depth in ("skip", "caption-only") or not data:
            if not data and depth not in ("skip", "caption-only"):
                failed += 1
                lines.append(f"[figure p.{page}: image bytes unavailable — "
                             f"not described]")
            continue
        if occ.observation_key in cache:
            text = cache[occ.observation_key]           # same pixels, one call
        else:
            if describer is None:
                try:
                    describer = _describe.Describer()
                except _describe.DescribeUnavailable as exc:
                    return ({"figures_described": "0",
                             "figures_described_known": "false",
                             "figures_description_note": str(exc)}, "")
            try:
                text = describer.describe_image(
                    data, depth=depth,
                    media_type="image/png", caption=caption)
            except _describe.DescribeUnavailable as exc:
                failed += 1
                lines.append(f"[figure p.{page}: description failed — "
                             f"{str(exc)[:120]}]")
                continue
            cache[occ.observation_key] = text
        described += 1
        head = f"[figure p.{page}: {caption.strip()}]" if caption else \
               f"[figure p.{page}]"
        lines.append(f"{head}\n{text}")

    counts = inv.accounting()
    counts["figures_described"] = str(described)
    counts["figures_described_known"] = "true"
    counts["figures_description_failed"] = str(failed)
    counts["skip_reasons"] = str(counts.get("skip_reasons", {}))
    counts["unique_images"] = str(counts.get("unique_images", 0))
    for key in ("figures_detected", "captions_associated",
                "descriptions_planned", "descriptions_skipped"):
        counts[key] = str(counts.get(key, 0))
    if describer is not None:
        counts["figure_model"] = _describe.model_label(describer.model)
    section = ("## Figures\n\nGenerated descriptions, not the document's own "
               "captions.\n\n" + "\n\n".join(lines)) if lines else ""
    return counts, section


def cmd_digest(root: Path, artifact: Path, option_profile: str,
               describe_figures: bool = True) -> int:
    """The single write path: extract, clean, publish. Replaces the old
    contrib/backfill_bodies.py, which preserved authored prose it had just
    invalidated and recorded nothing about having done so."""
    from placardlib import cleaner as _cleaner
    from placardlib import extract as _extract

    if not artifact.exists():
        print(f"error: {rel(root, artifact)} does not exist", file=sys.stderr)
        return 2

    # Owner's ruling: a directory of generated plots is described AS A FAMILY,
    # never file by file — N descriptions of the same plot family is a huge
    # waste. So BLOCK the per-file vision path rather than relying on nobody
    # taking it: a sweep that digests every artifact in a tree would otherwise
    # spend hundreds of calls without anyone deciding to. Checked before the
    # Docling probe, because this refusal needs no extractor at all.
    if describe_figures:
        from placardlib import collection as _collection
        member, verdict = _collection.member_of_collection(artifact)
        if member:
            print(f"refusing: {rel(root, artifact)} is one of "
                  f"{verdict.count} generated images in this directory.",
                  file=sys.stderr)
            print(f"  {verdict.reason}", file=sys.stderr)
            print(f"  -> describe the FAMILY once instead:\n"
                  f"     placard collection {rel(root, artifact.parent)}\n"
                  f"  -> or pass --no-figures to digest this one file's text "
                  f"without a vision call.", file=sys.stderr)
            return 4

    if not _extract.docling_available():
        print("error: docling is not importable in this interpreter.\n"
              "  Fix: .venv/bin/python placard.py digest <artifact>",
              file=sys.stderr)
        return 3

    side = sidecar_for(artifact)
    try:
        result = _extract.extract(artifact, option_profile=option_profile,
                                  want_figures=describe_figures)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    cleaned = _cleaner.clean(result.pages)
    body = cleaned.text
    if result.margin:
        body += ("\n\n## Margin and footnote text\n"
                 + "\n".join(f"- {m}" for m in result.margin))

    fig_counts, fig_section = _describe_figures(result, describe_figures)
    if fig_section:
        body += "\n\n" + fig_section

    stat = artifact.stat()
    fields = {
        "source": artifact.name,
        "source_sha256": sha256_of(artifact),
        "source_bytes": str(stat.st_size),
        "source_modified": _dt.date.fromtimestamp(stat.st_mtime).isoformat(),
        "placard_version": "2",
        "extractor": result.profile_id.split("/")[0],
        "profile_id": result.profile_id,
        "extracted_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "units_kind": result.units_kind,
        "units_total": str(result.units_total),
        "units_total_known": "true" if result.units_known else "false",
        "units_failed": str(result.units_failed),
        "tables_detected": str(result.tables_detected),
        "tables_exported": str(result.tables_exported),
        "figures_detected": str(result.figures_detected),
        "figures_detected_known": "true",
        "trim_notes": "; ".join(cleaned.notes),
    }
    fields.update(fig_counts)
    if result.margin_unavailable:
        fields["margin_unavailable"] = result.margin_unavailable

    if side.exists():
        entry_text = side.read_text(encoding="utf-8", errors="replace")
        try:
            fm = _refresh.refresh_body(
                entry_text=entry_text, sidecar_path=side,
                original_name=artifact.name, new_body=body, new_fields=fields,
                write_text=lambda p, t: Path(p).write_text(t, encoding="utf-8"),
                reread_entry=lambda: (
                    side.read_text(encoding="utf-8", errors="replace")
                    if side.exists() else None),
            )
        except _refresh.ProseConflict as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 5
        print(f"re-digested: {rel(root, side)}  "
              f"(authoring_status {fm.get('authoring_status')})")
        print("  -> authored prose carried through verbatim")
    else:
        fields["summary_basis"] = "unknown"
        fields["authoring_status"] = "unknown"
        fm = _publish.publish_digest(
            sidecar_path=side, original_name=artifact.name, body_text=body,
            frontmatter_fields=fields,
            prose_markdown=SCAFFOLD_BODY.format(name=artifact.name).split(
                "\n## Full text")[0].rstrip() + "\n",
            write_text=lambda p, t: Path(p).write_text(t, encoding="utf-8"),
        )
        print(f"digested: {rel(root, side)}")
        print("  -> prose sections are unfilled; authoring_status is 'unknown'")
    print(f"  layout {fm['body_layout']}, {result.units_total} page(s), "
          f"{result.tables_detected} table(s), "
          f"{result.figures_detected} figure(s), "
          f"{len(result.margin)} margin identifier(s)")
    if cleaned.notes:
        print(f"  cleaner: {'; '.join(cleaned.notes)}")
    return 0


def cmd_gaps(root: Path) -> int:
    """What is undigested here. The measured failure mode was never-digested,
    not digested-and-bypassed, so absence has to be visible."""
    from placardlib import discovery as _discovery

    report = _discovery.gaps(root)
    if report.total == 0:
        print(f"No digestible artifacts under {root}")
        return 0
    for path in report.undigested[:200]:
        print(f"UNDIGESTED  {rel(root, path)}")
    frac = report.coverage_frac
    print(f"\n{report.digested}/{report.total} digested"
          + (f" ({100 * frac:.0f}%)" if frac is not None else " (undefined)"))
    for ext, slot in sorted(report.by_ext.items(),
                            key=lambda kv: -(kv[1]["total"] - kv[1]["digested"])):
        missing = slot["total"] - slot["digested"]
        if missing:
            print(f"  {ext:<8} {missing:>5} undigested of {slot['total']}")
    return 0


def cmd_collection(root: Path, directory: Path, describe_figures: bool) -> int:
    """One digest for a directory of generated output.

    Large trees of generated plots hold many near-identical images. A family
    digest costs a few vision calls instead of one per image
    and states plainly how many files were actually looked at.
    """
    from placardlib import collection as _collection
    from placardlib import describe as _describe

    if not directory.is_dir():
        print(f"error: {rel(root, directory)} is not a directory",
              file=sys.stderr)
        return 2
    names, verdict = _collection.classify(directory)
    if not verdict.is_collection:
        print(f"not a collection: {rel(root, directory)}")
        print(f"  {verdict.reason}")
        print("  -> digest these individually instead")
        return 1

    samples = []
    if describe_figures:
        _describe.load_env()
        ready, reason = _describe.available()
        if not ready:
            print(f"warning: describing unavailable — {reason}", file=sys.stderr)
        else:
            describer = _describe.Describer()
            for name in _collection.sample_paths(names):
                data = (directory / name).read_bytes()
                try:
                    text = describer.describe_image(
                        data, depth="brief",
                        media_type=_describe.media_type_for(name))
                except _describe.DescribeUnavailable as exc:
                    print(f"warning: {name}: {str(exc)[:120]}", file=sys.stderr)
                    text = None
                samples.append((name, text))
    if not samples:
        samples = [(n, None) for n in _collection.sample_paths(names)]

    out = directory / _collection.COLLECTION_NAME
    out.write_text(_collection.render(directory, names, verdict, samples),
                   encoding="utf-8")
    described = sum(1 for _n, d in samples if d)
    print(f"collection digest: {rel(root, out)}")
    print(f"  {verdict.count} files described as one family "
          f"({described} sampled and looked at)")
    print(f"  shared: {verdict.shared_stem or '(none)'}")
    return 0


def cmd_prefetch(root: Path) -> int:
    """Download the extraction models now, so a first digest is not the moment
    the network becomes load-bearing.

    Docling downloads its layout and table models on first use. That puts a
    network dependency on the FIRST useful access to a document -- the access
    most likely to be in the middle of someone's actual work, and the one that
    looks like a hang rather than a download.
    """
    from placardlib import extract as _extract

    if not _extract.docling_available():
        print("error: docling is not importable in this interpreter.\n"
              "  Fix: .venv/bin/python placard.py prefetch", file=sys.stderr)
        return 3
    from docling.utils.model_downloader import download_models

    target = Path(os.environ.get("DOCLING_ARTIFACTS_PATH",
                                 Path.home() / ".cache" / "docling" / "models"))
    print(f"downloading extraction models to {target}")
    print("  (this is the download a first `digest` would otherwise trigger)")
    try:
        download_models(output_dir=target, progress=False,
                        with_layout=True, with_tableformer=True)
    except Exception as exc:
        print(f"error: model download failed ({type(exc).__name__}: {exc})\n"
              f"  Placard still works -- the models will be fetched on first "
              f"use instead.", file=sys.stderr)
        return 1
    print(f"done. Set DOCLING_ARTIFACTS_PATH={target} to pin this location,")
    print("and keep it off the Drive mount.")
    return 0


def cmd_verify_deep(root: Path) -> int:
    """verify's byte check, plus reading each digest against itself."""
    rc = cmd_verify(root)
    total = 0
    for artifact in sorted(iter_artifacts(root)):
        side = sidecar_for(artifact)
        if not side.exists():
            continue
        view = _schema.load_digest(side.read_text(encoding="utf-8", errors="replace"))
        if view.body_layout == "external" and view.body_path:
            target = side.with_name(view.body_path)
            body_text = (target.read_text(encoding="utf-8", errors="replace")
                         if target.exists() else "")
        else:
            body_text = _schema.inline_body(view.markdown)
        for f in _checks.check_digest(view, body_text=body_text):
            total += 1
            print(f"{f.code:28} {rel(root, side)}\n{'':28} {f.message}")
    print(f"\n{total} internal-consistency finding(s)")
    return 1 if (total or rc) else 0


def cmd_announce(root: Path, max_depth: int) -> int:
    """Report Placard coverage of a tree — built for a session-start hook.

    Deliberately cheap and deliberately quiet. Three constraints separate this
    from `verify`, which is the wrong tool for the job:

    * **No hashing.** Staleness needs every original's bytes; a hook that reads
      every deck in a project to start a session is a hook people uninstall.
      `verify` still does that, on demand.
    * **Silent when nothing is digested.** `verify` at a Drive root truthfully
      reports thousands "missing", but at session start that reads as a to-do
      list and pushes a session into digesting work nobody asked for. Absence
      of digests is not news; presence is.
    * **Depth-capped**, so pointing it at a home directory or a mounted cloud
      drive stays a fraction of a second.

    Counts only what exists. Exits 0 always — a hook must never fail a session.
    """
    digests: list[Path] = []
    maps: list[Path] = []
    root_depth = len(root.parts)
    deadline = time.monotonic() + ANNOUNCE_BUDGET_S
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        seen += len(filenames)
        if seen > ANNOUNCE_MAX_FILES or time.monotonic() > deadline:
            break                       # bounded: a hook must never near its limit
        if len(d.parts) - root_depth >= max_depth:
            dirnames[:] = []            # stop descending, still scan this level
        else:
            dirnames[:] = [x for x in dirnames
                           if x not in SKIP_DIRS and x not in ANNOUNCE_SKIP
                           and not x.startswith(".")]
        for name in filenames:
            if name == MAP_NAME:        # a map is also a *.placard.md — test first
                maps.append(d / name)
            elif name.endswith(SIDECAR_SUFFIX):
                digests.append(d / name)

    if not digests and not maps:
        return 0                        # silence is the whole point

    if (root / MAP_NAME).exists():
        entry = MAP_NAME
    else:
        # No map at the root: name the shallowest ones so the session still has
        # somewhere to start reading.
        shallow = sorted(maps, key=lambda p: (len(p.parts), str(p)))[:3]
        entry = ", ".join(rel(root, m) for m in shallow) or \
            "(no map yet — run `placard map` to build one)"

    print(f"Placard: {len(digests)} digest(s) under {len(maps)} map(s) in this "
          f"tree. Entry point: {entry}")
    print("Read the map first and follow its \"why descend\" summaries down. A "
          "digest's `## Full text` section is the original's cleaned full "
          "extraction — read that instead of re-opening the original. Open an "
          "original only when its digest's \"Open the original if…\" contract "
          "fires (pixels, exact layout, a figure's real content). Staleness is "
          "not checked here — run `placard verify` if a digest looks out of date.")
    return 0


def _hook_of(sidecar: Path) -> tuple[dict, str]:
    """(frontmatter, one-line 'what this is' hook) for a file sidecar."""
    text = sidecar.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    hook = " ".join(section_text(text, "What this is").split())
    if hook.startswith("_(") or not hook:
        hook = "(not yet digested)"
    else:
        hook = first_sentence(hook)
        if len(hook) > 220:
            hook = hook[:217].rstrip() + "…"
    return fm, hook


def _read_map_preserved(mappath: Path) -> tuple[str, str]:
    """(dir_summary, overview) authored content to carry across regenerations."""
    if not mappath.exists():
        return ("TODO", "")
    text = mappath.read_text(encoding="utf-8", errors="replace")
    ds = parse_frontmatter(text).get("dir_summary", "TODO")
    ov = section_text(text, "Overview")
    if ov.startswith("_(") or not ov.strip():
        ov = ""
    return (ds, ov)


def _undigested_here(d: Path) -> list:
    """Digestible artifacts in `d` with no sidecar beside them.

    Cheap by construction: one directory listing, no hashing, no recursion --
    `map` must not become something people stop running.
    """
    out = []
    try:
        entries = sorted(p for p in d.iterdir() if p.is_file())
    except OSError:
        return out
    for p in entries:
        if is_sidecar(p) or p.name == MAP_NAME or p.name.endswith(".body.md"):
            continue
        if p.suffix.lower() not in DIGESTIBLE_EXTS:
            continue
        if not sidecar_for(p).exists():
            out.append(p.name)
    return out


def _write_dir_map(root: Path, d: Path, direct: dict,
                   children: dict, count: dict) -> int:
    """Write d/PROJECT.placard.md. Returns number of digests in this subtree.

    `direct[d]` is the list of file sidecars directly in d, `children[d]` the
    list of child content-dirs, and `count[d]` the precomputed subtree digest
    count (see cmd_map). This is O(1) per directory rather than rescanning all
    sidecars per directory (which is quadratic on large trees)."""
    ds, overview = _read_map_preserved(d / MAP_NAME)
    child_dirs = sorted(children[d])
    here = sorted(direct[d])
    sub = count[d]

    label = d.name if d != root else root.name
    fm = {
        "dir_summary": ds,
        "placard_version": str(PLACARD_VERSION),
        "generated_on": _dt.date.today().isoformat(),
        "digests_in_subtree": str(sub),
    }
    lines = [dump_frontmatter(fm).rstrip(), ""]
    lines += [
        f"# {label} — Placard map",
        "",
        "Navigation plane. Walk this tree top-down: read a child's one-line "
        "summary to decide whether to descend. Open a file's digest for its "
        "summary **and** full cleaned text; open the original file only for "
        "pixels, exact layout, or a figure's actual content.",
        "",
    ]
    lines += ["## Overview", ""]
    lines.append(overview if overview else
                 "_(TODO: what is in this directory and why you'd come here.)_")
    lines.append("")

    if child_dirs:
        lines += ["## Subdirectories — why descend", ""]
        for cd in child_dirs:
            cds, _ = _read_map_preserved(cd / MAP_NAME)
            csub = count[cd]
            why = cds if cds and cds != "TODO" else "_(summary pending)_"
            lines.append(f"- **{cd.name}/** — {why}  ")
            lines.append(f"  {csub} digest(s) · "
                         f"[map]({cd.name}/{MAP_NAME})")
        lines.append("")

    if here:
        lines += ["## Files here", ""]
        for s in here:
            fmc, hook = _hook_of(s)
            src = fmc.get("source", s.name.replace(SIDECAR_SUFFIX, ""))
            tier = fmc.get("tier", "?")
            conf = fmc.get("confidence", "?")
            body = fmc.get("body", "none")
            btag = " · full-text" if body.strip() == "full" else ""
            lines.append(f"- **{src}** — {hook}  ")
            lines.append(f"  tier: {tier} · confidence: {conf}{btag} · "
                         f"[digest]({s.name})")
        lines.append("")

    # An honest map names what it does NOT cover. Without this, a directory
    # whose useful paper was never digested looks empty of interest, so the
    # access that would have produced the digest never happens -- the
    # self-perpetuating omission. A third of PDFs fleet-wide have no digest.
    undigested = _undigested_here(d)
    if undigested:
        lines += ["## Not digested here", "",
                  "These artifacts have no digest. Their content is UNKNOWN, "
                  "which is not the same as uninteresting — do not treat this "
                  "list as covered.", ""]
        for name in undigested[:50]:
            lines.append(f"- {name}")
        if len(undigested) > 50:
            lines.append(f"- _(+{len(undigested) - 50} more)_")
        lines.append("")

    lines.append(f"_{sub} digest(s) in this subtree; "
                 f"{len(here)} file(s) directly here._")
    (d / MAP_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sub


def cmd_map(root: Path) -> int:
    all_sidecars = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(SIDECAR_SUFFIX) and name != MAP_NAME:
                all_sidecars.append(Path(dirpath) / name)
    all_sidecars.sort()

    # A directory joins the navigation plane if it has a digest somewhere in its
    # subtree OR it already carries a map of its own.
    #
    # The second half matters more than it looks. `all_sidecars` deliberately
    # excludes MAP_NAME, so for a long time a directory whose only sidecar was
    # its own authored PROJECT.placard.md was invisible to its parent's
    # "why descend" list — and a directory of plain markdown never has digests,
    # because markdown needs no extraction. The result was backwards: the
    # CHEAPEST content to read was the content the navigation plane could not
    # see. Observed: some
    # subdirectories of a project were missing from its map, each with a hand-authored dir_summary that
    # `map` ignored and then deleted from the parent on the next run.
    def _map_dirs() -> list:
        found = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if MAP_NAME in filenames:
                found.append(Path(dirpath))
        return found

    content_dirs: set = {root}
    for d in [s.parent for s in all_sidecars] + _map_dirs():
        content_dirs.add(d)
        # add ancestors up to (but not above) root. Guard against sidecars that
        # sit directly at root: their .parents never contains root, so only add
        # ancestors that are themselves inside root.
        for anc in d.parents:
            if anc == root:
                break
            if root in anc.parents:
                content_dirs.add(anc)

    # Build per-directory indices once (linear), so map generation is
    # O(dirs + sidecars) instead of rescanning all sidecars per directory.
    direct: dict = {d: [] for d in content_dirs}
    for s in all_sidecars:
        if s.parent in direct:
            direct[s.parent].append(s)
    children: dict = {d: [] for d in content_dirs}
    for d in content_dirs:
        if d != root and d.parent in children:
            children[d.parent].append(d)

    # deepest-first so child dir_summaries are readable when parents assemble,
    # and so a directory's subtree count is ready before its parent needs it.
    ordered = sorted(content_dirs, key=lambda p: len(p.parts), reverse=True)
    count: dict = {}
    for d in ordered:
        count[d] = len(direct[d]) + sum(count[c] for c in children[d])

    n_maps = 0
    for d in ordered:
        _write_dir_map(root, d, direct, children, count)
        n_maps += 1
    print(f"wrote {n_maps} {MAP_NAME} map(s) covering "
          f"{len(all_sidecars)} digest(s)")
    # how many directory summaries still need authoring
    todo = sum(1 for d in content_dirs
               if _read_map_preserved(d / MAP_NAME)[0] in ("", "TODO"))
    if todo:
        print(f"  -> {todo} director(y/ies) still need a dir_summary "
              f"(author it, then re-run map to roll it up)")
    return 0


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="placard", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="project root (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scan", help="list artifacts + digest status")

    p_init = sub.add_parser("init", help="scaffold a digest beside an artifact")
    p_init.add_argument("artifact", help="path to the artifact")
    # `deep` is accepted for backward compatibility but not advertised: it
    # never behaved differently from `standard`.
    p_init.add_argument("--tier", choices=["skim", "standard", "deep"],
                        metavar="{skim,standard}")
    p_init.add_argument("--force", action="store_true")

    p_verify = sub.add_parser("verify",
                              help="report ok/stale/missing; exit 1 if stale")
    p_verify.add_argument("--deep", action="store_true",
                          help="also read each digest against itself "
                               "(coverage claims, body hashes, summary basis)")

    p_read = sub.add_parser("read",
                            help="resolve a digest to one generation and print "
                                 "its state and body")
    p_read.add_argument("artifact", help="path to the original artifact")

    p_refresh = sub.add_parser("refresh",
                               help="re-stamp provenance without destroying prose")
    p_refresh.add_argument("artifact", help="path to the original artifact")

    p_digest = sub.add_parser("digest",
                              help="the single write path: extract, clean, publish")
    p_digest.add_argument("artifact", help="path to the original artifact")
    p_digest.add_argument("--option-profile", default="text-v1",
                          help="extraction option profile (default: text-v1)")
    p_digest.add_argument("--no-figures", action="store_true",
                          help="skip the figure description pass (no model calls)")

    sub.add_parser("gaps", help="what is undigested under --root")
    sub.add_parser("prefetch",
                   help="download extraction models now (offline readiness)")

    p_coll = sub.add_parser("collection",
                            help="one digest for a directory of generated output")
    p_coll.add_argument("directory", help="the directory of generated images")
    p_coll.add_argument("--no-figures", action="store_true",
                        help="write the digest without sampling descriptions")

    sub.add_parser("map", help="(re)generate PROJECT.placard.md")

    p_ann = sub.add_parser("announce",
                           help="coverage report for a session hook; no hashing, "
                                "silent when nothing is digested")
    p_ann.add_argument("--max-depth", type=int, default=6,
                       help="how deep to walk (default: 6)")

    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if args.cmd == "scan":
        return cmd_scan(root)
    if args.cmd == "init":
        return cmd_init(root, Path(args.artifact).resolve(), args.tier, args.force)
    if args.cmd == "verify":
        return cmd_verify_deep(root) if args.deep else cmd_verify(root)
    if args.cmd == "read":
        return cmd_read(root, Path(args.artifact).resolve())
    if args.cmd == "refresh":
        return cmd_refresh(root, Path(args.artifact).resolve())
    if args.cmd == "digest":
        return cmd_digest(root, Path(args.artifact).resolve(),
                          args.option_profile,
                          describe_figures=not args.no_figures)
    if args.cmd == "gaps":
        return cmd_gaps(root)
    if args.cmd == "prefetch":
        return cmd_prefetch(root)
    if args.cmd == "collection":
        return cmd_collection(root, Path(args.directory).resolve(),
                              not args.no_figures)
    if args.cmd == "map":
        return cmd_map(root)
    if args.cmd == "announce":
        return cmd_announce(root, args.max_depth)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
