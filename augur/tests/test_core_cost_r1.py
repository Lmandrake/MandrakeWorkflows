"""Cost-meter and write-path defects from review R1 (findings 5, 7, 8, 17, 18, 19, 20).

Truth here is always set outside the meter: injected clocks and sleeps with known durations, a
kernel rusage reading taken by the test itself, or bytes the test chose to write."""
import json
import os
import resource

import pytest

from augur import core
from augur.collectors.base import Collector



class Clock(object):
    def __init__(self, t=1793500000.0):
        self.t = t
        self.m = 1000.0

    def now(self):
        return self.t

    def mono(self):
        return self.m

    def advance(self, s):
        self.t += s
        self.m += s


class FakeCPU(object):
    """A fake getrusage for the whole-producer meter: self CPU = rate x mono + extra."""

    def __init__(self, clock, rate=0.0):
        self.clock, self.rate, self.extra = clock, rate, 0.0

    def __call__(self):
        return self.clock.m * self.rate + self.extra, 0.0, 20 * 1000 * 1000


# --------------------------------------------------------------------------- finding 5

class Burn50(Collector):
    name, tier, signals = "burn", "counts", ()

    def __init__(self, clk):
        self.clk = clk

    def collect(self, ctx):
        import time
        t = time.thread_time()
        while time.thread_time() - t < 0.05:
            pass
        return {}


class Cheap(Collector):
    tier, signals = "counts", ()

    def __init__(self, name):
        self.name = name

    def collect(self, ctx):
        return {}


def test_one_cut_per_failing_collector_not_a_cascade(tmp_path):
    clk = Clock()
    cs = [Burn50(clk), Cheap("cheap_a"), Cheap("cheap_b")]
    c = core.Core(cs, str(tmp_path), home=str(tmp_path), clock=clk.now, mono=clk.mono,
                  lodestar=None, cpu_reader=FakeCPU(clk))
    for _ in range(160):
        c.last_run.pop("counts", None)
        c.tick()
        clk.advance(5)
    assert set(c.disabled_by_cost) == {"burn"}


# --------------------------------------------------------------------------- finding 7

class Slow(Collector):
    """Each call takes `cost` seconds of injected wall and monotonic time."""
    name, tier, signals = "slow", "fast", ()

    def __init__(self, clk, cost):
        self.clk, self.cost = clk, cost

    def collect(self, ctx):
        self.clk.advance(self.cost)
        return {}


class Stop(Exception):
    pass


def loop(c, clk, n, oversleep=None, wall_jump=None):
    """run_forever with an injected sleep; oversleep[i] adds monotonic+wall time to call i (a
    stall); wall_jump[i] adds wall time only (system sleep: mach_absolute_time stands still)."""
    calls = [0]

    def sleep(s):
        i = calls[0]
        calls[0] += 1
        if i >= n:
            raise Stop()
        clk.advance(max(0.0, s))
        if oversleep and i in oversleep:
            clk.advance(oversleep[i])
        if wall_jump and i in wall_jump:
            clk.t += wall_jump[i]
    with pytest.raises(Stop):
        c.run_forever(sleep=sleep)


def test_overrunning_ticks_are_late(tmp_path):
    clk = Clock()
    c = core.Core([Slow(clk, 8.0)], str(tmp_path), home=str(tmp_path), clock=clk.now,
                  mono=clk.mono, lodestar=None, cpu_reader=FakeCPU(clk))
    loop(c, clk, 20)
    # every tick after the first starts 8 s after the previous start, 6 s past its slot
    assert c.cost.late_over_1s() == 20
    assert c.cost.late_max() == pytest.approx(6.0)
    assert c.cost.verdict()[0] != "pass"


def test_stall_is_late_but_system_sleep_is_not(tmp_path):
    clk = Clock()
    c = core.Core([Slow(clk, 0.0)], str(tmp_path), home=str(tmp_path), clock=clk.now,
                  mono=clk.mono, lodestar=None, cpu_reader=FakeCPU(clk))
    loop(c, clk, 10, oversleep={3: 45.0, 6: 3.0}, wall_jump={6: 3600.0})
    assert c.cost.late_over_1s() == 1
    assert c.cost.late_max() == pytest.approx(45.0)


# --------------------------------------------------------------------------- finding 8

