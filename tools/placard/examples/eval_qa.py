#!/usr/bin/env python3
"""Measure the core claim on the example: does a model answer questions about the folder as
well from the digests as from the originals, and what does each cost in input tokens?

Three conditions, the same questions (`questions.json`), the same model, the same prompt:

    originals  the three files as a model ingests them natively: the PDF as a document block;
               the deck and the workbook rendered to PDF by LibreOffice (the deck WITH its
               notes pages, so the originals hold every fact the digests do)
    plaintext  the ordinary text route, no Placard: pypdf on the PDF, python-pptx on the deck
               (slide text and notes), openpyxl cell dumps of the workbook. Needs those three
               libraries; skipped, and said so, without them
    placards   PROJECT.placard.md plus the three digests, as text
    bodies     the `## Full text` bodies ONLY: what `placard digest` extracted mechanically,
               with no authored summary, no map and no frontmatter. The questions were written
               by the person who authored the summaries, so this is the condition the claim
               rests on; the authored prose cannot leak an answer into it
    summaries  the map and the digests WITHOUT their bodies: the authored layer alone.
               Contaminated by construction (same author as the questions); reported only to
               show what the bodies add
    none       no context at all: the control, so a fact a model could guess scores nothing

Scoring is mechanical (see questions.json `note`); no model grades another. Token counts are
the endpoint's own `usage.input_tokens`.

    python3 examples/eval_qa.py [--runs 3] [--out examples/results.json]

Environment, read at call time and never defaulted: ANTHROPIC_BASE_URL, a model id
(PLACARD_EVAL_MODEL, else PLACARD_DESCRIBE_MODEL, else ANTHROPIC_DEFAULT_SONNET_MODEL), and a
credential (see placardlib/describe.py). Needs `soffice` on PATH for the rendered originals.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from placardlib import describe  # noqa: E402

FOLDER = HERE / "quarterly-review"
MAX_TOKENS = 1500
TEMPERATURE = None   # the model's default; current Claude models accept no other
CONDITIONS = ("originals", "plaintext", "placards", "bodies", "summaries", "none")
NOTES_FILTER = 'pdf:impress_pdf_Export:{"ExportNotesPages":{"type":"boolean","value":"true"}}'

PROMPT = (
    "You are given the contents of a project folder. Answer each question using ONLY that "
    "content. If the content does not contain the answer, reply \"not in the folder\". "
    "Return one JSON object mapping each question id to a short answer string, and nothing "
    "else.\n\nQuestions:\n")


def model_id() -> str:
    override = os.getenv("PLACARD_EVAL_MODEL", "").strip()
    return override or describe.default_model()


def soffice_version() -> str:
    exe = shutil.which("soffice")
    if not exe:
        return "absent"
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60)
    return out.stdout.strip().splitlines()[0] if out.stdout.strip() else "unknown"


def render_pdf(path: Path, outdir: Path, filt: str = "pdf") -> Path:
    soffice = shutil.which("soffice")
    if not soffice:
        raise SystemExit("soffice is not on PATH; it renders the deck and workbook to PDF")
    subprocess.run([soffice, "--headless", "--convert-to", filt, "--outdir", str(outdir),
                    str(path)], check=True, capture_output=True, timeout=300)
    out = outdir / (path.stem + ".pdf")
    if not out.is_file():
        raise SystemExit(f"LibreOffice did not produce {out.name}")
    return out


def pdf_block(path: Path, title: str) -> dict:
    return {"type": "document", "title": title, "source": {
        "type": "base64", "media_type": "application/pdf",
        "data": base64.b64encode(path.read_bytes()).decode("ascii")}}


def contexts(tmp: Path) -> dict:
    report = FOLDER / "field-trial-report.pdf"
    deck = render_pdf(FOLDER / "review-deck.pptx", tmp, NOTES_FILTER)
    book = render_pdf(FOLDER / "sensor-log.xlsx", tmp)
    originals = [pdf_block(report, report.name),
                 pdf_block(deck, "review-deck.pptx (rendered with speaker notes)"),
                 pdf_block(book, "sensor-log.xlsx (rendered)")]
    texts = []
    for p in sorted(FOLDER.glob("*.placard.md")) + sorted(FOLDER.glob("*.body.md")):
        texts.append(f"=== {p.name} ===\n{p.read_text(encoding='utf-8')}")
    placards = [{"type": "text", "text": "\n\n".join(texts)}]
    heads = []
    for p in sorted(FOLDER.glob("*.placard.md")):
        text = p.read_text(encoding="utf-8")
        heads.append(f"=== {p.name} ===\n{text.split(chr(10) + '## Full text' + chr(10))[0]}")
    summaries = [{"type": "text", "text": "\n\n".join(heads)}]
    bodies = []
    for p in sorted(FOLDER.glob("*.placard.md")):
        if p.name == "PROJECT.placard.md":
            continue
        source = p.name[: -len(".placard.md")]
        text = p.read_text(encoding="utf-8")
        marker = "\n## Full text\n"
        if marker in text:
            body = text.split(marker, 1)[1]
        else:   # external body: the entry names it
            path = next(line.split(":", 1)[1].strip() for line in text.splitlines()
                        if line.startswith("body_path:"))
            body = (FOLDER / path).read_text(encoding="utf-8")
        bodies.append(f"=== {source} (extracted text) ===\n{body}")
    bodies = [{"type": "text", "text": "\n\n".join(bodies)}]
    out = {"originals": originals, "placards": placards, "bodies": bodies,
           "summaries": summaries, "none": []}
    plain = plaintext()
    if plain is not None:
        out["plaintext"] = [{"type": "text", "text": plain}]
    return out


def plaintext():
    """The no-Placard text route an agent would improvise; None if a library is missing."""
    try:
        import openpyxl
        import pypdf
        from pptx import Presentation
    except ImportError as exc:
        print(f"plaintext condition skipped: {exc.name} is not installed", file=sys.stderr)
        return None
    parts = []
    reader = pypdf.PdfReader(str(FOLDER / "field-trial-report.pdf"))
    parts.append("=== field-trial-report.pdf ===\n" + "\n".join(
        p.extract_text() or "" for p in reader.pages))
    deck = Presentation(str(FOLDER / "review-deck.pptx"))
    lines = []
    for i, slide in enumerate(deck.slides, 1):
        lines.append(f"[slide {i}]")
        for shape in slide.shapes:
            if shape.has_text_frame:
                lines.append(shape.text_frame.text)
        if slide.has_notes_slide:
            lines.append("notes: " + slide.notes_slide.notes_text_frame.text)
    parts.append("=== review-deck.pptx ===\n" + "\n".join(lines))
    book = openpyxl.load_workbook(str(FOLDER / "sensor-log.xlsx"), read_only=True)
    for ws in book.worksheets:
        rows = ["\t".join("" if v is None else str(v) for v in row)
                for row in ws.iter_rows(values_only=True)]
        parts.append(f"=== sensor-log.xlsx / {ws.title} ===\n" + "\n".join(rows))
    return "\n\n".join(parts)


def call(content: list, questions: list, model: str) -> tuple:
    d = describe.Describer(model=model)   # endpoint + credential, from the environment
    qtext = "\n".join(f"{q['id']}: {q['q']}" for q in questions)
    body = {"model": model, "max_tokens": MAX_TOKENS, "messages": [{"role": "user", "content":
            content + [{"type": "text", "text": PROMPT + qtext}]}]}
    if TEMPERATURE is not None:
        body["temperature"] = TEMPERATURE
    req = urllib.request.Request(d.url, data=json.dumps(body).encode(), headers=d._headers(),
                                 method="POST")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise SystemExit(f"HTTP {exc.code}: {exc.read()[:400]!r}")
            time.sleep(5 * (attempt + 1))
    else:
        raise SystemExit("endpoint kept failing")
    text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    answers = json.loads(m.group(0)) if m else {}
    return (answers, data["usage"]["input_tokens"], data["usage"]["output_tokens"],
            data.get("stop_reason"))


def norm(s) -> str:
    return re.sub(r"[,$%]", "", str(s).lower())


def check(c: dict, a: str) -> bool:
    if "num" in c:      # a whole number: 7 must not match 17, 291 not 1291
        return re.search(r"(?<![\d.])" + re.escape(c["num"]) + r"(?![\d]|\.\d)", a) is not None
    if "word" in c:     # whole words at the start; a suffix is allowed (sand -> sandy)
        return re.search(r"(?<![a-z])" + re.escape(c["word"]), a) is not None
    if "any" in c:
        return any(check(x, a) for x in c["any"])
    if "none_of" in c:
        return not any(re.search(r"(?<![a-z])" + re.escape(x) + r"(?![a-z])", a)
                       for x in c["none_of"])
    raise ValueError(f"unknown check {c}")


def score(q: dict, answer) -> int:
    a = norm(answer)
    if "not in the folder" in a:
        return 0
    return int(all(check(c, a) for c in q["checks"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", default=str(HERE / "results.json"))
    ap.add_argument("--rescore", metavar="RESULTS",
                    help="re-score the stored answers in RESULTS with the current scorer; no calls")
    args = ap.parse_args(argv)
    questions = json.loads((HERE / "questions.json").read_text())["questions"]
    if args.rescore:
        data = json.loads(Path(args.rescore).read_text())
        for r in data["detail"]:
            r["per_question"] = {q["id"]: score(q, r["answers"].get(q["id"], "")) for q in questions}
            r["correct"] = sum(r["per_question"].values())
        for cond, s in data["summary"].items():
            s["correct"] = [r["correct"] for r in data["detail"] if r["condition"] == cond]
        Path(args.rescore).write_text(json.dumps(data, indent=1) + "\n")
        print(json.dumps({c: s["correct"] for c, s in data["summary"].items()}))
        return 0
    model = model_id()
    with tempfile.TemporaryDirectory() as tmp:
        ctx = contexts(Path(tmp))
        runs = []
        for r in range(args.runs):
            for cond in [c for c in CONDITIONS if c in ctx]:
                answers, tin, tout, stop = call(ctx[cond], questions, model)
                per = {q["id"]: score(q, answers.get(q["id"], "")) for q in questions}
                runs.append({"run": r + 1, "condition": cond, "input_tokens": tin,
                             "output_tokens": tout, "stop_reason": stop, "correct": sum(per.values()),
                             "per_question": per, "answers": answers})
                print(f"run {r + 1} {cond:9s} {sum(per.values()):2d}/{len(questions)} "
                      f"input_tokens={tin}")
    summary = {}
    for cond in sorted({x["condition"] for x in runs}, key=CONDITIONS.index):
        rs = [x for x in runs if x["condition"] == cond]
        summary[cond] = {"correct": [x["correct"] for x in rs],
                         "input_tokens": [x["input_tokens"] for x in rs]}
    out = {"model": describe.model_label(model),
           "temperature": "model default" if TEMPERATURE is None else TEMPERATURE,
           "max_tokens": MAX_TOKENS, "questions": len(questions), "runs": args.runs,
           "soffice": soffice_version(),
           "measured_on": time.strftime("%Y-%m-%d"), "summary": summary, "detail": runs}
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
