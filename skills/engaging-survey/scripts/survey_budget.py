#!/usr/bin/env python3
"""Estimate a survey draft's length and burden from a markdown/plain-text export.

    python3 survey_budget.py draft.md [--json]

Convert .docx first: pandoc draft.docx -t gfm -o draft.md

A question is a line that starts with **Q<id>**, or a top-level (unindented) numbered item ("12. ..."), or a bold line ending in "?". Its answer options are the indented/bulleted lines after it.
A question with no options, or marked "open text"/"open-ended"/"paragraph", counts as open text.

Time is a rule of thumb, not a measurement: 10 s per single-choice item, 15 s plus 1.5 s per option
for select-all items, 45 s per open-text box, 5 s per identification field. Pilot it to know.
"""
import json
import re
import sys

Q_PATTERNS = [
    re.compile(r"^\*\*Q[\w.]+\b"),                 # **Q3.2 ...
    re.compile(r"^\d{1,3}\.\s+\S"),               # 12. What ... (top level; options are indented)
    re.compile(r"^\*\*[^*]+\?\*\*"),               # **Did you attend ...?**
]
OPTION = re.compile(r"^(\s+(\d+\.|[-*])|[-*])\s+\S")
OPEN_HINT = re.compile(r"\(\s*open[ -]?(text|ended)|\bparagraph\b", re.I)
SELECT_ALL = re.compile(r"select all|all that apply|check all", re.I)
ID_HINT = re.compile(r"\b(first name|last name|email|title|position|organi[sz]ation name)\b", re.I)


def parse(lines):
    qs, cur = [], None
    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue
        if any(p.match(stripped) for p in Q_PATTERNS) and not line.startswith((" ", "\t")):
            cur = {"text": stripped[:120], "options": 0, "hints": stripped}
            qs.append(cur)
        elif cur is not None and OPTION.match(line):
            cur["options"] += 1
        elif stripped.startswith("#"):
            cur = None
        elif cur is not None and cur["options"] == 0:
            cur["hints"] += " " + stripped  # wrapped stem or a "(select all ...)" note
    for q in qs:
        h = q["hints"]
        if ID_HINT.search(h) and q["options"] == 0 and len(h) < 90:
            q["kind"], q["secs"] = "id", 5
        elif q["options"] == 0 or (OPEN_HINT.search(h) and q["options"] < 3):
            q["kind"], q["secs"] = "open", 45
        elif SELECT_ALL.search(h):
            q["kind"], q["secs"] = "select_all", 15 + 1.5 * q["options"]
        else:
            q["kind"], q["secs"] = "single", 10
    return qs


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    qs = parse(open(args[0], encoding="utf-8", errors="replace"))
    kinds = {k: sum(q["kind"] == k for q in qs) for k in ("id", "single", "select_all", "open")}
    long_lists = [q["text"] for q in qs if q["options"] >= 8]
    minutes = sum(q["secs"] for q in qs) / 60
    out = {"questions": len(qs), "by_kind": kinds, "options_total": sum(q["options"] for q in qs),
           "long_option_lists_8plus": len(long_lists), "estimated_minutes": round(minutes, 1),
           "target": "2-5 min, ~8-12 items", "long_lists": long_lists}
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1))
        return
    print(f"{len(qs)} questions: {kinds['id']} identification, {kinds['single']} single-choice, "
          f"{kinds['select_all']} select-all, {kinds['open']} open text")
    print(f"{out['options_total']} answer options in all; {len(long_lists)} lists of 8+ options")
    print(f"estimated completion: ~{minutes:.0f} min (rule of thumb; target 2-5 min, ~8-12 items)")
    for t in long_lists:
        print(f"  long list: {t}")


if __name__ == "__main__":
    main()
