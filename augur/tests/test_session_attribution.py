"""Per-session CPU attribution against a simulated kernel (review R1 findings 1-4, 12-14).

The simulator is the truth: every process burns CPU at a known rate, owned by the session it
was started in (a session root owns itself; an orphan keeps its owner). Exits are reaped the way
the kernel does it: the parent (launchd once the parent is gone) gains the dead process's own +
child CPU in its child time. Augur only sees what libproc would show (pid, ppid, start, own CPU,
reaped-children CPU), so every assertion compares Augur's reading with the simulator's ledger,
never with Augur's own earlier output.
"""
import json
import os

import pytest

from augur.collectors import sessions as S

T0 = 1793503000.0
CLAUDE = "/opt/x/.local/share/claude/versions/2.1.292"


@pytest.fixture(autouse=True)
def no_sidepulse(monkeypatch, tmp_path):
    # RB-n13: never read the live SidePulse state from a test
    monkeypatch.setenv("SIDEPULSE_STATE_DIR", os.path.join(str(tmp_path), "no-sidepulse"))


class Sim(object):
    def __init__(self, tmp):
        self.home = os.path.join(str(tmp), "home")
        self.repo = os.path.join(str(tmp), "dev", "Repo")
        os.makedirs(os.path.join(self.repo, ".git"))
        os.makedirs(os.path.join(self.home, ".claude", "sessions"))
        self.storage = os.path.join(str(tmp), "agent-storage", "augur")
        os.makedirs(self.storage)
        self.p = {}            # pid -> dict
        self.truth = {}        # owner root pid -> CPU seconds burnt
        self.t = T0
        self.mono = 0.0
        self.fail_rusage = set()
        self.hide = set()      # pids invisible to libproc (exited, not yet reaped)

    # ---- the kernel
    def spawn(self, pid, ppid, rate=0.0, path="/bin/zsh", comm="zsh", session=False, cpu=0.0):
        owner = pid if session else self.p[ppid]["owner"]
        self.p[pid] = {"ppid": ppid, "start": int(self.t), "rate": rate, "own": cpu, "child": 0.0,
                       "path": path, "comm": comm, "owner": owner}
        self.truth.setdefault(owner, 0.0)
        if session:
            with open(os.path.join(self.home, ".claude", "sessions", "%d.json" % pid), "w") as fh:
                json.dump({"procStart": None}, fh)

    def advance(self, dt):
        for q in self.p.values():
            q["own"] += q["rate"] * dt
            self.truth[q["owner"]] += q["rate"] * dt
        self.t += dt
        self.mono += dt

    def exit(self, pid, reap=True):
        """pid exits; its live children are reparented to launchd. reap=False leaves it a hidden
        zombie whose parent has not waited yet (reap(pid) later)."""
        q = self.p[pid]
        q["rate"] = 0.0
        for c in self.p.values():
            if c["ppid"] == pid:
                c["ppid"] = 1
        if reap:
            self.reap(pid)
        else:
            self.hide.add(pid)

    def reap(self, pid):
        q = self.p.pop(pid)
        self.hide.discard(pid)
        parent = self.p.get(q["ppid"])
        if parent is not None:
            parent["child"] += q["own"] + q["child"]

    # ---- what libproc shows
    def readers(self):
        sim = self

        class R(S.Readers):
            def uid(self):
                return 501

            def all_pids(self):
                return sorted(p for p in sim.p if p not in sim.hide)

            def bsdinfo(self, pid):
                q = sim.p.get(pid)
                if q is None or pid in sim.hide:
                    return None
                return (q["ppid"], 501, q["start"], q["comm"])

            def rusage(self, pid):
                q = sim.p.get(pid)
                if q is None or pid in sim.hide or pid in sim.fail_rusage:
                    return None
                return (q["own"], q["own"], 10_000_000, 0, q["child"])

            def pidpath(self, pid):
                return sim.p[pid]["path"] if pid in sim.p else ""

            def cmdline(self, pid):
                return ""

            def environ_value(self, pid, name):
                q = sim.p.get(pid)
                return (q or {}).get("env", {}).get(name, "")

            def cwd(self, pid):
                return sim.repo

            def tree(self, pid, limit=S.TREE_LIMIT):
                out, todo = [], [pid]
                while todo and len(out) < limit:
                    x = todo.pop()
                    if x in out or x not in sim.p or x in sim.hide:
                        continue
                    out.append(x)
                    todo.extend(c for c, v in sim.p.items() if v["ppid"] == x and c != x)
                return out
        return R()

    def ctx(self, state):
        class C(object):
            pass
        c = C()
        c.home, c.storage, c.lodestar = self.home, self.storage, None
        c.now, c.mono = self.t, self.mono
        c.cadence = {"fast": 2, "agents": 5, "probes": 15, "counts": 60}
        c.state, c.shared = state, {}
        return c


