#!/usr/bin/env python3
"""Mark the network this Mac is on now as WORK, for Augur's machine.vpn.on_site (Sprites' "Hide @ Work").

Run it once while connected at work:  python3 augur/bin/work_here.py
It reads the domain name each active network service was handed by DHCP (option 15, e.g.
"wifi.example.com") and appends it to $AUGUR_HOME/config/work.json as {"dhcp_domains": [...]}. Augur
re-reads that file within seconds; no restart. A suffix matches itself and any sub-domain, so you may
edit the file down to "example.com" to cover every building's network.
  --list      print the current DHCP domains and the saved ones; change nothing
  --domain D  save D instead of reading the current network
  --clear     remove work.json (on_site then rests on the SSID helper alone, if any)
Nothing leaves the machine; the snapshot carries only the boolean."""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from augur import main as M                      # noqa: E402  storage_home(): $AUGUR_HOME, else the agent storage root
from augur.collectors.machine import WORK_FILE   # noqa: E402
from augur.darwin import native                  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--list", action="store_true")
    g.add_argument("--domain")
    g.add_argument("--clear", action="store_true")
    a = ap.parse_args(argv)
    path = os.path.join(M.storage_home(), WORK_FILE)
    try:
        with open(path) as fh:
            saved = list(json.load(fh).get("dhcp_domains") or [])
    except (OSError, ValueError, AttributeError):
        saved = []
    if a.clear:
        if os.path.exists(path):
            os.remove(path)
        print("removed %s" % path)
        return 0
    now = native.dhcp_domains()
    if a.list:
        print("current DHCP domains: %s" % (", ".join(now) if now else "none"))
        print("saved as work (%s): %s" % (path, ", ".join(saved) if saved else "none"))
        return 0
    add = [a.domain.strip().rstrip(".").lower()] if a.domain else (now or [])
    if not add or not add[0]:
        print("no DHCP domain on any network right now; pass --domain example.com", file=sys.stderr)
        return 2
    keep = saved + [d for d in add if d not in saved]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"dhcp_domains": keep}, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)
    print("work networks: %s (%s)" % (", ".join(keep), path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
