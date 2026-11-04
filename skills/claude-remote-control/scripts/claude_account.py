#!/usr/bin/env python3
"""claude-account: choose which Claude subscription account a WHOLE MACHINE uses.

Owner ruling, 2026-10-25 15:57 PDT: one account per machine; a switch closes every
Claude window on the machine, switches, and relaunches the machine's Fleet, no
exceptions. Design: a private design note (section 15 is the
built shape; read it before changing this file).

    claude-account [status] [--json]          this machine: live account, every account's health
    claude-account use <acct> --confirm <machine> [--no-relaunch] [--dry-run] [--json]
                                              stop the Fleet, move <acct>'s login in, relaunch
    claude-account enroll <acct> [--json]     start a browser login for <acct>; prints URL + op id
    claude-account code <acct> --op <id>      finish it: the code is read from STDIN, never argv
    claude-account promote <acct>             apply a staged re-login of the LIVE account (quiescent only)
    claude-account warm [<acct>...] [--json]  keep-alive: refresh dormant logins, verify they advanced
    claude-account capture [--json]           back up the live login into its account's vault (auto-capture)
    claude-account recover                    finish or roll back an interrupted switch (journal)
    claude-account arm --confirm <machine> | disarm
    claude-account fleet-stop | fleet-start   the two halves of a switch, for testing

LAYOUT (ext4 home, 0700 dirs, 0600 files; nothing here is ever in git)
    ~/.claude/.credentials.json + ~/.claude.json   the LIVE login every launcher uses unchanged
    ~/.claude-accounts/<acct>/                     a DORMANT login: a minimal Claude config dir
                                                   (.credentials.json + .claude.json) that is
                                                   warmed in place by `warm`
    ~/.claude-accounts/accounts.tsv                name, email (registry, no secrets)
    ~/.claude-accounts/machine.json                machine name, relaunch argv
    ~/.claude-accounts/DISARMED                    present = `use` refuses (the main desktop ships so)
    ~/.claude-accounts/journal.json                an in-flight switch (see `recover`)
    ~/.claude-accounts/health.json                 last observed token metadata, warm results
    ~/.claude-accounts/live.json                   the live login last seen by capture (name, email, hash)
    ~/.claude-accounts/<acct>/capture.json         where that vault credential came from (no secrets)
A SWITCH moves a login (rename), never copies it: a refresh rotates the refresh token (MEASURED
2026-10-25 on a second desktop), so an old copy can be a dead grant. AUTO-CAPTURE (design section 20)
is the one deliberate copy: the live login is copied into its own account's vault on every status,
warm, page poll, a 2-minute timer and before anything that changes the live credential, so a
`/login` as another account in any window never loses the account it replaced. That copy is a
BACKUP only: switching away moves the live credential itself over it, warm never touches the live
account's copy, and once the live email changes the old copy is marked "may need re-login".
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, ".claude-accounts")
LIVE_DIR = os.path.join(HOME, ".claude")
LIVE_CRED = os.path.join(LIVE_DIR, ".credentials.json")
LIVE_JSON = os.path.join(HOME, ".claude.json")
REGISTRY = os.path.join(ROOT, "accounts.tsv")
MACHINE = os.path.join(ROOT, "machine.json")
DISARMED = os.path.join(ROOT, "DISARMED")
JOURNAL = os.path.join(ROOT, "journal.json")
HEALTH = os.path.join(ROOT, "health.json")
LOG = os.path.join(ROOT, "log.jsonl")
LOCK = os.path.join(ROOT, ".lock")
STAGING = os.path.join(ROOT, ".staging")
TRASH = os.path.join(ROOT, ".trash")

# Variables that would route a launch away from the subscription login, or pick another
# credential store, whatever the files say. Scrubbed from every child we start and
# reported if a launcher or settings file sets them.
BAD_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
           "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
           "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CONFIG_DIR", "CLAUDE_SECURESTORAGE_CONFIG_DIR")
WARN_DAYS = 7
SCOPE_STOP_WAIT = 20


class Refused(Exception):
    """A deliberate refusal: printed, exit 3, nothing changed."""


# ---------------------------------------------------------------- small helpers
def now():
    return time.time()


def iso(ts=None):
    return dt.datetime.fromtimestamp(ts if ts is not None else now()).astimezone().isoformat(timespec="seconds")


def read_json(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json_atomic(path, data, mode=0o600):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def log_event(**kw):
    os.makedirs(ROOT, exist_ok=True)
    kw["ts"] = iso()
    with open(LOG, "a") as fh:
        fh.write(json.dumps(kw) + "\n")


def ensure_root():
    os.makedirs(ROOT, mode=0o700, exist_ok=True)
    os.chmod(ROOT, 0o700)


class MachineLock:
    """One exclusive flock per machine around every mutation (switch, promote, warm, capture).
    wait=True blocks; wait=False fails at once; a number retries for that many seconds."""

    def __init__(self, wait=True):
        self.wait = wait

    def __enter__(self):
        ensure_root()
        self.fh = open(LOCK, "a")
        os.chmod(LOCK, 0o600)
        deadline = now() + (self.wait if not isinstance(self.wait, bool) else 0)
        while True:
            try:
                fcntl.flock(self.fh, fcntl.LOCK_EX | (0 if self.wait is True else fcntl.LOCK_NB))
                return self
            except BlockingIOError:
                if now() >= deadline:
                    self.fh.close()
                    raise Refused("another claude-account operation is running on this machine; try again in a minute")
                time.sleep(0.1)

    def __exit__(self, *a):
        fcntl.flock(self.fh, fcntl.LOCK_UN)
        self.fh.close()


# ---------------------------------------------------------------- registries
def registry():
    """name -> email, from accounts.tsv (comments and blank lines ignored)."""
    out = {}
    try:
        with open(REGISTRY) as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2 and re.fullmatch(r"[a-z][a-z0-9_-]*", parts[0]) and "@" in parts[1]:
                    out[parts[0]] = parts[1].lower()
    except FileNotFoundError:
        pass
    return out


def machine_conf():
    conf = read_json(MACHINE, {}) or {}
    conf.setdefault("machine", os.uname().nodename.lower())
    conf.setdefault("relaunch", [])
    return conf


def account_or_refuse(acct):
    reg = registry()
    if acct not in reg:
        raise Refused(f"unknown account '{acct}'; known: {', '.join(sorted(reg)) or 'none (no accounts.tsv)'}")
    return reg[acct]


# ---------------------------------------------------------------- credentials (metadata only)
def cred_meta(path):
    """Token METADATA of a credentials file; never the tokens themselves."""
    d = read_json(path)
    if not d or "claudeAiOauth" not in d:
        return None
    o = d["claudeAiOauth"]
    rt = o.get("refreshToken") or ""
    rtexp = o.get("refreshTokenExpiresAt")
    return {
        "rt_hash": hashlib.sha256(rt.encode()).hexdigest()[:8] if rt else None,
        "access_expires": (o.get("expiresAt") or 0) / 1000 or None,
        "refresh_expires": rtexp / 1000 if isinstance(rtexp, (int, float)) else None,
        "subscription": o.get("subscriptionType"),
    }


def email_in(json_path):
    d = read_json(json_path, {}) or {}
    return ((d.get("oauthAccount") or {}).get("emailAddress") or "").lower() or None


def vault(acct):
    return os.path.join(ROOT, acct)


def live_account():
    """(name or None, email or None). None name with an email = a login not in the registry."""
    if not os.path.exists(LIVE_CRED):
        return None, None
    email = email_in(LIVE_JSON)
    for n, e in registry().items():
        if e == email:
            return n, email
    return None, email


def where(acct):
    """'live', 'vault' or None: where this account's login currently is on this machine."""
    if live_account()[0] == acct:
        return "live"
    if os.path.exists(os.path.join(vault(acct), ".credentials.json")):
        return "vault"
    return None


