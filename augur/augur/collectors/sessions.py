"""Per-agent collectors (DESIGN.md sections 3 "Per agent" and 5): sessions, attention, session_net.

sessions     (agents, 5 s)  roots from ~/.claude/sessions/*.json, trees by proc_listchildpids
                            (full own-uid sweep only when that dir is unlistable) -> "sessions"
attention    (fast, 2 s)    SidePulse state.json, else ~/.claude/sessions/<pid>.json status
                            -> path "sessions.attention"
session_net  (agents, 5 s)  one nettop exec over every session-tree pid -> path "sessions.net"

Decisions (the ticket left these open):
- A root (pidpath contains /claude/versions/) is a session only when ~/.claude/sessions/<pid>.json
  exists and its procStart is within +-2 s of the process start (hostrec.read_sessions semantics:
  a file with no parseable procStart is accepted). A root with no file (a nested helper) is not a
  session; its processes fold into the enclosing session's tree. If the sessions directory itself
  cannot be listed, every root counts (an empty list would be a false zero).
- Headless runs (1.2). `claude -p` DOES write a session file (2.1.292: kind interactive,
  entrypoint sdk-cli), so it is a root like any other. A root is headless when its file says
  entrypoint "sdk-cli" (a file naming another entrypoint is believed) or, with no entrypoint in
  the file, its argv carries -p / --print. A headless root is ATTRIBUTED to the
  nearest non-headless session root up its ppid chain (a -p under a -p resolves to the top
  interactive session): it is published with "headless": true, "parent": <that sid>, and the
  parent's project / project_key / managed. A headless root with no session ancestor (cron,
  launchd) carries "headless": true and no parent, identified from its own cwd as before. The
  ppid chain is primary. A run reparented off it (double fork, nohup) falls back to the inherited
  CLAUDE_CODE_MESSAGING_SOCKET=/tmp/cc-socks/<pid>.sock (the KERN_PROCARGS2 env block, read once
  per pid@start) when that pid is a live non-headless root. Only the pid is kept, never the value.
- CPU is never double-counted: walk() stops at every root, headless ones included, so a parent's
  load covers its own tree WITHOUT its headless children, and each child carries its own load.
  A consumer that wants the family's weight sums the parent's and its children's cpu_cores. When
  a child exits, the reap lands on the parent's tree and is cancelled by the gone-credit like any
  nested session's.
- No cwd readable, or no git toplevel and no registry row -> project "unknown" (S4: a bare folder
  name is never published).
- load: the session's first tick is {"unknown": "warming_up"}; later ticks carry all keys, with
  "provisional": True (the starved threshold is a proposal). cpu_cores over the tree = d(own) +
  d(reaped-children CPU, rusage_info_v4 child times) of pids seen in both sweeps, + all own+child
  CPU of pids born this interval. A tree pid that is gone leaves a credit (its last-seen own+child
  CPU) on the live process that will reap it. A reap adds the child's whole final total in one
  step, so the credit is used only on a child-time rise at least that large; smaller rises are
  other children and count. A nested session's credit also removes its own last interval, bounded
  by its last rate. A credit unmatched for CREDIT_MAX_AGE_S is retired (RB-m8; R1 1, 4; R2 1, 2). A pid reparented out of
  the tree (nohup, double fork) stays the session's while it lives (finding 2); what launchd
  reaps is lost, never subtracted. Root rusage failed, or more than half the tree's: load
  {"unknown": "read_failed"}; a counter going backwards: "counter_reset"; a tree that reaches
  TREE_LIMIT: "truncated" (findings 3, 12, 14). wait_s_per_s has no child term (none exists).
- A failed pidpath is retried next sweep, never cached as "not Claude" (finding 13).
- tasks.subagents: a subagent transcript (any spawnDepth) counts while its last complete line is
  not a terminal assistant line (end_turn or an API error) and it was written within 24 h; a
  mid-stream assistant line older than 5 min means it was cut off. Only the last 8 KB is read.
  (Owner bug 2026-11-01: the old 30 s mtime window dropped agents blocked on long tool calls.)
- tasks: sessionId comes from SidePulse's slot for the pid; without one, the newest top-level
  <slug>/*.jsonl modified at or after the session start (can mis-pick when two sessions share a
  project). No transcript directory at all -> tasks {"unknown": "read_failed"}. Always provisional.
- attention: slot first (a slot older than the process start is a previous owner of the pid and is
  ignored), then the session file's "status". Neither present -> the session is left out (absent:
  this Claude version writes no status). state.json present but unreadable and no fallback ->
  {"unknown": "read_failed"} for that session.
- session_net: nettop refuses more than 20 -p pids (exit 64, measured), so above 20 pids one
  unfiltered nettop runs and rows are filtered by pid. A flow is keyed by its proto + 4-tuple
  globally and credited to the first process row it appears under (never double-counted). The
  collector's first tick, and a session's first tick, read {"unknown": "warming_up"}.
Nothing here writes a path, command line or address into a value.
"""
import json
import os
import re
import socket
import subprocess
import time

try:
    from augur.collectors.base import Collector
except ImportError:  # pragma: no cover
    from .base import Collector

CLAUDE_MARK = "/claude/versions/"
# Measured on the Work Desktop 2026-11-05: an npm-installed CLI has no versions/ directory at all,
# its proc_pidpath is .../node_modules/@anthropic-ai/claude-code/bin/claude.exe, so CLAUDE_MARK alone
# found zero roots and every session went missing (sessions: [], so Sprites drew nothing).
CLAUDE_NPM_MARK = "/@anthropic-ai/claude-code/"


def is_claude_path(pp):
    """True when this executable path is a Claude CLI: either the versions/ layout or an npm install."""
    return CLAUDE_MARK in pp or CLAUDE_NPM_MARK in pp


SHELL_COMMS = ("zsh", "bash", "sh")
SHELL_PREFIX = "/bin/zsh -c source "
SHELL_MARK = "/.claude/shell-snapshots/"
STARVED_WAIT = 0.5
SUBAGENT_MAX_AGE_S = 24 * 3600.0   # a subagent file untouched this long is not running
STREAM_STALE_S = 300.0             # a mid-stream assistant line this old: the agent was cut off
SUBAGENT_TAIL = 8192
SUBAGENT_TAIL_MAX = 1 << 20   # R5-6: a resume line longer than the tail is looked for up to this
BG_YOUNG_S = 60.0         # a tool shell whose stdout cannot be read counts as background past this
FG_MAX_S = 660.0          # a foreground Bash call is moved to the background at 600 s
SOCK_RE = re.compile(r"/cc-socks/([0-9]+)\.sock$")
TASK_OUT_RE = re.compile(r"/tasks/([A-Za-z0-9]+)\.output$")
NOTICE_TEXT_RE = re.compile(r"^\s*<task-notification>\s*<task-id>(a[0-9a-f]+)</task-id>")
NOTICE_HINT = b"task-notification"
SCAN_CHUNK = 1 << 20
SCAN_BUDGET = 8 << 20     # RB-m7: transcript bytes scanned per collect; the rest waits a tick
WALL_STEP_S = 10.0        # |d(wall) - d(mono)| above this is a wall-clock step (RB-m5)
RESUME_SLACK_S = 2.0      # an agent file written this long after its notice was resumed


def notice_ids(line):
    """((agent id, epoch or None),) when this transcript line IS a completion notice, else ().
    Only the harness's own notification entries count, parsed as JSON (never a substring of a
    tool_use input, a tool_result, or a message quoting the block: the 09:45 false positive): a
    queue-operation enqueue, a user line with origin.kind task-notification, an attachment with
    commandMode task-notification. The block must START the field's text. Any unexpected shape
    reads as no notice (R4-2: it must never raise). A notice with no timestamp has epoch None."""
    if NOTICE_HINT not in line:
        return ()
    try:
        d = json.loads(line)
        if not isinstance(d, dict):
            return ()
        t, txt, ts = d.get("type"), None, d.get("timestamp")
        att = d.get("attachment") if isinstance(d.get("attachment"), dict) else {}
        origin = d.get("origin") if isinstance(d.get("origin"), dict) else {}
        msg = d.get("message") if isinstance(d.get("message"), dict) else {}
        if t == "queue-operation" and d.get("operation") == "enqueue":
            txt = d.get("content")
        elif t == "user" and origin.get("kind") == "task-notification":
            txt = msg.get("content")
        elif t == "attachment" and att.get("commandMode") == "task-notification":
            txt, ts = att.get("prompt"), ts or att.get("timestamp")
        m = NOTICE_TEXT_RE.match(txt) if isinstance(txt, str) else None
        if not m:
            return ()
        return ((m.group(1), _iso_epoch(ts)),)
    except Exception:  # noqa: BLE001 - a malformed line is no evidence, never a crash
        return ()