class Run(object):
    """Ticks the collector and keeps the truth per interval."""

    def __init__(self, sim):
        self.sim = sim
        self.coll = S.SessionsCollector(sim.readers())
        self.st = {}
        self.last_truth = {}

    def tick(self):
        out = self.coll.collect(self.sim.ctx(self.st))["sessions"]
        loads = {s["pid"]: s["load"] for s in out}
        truth = {}
        for owner, v in self.sim.truth.items():
            truth[owner] = v - self.last_truth.get(owner, 0.0)
        self.last_truth = dict(self.sim.truth)
        return loads, truth


def cores(truth, owner, dt=5.0):
    return truth.get(owner, 0.0) / dt


def two_sessions(tmp_path):
    sim = Sim(tmp_path)
    sim.spawn(101, 1, rate=0.0, path=CLAUDE, comm="2.1.292", session=True)
    sim.spawn(102, 101, rate=0.0)            # A's Bash-tool shell
    return sim


# --------------------------------------------------------------------------- finding 1

def test_nested_session_exit_is_not_dumped_on_parent(tmp_path):
    sim = two_sessions(tmp_path)
    sim.spawn(401, 102, rate=2.0, path=CLAUDE, comm="2.1.292", session=True, cpu=90.0)  # session B
    run = Run(sim)
    run.tick()
    for _ in range(2):
        sim.advance(5)
        loads, truth = run.tick()
    assert loads[401]["cpu_cores"] == pytest.approx(cores(truth, 401), abs=0.02)
    sim.advance(5)
    sim.exit(401)                            # B exits; A's shell reaps it (child time +100 s)
    loads, truth = run.tick()
    assert truth[101] == 0.0
    assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101), abs=0.02)


# --------------------------------------------------------------------------- finding 2

def test_orphaned_worker_neither_erases_nor_loses_cpu(tmp_path):
    sim = two_sessions(tmp_path)
    sim.p[101]["rate"] = 0.4
    sim.spawn(110, 102, rate=0.0, comm="sh")          # nohup wrapper
    sim.spawn(111, 110, rate=0.3, comm="server", cpu=12.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    loads, truth = run.tick()
    assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101), rel=0.05)
    sim.advance(5)
    sim.exit(110)                                     # wrapper exits: 111 reparented to launchd
    loads, truth = run.tick()
    assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101), rel=0.05)   # 0.7, not 0.0
    for _ in range(2):                                # the orphan keeps burning for the session
        sim.advance(5)
        loads, truth = run.tick()
        assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101), rel=0.05)
    sim.advance(5)
    sim.exit(111)                                     # launchd reaps it: nothing in the tree gains
    loads, truth = run.tick()
    # its last partial interval went to launchd and is unknowable; the rest is never subtracted
    tail = 0.3
    assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101) - tail, rel=0.05)


# --------------------------------------------------------------------------- finding 3

