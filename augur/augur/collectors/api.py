"""machine.api: are the agents' API calls failing right now? (owner idea 2026-11-01: "truer to the
source" than watching VPN and Wifi.)

Source: Claude Code transcripts, ~/.claude/projects/<slug>/<session>.jsonl and
<slug>/<session>/subagents/*.jsonl. A failed call is an assistant line with
"isApiErrorMessage": true and an "error" word (server_error, unknown, invalid_request, ...); a
successful call is an assistant line from a real model (model != "<synthetic>").

Reading:
- Only the transcript directories of live sessions (shared["transcript_dirs"], from the sessions
  collector) are listed, every RESCAN_S; between rescans only files modified in the last ACTIVE_FILE_S
  are stat'ed. Only bytes appended since the last read are read (offsets kept per file; a first
  sight reads at most TAIL_BYTES from the end). A partial last line waits for its newline. A file
  that shrank or changed inode is read again from its start.
- Only assistant lines are parsed, and only type, timestamp, isApiErrorMessage, error and model are
  kept; the error text is matched in memory to an error_kind and dropped. PRIVACY: no message text,
  path or session id ever leaves this module.

Verdict (provisional):
- failing: an API error in the last ERROR_WINDOW_S and no successful call after it in ANY session.
- ok: a successful call in the last ACTIVE_S, after the last error.
- otherwise ABSENT: idle agents say nothing, which is unmeasured, never "ok".
- error_kind of the newest error: network (ENOTFOUND, ECONNRESET, "Can't reach", connection lost,
  response stopped), rate_limit (429, overloaded, rate limit), server (5xx or server_error
  otherwise), other. Only "network" should drive the Sprites lost-connection huddle.
"""
import encodings.idna  # noqa: F401  RB-m10: loaded now, not lazily by the first getaddrinfo
import json
import os
import re
import socket
import stat
import sys
import threading
import time
from datetime import datetime
from urllib.parse import urlsplit

try:
    from augur.collectors.base import Collector
except ImportError:  # pragma: no cover
    from .base import Collector

ERROR_WINDOW_S = 60.0       # (kept for readers of the old rule; the hold below replaced it)
HOLD_S = 600.0              # R2-3: failing holds until a good call, at most this long
ACTIVE_S = 120.0
PROBE_FAILS = 2             # consecutive failed reachability probes = a network outage
PROBE_TIMEOUT_S = 3.0       # TCP connect timeout
PROBE_BOUND_S = 5.0         # R3-6: a probe still unanswered this long (DNS included) has failed
PROBE_SPACING_S = 15.0      # R3-10: while the transcript shows good calls, probe this sparsely
QUIET_S = 6.0               # ... and every agents tick once it has been silent this long
WALL_STEP_S = 10.0          # RB-m5: |d wall - d mono| beyond this between ticks is a clock step
SESSIONS_FRESH_S = 20.0     # R2-10: transcript_dirs older than this (sessions failing) are unused
ACTIVE_FILE_S = 600.0
RESCAN_S = 30.0
SESSION_LIVE_S = 24 * 3600.0   # a session idle longer than this is not listed for subagents
TAIL_BYTES = 64 * 1024
READ_CAP = 2 * 1024 * 1024
MARK = b'"assistant"'          # cheap prefilter before json.loads
RETRY_MARK = b'"api_error"'    # "type":"system","subtype":"api_error" retry lines (older versions)
BIG = b"\x00BIG\x00"           # prefix of a record over READ_CAP: head + tail only (R2-13)
EDGE = 8192

_NETWORK = re.compile(r"ENOTFOUND|ECONNRESET|ECONNREFUSED|ETIMEDOUT|EAI_AGAIN|EHOSTUNREACH|ENETUNREACH"
                      r"|Can.t reach|Connection lost|connection error|response stopped arriving"
                      r"|socket hang up|fetch failed", re.I)
_RATE = re.compile(r"\b429\b|\b529\b|overloaded|rate.?limit", re.I)
_SERVER = re.compile(r"\b5\d\d\b")


