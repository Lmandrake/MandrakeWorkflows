"""Augur's core (DESIGN.md section 4): tiers, stamping, absent and unknown, the atomic write,
the self-cost meter, the off switch.

One scheduler thread runs every tier in order (agents, fast, probes, counts) at the fast cadence,
raised to USER_INITIATED QoS for the tick (DESIGN section 8: Background QoS starved at 100 % busy).
Workers that may block (the path echo burst) live in their collectors on their own threads.

Rules carried out here:
- A collector that raises gets every one of its signals marked {"unknown": "read_failed"}, stamped
  now: never its previous value.
- A disabled collector (collectors.json, or cut by the cost meter) reads {"unknown": "disabled"};
  session_net is the exception: switched off, sessions[].net is ABSENT (DESIGN section 5).
- valid_until = observed_at + 2.5 x the tier's cadence; the file's own valid_until = written_at +
  5 x the fast cadence.
- Low Power Mode stops the probes tier (except lpm_exempt collectors): its signals read
  {"unknown": "disabled"}. On battery the tiers slow to fast 5 s, agents 15 s, probes 30 s.
"""

import collections
import ctypes
import json
import os
import resource
import socket
import subprocess
import sys
import time

SCHEMA = "augur.snapshot"
VERSION = "1.2"   # 1.2: sessions[].headless/parent, on_site description. 1.1 (C1): tasks.background, sessions_at, counts.as_of, and the
                  # keys 1.0 builds added unannounced (machine.api, bg_shells, other, load.method)
TIER_ORDER = ("agents", "fast", "probes", "counts")
CADENCE_AC = {"fast": 2.0, "agents": 5.0, "probes": 15.0, "counts": 60.0}
CADENCE_BATTERY = {"fast": 5.0, "agents": 15.0, "probes": 30.0, "counts": 60.0}
STAMP_FACTOR = 2.5
FILE_FACTOR = 5.0
OFF_RECHECK_S = 5.0
SAMPLE_EVERY_S = 60.0
COST_LOG_EVERY_S = 600.0
HOUR = 3600.0
SAMPLES_KEEP_DAYS = 14      # samples/snap-<day>.jsonl older than this are deleted at rollover (S3)
LOG_KEEP_DAYS = 7           # cost.jsonl / audit.jsonl lines older than this go at rollover
LOG_MAX_BYTES = 8 << 20     # and either log over this is cut to its newest lines at once
LOGS = ("cost.jsonl", "audit.jsonl")
ERR_REPEAT_S = 600.0        # an identical error line is written at most once per this (RB-m9)
PRIVATE_FILE, PRIVATE_DIR = 0o600, 0o700   # S3: every output is the owner's only
SLEEP_JUMP_S = 10.0         # wall clock ahead of monotonic by this much between ticks = the
                            # system slept (mach_absolute_time stops in sleep, time.time does not)

# DESIGN section 6 budget, percent of one core over 1 h
BUDGET_TOTAL = 1.0
FAIL_TOTAL = 2.0
BUDGET_LINES = {"fast": 0.15, "agents": 0.40, "probes": 0.25, "counts": 0.10, "write": 0.10}
BUDGET_RSS_MB = 40.0
BUDGET_SPAWNS_H = 1500
FAIL_MIN_WINDOW_S = 600.0   # never cut a collector on less than 10 min of evidence
QOS_USER_INITIATED = 0x19

# Collectors whose switched-off state is ABSENT rather than unknown "disabled".
ABSENT_WHEN_OFF = {"session_net"}


# --------------------------------------------------------------------------- spawn counting

_SPAWNS = [0]
_RealPopen = subprocess.Popen


class _CountingPopen(_RealPopen):
    def __init__(self, *a, **k):
        _SPAWNS[0] += 1
        super().__init__(*a, **k)


def install_spawn_counter():
    """Count every subprocess this process starts (the nettop execs): DESIGN section 6 spawns/h."""
    subprocess.Popen = _CountingPopen


def spawns():
    return _SPAWNS[0]


# --------------------------------------------------------------------------- helpers

def _cpu_self_children():
    s = resource.getrusage(resource.RUSAGE_SELF)
    c = resource.getrusage(resource.RUSAGE_CHILDREN)
    return s.ru_utime + s.ru_stime, c.ru_utime + c.ru_stime, s.ru_maxrss


def _current_rss():
    """This process's resident size now, bytes (proc_pid_rusage ri_resident_size, rusage_info_v4
    u64 slot 8); None when unreadable. R2-9: the budget is judged on this, not on ru_maxrss."""
    try:
        from augur.darwin import native
        buf = (ctypes.c_uint64 * 64)()
        if native._proc_fast().proc_pid_rusage(os.getpid(), 4, buf) != 0:
            return None
        return int(buf[8])
    except Exception:  # noqa: BLE001
        return None


def _rss_mb(maxrss):
    # macOS reports ru_maxrss in bytes, Linux in KB
    return maxrss / 1e6 if sys.platform == "darwin" else maxrss / 1e3