def test_failed_rusage_reads_unknown_not_zero(tmp_path):
    sim = two_sessions(tmp_path)
    sim.p[101]["rate"] = 0.5
    sim.spawn(103, 101, rate=0.2, comm="python3.12", cpu=20.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.fail_rusage = {101, 102, 103}
    sim.advance(5)
    loads, truth1 = run.tick()
    assert loads[101] == {"unknown": "read_failed"}
    sim.fail_rusage = set()                           # recovers: no spike, no loss
    sim.advance(5)
    loads, truth2 = run.tick()
    # the reading spans both intervals (10 s since the last measured tick)
    want = (truth1[101] + truth2[101]) / 10.0
    assert want == pytest.approx(0.7)
    assert loads[101]["cpu_cores"] == pytest.approx(want, rel=0.05)


def test_root_rusage_failure_alone_is_unknown(tmp_path):
    sim = two_sessions(tmp_path)
    run = Run(sim)
    run.tick()
    sim.fail_rusage = {101}
    sim.advance(5)
    loads, _ = run.tick()
    assert loads[101] == {"unknown": "read_failed"}


# --------------------------------------------------------------------------- finding 4

def test_exited_not_yet_reaped_child_is_not_double_counted(tmp_path):
    sim = two_sessions(tmp_path)
    sim.p[101]["rate"] = 0.3
    sim.spawn(104, 102, rate=1.0, comm="cc", cpu=9.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    loads, truth = run.tick()
    assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101), rel=0.05)
    sim.advance(5)
    sim.exit(104, reap=False)          # gone from libproc, the shell has not waited yet
    l1, t1 = run.tick()
    assert l1[101]["cpu_cores"] >= 0.3 - 1e-9        # the root's own CPU is never wiped
    sim.reap(104)                      # now the shell's child time rises by 104's whole total
    sim.advance(5)
    l2, t2 = run.tick()
    # 104's last 5 s are only visible once reaped, so they land a tick late; the two ticks
    # together must equal the truth (the old code read 0.0 then 4.1 against 1.3 + 0.3)
    assert (l1[101]["cpu_cores"] + l2[101]["cpu_cores"]) * 5 == pytest.approx(t1[101] + t2[101], rel=0.05)


def test_zombie_with_failed_read_is_not_gone(tmp_path):
    sim = two_sessions(tmp_path)
    sim.p[101]["rate"] = 0.3
    sim.spawn(104, 102, rate=1.0, comm="cc", cpu=9.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.advance(5)
    sim.p[104]["rate"] = 0.0
    sim.fail_rusage = {104}            # a zombie: listed, but its rusage read fails
    l1, t1 = run.tick()
    sim.fail_rusage = set()
    sim.reap(104)
    sim.advance(5)
    l2, t2 = run.tick()
    assert (l1[101]["cpu_cores"] + l2[101]["cpu_cores"]) * 5 == pytest.approx(t1[101] + t2[101], rel=0.05)


# --------------------------------------------------------------------------- findings 12-14

def test_counter_going_backwards_is_unknown_counter_reset(tmp_path):
    sim = two_sessions(tmp_path)
    sim.p[101]["own"] = 50.0
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.p[101]["own"] = 10.0           # a counter anomaly
    sim.advance(5)
    loads, _ = run.tick()
    assert loads[101] == {"unknown": "counter_reset"}


def test_transient_pidpath_failure_is_not_cached(tmp_path):
    sim = two_sessions(tmp_path)
    run = Run(sim)
    good = sim.p[101]["path"]
    sim.p[101]["path"] = ""            # proc_pidpath failed once
    loads, _ = run.tick()
    assert 101 not in loads
    sim.p[101]["path"] = good
    sim.advance(5)
    loads, _ = run.tick()
    assert 101 in loads


def test_truncated_tree_reads_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "TREE_LIMIT", 3)
    sim = two_sessions(tmp_path)
    for pid in (120, 121, 122):
        sim.spawn(pid, 102, rate=0.1, comm="cc")
    run = Run(sim)
    run.tick()
    sim.advance(5)
    loads, _ = run.tick()
    assert loads[101] == {"unknown": "truncated"}