def classify(error, text):
    """network | rate_limit | server | other, from the error word and the message text."""
    t = text if isinstance(text, str) else ("" if text is None else str(text))   # R5-2
    if _NETWORK.search(t):
        return "network"
    if error == "rate_limit" or _RATE.search(t):
        return "rate_limit"
    if error == "server_error" or _SERVER.search(t):
        return "server"
    return "other"


def _epoch(ts):
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def _str_end(b, i):
    """Index of the closing quote of the JSON string opening at b[i], or -1 if cut off."""
    j, n = i + 1, len(b)
    while j < n:
        c = b[j]
        if c == 0x5C:
            j += 2
            continue
        if c == 0x22:
            return j
        j += 1
    return -1


def _head_pairs(b):
    """R5-1: the scalar key/value pairs of a JSON object's PREFIX, with their nesting: a dict
    {(enclosing keys..., key): value}. Exact on a prefix (string state is known from the start).
    Only the top level and message.model are asked for."""
    out = {}
    stack = []           # frames: [is_object, current_key, expecting_key]
    i, n = 0, len(b)
    while i < n:
        c = b[i]
        if c == 0x22:
            j = _str_end(b, i)
            if j < 0:
                break
            tok = b[i:j + 1]
            i = j + 1
            if stack and stack[-1][0] and stack[-1][2]:
                try:
                    stack[-1][1] = json.loads(tok)
                except ValueError:
                    break
            elif stack and stack[-1][0]:
                try:
                    out[tuple(f[1] for f in stack)] = json.loads(tok)
                except ValueError:
                    break
            continue
        if c in (0x7B, 0x5B):
            stack.append([c == 0x7B, None, c == 0x7B])
            if len(stack) > 3:
                break                    # deeper than anything asked for
        elif c in (0x7D, 0x5D):
            if not stack:
                break
            stack.pop()
        elif c == 0x2C:
            if stack and stack[-1][0]:
                stack[-1][2] = True
        elif c == 0x3A:
            if stack and stack[-1][0]:
                stack[-1][2] = False
        elif c in b"tfn-0123456789" and stack and stack[-1][0] and not stack[-1][2]:
            m = re.match(rb"true|false|null|-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", b[i:i + 40])
            if not m:
                break
            out[tuple(f[1] for f in stack)] = json.loads(m.group(0))
            i += len(m.group(0))
            continue
        i += 1
    return out


def _tail_top(b):
    """R5-1: the top-level members of a JSON object's SUFFIX (the record's last bytes), parsed
    from the last top-level comma reachable by a backward scan (string state is exact from the
    end). {} when none is reachable."""
    depth, ins, best = 0, False, None
    i = len(b) - 1
    while i >= 0 and b[i] in b" \r\t":
        i -= 1
    while i >= 0:
        c = b[i]
        if c == 0x22:
            k, bs = i - 1, 0
            while k >= 0 and b[k] == 0x5C:
                bs, k = bs + 1, k - 1
            if bs % 2 == 0:
                ins = not ins
        elif not ins:
            if c in (0x7D, 0x5D):
                depth += 1
            elif c in (0x7B, 0x5B):
                depth -= 1
                if depth == 0:
                    best = i
                    break
            elif c == 0x2C and depth == 1:
                best = i
        i -= 1
    if best is None:
        return {}
    try:
        d = json.loads(b"{" + b[best + 1:])
    except (ValueError, RecursionError):
        return {}
    return d if isinstance(d, dict) else {}


def _parse_big(raw):
    """A record too large to load: decide from its head and tail bytes, TOP-LEVEL evidence only
    (R5-1): the record's own type, timestamp, isApiErrorMessage and error (from the head's or the
    tail's top level), and message.model from the head. A flag or timestamp nested in a payload
    (tool input, text) is no evidence."""
    if MARK not in raw:
        return None
    head, _, tail = raw.partition(b"\n")
    hp = _head_pairs(head)
    top = {k[0]: v for k, v in hp.items() if len(k) == 1}
    top.update({k: v for k, v in _tail_top(tail).items()
                if not isinstance(v, (dict, list))})
    if top.get("type") != "assistant":
        return None
    t = _epoch(top.get("timestamp"))
    if t is None:
        return None
    if top.get("isApiErrorMessage") is True:
        return classify(top.get("error"), ""), t
    model = hp.get(("message", "model"))
    if not isinstance(model, str) or not model or model == "<synthetic>":
        return None
    return "ok", t


