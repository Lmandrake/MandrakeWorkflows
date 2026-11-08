#!/usr/bin/env python3
"""The render gate: run ONE render at a time machine-wide, at nice 19, and only when the machine is not already loaded.

Why it exists (docs/NATIVE_PORT_HANDOFF.md, "Tools"): every browser/offscreen render in the Sprites suites is a heavy,
GPU- and CPU-hungry job on the owner's working machine. Two at once skew every timing measurement the suites make and
make the Mac unusable while they run. So each render takes an exclusive flock and waits its turn.

🔴 THIS FILE IS THE CONTRACT, RECOVERED, NOT A STUB. It was only ever created under the agent storage root
(~/agent-storage/sprites/live/native/tools/gate.py) and never committed, so when that tree was cleared, `tests/run_all.sh`
refused to start at all and EVERY browser-rendered suite silently stopped running — the failure looked like "missing
file", not like "11 test files are no longer being executed". Committing it is the fix: `run_all.sh` installs this copy
to the documented path when it is absent.

Usage:  gate.py CMD [ARGS...]      -- runs CMD under the gate; exits with CMD's exit status.
Env:    SPRITES_GATE_MAX_LOAD      -- 1-minute load ceiling (default 8)
        SPRITES_GATE_TIMEOUT       -- seconds to wait for the lock and for the load to fall (default 1800)
        SPRITES_GATE_NICE          -- niceness (default 19); 0 disables renicing
"""
import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path

LOCK = Path(os.environ.get("SPRITES_GATE_LOCK", str(Path.home() / "agent-storage/sprites/live/native/tools/.gate.lock")))
MAX_LOAD = float(os.environ.get("SPRITES_GATE_MAX_LOAD", "8"))
TIMEOUT = float(os.environ.get("SPRITES_GATE_TIMEOUT", "1800"))
NICENESS = int(os.environ.get("SPRITES_GATE_NICE", "19"))


def load1() -> float:
    """1-minute load average; 0.0 where the platform will not say (never a reason to refuse to run)."""
    try:
        return os.getloadavg()[0]
    except OSError:
        return 0.0


def wait_for_load(deadline: float) -> None:
    """Hold until the 1-minute load is under the ceiling, or the deadline passes (then run anyway, saying so)."""
    while load1() >= MAX_LOAD:
        if time.monotonic() >= deadline:
            print(f"gate: load {load1():.1f} still >= {MAX_LOAD} at the deadline; running anyway", file=sys.stderr)
            return
        time.sleep(5)


def main(argv: list) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + TIMEOUT
    with open(LOCK, "a+") as fh:
        # Exclusive and BLOCKING: the whole point is that renders queue rather than overlap. A non-blocking failure
        # here would silently skip the render, which is the class of bug this file's absence already caused once.
        waited = time.monotonic()
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            held = time.monotonic() - waited
            if held > 1:
                print(f"gate: waited {held:.0f}s for the render lock", file=sys.stderr)
            wait_for_load(deadline)
            if NICENESS > 0:
                try:
                    os.nice(NICENESS)
                except OSError as e:   # a lowered niceness cannot be raised back; not worth refusing the render
                    print(f"gate: could not renice ({e})", file=sys.stderr)
            return subprocess.call(argv)
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