def test_orphans_later_children_still_count(tmp_path):
    sim = two_sessions(tmp_path)
    sim.spawn(110, 102, comm="sh")
    sim.spawn(111, 110, rate=0.2, comm="server")
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.exit(110)
    sim.advance(5)
    run.tick()
    sim.spawn(112, 111, rate=0.5, comm="worker")     # the orphan forks after leaving the tree
    sim.advance(5)
    run.tick()
    sim.advance(5)
    loads, truth = run.tick()
    assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101), rel=0.05)
    assert loads[101]["procs"] == 4


# --------------------------------------------------------------------------- review R2

def test_r2_1_nested_zombie_and_cochild_no_phantom(tmp_path):
    """R2-1: nested session B exits but is reaped a sweep late; meanwhile an unrelated child of the
    same shell runs 5 s and is reaped. Truth: A burns 1.0 then 0.0 cores."""
    sim = two_sessions(tmp_path)
    sim.spawn(401, 102, rate=1.0, path=CLAUDE, comm="2.1.292", session=True, cpu=595.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.exit(401, reap=False)                 # B is a zombie: hidden, not yet reaped
    sim.spawn(150, 102, rate=1.0, comm="git")
    sim.advance(5)
    sim.exit(150)                             # unrelated child: 5 s, reaped this interval
    l1, t1 = run.tick()
    assert l1[101]["cpu_cores"] == pytest.approx(cores(t1, 101), abs=0.05)     # 1.0
    sim.reap(401)                             # B's 600 s land in the shell's child time now
    sim.advance(5)
    l2, t2 = run.tick()
    assert l2[101]["cpu_cores"] == pytest.approx(cores(t2, 101), abs=0.05)     # 0.0, not 120


def test_r2_1_cochild_reaped_with_nested_root_is_counted(tmp_path):
    sim = two_sessions(tmp_path)
    sim.spawn(401, 102, rate=2.0, path=CLAUDE, comm="2.1.292", session=True, cpu=100.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.spawn(150, 102, rate=1.0, comm="git")
    sim.advance(5)
    sim.exit(401)
    sim.exit(150)
    loads, truth = run.tick()
    # B's own last 5 s (10 CPU-s) belong to B, not A; the git child's 5 s are A's
    assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101), abs=0.05)