def parse_line(raw):
    """(kind, epoch) for an assistant line: kind "ok" or an error_kind; for a retry line
    ("system"/"api_error") an error_kind; None for anything else. Total (R5-2, S2): a line of
    any shape, or too deep to load, is None, never an exception."""
    try:
        return _parse_line(raw)
    except Exception:  # noqa: BLE001  untrusted input: no shape may abort the batch
        return None


def _parse_line(raw):
    if raw.startswith(BIG):
        return _parse_big(raw[len(BIG):])
    retry = RETRY_MARK in raw
    if MARK not in raw and not retry:
        return None
    try:
        d = json.loads(raw)
    except (ValueError, RecursionError):
        return None
    if retry and isinstance(d, dict) and d.get("type") == "system" and d.get("subtype") == "api_error":
        t = _epoch(d.get("timestamp"))
        if t is None:
            return None
        return classify(None, json.dumps(d.get("error"))[:2000]), t
    if not isinstance(d, dict) or d.get("type") != "assistant":
        return None
    t = _epoch(d.get("timestamp"))
    if t is None:
        return None
    m = d.get("message") if isinstance(d.get("message"), dict) else {}
    if d.get("isApiErrorMessage") is True:
        text = ""
        c = m.get("content")
        if isinstance(c, list) and c and isinstance(c[0], dict):
            text = c[0].get("text") or ""
        elif isinstance(c, str):
            text = c
        return classify(d.get("error"), text), t
    model = m.get("model")
    if not isinstance(model, str) or not model or model == "<synthetic>":
        return None                       # R2-11: no model, no evidence of a good call
    return "ok", t


class NotRegular(OSError):
    """S1: a transcript path that is not a regular file (a FIFO, a device, a symlink)."""


def _open_regular(path):
    """S1: open without blocking (a FIFO's open would wait for a writer forever) and without
    following a symlink; refuse anything that is not a regular file."""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise NotRegular("not a regular file")
        return os.fdopen(fd, "rb"), st
    except BaseException:
        os.close(fd)
        raise


class Tail(object):
    """Appended-bytes reader for one file."""

    def __init__(self):
        self.off = None
        self.ino = None
        self.size = 0          # the size fstat gave on the last read
        self.skip = False      # the read starts mid-record: drop up to its newline
        self.big = None        # [head, tail] of a record longer than READ_CAP being skipped
        self.fp = b""          # the bytes just before off: a rewrite in place is detected (R2-5)

    def read(self, path, st=None):
        fh, st = _open_regular(path)
        self.size = st.st_size
        with fh:
            if self.off is not None and st.st_ino == self.ino and st.st_size >= self.off and self.fp:
                fh.seek(self.off - len(self.fp))
                if fh.read(len(self.fp)) != self.fp:
                    self.off = 0                  # truncated and regrown on the same inode
                    self.skip, self.big, self.fp = False, None, b""
            if self.off is None or st.st_ino != self.ino or st.st_size < self.off:
                first = self.off is None
                self.ino = st.st_ino
                self.off = max(0, st.st_size - TAIL_BYTES) if first else 0
                self.skip, self.big, self.fp = False, None, b""     # R5-3: fp goes with off
                if self.off > 0:                  # R2-14: on a record boundary, keep it
                    fh.seek(self.off - 1)
                    self.skip = fh.read(1) != b"\n"
            if st.st_size <= self.off:
                return []
            fh.seek(self.off)
            data = fh.read(min(st.st_size - self.off, READ_CAP))
        out = []
        if self.skip or self.big is not None:
            i = data.find(b"\n")
            if i < 0:
                if self.big is not None:
                    self.big[1] = (self.big[1] + data)[-EDGE:]
                self._advance(data, len(data))
                return []
            if self.big is not None:              # R2-13: the huge record ends here
                out.append(BIG + self.big[0] + b"\n" + (self.big[1] + data[:i])[-EDGE:])
            self._advance(data, i + 1)
            data = data[i + 1:]
            self.skip, self.big = False, None
        end = data.rfind(b"\n")
        if end < 0:
            if len(data) >= READ_CAP:
                self.big = [data[:EDGE], data[-EDGE:]]
                self._advance(data, len(data))
            return out         # a partial last line: wait for its newline
        self._advance(data, end + 1)
        return out + data[:end].split(b"\n")

    def _advance(self, data, n):
        self.off += n
        self.fp = (self.fp + data[:n])[-32:]


