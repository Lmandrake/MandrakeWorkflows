#!/usr/bin/env python3
"""Acceptance for MANDRAKEWORKFLOWS_REALIGN_PROJECT_MAP_FOCUS_TO_LIVE_WAYPOINT. tests/test_project_map.py must follow the
owner's LIVE Waypoint focus choices (never hard-code them), and must keep its teeth on focus. Runs test_project_map.py:
  1. against this machine's real Waypoint tables: must pass;
  2. against a fixture HOME whose launches.md has the KesMine and KestrelWorks Focus cells FLIPPED: must pass;
  3. with a mutant projects.js that marks EVERY row focused, on the flipped fixture: must FAIL;
  4. with a mutant projects.js that marks NO row focused, on the live tables: must FAIL;
  5. test_project_map.py must still read ~/.config/waypoint (not a private fixture) and still check KesMine's focus.
The owner's real config is only read, never written. Prints PASS/FAIL per check. 🔴 READ-ONLY during a local run."""
import os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
SPR = Path(__file__).resolve().parents[1]; HOME = Path.home(); WP = HOME / ".config/waypoint"
fails = 0
def check(ok, msg):
    global fails
    print(("PASS " if ok else "FAIL ") + msg, flush=True); fails += not ok
def run(sprites, home):
    env = dict(os.environ, HOME=str(home), AUGUR_LODESTAR=str(HOME / "dev/Lodestar"))
    r = subprocess.run([sys.executable, str(sprites / "tests/test_project_map.py")], env=env, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr)[-600:]
def flip(text):
    out = []
    for l in text.splitlines():
        cells = l.split("|")
        if len(cells) > 3 and cells[1].strip() in ("KesMine", "KestrelWorks"):
            i = len(cells) - 2                      # the last cell is the Focus column
            cells[i] = " " if cells[i].strip().lower() in ("yes", "y", "true", "1", "x") else " yes "
            l = "|".join(cells)
        out.append(l)
    return "\n".join(out) + "\n"
tmp = Path(tempfile.mkdtemp())
fx = tmp / "home"; (fx / ".config/waypoint").mkdir(parents=True)
# waypoints.md holds absolute /Users/<me>/dev paths while the registry holds ~/dev: re-root both tables at the fixture
# HOME (whose dev/ is a symlink to the real one) so the join is the same as on the live tables.
for f in ("waypoints.md", "launches.md"):
    (fx / ".config/waypoint" / f).write_text((WP / f).read_text().replace(str(HOME) + "/", str(fx) + "/"))
(fx / ".config/waypoint/launches.md").write_text(flip((fx / ".config/waypoint/launches.md").read_text()))
(fx / "dev").symlink_to(HOME / "dev")                # registry paths are ~/dev/...: resolve to the same real dirs
def tree(mutant):
    t = Path(tempfile.mkdtemp(dir=tmp)); s = t / "sprites"
    for rel in ("tests/test_project_map.py", "app/projects.js", "prototype/labels/shortname.js"):
        (s / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy(SPR / rel, s / rel)
    (t / "augur").symlink_to(SPR.parent / "augur")
    if mutant:
        p = s / "app/projects.js"; src = p.read_text()
        new = src.replace("Object.assign(e, { alias, hex, focus }); }", f"Object.assign(e, {{ alias, hex, focus: {mutant} }}); }}")
        assert new != src, "mutation point not found in projects.js"; p.write_text(new)
    return s
rc, out = run(SPR, HOME); check(rc == 0, f"test_project_map passes on the live Waypoint tables [rc {rc}] {out.strip().splitlines()[-1] if out.strip() else ''}")
rc, out = run(tree(None), fx); check(rc == 0, f"test_project_map passes with KesMine/KestrelWorks focus flipped [rc {rc}] {out.strip().splitlines()[-1] if out.strip() else ''}")
rc, _ = run(tree("true"), fx); check(rc != 0, f"test_project_map FAILS when projects.js marks every row focused (flipped tables) [rc {rc}]")
rc, _ = run(tree("false"), HOME); check(rc != 0, f"test_project_map FAILS when projects.js marks no row focused (live tables) [rc {rc}]")
src = (SPR / "tests/test_project_map.py").read_text()
check('HOME / ".config/waypoint/launches.md"' in src and '"kestrel"' in src and "focus" in src,
      "test_project_map still reads the live ~/.config/waypoint tables and still checks the kestrel focus")
print(f"{5 - fails} passed, {fails} failed"); sys.exit(1 if fails else 0)
