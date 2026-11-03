#!/usr/bin/env python3
"""Validate authored SKILL.md files: size budget, frontmatter, cited-path safety.

These skills may be linked into a shared skills directory and are therefore
visible to every project. A skill that cites a local-only or ignored directory would carry that path
everywhere, so every cited repo path must be git-tracked. Checking it
mechanically beats remembering.

No skill may name a renderer (decision D6): skills ask for capabilities by property, and
the names to refuse are read from registry/renderers.yaml.

Run with no arguments to check the nine visual skills (MandrakeWorkflows/skills/, named in
VISUAL_SKILLS); pass explicit roots to narrow it. REPO is the visualize/ directory.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAX_LINES = 250
MIN_DESCRIPTION_CHARS = 100


def _repo_path_forms() -> list[str]:
    """Every spelling a skill may use for this repo: absolute and ~-relative, for this
    checkout and for the canonical ~/dev/MandrakeWorkflows/visualize (so a worktree checks too)."""
    forms = [str(REPO), str(Path.home() / "dev" / "MandrakeWorkflows" / "visualize"),
             "~/dev/MandrakeWorkflows/visualize"]
    try:
        forms.append("~/" + str(REPO.relative_to(Path.home())))
    except ValueError:
        pass
    return list(dict.fromkeys(forms))


CITED_PATH = re.compile(
    "(?:%s)/([A-Za-z0-9._/-]+)" % "|".join(re.escape(form) for form in _repo_path_forms())
)


def tracked_files() -> set[str]:
    """Every path git tracks in this repo. Ignored files are absent by design.

    Without git or a .git directory (an exported tree), every file on disk counts as tracked."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return set(out.splitlines())
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {
            str(p.relative_to(REPO))
            for p in REPO.rglob("*")
            if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts
        }


def parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML-frontmatter reader; folds block scalars onto one line."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    key: str | None = None
    for line in text[4:end].splitlines():
        match = re.match(r"^([a-z][a-z0-9_-]*):\s*(.*)$", line)
        if match:
            key = match.group(1)
            fields[key] = match.group(2).strip()
        elif key and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def _path_is_tracked(rel: str, tracked: set[str]) -> bool:
    rel = rel.rstrip(".,;:)").rstrip("/")
    if rel in tracked:
        return True
    prefix = rel + "/"
    return any(t.startswith(prefix) for t in tracked)


def _renderer_pattern() -> re.Pattern[str] | None:
    sys.path.insert(0, str(REPO / "tools"))
    from route_renderer import REGISTRY, renderer_names

    if not REGISTRY.exists():
        return None
    names = sorted(renderer_names(), key=len, reverse=True)
    return re.compile(
        r"(?<![A-Za-z0-9_-])(%s)(?![A-Za-z0-9_-])" % "|".join(re.escape(n) for n in names),
        re.IGNORECASE,
    )


_RENDERERS: list[re.Pattern[str] | None] = []


def renderer_pattern() -> re.Pattern[str] | None:
    if not _RENDERERS:
        _RENDERERS.append(_renderer_pattern())
    return _RENDERERS[0]


def check_skill(skill_md: Path, tracked: set[str]) -> list[str]:
    """Return a list of problems. Empty means the skill passes."""
    problems: list[str] = []
    text = skill_md.read_text()

    pattern = renderer_pattern()
    if pattern:
        for name in sorted({m.group(1) for m in pattern.finditer(text)}):
            problems.append(
                f"names renderer {name!r}; ask for the capability by property instead "
                "(D6, registry/renderers.yaml, tools/route_renderer.py)"
            )

    line_count = len(text.splitlines())
    if line_count > MAX_LINES:
        problems.append(f"{line_count} lines exceeds the {MAX_LINES}-line budget")

    fields = parse_frontmatter(text)
    if not fields:
        problems.append("missing or malformed YAML frontmatter")
    else:
        name = fields.get("name", "")
        if not name:
            problems.append("frontmatter has no name")
        elif name != skill_md.parent.name:
            problems.append(
                f"frontmatter name {name!r} != directory {skill_md.parent.name!r}"
            )
        description = fields.get("description", "").lstrip("> ").strip()
        if len(description) < MIN_DESCRIPTION_CHARS:
            problems.append(
                "description is missing or too short to trigger reliably "
                f"({len(description)} chars, want >= {MIN_DESCRIPTION_CHARS})"
            )

    for rel in sorted(set(CITED_PATH.findall(text))):
        if not _path_is_tracked(rel, tracked):
            problems.append(f"cited path is not git-tracked: {rel}")

    return problems


SKILLS_DIR = REPO.parent / "skills"
VISUAL_SKILLS = (
    "scientific-visualization", "visual-beautiful", "visual-composition", "visual-critic",
    "visual-encoding", "visual-intent", "visual-portfolio", "visual-presentation", "visual-render-qa",
)
DEFAULT_ROOTS = tuple(SKILLS_DIR / name for name in VISUAL_SKILLS)


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or list(DEFAULT_ROOTS)
    skill_files = sorted({p for root in roots for p in root.rglob("SKILL.md")})
    if not skill_files:
        print("no SKILL.md files found", file=sys.stderr)
        return 1

    tracked = tracked_files()
    failed = False
    for skill_md in skill_files:
        problems = check_skill(skill_md, tracked)
        if problems:
            failed = True
            print(f"FAIL {skill_md.parent.name}")
            for problem in problems:
                print(f"       {problem}")
        else:
            print(f"ok   {skill_md.parent.name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