def test_r2_2_late_reap_after_long_wait_no_double_count(tmp_path):
    """R2-2: a child with 300 s already counted exits and is reaped 10 minutes later."""
    sim = two_sessions(tmp_path)
    sim.spawn(160, 102, rate=1.0, comm="node", cpu=295.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.exit(160, reap=False)
    total_read, total_true = 0.0, 0.0
    for i in range(120):                      # 600 s unreaped
        sim.advance(5)
        if i == 119:
            sim.reap(160)
        loads, truth = run.tick()
        total_read += loads[101]["cpu_cores"] * 5
        total_true += truth.get(101, 0.0)
    sim.advance(5)
    loads, truth = run.tick()
    total_read += loads[101]["cpu_cores"] * 5
    total_true += truth.get(101, 0.0)
    assert total_true == pytest.approx(0.0)
    assert total_read == pytest.approx(0.0, abs=0.5)


def test_r2_2_parent_read_failing_long_keeps_credit(tmp_path):
    sim = two_sessions(tmp_path)
    sim.spawn(160, 102, rate=1.0, comm="node", cpu=295.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.exit(160, reap=False)
    sim.advance(5)
    run.tick()
    sim.fail_rusage = {102}                   # the shell's read fails for 4 minutes
    for _ in range(48):
        sim.advance(5)
        run.tick()
    sim.fail_rusage = set()
    sim.reap(160)
    sim.advance(5)
    loads, truth = run.tick()
    assert loads[101]["cpu_cores"] == pytest.approx(0.0, abs=0.05)


def test_r2_6_truncated_orphan_subtree_reads_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "TREE_LIMIT", 4)
    sim = two_sessions(tmp_path)
    sim.spawn(110, 102, comm="sh")
    sim.spawn(111, 110, rate=0.1, comm="make")
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.exit(110)                             # 111 orphaned
    for pid in (170, 171, 172, 173):
        sim.spawn(pid, 111, rate=0.1, comm="cc")
    sim.advance(5)
    loads, _ = run.tick()
    assert loads[101] == {"unknown": "truncated"}


def test_r2_7_pid_reaped_between_scan_and_read_counted_once(tmp_path):
    """R2-7: a child is listed by the scan, exits and is reaped before its rusage read."""
    sim = two_sessions(tmp_path)
    sim.spawn(190, 101, comm="zsh")           # the parent is read AFTER the child (pid order)
    sim.spawn(180, 190, rate=1.0, comm="cc", cpu=20.0)
    sim.p[180]["ppid"] = 190
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.advance(5)
    rd = run.coll.r
    real = rd.rusage

    def racy(pid):
        if pid == 180 and 180 in sim.p:
            sim.exit(180)                     # dies and is reaped right before its own read
            return None
        return real(pid)
    rd.rusage = racy
    total_read = total_true = 0.0
    for _ in range(3):
        loads, truth = run.tick()
        total_read += loads[101]["cpu_cores"] * 5
        total_true += truth.get(101, 0.0)
        sim.advance(5)
    assert total_read == pytest.approx(total_true, abs=0.3)


# --------------------------------------------------------------------------- review R3

def test_r3_1_root_exits_between_scan_and_read(tmp_path):
    """R3-1: session 1's root exits right before its rusage read. Truth: session 1 is gone, and
    session 2 (alive, 0.5 cores) still reads a number."""
    sim = two_sessions(tmp_path)
    sim.spawn(201, 1, rate=0.5, path=CLAUDE, comm="2.1.292", session=True)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.advance(5)
    rd = run.coll.r
    real = rd.rusage

    def racy(pid):
        if pid == 101 and 101 in sim.p:
            sim.exit(101)
            return None
        return real(pid)
    rd.rusage = racy
    loads, truth = run.tick()
    assert 101 not in loads
    assert loads[201]["cpu_cores"] == pytest.approx(cores(truth, 201), abs=0.02)


def test_r3_general_one_session_raising_degrades_only_it(tmp_path):
    """General rule: an exception inside one session's assembly leaves that session's load and
    tasks absent; every other session still reads, and the collector does not raise."""
    sim = two_sessions(tmp_path)
    sim.spawn(201, 1, rate=0.5, path=CLAUDE, comm="2.1.292", session=True)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    real = run.coll._project

    def boom(ctx, st, sid, pid, reg):
        if pid == 101:
            raise RuntimeError("injected")
        return real(ctx, st, sid, pid, reg)
    run.coll._project = boom
    out = run.coll.collect(sim.ctx(run.st))["sessions"]
    by = {s["pid"]: s for s in out}
    assert "load" not in by.get(101, {}) and "tasks" not in by.get(101, {})
    assert "cpu_cores" in by[201]["load"]


def test_r3_12_cochild_misplacement_is_bounded_by_the_tail(tmp_path):
    """R2-1 residual (R4-6: bound by the tail Augur ACTUALLY computed, both sides). Nested B was
    burning 2 cores, then went idle in its last interval; an unrelated git child of A burns 5 s
    and is reaped with B. Which of the two burnt the last interval is not knowable from the
    parent's child time. Truth: A = 1.0 core. Augur may remove at most B's computed tail, never
    add: truth - tail <= read <= truth. R5-13: B's rate is 0.4, so the tail (2 CPU-s) is smaller
    than the truth (5 CPU-s) and the lower side can fail (0.6 <= read)."""
    sim = two_sessions(tmp_path)
    sim.spawn(401, 102, rate=0.4, path=CLAUDE, comm="2.1.292", session=True, cpu=100.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    kb = (401, sim.p[401]["start"])
    tail_s = run.st["rate"][kb] * 5.0          # the tail Augur will apply for B: rate x interval
    assert tail_s == pytest.approx(2.0)
    assert 1.0 - tail_s / 5.0 > 0.5            # the lower bound is not vacuous
    sim.p[401]["rate"] = 0.0
    sim.spawn(150, 102, rate=1.0, comm="git")
    sim.advance(5)
    sim.exit(401)
    sim.exit(150)
    loads, truth = run.tick()
    read, want = loads[101]["cpu_cores"], cores(truth, 101)
    assert want == pytest.approx(1.0)
    assert want - min(tail_s, 5.0) / 5.0 - 1e-6 <= read <= want + 1e-6


# --------------------------------------------------------------------------- review R4

def test_r4_1_failed_session_sweep_rolls_back_its_credits(tmp_path):
    """R4-1: a reap credit consumed on a tick whose session then raises must be restored, or the
    next tick double-counts the reaped child (review: 60 CPU-s against a truth of 5)."""
    sim = two_sessions(tmp_path)
    sim.spawn(160, 102, rate=1.0, comm="node", cpu=50.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    state = {"exited": False}

    def step(i):
        if i == 0 and not state["exited"]:
            sim.exit(160)
            state["exited"] = True
    real = run.coll._tasks

    def boom(ctx, pid, *a, **k):
        if pid == 101 and run.coll._fail_once:
            run.coll._fail_once = False
            raise RuntimeError("injected after load")
        return real(ctx, pid, *a, **k)
    run.coll._fail_once = True
    run.coll._tasks = boom
    read = true = 0.0
    span = 5.0
    for i in range(3):
        sim.advance(5)
        step(i)
        out = run.coll.collect(sim.ctx(run.st))["sessions"]
        ld = {s["pid"]: s for s in out}.get(101, {}).get("load")
        t = sim.truth.get(101, 0.0) - run.last_truth.get(101, 0.0)
        run.last_truth = dict(sim.truth)
        true += t
        if ld and "cpu_cores" in ld:
            read += ld["cpu_cores"] * span
            span = 5.0
        else:
            span += 5.0
    assert true == pytest.approx(5.0)
    assert read == pytest.approx(true, abs=0.3)


# --------------------------------------------------------------------------- review R5

def _integrate_with_failure(run, sim, fail_on, n=4, step=None):
    # step(i), when given, replaces the tick's sim.advance(5) and must advance 5 s itself
    """Tick n times; session 101's sweep raises (after its load is built) on tick `fail_on`.
    Returns (CPU-s Augur read for 101, CPU-s the simulator burnt for 101). A tick with no load
    widens the next reading's span (the baseline is kept across it)."""
    real = run.coll._tasks
    tick = {"i": None}

    def boom(ctx, pid, *a, **k):
        if pid == 101 and tick["i"] == fail_on:
            raise RuntimeError("injected after load")
        return real(ctx, pid, *a, **k)
    run.coll._tasks = boom
    read = true = 0.0
    span = 5.0
    for i in range(n):
        tick["i"] = i
        if step:
            step(i)
        else:
            sim.advance(5)
        out = run.coll.collect(sim.ctx(run.st))["sessions"]
        ld = {s["pid"]: s for s in out}.get(101, {}).get("load")
        true += sim.truth.get(101, 0.0) - run.last_truth.get(101, 0.0)
        run.last_truth = dict(sim.truth)
        if ld and "cpu_cores" in ld:
            read += ld["cpu_cores"] * span
            span = 5.0
        else:
            span += 5.0
    return read, true


def test_r5_7_child_born_on_a_failing_tick_keeps_its_cpu(tmp_path):
    """R5-7: a child born inside the interval of the tick whose sweep raises. Review: Augur read
    15 CPU-s against simulator truth 20. Its baseline must not come from the failed tick."""
    sim = two_sessions(tmp_path)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.advance(1)
    sim.spawn(170, 102, rate=1.0, comm="node")       # born 1 s into the next interval
    sim.t -= 1
    sim.mono -= 1                                    # keep the tick grid (the 1 s is not burnt)
    read, true = _integrate_with_failure(run, sim, fail_on=0)
    assert true == pytest.approx(20.0)
    assert read == pytest.approx(true, abs=0.3)


def test_r5_7_birth_and_reap_on_the_same_failing_tick(tmp_path):
    """Both on the failing tick: 160 (1 core, 50 s of history) exits and is reaped, 170 is born."""
    sim = two_sessions(tmp_path)
    sim.spawn(160, 102, rate=1.0, comm="node", cpu=50.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()

    def step(i):
        if i == 0:
            sim.advance(1)
            sim.spawn(170, 102, rate=1.0, comm="node")    # born 1 s into the failing interval
            sim.advance(4)
            sim.exit(160)                                 # and 160 reaped in the same interval
        else:
            sim.advance(5)
    read, true = _integrate_with_failure(run, sim, fail_on=0, step=step)
    # 160: 5 s; 170: 4 s in the failing interval + 3 x 5 s
    assert true == pytest.approx(24.0)
    assert read == pytest.approx(true, abs=0.3)


# --------------------------------------------------------------------------- RB-m5

def test_rb_m5_wall_step_back_keeps_a_new_childs_first_interval(tmp_path):
    """RB-m5: the wall clock steps back 1 h between two sweeps (mono +5 s). A child born between
    them (on the stepped clock) burnt 2 CPU-s, all this interval. Truth: root 1.0 core + child
    2 / 5 = 0.4: 1.4 cores (the simulator's ledger)."""
    sim = two_sessions(tmp_path)
    sim.p[101]["rate"] = 1.0
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.t -= 3600.0                       # the step: wall back 1 h, mono unchanged
    sim.advance(3)
    sim.spawn(150, 101, rate=1.0, comm="cc")
    sim.advance(2)
    loads, truth = run.tick()
    assert truth[101] == pytest.approx(7.0)
    assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101), abs=0.01)


# --------------------------------------------------------------------------- RB-m8

def test_rb_m8_unmatched_credit_is_retired_and_no_longer_erases_a_later_child(tmp_path):
    """RB-m8: a child (100 CPU-s) exits but its reap never shows in the shell's child time. More
    than CREDIT_MAX_AGE_S later an unrelated child (120 CPU-s, born and reaped between sweeps)
    is reaped. Truth (the ledger): that interval's 120 s are this session's; the stale 100 s
    credit must not erase them, and the retirement is reported."""
    sim = two_sessions(tmp_path)
    sim.spawn(104, 102, rate=0.0, comm="cc", cpu=100.0)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    run.tick()
    sim.exit(104, reap=False)                 # its reap never reaches the shell
    sim.p.pop(104)
    sim.hide.discard(104)
    sim.advance(5)
    loads, _ = run.tick()
    assert loads[101]["pending_reconciliation_cpu_s"] == pytest.approx(100.0)
    for _ in range(int(S.CREDIT_MAX_AGE_S / 600) + 1):
        sim.advance(600)
        run.tick()
    sim.advance(5)
    sim.p[102]["child"] += 120.0              # a genuine child, born and reaped between sweeps
    sim.truth[101] += 120.0
    loads, truth = run.tick()
    assert truth[101] == pytest.approx(120.0)
    assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101), rel=0.01)
    assert loads[101]["pending_reconciliation_cpu_s"] == 0.0