def _iso_epoch(ts):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def open_regular(path):
    """A binary file object for a REGULAR file only (S1): O_NONBLOCK so a FIFO never blocks the
    scheduler thread, O_NOFOLLOW so a symlink to one is refused, then S_ISREG on the open fd.
    Anything else raises OSError."""
    import stat as _stat
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    try:
        if not _stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(22, "not a regular file")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def _last_line_epoch(path, size):
    """The newest `timestamp` among the complete lines in the file's last SUBAGENT_TAIL bytes, or
    None (R4-9: a resume is a written line, not an mtime). R5-6: when the tail holds no complete
    timestamped line (one long last line), the window grows up to SUBAGENT_TAIL_MAX before None,
    and None means unmeasured, never "ended"."""
    win = SUBAGENT_TAIL
    with open_regular(path) as fh:
        while True:
            lo = max(0, size - win)
            fh.seek(lo)
            data = fh.read(size - lo)
            lines = data.split(b"\n")
            if lo > 0:
                lines = lines[1:]           # the first piece is a cut line
            best = None
            for raw in lines:
                if raw.find(b'"timestamp"') < 0:
                    continue
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                t = _iso_epoch(d.get("timestamp")) if isinstance(d, dict) else None
                if t is not None and (best is None or t > best):
                    best = t
            if best is not None or lo == 0 or win >= SUBAGENT_TAIL_MAX:
                return best
            win *= 8


BG_ANNOUNCE_RE = re.compile(rb"background with ID: ([A-Za-z0-9]+)|moved to the background \(ID: ([A-Za-z0-9]+)\)")
STOPPED_WINDOW_S = 600.0
NETTOP = "/usr/bin/nettop"
NETTOP_MAX_PIDS = 20
NETTOP_TIMEOUT_S = 3.0
TREE_LIMIT = 200          # native.tree cap; a tree that reaches it reads unknown "truncated"
CREDIT_MAX_AGE_S = 3600.0  # RB-m8: an unmatched credit is retired after this much mono time
CREDIT_EPS_S = 0.02       # rusage tick rounding allowed when matching a reap to a credit
KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


# --------------------------------------------------------------------------- readers

class Readers(object):
    """Default readers: libproc via augur.darwin.native (imported lazily) and a nettop exec.
    Tests pass an object with the same method names."""

    def _n(self):
        from augur.darwin import native
        return native

    def all_pids(self):
        return self._n().all_pids()

    def bsdinfo(self, pid):
        return self._n().bsdinfo(pid)

    def rusage(self, pid):
        """(cpu_s, runnable_s, fp, disk, child_cpu_s); child_cpu_s = reaped children's CPU."""
        return self._n().rusage_children(pid)

    def pidpath(self, pid):
        return self._n().pidpath(pid)

    def cmdline(self, pid):
        return self._n().cmdline(pid)

    def cwd(self, pid):
        return self._n().cwd(pid)

    def environ_value(self, pid, name):
        return self._n().environ_value(pid, name)

    def stdout_path(self, pid):
        return self._n().stdout_path(pid)

    def tree(self, pid, limit=None):
        return self._n().tree(pid, limit or TREE_LIMIT)

    def uid(self):
        return os.getuid()

    def nettop(self, pids, timeout=NETTOP_TIMEOUT_S):
        """(returncode, stdout). Raises subprocess.TimeoutExpired / OSError."""
        args = [NETTOP, "-L", "1", "-n", "-x", "-J", "bytes_in,bytes_out,re-tx"]
        if len(pids) <= NETTOP_MAX_PIDS:
            for p in pids:
                args += ["-p", str(p)]
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout


# --------------------------------------------------------------------------- small pure helpers

def proc_start_epoch(s):
    """Claude's session-file procStart ('Sun Nov  1 05:58:07 2026', UTC) as an epoch.
    # from Lodestar hostrec._proc_start_epoch"""
    import calendar
    try:
        return float(calendar.timegm(time.strptime(" ".join(str(s).split()), "%a %b %d %H:%M:%S %Y")))
    except (TypeError, ValueError):
        return None


def sanitize_key(name):
    k = re.sub(r"[^a-z0-9._-]+", "-", (name or "").lower())
    k = re.sub(r"^[^a-z0-9]+", "", k)
    return k if KEY_RE.match(k) else "unknown"


def transcript_slug(cwd):
    """~/.claude/projects/<slug>: every character outside [A-Za-z0-9-] becomes '-' (verified
    against ls ~/.claude/projects: Orchard_Mandrake -> Orchard-Mandrake)."""
    return re.sub(r"[^A-Za-z0-9-]", "-", cwd)


def git_toplevel(path, isdir=os.path.isdir, exists=os.path.exists):
    """Nearest ancestor holding .git (dir or worktree file), no spawn. None when there is none."""
    p = os.path.abspath(path)
    while True:
        if exists(os.path.join(p, ".git")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


def _real(p):
    try:
        return os.path.realpath(os.path.expanduser(p))
    except (OSError, ValueError):
        return p


# --------------------------------------------------------------------------- vendored md table

# from Lodestar mdtable (parse / tables / _cells / _is_row / _is_separator), reduced
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def _is_row(line):
    return line.strip().startswith("|")


def _is_separator(line):
    s = line.strip()
    return s.startswith("|") and set(s) <= set("|-: \t") and "-" in s


def _cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in _UNESCAPED_PIPE.split(s)]


def md_tables(text):
    """[(headers, rows)] for every markdown table, headers lowercased."""
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines) - 1:
        if _is_row(lines[i]) and _is_separator(lines[i + 1]):
            headers = [c.lower() for c in _cells(lines[i])]
            rows = []
            j = i + 2
            while j < len(lines) and _is_row(lines[j]):
                cells = _cells(lines[j])
                if any(cells):
                    rows.append({h: (cells[k] if k < len(cells) else "") for k, h in enumerate(headers)})
                j += 1
            out.append((headers, rows))
            i = j
            continue
        i += 1
    return out


def _clean(v):
    return (v or "").strip().strip("`").strip()


def _split_machines(value):
    v = _clean(value).lower()
    if not v or v in ("all", "*", "-", "—"):
        return ()
    return tuple(x for x in re.split(r"[,\s]+", v) if x)


def parse_registry(text, role, key):
    """{realpath: (name, id)} of ACTIVE rows carried by this machine. Raises ValueError when
    the document has no table with name and path columns (unparseable)."""
    tables = md_tables(text)
    if not tables or "name" not in tables[0][0] or "path" not in tables[0][0]:
        raise ValueError("no registry table")
    overrides = {}
    for headers, rows in tables[1:]:
        if "machine" in headers and "path" in headers:
            for r in rows:
                n = _clean(r.get("repo") or r.get("name"))
                w = _clean(r.get("machine")).lower()
                t = _clean(r.get("path"))
                if n and w and t:
                    overrides[(n, w)] = t
    here = [v.lower() for v in (role, key) if v]
    out = {}
    for r in tables[0][1]:
        name, path = _clean(r.get("name")), _clean(r.get("path"))
        if not name or not path:
            continue
        if (_clean(r.get("state")).lower() or "active") != "active":
            continue
        machines = _split_machines(r.get("machines", ""))
        if machines and here and not any(h in machines for h in here):
            continue
        for w in here:
            if (name, w) in overrides:
                path = overrides[(name, w)]
                break
        out[_real(path)] = (name, _clean(r.get("id")) or sanitize_key(name))
    return out


def machine_role(text, key):
    for headers, rows in md_tables(text):
        if "key" in headers and "role" in headers:
            for r in rows:
                if _clean(r.get("key")).lower() == key:
                    return _clean(r.get("role")).lower() or None
    return None


def machine_key():
    k = os.environ.get("LODESTAR_MACHINE", "").strip()
    return (k or socket.gethostname().split(".")[0]).lower()


