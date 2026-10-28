#!/usr/bin/env python3
"""Check a directory tree against OKF v0.2 conformance (§11).

OKF v0.2 §11 — a bundle is conformant if:
  1. Every non-reserved `.md` file contains a parseable YAML frontmatter block.
  2. Every frontmatter block contains a non-empty `type` field.
  3. Reserved filenames (`index.md`, `log.md`) follow §8/§9 when present.

§8 also constrains index files: they carry NO frontmatter, except a bundle-root
`index.md` which MAY carry `okf_version`.

Usage:
    python3 contrib/okf_conformance.py <bundle-root> [--quiet]

Exit code 0 if conformant, 1 if not. Uses PyYAML when importable for a real
parse; otherwise falls back to a structural check and says so, because claiming
"parseable YAML" without a parser would be a false pass.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RESERVED = {"index.md", "log.md"}

try:
    import yaml  # type: ignore
    HAVE_YAML = True
except ImportError:
    yaml = None  # type: ignore
    HAVE_YAML = False


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_src, body). frontmatter_src is None if absent."""
    if not text.startswith("---"):
        return None, text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return None, text


def check(root: Path) -> tuple[list[str], list[str], int]:
    errors: list[str] = []
    warnings: list[str] = []
    checked = 0

    md_files = sorted(p for p in root.rglob("*.md") if p.is_file())
    for p in md_files:
        rel = p.relative_to(root)
        text = p.read_text(encoding="utf-8", errors="replace")
        fm_src, _body = split_frontmatter(text)
        checked += 1

        if p.name in RESERVED:
            # §8 forbids frontmatter in index.md (root may carry okf_version only).
            # §9 says nothing about log.md frontmatter, and Google's own reference
            # bundle gives log.md a `type: Log` block — so log.md is unconstrained.
            if p.name == "log.md":
                continue
            is_root_index = (p.name == "index.md" and p.parent == root)
            if fm_src is not None and not is_root_index:
                errors.append(
                    f"{rel}: index.md carries frontmatter "
                    f"(OKF §8: only a bundle-root index.md may, and only okf_version)")
            elif fm_src is not None and is_root_index:
                keys = set(re.findall(r"^(\w[\w-]*):", fm_src, re.M))
                extra = keys - {"okf_version"}
                if extra:
                    errors.append(
                        f"{rel}: root index.md may only carry okf_version, "
                        f"found also {sorted(extra)}")
            continue

        # Non-reserved: must have parseable frontmatter with non-empty type.
        if fm_src is None:
            errors.append(f"{rel}: no frontmatter block (OKF §11.1)")
            continue

        if HAVE_YAML and yaml is not None:
            try:
                data = yaml.safe_load(fm_src)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{rel}: frontmatter is not parseable YAML: {exc}")
                continue
            if not isinstance(data, dict):
                errors.append(f"{rel}: frontmatter is not a YAML mapping")
                continue
            t = data.get("type")
        else:
            m = re.search(r"^type:\s*(.+?)\s*$", fm_src, re.M)
            t = m.group(1) if m else None

        if t is None or (isinstance(t, str) and not t.strip()):
            errors.append(f"{rel}: missing or empty `type` (OKF §11.2)")

    # Broken links are explicitly NOT errors (§6.1) — report as information.
    for p in md_files:
        for target in re.findall(r"\]\((?!https?://|mailto:)([^)#]+?)\)", p.read_text(
                encoding="utf-8", errors="replace")):
            if target.startswith("/"):
                resolved = root / target.lstrip("/")
            else:
                resolved = (p.parent / target)
            if not resolved.exists():
                warnings.append(
                    f"{p.relative_to(root)} -> {target} (not present; "
                    f"permitted by §6.1, consumers MUST tolerate)")

    return errors, warnings, checked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    root = args.root.expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"not a directory: {root}")

    errors, warnings, checked = check(root)

    print(f"OKF v0.2 conformance check: {root}")
    print(f"  markdown files checked : {checked}")
    print(f"  YAML parser            : "
          f"{'PyYAML (real parse)' if HAVE_YAML else 'NONE — structural check only'}")
    print(f"  conformance errors     : {len(errors)}")
    print(f"  tolerated broken links : {len(warnings)}")

    if errors:
        print("\nERRORS (§11):")
        for e in errors:
            print(f"  ✗ {e}")
    if warnings and not args.quiet:
        print("\nBroken links — permitted, not errors (§6.1):")
        for w in warnings:
            print(f"  · {w}")

    print("\n" + ("CONFORMANT" if not errors else "NOT CONFORMANT"))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
