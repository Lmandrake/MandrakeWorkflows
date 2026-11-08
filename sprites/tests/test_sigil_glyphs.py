#!/usr/bin/env python3
"""Every glyph species' 9x9 table, checked against what the renderer will actually do to it.

The Living Sigils renderer (prototype/sigils/engine.js, makeGlyph) force-mirrors each glyph
left-to-right UNCONDITIONALLY and then lights the centre pixel. Both are silent: an asymmetric row
is rewritten with no error, no test failure and no visible clue except a wrong-looking glyph, which
is how the no-op mirror sat unnoticed through all 8 shipped sigils (sprites/LESSONS, 2026-11-06).
So the table is checked here, mechanically, rather than eyeballed:

  shape       exactly 8 variants, each 9 rows of 9 chars from "#." with a non-empty unique name
  mirror      every row equals its own reverse -> the force-mirror is provably a no-op
  pilot       the glyph the renderer builds is identical to the table (mirror AND pilot light
              changed nothing), so what an author typed is what a reader sees
  names       no name is reused across species (docs/SYMBOL_SPECIES.md keeps them distinct)

Pure text parsing, no browser and no node: it reads the .js tables directly, so it runs anywhere and
costs nothing. Exit 0 = pass.

Add a species by adding its file to SPECIES below; a new glyph species needs no new test.
"""
import json
import re
import sys
from pathlib import Path

SPR = Path(__file__).resolve().parents[1]
GLYPHS = SPR / "prototype/sigils"
SPECIES = [("c3_sigils", "glyphs_sigils.js")]   # c6_night is vector since 2026-11-07: tests/test_vector_glyphs.py

_fails = []


def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg, flush=True)
    if not ok:
        _fails.append(msg)
    return bool(ok)


def table(path):
    """The [[name, [rows]], ...] table out of a glyphs_*.js file, without running JS."""
    src = path.read_text()
    # the table assigns through `this` at top level (= window in a page, the bare global in the native and
    # node vm hosts, as prototype/labels/labels.js does); `window.` is accepted too, in case one changes.
    m = re.search(r"(?:this|window)\.SPRITES_GLYPHS_\w+\s*=\s*(\[[\s\S]*?\n\]);", src)
    if not m:
        raise SystemExit(f"{path}: no 'this.SPRITES_GLYPHS_* = [...];' assignment found")
    # the table is a JSON array already, bar the trailing commas JS allows
    return json.loads(re.sub(r",(\s*[\]}])", r"\1", m.group(1)))


def make_glyph(rows, N):
    """Port of makeGlyph (prototype/sigils/engine.js): resample, force-mirror, light the centre."""
    M = len(rows)
    c = (N - 1) >> 1
    vsym = all(rows[j] == rows[M - 1 - j] for j in range(M))
    base = [[0] * N for _ in range(N)]
    for j in range(N):
        for i in range(N):
            si = round(i * (M - 1) / (N - 1))
            sj = round(j * (M - 1) / (N - 1))
            if rows[sj][si] == "#":
                base[j][i] = 1
    for j in range(N):
        for i in range(N):
            if base[j][i]:
                base[j][N - 1 - i] = 1
                if vsym:
                    base[N - 1 - j][i] = 1
                    base[N - 1 - j][N - 1 - i] = 1
    base[c][c] = 1
    return ["".join("#" if v else "." for v in r) for r in base]


def main():
    seen = {}
    for species, fname in SPECIES:
        path = GLYPHS / fname
        if not check(path.exists(), f"{species}: {path} exists"):
            continue
        glyphs = table(path)
        check(len(glyphs) == 8, f"{species}: exactly 8 variants (the hardcoded %% 8 in app/stage.html "
                                f"and app/settings.js) -- got {len(glyphs)}")
        for entry in glyphs:
            name, rows = entry[0], entry[1]
            ok_shape = (isinstance(name, str) and name.strip()
                        and len(rows) == 9 and all(len(r) == 9 and set(r) <= {"#", "."} for r in rows))
            check(ok_shape, f"{species}/{name}: a 9x9 bitmap of '#' and '.' only")
            if not ok_shape:
                continue
            bad = [j for j, r in enumerate(rows) if r != r[::-1]]
            check(not bad, f"{species}/{name}: every row is its own mirror, so the renderer's "
                           f"force-mirror is a no-op -- asymmetric rows: {bad}")
            check(make_glyph(rows, 9) == list(rows),
                  f"{species}/{name}: the glyph the renderer builds equals the table (mirror and "
                  f"pilot light both changed nothing)")
            check(rows[4][4] == "#", f"{species}/{name}: the centre pixel is drawn lit in the table, "
                                     f"not left to the pilot light to add")
            prev = seen.get(name)
            check(prev is None, f"{name!r} is used once across all species (also in {prev})")
            seen.setdefault(name, species)

    print(f"\n{'ALL PASS' if not _fails else str(len(_fails)) + ' FAIL'} "
          f"({len(seen)} glyphs over {len(SPECIES)} species)", flush=True)
    sys.exit(1 if _fails else 0)


if __name__ == "__main__":
    main()