class Registry(object):
    """Lodestar's sync/registry.md, re-parsed only when its mtime changes."""

    def __init__(self):
        self._sig = None
        self._val = None

    def lookup(self, lodestar):
        """('absent', None) Lodestar missing / no registry; ('failed', None) unreadable or
        unparseable; ('ok', {realpath: (name, id)})."""
        if not lodestar:
            return "absent", None
        reg = os.path.join(lodestar, "sync", "registry.md")
        mach = os.path.join(lodestar, "machines.md")
        try:
            st = os.stat(reg)
        except FileNotFoundError:
            return "absent", None
        except OSError:
            return "failed", None
        try:
            mst = os.stat(mach).st_mtime
        except OSError:
            mst = None
        key = machine_key()
        sig = (reg, st.st_mtime, st.st_size, mst, key)
        if sig == self._sig:
            return self._val
        try:
            with open(reg, encoding="utf-8") as fh:
                text = fh.read()
            role = None
            try:
                with open(mach, encoding="utf-8") as fh:
                    role = machine_role(fh.read(), key)
            except OSError:
                pass
            val = ("ok", parse_registry(text, role, key))
        except (OSError, ValueError, UnicodeDecodeError):
            val = ("failed", None)
        self._sig, self._val = sig, val
        return val


# --------------------------------------------------------------------------- shared file readers

_SP_DIR = []


def sidepulse_dir():
    """SidePulse's state dir (RB-n13), never derived from AUGUR_HOME: $SIDEPULSE_STATE_DIR (as
    sidepulse_client reads it), else <agent storage root>/sidepulse with the root from
    $AGENT_STORAGE_ROOT or Lodestar's agent_storage.py (run once per process). Raises RuntimeError
    naming both variables when neither yields a root; there is no fallback."""
    v = os.environ.get("SIDEPULSE_STATE_DIR", "").strip()
    if v:
        return os.path.expanduser(v)
    v = os.environ.get("AGENT_STORAGE_ROOT", "").strip()
    if v:
        return os.path.join(os.path.expanduser(v), "sidepulse")
    if not _SP_DIR:
        helper = os.path.expanduser("~/dev/Lodestar/bin/lib/agent_storage.py")
        try:
            root = subprocess.run(["/usr/bin/python3", helper], capture_output=True, text=True,
                                  timeout=20).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            root = ""
        if not root:
            raise RuntimeError("SIDEPULSE_STATE_DIR and AGENT_STORAGE_ROOT unset and "
                               "agent_storage.py printed no root")
        _SP_DIR.append(os.path.join(root, "sidepulse"))
    return _SP_DIR[0]


def read_sidepulse(ctx):
    """('absent', {}) no file; ('failed', {}) unreadable or no storage root; ('ok', {pid: slot})."""
    try:
        p = os.path.join(sidepulse_dir(), "state.json")
    except RuntimeError:
        return "failed", {}
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except FileNotFoundError:
        return "absent", {}
    except (OSError, ValueError):
        return "failed", {}
    slots = d.get("slots") if isinstance(d, dict) else None
    if isinstance(slots, dict):
        slots = list(slots.values())
    if not isinstance(slots, list):
        return "failed", {}
    out = {}
    for s in slots:
        if not isinstance(s, dict):
            continue
        try:
            out[int(s.get("pid"))] = s
        except (TypeError, ValueError):
            continue
    return "ok", out


