"""Core tests (DESIGN.md section 9): freshness, unknown-on-raise, stale file, off switch, absence,
cost meter, schema validation of every written snapshot, privacy."""

import json
import os
import re
import time

import pytest

from augur import core
from augur.collectors.base import Collector

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(os.path.dirname(HERE), "schema", "snapshot.schema.json")
EXAMPLE_PATH = os.path.join(os.path.dirname(HERE), "schema", "example.json")

jsonschema = pytest.importorskip("jsonschema")


def validator():
    with open(SCHEMA_PATH) as fh:
        return jsonschema.Draft202012Validator(json.load(fh))


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
    """A fake getrusage: self CPU advances by `rate` x mono seconds."""

    def __init__(self, clock, rate=0.0):
        self.clock, self.rate, self.extra = clock, rate, 0.0

    def __call__(self):
        return self.clock.m * self.rate + self.extra, 0.0, 20 * 1000 * 1000


class Cpu(Collector):
    name, tier, signals = "cpu", "fast", ("machine.cpu",)

    def __init__(self):
        self.n = 0

    def collect(self, ctx):
        self.n += 1
        if self.n == 1:
            return {"machine.cpu": {"unknown": "warming_up"}}
        return {"machine.cpu": {"busy_pct": 10.0, "cores_busy": 1.0, "ncpu": 10}}


class Boom(Collector):
    name, tier, signals = "boom", "probes", ("machine.thermal",)

    def __init__(self):
        self.raise_now = False

    def collect(self, ctx):
        if self.raise_now:
            raise RuntimeError("sensor gone")
        return {"machine.thermal": {"state": 0, "low_power": False}}


class NoBattery(Collector):
    name, tier, signals = "power", "probes", ("machine.power",)
    lpm_exempt = True

    def collect(self, ctx):
        return {}


class Sess(Collector):
    name, tier, signals = "sessions", "agents", ("sessions",)

    def collect(self, ctx):
        return {"sessions": [{"id": "100@1793400000", "pid": 100, "started_at": 1793400000.0,
                              "project": "Demo", "project_key": "demo", "managed": False,
                              "load": {"cpu_cores": 0.1, "mem_gb": 0.2, "procs": 3,
                                       "wait_s_per_s": 0.0, "starved": False},
                              "tasks": {"shells": 1, "subagents": 0, "total": 1,
                                        "method": "tree+transcripts"}}]}


class Net(Collector):
    name, tier, signals = "session_net", "agents", ("sessions.net",)

    def collect(self, ctx):
        return {"sessions.net": {"100@1793400000": {"rx_mbps": 0.1, "tx_mbps": 0.2, "flows": 2}}}


def make(tmp_path, collectors, rate=0.0):
    clk = Clock()
    c = core.Core(collectors, str(tmp_path), home=str(tmp_path), clock=clk.now, mono=clk.mono,
                  lodestar=None, cpu_reader=FakeCPU(clk, rate))
    return c, clk


def read(c):
    with open(c.snapshot_path) as fh:
        return json.load(fh)


def test_example_validates_and_v2_rejected():
    v = validator()
    with open(EXAMPLE_PATH) as fh:
        ex = json.load(fh)
    assert not list(v.iter_errors(ex))
    ex["version"] = "2.0"
    assert list(v.iter_errors(ex))


def test_tier_stamps_and_file_valid_until(tmp_path):
    c, clk = make(tmp_path, [Cpu(), Boom(), Sess(), Net()])
    c.tick()
    clk.advance(2)
    c.tick()
    s = read(c)
    assert not list(validator().iter_errors(s))
    cpu = s["machine"]["cpu"]
    assert cpu["valid_until"] - cpu["observed_at"] == pytest.approx(5.0)
    th = s["machine"]["thermal"]
    assert th["valid_until"] - th["observed_at"] == pytest.approx(37.5)
    ld = s["sessions"][0]["load"]
    assert ld["valid_until"] - ld["observed_at"] == pytest.approx(12.5)
    assert s["valid_until"] - s["written_at"] == pytest.approx(10.0)
    assert s["sessions"][0]["net"]["tx_mbps"] == 0.2
    assert [p["key"] for p in s["projects"]] == ["lodestar", "demo"]
    assert s["projects"][0]["sessions"] == 0 and "counts" not in s["projects"][0]