# --------------------------------------------------------------------------- headless runs (1.2)

def _headless_file(sim, pid, entrypoint="sdk-cli"):
    with open(os.path.join(sim.home, ".claude", "sessions", "%d.json" % pid), "w") as fh:
        json.dump({"procStart": None, "kind": "interactive", "entrypoint": entrypoint}, fh)


def _rows(run):
    return {s["pid"]: s for s in run.coll.collect(run.sim.ctx(run.st))["sessions"]}


def test_headless_child_is_attributed_to_its_session_and_not_double_counted(tmp_path):
    sim = two_sessions(tmp_path)
    sim.p[101]["rate"] = 0.1
    sim.spawn(103, 102, rate=0.0, path="/usr/bin/python3", comm="python3")   # zsh -> python
    sim.spawn(501, 103, rate=0.5, path=CLAUDE, comm="2.1.292", session=True)  # -> claude -p
    _headless_file(sim, 501)
    run = Run(sim)
    run.tick()
    sim.advance(5)
    loads, truth = run.tick()
    rows = _rows(run)
    a, c = rows[101], rows[501]
    assert c["headless"] is True and c["parent"] == a["id"]
    assert (c["project"], c["project_key"]) == (a["project"], a["project_key"])
    assert "parent" not in a and "headless" not in a
    # each carries its own load; the parent's excludes the child
    assert loads[501]["cpu_cores"] == pytest.approx(cores(truth, 501), abs=0.02)
    assert loads[101]["cpu_cores"] == pytest.approx(cores(truth, 101), abs=0.02)


