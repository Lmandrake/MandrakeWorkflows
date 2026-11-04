#!/usr/bin/env python3
"""rc_account.py — switch the machine between two (or more) Claude accounts.

    rc account                 list slots; mark the live one
    rc account save <name>     save the LIVE login into slot <name>
    rc account add <name>      save the live login to its slot, then `claude auth login`
                               for the other account, then save that as slot <name>
    rc account <name>          switch: save the live login back to its own slot, swap
                               slot <name> in, stop the Remote Control server

WHY SLOTS AND NOT /login EACH TIME
Every `/login` is an interactive browser round-trip AND (measured 2026-09-19, 4 of 4
events) drops Remote Control in every other window on the machine. The drop cannot be
avoided — the account genuinely changes — but the browser can: a refresh token lives
~4 weeks (`refreshTokenExpiresAt`), so a slot saved this week is still good next week.

WHAT A SLOT HOLDS  (~/.claude/accounts/<name>/, mode 0700)
    credentials.json   the whole ~/.claude/.credentials.json (claudeAiOauth + mcpOAuth)
    oauthAccount.json  the `oauthAccount` object out of ~/.claude.json — the identity the
                       CLI shows and (probably — UNMEASURED) what Remote Control compares
                       when it says "account or organization changed"

THE ORDER OF A SWITCH IS THE WHOLE SAFETY
The live credentials are saved BACK to their own slot before the other slot is copied
in. If Claude rotates refresh tokens on use (UNMEASURED), the slot always holds the
newest one and nothing is lost; if it does not, the save-back is harmless.

WHAT A SWITCH DOES NOT DO
It does not restart the windows. Running sessions keep the old token in memory until
they restart, and they will print the "account changed" line and lose Remote Control.
So a switch is done at a fleet boundary: `rc account <name>`, then close the windows
(or let them finish and hand off), then `rc fleet`. The Remote Control server IS
stopped here, because it is stateless (its spawned sessions survive) and a server on
the wrong account is worse than none. The phone's Claude app must switch to the same
account to see this machine.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
CREDS = os.path.join(HOME, ".claude", ".credentials.json")
STATE = os.path.join(HOME, ".claude.json")
SLOTS = os.path.join(HOME, ".claude", "accounts")


def live_identity():
    try:
        return json.load(open(STATE)).get("oauthAccount") or {}
    except (OSError, ValueError):
        return {}


def slot_dir(name):
    return os.path.join(SLOTS, name)


def slot_identity(name):
    try:
        return json.load(open(os.path.join(slot_dir(name), "oauthAccount.json")))
    except (OSError, ValueError):
        return {}


def slots():
    if not os.path.isdir(SLOTS):
        return []
    return sorted(d for d in os.listdir(SLOTS) if os.path.isfile(os.path.join(slot_dir(d), "credentials.json")))


def slot_for_live():
    live = live_identity().get("accountUuid")
    for s in slots():
        if live and slot_identity(s).get("accountUuid") == live:
            return s
    return None


def save(name, quiet=False):
    ident = live_identity()
    if not ident.get("accountUuid") or not os.path.isfile(CREDS):
        sys.exit("no live login to save (no oauthAccount in ~/.claude.json or no credentials file)")
    d = slot_dir(name)
    os.makedirs(d, mode=0o700, exist_ok=True)
    os.chmod(d, 0o700)
    shutil.copy2(CREDS, os.path.join(d, "credentials.json"))
    with open(os.path.join(d, "oauthAccount.json"), "w") as fh:
        json.dump(ident, fh, indent=1)
    for f in ("credentials.json", "oauthAccount.json"):
        os.chmod(os.path.join(d, f), 0o600)
    if not quiet:
        print(f"saved live login ({ident.get('emailAddress')}) as slot '{name}'")


def stop_rc_server():
    out = subprocess.run(["pgrep", "-f", "claude remote-control"], capture_output=True, text=True).stdout.split()
    for pid in out:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            pass
    if out:
        time.sleep(2)
        print(f"stopped the Remote Control server ({len(out)} process) — `rc server` or `rc fleet` restarts it on the new account")


def switch(name):
    if name not in slots():
        sys.exit(f"no slot '{name}'. slots: {', '.join(slots()) or 'none'}   (rc account add {name})")
    target = slot_identity(name)
    if live_identity().get("accountUuid") == target.get("accountUuid"):
        print(f"already on '{name}' ({target.get('emailAddress')})")
        return
    # 1. the live login goes back to its own slot first (newest tokens win)
    cur = slot_for_live()
    if cur:
        save(cur, quiet=True)
        print(f"saved the current login back to slot '{cur}'")
    else:
        print("⚠️ the current login matches no slot — it is NOT saved. Ctrl-C now and `rc account save <name>` if you want it back later.")
        time.sleep(4)
    # 2. swap the credentials file, then the identity block in ~/.claude.json
    shutil.copy2(os.path.join(slot_dir(name), "credentials.json"), CREDS)
    os.chmod(CREDS, 0o600)
    state = json.load(open(STATE))
    state["oauthAccount"] = target
    tmp = STATE + ".rc_account.tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=2)
    os.replace(tmp, STATE)
    # 3. a server on the wrong account is worse than none
    stop_rc_server()
    print(f"\nswitched to '{name}' ({target.get('emailAddress')}).")
    print("  Windows already open keep the OLD account until restarted, and will lose Remote Control.")
    print("  Next: close them (or let them hand off), then `rc fleet` — and switch the phone's Claude app to the same account.")


def add(name):
    cur = slot_for_live()
    if cur:
        save(cur, quiet=True)
        print(f"current login ({live_identity().get('emailAddress')}) saved back to slot '{cur}'")
    else:
        sys.exit("the current login has no slot yet — run `rc account save <name-for-this-account>` first, so it can be switched back to")
    print(f"\nNow sign in as the OTHER account. This opens the normal Claude login (browser or code paste).")
    print("Every open Claude window will lose Remote Control when this completes — that is expected.\n")
    r = subprocess.run(["claude", "auth", "login"])
    if r.returncode != 0:
        sys.exit("login did not complete; nothing saved")
    if live_identity().get("accountUuid") == slot_identity(cur).get("accountUuid"):
        sys.exit("still on the same account after login — the other account was not chosen; nothing saved")
    save(name)
    stop_rc_server()
    print(f"\nslot '{name}' ready. `rc account {cur}` / `rc account {name}` switch between them from now on.")


def show():
    live = live_identity()
    print(f"live: {live.get('emailAddress','?')}  ({live.get('subscriptionType') or live.get('billingType','?')})")
    ss = slots()
    if not ss:
        print("slots: none — `rc account save <name>` to save this login, then `rc account add <other>`")
        return
    for s in ss:
        ident = slot_identity(s)
        mark = "  <- live" if ident.get("accountUuid") == live.get("accountUuid") else ""
        try:
            exp = json.load(open(os.path.join(slot_dir(s), "credentials.json")))["claudeAiOauth"]["refreshTokenExpiresAt"] / 1000
            days = int((exp - time.time()) / 86400)
            life = f"refresh token good for {days} more days" if days > 0 else "refresh token EXPIRED — `rc account add` again"
        except (KeyError, ValueError, OSError):
            life = "token lifetime unknown"
        print(f"  {s:<12} {ident.get('emailAddress','?'):<32} {life}{mark}")


def main(argv):
    if not argv:
        show()
    elif argv[0] == "save" and len(argv) == 2:
        save(argv[1])
    elif argv[0] == "add" and len(argv) == 2:
        add(argv[1])
    elif len(argv) == 1:
        switch(argv[0])
    else:
        sys.exit(__doc__.split("\n\n")[0])


if __name__ == "__main__":
    main(sys.argv[1:])