def test_warming_up_has_no_value_keys(tmp_path):
    c, _ = make(tmp_path, [Cpu()])
    c.tick()
    cpu = read(c)["machine"]["cpu"]
    assert cpu["unknown"] == "warming_up"
    assert not set(cpu) - {"observed_at", "valid_until", "unknown"}


def test_raising_collector_reads_unknown_never_previous(tmp_path):
    b = Boom()
    c, clk = make(tmp_path, [b])
    c.tick()
    assert read(c)["machine"]["thermal"]["state"] == 0
    b.raise_now = True
    clk.advance(15)
    c.tick()
    th = read(c)["machine"]["thermal"]
    assert th["unknown"] == "read_failed"
    assert "state" not in th and "low_power" not in th


def test_absent_source_is_absent(tmp_path):
    c, _ = make(tmp_path, [NoBattery()])
    c.tick()
    assert "power" not in read(c)["machine"]


def test_stopped_producer_goes_stale(tmp_path):
    c, clk = make(tmp_path, [Cpu()])
    c.tick()
    s = read(c)
    # nothing writes for 10.1 s: a reader's now passes the file's valid_until
    assert s["written_at"] + 10.1 > s["valid_until"]


def test_off_switch(tmp_path):
    c, clk = make(tmp_path, [Cpu(), Sess()])
    c.tick()
    open(c.off_path, "w").close()
    clk.advance(2)
    c.tick()
    s = read(c)
    assert s["off"] is True and s["sessions"] == [] and s["projects"] == [] and s["machine"] == {}
    assert not list(validator().iter_errors(s))
    seq = s["seq"]
    clk.advance(2)
    assert c.tick() is None             # off: written once, then quiet
    os.remove(c.off_path)
    clk.advance(2)
    c.tick()
    s = read(c)
    assert "off" not in s and s["seq"] > seq and s["sessions"]


def test_collector_switch_disables(tmp_path):
    c, clk = make(tmp_path, [Cpu(), Sess(), Net()])
    with open(c.switch_path, "w") as fh:
        json.dump({"cpu": False, "session_net": False}, fh)
    c.tick()
    s = read(c)
    assert s["machine"]["cpu"]["unknown"] == "disabled"
    assert "net" not in s["sessions"][0]          # session_net off = absent, not unknown


def test_low_power_stops_probes(tmp_path):
    b = Boom()
    c, clk = make(tmp_path, [b, NoBattery()])
    c.shared["low_power"] = True
    c.tick()
    assert read(c)["machine"]["thermal"]["unknown"] == "disabled"


def test_battery_slows_tiers(tmp_path):
    c, clk = make(tmp_path, [Cpu()])
    c.shared["on_battery"] = True
    c.tick()
    s = read(c)
    assert s["cadence_s"]["fast"] == 5.0 and s["valid_until"] - s["written_at"] == pytest.approx(25.0)


class Burn(Collector):
    """Burns a known CPU time per call (reported through a fake thread clock)."""
    name, tier, signals = "burn", "agents", ()

    def collect(self, ctx):
        t = time.thread_time()
        while time.thread_time() - t < 0.05:
            pass
        return {}


def test_cost_meter_reports_known_burn(tmp_path):
    b = Burn()
    c, clk = make(tmp_path, [b])
    for _ in range(10):
        c.tick()
        clk.advance(5)
    lines = c.cost.lines(by="collector")
    span = c.cost.window_s()
    reported_s = lines["burn"] * span / 100.0
    assert reported_s == pytest.approx(0.5, rel=0.2)


class Spawner(Collector):
    name, tier, signals = "spawner", "agents", ()

    def collect(self, ctx):
        import subprocess
        subprocess.run(["/bin/sh", "-c", "i=0; while [ $i -lt 20000 ]; do i=$((i+1)); done"])
        return {}


def test_cost_meter_sees_children(tmp_path):
    core.install_spawn_counter()
    s0 = core.spawns()
    c, clk = make(tmp_path, [Spawner()])
    c.tick()
    assert core.spawns() == s0 + 1
    assert c.cost.lines(by="collector")["spawner"] > 0