def test_headless_with_no_session_ancestor_stays_standalone(tmp_path):
    sim = Sim(tmp_path)
    sim.p[1] = {"ppid": 0, "start": int(sim.t), "rate": 0.0, "own": 0.0, "child": 0.0,
                "path": "/sbin/launchd", "comm": "launchd", "owner": 1}
    sim.spawn(601, 1, rate=0.0, path="/bin/sh", comm="sh")                    # cron shell
    sim.spawn(602, 601, rate=0.0, path=CLAUDE, comm="2.1.292", session=True)
    _headless_file(sim, 602)
    run = Run(sim)
    rows = _rows(run)
    assert rows[602]["headless"] is True
    assert "parent" not in rows[602]


def test_nested_headless_resolves_to_the_top_interactive_session(tmp_path):
    sim = two_sessions(tmp_path)
    sim.spawn(701, 102, path=CLAUDE, comm="2.1.292", session=True)            # -p under A
    _headless_file(sim, 701)
    sim.spawn(702, 701, path="/bin/zsh", comm="zsh")
    sim.spawn(703, 702, path=CLAUDE, comm="2.1.292", session=True)            # -p under that -p
    _headless_file(sim, 703)
    rows = _rows(Run(sim))
    assert rows[701]["parent"] == rows[101]["id"]
    assert rows[703]["parent"] == rows[101]["id"]


