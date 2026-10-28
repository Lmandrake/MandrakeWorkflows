#!/usr/bin/env python3
"""PreToolUse hook: refuse to Read a heavy original when a usable digest sits beside it.

This is the layer that does not depend on a session choosing to care. The skill
(layer 1), the always-loaded CLAUDE.md block (layer 2) and the session-start
announce (layer 3) are all *nudges*: they put text in front of a model and hope.
This one costs the model its Read call.

## What it blocks, and what it deliberately does not

Only `Read`, and only on a heavy extension (`HEAVY` below). Everything else is
allowed through untouched, which is what makes the regeneration path safe:
`digest` and `refresh` open originals from inside `placard.py` under Bash, and a
`Read`-matched hook never sees them. Extraction is not a Read.

The decision is delegated, never reimplemented. `placard.py read` already owns
the state machine and encodes the verdict in its exit status
(`placard.py:cmd_read`): **0 for `ok`/`legacy`, non-zero for everything else.**
Those two states are exactly "the digest can answer"; the rest are
`source-stale` / `extraction-stale` (regenerate), `body-missing` (retry) and
`unavailable` / `needs-source-inspection` (which `placardlib/read.py:
authorizes_original` defines as the two states that *permit* opening the
original). So a non-zero exit means the original is authorized and this hook
gets out of the way.

🔴 **Do not replace that exit-code check with a parse of the printed state.**
The state vocabulary belongs to `placardlib.read`, not to this file, and the
characteristic defect in this repo is a gate comparing against a vocabulary it
assumed rather than measured — a snake_case/Title-Case mismatch made the figure
gate inert while its unit tests passed, because the fixtures shared the code's
assumption. Keying on the exit code means this hook cannot drift
out of agreement with the state machine, because it never names a state.

## Fail open, always

Every unexpected condition — no payload, no `placard.py`, no python, a timeout,
any exception — exits 0 and allows the Read. A guard that breaks a session when
the guarded subsystem is absent is worse than no guard. The cost of a miss is a
wasted extraction; the cost of a false block is a session that cannot read its
own files.

## Blocking mechanism

Exit 2 with the reason on stderr, not `permissionDecision: deny`. A session
running `defaultMode=bypassPermissions` skips permission decisions entirely,
but a blocking exit code is still honoured.

## The override, and why it is a token rather than an env var

A `Read` tool call carries no environment, so `PLACARD_ALLOW_ORIGINAL=1` is
unreachable from the thing being blocked — an env-var escape hatch would read as
an escape hatch while being unusable, which is the exact class of dead promise
this file exists to remove. Instead:

    python3 contrib/placard_read_guard.py --allow-once <file>

writes a single-use token that the next Read of that file consumes. One Bash
call, agent-actionable, and it leaves the override as a deliberate recorded act
rather than a silent default.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Text-extractable heavy artifacts — Placard's unit. Images are deliberately
# absent: a Read of an image is a *visual* read, which a text body cannot serve
# and which `needs-source-inspection` exists to authorize. Blocking those would
# fail closed on exactly the work the original is needed for.
HEAVY = {".pdf", ".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".xls"}

ALLOW = 0   # stay out of the way
BLOCK = 2   # refuse, reason on stderr


def _token_path(target: Path) -> Path:
    """One-shot override token, keyed by resolved path so it cannot leak to
    another file. Lives in the system temp dir: an override should not survive a
    reboot."""
    digest = hashlib.sha256(str(target).encode("utf-8")).hexdigest()[:32]
    return Path(tempfile.gettempdir()) / f"placard-allow-{digest}"


def _placard_py() -> Path | None:
    raw = os.environ.get("PLACARD_PY") or str(Path.home() / "dev/MandrakeWorkflows/tools/placard/placard.py")
    p = Path(raw).expanduser()
    return p if p.is_file() else None


def _body_path(sidecar: Path) -> str | None:
    """The entry names its body when the body is a separate file. Best-effort:
    this is for the message only, so any failure just omits a line."""
    try:
        head = sidecar.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return None
    m = re.search(r"^body_path:\s*(.+?)\s*$", head, re.M)
    if not m:
        return None
    name = m.group(1).strip().strip("'\"")
    if not name or name in ("null", "none", "~"):
        return None
    return str((sidecar.parent / name).resolve())


def _refuse(target: Path, sidecar: Path) -> int:
    body = _body_path(sidecar)
    lines = [
        "",
        "⛔ Placard: read the digest, not the original.",
        "",
        f"   {target.name} has a digest beside it that reports it CAN answer,",
        "   so this Read was refused. The digest's `## Full text` section is the",
        "   cleaned, faithful extraction of this file — extract once, read many.",
        "",
        f"   digest: {sidecar}",
    ]
    if body:
        lines.append(f"   body:   {body}")
    lines += [
        "",
        "   Read that instead. To get it with its state checked:",
        f"     python3 {_placard_py()} read {target}",
        "",
        "   This is not a wall — the guard allows the original automatically when",
        "   the digest cannot answer (`unavailable`, `needs-source-inspection`) or",
        "   is stale (`source-stale`, `extraction-stale` — re-digest instead).",
        "",
        "   If you genuinely need the original itself (pixels, exact layout, a",
        "   figure's actual content), take the override deliberately:",
        f"     python3 {Path(__file__).resolve()} --allow-once {target}",
        "   then Read it again. The token is consumed by that one Read.",
        "",
    ]
    sys.stderr.write("\n".join(lines))
    return BLOCK


def main() -> int:
    # Fast path: most Reads are not heavy types. Peek at the raw payload before
    # any parsing/path work (the extension must appear in it to matter).
    try:
        raw_in = sys.stdin.read()
    except Exception:
        return ALLOW
    low = raw_in.lower()
    if not any(ext in low for ext in HEAVY):
        return ALLOW
    try:
        payload = json.loads(raw_in)
    except Exception:
        return ALLOW

    # The matcher should scope this to Read, but never rely on configuration to
    # enforce a precondition the code can check itself.
    tool = payload.get("tool_name")
    if tool is not None and tool != "Read":
        return ALLOW

    raw = (payload.get("tool_input") or {}).get("file_path")
    if not raw:
        return ALLOW

    try:
        target = Path(raw).expanduser()
    except Exception:
        return ALLOW

    if target.suffix.lower() not in HEAVY:
        return ALLOW
    if not target.is_file():
        return ALLOW

    # A deliberate one-shot override, consumed here so it cannot persist.
    token = _token_path(target.resolve())
    if token.exists():
        try:
            token.unlink()
        except OSError:
            pass
        return ALLOW

    sidecar = target.with_name(target.name + ".placard.md")
    if not sidecar.is_file():
        # No digest. Allow — and say nothing. Finding none is not a reason to
        # make them: a session nudged here would go digest unasked.
        return ALLOW

    placard = _placard_py()
    if placard is None:
        return ALLOW
    py = shutil.which("python3") or "/usr/bin/python3"
    if not os.access(py, os.X_OK):
        return ALLOW

    try:
        proc = subprocess.run(
            [py, str(placard), "read", str(target)],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return ALLOW  # fail open: a guard must not break the session

    # 0 == state ok|legacy == the digest can answer. Anything else authorizes
    # the original (stale, body-missing, unavailable, needs-source-inspection).
    if proc.returncode != 0:
        return ALLOW

    return _refuse(target, sidecar)


def _allow_once(arg: str) -> int:
    target = Path(arg).expanduser()
    try:
        resolved = target.resolve()
    except Exception:
        resolved = target
    path = _token_path(resolved)
    path.write_text("", encoding="utf-8")
    print(f"Placard: one-shot override armed for {resolved}")
    print("The next Read of that file will be allowed, and the token consumed.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--allow-once":
        if len(sys.argv) != 3:
            sys.stderr.write("usage: placard_read_guard.py --allow-once <file>\n")
            sys.exit(1)
        sys.exit(_allow_once(sys.argv[2]))
    sys.exit(main())