def git_rev(repo_dir):
    """Short sha of HEAD read from .git files (no spawn); '0000000' when unreadable."""
    try:
        g = os.path.join(repo_dir, ".git")
        if os.path.isfile(g):  # a worktree: "gitdir: <path>"
            with open(g) as fh:
                g = fh.read().split(":", 1)[1].strip()
        with open(os.path.join(g, "HEAD")) as fh:
            head = fh.read().strip()
        if head.startswith("ref:"):
            ref = head.split(None, 1)[1]
            p = os.path.join(g, ref)
            if os.path.exists(p):
                with open(p) as fh:
                    return fh.read().strip()[:7]
            common = g
            cd = os.path.join(g, "commondir")
            if os.path.exists(cd):
                with open(cd) as fh:
                    common = os.path.normpath(os.path.join(g, fh.read().strip()))
            p = os.path.join(common, ref)
            if os.path.exists(p):
                with open(p) as fh:
                    return fh.read().strip()[:7]
            with open(os.path.join(common, "packed-refs")) as fh:
                for line in fh:
                    if line.strip().endswith(ref):
                        return line.split()[0][:7]
        return head[:7]
    except (OSError, IndexError):
        return "0000000"


def machine_key():
    k = (os.environ.get("LODESTAR_MACHINE") or "").strip().lower()
    return k or socket.gethostname().split(".")[0].lower()


def find_lodestar(home):
    p = os.environ.get("AUGUR_LODESTAR")
    if p is not None:
        return p if p and os.path.isdir(p) else None
    p = os.path.join(home, "dev", "Lodestar")
    return p if os.path.isdir(p) else None


def _write_all(fd, data):
    """os.write until every byte is out (a short write would publish truncated JSON)."""
    view = memoryview(data)
    while view:
        n = os.write(fd, view)
        if n <= 0:
            raise OSError("short write")
        view = view[n:]