def test_headless_by_argv_when_the_file_names_no_entrypoint(tmp_path):
    sim = two_sessions(tmp_path)
    sim.spawn(801, 102, path=CLAUDE, comm="2.1.292", session=True)            # file: procStart only
    run = Run(sim)
    run.coll.r.cmdline = lambda pid: "claude -p say ok" if pid == 801 else ""
    rows = _rows(run)
    assert rows[801]["parent"] == rows[101]["id"]
    # an interactive nested session (entrypoint cli) is NOT a child, even with " -p " in its prompt
    sim.spawn(802, 102, path=CLAUDE, comm="2.1.292", session=True)
    _headless_file(sim, 802, entrypoint="cli")
    run.coll.r.cmdline = lambda pid: "claude fix the -p flag"
    rows = _rows(run)
    assert "parent" not in rows[802] and "headless" not in rows[802]


def test_reparented_headless_falls_back_to_the_inherited_socket(tmp_path):
    sim = two_sessions(tmp_path)
    sim.p[1] = {"ppid": 0, "start": int(sim.t), "rate": 0.0, "own": 0.0, "child": 0.0,
                "path": "/sbin/launchd", "comm": "launchd", "owner": 1}
    sim.spawn(901, 1, path=CLAUDE, comm="2.1.292", session=True)     # `( claude -p ... & )`
    sim.p[901]["env"] = {"CLAUDE_CODE_MESSAGING_SOCKET": "/tmp/cc-socks/101.sock"}
    _headless_file(sim, 901)
    sim.spawn(902, 1, path=CLAUDE, comm="2.1.292", session=True)     # socket names no live root
    sim.p[902]["env"] = {"CLAUDE_CODE_MESSAGING_SOCKET": "/tmp/cc-socks/4242.sock"}
    _headless_file(sim, 902)
    rows = _rows(Run(sim))
    assert rows[901]["parent"] == rows[101]["id"]
    assert "parent" not in rows[902] and rows[902]["headless"] is True