def test_collector_over_3x_is_disabled(tmp_path):
    b = Burn()
    b.tier = "counts"           # counts line budget 0.10 %: 50 ms per 5 s is 1 %, > 3x
    c, clk = make(tmp_path, [b])
    for _ in range(140):        # 11+ minutes of evidence (FAIL_MIN_WINDOW_S)
        c.last_run.pop("counts", None)
        c.tick()
        clk.advance(5)
        if "burn" in c.disabled_by_cost:
            break
    assert "burn" in c.disabled_by_cost
    log = open(os.path.join(str(tmp_path), "cost.jsonl")).read()
    assert '"event":"disabled"' in log


def test_verdict_pass_when_cheap(tmp_path):
    c, clk = make(tmp_path, [Cpu()], rate=0.001)   # 0.1 % of one core
    for _ in range(30):
        c.tick()
        clk.advance(2)
    s = read(c)
    assert s["cost"]["verdict"] == "pass"
    assert s["cost"]["cpu_pct_1core_60s"] == pytest.approx(0.1, rel=0.05)


def test_samples_and_audit_written(tmp_path):
    c, clk = make(tmp_path, [Cpu()])
    c.shared["audit"]["iface_rx_bytes"] = 5
    c.tick()
    files = os.listdir(os.path.join(str(tmp_path), "samples"))
    assert len(files) == 1
    a = os.path.join(str(tmp_path), "audit.jsonl")
    assert json.loads(open(a).readline())["audit"]["iface_rx_bytes"] == 5
    assert oct(os.stat(a).st_mode & 0o777) == "0o600"
    assert oct(os.stat(c.snapshot_path).st_mode & 0o777) == "0o600"   # S3: was 0644


IPV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def _numbers_ok(obj):
    """Absence property: no Signal carrying `unknown` also carries a value key."""
    if isinstance(obj, dict):
        if "unknown" in obj:
            assert set(obj) <= {"observed_at", "valid_until", "unknown", "provisional"}, obj
        for v in obj.values():
            _numbers_ok(v)
    elif isinstance(obj, list):
        for v in obj:
            _numbers_ok(v)


def test_privacy_and_absence_property(tmp_path):
    b = Boom()
    c, clk = make(tmp_path, [Cpu(), b, Sess(), Net(), NoBattery()])
    c.tick()
    b.raise_now = True
    clk.advance(15)
    c.tick()
    raw = open(c.snapshot_path).read()
    s = json.loads(raw)
    _numbers_ok(s)
    stripped = re.sub(r'"\d+@\d+"', '""', raw)
    assert "@" not in stripped and "/Users/" not in raw and not IPV4.search(raw)


# --------------------------------------------------------------------------- CONTRACT R1, R5 (2026-11-01)

import hashlib

# C1: the schema's hash is pinned to the version it carries. Changing the schema without
# changing VERSION fails here; whoever bumps the version updates the pin in the same commit.
SCHEMA_PIN = {"1.1": "5991430fe012a715e5ce3c89f26428d6bd40804ed3c520174f21965d6f25847e"}