def cred_path(acct):
    w = where(acct)
    return LIVE_CRED if w == "live" else os.path.join(vault(acct), ".credentials.json") if w == "vault" else None


# ---------------------------------------------------------------- claude binary and environment
def claude_bin():
    env = os.environ.get("CLAUDE_ACCOUNT_CLAUDE_BIN")
    if env:
        return env
    for p in (os.path.join(HOME, ".local", "bin", "claude"), shutil.which("claude") or ""):
        if p and os.path.exists(p):
            return p
    raise Refused("no claude binary found (~/.local/bin/claude)")


def clean_env(config_dir=None):
    env = {k: v for k, v in os.environ.items() if k not in BAD_ENV}
    lb = os.path.join(HOME, ".local", "bin")
    if lb not in env.get("PATH", "").split(":"):
        env["PATH"] = lb + ":" + env.get("PATH", "/usr/bin:/bin")
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = config_dir
    return env


def auth_status(config_dir=None):
    """`claude auth status` for the live login (config_dir None) or a vault/staging dir."""
    try:
        r = subprocess.run([claude_bin(), "auth", "status"], env=clean_env(config_dir), cwd=HOME,
                           capture_output=True, text=True, timeout=60)
        d = json.loads(r.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return {"loggedIn": False}
    return d


# ---------------------------------------------------------------- effective configuration
def gateway_findings():
    """Anything that would make a launch NOT use the subscription login (GenAI gateway, an
    API key, another config dir). Each finding is a short human string."""
    out = []
    for path in (os.path.join(LIVE_DIR, "settings.json"), os.path.join(LIVE_DIR, "settings.local.json"),
                 "/etc/claude-code/managed-settings.json"):
        d = read_json(path, {}) or {}
        if d.get("apiKeyHelper"):
            out.append(f"{path}: apiKeyHelper is set (gateway/API-key mode)")
        for k in (d.get("env") or {}):
            if k in BAD_ENV:
                out.append(f"{path}: env sets {k}")
    for path in ["/etc/environment", os.path.join(HOME, ".bashrc"), os.path.join(HOME, ".profile"),
                 os.path.join(HOME, ".bash_profile"), os.path.join(HOME, ".zshrc"), os.path.join(HOME, ".zshenv")] + \
            sorted(os.path.join("/etc/profile.d", f) for f in (os.listdir("/etc/profile.d") if os.path.isdir("/etc/profile.d") else [])):
        try:
            with open(path, errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    s = line.split("#", 1)[0]
                    for k in BAD_ENV:
                        if re.search(rf"(^|[\s;]|export\s+){k}=", s):
                            out.append(f"{path}:{i}: sets {k}")
        except OSError:
            continue
    return out


# ---------------------------------------------------------------- processes (the Fleet)
def claude_pids():
    """Every running Claude Code process of this user (native binary under .../claude/versions/
    or named `claude`). WSL only: a Windows-native Claude is invisible to /proc."""
    me = os.getpid()
    uid = os.getuid()
    out = []
    for name in os.listdir("/proc"):
        if not name.isdigit() or int(name) == me:
            continue
        p = f"/proc/{name}"
        try:
            if os.stat(p).st_uid != uid:
                continue
            with open(f"{p}/comm") as fh:
                comm = fh.read().strip()
            exe = os.readlink(f"{p}/exe")
        except OSError:
            continue
        if comm == "claude" or "/claude/versions/" in exe:
            out.append(int(name))
    return sorted(out)


def proc_env(pid):
    try:
        with open(f"/proc/{pid}/environ", "rb") as fh:
            raw = fh.read().split(b"\0")
    except OSError:
        return {}
    env = {}
    for item in raw:
        if b"=" in item:
            k, v = item.split(b"=", 1)
            env[k.decode(errors="replace")] = v.decode(errors="replace")
    return env


def under_claude():
    """True when one of our ancestors is a Claude process."""
    pid, pids = os.getppid(), set(claude_pids())
    while pid > 1:
        if pid in pids:
            return True
        try:
            with open(f"/proc/{pid}/stat") as fh:
                pid = int(fh.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return False
    return False


def fleet_stop(wait=SCOPE_STOP_WAIT):
    """SIGTERM every Claude process, wait, SIGKILL the rest. Returns (stopped, survivors)."""
    pids = claude_pids()
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = now() + wait
    while now() < deadline and claude_pids():
        time.sleep(0.5)
    for pid in claude_pids():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    time.sleep(1)
    return pids, claude_pids()


def fleet_start(conf):
    argv = conf.get("relaunch") or []
    if not argv:
        return "no relaunch configured (machine.json 'relaunch')"
    try:
        r = subprocess.run(argv, env=clean_env(), cwd=HOME, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"relaunch failed: {e}"
    if r.returncode != 0:
        return f"relaunch exited {r.returncode}: {(r.stderr or r.stdout).strip()[-300:]}"
    return None


def verify_relaunch(timeout=90):
    """Wait for Claude processes to appear; report any that carry a routing variable."""
    deadline = now() + timeout
    pids = []
    while now() < deadline:
        pids = claude_pids()
        if pids:
            time.sleep(5)
            pids = claude_pids()
            break
        time.sleep(2)
    bad = []
    for pid in pids:
        env = proc_env(pid)
        for k in BAD_ENV:
            if k in env:
                bad.append(f"pid {pid} has {k}")
    return pids, bad


# ---------------------------------------------------------------- auto-capture (design section 20)
LIVE_SEEN = os.path.join(ROOT, "live.json")


def capture_info(acct):
    return read_json(os.path.join(vault(acct), "capture.json"))


def _set_capture_info(acct, info):
    write_json_atomic(os.path.join(vault(acct), "capture.json"), info)


def _copy_atomic(data, dst):
    """Write bytes to dst atomically, 0600, in a 0700 dir."""
    d = os.path.dirname(dst)
    os.makedirs(d, mode=0o700, exist_ok=True)
    os.chmod(d, 0o700)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, dst)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _capture_locked(reason):
    """Keep a current vault copy of the live login. Caller holds MachineLock. Returns a short
    result dict (hashes and names only). Never runs while a switch journal exists, because the
    live file may then be half of a move."""
    if os.path.exists(JOURNAL):
        return {"result": "skipped-journal"}
    try:
        with open(LIVE_CRED, "rb") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return {"result": "no-live-login"}
    try:
        oauth_cred = json.loads(raw).get("claudeAiOauth") or {}
    except (json.JSONDecodeError, AttributeError):
        return {"result": "skipped-unreadable"}  # Claude may be mid-write; the next poll retries
    rt = oauth_cred.get("refreshToken") or ""
    if not rt:
        return {"result": "skipped-no-refresh-token"}
    live_hash = hashlib.sha256(rt.encode()).hexdigest()[:8]
    acct, email = live_account()
    seen = read_json(LIVE_SEEN, {}) or {}
    out = {"result": "current", "account": acct, "email": email, "rt_hash": live_hash}
    # The live email changed since the last capture (a /login as another account, or a switch):
    # the previous account keeps its last captured copy, marked honestly.
    prev = seen.get("account")
    if prev and prev != acct and prev in registry():
        info = capture_info(prev)
        vmeta = cred_meta(os.path.join(vault(prev), ".credentials.json"))
        if info and info.get("origin") == "capture" and vmeta and vmeta["rt_hash"] == info.get("rt_hash") \
                and not info.get("replaced_by_email_change"):
            last_seen_hash = seen.get("rt_hash")
            if last_seen_hash == info["rt_hash"]:
                note = (f"captured-at {info['captured_at']} (last seen live {seen.get('ts')}); "
                        f"may need re-login if it rotated after that")
            else:
                note = (f"captured-at {info['captured_at']}, but the live login had rotated since "
                        f"(last seen {last_seen_hash}); likely needs re-login")
            info.update(replaced_by_email_change=iso(), live_email_now=email, note=note)
            _set_capture_info(prev, info)
            out["previous"] = {"account": prev, "note": note}
            log_event(op="capture-email-change", frm=prev, to=acct, prev_rt_hash=info["rt_hash"])
    if acct is None:
        out["result"] = "unregistered-email" if email else "no-email"
    else:
        vcred = os.path.join(vault(acct), ".credentials.json")
        vmeta = cred_meta(vcred)
        if not vmeta or vmeta["rt_hash"] != live_hash:
            _copy_atomic(raw, vcred)
            oauth = _oauth_of(LIVE_JSON)
            if oauth:
                _set_oauth_account(os.path.join(vault(acct), ".claude.json"), oauth, minimal=True)
                os.chmod(os.path.join(vault(acct), ".claude.json"), 0o600)
            _set_capture_info(acct, {"origin": "capture", "captured_at": iso(), "rt_hash": live_hash,
                                     "replaced": vmeta and vmeta["rt_hash"], "reason": reason,
                                     "note": "backup of the live login (the live file is authoritative)"})
            out["result"] = "captured"
            log_event(op="capture", acct=acct, rt_hash=live_hash, replaced=vmeta and vmeta["rt_hash"], reason=reason)
    write_json_atomic(LIVE_SEEN, {"account": acct, "email": email, "rt_hash": live_hash, "ts": iso()})
    return out


def capture(reason, wait=2):
    """Capture under the machine lock; a busy lock skips (the next poll or the timer retries)."""
    try:
        with MachineLock(wait=wait):
            return _capture_locked(reason)
    except Refused:
        return {"result": "skipped-busy"}
    except OSError as e:
        return {"result": f"failed: {e.__class__.__name__}"}


# ---------------------------------------------------------------- the switch
def _move(src, dst):
    os.makedirs(os.path.dirname(dst), mode=0o700, exist_ok=True)
    if os.path.exists(dst):
        _trash(dst)
    os.rename(src, dst)


def _trash(path):
    os.makedirs(TRASH, mode=0o700, exist_ok=True)
    dst = os.path.join(TRASH, f"{os.path.basename(os.path.dirname(path))}-{os.path.basename(path)}-{int(now())}")
    os.rename(path, dst)
    return dst


def _set_oauth_account(json_path, oauth, minimal=False):
    d = read_json(json_path, None)
    if d is None:
        d = {"hasCompletedOnboarding": True} if minimal else {}
    d["oauthAccount"] = oauth
    mode = os.stat(json_path).st_mode & 0o777 if os.path.exists(json_path) else 0o600
    write_json_atomic(json_path, d, mode)


def _oauth_of(json_path):
    return (read_json(json_path, {}) or {}).get("oauthAccount")


def move_in(old, new, journal):
    """The only mutation of a switch. Live login -> vault/<old>; vault/<new> -> live."""
    journal["step"] = "moving"
    write_json_atomic(JOURNAL, journal)
    if old and os.path.exists(LIVE_CRED):
        oauth = _oauth_of(LIVE_JSON)
        moved_hash = (cred_meta(LIVE_CRED) or {}).get("rt_hash")
        # the live credential itself goes to the vault; an older captured backup of it is
        # superseded, so it is deleted rather than kept in .trash as one more token copy
        oldv = os.path.join(vault(old), ".credentials.json")
        if os.path.exists(oldv) and (capture_info(old) or {}).get("origin") == "capture":
            os.unlink(oldv)
        _move(LIVE_CRED, os.path.join(vault(old), ".credentials.json"))
        os.chmod(vault(old), 0o700)
        if oauth:
            _set_oauth_account(os.path.join(vault(old), ".claude.json"), oauth, minimal=True)
        _set_capture_info(old, {"origin": "moved", "moved_at": iso(), "rt_hash": moved_hash,
                                "note": "the live credential itself, moved here by a switch"})
    _move(os.path.join(vault(new), ".credentials.json"), LIVE_CRED)
    if os.path.exists(os.path.join(vault(new), "capture.json")):
        os.unlink(os.path.join(vault(new), "capture.json"))
    oauth = _oauth_of(os.path.join(vault(new), ".claude.json"))
    if oauth:
        _set_oauth_account(LIVE_JSON, oauth)
    journal["step"] = "moved"
    write_json_atomic(JOURNAL, journal)


def recover(quiet=False):
    """Finish an interrupted move by locating each grant by its refresh-token hash."""
    j = read_json(JOURNAL)
    if not j:
        if not quiet:
            print("nothing to recover")
        return None
    old, new = j.get("from"), j.get("to")
    if j.get("step") in ("stopping", "checked"):
        os.unlink(JOURNAL)
        return f"journal at '{j.get('step')}': nothing had moved; cleared"
    live = cred_meta(LIVE_CRED)
    newv = os.path.join(vault(new), ".credentials.json")
    oldv = os.path.join(vault(old), ".credentials.json") if old else None
    if live and live["rt_hash"] == j.get("old_hash") and os.path.exists(newv):
        move_in(old, new, j)  # nothing moved yet
    elif not live and os.path.exists(newv):
        _move(newv, LIVE_CRED)  # old moved out, new not in yet
        oauth = _oauth_of(os.path.join(vault(new), ".claude.json"))
        if oauth:
            _set_oauth_account(LIVE_JSON, oauth)
    elif live and live["rt_hash"] == j.get("new_hash"):
        oauth = _oauth_of(os.path.join(vault(new), ".claude.json"))
        if oauth and email_in(LIVE_JSON) != (oauth.get("emailAddress") or "").lower():
            _set_oauth_account(LIVE_JSON, oauth)
    else:
        return f"journal kept: cannot place the grants (live={live and live['rt_hash']}, " \
               f"old vault={'yes' if oldv and os.path.exists(oldv) else 'no'}); read {JOURNAL}"
    if old and (cred_meta(os.path.join(vault(old), ".credentials.json")) or {}).get("rt_hash") == j.get("old_hash"):
        _set_capture_info(old, {"origin": "moved", "moved_at": iso(), "rt_hash": j.get("old_hash"),
                                "note": "the live credential itself, moved here by a recovered switch"})
    if os.path.exists(os.path.join(vault(new), "capture.json")):
        os.unlink(os.path.join(vault(new), "capture.json"))
    os.unlink(JOURNAL)
    log_event(op="recover", frm=old, to=new)
    return f"recovered: live login is now '{new}'"


def cmd_use(acct, confirm, relaunch=True, dry_run=False):
    conf = machine_conf()
    machine = conf["machine"]
    email = account_or_refuse(acct)
    if os.path.exists(DISARMED):
        raise Refused(f"{machine} is DISARMED for switching: {open(DISARMED).read().strip()}")
    if (confirm or "").lower() != machine.lower():
        raise Refused(f"this will close every Claude window on {machine}. Repeat with --confirm {machine}")
    if os.path.exists(JOURNAL):
        raise Refused(f"an earlier switch was interrupted; run `claude-account recover` first")
    gw = gateway_findings()
    if gw:
        raise Refused("this machine is not in subscription mode, a switch would not take effect:\n  " + "\n  ".join(gw))
    old, live_email = live_account()
    if old is None and live_email:
        raise Refused(f"the live login ({live_email}) is not in accounts.tsv; add it before switching away")
    if old == acct:
        return {"ok": True, "machine": machine, "account": acct, "changed": False,
                "message": f"{machine} is already on {acct} ({email}); nothing done"}
    vcred = os.path.join(vault(acct), ".credentials.json")
    meta = cred_meta(vcred)
    stale_note = (capture_info(acct) or {}).get("note") if (capture_info(acct) or {}).get("replaced_by_email_change") else None
    if not meta:
        raise Refused(f"{acct} is not enrolled on {machine}; run: claude-account enroll {acct}")
    if meta["refresh_expires"] and meta["refresh_expires"] < now():
        raise Refused(f"{acct}'s saved login expired on {iso(meta['refresh_expires'])[:10]} (last observed); re-enroll it")
    vemail = email_in(os.path.join(vault(acct), ".claude.json"))
    if vemail and vemail != email:
        raise Refused(f"vault '{acct}' holds {vemail}, registry says {email}; refusing")
    if under_claude():
        raise Refused("run this from a terminal, ssh or the page, not from inside a Claude session: "
                      "the switch stops every Claude process, including the one that would be running it")
    if dry_run:
        return {"ok": True, "dry_run": True, "machine": machine, "from": old, "to": acct,
                "would_stop": claude_pids(), "relaunch": conf.get("relaunch")}
    with MachineLock(wait=5):
        _capture_locked("before-use")
        journal = {"op": "use", "from": old, "to": acct, "started": iso(), "step": "stopping",
                   "old_hash": (cred_meta(LIVE_CRED) or {}).get("rt_hash"), "new_hash": meta["rt_hash"]}
        write_json_atomic(JOURNAL, journal)
        stopped, survivors = fleet_stop()
        if survivors:
            os.unlink(JOURNAL)
            err = fleet_start(conf) if relaunch else None
            raise Refused(f"could not stop Claude pids {survivors}; nothing switched"
                          + (f"; old Fleet relaunch: {err or 'ok'}" if relaunch else ""))
        journal["step"] = "checked"
        write_json_atomic(JOURNAL, journal)
        try:
            move_in(old, acct, journal)
        except OSError as e:
            msg = recover(quiet=True)
            raise Refused(f"move failed ({e}); recovery: {msg}")
        st = auth_status()
        got = (st.get("email") or "").lower()
        if not st.get("loggedIn") or got != email:
            # roll back: put the grants where they were, so credentials are never lost
            back = {"op": "rollback", "from": acct, "to": old, "step": "checked",
                    "old_hash": meta["rt_hash"], "new_hash": journal["old_hash"]}
            if old:
                move_in(acct, old, back)
            else:
                _move(LIVE_CRED, os.path.join(vault(acct), ".credentials.json"))
            os.unlink(JOURNAL)
            err = fleet_start(conf) if relaunch else None
            raise Refused(f"after the move `claude auth status` said loggedIn={st.get('loggedIn')} email={got or '?'}; "
                          f"rolled back to {old}" + (f"; relaunch: {err or 'ok'}" if relaunch else ""))
        os.unlink(JOURNAL)
        result = {"ok": True, "machine": machine, "from": old, "to": acct, "changed": True,
                  "stopped": len(stopped), "email": got}
        _capture_locked("after-use")
        if relaunch:
            err = fleet_start(conf)
            result["relaunch"] = err or "started"
            if not err:
                pids, bad = verify_relaunch()
                result["fleet_pids"] = len(pids)
                result["fleet_env_problems"] = bad
        log_event(op="use", **{k: v for k, v in result.items() if k != "ok"})
    result["message"] = (f"{machine} now on {acct} ({got}); stopped {result['stopped']} Claude process(es)"
                         + (f"; Fleet relaunch: {result.get('relaunch')}, {result.get('fleet_pids', 0)} running" if relaunch else "; Fleet NOT relaunched")
                         + (f". NOTE {acct}'s login was an automatic capture ({stale_note}); if Claude asks to log in, "
                            f"use the page's Log in for {acct}" if stale_note else ""))
    return result


# ---------------------------------------------------------------- enrollment
URL_RE = re.compile(r"https://\S+")


def _tmux(*args, **kw):
    return subprocess.run(["tmux", *args], capture_output=True, text=True, **kw)


def cmd_enroll(acct):
    email = account_or_refuse(acct)
    ensure_root()
    os.makedirs(STAGING, mode=0o700, exist_ok=True)
    for stale in os.listdir(STAGING):  # a new enrollment abandons any earlier one for this account
        if stale.startswith(f"{acct}-"):
            shutil.rmtree(os.path.join(STAGING, stale), ignore_errors=True)
    op = hashlib.sha256(os.urandom(16)).hexdigest()[:10]
    sdir = os.path.join(STAGING, f"{acct}-{op}")
    os.makedirs(sdir, mode=0o700)
    write_json_atomic(os.path.join(sdir, ".enroll.json"), {"acct": acct, "email": email, "op": op, "started": iso()})
    sess = f"claude-enroll-{acct}"
    _tmux("kill-session", "-t", sess)
    inner = f"CLAUDE_CONFIG_DIR='{sdir}' '{claude_bin()}' auth login --claudeai --email '{email}'; echo LOGIN_EXITED; sleep 900"
    env = clean_env()
    # Never pop a browser on the target machine's desktop: the owner opens the URL on his own device.
    env["BROWSER"] = "true"
    r = subprocess.run(["tmux", "new-session", "-d", "-s", sess, "-x", "500", "-y", "50", inner],
                       env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise Refused(f"could not start the login session: {r.stderr.strip()}")
    url = None
    for _ in range(40):
        pane = _tmux("capture-pane", "-p", "-J", "-t", sess).stdout
        m = URL_RE.search(pane)
        if m:
            url = m.group(0)
            break
        time.sleep(1)
    if not url:
        _tmux("kill-session", "-t", sess)
        shutil.rmtree(sdir, ignore_errors=True)
        raise Refused("no login URL appeared within 40 s")
    log_event(op="enroll", acct=acct, opid=op)
    return {"ok": True, "account": acct, "email": email, "op": op, "url": url,
            "message": f"open the URL in a browser signed in to {email}, then send the code with: "
                       f"claude-account code {acct} --op {op}   (code on stdin)"}


def _staging_for(acct, op):
    sdir = os.path.join(STAGING, f"{acct}-{op}")
    meta = read_json(os.path.join(sdir, ".enroll.json"))
    if not meta or meta.get("acct") != acct:
        raise Refused(f"no enrollment {op} in progress for {acct}; start one with: claude-account enroll {acct}")
    return sdir, meta


def cmd_code(acct, op, code):
    email = account_or_refuse(acct)
    sdir, meta = _staging_for(acct, op)
    code = (code or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9#_\-.~]{8,512}", code):
        raise Refused("that does not look like a login code")
    sess = f"claude-enroll-{acct}"
    if _tmux("has-session", "-t", sess).returncode != 0:
        raise Refused(f"the login session for {acct} has ended; start again with: claude-account enroll {acct}")
    # The code travels through tmux's buffer from our stdin, never through an argv.
    subprocess.run(["tmux", "load-buffer", "-b", f"code-{op}", "-"], input=code, text=True, check=True)
    _tmux("paste-buffer", "-d", "-b", f"code-{op}", "-t", sess)
    _tmux("send-keys", "-t", sess, "Enter")
    st = {}
    for _ in range(45):
        st = auth_status(sdir)
        if st.get("loggedIn"):
            break
        time.sleep(1)
    if not st.get("loggedIn"):
        pane = _tmux("capture-pane", "-p", "-t", sess).stdout.strip()
        tail = [ln for ln in pane.splitlines() if "login_hint" not in ln and "http" not in ln][-3:]
        if "LOGIN_EXITED" in pane:  # the login process gave up: this enrollment is over, clean it away
            _tmux("kill-session", "-t", sess)
            shutil.rmtree(sdir, ignore_errors=True)
            raise Refused("login failed, enrollment closed (start again with: claude-account enroll "
                          f"{acct}): " + " | ".join(tail))
        raise Refused("not logged in yet: " + " | ".join(tail))
    _tmux("kill-session", "-t", sess)
    got = (st.get("email") or email_in(os.path.join(sdir, ".claude.json")) or "").lower()
    if got != email:
        shutil.rmtree(sdir, ignore_errors=True)
        raise Refused(f"the browser logged in as {got or '?'}, not {email}; discarded. Sign that browser in to {email} and enroll again")
    os.unlink(os.path.join(sdir, ".enroll.json"))
    return promote(acct, sdir)


def promote(acct, sdir=None):
    """Move a verified staged login into place. A dormant account: replaces its vault (the old
    one goes to .trash). The live account: only while no Claude process runs."""
    if sdir is None:
        cands = sorted(d for d in os.listdir(STAGING) if d.startswith(acct + "-")) if os.path.isdir(STAGING) else []
        cands = [os.path.join(STAGING, d) for d in cands if os.path.exists(os.path.join(STAGING, d, ".credentials.json"))
                 and not os.path.exists(os.path.join(STAGING, d, ".enroll.json"))]
        if not cands:
            raise Refused(f"no verified staged login for {acct}")
        sdir = cands[-1]
    with MachineLock():
        _capture_locked("before-promote")
        if where(acct) == "live":
            if claude_pids():
                return {"ok": True, "account": acct, "staged": sdir, "message":
                        f"{acct} logged in and verified, but it is the LIVE account and Claude is running; "
                        f"it is staged. Apply it with `claude-account promote {acct}` when the Fleet is closed"}
            _trash(LIVE_CRED)
            _move(os.path.join(sdir, ".credentials.json"), LIVE_CRED)
            oauth = _oauth_of(os.path.join(sdir, ".claude.json"))
            if oauth:
                _set_oauth_account(LIVE_JSON, oauth)
            shutil.rmtree(sdir, ignore_errors=True)
            _capture_locked("after-promote")
            msg = f"{acct} re-logged in and is live"
        else:
            if os.path.isdir(vault(acct)):
                os.makedirs(TRASH, mode=0o700, exist_ok=True)
                os.rename(vault(acct), os.path.join(TRASH, f"{acct}-vault-{int(now())}"))
            os.rename(sdir, vault(acct))
            os.chmod(vault(acct), 0o700)
            msg = f"{acct} enrolled on {machine_conf()['machine']} (dormant until you switch to it)"
    log_event(op="promote", acct=acct)
    return {"ok": True, "account": acct, "message": msg}


# ---------------------------------------------------------------- keep-alive
WARM_ARGS = ["-p", "Reply with the single word OK.", "--model", "sonnet", "--setting-sources", "project",
             "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"]


def classify(text):
    t = text.lower()
    if any(s in t for s in ("invalid_grant", "oauth token has expired", "/login", "not logged in",
                            "authentication_error", "401", "invalid api key", "revoked")):
        return "auth"
    if any(s in t for s in ("rate limit", "usage limit", "429", "overloaded", "limit reached")):
        return "rate-limit"
    if any(s in t for s in ("enotfound", "econnrefused", "econnreset", "etimedout", "network", "fetch failed")):
        return "network"
    if any(s in t for s in ("model", "not_found")):
        return "model"
    return "other"


def warm_one(acct, health):
    w = where(acct)
    rec = health.setdefault(acct, {})
    if not w:
        rec["warm"] = {"ts": iso(), "result": "not-enrolled"}
        return rec["warm"]
    path = cred_path(acct)
    before = cred_meta(path)
    if w == "live" and claude_pids():
        result = "observed"  # the Fleet uses it; warming would race its own refresh
        if before and rec.get("observed", {}).get("rt_hash") not in (None, before["rt_hash"]):
            rec["renewed"] = iso()
            result = "renewed-by-use"
        rec["observed"] = dict(before or {}, ts=iso())
        rec["warm"] = {"ts": iso(), "result": result}
        return rec["warm"]
    cwd = tempfile.mkdtemp(prefix="claude-warm-")
    try:
        r = subprocess.run([claude_bin(), *WARM_ARGS], env=clean_env(vault(acct) if w == "vault" else None),
                           cwd=cwd, capture_output=True, text=True, timeout=180)
        out, rc = (r.stdout + "\n" + r.stderr), r.returncode
    except subprocess.TimeoutExpired:
        out, rc = "timeout", 124
    finally:
        shutil.rmtree(cwd, ignore_errors=True)
    after = cred_meta(path) or {}
    advanced = bool(before and after and (after.get("rt_hash") != before.get("rt_hash")
                                          or (after.get("access_expires") or 0) > (before.get("access_expires") or 0)))
    if rc == 0 and advanced:
        result = "renewed"
        rec["renewed"] = iso()
        info = capture_info(acct) if w == "vault" else None
        if info and info.get("replaced_by_email_change"):  # a refresh proved the captured copy is a live grant
            info.pop("replaced_by_email_change")
            info["note"] = f"captured-at {info.get('captured_at')}, proven by warm {iso()}"
            _set_capture_info(acct, info)
    elif rc == 0 and before and (before.get("access_expires") or 0) > now() + 60:
        result = "ok-not-due"  # the access token was still valid, so no refresh was needed or proven
    elif rc == 0:
        result = "ok-unproven"
    else:
        result = "failed-" + classify(out)
    rec["observed"] = dict(after, ts=iso())
    rec["warm"] = {"ts": iso(), "result": result,
                   "refresh_expires_before": before and before.get("refresh_expires"),
                   "refresh_expires_after": after.get("refresh_expires"),
                   "rotated": bool(before and after.get("rt_hash") != before.get("rt_hash"))}
    if result.startswith("failed"):
        rec["warm"]["detail"] = out.strip()[-200:]
    return rec["warm"]


def cmd_warm(accts):
    reg = registry()
    accts = accts or sorted(reg)
    with MachineLock():
        cap = _capture_locked("warm")
        health = read_json(HEALTH, {}) or {}
        res = {}
        for a in accts:
            account_or_refuse(a)
            res[a] = warm_one(a, health)
        write_json_atomic(HEALTH, health)
    log_event(op="warm", results={a: r["result"] for a, r in res.items()})
    return {"ok": all(not r["result"].startswith("failed") for r in res.values()), "results": res, "capture": cap}


# ---------------------------------------------------------------- status
def days(ts):
    return None if ts is None else round((ts - now()) / 86400, 1)


def cmd_status(do_capture=True):
    cap = capture("status") if do_capture else None
    conf = machine_conf()
    reg = registry()
    live, live_email = live_account()
    health = read_json(HEALTH, {}) or {}
    accts = []
    for a, e in sorted(reg.items()):
        w = where(a)
        meta = cred_meta(cred_path(a)) if w else None
        h = health.get(a, {})
        state = "not enrolled"
        if meta:
            dl = days(meta["refresh_expires"])
            state = "expired" if dl is not None and dl <= 0 else "ok" if dl is None or dl >= WARN_DAYS else "expiring"
        info = capture_info(a) or {}
        vault_note = info.get("note") if w == "vault" and info.get("replaced_by_email_change") else None
        if w == "live":
            vmeta = cred_meta(os.path.join(vault(a), ".credentials.json"))
            vault_note = ("backed up " + str(info.get("captured_at") or "?") if vmeta and meta and vmeta["rt_hash"] == meta["rt_hash"]
                          else "NOT backed up yet")
        accts.append({"name": a, "email": e, "where": w or "none", "state": state, "vault_note": vault_note,
                      "refresh_days_left": days(meta["refresh_expires"]) if meta else None,
                      "last_renewed": h.get("renewed"), "last_warm": h.get("warm"),
                      "staged": any(d.startswith(a + "-") for d in os.listdir(STAGING)) if os.path.isdir(STAGING) else False})
    pids = claude_pids()
    return {"ok": True, "machine": conf["machine"], "live": live, "live_email": live_email,
            "armed": not os.path.exists(DISARMED), "disarmed_note": open(DISARMED).read().strip() if os.path.exists(DISARMED) else None,
            "interrupted_switch": os.path.exists(JOURNAL), "claude_processes": len(pids),
            "subscription_mode_problems": gateway_findings(), "accounts": accts, "capture": cap,
            "note": "days left and health are LAST OBSERVED from the credential files; a failed warm is the real signal"}


def print_status(s):
    print(f"{s['machine']}: live account {s['live'] or '?'} ({s['live_email'] or 'no login'}), "
          f"{s['claude_processes']} Claude process(es), {'ARMED' if s['armed'] else 'DISARMED'}")
    if s["interrupted_switch"]:
        print("  !! an interrupted switch: run `claude-account recover`")
    for p in s["subscription_mode_problems"]:
        print(f"  !! not subscription mode: {p}")
    for a in s["accounts"]:
        mark = "*" if a["where"] == "live" else " "
        dl = "" if a["refresh_days_left"] is None else f"{a['refresh_days_left']}d left"
        lw = a["last_warm"]["result"] if a["last_warm"] else "never warmed"
        print(f" {mark} {a['name']:8} {a['email']:32} {a['state']:12} {dl:10} {lw}{'  (re-login staged)' if a['staged'] else ''}")
        if a.get("vault_note"):
            print(f"     {'':8} vault: {a['vault_note']}")
    cap = s.get("capture") or {}
    if cap.get("previous"):
        print(f"  live login changed: {cap['previous']['account']} kept its last capture ({cap['previous']['note']})")
    if cap.get("result") == "unregistered-email":
        print(f"  !! the live login {cap.get('email')} is not in accounts.tsv, so it is not backed up")


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(prog="claude-account", description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("status")
    u = sub.add_parser("use")
    u.add_argument("acct")
    u.add_argument("--confirm", default="")
    u.add_argument("--no-relaunch", action="store_true")
    u.add_argument("--dry-run", action="store_true")
    e = sub.add_parser("enroll")
    e.add_argument("acct")
    c = sub.add_parser("code")
    c.add_argument("acct")
    c.add_argument("--op", required=True)
    pr = sub.add_parser("promote")
    pr.add_argument("acct")
    w = sub.add_parser("warm")
    w.add_argument("accts", nargs="*")
    sub.add_parser("recover")
    sub.add_parser("capture")
    a = sub.add_parser("arm")
    a.add_argument("--confirm", default="")
    sub.add_parser("disarm")
    sub.add_parser("fleet-stop")
    sub.add_parser("fleet-start")
    for p in sub.choices.values():
        p.add_argument("--json", action="store_true", dest="json_sub")
    args = ap.parse_args(argv)
    as_json = args.json or getattr(args, "json_sub", False)
    try:
        cmd = args.cmd or "status"
        if cmd == "status":
            res = cmd_status()
            if not as_json:
                print_status(res)
                return 0
        elif cmd == "use":
            res = cmd_use(args.acct, args.confirm, relaunch=not args.no_relaunch, dry_run=args.dry_run)
        elif cmd == "enroll":
            res = cmd_enroll(args.acct)
            if not as_json:
                print(f"Open in a browser signed in to {res['email']}:\n{res['url']}\nThen: "
                      f"claude-account code {args.acct} --op {res['op']}   and paste the code (stdin)")
                return 0
        elif cmd == "code":
            code = sys.stdin.readline() if not sys.stdin.isatty() else __import__("getpass").getpass("code: ")
            res = cmd_code(args.acct, args.op, code)
        elif cmd == "promote":
            res = promote(args.acct)
        elif cmd == "warm":
            res = cmd_warm(args.accts)
            if not as_json:
                for k, v in res["results"].items():
                    print(f"{k:8} {v['result']}")
                return 0 if res["ok"] else 1
        elif cmd == "capture":
            cap = capture("timer", wait=10)
            res = dict(cap, ok=not cap["result"].startswith("failed"),
                       message=f"capture: {cap['result']}" + (f" {cap.get('account')} {cap.get('rt_hash')}" if cap.get("account") else ""))
        elif cmd == "recover":
            with MachineLock():
                res = {"ok": True, "message": recover()}
        elif cmd == "arm":
            m = machine_conf()["machine"]
            if args.confirm.lower() != m.lower():
                raise Refused(f"arming lets a switch close every Claude window on {m}. Repeat with --confirm {m}")
            if os.path.exists(DISARMED):
                os.unlink(DISARMED)
            with open(os.path.join(ROOT, "ARMED_BY_OWNER"), "w") as fh:  # install.sh will not re-disarm
                fh.write(f"armed {iso()}\n")
            log_event(op="arm")
            res = {"ok": True, "message": f"{m} ARMED: `claude-account use <acct> --confirm {m}` will now switch it"}
        elif cmd == "disarm":
            ensure_root()
            with open(DISARMED, "w") as fh:
                fh.write(f"disarmed {iso()}; arm with: claude-account arm --confirm {machine_conf()['machine']}\n")
            if os.path.exists(os.path.join(ROOT, "ARMED_BY_OWNER")):
                os.unlink(os.path.join(ROOT, "ARMED_BY_OWNER"))
            res = {"ok": True, "message": "disarmed"}
        elif cmd in ("fleet-stop", "fleet-start") and (os.path.exists(DISARMED) or under_claude()):
            raise Refused("refused: this machine is DISARMED or this runs inside a Claude session")
        elif cmd == "fleet-stop":
            stopped, surv = fleet_stop()
            res = {"ok": not surv, "stopped": stopped, "survivors": surv, "message": f"stopped {len(stopped)}, survivors {surv}"}
        elif cmd == "fleet-start":
            err = fleet_start(machine_conf())
            res = {"ok": err is None, "message": err or "Fleet started"}
    except Refused as ex:
        if as_json:
            print(json.dumps({"ok": False, "refused": str(ex)}))
        else:
            print(f"claude-account: {ex}", file=sys.stderr)
        return 3
    if as_json:
        print(json.dumps(res, indent=2))
    else:
        print(res.get("message") or json.dumps(res, indent=2))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
