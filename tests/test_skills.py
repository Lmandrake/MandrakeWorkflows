"""Every skill under skills/ has a usable SKILL.md: frontmatter with `name` (matching its
directory) and a non-empty `description`, and no relative markdown link that points nowhere.

Stdlib only. Run with `python3 -m pytest -q tests` or plain `python3 tests/test_skills.py`.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^(```|~~~).*?^\1", re.M | re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def skill_dirs():
    return sorted(p.parent for p in SKILLS.glob("*/SKILL.md") if not p.parent.name.endswith("-workspace"))


def frontmatter(text):
    """The YAML block between the opening and closing `---`, as {key: value} for top-level
    keys; folded (`>`, `>-`, `|`) values are joined from their indented lines."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fields, key = {}, None
    for line in text[4:end].splitlines():
        m = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            key, val = m.group(1), m.group(2).strip()
            fields[key] = "" if val in (">", ">-", "|", "|-") else val.strip("'\"")
        elif key and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def dangling_links(md):
    text = INLINE_CODE.sub("", FENCE.sub("", md.read_text(encoding="utf-8")))
    bad = []
    for target in LINK.findall(text):
        if re.match(r"[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith(("#", "<")):
            continue                                   # URL, mailto:, anchor, <placeholder>
        path = target.split("#", 1)[0]
        if path and not (md.parent / path).exists():
            bad.append(target)
    return bad


def problems():
    found = []
    dirs = skill_dirs()
    if not dirs:
        found.append("no skills/*/SKILL.md found")
    for d in dirs:
        fm = frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
        if fm is None:
            found.append("%s: SKILL.md has no frontmatter" % d.name)
            continue
        if fm.get("name") != d.name:
            found.append("%s: frontmatter name %r does not match the directory" % (d.name, fm.get("name")))
        if len(fm.get("description", "")) < 20:
            found.append("%s: description missing or too short" % d.name)
        for md in sorted(d.rglob("*.md")):
            found.extend("%s: dangling link %s" % (md.relative_to(ROOT), t) for t in dangling_links(md))
    return found


def test_every_skill_is_valid():
    assert problems() == []


def test_checker_catches_defects(tmp_path):
    md = tmp_path / "x.md"
    md.write_text("[ok](x.md) [web](https://e.example) [gone](missing.md) `[code](nope.md)`\n")
    assert dangling_links(md) == ["missing.md"]
    assert frontmatter("---\nname: a\ndescription: >\n  folded\n  text\n---\n") == {
        "name": "a", "description": "folded text"}
    assert frontmatter("no frontmatter") is None


if __name__ == "__main__":
    out = problems()
    print("\n".join(out) or "%d skills valid" % len(skill_dirs()))
    sys.exit(1 if out else 0)
