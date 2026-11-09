"""The owner's load-testing rule, as a refusal: load (renders, stress, CPU burns) may ONLY run on on-site network without the VPN.

Owner, standing rule for the Laptop: "Load testing may ONLY happen while on on-site network without the VPN. Period."
Augur publishes the network state at machine.vpn in its snapshot; we proceed only when on_site is true and state is not
'up'. Missing, unreadable, malformed or stale (now > valid_until) is a REFUSAL, never a pass: unknown = don't run.

Shared by tests/tools/gate.py and tools/size_calibrate.py (gate.py is also copied alone to the agent storage root by
tests/run_all.sh, which copies this file beside it).
Env: SPRITES_AUGUR_SNAPSHOT -- snapshot path (default ~/agent-storage/augur/live/snapshot.json); tests point it at a fixture.
"""
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_SNAPSHOT = Path.home() / "agent-storage/augur/live/snapshot.json"


def refusal(snapshot=None, now=None):
    """None when load is allowed, else the reason string."""
    path = Path(snapshot or os.environ.get("SPRITES_AUGUR_SNAPSHOT") or DEFAULT_SNAPSHOT)
    try:
        snap = json.loads(path.read_text())
        vpn = snap["machine"]["vpn"]
        valid_until = float(snap["valid_until"])
        on_site, state = vpn["on_site"], vpn["state"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        return f"cannot read machine.vpn from {path} ({type(e).__name__}: {e}); unknown = don't run"
    if (time.time() if now is None else now) > valid_until:
        return f"Augur snapshot {path} is stale (valid_until passed); unknown = don't run"
    if on_site is not True:
        return f"machine is not on site (on_site={on_site!r})"
    if state == "up":
        return "VPN is up"
    return None


def require(snapshot=None, now=None):
    """Exit 3 with a message naming the rule unless load is allowed."""
    why = refusal(snapshot, now)
    if why:
        print(f"REFUSED: {why}. Rule (owner): load testing may ONLY happen on on-site network without the VPN. Period.", file=sys.stderr)
        sys.exit(3)