def test_worker_thread_cpu_is_charged_to_its_line(tmp_path):
    from augur.collectors import machine
    st = machine.StrainCollector({"cpu_ticks": lambda: None})
    clk = Clock()
    c = core.Core([st], str(tmp_path), home=str(tmp_path), clock=clk.now, mono=clk.mono,
                  lodestar=None, cpu_reader=FakeCPU(clk))
    r0 = resource.getrusage(resource.RUSAGE_SELF)
    for _ in range(10):
        c.last_run.pop("probes", None)
        c.tick()
        clk.advance(15)
    r1 = resource.getrusage(resource.RUSAGE_SELF)
    kernel_s = (r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime)
    line_s = c.cost.lines()["probes"] * c.cost.window_s() / 100.0
    assert kernel_s >= 0.2                       # ten 20 ms bursts, by the kernel's count
    assert line_s >= 0.19                        # the bursts are on the probes line
    assert line_s <= kernel_s * 1.05


def test_known_burn_against_kernel_rusage(tmp_path):
    """Replaces the thread_time-on-thread_time check: the meter's line against getrusage."""
    clk = Clock()
    b = Burn50(clk)
    b.tier = "agents"
    c = core.Core([b], str(tmp_path), home=str(tmp_path), clock=clk.now, mono=clk.mono,
                  lodestar=None, cpu_reader=FakeCPU(clk))
    r0 = resource.getrusage(resource.RUSAGE_SELF)
    for _ in range(10):
        c.tick()
        clk.advance(5)
    r1 = resource.getrusage(resource.RUSAGE_SELF)
    kernel_s = (r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime)
    burn_s = c.cost.lines(by="collector")["burn"] * c.cost.window_s() / 100.0
    assert burn_s == pytest.approx(0.5, rel=0.2)
    assert burn_s <= kernel_s * 1.05


# --------------------------------------------------------------------------- findings 17, 20

def test_long_gap_keeps_a_window_and_never_defaults_to_pass(tmp_path):
    clk = Clock()
    cpu = FakeCPU(clk, rate=0.05)                # 5 % of one core: over the 2 % fail line
    m = core.CostMeter(clk.mono, cpu)
    clk.advance(60)
    m.sample()
    clk.advance(3700)                            # a stall longer than the window
    m.sample()
    h, dt = m._window(core.HOUR)
    assert h == pytest.approx(5.0, rel=0.01)
    assert m.verdict()[0] == "fail"
    m2 = core.CostMeter(clk.mono, cpu)           # one point only: no window at all
    assert m2.verdict()[0] == "watch" and "no window" in m2.verdict()[1]


def test_hour_window_base_is_inside_the_hour(tmp_path):
    clk = Clock()
    cpu = FakeCPU(clk, rate=0.0)
    m = core.CostMeter(clk.mono, cpu)
    for i in range(121):                         # 1 % for the first hour, then nothing
        cpu.rate = 0.0
        if i <= 60:
            cpu.extra = 0.6 * i
        m.sample()
        clk.advance(60)
    clk.m -= 60
    h, _ = m._window(core.HOUR)
    assert h == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- finding 18