def _schema_hash():
    with open(SCHEMA_PATH, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def test_c1_schema_hash_is_pinned_to_the_version():
    with open(SCHEMA_PATH) as fh:
        title = json.load(fh)["title"]
    assert core.VERSION in SCHEMA_PIN, "VERSION %s has no schema pin" % core.VERSION
    assert title.endswith(core.VERSION)
    with open(EXAMPLE_PATH) as fh:
        assert json.load(fh)["version"] == core.VERSION
    assert SCHEMA_PIN[core.VERSION] == _schema_hash(), \
        "schema changed under version %s: bump the minor (keys added) or major (meaning changed)" \
        % core.VERSION


class Sess11(Collector):
    """A 1.0+ sessions collector whose `total` is the background count (2d093a3)."""
    name, tier, signals = "sessions", "agents", ("sessions",)

    def collect(self, ctx):
        return {"sessions": [{"id": "100@1793400000", "pid": 100, "started_at": 1793400000.0,
                              "project": "Demo", "project_key": "demo", "managed": False,
                              "tasks": {"shells": 3, "bg_shells": 1, "subagents": 2, "other": 1,
                                        "total": 4, "method": "tree+transcripts"}}]}


def test_c1_total_keeps_its_1_0_meaning_and_background_is_new(tmp_path):
    c, _ = make(tmp_path, [Sess11()])
    c.tick()
    s = read(c)
    t = s["sessions"][0]["tasks"]
    # hand count: 3 shells (foreground and background) + 2 subagents = 5 (DESIGN s11, 1.0);
    # background = 1 bg shell + 2 subagents + 1 other = 4
    assert t["total"] == 5 and t["background"] == 4
    assert s["version"] == "1.1"
    assert not list(validator().iter_errors(s))


class SessFlaky(Collector):
    name, tier, signals = "sessions", "agents", ("sessions",)

    def __init__(self):
        self.mode = "ok"

    def collect(self, ctx):
        if self.mode == "raise":
            raise OSError(2, "No such file", "/Users/someone/.claude/projects/x/y.jsonl")
        ctx.shared["session_trees"] = {"111@5": [111, 112]}
        ctx.shared["session_ids_by_pid"] = {111: "111@5"}
        ctx.shared["transcript_dirs"] = {"111@5": "/somewhere"}
        ctx.shared["sessions_mono"] = ctx.mono
        return {"sessions": [{"id": "111@5", "pid": 111, "started_at": 5.0, "project": "p",
                              "project_key": "p", "managed": False,
                              "load": {"cpu_cores": 0.5, "mem_gb": 0.1, "procs": 2}}]}


def test_c3_sessions_at_stamps_a_measured_list(tmp_path):
    c, clk = make(tmp_path, [SessFlaky()])
    c.tick()
    s = read(c)
    sa = s["sessions_at"]
    assert "unknown" not in sa and sa["observed_at"] == pytest.approx(clk.t)
    assert sa["valid_until"] - sa["observed_at"] == pytest.approx(12.5)    # 2.5 x 5 s agents
    assert [x["id"] for x in s["sessions"]] == ["111@5"]


def test_c3_rb2_failed_sweep_publishes_unknown_never_old_rows(tmp_path):
    f = SessFlaky()
    c, clk = make(tmp_path, [f])
    c.tick()
    f.mode = "raise"
    clk.advance(5)
    c.tick()
    s = read(c)
    assert s["sessions"] == [] and s["sessions_at"]["unknown"] == "read_failed"
    assert [p["key"] for p in s["projects"]] == ["lodestar"]       # the dead session counts nowhere
    for k in ("session_trees", "session_ids_by_pid", "transcript_dirs"):
        assert c.shared[k] == {}, k
    assert "sessions_mono" not in c.shared
    assert not list(validator().iter_errors(s))


def test_c3_rb2_switched_off_sessions_read_disabled_for_days(tmp_path):
    c, clk = make(tmp_path, [SessFlaky()])
    c.tick()
    with open(c.switch_path, "w") as fh:
        json.dump({"sessions": False}, fh)
    for _ in range(3):
        clk.advance(5 * 86400 / 3)
        c.tick()
    s = read(c)
    assert s["sessions"] == [] and s["sessions_at"]["unknown"] == "disabled"
    assert c.shared["session_trees"] == {}


def test_c3_before_first_sweep_is_warming_up(tmp_path):
    c, _ = make(tmp_path, [SessFlaky()])
    c.signals.clear()
    snap = c.assemble(c.clock())
    assert snap["sessions"] == [] and snap["sessions_at"]["unknown"] == "warming_up"


def test_c3_no_sessions_collector_no_sessions_at(tmp_path):
    c, _ = make(tmp_path, [Cpu()])
    c.tick()
    assert "sessions_at" not in read(c)


def test_s3_outputs_are_private(tmp_path):
    c, clk = make(tmp_path, [Cpu()])
    c.tick()
    st = lambda p: oct(os.stat(p).st_mode & 0o777)                     # noqa: E731
    assert st(c.snapshot_path) == "0o600" and st(c.live) == "0o700"
    sd = os.path.join(str(tmp_path), "samples")
    assert st(sd) == "0o700"
    assert all(st(os.path.join(sd, n)) == "0o600" for n in os.listdir(sd))
    core.append_line(os.path.join(str(tmp_path), "cost.jsonl"), {"t": 1})
    assert st(os.path.join(str(tmp_path), "cost.jsonl")) == "0o600"


def test_s3_samples_older_than_keep_days_are_deleted_at_rollover(tmp_path):
    c, clk = make(tmp_path, [Cpu()])
    sd = os.path.join(str(tmp_path), "samples")
    day = lambda t: time.strftime("%Y-%m-%d", time.localtime(t))      # noqa: E731
    old = "snap-%s.jsonl" % day(clk.t - 15 * 86400)
    keep = "snap-%s.jsonl" % day(clk.t - 13 * 86400)
    for n in (old, keep, "notes.txt"):
        open(os.path.join(sd, n), "w").write("{}\n")
    c.tick()
    names = set(os.listdir(sd))
    assert old not in names and keep in names and "notes.txt" in names
    assert "snap-%s.jsonl" % day(clk.t) in names


def test_n1_planted_symlinks_are_not_followed(tmp_path):
    victim = tmp_path / "victim"
    victim.write_text("secret")
    os.chmod(str(victim), 0o600)
    live = tmp_path / "live"
    live.mkdir()
    p = str(live / "snapshot.json")
    for pid in range(os.getpid() - 2, os.getpid() + 3):                 # the old predictable names
        os.symlink(str(victim), "%s.tmp.%d" % (p, pid))
    core.write_atomic(p, b"{}")
    assert victim.read_text() == "secret" and oct(os.stat(str(victim)).st_mode & 0o777) == "0o600"
    assert not os.path.islink(p) and open(p).read() == "{}"
    link = str(tmp_path / "audit.jsonl")
    os.symlink(str(victim), link)
    with pytest.raises(OSError):
        core.append_line(link, {"t": 1})
    assert victim.read_text() == "secret"


def test_n2_existing_file_is_brought_to_its_mode(tmp_path):
    p = str(tmp_path / "audit.jsonl")
    open(p, "w").close()
    os.chmod(p, 0o644)
    core.append_line(p, {"t": 1}, mode=0o600)
    assert oct(os.stat(p).st_mode & 0o777) == "0o600"


def test_n3_logged_exception_carries_no_path(tmp_path, capsys):
    f = SessFlaky()
    c, clk = make(tmp_path, [f])
    f.mode = "raise"
    c.tick()
    err = capsys.readouterr().err
    assert "sessions raised FileNotFoundError errno 2" in err or "sessions raised OSError errno 2" in err
    assert "/Users/" not in err and ".jsonl" not in err


def test_rbm9_identical_error_lines_are_rate_limited(tmp_path, capsys):
    f = SessFlaky()
    f.mode = "raise"
    c, clk = make(tmp_path, [f])
    for _ in range(100):                           # 500 s: one line, not 100
        c.tick()
        clk.advance(5)
    assert capsys.readouterr().err.count("sessions raised") == 1
    clk.advance(core.ERR_REPEAT_S)
    c.tick()
    err = capsys.readouterr().err
    assert err.count("sessions raised") == 1 and "repeated 99 times" in err


def test_rbn14_log_stamp_carries_its_offset(tmp_path, capsys):
    c, _ = make(tmp_path, [Cpu()])
    c._log_err("x")
    line = capsys.readouterr().err
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d{4} augur: x$", line.strip()), line


def test_rb3_deleted_live_and_samples_are_remade(tmp_path):
    import shutil
    c, clk = make(tmp_path, [Cpu()])
    c.tick()
    shutil.rmtree(c.live)
    shutil.rmtree(os.path.join(str(tmp_path), "samples"))
    clk.advance(61)
    c.tick()
    assert os.path.exists(c.snapshot_path) and read(c)["seq"] == 1
    assert len(os.listdir(os.path.join(str(tmp_path), "samples"))) == 1


def test_rbm11_torn_tail_is_not_glued_to_the_next_record(tmp_path, monkeypatch):
    p = str(tmp_path / "cost.jsonl")
    core.append_line(p, {"a": 1})
    real = os.write
    calls = {"n": 0}

    def torn(fd, b):                               # writes 5 bytes, then the disk is full
        calls["n"] += 1
        if calls["n"] == 1:
            return real(fd, bytes(b)[:5])
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(core.os, "write", torn)
    with pytest.raises(OSError):
        core.append_line(p, {"b": 2})
    monkeypatch.setattr(core.os, "write", real)
    assert open(p).read() == '{"a":1}\n'           # truncated back to where it started
    with open(p, "a") as fh:                       # a torn tail written by someone else
        fh.write('{"c":')
    core.append_line(p, {"d": 4})
    assert open(p).read().splitlines()[-1] == '{"d":4}'


def test_rb4_sleep_span_is_logged_to_audit(tmp_path):
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("_r1", os.path.join(HERE, "test_core_cost_r1.py"))
    r1 = ilu.module_from_spec(spec)
    spec.loader.exec_module(r1)
    clk = r1.Clock()
    c = core.Core([r1.Slow(clk, 0.0)], str(tmp_path), home=str(tmp_path), clock=clk.now,
                  mono=clk.mono, lodestar=None, cpu_reader=r1.FakeCPU(clk))
    t_before = {}

    class Mark(Exception):
        pass
    r1.loop(c, clk, 6, wall_jump={3: 3600.0})
    rows = [json.loads(l) for l in open(os.path.join(str(tmp_path), "audit.jsonl"))]
    sl = [r for r in rows if r.get("event") == "slept"]
    assert len(sl) == 1
    # truth: the wall clock ran 3600 s ahead of the monotonic one in the 4th sleep call
    assert sl[0]["slept_s"] == pytest.approx(3600.0, abs=0.2)
    assert sl[0]["to"] - sl[0]["from"] == pytest.approx(3602.0, abs=0.2)


def _lines(p):
    with open(p) as fh:
        return [json.loads(x) for x in fh if x.strip()]


def test_logs_keep_days_retention_at_rollover(tmp_path):
    """cost.jsonl and audit.jsonl lose lines older than LOG_KEEP_DAYS (by each line's own t),
    keep the rest in order, and stay 0600. Truth: the t values this test wrote."""
    c, clk = make(tmp_path, [Cpu()])
    d = 86400.0
    for name in ("cost.jsonl", "audit.jsonl"):
        p = os.path.join(str(tmp_path), name)
        with open(p, "w") as fh:
            for t in (clk.t - 9 * d, clk.t - 8 * d, clk.t - 6 * d, clk.t - 1 * d):
                fh.write(json.dumps({"t": t, "tag": name}) + "\n")
        os.chmod(p, 0o644)
    c.tick()
    for name in ("cost.jsonl", "audit.jsonl"):
        p = os.path.join(str(tmp_path), name)
        ts = [r["t"] for r in _lines(p) if r.get("tag") == name]
        assert ts == [clk.t - 6 * d, clk.t - 1 * d], (name, ts)
        assert oct(os.stat(p).st_mode & 0o777) == "0o600"
    assert any("audit" in r for r in _lines(os.path.join(str(tmp_path), "audit.jsonl")))


def test_logs_size_cap_keeps_the_newest_lines(tmp_path, monkeypatch):
    """A log over LOG_MAX_BYTES is cut to at most that, newest lines kept whole, at the next
    sample, without waiting for the rollover. Truth: the sequence numbers this test wrote."""
    monkeypatch.setattr(core, "LOG_MAX_BYTES", 4096)
    c, clk = make(tmp_path, [Cpu()])
    c.tick()
    p = os.path.join(str(tmp_path), "cost.jsonl")
    with open(p, "a") as fh:
        for i in range(400):
            fh.write(json.dumps({"t": clk.t, "seq": i}) + "\n")
    clk.advance(61)
    c.tick()
    assert os.path.getsize(p) <= 4096
    seqs = [r["seq"] for r in _lines(p) if "seq" in r]
    assert seqs and seqs[-1] == 399 and seqs == list(range(seqs[0], 400))