def _ppid_default(pid):
    """A process's parent pid (libproc on macOS, /proc on Linux); None when unreadable."""
    if sys.platform == "darwin":
        from augur.darwin import native
        bi = native.bsdinfo(pid)
        return bi[0] if bi else None
    try:
        with open("/proc/%d/stat" % int(pid), "rb") as fh:
            return int(fh.read().rsplit(b")", 1)[1].split()[1])
    except (OSError, ValueError, IndexError):
        return None


def _env_var_default(pid, name):
    """A process's environment variable at exec: KERN_PROCARGS2 on macOS, /proc on Linux."""
    if sys.platform == "darwin":
        from augur.darwin import native
        return native.env_var(pid, name)
    try:
        with open("/proc/%d/environ" % int(pid), "rb") as fh:
            for kv in fh.read().split(b"\0"):
                if kv.startswith(name.encode() + b"="):
                    return kv[len(name) + 1:].decode("utf-8", "replace")
    except OSError:
        pass
    return None


def _port_of(url):
    """R3-4: the URL's own port, else the scheme's (https 443, http 80)."""
    u = urlsplit(url)
    return u.port or (80 if u.scheme == "http" else 443)


def _reach_url(url, timeout=PROBE_TIMEOUT_S):
    """Resolve and TCP-connect to the URL's host and port (no TLS, no bytes sent). True or
    raises. Name resolution has no timeout of its own; the caller bounds the whole probe."""
    with socket.create_connection((urlsplit(url).hostname, _port_of(url)), timeout=timeout):
        return True


def _url_ok(url):
    """R4-11: a usable base URL has an http(s) scheme, a host and a valid port."""
    try:
        u = urlsplit(url)
        _ = u.port
    except (ValueError, TypeError, AttributeError):
        return False
    return u.scheme in ("http", "https") and bool(u.hostname)


class _Probe(object):
    """Reachability state for one in-use base URL. Times: *_mono on ctx.mono (spacing, hold),
    started on the collector's own mono (the bound); *_wall are published epochs."""

    def __init__(self):
        self.fails = 0          # consecutive failed probes
        self.fail_since = None  # wall epoch of the first failure of the run (R4-5b, vs transcript)
        self.err_wall = None    # wall epoch of the newest failed probe in a failure run
        self.err_mono = None    # ... on ctx.mono, for the R3-5 hold
        self.ok_wall = None     # wall epoch of the newest good probe
        self.last_mono = None   # ctx.mono when the last probe started
        self.thread = None      # the in-flight worker
        self.token = None       # its token; a result is accepted only under the current token
        self.started = None     # collector mono() when it started
        self.result = None      # (token, outcome, wall epoch) published by the worker
        self.hung = None        # R5-8: the one abandoned worker, while it is still alive
        self.fault = False      # RB-m10: the last outcome was an internal fault, not evidence


