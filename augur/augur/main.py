"""Augur's entry: resolve the storage home, build the collectors, run the core."""

import argparse
import json
import os
import subprocess
import sys
import time

from augur import core

AUGUR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(AUGUR_DIR)


def storage_home(env=None):
    """$AUGUR_HOME, else <agent storage root>/augur from Lodestar's helper. Fails by name."""
    e = os.environ if env is None else env
    if e.get("AUGUR_HOME"):
        return os.path.expanduser(e["AUGUR_HOME"])
    helper = os.path.expanduser("~/dev/Lodestar/bin/lib/agent_storage.py")
    try:
        root = subprocess.run([sys.executable, helper], capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError) as ex:
        raise SystemExit("augur: AUGUR_HOME unset and agent_storage.py failed (%s)" % ex)
    if not root:
        raise SystemExit("augur: AUGUR_HOME unset and agent_storage.py printed no root")
    return os.path.join(root, "augur")


BACKOFF_S = (5.0, 15.0, 60.0, 300.0)


def make_core(build, sleep=time.sleep, log=None, tries=None):
    """RB-n15: storage that is read-only or not mounted makes Core() raise OSError. Exiting would
    have launchd restart us every 20 s (~4,300 full start-ups a day), so wait and retry in
    process with a growing back-off, one log line per attempt (type and errno only). `tries`
    bounds the attempts (tests); the OSError of the last one is re-raised."""
    log = log or (lambda m: (sys.stderr.write("%s augur: %s\n" % (
        time.strftime("%Y-%m-%dT%H:%M:%S%z"), m)), sys.stderr.flush()))
    n = 0
    while True:
        try:
            return build()
        except OSError as e:
            n += 1
            if tries is not None and n >= tries:
                raise
            wait = BACKOFF_S[min(n - 1, len(BACKOFF_S) - 1)]
            log("storage not writable (%s); retry %d in %.0f s" % (core.err_text(e), n, wait))
            sleep(wait)


def build_collectors():
    out = []
    from augur.collectors import machine, sessions
    from augur.lodestar import burning
    out.extend(machine.all_collectors())
    out.extend(sessions.all_collectors())
    from augur.collectors import api
    out.append(api.ApiCollector())          # after sessions: reads shared["transcript_dirs"]
    out.extend(burning.all_collectors())
    return out


def main(argv):
    ap = argparse.ArgumentParser(prog="augur")
    ap.add_argument("--once", action="store_true", help="run every tier once (twice, for deltas) and print")
    ap.add_argument("--ticks", type=int, default=0, help="run N fast ticks then exit")
    a = ap.parse_args(argv)
    home = storage_home()
    core.install_spawn_counter()
    c = make_core(lambda: core.Core(build_collectors(), home, repo_dir=REPO_DIR,
                                    platform=sys.platform if sys.platform in ("darwin", "linux") else "windows"))
    sys.stderr.write("%s augur: start pid %d rev %s home %s PATH=%s\n" % (
        time.strftime("%Y-%m-%dT%H:%M:%S%z"), os.getpid(), c.rev, home, os.environ.get("PATH")))
    sys.stderr.flush()
    if a.once or a.ticks:
        n = a.ticks or 3
        snap = None
        for i in range(n):
            snap = c.tick() or snap
            if i < n - 1:
                time.sleep(c.cadence["fast"])
        print(json.dumps(snap, indent=1))
        return 0
    c.run_forever()
    return 0