def read_session_file(home, pid):
    """The parsed ~/.claude/sessions/<pid>.json, or None."""
    try:
        with open(os.path.join(home, ".claude", "sessions", "%d.json" % pid), encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def _merge_notice(d, aid, t):
    """R5-5: keep the newest TIMESTAMPED notice per agent id. None (no timestamp) stands only while
    no timestamped notice exists for that id; one that does replaces it for good."""
    if aid not in d or d[aid] is None:
        d[aid] = t
    elif t is not None:
        d[aid] = max(t, d[aid])


def _child(ru):
    return ru[4] if len(ru) > 4 else 0.0


def _own_child(ru):
    return ru[0] + _child(ru)


def _start_of(sid):
    try:
        return int(sid.split("@", 1)[1])
    except (IndexError, ValueError, AttributeError):
        return None


def _last_line_state(path, size):
    """("end"|"run"|"stream", None) from the last complete line in the file's tail. Only type,
    stop_reason and isApiErrorMessage are read; never message text."""
    with open_regular(path) as fh:
        fh.seek(max(0, size - SUBAGENT_TAIL))
        data = fh.read(SUBAGENT_TAIL)
    for raw in reversed(data.split(b"\n")):
        if not raw.strip():
            continue
        try:
            d = json.loads(raw)
        except ValueError:
            continue                      # a partial last line (or cut head): look further back
        if not isinstance(d, dict):
            continue
        if d.get("type") != "assistant":
            return "run"                  # user / attachment: a tool result is pending
        if d.get("isApiErrorMessage") is True:
            return "end"                  # died on an API error
        m = d.get("message") if isinstance(d.get("message"), dict) else {}
        sr = m.get("stop_reason")
        if sr == "end_turn":
            return "end"
        return "run" if sr else "stream"  # tool_use waits on its tool; None = mid-stream
    return "run"


def subagent_running(path, st, now, cache):
    """Running = its last complete line is not a terminal assistant line (end_turn, or an API
    error), and a mid-stream line is not older than STREAM_STALE_S. A resumed agent (new lines
    after an end_turn) runs again. Cached by (size, mtime)."""
    sig = (st.st_size, st.st_mtime)
    hit = cache.get(path)
    if hit is None or hit[0] != sig:
        try:
            hit = (sig, _last_line_state(path, st.st_size))
        except OSError:
            hit = (sig, "end")
        cache[path] = hit
    state = hit[1]
    if state == "stream":
        return now - st.st_mtime <= STREAM_STALE_S
    return state == "run"


# --------------------------------------------------------------------------- sessions

class SessionsCollector(Collector):
    name = "sessions"
    tier = "agents"
    platforms = ("darwin",)
    signals = ("sessions",)

    def __init__(self, readers=None):
        self.r = readers or Readers()
        self.registry = Registry()
        self._sub_state = {}             # subagent transcript -> ((size, mtime), state)
        self._bg_ids = {}                # transcript -> [offset, inode, set of announced task ids]
        self._notices = {}               # transcript -> [offset, inode, set of notified agent ids]
        self._last_t = {}                # agent file -> ((size, mtime, inode), newest line timestamp)
        self._seen = None                # transcript paths read this collect (R5-11, RB-m9 prune)
        self._pick = {}                  # (pid, start) -> (project dir mtime, picked session id)
        self._budget = None              # [bytes left this collect] (RB-m7)
        self._behind = False
        self._seen_picks = None

    def _prune(self):
        """R5-11, RB-m9: once per collect, against the union over every session's transcripts."""
        keep = self._seen or set()
        for cache in (self._last_t, self._sub_state, self._bg_ids, self._notices):
            for k in [k for k in cache if k not in keep]:
                del cache[k]
        for k in [k for k in self._pick if k not in (self._seen_picks or ())]:
            del self._pick[k]

    def _scan(self, ctx, st):
        """{pid: {ppid, start, comm, root}} over the session trees only: candidate roots are the
        pids named by ~/.claude/sessions/*.json, each tree is a proc_listchildpids walk. When the
        sessions directory cannot be listed, falls back to a full sweep of own-uid pids."""
        try:
            names = os.listdir(os.path.join(ctx.home, ".claude", "sessions"))
        except OSError:
            procs, live = self._sweep(st)
            return procs, live, False, set()
        r = self.r
        me = r.uid()
        paths = st.setdefault("paths", {})
        procs, live, cand = {}, set(), set()
        for n in names:
            if n.endswith(".json") and n[:-5].isdigit():
                cand.add(int(n[:-5]))

        def add(pid, is_cand):
            bi = r.bsdinfo(pid)
            if not bi or bi[1] != me:
                return None
            key = (pid, bi[2])
            live.add(key)
            root = False
            if is_cand:
                if key not in paths:
                    pp = r.pidpath(pid) or ""
                    if not pp:          # a transient failure is not "not Claude": retry next tick
                        procs[pid] = {"ppid": bi[0], "start": bi[2], "comm": bi[3], "root": False}
                        return False
                    paths[key] = is_claude_path(pp)
                root = paths[key]
            procs[pid] = {"ppid": bi[0], "start": bi[2], "comm": bi[3], "root": root}
            return root

        truncated = set()
        for pid in sorted(cand):
            if add(pid, True):
                t = r.tree(pid, TREE_LIMIT)
                if len(t) >= TREE_LIMIT:
                    truncated.add(pid)
                for q in t[1:]:
                    if q not in procs:
                        add(q, q in cand)
        # last sweep's tree pids not reached this time (reparented orphans): looked up by pid,
        # kept only while the same pid@start lives
        for k in st.get("ru_sid", {}):
            if k[0] not in procs:
                add(k[0], False)
                if procs.get(k[0], {}).get("start") == k[1]:
                    t = r.tree(k[0], TREE_LIMIT)
                    if len(t) >= TREE_LIMIT:
                        truncated.add(k[0])       # R2-6: an orphan subtree at the cap, too
                    for q in t[1:]:
                        if q not in procs:
                            add(q, q in cand)
        for k in [k for k in paths if k not in live]:
            del paths[k]
        return procs, live, True, truncated

    # one sweep: {pid: {start, ppid, comm}} for own uid, plus cached path per pid@start
    def _sweep(self, st):
        r = self.r
        me = r.uid()
        procs = {}
        paths = st.setdefault("paths", {})
        live = set()
        for pid in r.all_pids():
            bi = r.bsdinfo(pid)
            if not bi or bi[1] != me:
                continue
            key = (pid, bi[2])
            live.add(key)
            if key not in paths:
                pp = r.pidpath(pid) or ""
                if not pp:
                    procs[pid] = {"ppid": bi[0], "start": bi[2], "comm": bi[3], "root": False}
                    continue
                paths[key] = is_claude_path(pp)
            procs[pid] = {"ppid": bi[0], "start": bi[2], "comm": bi[3], "root": paths[key]}
        for k in [k for k in paths if k not in live]:
            del paths[k]
        return procs, live

    def _is_session(self, ctx, st, pid, start, sessions_listable):
        key = (pid, start)
        cache = st.setdefault("matched", {})
        if cache.get(key):
            return True
        if not sessions_listable:
            return True
        d = read_session_file(ctx.home, pid)
        if d is None:
            return False
        want = proc_start_epoch(d.get("procStart"))
        ok = want is None or abs(start - want) <= 2
        if ok:
            cache[key] = True
        return ok

    def _headless(self, ctx, st, pid, start):
        """True when this root is a headless run: its session file's entrypoint is sdk-cli, or its
        argv carries -p / --print. Cached per pid@start once an answer was read."""
        key = (pid, start)
        cache = st.setdefault("headless", {})
        if key in cache:
            return cache[key]
        d = read_session_file(ctx.home, pid)
        if d is not None and isinstance(d.get("entrypoint"), str):
            cache[key] = d["entrypoint"] == "sdk-cli"    # the file is the better witness: argv is
            return cache[key]                             # space-joined, so a prompt can hold " -p "
        try:
            argv = (self.r.cmdline(pid) or "").split()
        except Exception:  # noqa: BLE001 - unreadable argv is no evidence
            argv = []
        if not argv:
            return False                 # nothing read: not cached, retried next sweep
        cache[key] = any(a in ("-p", "--print") or a.startswith("--print=") for a in argv[1:])
        return cache[key]

    def _ancestors(self, st, procs, roots, heads):
        """{headless sid: (parent sid, parent pid)}: the nearest non-headless root up each headless
        root's ppid chain. Pids outside the scanned trees are looked up by bsdinfo."""
        out = {}
        for pid in heads:
            q, seen = procs[pid]["ppid"], set()
            while q and q > 1 and q not in seen and len(seen) < 256:
                seen.add(q)
                if q in roots and q not in heads:
                    out[roots[pid]] = (roots[q], q)
                    break
                p = procs.get(q)
                if p is not None:
                    q = p["ppid"]
                else:
                    bi = self.r.bsdinfo(q)
                    q = bi[0] if bi else None
            if roots[pid] not in out:    # reparented (double fork, nohup): the inherited socket
                sp = self._socket_pid(st, pid, procs[pid]["start"])
                if sp in roots and sp not in heads:
                    out[roots[pid]] = (roots[sp], sp)
        return out

    def _socket_pid(self, st, pid, start):
        """The session pid named by the run's inherited CLAUDE_CODE_MESSAGING_SOCKET
        (/tmp/cc-socks/<pid>.sock), or None. Read once per pid@start."""
        cache = st.setdefault("sock", {})
        key = (pid, start)
        if key not in cache:
            try:
                v = self.r.environ_value(pid, "CLAUDE_CODE_MESSAGING_SOCKET") or ""
            except Exception:  # noqa: BLE001 - no evidence, never a crash
                v = ""
            m = SOCK_RE.search(v)
            cache[key] = int(m.group(1)) if m else None
        return cache[key]

    def _project(self, ctx, st, sid, pid, reg):
        cache = st.setdefault("proj", {})
        if sid not in cache:
            cwd = ""
            try:
                cwd = self.r.cwd(pid) or ""
            except Exception:
                cwd = ""
            top = git_toplevel(cwd) if cwd else None
            cache[sid] = {"cwd": cwd, "top": _real(top) if top else None,
                          "base": os.path.basename((top or cwd).rstrip("/")) if (top or cwd) else ""}
        c = cache[sid]
        status, rows = reg
        # S4: a folder outside any repo is not a project name (it can be a person or a proposal):
        # only a git toplevel or a registry row names one
        base = c["base"] if c["top"] else ""
        out = {"project": base or "unknown", "project_key": sanitize_key(base) if base else "unknown"}
        top = c["top"]
        if top and ctx.lodestar and top == _real(ctx.lodestar):
            out["project_key"] = "lodestar"
        if status == "absent":
            out["managed"] = False
        elif status == "ok":
            hit = rows.get(top) if top else None
            if hit:
                out["project"], out["project_key"], out["managed"] = hit[0], hit[1], True
                if top == _real(ctx.lodestar or ""):
                    out["project_key"] = "lodestar"
            else:
                out["managed"] = False
        return out, c["cwd"]

    def collect(self, ctx):
        self._seen, self._seen_picks = set(), set()
        self._budget = [SCAN_BUDGET]
        try:
            out = self._collect(ctx)
            self._prune()                # only after a whole sweep: a partial one would evict
            return out
        finally:
            self._seen = self._seen_picks = self._budget = None

    def _collect(self, ctx):
        st = ctx.state
        procs, live, sessions_listable, truncated = self._scan(ctx, st)
        roots = {}
        for pid, p in procs.items():
            if p["root"] and self._is_session(ctx, st, pid, p["start"], sessions_listable):
                roots[pid] = "%d@%d" % (pid, p["start"])
        m = st.get("matched", {})
        for k in [k for k in m if k not in live]:
            del m[k]
        for name in ("headless", "sock"):
            hl = st.setdefault(name, {})
            for k in [k for k in hl if k not in live]:
                del hl[k]
        heads = {pid for pid in roots if self._headless(ctx, st, pid, procs[pid]["start"])}
        parent_of = self._ancestors(st, procs, roots, heads)
        children = {}
        for pid, p in procs.items():
            children.setdefault(p["ppid"], []).append(pid)
        trees, in_tree = {}, set()

        def walk(sid, top):
            todo = [top]
            while todo:
                q = todo.pop()
                if q in in_tree:
                    continue
                in_tree.add(q)
                trees[sid].append(q)
                for c in children.get(q, ()):
                    if c not in roots and c != q:
                        todo.append(c)
        for rp, sid in roots.items():
            trees[sid] = []
            walk(sid, rp)
        # orphans: pids this session started that were reparented out of its tree (nohup, a
        # double fork) stay the session's while it lives (review R1 finding 2)
        prev = st.get("ru", {})
        prev_sid = st.get("ru_sid", {})  # (pid, start) -> sid, last sweep
        orphans = {}                     # sid -> top pids of orphaned subtrees (tasks "other")
        for k, sid in sorted(prev_sid.items()):
            p = procs.get(k[0])
            if sid in trees and k[0] not in in_tree and k[0] not in roots and p and p["start"] == k[1]:
                if p["ppid"] not in procs or p["ppid"] <= 1:
                    orphans.setdefault(sid, []).append(k[0])
                walk(sid, k[0])
        for sid in trees:
            trees[sid].sort()
        owner = {pid: sid for sid, t in trees.items() for pid in t}

        def key(pid):
            return (pid, procs[pid]["start"])

        def alive(k):
            p = procs.get(k[0])
            return p is not None and p["start"] == k[1]

        # rusage only for tree pids; a failed read is NOT an exit (finding 3)
        now_m = ctx.mono
        cur = {}
        vanished = set()
        for sid, tree in trees.items():
            for pid in tree:
                ru = self.r.rusage(pid)
                if ru:
                    cur[key(pid)] = ru
                else:
                    # R2-7: a failed read of a pid that has since exited is an exit this tick
                    bi = self.r.bsdinfo(pid)
                    if not bi or bi[2] != procs[pid]["start"]:
                        vanished.add(pid)
        if vanished:
            for sid in list(trees):
                if int(sid.split("@")[0]) in vanished:      # R3-1: the session itself ended
                    for p in trees.pop(sid):
                        owner.pop(p, None)
                    continue
                trees[sid] = [p for p in trees[sid] if p not in vanished]
            for pid in vanished:
                procs.pop(pid, None)
                owner.pop(pid, None)
        # Gone-credits (R1 1, 4; R2 1, 2, 7). A reap adds the dead child's WHOLE final own+child
        # total to its parent's child time in one step, never less than what was last seen. So a
        # credit [known, tail] on the live process that will reap it is used only against a
        # child-time rise of at least `known`, and then removes known + at most `tail` (the part
        # of the final total that is not this session's: a nested session's last interval, bounded
        # by its last rate). Smaller rises are other children: counted. A credit lives as long as
        # its target pid@start does (no expiry: a late reap must not double-count).
        par = st.get("ru_par", {})
        pending = st.setdefault("pending", {})     # target key -> [[known, tail], ...]
        rates = st.get("rate", {})
        gone = [k for k in prev if not alive(k)]
        gone_set = set(gone)
        since = max(0.0, now_m - st.get("ru_mono", now_m))

        def target(k):
            t, seen = par.get(k), set()
            while t is not None and t in gone_set and t not in seen:
                seen.add(t)
                t = par.get(t)
            return t if t is not None and alive(t) and t[0] in owner else None
        for k in gone:
            t = target(k)
            moved = pending.pop(k, None)
            if t is None:
                continue                 # reaped by launchd (an orphan): no tree pid gains it
            foreign = prev_sid.get(k) != owner.get(t[0])
            tail = rates.get(k, 0.0) * since if foreign else 0.0
            pending.setdefault(t, []).append([_own_child(prev[k]), tail, now_m])
            if moved:
                pending[t].extend(moved)
        for t in [t for t in pending if not alive(t)]:
            del pending[t]
        # RB-m8: a credit unmatched for CREDIT_MAX_AGE_S is retired (its reap never showed, or was
        # folded into a smaller rise); the drop shows in pending_reconciliation_cpu_s and the
        # retired CPU-s are counted in audit credit_retired_cpu_s, never silently
        retired = 0.0
        for t in list(pending):
            keep = [c for c in pending[t] if len(c) < 3 or now_m - c[2] <= CREDIT_MAX_AGE_S]
            retired += sum(c[0] for c in pending[t] if c not in keep)
            if keep:
                pending[t] = keep
            else:
                del pending[t]
        if retired:
            audit = ctx.shared.setdefault("audit", {})
            audit["credit_retired_cpu_s"] = round(audit.get("credit_retired_cpu_s", 0.0) + retired, 3)
        new_rates = {}
        last = st.get("last", {})       # sid -> (mono, wait, wall)
        prev_wall = st.get("wall")
        reg = self.registry.lookup(ctx.lodestar)
        side_status, slots = read_sidepulse(ctx)
        shell_cache = st.setdefault("shell", {})
        out, wait_sum, any_measured, new_last = [], 0.0, False, {}
        new_ru = {}
        tdirs = {}
        acc = {"wait_sum": 0.0, "any": False}

        def one(sid, tree, tx):
                # R5-7: every write goes to the scratch `tx`; collect() merges it only on success
                t_ru, t_last, t_rates, t_pend = tx["ru"], tx["last"], tx["rates"], tx["pending"]
                rp = int(sid.split("@")[0])
                start = procs[rp]["start"]
                ident, cwd = self._project(ctx, st, sid, rp, reg)
                if sid in parent_of:     # a headless child wears its parent's identity (1.2)
                    psid, ppid_ = parent_of[sid]
                    ident = dict(self._project(ctx, st, psid, ppid_, reg)[0])
                    ident["parent"] = psid
                if rp in heads:
                    ident = dict(ident, headless=True)
                tx["proj_out"] = ident
                s = {"id": sid, "pid": rp, "started_at": float(start)}
                s.update(ident)
                keys = [key(p) for p in tree]
                failed = [k for k in keys if k not in cur]
                carry = {k: prev[k] for k in keys if k in prev}

                def adopt():
                    t_ru.update(carry)
                    t_ru.update((k, cur[k]) for k in keys if k in cur)
                if rp in truncated or any(o in truncated for o in orphans.get(sid, ())):
                    load = {"unknown": "truncated"}           # finding 14: never a partial sum
                    adopt()
                    t_last[sid] = (now_m, None, ctx.now)
                elif sid not in last:
                    load = {"unknown": "warming_up"}
                    adopt()
                    t_last[sid] = (now_m, None, ctx.now)
                elif key(rp) in failed or 2 * len(failed) > len(keys):
                    load = {"unknown": "read_failed"}         # finding 3: absent, never 0
                    t_ru.update(carry)                        # keep the baseline for the next read
                    t_last[sid] = last[sid]
                else:
                    dt = now_m - last[sid][0]
                    cpu_s = wait = 0.0
                    reset = False
                    lw = last[sid][2] if len(last[sid]) > 2 else prev_wall
                    # RB-m5: after a wall step (wall and mono intervals differ by > WALL_STEP_S)
                    # the last sweep is placed on the new wall clock by the mono interval
                    if lw is not None and abs((ctx.now - lw) - dt) > WALL_STEP_S:
                        lw = ctx.now - dt
                    born_after = int(lw) if lw is not None else None
                    use_credit = []
                    for k in keys:
                        if k not in cur or dt <= 0:
                            continue
                        if k in prev:
                            dc = cur[k][0] - prev[k][0]
                            dr = cur[k][1] - prev[k][1]
                            dch = _child(cur[k]) - _child(prev[k])
                            if dc < -1e-6 or dch < -1e-6:
                                reset = True
                                break
                            cpu_s += max(0.0, dc)
                            wait += max(0.0, dr - dc) / dt
                            if dt > 0:
                                t_rates[k] = max(0.0, dc + max(0.0, dch)) / dt
                            if dch > 0 and t_pend.get(k):
                                used = []
                                for i, c in sorted(enumerate(t_pend[k]), key=lambda x: -x[1][0]):
                                    known, tail = c[0], c[1]
                                    if dch >= known - CREDIT_EPS_S:
                                        dch -= min(dch, known + tail)
                                        used.append(i)
                                if used:
                                    use_credit.append((k, used))
                            if dch > 0:
                                cpu_s += dch      # children born and reaped between sweeps
                        elif born_after is not None and k[1] >= born_after:
                            cpu_s += _own_child(cur[k])   # born this interval: all of it is new
                    adopt()
                    t_last[sid] = (now_m, None, ctx.now)
                    if reset:
                        load = {"unknown": "counter_reset"}   # finding 12
                    else:
                        for k, used in use_credit:
                            t_pend[k] = [c for i, c in enumerate(t_pend[k]) if i not in used]
                        mem = sum((cur.get(k) or carry[k])[2] for k in keys if k in cur or k in carry)
                        cpu = cpu_s / dt if dt > 0 else 0.0
                        starved = wait >= STARVED_WAIT and (last[sid][1] or 0.0) >= STARVED_WAIT
                        load = {"cpu_cores": round(cpu, 3), "mem_gb": round(mem / 1e9, 3),
                                "procs": len(tree), "wait_s_per_s": round(wait, 3),
                                "starved": bool(starved), "provisional": True,
                                # prior art (PROCESS_TRACKING_PRIOR_ART.md): a sampled tree with reap
                                # reconciliation, never "exact"; CPU of exited children not yet
                                # matched to a reap is reported, not guessed
                                "method": "sampled_with_reap_reconciliation",
                                "pending_reconciliation_cpu_s": round(sum(
                                    c[0] for k in keys for c in t_pend.get(k, ())), 3)}
                        tx["wait"] = wait
                        t_last[sid] = (now_m, wait, ctx.now)
                s["load"] = load
                # tasks
                shells, tool_shells = 0, []
                for p in tree:
                    if p == rp or procs[p]["comm"] not in SHELL_COMMS:
                        continue
                    k = (p, procs[p]["start"])
                    if k not in shell_cache:
                        try:
                            c = self.r.cmdline(p) or ""
                        except Exception:
                            c = ""
                        shell_cache[k] = c.startswith(SHELL_PREFIX) and SHELL_MARK in c
                    shells += shell_cache[k]
                    if shell_cache[k]:
                        tool_shells.append(k)
                if cwd:          # R4-2: before _tasks, so a tasks failure cannot blind machine.api
                    tx["tdir"] = os.path.join(ctx.home, ".claude", "projects", transcript_slug(cwd))
                s["tasks"] = self._tasks(ctx, rp, start, cwd, slots, shells, tool_shells,
                                         len(orphans.get(sid, ())), st)
                return s

        for sid, tree in sorted(trees.items()):
            # R4-1, R5-7: a session's sweep is a transaction over everything it writes (baselines,
            # last, rates, the credit ledger, its identity and transcript dir). It runs on a scratch
            # copy, merged only on success; on an exception nothing of that session changes from
            # the previous state, so a consumed credit is not lost and a child born this interval
            # keeps no baseline from the failed tick (its whole CPU counts on the next good tick).
            keys0 = [(p, procs[p]["start"]) for p in tree if p in procs]
            tx = {"ru": {}, "last": {}, "rates": {}, "wait": None, "tdir": None, "proj_out": None,
                  "pending": {k: [list(c) for c in pending[k]] for k in keys0 if k in pending}}
            try:
                s = one(sid, tree, tx)
            except Exception as ex:  # noqa: BLE001 - one session never blanks the others
                # R3 rule: a per-session failure degrades only that session's load and tasks
                # (absent); its baselines are kept so the next tick spans both intervals
                rp = int(sid.split("@")[0])
                p0 = procs.get(rp)
                if p0 is not None:
                    row = {"id": sid, "pid": rp, "started_at": float(p0["start"])}
                    row.update((st.get("proj_out") or {}).get(sid) or {"project": "unknown", "project_key": "unknown"})
                    out.append(row)
                for k in keys0:
                    if k in prev:
                        new_ru[k] = prev[k]
                    if k in rates:
                        new_rates[k] = rates[k]
                if sid in last:
                    new_last[sid] = last[sid]
                errs = st.setdefault("errors", {})
                errs[type(ex).__name__] = errs.get(type(ex).__name__, 0) + 1
                continue
            new_ru.update(tx["ru"])
            new_last.update(tx["last"])
            new_rates.update(tx["rates"])
            for k in keys0:
                pending.pop(k, None)
            pending.update((k, v) for k, v in tx["pending"].items() if v)
            if tx["wait"] is not None:
                acc["wait_sum"] += tx["wait"]
                acc["any"] = True
            if tx["tdir"]:
                tdirs[sid] = tx["tdir"]
            st.setdefault("proj_out", {})[sid] = tx["proj_out"]
            out.append(s)
        wait_sum, any_measured = acc["wait_sum"], acc["any"]
        for k in [k for k in shell_cache if k not in live]:
            del shell_cache[k]
        bgo = st.get("bg_out", {})
        for k in [k for k in bgo if k not in live]:
            del bgo[k]
        proj = st.get("proj", {})
        for k in [k for k in proj if k not in trees]:
            del proj[k]
        po = st.get("proj_out", {})
        for k in [k for k in po if k not in trees]:
            del po[k]
        st["ru"], st["last"], st["wall"] = new_ru, new_last, ctx.now
        st["ru_mono"], st["rate"] = now_m, new_rates
        st["ru_sid"] = {k: owner[k[0]] for k in new_ru}
        st["ru_par"] = {k: (key(procs[k[0]]["ppid"]) if procs[k[0]]["ppid"] in procs else None)
                        for k in new_ru}
        ctx.shared["session_trees"] = trees
        ctx.shared["transcript_dirs"] = tdirs        # read by the api collector
        ctx.shared["sessions_mono"] = ctx.mono       # R2-10: when that list was last current
        ctx.shared["session_ids_by_pid"] = {int(sid.split("@")[0]): sid for sid in trees}
        # None until a delta exists; with no sessions at all after the first tick the sum is 0.0
        measured = any_measured or (not trees and st.get("ticked"))
        ctx.shared["agent_wait_s_per_s"] = round(wait_sum, 3) if measured else None
        st["ticked"] = True
        return {"sessions": out}

    _buf = None

    @classmethod
    def _scan_lines(cls, path, start, size, on_line, state=None):
        """Feed complete lines in [start, size) to on_line (a memoryview of whole lines), reading
        into ONE reused buffer, never past `size` (R4-3). R3-2: no mmap (a truncation under a
        mapping is SIGBUS); a short read just ends the scan. R2-9: one reused bytearray keeps RSS
        flat. A line longer than the buffer is skipped whole, and `state["skip"]` carries "inside
        an over-long line" across calls, so its tail is never parsed as a record of its own.
        Returns the offset after the last consumed byte."""
        if cls._buf is None:
            cls._buf = bytearray(2 * SCAN_CHUNK)
        state = state if state is not None else {}
        buf = cls._buf
        mv = memoryview(buf)
        off, have = start, 0                     # bytes [0, have) of buf hold data from `off`
        try:
            with open_regular(path) as fh:
                fh.seek(start)
                while off + have < size:
                    want = min(len(buf) - have, size - off - have)
                    n = fh.readinto(mv[have:have + want])
                    if not n:
                        break                    # truncated under us: stop, next tick re-checks
                    have += n
                    if state.get("skip"):        # still inside an over-long line
                        k = buf.find(b"\n", 0, have)
                        if k < 0:
                            off += have
                            have = 0
                            continue
                        state["skip"] = False
                        buf[:have - k - 1] = buf[k + 1:have]
                        off += k + 1
                        have -= k + 1
                    end = buf.rfind(b"\n", 0, have) + 1
                    if end:
                        on_line(mv[:end])
                        buf[:have - end] = buf[end:have]
                        off += end
                        have -= end
                    elif have == len(buf):       # a line longer than the buffer: skip it whole
                        state["skip"] = True
                        off += have
                        have = 0
        finally:
            mv.release()
        return off

    FP_LEN = 64

    @classmethod
    def _entry(cls, store, path, stt, result):
        """The incremental-scan entry [offset, inode, result, scan state, fp, (size, mtime)] for
        path, reset to byte 0 on a new inode, a shrink, or (R5-4) a rewrite in place: the FP_LEN
        bytes before the offset (Tail's R2-5 fingerprint) are re-read whenever size or mtime moved,
        and a mismatch resets the offset AND the over-long-line skip state."""
        e = store.get(path)
        sig = (stt.st_size, stt.st_mtime)
        if e is not None and e[1] == stt.st_ino and stt.st_size >= e[0] and e[5] != sig and e[4]:
            try:
                with open_regular(path) as fh:
                    fh.seek(e[0] - len(e[4]))
                    if fh.read(len(e[4])) != e[4]:
                        e = None
            except OSError:
                e = None
        if e is None or e[1] != stt.st_ino or stt.st_size < e[0]:
            e = store[path] = [0, stt.st_ino, result(), {}, b"", None]
        e[5] = sig
        return e

    def _advance(self, e, path, size, on_line):
        """Scan e's file up to `size`, within this collect's byte budget (RB-m7: after a restart
        every main transcript is read from byte 0; spread over ticks, never one long stall). A
        scan cut short marks self._behind, and that session's tasks read warming_up."""
        b = self._budget
        if b is not None:
            if b[0] <= 0:
                self._behind = True
                return
            if size - e[0] > b[0]:
                size = e[0] + b[0]
                self._behind = True
        cls = type(self)
        try:
            start = e[0]
            e[0] = cls._scan_lines(path, e[0], size, on_line, e[3])
            if b is not None:
                b[0] -= max(e[0] - start, size - start)
            with open_regular(path) as fh:
                fh.seek(max(0, e[0] - cls.FP_LEN))
                e[4] = fh.read(e[0] - max(0, e[0] - cls.FP_LEN))
        except OSError:
            pass

    def _announced(self, path, regex=BG_ANNOUNCE_RE, store=None):
        """Task ids announced as background launches in one transcript, read incrementally."""
        store = self._bg_ids if store is None else store
        try:
            stt = os.stat(path)
        except OSError:
            return set()
        e = self._entry(store, path, stt, set)
        if stt.st_size > e[0]:
            # chunked, never mmap (R3-2); RSS stays flat because chunks are bounded (R2-9)
            def scan(block):
                for m in regex.finditer(block):
                    try:
                        e[2].add(bytes(next(g for g in m.groups() if g)).decode())
                    except Exception:  # noqa: BLE001 - one odd match never poisons the file
                        continue
            self._advance(e, path, stt.st_size, scan)
        return e[2]

    def _noticed(self, path):
        """Agent ids with a real completion notice in one transcript, read incrementally by
        chunks, one complete line at a time (only lines that mention task-notification parse).
        {agent id: epoch of its newest notice}."""
        try:
            stt = os.stat(path)
        except OSError:
            return {}
        e = self._entry(self._notices, path, stt, dict)
        if stt.st_size > e[0]:
            def scan(block):
                buf, n = block.obj, block.nbytes   # the shared bytearray: find, never a regex
                pos = buf.find(NOTICE_HINT, 0, n)
                while pos >= 0:
                    a = buf.rfind(b"\n", 0, pos) + 1
                    b = buf.find(b"\n", pos, n)
                    b = n if b < 0 else b
                    for aid, t in notice_ids(bytes(block[a:b])):     # never raises (R4-2)
                        _merge_notice(e[2], aid, t)
                    pos = buf.find(NOTICE_HINT, b, n)
            self._advance(e, path, stt.st_size, scan)
        return e[2]

    def _bg_shell(self, ctx, k, announced, st):
        """Is tool shell k a background one? By its stdout task id (announced, or older than any
        foreground call can live); with no readable stdout, by age."""
        cache = st.setdefault("bg_out", {})
        if k not in cache:
            try:
                m = TASK_OUT_RE.search(self.r.stdout_path(k[0]) or "")
            except Exception:  # noqa: BLE001
                m = None
            cache[k] = m.group(1) if m else None
        tid = cache[k]
        age = ctx.now - k[1]
        if tid is None:
            return age > BG_YOUNG_S
        return tid in announced or age > FG_MAX_S

    def _tasks(self, ctx, pid, start, cwd, slots, shells, tool_shells=(), other=0, st=None):
        if not cwd:
            return {"unknown": "read_failed"}
        self._behind = False
        out = self._tasks1(ctx, pid, start, cwd, slots, shells, tool_shells, other, st)
        if self._behind and "unknown" not in out:
            return {"unknown": "warming_up"}       # RB-m7: transcripts not yet read to the end
        return out

    def _tasks1(self, ctx, pid, start, cwd, slots, shells, tool_shells=(), other=0, st=None):
        pdir = os.path.join(ctx.home, ".claude", "projects", transcript_slug(cwd))
        slot = slots.get(pid)
        sess = hit = dmt = None
        if slot and isinstance(slot.get("sid"), str) and (slot.get("t") or 0) >= start - 2:
            sess = slot["sid"]
        if sess is None:
            # RB-m6: the pick is cached per (pid, start) and the directory's mtime (a new
            # transcript changes it), so the listing runs only when the directory changed
            try:
                dmt = os.stat(pdir).st_mtime
            except OSError:
                return {"unknown": "read_failed"}
            pk = (pid, start)
            if self._seen_picks is not None:
                self._seen_picks.add(pk)
            hit = self._pick.get(pk)
            if hit is not None and hit[0] == dmt:
                sess = hit[1]
        if sess is None and not (hit is not None and hit[0] == dmt):
            best = None
            try:
                with os.scandir(pdir) as it:
                    for e in it:
                        if e.name.endswith(".jsonl") and e.is_file(follow_symlinks=False):
                            mt = e.stat().st_mtime
                            if mt >= start and (best is None or mt > best[0]):
                                best = (mt, e.name[:-6])
            except OSError:
                return {"unknown": "read_failed"}
            sess = best[1] if best else None
            self._pick[pk] = (dmt, sess)
        subs = 0
        files = []
        seen = self._seen if self._seen is not None else set()
        if sess:
            sub = os.path.join(pdir, sess, "subagents")
            cutoff = ctx.now - SUBAGENT_MAX_AGE_S
            cache = self._sub_state
            files.append(os.path.join(pdir, sess + ".jsonl"))
            seen.add(files[-1])
            agents = []
            try:
                with os.scandir(sub) as it:
                    for e in it:
                        if (e.name.startswith("agent-") and e.name.endswith(".jsonl")
                                and e.is_file(follow_symlinks=False)):
                            est = e.stat()
                            if est.st_mtime >= cutoff:
                                files.append(e.path)
                                seen.add(e.path)
                                if subagent_running(e.path, est, ctx.now, cache):
                                    agents.append((e.path, e.name[6:-6], est))
                # bake-off: a completion notice for the agent's id (in the session's main file
                # or a parent agent's file) ends it even when its own last line is not
                # end_turn; a line written after the notice was first seen means it resumed
                if agents:
                    noticed = {}
                    for f in files:
                        for aid, t in self._noticed(f).items():
                            _merge_notice(noticed, aid, t)
                    unmeasured = False
                    for path, aid, est in agents:
                        if aid not in noticed:
                            subs += 1
                            continue
                        if noticed[aid] is None:
                            unmeasured = True        # a notice that cannot be ordered: no guess
                            continue
                        # R4-9: resumed only if the agent file holds a line written after the
                        # notice (its own timestamp), never because its mtime moved (a touch)
                        # R5-6: cached by (size, mtime, inode); a failed read is never cached and
                        # a tail with no timestamped line is unmeasured, never "ended"
                        sig = (est.st_size, est.st_mtime, est.st_ino)
                        hit = self._last_t.get(path)       # a cost guard
                        if hit is None or hit[0] != sig:
                            try:
                                hit = (sig, _last_line_epoch(path, est.st_size))
                            except OSError:
                                unmeasured = True
                                continue
                            self._last_t[path] = hit
                        last_t = hit[1]
                        if last_t is None:
                            unmeasured = True
                        elif last_t > noticed[aid] + RESUME_SLACK_S:
                            subs += 1
                    if unmeasured:
                        return {"unknown": "read_failed"}
            except FileNotFoundError:
                subs = 0           # no subagent has run in this session yet
            except OSError:
                return {"unknown": "read_failed"}
        elif not os.path.isdir(pdir):
            return {"unknown": "read_failed"}
        # background work (owner ruling 2026-11-01): run_in_background shells of the session and
        # its subagents, live subagents, and orphaned workers it launched. Not foreground tool
        # shells, not MCP servers or the harness's own helpers (non-shell children of the root).
        bg = 0
        if tool_shells:
            ann = set()
            for f in files:
                ann |= self._announced(f)
            bg = sum(1 for k in tool_shells if self._bg_shell(ctx, k, ann, st if st is not None else {}))
        return {"shells": int(shells), "bg_shells": bg, "subagents": subs, "other": int(other),
                "total": bg + subs + int(other), "method": "tree+transcripts", "provisional": True}


# --------------------------------------------------------------------------- attention

class AttentionCollector(Collector):
    name = "attention"
    tier = "fast"
    platforms = ("darwin",)
    signals = ("sessions.attention",)

    def __init__(self, readers=None):
        self.r = readers or Readers()

    def collect(self, ctx):
        ids = ctx.shared.get("session_ids_by_pid") or {}
        if not ids:
            return {"sessions.attention": {}}
        status, slots = read_sidepulse(ctx)
        out = {}
        for pid, sid in ids.items():
            start = _start_of(sid) or 0
            v = None
            slot = slots.get(pid)
            if slot and (slot.get("t") or slot.get("since") or 0) >= start - 2:
                state = slot.get("state")
                since = slot.get("since")
                since = float(since) if isinstance(since, (int, float)) else None
                if state == "working":
                    v = {"state": "working"}
                elif state == "needs-you":
                    v = {"state": "needs_you"}
                elif state == "done":
                    recent = since is not None and ctx.now - since <= STOPPED_WINDOW_S
                    v = {"state": "stopped" if recent else "idle"}
                if v is not None and since is not None:
                    v["since"] = round(since, 3)
            if v is None:
                d = read_session_file(ctx.home, pid) or {}
                word = {"busy": "working", "waiting": "needs_you", "idle": "idle"}.get(d.get("status"))
                if word:
                    v = {"state": word}
                    su = d.get("statusUpdatedAt")
                    if isinstance(su, (int, float)) and su > 0:
                        v["since"] = round(su / 1000.0, 3)
            if v is None and status == "failed":
                v = {"unknown": "read_failed"}
            if v is not None:
                out[sid] = v
        return {"sessions.attention": out}


# --------------------------------------------------------------------------- session_net

_FLOW_RE = re.compile(r"^(tcp|udp)[46] ")


def _split_endpoint(ep, proto):
    """'a.b.c.d:port' (v4) or 'addr.port' (v6) -> host string."""
    if proto.endswith("4"):
        return ep.rsplit(":", 1)[0]
    return ep.rsplit(".", 1)[0]


def _is_loop(host):
    h = host.split("%", 1)[0].lower()
    return h.startswith("127.") or h == "::1" or h.startswith("::ffff:127.")


def _num(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def parse_nettop(text, wanted):
    """{flow_key: (pid, in, out, retx, tcp)} for live, non-loopback flows of `wanted` pids.
    Raises ValueError when the header is missing. Flow keys and addresses stay in memory."""
    lines = text.splitlines()
    if not lines or "bytes_in" not in lines[0]:
        raise ValueError("no nettop header")
    rows = []
    local_hosts = set()
    pid = None
    for ln in lines[1:]:
        if not ln.strip():
            continue
        parts = ln.split(",")
        if _FLOW_RE.match(ln):
            if pid is None:
                continue
            proto, tup = parts[0].split(" ", 1)
            if "<->" not in tup:
                continue
            a, b = tup.split("<->", 1)
            la, rb = _split_endpoint(a, proto), _split_endpoint(b, proto)
            local_hosts.add(la.split("%", 1)[0])
            rows.append((proto, tup, la, rb, pid, parts[1:4]))
        else:
            name = parts[0]
            p = _num(name.rsplit(".", 1)[-1]) if "." in name else None
            pid = p if p is not None and p in wanted else None
    out = {}
    for proto, tup, la, rb, p, vals in rows:
        if "*" in rb or _is_loop(la) or _is_loop(rb) or rb.split("%", 1)[0] in local_hosts:
            continue
        bi, bo, rx = (_num(v) for v in (vals + ["", "", ""])[:3])
        key = proto + " " + tup
        if key in out:            # same socket listed under two pids: credit the first only
            continue
        # an unparsable counter stays None (unknown), never 0 and never dropped (R1 finding 15)
        out[key] = (p, bi, bo, rx, proto.startswith("tcp"))
    return out


class SessionNetCollector(Collector):
    name = "session_net"
    tier = "agents"
    platforms = ("darwin",)
    signals = ("sessions.net",)

    # DESIGN section 6: nettop measured 0.79 % of one core at the 5 s agents cadence under the
    # Background band (~42 ms CPU per exec there vs ~12 ms from a terminal), over the 0.40 %
    # agents line on its own. At 15 s it is ~0.26 %; consumers still get rx/tx within 15 s.
    # R5 (c): 30 s while every session read under IDLE_BPS (rx + tx) on the last exec, 15 s
    # otherwise (any unknown, a first tick, a burst). The core reads every_s on each tier pass.
    every_s = 15.0
    BUSY_EVERY_S, IDLE_EVERY_S = 15.0, 30.0
    IDLE_BPS = 10_000.0

    def __init__(self, readers=None):
        self.r = readers or Readers()

    def collect(self, ctx):
        self.every_s = self.BUSY_EVERY_S
        out = self._collect(ctx)
        v = out.get("sessions.net")
        if isinstance(v, dict) and v and "unknown" not in v and all(
                isinstance(x, dict) and "unknown" not in x
                and (x.get("rx_bps", 0.0) + x.get("tx_bps", 0.0)) < self.IDLE_BPS for x in v.values()):
            self.every_s = self.IDLE_EVERY_S
        if isinstance(v, dict):
            for x in v.values():
                if isinstance(x, dict):
                    x.pop("rx_bps", None)
                    x.pop("tx_bps", None)
        return out

    def _collect(self, ctx):
        trees = ctx.shared.get("session_trees") or {}
        st = ctx.state
        if not trees:
            st.pop("flows", None)
            st["seen"] = set()
            return {}
        by_pid = {}
        for sid, pids in trees.items():
            for p in pids:
                by_pid[p] = sid
        pids = sorted(by_pid)
        t0, c0 = time.monotonic(), _children_cpu()
        try:
            rc, text = self.r.nettop(pids, timeout=NETTOP_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            self._meter(ctx, t0, c0)
            return {"sessions.net": {"unknown": "timeout"}}
        except OSError:
            return {"sessions.net": {"unknown": "read_failed"}}
        mono = ctx.mono
        self._meter(ctx, t0, c0)
        if rc != 0:
            return {"sessions.net": {"unknown": "read_failed"}}
        try:
            flows = parse_nettop(text, set(pids))
        except ValueError:
            return {"sessions.net": {"unknown": "read_failed"}}
        prev = st.get("flows")
        prev_mono = st.get("mono")
        seen = st.get("seen") or set()
        # per-flow baselines carry their own time: a flow whose row could not be parsed keeps its
        # last good reading, so the next good one is a delta over its own interval
        base = {}
        for key, (p, bi, bo, rx, tcp) in flows.items():
            if bi is not None and bo is not None:
                base[key] = (p, bi, bo, rx, tcp, mono)
            elif prev and key in prev:
                base[key] = prev[key]
        st["flows"], st["mono"], st["seen"] = base, mono, set(trees)
        if prev is None or prev_mono is None or mono <= prev_mono:
            return {"sessions.net": {"unknown": "warming_up"}}
        acc = {sid: [0.0, 0.0, 0, 0, 0, False, False] for sid in trees}
        # rx B/s, tx B/s, flows, dretx, dout_tcp, any flow unparsable, any retx unknown
        rx_sum = tx_sum = 0
        for key, (p, bi, bo, rx, tcp) in flows.items():
            sid = by_pid.get(p)
            if sid is None:
                continue
            a = acc[sid]
            a[2] += 1
            if bi is None or bo is None:
                a[5] = True
                continue
            old = prev.get(key)
            if old is None or bi < old[1] or bo < old[2]:
                continue                              # first sight or reset: 0, never a guess
            dtf = mono - (old[5] if len(old) > 5 else prev_mono)
            if dtf <= 0:
                continue
            a[0] += (bi - old[1]) / dtf
            a[1] += (bo - old[2]) / dtf
            rx_sum += bi - old[1]
            tx_sum += bo - old[2]
            if tcp:
                if rx is None or old[3] is None:
                    a[6] = True
                else:
                    a[3] += max(0, rx - old[3])
                    a[4] += bo - old[2]
        out = {}
        for sid, (rin, rout, n, dre, dtcp, broken, noretx) in acc.items():
            if sid not in seen:
                out[sid] = {"unknown": "warming_up"}
                continue
            if broken:
                out[sid] = {"unknown": "read_failed"}
                continue
            v = {"rx_mbps": round(rin * 8 / 1e6, 3), "tx_mbps": round(rout * 8 / 1e6, 3),
                 "flows": n, "provisional": True, "rx_bps": rin * 8, "tx_bps": rout * 8}
            if dtcp > 0 and not noretx:
                v["retx_pct"] = round(dre / dtcp * 100.0, 2)
            out[sid] = v
        audit = ctx.shared.setdefault("audit", {})
        audit["session_rx_bytes"] = audit.get("session_rx_bytes", 0) + rx_sum
        audit["session_tx_bytes"] = audit.get("session_tx_bytes", 0) + tx_sum
        audit["session_net_ticks"] = audit.get("session_net_ticks", 0) + 1
        return {"sessions.net": out}

    def _meter(self, ctx, t0, c0):
        audit = ctx.shared.setdefault("audit", {})
        audit["nettop_calls"] = audit.get("nettop_calls", 0) + 1
        audit["nettop_wall_ms"] = round(audit.get("nettop_wall_ms", 0.0) + (time.monotonic() - t0) * 1e3, 3)
        audit["nettop_cpu_ms"] = round(audit.get("nettop_cpu_ms", 0.0) + (_children_cpu() - c0) * 1e3, 3)


def _children_cpu():
    try:
        import resource
        ru = resource.getrusage(resource.RUSAGE_CHILDREN)
        return ru.ru_utime + ru.ru_stime
    except Exception:
        return 0.0


def all_collectors(readers=None):
    r = readers or Readers()
    return [SessionsCollector(r), AttentionCollector(r), SessionNetCollector(r)]