class ApiCollector(Collector):
    """See the module doc. R2-3: Claude Code retries a failing call silently for ~3 min before it
    writes the error line (measured: median 182 s, p10 174 s), so the transcript alone shows an
    outage minutes late. While any session is busy, the collector also checks that each API host
    the busy sessions actually use resolves and accepts a TCP connection. R5-10: that host is the
    ANTHROPIC_BASE_URL in the session's own process environment (its children carry it; it is
    fixed when the session starts), never ~/.claude/settings.json, which names the NEXT session's
    account. PROBE_FAILS consecutive failures of any one host read failing with error_kind
    network. A probe still unanswered after PROBE_BOUND_S (a hanging resolver) counts as failed,
    so the bound is ~2 x PROBE_BOUND_S plus a tick; a result that completed between polls (say at
    5.5 s, read at 6 s) is still taken as the answer (R5-15). Evidence precedence (R3-3): a
    transcript error clears only on a later good assistant line (or ages out at HOLD_S); a good
    probe clears only probe-made failure. The probe only raises failing; with no transcript
    evidence it cannot by itself make "ok". With no usable URL, or a probe fault, the transcript
    verdict stands as it would while idle (R5-12); only with no transcript verdict does the
    reason (env_missing, env_invalid, read_failed) show."""
    name = "api"
    tier = "agents"
    platforms = ("darwin", "linux")
    signals = ("machine.api",)

    def __init__(self, clock=time.time, resolver=None, base_url=None, reach=None, mono=time.monotonic,
                 env_var=None, ppid=None):
        self.clock = clock
        self.tails = {}        # path -> Tail
        self.files = {}        # path -> session key (the top-level transcript's stem)
        self.scanned = {}      # dir -> time of the last listing
        self.last = {}         # session key -> {"err": (t, seq, kind), "ok": (t, seq)}
        self.seq = 0
        self.resolver = resolver
        self.base_url = base_url   # tests: one URL (or None) instead of the sessions' environments
        self.env_var = env_var or _env_var_default
        self.ppid = ppid or _ppid_default
        self.reach = reach or _reach_url
        self.mono = mono       # R4-4: the probe bound is measured on the monotonic clock
        self._probes = {}      # url -> _Probe
        self._pid_env = {}     # (sid, pid) -> (ppid, URL or None), read once per pid (R6 F1)
        self._lock = threading.Lock()
        self._clk = None       # (wall, ctx.mono) of the previous tick (RB-m5)
        self._env_logged = False
        self._fault_logged = False
        self._hung_logged = False
        self._worker_cpu = 0.0

    @property
    def fails(self):
        """The worst consecutive-failure count over the in-use hosts."""
        return max([p.fails for p in self._probes.values()] or [0])

    def drain_worker_cpu(self):
        """R3-7: the probe thread's CPU, for the core's per-line meter."""
        with self._lock:
            v, self._worker_cpu = self._worker_cpu, 0.0
        return v

    def _list(self, d, now):
        try:
            it = os.scandir(d)
        except OSError:
            return
        with it:
            for e in it:
                try:
                    if e.name.endswith(".jsonl") and e.is_file(follow_symlinks=False):    # S1
                        if now - e.stat().st_mtime <= ACTIVE_FILE_S:
                            self.files.setdefault(e.path, e.name[:-6])
                    elif e.is_dir(follow_symlinks=False):
                        # a dir's mtime moves only when entries are added, not when a file in
                        # it grows: list the subagents of every session whose transcript or
                        # session dir changed within SESSION_LIVE_S
                        top = os.path.join(d, e.name + ".jsonl")
                        try:
                            tm = os.stat(top).st_mtime
                        except OSError:
                            tm = e.stat().st_mtime
                        if now - tm > SESSION_LIVE_S:
                            continue
                        with os.scandir(os.path.join(e.path, "subagents")) as sub:
                            for s in sub:
                                if s.name.endswith(".jsonl") and s.is_file(follow_symlinks=False) \
                                        and now - s.stat().st_mtime <= ACTIVE_FILE_S:
                                    self.files.setdefault(s.path, e.name)
                except OSError:
                    continue

    # ---- reachability probe (R2-3)
    def _busy(self, ctx):
        """The pids of the busy sessions."""
        out = []
        for pid in (ctx.shared.get("session_ids_by_pid") or {}):
            try:
                with open(os.path.join(ctx.home, ".claude", "sessions", "%d.json" % int(pid)),
                          encoding="utf-8") as fh:
                    if (json.load(fh) or {}).get("status") == "busy":
                        out.append(int(pid))
            except (OSError, ValueError, AttributeError, TypeError):
                continue
        return out

    def _urls(self, ctx, pids):
        """R5-10: the distinct ANTHROPIC_BASE_URL values the busy sessions run with, read from
        each session's own processes. R6 F1: only the root and its direct children (the MCP
        servers and shell snapshot shells Claude Code spawns) count, never deeper descendants
        (a tool command may set its own); a source that exits stops counting; and when those
        disagree the session is unscoped (no URL: the transcript stands)."""
        if self.base_url is not None:
            u = self.base_url()
            return [u] if u else []
        ids = ctx.shared.get("session_ids_by_pid") or {}
        trees = ctx.shared.get("session_trees") or {}
        live = set(trees) | set(ids.values())
        self._pid_env = {k: v for k, v in self._pid_env.items()
                         if k[0] in live and k[1] in (trees.get(k[0]) or ())}
        urls = []
        for pid in pids:
            sid = ids.get(pid)
            if sid is None:
                continue
            vals = set()
            for q in (trees.get(sid) or [pid]):
                e = self._pid_env.get((sid, q))
                if e is None:
                    try:
                        pp = self.ppid(q)
                    except Exception:  # noqa: BLE001  unreadable: not known to be a child
                        pp = None
                    v = None
                    if q == pid or pp == pid:
                        try:
                            v = self.env_var(q, "ANTHROPIC_BASE_URL")
                        except Exception:  # noqa: BLE001  an unreadable process is no URL
                            v = None
                    v = v.strip() if isinstance(v, str) and v.strip() else None
                    e = self._pid_env[(sid, q)] = (pp, v)
                if e[1] and (q == pid or e[0] == pid):
                    vals.add(e[1])
            u = vals.pop() if len(vals) == 1 else None
            if u and u not in urls:
                urls.append(u)
        return urls

    @staticmethod
    def _url_ok(url):
        return _url_ok(url)

    def _probe(self, p, url, now, due):
        """(outcome, wall epoch) for a probe result this tick, or None for no new result.
        outcome: True reachable, False unreachable (an OSError, a timeout, or the bound),
        "fault" an internal error (RB-m10). R5-9: the worker publishes (token, outcome, epoch)
        under the lock, and the drain and the abandonment happen under that one lock, so a
        result is counted once and a stale worker's answer can never be read. R5-8: at most one
        abandoned worker per host; while it is alive a due probe counts as failed (R3-6: a
        hanging resolver is an outage) without starting another thread."""
        if self.resolver is not None:            # tests: synchronous resolver
            if not due:
                return None
            try:
                self.resolver(urlsplit(url).hostname)
                return True, now
            except OSError:
                return False, now
            except Exception:  # noqa: BLE001
                return "fault", now
        m = self.mono()                          # never under the lock (tests' mono may join)
        abandoned = False
        with self._lock:
            res, p.result = p.result, None
            if res is not None and res[0] != p.token:
                res = None                       # not the current worker's: dropped
            if res is None and p.token is not None and m - p.started >= PROBE_BOUND_S:
                p.hung, p.thread, p.token, p.started = p.thread, None, None, None
                abandoned = True                 # its late answer can no longer match a token
        if res is not None:
            p.thread, p.token, p.started = None, None, None
            return res[1], res[2]
        if abandoned:
            return False, now
        if p.token is not None or not due:
            return None
        if p.hung is not None:
            if p.hung.is_alive():
                if not self._hung_logged:
                    self._hung_logged = True
                    sys.stderr.write("augur: api probe: a worker is hung in name resolution; "
                                     "counting due probes as failed, no new thread\n")
                return False, now
            p.hung = None
        self._hung_logged = False
        token = object()
        clk, reach = self.clock, self.reach

        def work():
            t0 = time.thread_time()
            try:
                out = bool(reach(url, PROBE_TIMEOUT_S))
            except OSError:                      # socket.timeout and gaierror are OSErrors
                out = False
            except Exception:  # noqa: BLE001  RB-m10: our fault, not the network's
                out = "fault"
            with self._lock:
                self._worker_cpu += time.thread_time() - t0
                if p.token is token:
                    p.result = (token, out, clk())
        th = threading.Thread(target=work, name="augur-api-probe", daemon=True)
        with self._lock:
            p.token, p.started, p.thread = token, m, th
        th.start()
        return None

    def _rebase(self, d):
        """RB-m5: the wall clock stepped by d (< 0) between two ticks. Shift every stored wall
        time by d so transcript lines written on the new clock compare correctly with older
        ones and nothing freezes until the clock catches up."""
        for r in self.last.values():
            if r["ok"]:
                r["ok"] = (r["ok"][0] + d, r["ok"][1])
            if r["err"]:
                r["err"] = (r["err"][0] + d,) + tuple(r["err"][1:])
        for k in self.scanned:
            self.scanned[k] += d
        for p in self._probes.values():
            for f in ("fail_since", "err_wall", "ok_wall"):
                if getattr(p, f) is not None:
                    setattr(p, f, getattr(p, f) + d)
            p.last_mono = None                   # re-measure at once

    def collect(self, ctx):
        now = ctx.now
        mono = getattr(ctx, "mono", now)
        if self._clk is not None:
            d = (now - self._clk[0]) - (mono - self._clk[1])
            if d < -WALL_STEP_S:
                self._rebase(d)
        self._clk = (now, mono)
        sm = ctx.shared.get("sessions_mono")
        if sm is None or mono - sm > SESSIONS_FRESH_S:
            return {}          # R2-10: the session list is not current: unmeasured
        dirs = set((ctx.shared.get("transcript_dirs") or {}).values())
        for d in dirs:
            if now - self.scanned.get(d, -1e18) >= RESCAN_S:
                self.scanned[d] = now
                self._list(d, now)
        for d in [d for d in self.scanned if d not in dirs]:
            del self.scanned[d]
        for path in list(self.files):
            if os.path.dirname(path) not in dirs and \
                    os.path.dirname(os.path.dirname(os.path.dirname(path))) not in dirs:
                self.files.pop(path, None)
                self.tails.pop(path, None)
                continue
            try:
                st = os.stat(path)
            except OSError:
                self.files.pop(path, None)
                self.tails.pop(path, None)
                continue
            if now - st.st_mtime > ACTIVE_FILE_S:
                self.files.pop(path, None)
                self.tails.pop(path, None)
                continue
            tail = self.tails.setdefault(path, Tail())
            lines = []
            try:
                for _ in range(4):           # up to 4 x READ_CAP per file per tick (R2-13)
                    lines += tail.read(path)
                    if tail.off >= tail.size:
                        break
            except NotRegular:
                self.files.pop(path, None)   # S1: never a transcript
                self.tails.pop(path, None)
                continue
            except OSError:
                continue
            sk = self.files[path]
            for raw in lines:
                r = parse_line(raw)          # total (R5-2, S2): one bad line drops only itself
                if r is None:
                    continue
                kind, t = r
                self.seq += 1          # R2-15: on equal timestamps the later line wins
                rec = self.last.setdefault(sk, {"err": None, "ok": None})
                if kind == "ok":
                    if rec["ok"] is None or (t, self.seq) > rec["ok"]:
                        rec["ok"] = (t, self.seq)
                elif rec["err"] is None or (t, self.seq) > rec["err"][:2]:
                    rec["err"] = (t, self.seq, kind)
        for k in [k for k, r in self.last.items()
                  if max([(r["ok"] or (0.0,))[0], (r["err"] or (0.0,))[0]]) < now - HOLD_S]:
            del self.last[k]
        probe_unknown = None
        busy = self._busy(ctx)
        if busy:
            urls = self._urls(ctx, busy)
            good = [u for u in urls if _url_ok(u)]
            if not good:
                # owner rule: a missing or broken account variable fails loudly by name, never
                # a default (R4-5a); it blocks only the PROBE, never the transcript verdict
                probe_unknown = "env_missing" if not urls else "env_invalid"
                if self._env_logged != probe_unknown:
                    self._env_logged = probe_unknown
                    sys.stderr.write("augur: api probe: ANTHROPIC_BASE_URL is %s in the busy "
                                     "sessions' environment; probe off (%s)\n"
                                     % ("not set" if not urls else "not a usable http(s) URL",
                                        probe_unknown))
            else:
                self._env_logged = False
            oks = [r["ok"][0] for r in self.last.values() if r["ok"]]
            fresh_ok = bool(oks) and now - max(oks) < QUIET_S
            for u in good:
                p = self._probes.setdefault(u, _Probe())
                due = p.last_mono is None or mono - p.last_mono >= \
                    (PROBE_SPACING_S if fresh_ok and p.fails == 0 else 0.0)
                if due and p.token is None:
                    p.last_mono = mono
                r = self._probe(p, u, now, due)
                if r is None:
                    continue
                ok, at = r
                if ok == "fault":
                    p.fault = True
                    if not self._fault_logged:
                        self._fault_logged = True
                        sys.stderr.write("augur: api probe: internal fault in the probe worker "
                                         "(not network evidence); read_failed\n")
                    continue
                p.fault = False
                if ok:
                    p.fails, p.ok_wall, p.fail_since = 0, at, None
                else:
                    if p.fails == 0:
                        p.fail_since = at
                    p.fails += 1
                    if p.fails >= PROBE_FAILS:
                        p.err_wall, p.err_mono = at, mono
            for u in [u for u in self._probes if u not in good]:
                q = self._probes[u]
                if q.hung is not None and q.hung.is_alive():
                    q.fails, q.fail_since = 0, None      # kept only to cap its threads (R5-8)
                else:
                    del self._probes[u]
            if good and all(self._probes[u].fault for u in good):
                probe_unknown = "read_failed"
            elif good:
                self._fault_logged = False
        else:
            for p in self._probes.values():
                p.fails = 0
        oks = [r["ok"][0] for r in self.last.values() if r["ok"]]
        for p in self._probes.values():
            # R4-5b: a good call (direct evidence) after a probe-made outage clears it
            if p.fails >= PROBE_FAILS and oks and p.fail_since is not None and \
                    max(oks) >= p.fail_since:
                p.fails, p.fail_since = 0, None
            if p.fails >= PROBE_FAILS and p.err_mono is not None and mono - p.err_mono > HOLD_S:
                p.fails = 0                      # R3-5: an outage with no new probe ages out
        out = self._verdict(now)
        if probe_unknown and not out:
            return {"machine.api": {"unknown": probe_unknown}}
        return out

    def _verdict(self, now):
        oks = [r["ok"] for r in self.last.values() if r["ok"]]
        last_ok = max(oks) if oks else None
        out_p = [p for p in self._probes.values() if p.fails >= PROBE_FAILS]
        outage = bool(out_p)
        failing, kinds = [], []
        for r in self.last.values():
            e = r["err"]
            if not e or now - e[0] > HOLD_S or (r["ok"] is not None and r["ok"] > e[:2]):
                continue
            if last_ok is not None and last_ok > e[:2]:
                continue       # a good call since, in any session (by spec)
            failing.append(e)
            kinds.append(e[2])
        errs = [r["err"] for r in self.last.values() if r["err"]]
        last_err = max(errs) if errs else None
        n_failing = sum(1 for r in self.last.values() if r["err"] and now - r["err"][0] <= HOLD_S
                        and (r["ok"] is None or r["ok"] < r["err"][:2]))
        v = {"failing_sessions": n_failing, "provisional": True}
        if outage:
            v["last_error_at"] = round(max(p.err_wall for p in out_p), 3)
        elif last_err is not None:
            v["last_error_at"] = round(last_err[0], 3)
        if last_ok is not None:
            v["last_ok_at"] = round(last_ok[0], 3)
        if outage or failing:
            v["state"] = "failing"
            # R2-4: network wins: one session's HTTP 400 must not mask another's lost link
            v["error_kind"] = "network" if (outage or "network" in kinds) else max(failing)[2]
        elif last_ok is not None and now - last_ok[0] <= ACTIVE_S:
            v["state"] = "ok"
            if last_err is not None:
                v["error_kind"] = last_err[2]
        else:
            return {}          # no call in the window: unmeasured, absent
        return {"machine.api": v}
