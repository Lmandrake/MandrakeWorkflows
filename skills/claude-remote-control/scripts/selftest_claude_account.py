#!/usr/bin/env python3
"""Selftest for claude_account.py on a fake $HOME with a fake `claude` binary.

Never touches a real login or a real process: HOME is a temp dir, CLAUDE_ACCOUNT_CLAUDE_BIN
is a stub, and claude_pids/os.kill/fleet_start are replaced before any switch runs.
    python3 scripts/selftest_claude_account.py
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, sys, time, hashlib
home = os.environ["HOME"]
cfg = os.environ.get("CLAUDE_CONFIG_DIR")
cred = os.path.join(cfg, ".credentials.json") if cfg else os.path.join(home, ".claude", ".credentials.json")
cj = os.path.join(cfg, ".claude.json") if cfg else os.path.join(home, ".claude.json")
def load(p):
    try: return json.load(open(p))
    except Exception: return None
a = sys.argv[1:]
if a[:2] == ["auth", "status"]:
    c, j = load(cred), load(cj) or {}
    print(json.dumps({"loggedIn": bool(c), "email": (j.get("oauthAccount") or {}).get("emailAddress")}))
elif a[:2] == ["auth", "login"]:
    email = os.environ.get("FAKE_LOGIN_AS") or a[a.index("--email") + 1]
    print("Visit https://claude.ai/oauth/authorize?code=true&x=1 to log in"); sys.stdout.flush()
    code = sys.stdin.readline().strip()
    os.makedirs(cfg, exist_ok=True)
    json.dump({"claudeAiOauth": {"refreshToken": "rt-" + code, "accessToken": "a", "expiresAt": int(time.time()*1000) + 8*3600e3,
               "refreshTokenExpiresAt": int(time.time()*1000) + 30*86400e3}}, open(cred, "w"))
    json.dump({"oauthAccount": {"emailAddress": email}}, open(cj, "w"))
    print("Login successful")
elif a and a[0] == "-p":
    if os.environ.get("FAKE_WARM_FAIL"):
        print("API Error: 401 OAuth token has expired", file=sys.stderr); sys.exit(1)
    if "--setting-sources" not in a or "--strict-mcp-config" not in a: sys.exit("warm must be neutral")
    c = load(cred)
    if c and c["claudeAiOauth"]["expiresAt"] < time.time()*1000:
        c["claudeAiOauth"]["refreshToken"] += "+"
        c["claudeAiOauth"]["expiresAt"] = int(time.time()*1000 + 8*3600e3)
        c["claudeAiOauth"]["refreshTokenExpiresAt"] += 86400e3
        json.dump(c, open(cred, "w"))
    print("OK")
else:
    sys.exit("fake claude: unsupported " + " ".join(a))
'''

FAILS = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def make_login(cfg_dir, json_path, email, rt, expired_access=False, rt_days=20):
    import time
    os.makedirs(cfg_dir, exist_ok=True)
    t = time.time() * 1000
    json.dump({"claudeAiOauth": {"refreshToken": rt, "accessToken": "x",
                                 "expiresAt": int(t - 3600e3 if expired_access else t + 3600e3),
                                 "refreshTokenExpiresAt": int(t + rt_days * 86400e3)}},
              open(os.path.join(cfg_dir, ".credentials.json"), "w"))
    d = json.load(open(json_path)) if os.path.exists(json_path) else {}
    d["oauthAccount"] = {"emailAddress": email}
    d.setdefault("projects", {"/x": {"trusted": True}})
    json.dump(d, open(json_path, "w"))


def capture_tests(ca, check, refused, fake_pids):
    """Auto-capture: a /login in a window must never lose the account it replaced."""
    vc = lambda a: os.path.join(ca.vault(a), ".credentials.json")
    h = lambda p: (ca.cred_meta(p) or {}).get("rt_hash")
    fake_pids[:] = [99]  # windows are open, as on a real machine
    # start clean: alt live, nothing vaulted for alt, lukas dormant (whatever its state)
    for a in ("alt",):
        if os.path.isdir(ca.vault(a)):
            import shutil
            shutil.rmtree(ca.vault(a))
    make_login(ca.LIVE_DIR, ca.LIVE_JSON, "alt@example.com", "rt-alt-1")
    s = ca.cmd_status()
    check(s["capture"]["result"] == "captured" and h(vc("alt")) == h(ca.LIVE_CRED),
          "capture: status backs up the live login into its vault")
    check(oct(os.stat(vc("alt")).st_mode & 0o777) == "0o600" and oct(os.stat(ca.vault("alt")).st_mode & 0o777) == "0o700",
          "capture: vault copy 0600 in a 0700 dir")
    check(ca.email_in(os.path.join(ca.vault("alt"), ".claude.json")) == "alt@example.com",
          "capture: vault .claude.json carries the account's email")
    check(ca.cmd_status()["capture"]["result"] == "current", "capture: unchanged live login is not re-copied")
    check([a for a in s["accounts"] if a["name"] == "alt"][0]["vault_note"].startswith("backed up"),
          "capture: status says the live account is backed up")
    # the live login rotates (a Claude refresh): the backup follows it
    make_login(ca.LIVE_DIR, ca.LIVE_JSON, "alt@example.com", "rt-alt-2")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ca.main(["--json", "capture"])
    r = json.loads(buf.getvalue())
    check(rc == 0 and r["result"] == "captured" and h(vc("alt")) == h(ca.LIVE_CRED),
          "capture: a rotated live login refreshes the backup (CLI `capture`, the timer's command)")
    # rotate again with NO capture, then someone does /login as system in a window
    make_login(ca.LIVE_DIR, ca.LIVE_JSON, "alt@example.com", "rt-alt-3-uncaptured")
    st_backup = h(vc("alt"))
    make_login(ca.LIVE_DIR, ca.LIVE_JSON, "system@example.com", "rt-system-login")
    s = ca.cmd_status()
    info = ca.capture_info("alt")
    check(s["live"] == "system" and h(vc("system")) == h(ca.LIVE_CRED), "email change: the new live account is captured")
    check(h(vc("alt")) == st_backup and ca.where("alt") == "vault",
          "email change: the previous account keeps its last captured copy")
    check(info.get("replaced_by_email_change") and "may need re-login" in info["note"] and info["captured_at"] in info["note"],
          "rotation-stale: old copy marked 'captured-at <ts>, may need re-login'")
    row = [a for a in s["accounts"] if a["name"] == "alt"][0]
    check(row["vault_note"] and "may need re-login" in row["vault_note"], "rotation-stale: status shows the mark")
    check(s["capture"]["previous"]["account"] == "alt", "email change: reported in the status capture result")
    s2 = ca.cmd_status()
    check(s2["capture"].get("previous") is None and ca.capture_info("alt")["note"] == info["note"],
          "email change: marked once, not re-marked every poll")
    # an unregistered email is not captured and is flagged
    make_login(ca.LIVE_DIR, ca.LIVE_JSON, "stranger@example.com", "rt-stranger")
    check(ca.cmd_status()["capture"]["result"] == "unregistered-email" and not os.path.exists(ca.vault("stranger")),
          "capture: an unregistered login is flagged, not vaulted")
    make_login(ca.LIVE_DIR, ca.LIVE_JSON, "system@example.com", "rt-system-login")
    ca.cmd_status()
    # DISARMED gates switches only: capture still backs up the live login (it never changes it)
    open(ca.DISARMED, "w").write("test")
    make_login(ca.LIVE_DIR, ca.LIVE_JSON, "system@example.com", "rt-system-disarmed")
    live_before = h(ca.LIVE_CRED)
    r = ca.capture("t")
    check(r["result"] == "captured" and h(vc("system")) == live_before and h(ca.LIVE_CRED) == live_before,
          "disarmed: capture still backs up the live login and leaves it unchanged")
    check("DISARMED" in (refused(ca.cmd_use, "alt", "testbox") or "") and ca.live_account()[0] == "system",
          "disarmed: a switch is still refused")
    os.unlink(ca.DISARMED)
    # a journal (interrupted switch) blocks capture
    ca.write_json_atomic(ca.JOURNAL, {"op": "use", "step": "moving"})
    check(ca.capture("t")["result"] == "skipped-journal", "capture: never runs while a switch journal exists")
    os.unlink(ca.JOURNAL)
    # a busy lock skips instead of hanging
    with ca.MachineLock():
        check(ca.capture("t", wait=0.3)["result"] == "skipped-busy", "capture: a busy machine lock skips")
    # switching away MOVES the live credential (newer than its backup), never the older copy
    make_login(ca.LIVE_DIR, ca.LIVE_JSON, "system@example.com", "rt-system-rotated-uncaptured")
    sys_live = h(ca.LIVE_CRED)
    check(h(vc("system")) != sys_live, "setup: system's backup is older than its live login")
    fake_pids[:] = []
    trash_before = len(os.listdir(ca.TRASH)) if os.path.isdir(ca.TRASH) else 0
    # simulate the race: the live login rotated after the last capture and before the switch
    real_locked = ca._capture_locked
    ca._capture_locked = lambda reason: {"result": "suppressed"} if reason == "before-use" else real_locked(reason)
    res = ca.cmd_use("alt", "testbox")
    ca._capture_locked = real_locked
    check(res["changed"] and h(vc("system")) == sys_live and ca.capture_info("system")["origin"] == "moved",
          "switch away: the live credential itself is moved to the vault, not the older backup")
    check((len(os.listdir(ca.TRASH)) if os.path.isdir(ca.TRASH) else 0) == trash_before,
          "switch away: the superseded backup is deleted, not kept as another token copy in .trash")
    check("may need re-login" in res["message"] and h(ca.LIVE_CRED) == st_backup,
          "switch to a captured copy: the result warns it may need re-login")
    check(h(vc("alt")) == st_backup and ca.capture_info("alt")["origin"] == "capture"
          and not ca.capture_info("alt").get("replaced_by_email_change"),
          "after the switch the new live account is backed up again, unmarked")
    # warm proves a marked copy: mark system artificially as captured, expire its access token, warm
    info = {"origin": "capture", "captured_at": ca.iso(), "rt_hash": h(vc("system")),
            "replaced_by_email_change": ca.iso(), "note": "captured-at x, may need re-login"}
    ca._set_capture_info("system", info)
    c = json.load(open(vc("system")))
    c["claudeAiOauth"]["expiresAt"] = 0
    json.dump(c, open(vc("system"), "w"))
    w = ca.cmd_warm(["system"])
    check(w["results"]["system"]["result"] == "renewed" and not ca.capture_info("system").get("replaced_by_email_change"),
          "warm: a renewed captured copy loses its may-need-re-login mark")
    # a switch performed by `use` is not mistaken for a /login email change
    check(ca.capture_info("system")["note"].startswith("captured-at") and ca.cmd_status()["capture"].get("previous") is None,
          "a switch is not reported as a /login email change")


def main():
    tmp = tempfile.mkdtemp(prefix="ca-selftest-")
    os.environ["HOME"] = tmp
    for k in ("CLAUDE_CONFIG_DIR", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"):
        os.environ.pop(k, None)
    stub = os.path.join(tmp, "fake-claude")
    open(stub, "w").write(FAKE_CLAUDE)
    os.chmod(stub, 0o755)
    os.environ["CLAUDE_ACCOUNT_CLAUDE_BIN"] = stub
    spec = importlib.util.spec_from_file_location("ca", os.path.join(HERE, "claude_account.py"))
    ca = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ca)
    # hard isolation from real processes
    fake_pids = []
    ca.claude_pids = lambda: list(fake_pids)
    ca.under_claude = lambda: False
    ca.os.kill = lambda *a: (_ for _ in ()).throw(AssertionError("os.kill called in selftest"))
    starts = []
    ca.fleet_start = lambda conf: starts.append(1) or None
    ca.verify_relaunch = lambda timeout=0: ([1], [])
    ca.gateway_findings_orig = ca.gateway_findings
    ca.gateway_findings = lambda: []
    check(ca.HOME == tmp and ca.ROOT.startswith(tmp), "module reads the fake HOME")

    os.makedirs(ca.ROOT)
    open(ca.REGISTRY, "w").write("lukas lukas@example.com\nalt alt@example.com\nsystem system@example.com\n")
    json.dump({"machine": "testbox", "relaunch": ["true"]}, open(ca.MACHINE, "w"))
    make_login(ca.LIVE_DIR, ca.LIVE_JSON, "system@example.com", "rt-sys")
    s = ca.cmd_status()
    check(s["live"] == "system", "status: live account read from ~/.claude.json")
    check([a["where"] for a in s["accounts"]] == ["none", "none", "live"], "status: where of each account")

    def refused(fn, *a, **k):
        try:
            fn(*a, **k)
        except ca.Refused as e:
            return str(e)
        return None

    check("not enrolled" in (refused(ca.cmd_use, "lukas", "testbox") or ""), "use refuses an unenrolled account")
    check("--confirm testbox" in (refused(ca.cmd_use, "lukas", "") or ""), "use requires --confirm <machine>")
    check("unknown account" in (refused(ca.cmd_use, "bob", "testbox") or ""), "use refuses an unknown account")

    # enrollment: code via stdin path (cmd_code takes the string; main reads stdin)
    r = ca.cmd_enroll("lukas")
    check(r["url"].startswith("https://claude.ai/oauth"), "enroll prints the login URL")
    r2 = ca.cmd_code("lukas", r["op"], "CODE12345678")
    check(ca.where("lukas") == "vault", "code verifies and promotes into the vault: " + r2["message"])
    check(oct(os.stat(ca.vault("lukas")).st_mode & 0o777) == "0o700", "vault dir is 0700")
    # wrong Google account is refused and discarded
    os.environ["FAKE_LOGIN_AS"] = "someoneelse@example.com"
    r = ca.cmd_enroll("alt")
    msg = refused(ca.cmd_code, "alt", r["op"], "CODEABCDEFGH")
    os.environ.pop("FAKE_LOGIN_AS")
    check(msg and "not alt@example.com" in msg and ca.where("alt") is None, "enrollment as the wrong email is refused")
    check("no enrollment" in (refused(ca.cmd_code, "alt", "deadbeef00", "CODEABCDEFGH") or ""), "code without a live op is refused")

    # gateway mode refuses
    ca.gateway_findings = lambda: ["settings.json: apiKeyHelper is set"]
    check("not in subscription mode" in (refused(ca.cmd_use, "lukas", "testbox") or ""), "gateway mode refuses a switch")
    ca.gateway_findings = lambda: []
    # real gateway detector on the fake home
    os.makedirs(ca.LIVE_DIR, exist_ok=True)
    json.dump({"env": {"ANTHROPIC_BASE_URL": "https://gw"}}, open(os.path.join(ca.LIVE_DIR, "settings.json"), "w"))
    check(any("ANTHROPIC_BASE_URL" in f for f in ca.gateway_findings_orig()), "settings.json env routing var is detected")
    os.unlink(os.path.join(ca.LIVE_DIR, "settings.json"))

    # disarmed refuses
    open(ca.DISARMED, "w").write("test")
    check("DISARMED" in (refused(ca.cmd_use, "lukas", "testbox") or ""), "DISARMED machine refuses")
    os.unlink(ca.DISARMED)

    # the switch: system -> lukas
    fake_pids[:] = []
    sys_hash = ca.cred_meta(ca.LIVE_CRED)["rt_hash"]
    luk_hash = ca.cred_meta(os.path.join(ca.vault("lukas"), ".credentials.json"))["rt_hash"]
    res = ca.cmd_use("lukas", "testbox")
    check(res["changed"] and ca.live_account()[0] == "lukas", "use moves lukas live: " + res["message"])
    check(ca.cred_meta(ca.LIVE_CRED)["rt_hash"] == luk_hash, "live credential is lukas's grant")
    check(ca.cred_meta(os.path.join(ca.vault("system"), ".credentials.json"))["rt_hash"] == sys_hash,
          "system's grant moved (not copied) into its vault")
    lv = os.path.join(ca.vault("lukas"), ".credentials.json")
    check(ca.cred_meta(lv)["rt_hash"] == luk_hash and ca.capture_info("lukas")["origin"] == "capture"
          and oct(os.stat(lv).st_mode & 0o777) == "0o600",
          "the only second copy of lukas's grant is the auto-capture backup (0600, marked capture)")
    check(json.load(open(ca.LIVE_JSON)).get("projects"), "~/.claude.json keeps its other keys")
    check(starts == [1], "Fleet relaunched once")
    check(not os.path.exists(ca.JOURNAL), "journal cleared")
    check(ca.cmd_use("lukas", "testbox")["changed"] is False, "use of the live account is a no-op")

    # survivors abort without moving
    real_stop = ca.fleet_stop
    ca.fleet_stop = lambda: ([5], [5])
    check("could not stop" in (refused(ca.cmd_use, "system", "testbox") or "") and ca.live_account()[0] == "lukas",
          "a process that will not die aborts the switch, nothing moved")
    ca.fleet_stop = real_stop

    # verification failure rolls back and keeps both credentials
    real_status = ca.auth_status
    ca.auth_status = lambda cfg=None: {"loggedIn": False}
    msg = refused(ca.cmd_use, "system", "testbox")
    ca.auth_status = real_status
    check(msg and "rolled back" in msg and ca.live_account()[0] == "lukas"
          and ca.cred_meta(os.path.join(ca.vault("system"), ".credentials.json"))["rt_hash"] == sys_hash,
          "failed post-switch verification rolls back with both grants intact")

    # recover from a crash between the two renames
    j = {"op": "use", "from": "lukas", "to": "system", "step": "moving",
         "old_hash": luk_hash, "new_hash": sys_hash}
    ca.write_json_atomic(ca.JOURNAL, j)
    os.rename(ca.LIVE_CRED, os.path.join(ca.vault("lukas"), ".credentials.json"))  # half a move
    out = ca.recover(quiet=True)
    check(ca.live_account()[0] == "system" and ca.cred_meta(ca.LIVE_CRED)["rt_hash"] == sys_hash
          and not os.path.exists(ca.JOURNAL), "recover finishes a half-done move: " + str(out))
    check(refused(ca.cmd_use, "lukas", "testbox", dry_run=True) is None, "use is accepted again after recover")

    # warm: dormant system... now live is lukas again after the previous line? check and warm
    dormant = [a for a in ("lukas", "system") if ca.where(a) == "vault"][0]
    p = os.path.join(ca.vault(dormant), ".credentials.json")
    c = json.load(open(p))
    c["claudeAiOauth"]["expiresAt"] = 0
    json.dump(c, open(p, "w"))
    before = ca.cred_meta(p)
    w = ca.cmd_warm([dormant])
    after = ca.cred_meta(p)
    check(w["results"][dormant]["result"] == "renewed" and after["rt_hash"] != before["rt_hash"],
          "warm renews a dormant login and proves it (rotated hash)")
    check(ca.cmd_warm([dormant])["results"][dormant]["result"] == "ok-not-due", "warm reports not-due honestly")
    fake_pids[:] = [99]
    live = ca.live_account()[0]
    check(ca.cmd_warm([live])["results"][live]["result"] == "observed", "warm only observes the live account while Claude runs")
    fake_pids[:] = []
    os.environ["FAKE_WARM_FAIL"] = "1"
    check(ca.cmd_warm([dormant])["results"][dormant]["result"] == "failed-auth", "warm classifies an auth failure")
    os.environ.pop("FAKE_WARM_FAIL")
    check(ca.cmd_warm(["alt"])["results"]["alt"]["result"] == "not-enrolled", "warm skips an unenrolled account")

    # CLI: code from stdin, JSON refusal
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ca.main(["--json", "use", "alt", "--confirm", "testbox"])
    check(rc == 3 and json.loads(buf.getvalue())["ok"] is False, "CLI --json refusal exits 3 with ok:false")
    r = ca.cmd_enroll("alt")
    sys.stdin = io.StringIO("CODEFROMSTDIN1\n")
    with contextlib.redirect_stdout(io.StringIO()):
        rc = ca.main(["code", "alt", "--op", r["op"]])
    check(rc == 0 and ca.where("alt") == "vault", "CLI `code` reads the code from stdin")
    capture_tests(ca, check, refused, fake_pids)
    secrets = [l for l in open(ca.LOG) if "rt-" in l or "CODE" in l]
    check(not secrets, "log.jsonl holds no tokens or codes")
    print(f"{'ALL PASS' if not FAILS else str(len(FAILS)) + ' FAIL'}  (home {tmp})")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
