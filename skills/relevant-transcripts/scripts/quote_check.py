#!/usr/bin/env python3
"""Mechanical fidelity scorer for a relevant-transcripts archive.

Measures, for every summary/source pair:

  T1  quote-mark integrity  — is a span inside quote marks actually verbatim?
  T5  voice provenance      — what share of body words are marked as someone's words?
  T2* attribution           — approximate; the judged track is authoritative

Taxonomy and thresholds are fixed in advance. Do not tune them to taste.

WHY THE VALIDATE MODE EXISTS: the first throwaway version of this check paired every `"`
with the next `"` regardless of nesting, so it silently captured the prose *between* two
adjacent quotes and reported it as an unsupported quotation. It produced a confident wrong
number. No corpus figure from this script may be reported until `--validate` passes.

The archive is found from --root, else TRANSCRIPTS_ROOT, else the TRANSCRIPTS shortcut; with none
set it refuses by name. It must hold source/ and summary/; eval/ is
where report and sample write their worksheets (report prints only when eval/ is absent).

Usage:
    quote_check.py [--root DIR] report                score all pairs, write mechanical_results.md
    quote_check.py sample [-n 60]         emit a seeded random span sample for hand-labeling
    quote_check.py validate               score the hand labels in extractor_validation.md
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import random
import re
import sys
import unicodedata
from collections import defaultdict

ROOT_ENV = "TRANSCRIPTS_ROOT"
SHORTCUT_ENV = "TRANSCRIPTS"   # shell export; no hard-wired default
# Set by set_root() before any command runs.
REPO = SUMMARY_DIR = SOURCE_DIR = EVAL_DIR = ""


def set_root(cli_root: str | None) -> str:
    """Resolve the archive root: --root, else $TRANSCRIPTS_ROOT, else $TRANSCRIPTS. With none
    set, or a root without source/ and summary/, it refuses by name, never scoring an empty archive."""
    global REPO, SUMMARY_DIR, SOURCE_DIR, EVAL_DIR
    raw = cli_root or os.environ.get(ROOT_ENV) or os.environ.get(SHORTCUT_ENV)
    if not raw:
        sys.exit(f"{ROOT_ENV} is not set (nor {SHORTCUT_ENV}); set it or pass --root to the "
                 "directory holding source/ and summary/")
    REPO = os.path.abspath(os.path.expanduser(raw))
    SUMMARY_DIR = os.path.join(REPO, "summary")
    SOURCE_DIR = os.path.join(REPO, "source")
    EVAL_DIR = os.path.join(REPO, "eval")
    missing = [d for d in (SOURCE_DIR, SUMMARY_DIR) if not os.path.isdir(d)]
    if missing:
        sys.exit(f"{ROOT_ENV}: archive root {REPO} has no {', '.join(os.path.basename(m) + '/' for m in missing)}"
                 f" (set {ROOT_ENV} or pass --root to the directory holding source/ and summary/)")
    return REPO

SMOOTHED_FLOOR = 0.60   # >= this share of the span present as one contiguous run
MIN_SPAN_WORDS = 5      # shorter spans are usually terms of art, not quoted speech
SEED = 20260914


# ---------------------------------------------------------------- normalization

def normalize(text: str) -> list[str]:
    """Fold to a comparable word list. Hyphens and dashes become separators so that
    'sub-hourly' matches 'sub hourly'; apostrophes are dropped so "don't" matches "dont"."""
    text = unicodedata.normalize("NFKD", text)
    for a, b in (("’", ""), ("‘", ""), ("'", ""),
                 ("—", " "), ("–", " "), ("-", " ")):
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    return text.split()


def build_index(words: list[str]) -> dict[str, list[int]]:
    idx = defaultdict(list)
    for i, w in enumerate(words):
        idx[w].append(i)
    return idx


def longest_run(span: list[str], src: list[str], idx: dict[str, list[int]]) -> int:
    """Longest contiguous run of `span` occurring verbatim in `src`.

    Anchors on each span word's occurrences in the source and extends forward. Cheap in
    practice because spans are short, and vastly cheaper than substring-scanning the source
    once per candidate sub-run.
    """
    best = 0
    n = len(span)
    for i in range(n):
        if n - i <= best:
            break                      # cannot beat the current best from here
        for p in idx.get(span[i], ()):
            j = 0
            while i + j < n and p + j < len(src) and span[i + j] == src[p + j]:
                j += 1
            if j > best:
                best = j
                if best == n:
                    return best
    return best


# ---------------------------------------------------------------- summary parsing

NOTE_HEADING = re.compile(r"^#{1,6}\s+.*(transcription\s+note|note on this record)", re.I)
NOTE_BOLD = re.compile(r"^\*\*(transcription note|note)\b", re.I)
ANY_HEADING = re.compile(r"^#{1,6}\s+")


def strip_note(text: str) -> str:
    """Drop the transcription-note block.

    The note legitimately quotes garbled audio ('wharf' for WRF, 'Worf / Warp / World'), so
    scoring it as failed quotation would manufacture defects. Everything else is kept —
    including the Participants block, which carries real speech quotes.
    """
    out, skipping, skip_to_blank = [], False, False
    for line in text.split("\n"):
        if skipping:
            if skip_to_blank:
                if not line.strip():
                    skipping = skip_to_blank = False
                continue
            if ANY_HEADING.match(line):
                skipping = False       # fall through and keep this heading
            else:
                continue
        if NOTE_HEADING.match(line):
            skipping, skip_to_blank = True, False
            continue
        if NOTE_BOLD.match(line):
            skipping, skip_to_blank = True, True
            continue
        out.append(line)
    return "\n".join(out)


def extract_spans(text: str) -> tuple[list[dict], bool]:
    """Quoted spans, with delimiters paired properly.

    Curly pairs are unambiguous and taken first. Remaining straight quotes are paired
    sequentially across the WHOLE document (not per line) — a `"` is never an apostrophe, so
    sequential pairing is sound as long as the count is even. An odd count means a stray
    quote mark, which desynchronizes every pair after it; that file is flagged rather than
    silently mis-scored.
    """
    spans = []
    for m in re.finditer(r"“([^”]{1,600})”", text):
        spans.append({"text": m.group(1), "kind": "curly"})

    rest = re.sub(r"“[^”]{1,600}”", " ", text)
    pieces = rest.split('"')
    parity_ok = (len(pieces) % 2 == 1)          # even number of quote marks
    for i in range(1, len(pieces), 2):
        spans.append({"text": pieces[i], "kind": "straight"})
    return spans, parity_ok


def fragments(span_text: str) -> list[str]:
    """A quote with marked elision is several verbatim claims, and each is scored on its own.

    Bracketed editorial insertions are the writer's, not the speaker's, so they are removed
    before scoring rather than counted against the quote.
    """
    s = re.sub(r"\[[^\]]*\]", " ", span_text)
    s = re.sub(r"\*+", "", s)                    # markdown emphasis inside quotes
    return [f for f in re.split(r"…|\.\.\.|\s+/\s+", s) if len(normalize(f)) >= MIN_SPAN_WORDS]


def classify(frag: str, src: list[str], idx: dict[str, list[int]]) -> tuple[str, int, int]:
    words = normalize(frag)
    run = longest_run(words, src, idx)
    if run == len(words):
        verdict = "verbatim"
    elif run / len(words) >= SMOOTHED_FLOOR:
        verdict = "smoothed"
    else:
        verdict = "unsupported"
    return verdict, run, len(words)


# ---------------------------------------------------------------- attribution (approximate)

PRONOUNS = {"he", "she", "they", "his", "her", "their", "him", "them"}


def harvest_names(text: str) -> set[str]:
    """Names the summary itself treats as people: bolded, optionally label-style `**Name:**`."""
    names = set()
    for m in re.finditer(r"\*\*([A-Z][a-zA-Z.'-]+(?:\s+[A-Z][a-zA-Z.'-]+){0,3}):?\*\*", text):
        for tok in m.group(1).split():
            tok = tok.strip(".,;:'").lower()
            if len(tok) > 2:
                names.add(tok)
    return names


def attribution_rate(body: str, names: set[str]) -> tuple[int, int, int]:
    """(units, unowned units, unowned units that also lack a pronoun) over the WRITER's prose.

    Rewritten 2026-09-15. The first version counted names per sentence, and that broke the
    moment summaries became quote-dense: a sentence inside a long quotation carries its speaker
    in the label *above* it, not inside itself, so heavily-attributed text scored as heavily
    unattributed. It reported a regression where there was a large improvement.

    Two corrections:

    1. **Quoted spans leave the pool but still confer ownership.** A quotation is owned by
       whoever introduces it. What is genuinely at issue is the writer's own prose — which is
       where meaning-reversals are found.
    2. **Ownership carries forward within a block.** "The author argued X. They then conceded Y."
       owns both sentences; demanding the name in every sentence is not how prose works.

    Still approximate: a name can appear without owning the claim, and a claim can be owned by
    context no regex sees. It is a screen. Blind judges score attribution authoritatively.
    """
    blocks = re.split(r"\n\s*\n|\n(?=\s*[-*]\s)", body)
    units = unowned = unowned_no_ref = 0
    quote_span = re.compile(r"(“[^”]{1,600}”|\"[^\"\n]{1,600}\")")

    for block in blocks:
        if ANY_HEADING.match(block.strip()):
            continue
        owned = False
        for piece in quote_span.split(block):
            if not piece or not piece.strip():
                continue
            stripped = piece.strip()
            is_quote = stripped[0] in '“"' and stripped[-1] in '”"' and len(stripped) > 1
            plain = re.sub(r"\*+", "", piece)
            plain = re.sub(r"^\s*[-*]\s+", "", plain)
            if {t.strip(".,;:'\"()[]").lower() for t in plain.split()} & names:
                owned = True
            if is_quote:
                continue                      # the speaker's words, not the writer's
            for sentence in re.split(r"(?<=[.!?])\s+", plain):
                words = sentence.split()
                if len(words) < 6:
                    continue
                units += 1
                toks = {t.strip(".,;:'\"()[]").lower() for t in words}
                if owned or (toks & names):
                    continue
                unowned += 1
                if not (toks & PRONOUNS):
                    unowned_no_ref += 1
    return units, unowned, unowned_no_ref


# ---------------------------------------------------------------- pairing

def pairs() -> list[tuple[str, list[str]]]:
    out = []
    for s in sorted(glob.glob(os.path.join(SUMMARY_DIR, "*.md"))):
        base = os.path.basename(s)[:-3]
        srcs = sorted(glob.glob(os.path.join(SOURCE_DIR, base + "*.txt")))
        if srcs:
            out.append((base, srcs))
        else:
            print(f"WARNING: no source for {base}", file=sys.stderr)
    return out


def score_all() -> list[dict]:
    rows = []
    for base, srcs in pairs():
        summary = open(os.path.join(SUMMARY_DIR, base + ".md")).read()
        body = strip_note(summary)
        src_words = normalize(" ".join(open(f).read() for f in srcs))
        idx = build_index(src_words)

        spans, parity_ok = extract_spans(body)
        counts = defaultdict(int)
        quoted_words = 0
        detail = []
        for sp in spans:
            for frag in fragments(sp["text"]):
                verdict, run, n = classify(frag, src_words, idx)
                counts[verdict] += 1
                quoted_words += n
                detail.append({"file": base, "kind": sp["kind"], "verdict": verdict,
                               "run": run, "words": n, "text": frag.strip()[:220]})

        names = harvest_names(summary)
        sents, no_name, no_ref = attribution_rate(body, names)
        body_words = len(normalize(body))

        rows.append({
            "base": base, "parity_ok": parity_ok,
            "verbatim": counts["verbatim"], "smoothed": counts["smoothed"],
            "unsupported": counts["unsupported"],
            "frags": sum(counts.values()),
            "quoted_words": quoted_words, "body_words": body_words,
            "sentences": sents, "no_name": no_name, "no_ref": no_ref,
            "detail": detail,
        })
    return rows


# ---------------------------------------------------------------- outputs

def cmd_report(_args) -> int:
    rows = score_all()
    bad_parity = [r["base"] for r in rows if not r["parity_ok"]]

    hdr = (f"{'pair':58}{'frag':>5}{'vbtm':>5}{'smth':>5}{'unsup':>6}"
           f"{'%vbtm':>7}{'voice':>7}{'unownd':>8}")
    lines = [hdr, "-" * len(hdr)]
    tot = defaultdict(int)
    for r in sorted(rows, key=lambda r: -(r["unsupported"] / max(r["frags"], 1))):
        pv = r["verbatim"] / r["frags"] if r["frags"] else 0
        voice = r["quoted_words"] / r["body_words"] if r["body_words"] else 0
        nn = r["no_name"] / r["sentences"] if r["sentences"] else 0
        flag = "" if r["parity_ok"] else "  <- ODD QUOTE COUNT"
        lines.append(f"{r['base'][:57]:58}{r['frags']:>5}{r['verbatim']:>5}"
                     f"{r['smoothed']:>5}{r['unsupported']:>6}{pv:>6.0%}"
                     f"{voice:>7.0%}{nn:>7.0%}{flag}")
        for k in ("frags", "verbatim", "smoothed", "unsupported",
                  "quoted_words", "body_words", "sentences", "no_name", "no_ref"):
            tot[k] += r[k]

    lines += ["-" * len(hdr)]
    lines.append(f"{'TOTAL (' + str(len(rows)) + ' pairs)':58}{tot['frags']:>5}"
                 f"{tot['verbatim']:>5}{tot['smoothed']:>5}{tot['unsupported']:>6}"
                 f"{tot['verbatim']/max(tot['frags'],1):>6.0%}"
                 f"{tot['quoted_words']/max(tot['body_words'],1):>7.0%}"
                 f"{tot['no_name']/max(tot['sentences'],1):>7.0%}")

    ok = [r for r in rows if r["parity_ok"]]
    okt = defaultdict(int)
    for r in ok:
        for k in ("frags", "verbatim", "smoothed", "unsupported", "quoted_words",
                  "body_words", "sentences", "no_name", "no_ref"):
            okt[k] += r[k]
    lines.append(f"{'TOTAL, parity-OK only (' + str(len(ok)) + ' pairs)':58}{okt['frags']:>5}"
                 f"{okt['verbatim']:>5}{okt['smoothed']:>5}{okt['unsupported']:>6}"
                 f"{okt['verbatim']/max(okt['frags'],1):>6.0%}"
                 f"{okt['quoted_words']/max(okt['body_words'],1):>7.0%}"
                 f"{okt['no_name']/max(okt['sentences'],1):>7.0%}")

    summary_txt = "\n".join(lines)
    print(summary_txt)
    print()
    print(f"T1 quote integrity   verbatim {tot['verbatim']/max(tot['frags'],1):.1%}"
          f"  smoothed {tot['smoothed']/max(tot['frags'],1):.1%}"
          f"  unsupported {tot['unsupported']/max(tot['frags'],1):.1%}")
    print(f"T5 voice provenance  {tot['quoted_words']/max(tot['body_words'],1):.1%} "
          f"of body words are inside quote marks")
    print(f"T2 attribution*      {tot['no_name']/max(tot['sentences'],1):.1%} of the writer's own "
          f"prose units are unowned; {tot['no_ref']/max(tot['sentences'],1):.1%} lack even a pronoun")
    print("                     * approximate screen only — judged track is authoritative")
    if bad_parity:
        print(f"\nPARITY FAILURES ({len(bad_parity)}) — spans unreliable, excluded from claims:")
        for b in bad_parity:
            print(f"  {b}")
    else:
        print("\nparity: all files have an even number of straight quote marks")

    if not os.path.isdir(EVAL_DIR):
        print(f"\nno {EVAL_DIR}; results printed only")
        return 0
    with open(os.path.join(EVAL_DIR, "mechanical_results.md"), "w") as fh:
        fh.write("# Mechanical results (T1, T5, T2-approx)\n\n")
        fh.write("Generated by `eval/quote_check.py report`. Regenerate rather than hand-edit.\n\n")
        fh.write("```\n" + summary_txt + "\n```\n")
    with open(os.path.join(EVAL_DIR, "spans.json"), "w") as fh:
        json.dump([d for r in rows for d in r["detail"]], fh, indent=1)
    print(f"\nwrote {os.path.join(EVAL_DIR, 'mechanical_results.md')} and spans.json")
    return 0


def cmd_sample(args) -> int:
    """Emit a seeded random span sample as a labeling worksheet."""
    rows = score_all()
    allspans = [d for r in rows for d in r["detail"]]
    random.Random(SEED).shuffle(allspans)
    picked = allspans[: args.n]
    path = os.path.join(EVAL_DIR, "extractor_validation.md")
    with open(path, "w") as fh:
        fh.write("# Extractor validation worksheet\n\n")
        fh.write(f"{args.n} spans sampled with seed {SEED} from `spans.json`.\n\n")
        fh.write("Label each `label:` line with exactly one of:\n\n")
        fh.write("- `speech` — a quotation of something a participant said\n")
        fh.write("- `not-speech` — term of art, scare quote, name variant, document title\n")
        fh.write("- `parser-error` — not a quoted span at all (prose between quotes, "
                 "markdown artifact, truncated fragment)\n\n")
        fh.write("A `parser-error` rate above 5% invalidates the corpus figures.\n\n---\n\n")
        for i, d in enumerate(picked, 1):
            fh.write(f"## {i}. {d['file']}\n\n")
            fh.write(f"- verdict: `{d['verdict']}` (run {d['run']}/{d['words']} words)\n")
            fh.write(f"- span: {d['text']!r}\n")
            fh.write("- label: \n\n")
    print(f"wrote {path} with {len(picked)} spans to label")
    return 0


def cmd_validate(_args) -> int:
    path = os.path.join(EVAL_DIR, "extractor_validation.md")
    if not os.path.exists(path):
        print(f"missing {path} — run `sample` and label it first", file=sys.stderr)
        return 2
    labels = [m.group(1).strip().strip("`")
              for m in re.finditer(r"^- label:\s*(.*)$", open(path).read(), re.M)]
    filled = [l for l in labels if l]
    counts = defaultdict(int)
    for l in filled:
        counts[l] += 1
    print(f"labeled {len(filled)} of {len(labels)} spans")
    for k in sorted(counts):
        print(f"  {k:14} {counts[k]:>4}  {counts[k]/len(filled):>6.1%}")
    if not filled:
        return 2
    err = counts.get("parser-error", 0) / len(filled)
    print(f"\nparser-error rate: {err:.1%}  (bar: <5%)")
    if err >= 0.05:
        print("FAIL — fix the extractor and re-validate. Corpus figures are withheld.")
        return 1
    print("PASS — corpus figures may be reported.")
    if len(filled) < len(labels):
        print(f"NOTE: {len(labels)-len(filled)} spans unlabeled; rate is over labeled spans only.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help=f"archive root (default: ${ROOT_ENV}, else ${SHORTCUT_ENV})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    sp = sub.add_parser("sample")
    sp.add_argument("-n", type=int, default=60)
    sp.set_defaults(fn=cmd_sample)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    args = ap.parse_args()
    set_root(args.root)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