def write_atomic(path, data, mode=PRIVATE_FILE):
    """A fresh temp file from mkstemp (O_EXCL, never a planted name or symlink: S5 N1), fchmod on
    the fd (never a path that could be a link), fsync, os.replace (which replaces a link at
    `path` rather than following it)."""
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".",
                               prefix=os.path.basename(path) + ".tmp.")
    try:
        try:
            os.fchmod(fd, mode)
            _write_all(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def append_line(path, rec, mode=PRIVATE_FILE):
    """One JSON line. O_NOFOLLOW (a link at `path` is refused, S5 N1); the mode is enforced on an
    existing file too (N2); a torn tail from an earlier failed append gets its newline first, and
    a failed write is truncated back to where it started, so no record is glued to another
    (RB-m11)."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, mode)
    try:
        st = os.fstat(fd)
        if st.st_mode & 0o777 != mode:
            os.fchmod(fd, mode)
        start = st.st_size
        data = (json.dumps(rec, separators=(",", ":")) + "\n").encode()
        if start and os.pread(fd, 1, start - 1) != b"\n":
            data = b"\n" + data
        try:
            _write_all(fd, data)
        except BaseException:
            try:
                os.ftruncate(fd, start)
            except OSError:
                pass
            raise
    finally:
        os.close(fd)


def err_text(err):
    """An exception as its type name and errno only: str(OSError) carries a path (S5 N3)."""
    no = getattr(err, "errno", None)
    return type(err).__name__ + (" errno %d" % no if isinstance(no, int) else "")


def _last_hour_slot(path):
    """The wall-clock hour (epoch // 3600) of the newest 1 h line in cost.jsonl, or None."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 65536))
            tail = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    for line in reversed(tail):
        if '"window":"1h"' in line:
            try:
                return int(float(json.loads(line)["t"]) // HOUR)
            except (ValueError, KeyError, TypeError):
                continue
    return None


def set_thread_qos(qos):
    try:
        ctypes.CDLL("/usr/lib/libSystem.dylib").pthread_set_qos_class_self_np(qos, 0)
    except (OSError, AttributeError):
        pass


def _tasks_v11(t):
    """C1: `total` keeps its 1.0 meaning (shells + subagents, DESIGN s11); the background count
    that 2d093a3 put under `total` is published as `background` (bg_shells + subagents +
    other). A stamp carrying `unknown` is left alone (no value keys)."""
    if "unknown" in t:
        return t
    out = dict(t)
    if isinstance(t.get("total"), int) and all(isinstance(t.get(k), int)
                                               for k in ("bg_shells", "subagents", "other")):
        out["background"] = t["bg_shells"] + t["subagents"] + t["other"]
    if isinstance(t.get("shells"), int) and isinstance(t.get("subagents"), int):
        out["total"] = t["shells"] + t["subagents"]
    else:
        out.pop("total", None)              # its 1.0 meaning is unmeasured: absent
    return out


# --------------------------------------------------------------------------- context

class Ctx(object):
    def __init__(self, core, state):
        self.now = core.clock()
        self.mono = core.mono()
        self.cadence = dict(core.cadence)
        self.state = state
        self.shared = core.shared
        self.home = core.home
        self.storage = core.storage
        self.lodestar = core.lodestar


# --------------------------------------------------------------------------- cost meter

class CostMeter(object):
    """Rolling 60 s / 1 h windows of the whole producer (self + reaped children) and per-line
    CPU (thread CPU + children delta across each collect()). Lines are tiers plus "write"."""

    def __init__(self, mono, cpu_reader=_cpu_self_children, rss_reader=None):
        self.mono = mono
        self.read = cpu_reader
        self.read_rss = rss_reader if rss_reader is not None else (
            _current_rss if cpu_reader is _cpu_self_children else (lambda: None))
        self.rss_peak_mb = 0.0
        self.t0 = mono()
        self.whole = collections.deque()          # (mono, total_cpu_s)
        self.buckets = collections.OrderedDict()  # minute index -> {("line"|"coll", name): cpu_s}
        self.spawn_marks = collections.deque()    # (mono, spawn counter)
        self.late = collections.deque()           # (mono, lateness_s) for fast ticks
        self.line_of = {}                         # collector -> line
        self.rss_mb = 0.0
        self.sample()

    def sample(self):
        now = self.mono()
        s, c, maxrss = self.read()
        self.whole.append((now, s + c))
        self.rss_peak_mb = _rss_mb(maxrss)
        cur = self.read_rss()
        self.rss_mb = cur / 1e6 if cur is not None else self.rss_peak_mb
        self.spawn_marks.append((now, spawns()))
        # keep the newest point older than the hour: a gap longer than the window still has a base
        while len(self.whole) > 2 and now - self.whole[1][0] > HOUR:
            self.whole.popleft()
        while self.spawn_marks and now - self.spawn_marks[0][0] > HOUR + 60:
            self.spawn_marks.popleft()
        cutoff = int((now - HOUR) // 60)
        while self.buckets and next(iter(self.buckets)) < cutoff:
            self.buckets.popitem(last=False)
        while self.late and now - self.late[0][0] > HOUR:
            self.late.popleft()

    def add(self, line, collector, cpu_s):
        """Per-minute buckets: the 1 h sums cost <= 61 small dict merges per tick, not a rescan of
        every call in the hour."""
        b = self.buckets.setdefault(int(self.mono() // 60), {})
        cpu_s = max(0.0, cpu_s)
        self.line_of[collector] = line
        b[("line", line)] = b.get(("line", line), 0.0) + cpu_s
        b[("coll", collector)] = b.get(("coll", collector), 0.0) + cpu_s

    def add_late(self, lateness_s):
        self.late.append((self.mono(), lateness_s))

    def _window(self, span):
        now = self.mono()
        if len(self.whole) < 2:
            return None, 0.0
        # the oldest point inside the span; the newest one outside only when nothing older than
        # the last sample is inside (a long gap): never a base wider than needed (R1 finding 20)
        pts = list(self.whole)
        i = next((j for j, (t, _v) in enumerate(pts) if now - t <= span), len(pts) - 1)
        base = pts[min(i, len(pts) - 2)]
        dt = self.whole[-1][0] - base[0]
        if dt <= 0:
            return None, 0.0
        return 100.0 * (self.whole[-1][1] - base[1]) / dt, dt

    def window_s(self):
        return min(HOUR, self.mono() - self.t0)

    def lines(self, by="line", exclude=()):
        """Percent of one core per line (or per collector). `exclude` names collectors left out
        of the line sums (the ones already cut: a cut is judged on what is still running)."""
        span = max(1.0, self.window_s())
        out = {}
        for b in self.buckets.values():
            for (k, name), cpu in b.items():
                if by == "line":
                    if exclude:
                        if k != "coll" or name in exclude:
                            continue
                        name = self.line_of.get(name, name)
                    elif k != "line":
                        continue
                elif k != "coll":
                    continue
                out[name] = out.get(name, 0.0) + cpu
        return {k: 100.0 * v / span for k, v in out.items()}

    def spawns_per_h(self):
        if len(self.spawn_marks) < 2:
            return 0.0
        (t0, n0), (t1, n1) = self.spawn_marks[0], self.spawn_marks[-1]
        dt = t1 - t0
        return 0.0 if dt <= 0 else (n1 - n0) * HOUR / dt

    def late_over_1s(self):
        return sum(1 for _t, l in self.late if l > 1.0)

    def late_max(self):
        return max([l for _t, l in self.late] or [0.0])

    def verdict(self, exclude=()):
        """(verdict, why, lines_over_3x). Judged on the window so far (<= 1 h); `exclude` as in
        lines()."""
        h, _ = self._window(HOUR)
        lines = self.lines(exclude=exclude)
        why = []
        fail_lines = []
        v = "pass"
        if h is None:
            v = "watch"                  # no window: unmeasured, never a pass (R1 finding 17)
            why.append("no window")
        if h is not None and h > FAIL_TOTAL and self.window_s() >= FAIL_MIN_WINDOW_S:
            v = "fail"
            why.append("whole %.2f%% > %.1f%%" % (h, FAIL_TOTAL))
        for k, budget in BUDGET_LINES.items():
            x = lines.get(k, 0.0)
            if x > 3 * budget and self.window_s() >= FAIL_MIN_WINDOW_S:
                v = "fail"
                fail_lines.append(k)
                why.append("%s %.3f%% > 3x %.2f%%" % (k, x, budget))
            elif x > budget:
                if v == "pass":
                    v = "watch"
                why.append("%s %.3f%% > %.2f%%" % (k, x, budget))
        if v == "pass":
            if h is not None and h > BUDGET_TOTAL:
                v = "watch"
                why.append("whole %.2f%% > %.1f%%" % (h, BUDGET_TOTAL))
            if self.rss_mb > BUDGET_RSS_MB:
                v = "watch"
                why.append("rss %.1f MB > %.0f" % (self.rss_mb, BUDGET_RSS_MB))
            if self.spawns_per_h() > BUDGET_SPAWNS_H:
                v = "watch"
                why.append("spawns %.0f/h > %d" % (self.spawns_per_h(), BUDGET_SPAWNS_H))
            if self.late_over_1s():
                v = "watch"
                why.append("%d fast ticks late > 1 s" % self.late_over_1s())
        return v, "; ".join(why) or "within budget", fail_lines

    def summary(self):
        m60, _ = self._window(60.0)
        h, _ = self._window(HOUR)
        v, why, _ = self.verdict()
        out = {"rss_mb": round(self.rss_mb, 1), "rss_peak_mb": round(self.rss_peak_mb, 1),
               "spawns_per_h": round(self.spawns_per_h(), 1),
               "collectors": {k: round(x, 4) for k, x in sorted(self.lines().items())},
               "verdict": v}
        if m60 is not None:
            out["cpu_pct_1core_60s"] = round(m60, 3)
        if h is not None:
            out["cpu_pct_1core_1h"] = round(h, 3)
        return out, why


# --------------------------------------------------------------------------- the core

class Core(object):
    def __init__(self, collectors, storage, home=None, clock=time.time, mono=time.monotonic,
                 repo_dir=None, platform="darwin", lodestar="auto", cpu_reader=_cpu_self_children,
                 power_reader=None):
        self.collectors = list(collectors)
        self.storage = storage
        self.home = home or os.path.expanduser("~")
        self.clock = clock
        self.mono = mono
        self.platform = platform
        self.lodestar = find_lodestar(self.home) if lodestar == "auto" else lodestar
        self.live = os.path.join(storage, "live")
        self.snapshot_path = os.path.join(self.live, "snapshot.json")
        self.off_path = os.path.join(storage, "off")
        self.switch_path = os.path.join(storage, "collectors.json")
        self.cadence = dict(CADENCE_AC)
        self.shared = {"audit": {}}
        self.states = {c.name: {} for c in self.collectors}
        self.signals = {}            # path -> (owner tier, stamped value)
        self.last_run = {}           # tier -> mono of last run
        self.disabled_by_cost = {}   # collector -> reason
        self.switches = {}
        self._switch_mtime = None
        self.seq = 0
        self.started_at = clock()
        self.started_mono = mono()
        self.rev = git_rev(repo_dir) if repo_dir else "0000000"
        self.pid = os.getpid()
        self.machine = machine_key()
        self.cost = CostMeter(mono, cpu_reader)
        self.was_off = False
        self._last_sample = None
        self._last_cost_log = mono()
        self._hour_slot = int(clock() // HOUR)    # wall-clock hour this life is logging
        self._next_fast = None
        self._last_tick_mono = None
        self._errs = {}              # message -> [mono last written, repeats suppressed] (RB-m9)
        self._sample_day = None
        self.sessions_at = None      # the sessions list's own stamp (C3); None until first run
        self._ensure_dirs()

    def _ensure_dirs(self):
        """live/ and samples/ exist and are the owner's only (S3). Called at start and again when
        a write finds its directory gone (RB3: an agent tidied ~/agent-storage under us)."""
        for d in (self.storage, self.live, os.path.join(self.storage, "samples")):
            os.makedirs(d, mode=PRIVATE_DIR, exist_ok=True)
            if os.stat(d).st_mode & 0o777 != PRIVATE_DIR:
                os.chmod(d, PRIVATE_DIR)

    # ---- switches
    def _read_switches(self):
        try:
            mt = os.path.getmtime(self.switch_path)
        except OSError:
            self.switches, self._switch_mtime = {}, None
            return
        if mt == self._switch_mtime:
            return
        self._switch_mtime = mt
        try:
            with open(self.switch_path) as fh:
                d = json.load(fh)
            self.switches = {k: bool(v) for k, v in d.items() if not k.startswith("_")}
        except (OSError, ValueError, AttributeError):
            self.switches = {}

    def enabled(self, c):
        return self.switches.get(c.name, True) and c.name not in self.disabled_by_cost

    def _cadence_now(self):
        bat = self.shared.get("on_battery")
        self.cadence = dict(CADENCE_BATTERY if bat else CADENCE_AC)

    # ---- stamping
    def period(self, c):
        """A collector's own period: its tier's cadence, or its `every_s` when slower (DESIGN
        section 6: an over-budget collector moves to a slower cadence before it is cut)."""
        return max(self.cadence[c.tier], float(getattr(c, "every_s", 0) or 0))

    def _stamp(self, tier, now, value, period=None):
        st = {"observed_at": round(now, 3),
              "valid_until": round(now + STAMP_FACTOR * (period or self.cadence[tier]), 3)}
        if isinstance(value, dict) and "unknown" in value:
            st["unknown"] = str(value["unknown"])
            return st
        if isinstance(value, dict):
            for k, v in value.items():
                if v is not None:
                    st[k] = v
        return st

    def _set(self, c, path, value, now):
        per = self.period(c)
        stamp = lambda v: self._stamp(c.tier, now, v, per)  # noqa: E731
        if path == "sessions":
            rows = []
            for s in value or []:
                row = {k: v for k, v in s.items() if k not in ("load", "tasks") and v is not None}
                for sub in ("load", "tasks"):
                    if s.get(sub) is not None:
                        row[sub] = stamp(s[sub])
                if isinstance(row.get("tasks"), dict):
                    row["tasks"] = _tasks_v11(row["tasks"])
                rows.append(row)
            self.signals[path] = (c.tier, rows)
            self.sessions_at = stamp({})
        elif path == "projects.counts":
            if isinstance(value, dict) and "by_key" in value:
                self.signals[path] = (c.tier, {k: {"name": v.get("name") or k,
                                                   "registered": v.get("registered", True),
                                                   "counts": stamp(v["counts"])}
                                               for k, v in value["by_key"].items()})
            else:
                self.signals[path] = (c.tier, {"*": stamp(value or {"unknown": "read_failed"})})
        elif path in ("sessions.attention", "sessions.net"):
            if isinstance(value, dict) and "unknown" in value and len(value) == 1:
                self.signals[path] = (c.tier, {"*": stamp(value)})
            else:
                self.signals[path] = (c.tier, {sid: stamp(v)
                                               for sid, v in (value or {}).items()})
        else:
            self.signals[path] = (c.tier, stamp(value))

    def _mark(self, c, reason, now):
        """Every signal of `c` reads unknown `reason` (or is removed, for ABSENT_WHEN_OFF)."""
        for path in c.signals:
            if reason == "disabled" and c.name in ABSENT_WHEN_OFF:
                self.signals.pop(path, None)
                continue
            if path == "sessions":
                self._sessions_unknown(c, reason, now)
            elif path in ("sessions.attention", "sessions.net", "projects.counts"):
                self.signals[path] = (c.tier, {"*": self._stamp(c.tier, now, {"unknown": reason})})
            else:
                self.signals[path] = (c.tier, self._stamp(c.tier, now, {"unknown": reason}))

    def _sessions_unknown(self, c, reason, now):
        """C3 / RB2: the list is unmeasured, so it is published EMPTY with sessions_at unknown,
        never the previous rows under a fresh stamp; the structure the sessions sweep shares
        with attention, session_net and api is cleared with it, so none of them keeps working
        on dead pids."""
        self.signals["sessions"] = (c.tier, [])
        self.sessions_at = self._stamp(c.tier, now, {"unknown": reason}, self.period(c))
        for k in ("session_trees", "session_ids_by_pid", "transcript_dirs"):
            self.shared[k] = {}
        self.shared.pop("sessions_mono", None)

    # ---- running collectors
    def _run_collector(self, c):
        now = self.clock()
        ctx = Ctx(self, self.states[c.name])
        t0 = time.thread_time()
        ch0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            out = c.collect(ctx)
            err = None
        except Exception as e:  # noqa: BLE001 - one collector never brings the producer down
            out, err = None, e
        ch1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (time.thread_time() - t0) + ((ch1.ru_utime + ch1.ru_stime) - (ch0.ru_utime + ch0.ru_stime))
        drain = getattr(c, "drain_worker_cpu", None)
        if drain is not None:       # CPU its own worker threads report (R1 finding 8)
            try:
                cpu += max(0.0, float(drain()))
            except Exception:  # noqa: BLE001
                pass
        self.cost.add(c.tier, c.name, cpu)
        if err is not None:
            self._mark(c, "read_failed", now)
            self._log_err("%s raised %s" % (c.name, err_text(err)))
            return
        out = out or {}
        for path in c.signals:
            if path in out:
                try:
                    self._set(c, path, out[path], now)
                except Exception as e:  # noqa: BLE001 - R3 rule: one bad value, one absent field
                    self.signals.pop(path, None)
                    if path == "sessions":
                        self._sessions_unknown(c, "read_failed", now)
                    self._log_err("%s: %s unstampable (%s)" % (c.name, path, err_text(e)))
            elif path == "sessions":
                # no list this time: unmeasured, never the old rows (RB2)
                self._sessions_unknown(c, "read_failed", now)
            elif path in self.signals:
                # the collector did not produce it this time: no source, so ABSENT
                self.signals.pop(path, None)

    def _log_err(self, msg):
        """One stderr line, stamped with its UTC offset (RB-n14: the DST fall-back hour is not
        written twice). An identical message is written at most once per ERR_REPEAT_S, then
        with the count it stood for (RB-m9: a persistent failure no longer adds 43k lines/day)."""
        m = self.mono()
        hit = self._errs.get(msg)
        if hit is not None and m - hit[0] < ERR_REPEAT_S:
            hit[1] += 1
            return
        rep = hit[1] if hit else 0
        self._errs[msg] = [m, 0]
        if len(self._errs) > 256:
            for k in [k for k, v in self._errs.items() if m - v[0] >= ERR_REPEAT_S]:
                del self._errs[k]
        try:
            sys.stderr.write("%s augur: %s%s\n" % (
                time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(self.clock())), msg,
                " (repeated %d times since)" % rep if rep else ""))
            sys.stderr.flush()
        except (OSError, ValueError):
            pass

    def run_due(self):
        mono = self.mono()
        self._read_switches()
        self._cadence_now()
        lpm = bool(self.shared.get("low_power"))
        for tier in TIER_ORDER:
            last = self.last_run.get(tier)
            if last is not None and mono - last < self.cadence[tier] - 0.05:
                continue
            self.last_run[tier] = mono
            for c in self.collectors:
                if c.tier != tier:
                    continue
                every = float(getattr(c, "every_s", 0) or 0)
                if every > self.cadence[tier]:
                    lr = self.last_run.get("c:" + c.name)
                    if lr is not None and mono - lr < every - 0.05:
                        continue
                    self.last_run["c:" + c.name] = mono
                if not self.enabled(c):
                    self._mark(c, "disabled", self.clock())
                    continue
                if tier == "probes" and lpm and not getattr(c, "lpm_exempt", False):
                    self._mark(c, "disabled", self.clock())
                    continue
                self._run_collector(c)

    # ---- assembling
    def _projects(self, sessions):
        """The Lodestar entry always; every project with a live session; every project Lodestar
        reports with burning > 0 even with no session (Sprites' ghost visitor). Counts come only
        from Lodestar (projects.counts); unmanaged projects never carry them."""
        counts = self.signals.get("projects.counts", (None, None))[1]
        by = collections.OrderedDict()
        by["lodestar"] = {"key": "lodestar", "name": "Lodestar", "kind": "lodestar", "sessions": 0}
        for s in sessions:
            k = s.get("project_key")
            if not k or s.get("parent"):    # 1.2: a headless child is its parent's, not a session
                continue
            if k not in by:
                kind = "managed" if s.get("managed") is True else "unmanaged"
                if k == "lodestar":
                    kind = "lodestar"
                by[k] = {"key": k, "name": s.get("project") or k, "kind": kind, "sessions": 0}
            by[k]["sessions"] += 1
        if counts:
            if "*" in counts:           # Lodestar's feed is stale or failed: unmeasured, never 0
                for p in by.values():
                    if p["kind"] != "unmanaged":
                        p["counts"] = dict(counts["*"])
            else:
                for k, v in counts.items():
                    if k in by:
                        if by[k]["kind"] != "unmanaged":
                            by[k]["counts"] = dict(v["counts"])
                    elif (v["counts"].get("burning") or 0) > 0 and v.get("registered", True):
                        # C7: a key outside the registry is never drawn as a managed ghost
                        by[k] = {"key": k, "name": v["name"], "kind": "managed", "sessions": 0,
                                 "counts": dict(v["counts"])}
        return list(by.values())

    def assemble(self, now):
        machine = {}
        for path, (_tier, val) in self.signals.items():
            if path.startswith("machine."):
                machine[path.split(".", 1)[1]] = val
        sessions = [dict(s) for s in self.signals.get("sessions", (None, []))[1]]
        att = self.signals.get("sessions.attention", (None, {}))[1]
        net = self.signals.get("sessions.net", (None, {}))[1]
        for s in sessions:
            sid = s.get("id")
            a = att.get(sid) or att.get("*")
            if a is not None:
                s["attention"] = a
            n = net.get(sid) or net.get("*")
            if n is not None:
                s["net"] = n
        summary, _why = self.cost.summary()
        cost = {"observed_at": round(now, 3),
                "valid_until": round(now + STAMP_FACTOR * self.cadence["fast"], 3)}
        cost.update(summary)
        snap = {"schema": SCHEMA, "version": VERSION,
                "producer": {"name": "augur", "rev": self.rev, "pid": self.pid,
                             "platform": self.platform, "machine": self.machine,
                             "started_at": round(self.started_at, 3)},
                "written_at": round(now, 3),
                "valid_until": round(now + FILE_FACTOR * self.cadence["fast"], 3),
                "seq": self.seq, "cadence_s": dict(self.cadence),
                "machine": machine, "sessions": sessions,
                "projects": self._projects(sessions), "cost": cost}
        sa = self.sessions_at
        if sa is None and any("sessions" in c.signals for c in self.collectors):
            sa = self._stamp("agents", now, {"unknown": "warming_up"})
        if sa is not None:
            snap["sessions_at"] = dict(sa)
        return snap

    def off_snapshot(self, now):
        return {"schema": SCHEMA, "version": VERSION,
                "producer": {"name": "augur", "rev": self.rev, "pid": self.pid,
                             "platform": self.platform, "machine": self.machine,
                             "started_at": round(self.started_at, 3)},
                "written_at": round(now, 3),
                "valid_until": round(now + FILE_FACTOR * self.cadence["fast"], 3),
                "seq": self.seq, "off": True, "cadence_s": dict(self.cadence),
                "machine": {}, "sessions": [], "projects": []}

    def write(self, snap):
        t0 = time.thread_time()
        data = json.dumps(snap, separators=(",", ":")).encode()
        try:
            write_atomic(self.snapshot_path, data, PRIVATE_FILE)
        except FileNotFoundError:           # RB3: live/ deleted under us: remake it, once
            self._ensure_dirs()
            write_atomic(self.snapshot_path, data, PRIVATE_FILE)
        self.seq += 1
        self.cost.add("write", "write", time.thread_time() - t0)
        return data

    # ---- one tick
    def is_off(self):
        return os.path.exists(self.off_path)

    def tick(self):
        """One fast tick. Returns the snapshot written (or None when off and already written)."""
        if self.is_off():
            if self.was_off:
                return None
            self.was_off = True
            snap = self.off_snapshot(self.clock())
            self.write(snap)
            return snap
        if self.was_off:
            self.was_off = False
            self.last_run = {}          # restart every tier now
        self.run_due()
        self._enforce_cost()
        self.cost.sample()
        now = self.clock()
        snap = self.assemble(now)
        self.write(snap)
        try:
            try:
                self._periodic(snap)        # history lines: a full disk must not stop the snapshot
            except FileNotFoundError:       # RB3: samples/ (or the home) deleted: remake, once
                self._ensure_dirs()
                self._periodic(snap)
        except Exception as e:  # noqa: BLE001
            self._log_err("periodic raised %s" % err_text(e))
        return snap

    def _enforce_cost(self):
        cut = set(self.disabled_by_cost)
        v, why, fail_lines = self.cost.verdict(exclude=cut)
        if v != "fail" or not fail_lines:
            return
        by = self.cost.lines(by="collector")
        for line in fail_lines:
            cands = [c for c in self.collectors if c.tier == line and c.name not in self.disabled_by_cost]
            if not cands:
                continue
            worst = max(cands, key=lambda c: by.get(c.name, 0.0))
            self.disabled_by_cost[worst.name] = why
            self._log_err("cost meter FAIL: disabled collector %s (%s)" % (worst.name, why))
            append_line(os.path.join(self.storage, "cost.jsonl"),
                        {"t": round(self.clock(), 1), "event": "disabled", "collector": worst.name,
                         "why": why})

    def _periodic(self, snap):
        mono = self.mono()
        now = snap["written_at"]
        if self._last_sample is None or mono - self._last_sample >= SAMPLE_EVERY_S:
            self._last_sample = mono
            day = time.strftime("%Y-%m-%d", time.localtime(now))
            rollover = day != self._sample_day
            if rollover:
                self._prune_samples(now)
            for n in LOGS:
                self._trim_log(os.path.join(self.storage, n), now, rollover)
            append_line(os.path.join(self.storage, "samples", "snap-%s.jsonl" % day), snap)
            self._sample_day = day
            append_line(os.path.join(self.storage, "audit.jsonl"),
                        {"t": round(now, 1), "pid": self.pid, "started_at": round(self.started_at, 1),
                         "audit": dict(self.shared.get("audit") or {}),
                         "fast_late_max_s": round(self.cost.late_max(), 3),
                         "fast_late_over_1s": self.cost.late_over_1s()}, mode=0o600)
        if mono - self._last_cost_log >= COST_LOG_EVERY_S:
            self._last_cost_log = mono
            summary, why = self.cost.summary()
            rec = {"t": round(now, 1), "window": "10m", "why": why,
                   "by_collector": {k: round(v, 4) for k, v in self.cost.lines(by="collector").items()}}
            rec.update(summary)
            append_line(os.path.join(self.storage, "cost.jsonl"), rec)
        slot = int(now // HOUR)
        if slot > self._hour_slot:
            # one 1 h line per wall-clock hour, written at its end even when the producer
            # restarted inside it (R1 finding 18); window_s says how much of it was measured
            cpath = os.path.join(self.storage, "cost.jsonl")
            done = _last_hour_slot(cpath)
            if done is not None and done >= slot:
                self._hour_slot = slot
                return
            summary, why = self.cost.summary()
            # R2-12: the slot advances only once the line is written, so a failed append is
            # retried next tick instead of losing the hour
            append_line(cpath,
                        {"t": round(now, 1), "window": "1h", "window_s": round(self.cost.window_s(), 1),
                         "cpu_pct_1core_1h": summary.get("cpu_pct_1core_1h"),
                         "rss_mb": summary["rss_mb"], "spawns_per_h": summary["spawns_per_h"],
                         "collectors": summary["collectors"],
                         "by_collector": {k: round(v, 4) for k, v in self.cost.lines(by="collector").items()},
                         "late_over_1s": self.cost.late_over_1s(), "verdict": summary["verdict"],
                         "why": why})
            self._hour_slot = slot

    def _trim_log(self, path, now, rollover):
        """Retention for the append-only logs: at each day rollover (and at start) drop lines whose
        own t is more than LOG_KEEP_DAYS old; at any sample, a file over LOG_MAX_BYTES keeps only
        its newest whole lines within that size. A line without a readable t is kept by age.
        Rewritten atomically 0600; only this thread appends, so no line is lost to the swap."""
        try:
            size = os.stat(path).st_size
        except OSError:
            return
        if not rollover and size <= LOG_MAX_BYTES:
            return
        try:
            with open(path, "rb") as fh:
                lines = fh.read().splitlines(True)
        except OSError:
            return
        cut = now - LOG_KEEP_DAYS * 86400.0
        keep = []
        for ln in lines:
            try:
                t = float(json.loads(ln)["t"])
            except (ValueError, KeyError, TypeError):
                t = None
            if t is None or t >= cut:
                keep.append(ln if ln.endswith(b"\n") else ln + b"\n")
        total, start = 0, len(keep)
        while start > 0 and total + len(keep[start - 1]) <= LOG_MAX_BYTES:
            start -= 1
            total += len(keep[start])
        keep = keep[start:]
        if len(keep) != len(lines):
            write_atomic(path, b"".join(keep))

    def _prune_samples(self, now):
        """S3 / RB-m9: at each day rollover (and at start), delete snap-<day>.jsonl files more
        than SAMPLES_KEEP_DAYS days old. The day is read from the name, never the mtime."""
        d = os.path.join(self.storage, "samples")
        cut = time.strftime("%Y-%m-%d", time.localtime(now - SAMPLES_KEEP_DAYS * 86400.0))
        try:
            names = os.listdir(d)
        except OSError:
            return
        for n in names:
            if n.startswith("snap-") and n.endswith(".jsonl") and len(n) == 21 and n[5:15] < cut:
                try:
                    os.unlink(os.path.join(d, n))
                except OSError:
                    pass

    def _log_slept(self, wall_from, wall_to, slept_s):
        """RB4: a system-sleep span goes to audit.jsonl, so pilot1_check can excuse it."""
        try:
            append_line(os.path.join(self.storage, "audit.jsonl"),
                        {"t": round(wall_to, 1), "event": "slept", "from": round(wall_from, 1),
                         "to": round(wall_to, 1), "slept_s": round(slept_s, 1)})
        except OSError as e:
            self._log_err("slept line not written (%s)" % err_text(e))

    # ---- the loop
    def run_forever(self, sleep=time.sleep):
        """Lateness (R1 finding 7) = tick start - its slot, measured BEFORE re-gridding, so an
        overrun shows up on the next tick. Sleep is told apart by the wall clock running ahead of
        the monotonic one (mach_absolute_time stops in system sleep), never by a monotonic gap,
        which only a stall makes."""
        set_thread_qos(QOS_USER_INITIATED)
        self._next_fast = self.mono()
        last = None                     # (wall, mono) at the previous tick start
        while True:
            if self.is_off() and self.was_off:
                sleep(1.0)              # off: one stat a second, well inside the 5 s re-check
                self._next_fast, last = self.mono(), None
                continue
            mono, wall = self.mono(), self.clock()
            late = mono - self._next_fast
            slept = last is not None and (wall - last[0]) - (mono - last[1]) > SLEEP_JUMP_S
            if slept:
                self._log_slept(last[0], wall, (wall - last[0]) - (mono - last[1]))
            if late > 0 and not slept:
                self.cost.add_late(late)
            base = mono if late > 0 else self._next_fast    # re-grid from a late start
            last = (wall, mono)
            try:
                self.tick()
            except Exception as e:  # noqa: BLE001
                self._log_err("tick raised %s" % err_text(e))
            self._next_fast = base + self.cadence["fast"]
            sleep(max(0.0, self._next_fast - self.mono()))