def hour_lines(tmp_path):
    p = os.path.join(str(tmp_path), "cost.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if '"window":"1h"' in l]


def test_hour_lines_survive_restarts(tmp_path):
    clk = Clock(t=1793520000.0)                  # 2026-11-01 xx:00:00 local, an hour boundary
    clk.t -= clk.t % 3600
    for _restart in range(3):                    # three 50-min lives across 2.5 hours
        c = core.Core([Slow(clk, 0.0)], str(tmp_path), home=str(tmp_path), clock=clk.now,
                      mono=clk.mono, lodestar=None, cpu_reader=FakeCPU(clk))
        for _ in range(50 * 6):
            c.tick()
            clk.advance(10)
    hours = {int(r["t"] // 3600) for r in hour_lines(tmp_path)}
    assert len(hours) == 2                       # 150 min from :00: two hour boundaries crossed
    assert all("window_s" in r for r in hour_lines(tmp_path))


# --------------------------------------------------------------------------- finding 19

def test_short_writes_are_completed(tmp_path, monkeypatch):
    real = os.write
    monkeypatch.setattr(core.os, "write", lambda fd, b: real(fd, bytes(b)[:7]))
    data = json.dumps({"k": "x" * 5000}).encode()
    p = os.path.join(str(tmp_path), "snap.json")
    core.write_atomic(p, data)
    assert open(p, "rb").read() == data


def test_failed_write_leaves_no_tmp_and_keeps_old(tmp_path, monkeypatch):
    p = os.path.join(str(tmp_path), "snap.json")
    core.write_atomic(p, b"old")

    def boom(fd):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(core.os, "fsync", boom)
    with pytest.raises(OSError):
        core.write_atomic(p, b"new")
    assert open(p, "rb").read() == b"old"
    assert os.listdir(str(tmp_path)) == ["snap.json"]


# --------------------------------------------------------------------------- review R2

def test_r2_9_rss_judged_on_current_not_lifetime_peak(tmp_path):
    clk = Clock()
    state = {"peak": 45e6, "cur": 25e6}                 # truth: a past 45 MB spike, 25 MB now
    m = core.CostMeter(clk.mono, lambda: (0.0, 0.0, state["peak"]),
                       rss_reader=lambda: state["cur"])
    clk.advance(60)
    m.sample()
    v, why, _ = m.verdict()
    assert "rss" not in why
    assert m.summary()[0]["rss_mb"] == pytest.approx(25.0)
    assert m.summary()[0]["rss_peak_mb"] == pytest.approx(45.0)
    state["cur"] = 41e6
    m.sample()
    assert "rss 41.0 MB" in m.verdict()[1]


def test_r2_12_failed_hour_line_is_retried(tmp_path, monkeypatch):
    clk = Clock(t=1793520000.0)
    clk.t -= clk.t % 3600
    c = core.Core([Slow(clk, 0.0)], str(tmp_path), home=str(tmp_path), clock=clk.now,
                  mono=clk.mono, lodestar=None, cpu_reader=FakeCPU(clk))
    real = core.append_line
    fail = {"on": False}

    def flaky(path, rec, mode=core.PRIVATE_FILE):
        if fail["on"] and rec.get("window") == "1h":
            raise OSError(28, "No space left on device")
        return real(path, rec, mode)
    monkeypatch.setattr(core, "append_line", flaky)
    for _ in range(359):
        c.tick()
        clk.advance(10)
    fail["on"] = True
    for _ in range(3):                                   # the hour boundary passes while full
        try:
            c.tick()
        except OSError:
            pass
        clk.advance(10)
    fail["on"] = False
    for _ in range(3):
        c.tick()
        clk.advance(10)
    assert len(hour_lines(tmp_path)) == 1


# --------------------------------------------------------------------------- review R3 (crash safety)

class BadShape(Collector):
    """Returns a value the core cannot stamp (sessions not a list of dicts)."""
    name, tier, signals = "sessions", "agents", ("sessions",)

    def collect(self, ctx):
        return {"sessions": [42]}


class GoodCpu(Collector):
    name, tier, signals = "cpu", "fast", ("machine.cpu",)

    def collect(self, ctx):
        return {"machine.cpu": {"busy_pct": 10.0, "cores_busy": 1.0, "ncpu": 10}}


def test_r3_bad_collector_output_degrades_only_its_field(tmp_path):
    clk = Clock()
    c = core.Core([BadShape(), GoodCpu()], str(tmp_path), home=str(tmp_path), clock=clk.now,
                  mono=clk.mono, lodestar=None, cpu_reader=FakeCPU(clk))
    snap = c.tick()
    assert snap is not None and snap["machine"]["cpu"]["busy_pct"] == 10.0
    assert snap["sessions"] == []                     # its own field: absent (empty), not a crash


def test_r3_periodic_failure_does_not_lose_the_snapshot(tmp_path, monkeypatch):
    clk = Clock()
    c = core.Core([GoodCpu()], str(tmp_path), home=str(tmp_path), clock=clk.now,
                  mono=clk.mono, lodestar=None, cpu_reader=FakeCPU(clk))

    def boom(*a, **k):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(core, "append_line", boom)
    snap = c.tick()                                   # samples/audit/cost lines all fail
    assert snap is not None and read(c)["seq"] == snap["seq"]


def read(c):
    with open(c.snapshot_path) as fh:
        return json.load(fh)
