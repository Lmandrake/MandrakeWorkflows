"""machine.api from synthetic Claude Code transcripts: error, then ok, then idle; new and rotated
files; a partial last line; subagent files; classification; privacy; cost of a tick. The truth is
the transcript lines each test writes, with their own timestamps."""
import json
import os
import time
from datetime import datetime, timezone

import pytest

from augur.collectors import api as A

T0 = 1793540000.0
SECRET = "the quick brown secret prompt text"


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def ok_line(t):
    return {"type": "assistant", "timestamp": iso(t), "sessionId": "s",
            "message": {"model": "us.anthropic.claude-x", "content": [{"type": "text", "text": SECRET}]}}


def err_line(t, error="server_error", text="API Error: Can't reach the API server (ENOTFOUND)"):
    return {"type": "assistant", "timestamp": iso(t), "sessionId": "s", "isApiErrorMessage": True,
            "error": error, "message": {"model": "<synthetic>", "content": [{"type": "text", "text": text}]}}


def user_line(t):
    return {"type": "user", "timestamp": iso(t), "message": {"content": SECRET}}


class W(object):
    def __init__(self, tmp):
        self.home = str(tmp)
        self.pdir = os.path.join(self.home, ".claude", "projects", "-x-Repo")
        os.makedirs(self.pdir)
        self.c = A.ApiCollector()
        self.shared = {"transcript_dirs": {"1@1": self.pdir}}

    def path(self, name="sess-a", sub=None):
        if sub:
            d = os.path.join(self.pdir, name, "subagents")
            os.makedirs(d, exist_ok=True)
            return os.path.join(d, sub + ".jsonl")
        return os.path.join(self.pdir, name + ".jsonl")

    def write(self, recs, name="sess-a", sub=None, raw=None, mode="a", mtime=None):
        p = self.path(name, sub)
        with open(p, mode) as fh:
            for r in recs:
                fh.write(json.dumps(r) + "\n")
            if raw:
                fh.write(raw)
        t = mtime if mtime is not None else T0
        os.utime(p, (t, t))
        return p

    def tick(self, now, mono=None):
        class C(object):
            pass
        c = C()
        c.now, c.home, c.shared = now, self.home, self.shared
        c.mono = now if mono is None else mono
        if not getattr(self, "pin_mono", False):
            self.shared["sessions_mono"] = c.mono
        for p in self.c.files:
            if os.path.exists(p):
                os.utime(p, (now, now))
        return self.c.collect(c).get("machine.api")


def test_error_then_ok_then_idle(tmp_path):
    w = W(tmp_path)
    w.write([user_line(T0 - 30), ok_line(T0 - 20)])
    v = w.tick(T0)
    assert v["state"] == "ok" and v["last_ok_at"] == pytest.approx(T0 - 20, abs=0.01)
    w.write([err_line(T0 + 1)], mtime=T0 + 1)
    v = w.tick(T0 + 2)
    assert v["state"] == "failing" and v["failing_sessions"] == 1 and v["error_kind"] == "network"
    assert v["last_error_at"] == pytest.approx(T0 + 1, abs=0.01)
    w.write([ok_line(T0 + 10)], mtime=T0 + 10)
    v = w.tick(T0 + 11)
    assert v["state"] == "ok" and v["failing_sessions"] == 0
    assert w.tick(T0 + 10 + A.ACTIVE_S + 1) is None       # idle: absent, never "ok"


def test_error_ages_out_to_absent_not_ok(tmp_path):
    w = W(tmp_path)
    w.write([err_line(T0)])
    assert w.tick(T0 + 1)["state"] == "failing"
    assert w.tick(T0 + A.HOLD_S + 1) is None             # R2-3: held, then absent (not ok)


def test_ok_in_another_session_clears_failing(tmp_path):
    w = W(tmp_path)
    w.write([err_line(T0)], name="sess-a")
    w.write([ok_line(T0 + 3)], name="sess-b")
    v = w.tick(T0 + 4)
    assert v["state"] == "ok" and v["failing_sessions"] == 1   # a's newest outcome is still an error


def test_partial_last_line_waits_for_its_newline(tmp_path):
    w = W(tmp_path)
    w.write([ok_line(T0 - 5)])
    half = json.dumps(err_line(T0))
    w.write([], raw=half[:40])
    assert w.tick(T0 + 1)["state"] == "ok"
    w.write([], raw=half[40:] + "\n")
    assert w.tick(T0 + 2)["state"] == "failing"


def test_new_file_and_subagent_file_are_picked_up(tmp_path):
    w = W(tmp_path)
    w.write([ok_line(T0 - 5)])
    w.tick(T0)
    w.write([err_line(T0 + 1, text="API Error: Rate limit reached (429)")], name="sess-a", sub="agent-1")
    v = w.tick(T0 + A.RESCAN_S + 1)
    assert v["state"] == "failing" and v["error_kind"] == "rate_limit"


def test_rotated_file_is_read_from_its_start(tmp_path):
    w = W(tmp_path)
    p = w.write([ok_line(T0 - 5)] * 50)
    w.tick(T0)
    os.remove(p)
    w.write([err_line(T0 + 1)], mode="w")                 # replaced: new inode, smaller
    assert w.tick(T0 + 2)["state"] == "failing"


def test_only_appended_bytes_are_read(tmp_path, monkeypatch):
    w = W(tmp_path)
    w.write([ok_line(T0 - 5)] * 2000)
    w.tick(T0)
    seen = []
    real = A.parse_line
    monkeypatch.setattr(A, "parse_line", lambda raw: seen.append(raw) or real(raw))
    w.write([ok_line(T0 + 1)])
    w.tick(T0 + 2)
    assert len(seen) == 1


def test_first_sight_reads_only_the_tail(tmp_path):
    w = W(tmp_path)
    w.write([err_line(T0 - 9000)] * 400 + [ok_line(T0 - 5)])
    assert w.tick(T0)["state"] == "ok"
    assert w.c.tails[w.path()].off == os.path.getsize(w.path())


def test_classification():
    assert A.classify("server_error", "API Error: Can't reach the API server (ENOTFOUND)") == "network"
    assert A.classify("server_error", "API Error: Connection lost mid-response.") == "network"
    assert A.classify("unknown", "API Error: Request rejected (429)") == "rate_limit"
    assert A.classify("server_error", "API Error: 529 Overloaded") == "rate_limit"
    assert A.classify("server_error", "API Error: 500 internal") == "server"
    assert A.classify("authentication_failed", "Not logged in") == "other"


def test_privacy_no_text_paths_or_ids(tmp_path):
    w = W(tmp_path)
    w.write([user_line(T0 - 2), err_line(T0 - 1, text="API Error: " + SECRET), ok_line(T0)])
    blob = json.dumps(w.tick(T0 + 1))
    for bad in (SECRET, "sess-a", w.pdir, "/", "Error"):
        assert bad not in blob, bad


def test_tick_cost_is_small(tmp_path):
    w = W(tmp_path)
    for i in range(10):
        w.write([ok_line(T0 - 5)] * 300, name="s%d" % i)
    w.tick(T0)
    for i in range(10):
        w.write([ok_line(T0 + 1)], name="s%d" % i)
    t = time.thread_time()
    w.tick(T0 + 2)
    assert time.thread_time() - t < 0.01                 # 10 live transcripts: under 10 ms


def test_snapshot_validates_and_idle_is_absent(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    from augur import core
    from augur.collectors.base import Collector
    w = W(tmp_path)
    w.write([err_line(T0 - 1)])
    clk = {"t": T0}

    class Dirs(Collector):
        name, tier, signals = "sessions", "agents", ()

        def collect(self, ctx):
            ctx.shared["transcript_dirs"] = {"1@1": w.pdir}
            ctx.shared["sessions_mono"] = ctx.mono
            return {}
    c = core.Core([Dirs(), A.ApiCollector()], str(tmp_path / "aug"), home=w.home,
                  clock=lambda: clk["t"], mono=lambda: clk["t"], lodestar=None,
                  cpu_reader=lambda: (0.0, 0.0, 1000))
    c.tick()
    snap = json.load(open(c.snapshot_path))
    schema = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                         "schema", "snapshot.schema.json")))
    assert not list(jsonschema.Draft202012Validator(schema).iter_errors(snap))
    assert snap["machine"]["api"]["state"] == "failing"
    assert snap["machine"]["api"]["valid_until"] - snap["machine"]["api"]["observed_at"] == pytest.approx(12.5)
    clk["t"] = T0 + 600
    c.last_run.clear()
    c.tick()
    assert "api" not in json.load(open(c.snapshot_path))["machine"]


def test_subagent_file_in_an_old_subagents_dir_is_seen(tmp_path):
    # a directory's mtime moves only when entries are added, not when a file in it grows
    w = W(tmp_path)
    w.write([ok_line(T0 - 4000)], mtime=T0 - 4000)                 # parent transcript idle
    p = w.write([ok_line(T0 - 4000)], sub="agent-1", mtime=T0 - 4000)
    sub = os.path.dirname(p)
    os.utime(sub, (T0 - 4000, T0 - 4000))
    with open(p, "a") as fh:
        fh.write(json.dumps(err_line(T0 - 1)) + "\n")
    os.utime(p, (T0, T0))
    os.utime(sub, (T0 - 4000, T0 - 4000))
    assert w.tick(T0)["state"] == "failing"


# --------------------------------------------------------------------------- review R2

class Resolver(object):
    """Injected DNS: fails while .down is True. The truth is the test's own outage switch."""

    def __init__(self):
        self.down, self.calls = False, 0

    def __call__(self, host):
        self.calls += 1
        if self.down:
            import socket
            raise socket.gaierror(8, "nodename nor servname provided")
        return True


def busy_world(tmp_path, resolver):
    w = W(tmp_path)
    w.c = A.ApiCollector(resolver=resolver, base_url=lambda: "https://api.example.invalid")
    w.shared["session_ids_by_pid"] = {1: "1@1"}
    w.shared["sessions_mono"] = 0.0
    sd = os.path.join(w.home, ".claude", "sessions")
    os.makedirs(sd, exist_ok=True)
    w.busy = lambda b: json.dump({"pid": 1, "status": "busy" if b else "idle"},
                                 open(os.path.join(sd, "1.json"), "w"))
    w.busy(True)
    return w


def tick_m(w, now):
    return w.tick(now)


def test_r2_3_failing_within_seconds_of_the_outage(tmp_path):
    """The transcript error line arrives ~3 min into an outage (Claude Code retries first). A busy
    session whose API host stops resolving must read failing within two agents ticks."""
    res = Resolver()
    w = busy_world(tmp_path, res)
    w.write([ok_line(T0 - 2)])
    assert tick_m(w, T0)["state"] == "ok"
    res.down = True                                      # the outage starts at T0 + 1
    tick_m(w, T0 + 5)
    v = tick_m(w, T0 + 10)
    assert v["state"] == "failing" and v["error_kind"] == "network"
    for t in range(15, 200, 5):                          # no transcript line for 3 minutes
        assert tick_m(w, T0 + t)["state"] == "failing", t
    w.write([err_line(T0 + 200)], mtime=T0 + 200)        # Claude Code finally writes its error
    assert tick_m(w, T0 + 201)["state"] == "failing"


def test_r2_3_failing_holds_until_a_success(tmp_path):
    res = Resolver()
    w = busy_world(tmp_path, res)
    w.busy(False)                                        # the turn ended on the error
    w.write([err_line(T0)])
    for t in (1, 61, 300, 590):
        assert tick_m(w, T0 + t)["state"] == "failing", t   # was absent after 60 s
    w.write([ok_line(T0 + 595)], mtime=T0 + 595)
    assert tick_m(w, T0 + 596)["state"] == "ok"


def test_r2_3_hold_is_bounded(tmp_path):
    w = busy_world(tmp_path, Resolver())
    w.busy(False)
    w.write([err_line(T0)])
    assert tick_m(w, T0 + A.HOLD_S + 5) is None


def test_r2_3_resolver_not_used_while_idle(tmp_path):
    res = Resolver()
    w = busy_world(tmp_path, res)
    w.busy(False)
    res.down = True
    w.write([ok_line(T0 - 300)], mtime=T0 - 300)
    assert tick_m(w, T0) is None and res.calls == 0      # idle: unmeasured, no probe


def test_r2_3_one_failed_resolve_is_not_an_outage(tmp_path):
    res = Resolver()
    w = busy_world(tmp_path, res)
    w.write([ok_line(T0 - 2)])
    tick_m(w, T0)
    res.down = True
    v1 = tick_m(w, T0 + 5)
    res.down = False
    v2 = tick_m(w, T0 + 10)
    assert v1["state"] == "ok" and v2["state"] == "ok"


def test_r2_4_network_error_not_masked_by_another_sessions_error(tmp_path):
    w = W(tmp_path)
    w.write([err_line(T0)], name="sess-a")
    w.write([err_line(T0 + 1, error="invalid_request", text="API Error: 400 bad request")], name="sess-b")
    v = w.tick(T0 + 2)
    assert v["state"] == "failing" and v["error_kind"] == "network"


def test_r2_5_truncate_and_regrow_same_inode(tmp_path):
    w = W(tmp_path)
    p = w.write([ok_line(T0 - 5)] * 3)
    w.tick(T0)
    with open(p, "r+") as fh:                             # same inode, rewritten larger
        fh.truncate(0)
        fh.write(json.dumps(err_line(T0 + 1)) + "\n" + json.dumps(user_line(T0 + 1)) * 2 + "\n")
    os.utime(p, (T0 + 1, T0 + 1))
    assert w.tick(T0 + 2)["state"] == "failing"


def test_r2_10_stale_transcript_dirs_are_ignored(tmp_path):
    w = W(tmp_path)
    w.shared["sessions_mono"] = T0 - 600                  # sessions collector failing since
    w.pin_mono = True
    w.write([err_line(T0)])
    assert w.tick(T0 + 1) is None


def test_r2_11_assistant_line_without_model_is_not_a_success(tmp_path):
    w = W(tmp_path)
    w.write([err_line(T0), {"type": "assistant", "timestamp": iso(T0 + 1), "message": {}}])
    assert w.tick(T0 + 2)["state"] == "failing"


def test_r2_13_huge_good_line_still_counts(tmp_path):
    w = W(tmp_path)
    w.write([err_line(T0 - 1)])
    w.tick(T0)
    big = ok_line(T0 + 1)
    big["message"]["content"][0]["text"] = "x" * (3 * 1024 * 1024)
    w.write([big], mtime=T0 + 1)
    assert w.tick(T0 + 2)["state"] == "ok"


def test_r2_14_first_sight_keeps_a_record_on_the_boundary(tmp_path):
    w = W(tmp_path)
    line = json.dumps(err_line(T0)) + "\n"
    p = w.path()
    with open(p, "w") as fh:
        fh.write(json.dumps(user_line(T0 - 9)) + "\n")
        mark = fh.tell()
        fh.write(line)                                    # starts at byte `mark`
        fh.write("u" * (A.TAIL_BYTES - len(line) - 1) + "\n")
    os.utime(p, (T0, T0))
    assert os.path.getsize(p) - A.TAIL_BYTES == mark      # the tail starts exactly on the record
    assert w.tick(T0 + 1)["state"] == "failing"


def test_r2_15_equal_timestamps_later_line_wins(tmp_path):
    w = W(tmp_path)
    w.write([err_line(T0), ok_line(T0)])
    assert w.tick(T0 + 1)["state"] == "ok"
    w2 = W(tmp_path / "b")
    w2.write([ok_line(T0), err_line(T0)])
    assert w2.tick(T0 + 1)["state"] == "failing"


def test_r2_3_retry_lines_count_when_present(tmp_path):
    w = W(tmp_path)
    w.write([ok_line(T0 - 30), {"type": "system", "subtype": "api_error", "timestamp": iso(T0),
                                "retryAttempt": 1, "error": {"cause": {"code": "ENOTFOUND"}}}])
    v = w.tick(T0 + 1)
    assert v["state"] == "failing" and v["error_kind"] == "network"


# --------------------------------------------------------------------------- review R3

def test_r3_3_good_probe_does_not_clear_a_transcript_failure(tmp_path):
    """A mid-stream failure ("Connection lost") with the host still reachable: the transcript is
    the stronger evidence. Only a later good assistant line clears it."""
    res = Resolver()
    w = busy_world(tmp_path, res)
    w.write([ok_line(T0 - 30)])
    tick_m(w, T0 - 20)
    w.write([err_line(T0, text="API Error: Connection lost mid-response.")], mtime=T0)
    for t in (1, 6, 11, 30):
        assert tick_m(w, T0 + t)["state"] == "failing", t
    w.write([ok_line(T0 + 40)], mtime=T0 + 40)
    assert tick_m(w, T0 + 41)["state"] == "ok"


def test_r3_3_probe_ok_alone_reads_ok_only_without_transcript_evidence(tmp_path):
    """R4-7: exact verdicts. (a) No transcript evidence at all, probe good: absent (a TCP
    handshake is not a good call). (b) A transcript error, probe good: failing."""
    res = Resolver()
    w = busy_world(tmp_path, res)
    w.write([user_line(T0 - 1)])                          # the transcript exists, no API outcome
    assert tick_m(w, T0) is None
    assert tick_m(w, T0 + 5) is None
    w.write([err_line(T0 + 6)], mtime=T0 + 6)
    assert tick_m(w, T0 + 10)["state"] == "failing"


def test_r3_4_probe_honours_the_url_port(tmp_path):
    import socket
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(4)
    port = srv.getsockname()[1]
    try:
        assert A._reach_url("http://127.0.0.1:%d/v1" % port, 3.0) is True
    finally:
        srv.close()
    assert A._port_of("https://h.example") == 443 and A._port_of("http://h.example") == 80
    assert A._port_of("http://h.example:4000") == 4000


def test_r3_5_missing_base_url_reads_env_missing_once(tmp_path, capsys):
    w = W(tmp_path)
    w.c = A.ApiCollector(base_url=lambda: None)
    w.shared["session_ids_by_pid"] = {1: "1@1"}
    sd = os.path.join(w.home, ".claude", "sessions")
    os.makedirs(sd, exist_ok=True)
    json.dump({"pid": 1, "status": "busy"}, open(os.path.join(sd, "1.json"), "w"))
    w.write([user_line(T0 - 2)])                          # R5-12: no transcript verdict
    v1 = w.tick(T0)
    v2 = w.tick(T0 + 5)
    assert v1 == {"unknown": "env_missing"} and v2 == {"unknown": "env_missing"}
    err = capsys.readouterr().err
    assert err.count("ANTHROPIC_BASE_URL") == 1


def test_r3_5_outage_ages_out_when_the_probe_stops(tmp_path):
    """R4-7: R3-5's real case. While BUSY, the URL disappears after a probe outage: the probe
    stops, the outage must age out (no frozen `fails`), and the reason is env_missing."""
    res = Resolver()
    url = {"u": "https://api.example.invalid"}
    w = busy_world(tmp_path, res)
    w.c.base_url = lambda: url["u"]
    w.write([ok_line(T0 - 2)])
    tick_m(w, T0)
    res.down = True
    tick_m(w, T0 + 5)
    assert tick_m(w, T0 + 10)["state"] == "failing"
    url["u"] = None                                       # still busy
    assert tick_m(w, T0 + 15)["state"] == "ok"           # R5-12: the transcript's ok stands
    url["u"] = "https://api.example.invalid"
    res.down = False
    assert tick_m(w, T0 + 10 + A.HOLD_S + 5) is None     # not a frozen outage


def test_r3_6_hanging_dns_is_a_failure_within_the_bound(tmp_path):
    """getaddrinfo that never answers: the probe must count as failed at PROBE_BOUND_S."""
    import threading
    gate = threading.Event()
    w = W(tmp_path)
    clock = {"t": T0}
    w.c = A.ApiCollector(base_url=lambda: "https://api.example.invalid",
                         reach=lambda url, timeout: gate.wait(60) or False,
                         clock=lambda: clock["t"], mono=lambda: clock["t"])
    w.shared["session_ids_by_pid"] = {1: "1@1"}
    sd = os.path.join(w.home, ".claude", "sessions")
    os.makedirs(sd, exist_ok=True)
    json.dump({"pid": 1, "status": "busy"}, open(os.path.join(sd, "1.json"), "w"))
    w.write([ok_line(T0 - 2)])
    states = []
    for t in range(0, 30, 5):
        clock["t"] = T0 + t
        v = w.tick(T0 + t)
        states.append((t, v and v.get("state")))
    gate.set()
    first = next(t for t, s in states if s == "failing")
    # two failures, each bounded at PROBE_BOUND_S, seen on 5 s agents ticks: <= 10 s, as claimed
    assert first <= 10, states


def test_r3_7_probe_cpu_is_drained_to_the_line(tmp_path):
    w = W(tmp_path)
    w.c = A.ApiCollector(base_url=lambda: "https://x.invalid", reach=lambda u, t: True)
    w.c._worker_cpu = 0.004
    assert w.c.drain_worker_cpu() == pytest.approx(0.004) and w.c.drain_worker_cpu() == 0.0


def test_r3_9_truncate_and_regrow_larger_than_old_offset(tmp_path):
    """R2-5's real case: rewritten in place LARGER than the old offset."""
    w = W(tmp_path)
    p = w.write([ok_line(T0 - 5)] * 3)
    w.tick(T0)
    old = os.path.getsize(p)
    with open(p, "r+") as fh:
        fh.truncate(0)
        fh.write(json.dumps(err_line(T0 + 1)) + "\n" + json.dumps(user_line(T0 + 1)) * 6 + "\n")
    os.utime(p, (T0 + 1, T0 + 1))
    assert os.path.getsize(p) > old
    assert w.tick(T0 + 2)["state"] == "failing"


def test_r3_10_probe_backs_off_while_the_transcript_is_live(tmp_path):
    calls = []
    w = W(tmp_path)
    w.c = A.ApiCollector(base_url=lambda: "https://x.invalid",
                         resolver=lambda h: calls.append(h) or True)
    w.shared["session_ids_by_pid"] = {1: "1@1"}
    sd = os.path.join(w.home, ".claude", "sessions")
    os.makedirs(sd, exist_ok=True)
    json.dump({"pid": 1, "status": "busy"}, open(os.path.join(sd, "1.json"), "w"))
    for t in range(0, 60, 5):                              # a good call every 5 s
        w.write([ok_line(T0 + t)], mtime=T0 + t)
        w.tick(T0 + t + 1)
    assert len(calls) <= 60 / A.PROBE_SPACING_S + 1


# --------------------------------------------------------------------------- review R4

def test_r4_4_hung_worker_is_abandoned_and_a_later_probe_clears(tmp_path):
    """R4-4 under R5-8/R5-9 (joins, no sleeps): the first probe hangs; it is abandoned at the
    bound and, while it stays hung, due probes count as failed (failing). Once it has returned, a
    fresh worker runs and its good answer clears the probe-made outage."""
    import threading
    gate = threading.Event()
    calls = {"n": 0}

    def reach(url, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            gate.wait(60)                                 # a probe that does not return
            return False
        return True
    clock = {"m": 0.0}
    w = W(tmp_path)
    c = w.c = A.ApiCollector(base_url=lambda: "https://x.invalid", reach=reach,
                             mono=lambda: clock["m"])
    busy_one(w)
    states = []
    for t in range(0, 20, 5):
        clock["m"] = float(t)
        v = w.tick(T0 + t)
        states.append(v and v.get("state"))
    assert "failing" in states and calls["n"] == 1, states
    p = c._probes["https://x.invalid"]
    gate.set()
    p.hung.join(10)                                       # the hung worker has returned
    for t in range(20, 35, 5):
        clock["m"] = float(t)
        v = w.tick(T0 + t)
        states.append(v and v.get("state"))
        settle(c)
    assert states[-1] != "failing" and calls["n"] >= 2, states   # cleared by a later probe


def test_r4_5a_missing_url_does_not_hide_a_transcript_failure(tmp_path):
    w = W(tmp_path)
    w.c = A.ApiCollector(base_url=lambda: None)
    w.shared["session_ids_by_pid"] = {1: "1@1"}
    sd = os.path.join(w.home, ".claude", "sessions")
    os.makedirs(sd, exist_ok=True)
    json.dump({"pid": 1, "status": "busy"}, open(os.path.join(sd, "1.json"), "w"))
    w.write([err_line(T0 - 1)])
    v = w.tick(T0)
    assert v["state"] == "failing" and v["error_kind"] == "network"


def test_r4_5b_good_calls_clear_a_probe_made_outage(tmp_path):
    res = Resolver()
    w = busy_world(tmp_path, res)
    w.write([user_line(T0 - 1)])
    res.down = True
    tick_m(w, T0)
    assert tick_m(w, T0 + 5)["state"] == "failing"        # probe outage, no API outcome yet
    w.write([ok_line(T0 + 8)], mtime=T0 + 8)              # a real-model good call lands
    assert tick_m(w, T0 + 10)["state"] == "ok"


def test_r4_10_finished_result_is_read_at_once(tmp_path):
    w = W(tmp_path)
    w.c = A.ApiCollector(base_url=lambda: "https://x.invalid", reach=lambda u, t: False)
    w.shared["session_ids_by_pid"] = {1: "1@1"}
    sd = os.path.join(w.home, ".claude", "sessions")
    os.makedirs(sd, exist_ok=True)
    json.dump({"pid": 1, "status": "busy"}, open(os.path.join(sd, "1.json"), "w"))
    seen = []
    for t in range(0, 30, 5):                             # good calls keep the probe sparse
        w.write([ok_line(T0 + t)], mtime=T0 + t)
        w.tick(T0 + t + 1)
        settle(w.c)                                       # R5-9: a join, not a 20 ms sleep
        seen.append(w.c.fails)
    assert seen[1] >= 1, seen                             # the first result is read next tick


def test_r4_11_malformed_urls_read_as_config_errors(tmp_path):
    for bad in ("host.example:4000", "https://h:abc/", "ftp://", "not a url"):
        w = W(tmp_path / str(abs(hash(bad))))
        w.c = A.ApiCollector(base_url=lambda b=bad: b, reach=lambda u, t: True)
        w.shared["session_ids_by_pid"] = {1: "1@1"}
        sd = os.path.join(w.home, ".claude", "sessions")
        os.makedirs(sd, exist_ok=True)
        json.dump({"pid": 1, "status": "busy"}, open(os.path.join(sd, "1.json"), "w"))
        w.write([user_line(T0 - 1)])                     # R5-12: no transcript verdict
        assert w.tick(T0) == {"unknown": "env_invalid"}, bad


# --------------------------------------------------------------------------- review R5

def busy_one(w, pid=1):
    w.shared["session_ids_by_pid"] = {pid: "%d@1" % pid}
    sd = os.path.join(w.home, ".claude", "sessions")
    os.makedirs(sd, exist_ok=True)
    with open(os.path.join(sd, "%d.json" % pid), "w") as fh:
        json.dump({"pid": pid, "status": "busy"}, fh)


def settle(c):
    """Wait for every probe worker that is meant to return (join, never a sleep)."""
    for p in list(c._probes.values()):
        th = p.thread
        if th is not None:
            th.join(10)


def test_r5_1_nested_error_flag_in_a_big_record_is_not_an_error(tmp_path):
    """A real-model good call whose tool_use input carries "isApiErrorMessage": true (and a
    timestamp) near its end, over READ_CAP, keys in Claude Code's own order (message first).
    Truth: a good call at T0 + 1."""
    w = W(tmp_path)
    w.write([user_line(T0 - 1)])
    w.tick(T0)
    big = {"parentUuid": None,
           "message": {"model": "us.anthropic.claude-x",
                       "content": [{"type": "tool_use", "input": {
                           "pad": "x" * (A.READ_CAP + 4096), "isApiErrorMessage": True,
                           "timestamp": iso(T0 - 5000)}}]},
           "type": "assistant", "timestamp": iso(T0 + 1), "sessionId": "s"}
    w.write([big], mtime=T0 + 1)
    v = w.tick(T0 + 2)
    assert v["state"] == "ok" and v["last_ok_at"] == pytest.approx(T0 + 1, abs=0.01), v


def test_r5_1_top_level_flag_in_a_big_record_still_counts():
    head = json.dumps({"type": "assistant", "timestamp": iso(T0), "isApiErrorMessage": True,
                       "error": "unknown", "message": {"model": "<synthetic>", "content": "x"}})
    raw = A.BIG + head.encode() + b"\n" + head.encode()
    assert A.parse_line(raw) == ("other", pytest.approx(T0, abs=0.01))
    nested = json.dumps({"type": "assistant", "timestamp": iso(T0),
                         "message": {"model": "m", "content": [{"isApiErrorMessage": True}]}})
    assert A.parse_line(A.BIG + nested.encode() + b"\n" + nested.encode())[0] == "ok"


def test_r5_2_malformed_error_line_does_not_lose_the_next_line(tmp_path):
    """GPT G9: an error line whose text is a number, then a real network error. Truth: failing,
    network; no exception out of collect."""
    w = W(tmp_path)
    bad = {"type": "assistant", "timestamp": iso(T0 - 2), "isApiErrorMessage": True,
           "message": {"content": [{"text": 1}]}}
    w.write([ok_line(T0 - 5), bad, err_line(T0 - 1)])
    v = w.tick(T0)
    assert v["state"] == "failing" and v["error_kind"] == "network", v


def test_r5_s2_deeply_nested_line_does_not_drop_the_batch(tmp_path):
    """S2: an assistant line nested 20,000 deep (RecursionError in json.loads), then an error."""
    w = W(tmp_path)
    deep = ('{"type": "assistant", "timestamp": "%s", "message": {"model": "m", "content": %s%s}}'
            % (iso(T0 - 2), "[" * 20000, "]" * 20000))
    p = w.write([ok_line(T0 - 5)], raw=deep + "\n")
    with open(p, "a") as fh:
        fh.write(json.dumps(err_line(T0 - 1)) + "\n")
    os.utime(p, (T0, T0))
    v = w.tick(T0)
    assert v["state"] == "failing" and v["error_kind"] == "network", v


def test_r5_3_read_after_truncation_to_empty(tmp_path):
    """GPT G7b: truncated to 0 bytes, then an error appended. Truth: failing."""
    w = W(tmp_path)
    p = w.write([ok_line(T0 - 5)] * 3)
    w.tick(T0)
    open(p, "w").close()
    os.utime(p, (T0 + 1, T0 + 1))
    w.tick(T0 + 1)
    w.write([err_line(T0 + 2)], mtime=T0 + 2)
    assert w.tick(T0 + 3)["state"] == "failing"


def test_r5_s1_fifo_transcript_does_not_block_the_tick(tmp_path):
    """S1: a FIFO named *.jsonl under subagents. The tick runs on a helper thread; if it blocks
    past the join, the test opens the FIFO's write end to release it, then fails."""
    import threading
    w = W(tmp_path)
    w.write([err_line(T0 - 1)])
    fifo = w.path(sub="agent-x")
    os.mkfifo(fifo)
    os.utime(fifo, (T0, T0))
    out = {}
    th = threading.Thread(target=lambda: out.setdefault("v", w.tick(T0)), daemon=True)
    th.start()
    th.join(10)
    blocked = th.is_alive()
    if blocked:
        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        os.close(fd)
        th.join(10)
    assert not blocked, "the tick blocked in open() on a FIFO"
    assert out["v"]["state"] == "failing"
    assert fifo not in w.c.files or fifo not in w.c.tails


def test_r5_9_result_published_before_the_bound_check_counts_once(tmp_path):
    """GPT C4, deterministic: the injected mono() releases worker A and joins it inside the bound
    check. Truth: one probe finished (failed), so fails == 1 at t=6 and t=8, never failing."""
    import threading
    gates = [threading.Event(), threading.Event()]
    calls = []

    def reach(url, timeout):
        i = len(calls)
        calls.append(i)
        gates[min(i, 1)].wait(30)
        return False
    clock = {"m": 0.0, "hook": False}
    box = {}

    def mono():
        if clock["hook"]:
            clock["hook"] = False
            gates[0].set()
            box["c"]._probes["https://x.invalid"].thread.join(10)   # A publishes now
        return clock["m"]
    w = W(tmp_path)
    c = box["c"] = w.c = A.ApiCollector(base_url=lambda: "https://x.invalid", reach=reach, mono=mono)
    busy_one(w)
    w.tick(T0)                                            # starts A
    clock["m"], clock["hook"] = 6.0, True
    v6 = w.tick(T0 + 6)
    f6 = c._probes["https://x.invalid"].fails
    clock["m"] = 8.0
    v8 = w.tick(T0 + 8)
    f8 = c._probes["https://x.invalid"].fails
    gates[1].set()
    settle(c)
    assert (f6, f8) == (1, 1), (f6, f8)
    assert (v6 or {}).get("state") != "failing" and (v8 or {}).get("state") != "failing"


def test_r5_9_result_published_after_abandonment_is_dropped(tmp_path):
    """A answers after it was abandoned at t=6: dropped. B starts at t=8 and fails: fails 1, 1, 2."""
    import threading
    gates = [threading.Event(), threading.Event()]
    calls = []

    def reach(url, timeout):
        i = len(calls)
        calls.append(i)
        gates[min(i, 1)].wait(30)
        return False
    clock = {"m": 0.0}
    w = W(tmp_path)
    c = w.c = A.ApiCollector(base_url=lambda: "https://x.invalid", reach=reach, mono=lambda: clock["m"])
    busy_one(w)
    w.tick(T0)
    p = c._probes["https://x.invalid"]
    a = p.thread
    clock["m"] = 6.0
    w.tick(T0 + 6)                                        # A abandoned: fails 1
    f = [p.fails]
    gates[0].set()
    a.join(10)                                            # A publishes late: must be dropped
    clock["m"] = 8.0
    w.tick(T0 + 8)                                        # B starts
    f.append(p.fails)
    gates[1].set()
    settle(c)
    clock["m"] = 10.0
    v = w.tick(T0 + 10)                                   # B's failure read
    f.append(p.fails)
    assert f == [1, 1, 2] and len(calls) == 2, (f, calls)
    assert v["state"] == "failing"


def test_r5_8_hung_resolver_keeps_one_worker(tmp_path):
    """RB1/R5-8: a reach that blocks for 10 min, ticked every 5 s. Truth: one worker ever
    started (at most one abandoned thread alive), and the hang reads as an outage (R3-6)."""
    import threading
    gate = threading.Event()
    started = []

    def reach(url, timeout):
        started.append(threading.current_thread())
        gate.wait(120)
        return False
    clock = {"m": 0.0}
    w = W(tmp_path)
    c = w.c = A.ApiCollector(base_url=lambda: "https://x.invalid", reach=reach, mono=lambda: clock["m"])
    busy_one(w)
    states = []
    for t in range(0, 600, 5):
        clock["m"] = float(t)
        v = w.tick(T0 + t)
        states.append(v and v.get("state"))
    alive = [th for th in started if th.is_alive()]
    gate.set()
    for th in started:
        th.join(10)
    assert len(started) == 1 and len(alive) <= 1, (len(started), len(alive))
    assert states[2:] == ["failing"] * (len(states) - 2), states[:6]


def test_r5_8_hung_worker_with_good_calls_reads_the_transcript(tmp_path):
    """While the one abandoned worker hangs, good calls keep landing: the probe cannot tell, so
    the transcript's ok stands (no flapping into failing)."""
    import threading
    gate = threading.Event()

    def reach(url, timeout):
        gate.wait(120)
        return False
    clock = {"m": 0.0}
    w = W(tmp_path)
    c = w.c = A.ApiCollector(base_url=lambda: "https://x.invalid", reach=reach, mono=lambda: clock["m"])
    busy_one(w)
    states = []
    for t in range(0, 120, 5):
        clock["m"] = float(t)
        w.write([ok_line(T0 + t)], mtime=T0 + t)
        v = w.tick(T0 + t + 1)
        states.append(v and v.get("state"))
    gate.set()
    settle(c)
    for p in c._probes.values():
        if p.hung is not None:
            p.hung.join(10)
    assert states[3:] == ["ok"] * (len(states) - 3), states


def test_r5_m10_internal_fault_in_the_worker_is_not_an_outage(tmp_path, capsys):
    """RB-m10: reach raises ImportError (an interpreter removed under the agent). Truth: no
    network evidence, so never failing; unknown read_failed, logged once."""
    def reach(url, timeout):
        raise ImportError("No module named 'encodings.idna'")
    w = W(tmp_path)
    c = w.c = A.ApiCollector(base_url=lambda: "https://x.invalid", reach=reach)
    busy_one(w)
    vs = []
    for t in range(0, 30, 5):
        vs.append(w.tick(T0 + t))
        settle(c)
    assert all(v is None or v.get("state") != "failing" for v in vs), vs
    assert vs[-1] == {"unknown": "read_failed"}, vs
    assert capsys.readouterr().err.count("read_failed") == 1


def test_r5_15_result_completed_after_the_bound_but_before_the_poll_is_accepted(tmp_path):
    """Accepted behaviour: an answer that arrived at 5.5 s and is read at 6 s is the answer."""
    import threading
    gate = threading.Event()
    w = W(tmp_path)
    clock = {"m": 0.0}
    c = w.c = A.ApiCollector(base_url=lambda: "https://x.invalid",
                             reach=lambda u, t: gate.wait(30) and True, mono=lambda: clock["m"])
    busy_one(w)
    w.tick(T0)
    gate.set()
    settle(c)
    clock["m"] = 6.0
    w.tick(T0 + 6)
    p = c._probes["https://x.invalid"]
    assert p.fails == 0 and p.ok_wall is not None


def test_r5_12_missing_url_busy_and_idle_agree(tmp_path):
    """R5-12: with ANTHROPIC_BASE_URL missing, a fresh good call reads the same busy or idle."""
    w = W(tmp_path)
    w.c = A.ApiCollector(base_url=lambda: None)
    busy_one(w)
    w.write([ok_line(T0 - 2)])
    busy = w.tick(T0)
    w2 = W(tmp_path / "idle")
    w2.c = A.ApiCollector(base_url=lambda: None)
    w2.write([ok_line(T0 - 2)])
    idle = w2.tick(T0)
    assert busy == idle and busy["state"] == "ok", (busy, idle)


def test_r5_m5_backwards_wall_step_does_not_freeze_the_probe(tmp_path):
    """RB-m5 (clock2): a probe outage, then the wall clock steps back 1 h as the outage ends; good
    calls every 5 s on the new clock. Truth: the API works, so the verdict returns to ok within
    two ticks and the probe keeps running."""
    res = Resolver()
    w = busy_world(tmp_path, res)
    w.write([user_line(T0 - 1)])
    res.down = True
    w.tick(T0, mono=0.0)
    assert w.tick(T0 + 5, mono=5.0)["state"] == "failing"
    res.down = False
    calls0 = res.calls
    states = []
    for i in range(1, 13):
        wall, mono = T0 + 5 - 3600 + 5 * i, 5.0 + 5 * i
        w.write([ok_line(wall - 1)], mtime=wall - 1)
        v = w.tick(wall, mono=mono)
        states.append(v and v.get("state"))
    assert states[1:] == ["ok"] * 11, states
    assert res.calls > calls0


def test_r5_10_env_var_parser():
    import struct
    raw = (struct.pack("<i", 2) + b"/bin/exe\0\0\0\0" + b"exe\0\0"
           + b"FOO=1\0ANTHROPIC_BASE_URL=https://h.example\0\0\0ptr_munge=ANTHROPIC_BASE_URL=x\0")
    from augur.darwin import native as N
    assert N._procargs_env(raw, "ANTHROPIC_BASE_URL") == "https://h.example"
    assert N._procargs_env(raw, "FOO") == "1"
    assert N._procargs_env(raw, "exe") is None and N._procargs_env(raw, "ptr_munge") is None
    assert N._procargs_env(b"\x01\0", "FOO") is None


@pytest.mark.skipif(not __import__("sys").platform.startswith("darwin"), reason="KERN_PROCARGS2")
def test_r5_10_env_var_reads_this_process():
    from augur.darwin import native as N
    assert N.env_var(os.getpid(), "HOME") == os.environ["HOME"]
    assert N.env_var(os.getpid(), "AUGUR_NO_SUCH_VARIABLE_R5") is None


@pytest.mark.skipif(not __import__("sys").platform.startswith("darwin"), reason="KERN_PROCARGS2")
def test_r6_f2_env_var_buffer_sized_by_the_kernel(monkeypatch):
    """R6 F2: env_var allocated a kern.argmax (1 MiB) buffer per call, which the live producer kept
    as RSS. Truth: the kernel's own size answer for this pid (a NULL-buffer sysctl), measured here
    independently; every buffer env_var makes must be near it, and the value must still be read."""
    import ctypes
    from augur.darwin import native as N
    mib = (ctypes.c_int * 3)(1, 49, os.getpid())
    need = ctypes.c_size_t(0)
    assert ctypes.CDLL("/usr/lib/libSystem.dylib").sysctl(mib, 3, None, ctypes.byref(need), None, 0) == 0
    sizes, real = [], ctypes.create_string_buffer
    monkeypatch.setattr(N.ctypes, "create_string_buffer", lambda n, *a: sizes.append(n) or real(n, *a))
    assert N.env_var(os.getpid(), "HOME") == os.environ["HOME"]
    assert sizes and max(sizes) <= 2 * need.value + 8192, (sizes, need.value)


def env_world(tmp_path, settings_url, env, down):
    """A busy session (pid 1, child 2) whose own environment carries `env[pid]`;
    ~/.claude/settings.json names `settings_url` (the NEXT session's). The resolver fails for
    hosts in `down`."""
    w = W(tmp_path)
    calls = []

    def resolver(host):
        calls.append(host)
        if host in down:
            import socket
            raise socket.gaierror(8, "nodename nor servname provided")
        return True
    w.ppid = {2: 1, 4: 3}
    w.c = A.ApiCollector(resolver=resolver, env_var=lambda pid, name: env.get(pid),
                         ppid=lambda pid: w.ppid.get(pid))
    os.makedirs(os.path.join(w.home, ".claude"), exist_ok=True)
    with open(os.path.join(w.home, ".claude", "settings.json"), "w") as fh:
        json.dump({"env": {"ANTHROPIC_BASE_URL": settings_url}}, fh)
    busy_one(w)
    w.shared["session_trees"] = {"1@1": [1, 2]}
    return w, calls


def test_r5_10_probe_uses_the_running_sessions_url(tmp_path):
    """After a switch to an unreachable host, the running session still calls the old one, which
    serves; it is inside a 3 min tool call. Truth: no call failed, so never failing."""
    w, calls = env_world(tmp_path, "https://next.invalid", {2: "https://old.invalid"}, {"next.invalid"})
    w.write([ok_line(T0 - 2)])
    states = [(w.tick(T0 + t) or {}).get("state") for t in range(0, 180, 5)]
    assert "failing" not in states, states
    assert set(calls) == {"old.invalid"}


def test_r5_10_outage_of_the_sessions_host_is_seen(tmp_path):
    w, calls = env_world(tmp_path, "https://next.invalid", {2: "https://old.invalid"}, {"old.invalid"})
    w.write([ok_line(T0 - 30)])
    w.tick(T0)
    assert w.tick(T0 + 5)["state"] == "failing"


def test_r5_10_each_sessions_host_is_probed(tmp_path):
    w, calls = env_world(tmp_path, "https://next.invalid",
                         {2: "https://a.invalid", 4: "https://b.invalid"}, set())
    w.shared["session_ids_by_pid"] = {1: "1@1", 3: "3@1"}
    w.shared["session_trees"] = {"1@1": [1, 2], "3@1": [3, 4]}
    sd = os.path.join(w.home, ".claude", "sessions")
    with open(os.path.join(sd, "3.json"), "w") as fh:
        json.dump({"pid": 3, "status": "busy"}, fh)
    w.write([user_line(T0 - 1)])
    w.tick(T0)
    assert sorted(calls) == ["a.invalid", "b.invalid"]


def test_r5_10_no_known_url_never_overrides_the_transcript(tmp_path):
    """No busy session exposes ANTHROPIC_BASE_URL: no probe at all (settings.json is not used);
    the transcript stands, and with no transcript evidence the reason is env_missing."""
    w, calls = env_world(tmp_path, "https://next.invalid", {}, {"next.invalid"})
    w.write([ok_line(T0 - 2)])
    assert w.tick(T0)["state"] == "ok" and w.tick(T0 + 5)["state"] == "ok"
    assert calls == []
    w2, calls2 = env_world(tmp_path / "b", "https://next.invalid", {}, set())
    w2.write([user_line(T0 - 1)])
    assert w2.tick(T0) == {"unknown": "env_missing"} and calls2 == []


def test_r6_f1_a_grandchilds_url_never_pins_the_probe(tmp_path):
    """R6 F1: a tool command run as ANTHROPIC_BASE_URL=<other> pytest is a grandchild of the
    claude root (root 1 > shell 2 > pytest 5). The session's own calls go to its host and serve.
    Truth: the session never called that host, so it is never probed and never failing."""
    w, calls = env_world(tmp_path, "https://next.invalid", {5: "https://gw.example.invalid"},
                         {"gw.example.invalid"})
    w.ppid[5] = 2
    w.shared["session_trees"] = {"1@1": [1, 2, 5]}
    w.write([ok_line(T0 - 2)])
    states = [(w.tick(T0 + t) or {}).get("state") for t in range(0, 60, 5)]
    assert "failing" not in states, states
    assert calls == []


def test_r6_f1_cached_url_is_dropped_when_its_source_exits(tmp_path):
    """The child that gave the URL exits and a new direct child carries another: the new one is
    probed. Truth: the old source pid is no longer in the session's tree."""
    w, calls = env_world(tmp_path, "https://next.invalid", {2: "https://a.invalid",
                                                            6: "https://b.invalid"}, set())
    w.ppid[6] = 1
    w.write([user_line(T0 - 1)])
    w.tick(T0)
    w.shared["session_trees"] = {"1@1": [1, 6]}
    del calls[:]
    w.tick(T0 + 20)
    w.tick(T0 + 40)
    assert calls and set(calls) == {"b.invalid"}, calls


def test_r6_f1_disagreeing_children_leave_the_probe_unscoped(tmp_path):
    """Two of the session's own children name different hosts: no probe (the transcript stands).
    Truth: neither is known to be the one the session calls."""
    w, calls = env_world(tmp_path, "https://next.invalid", {2: "https://a.invalid",
                                                            7: "https://b.invalid"}, {"a.invalid"})
    w.ppid[7] = 1
    w.shared["session_trees"] = {"1@1": [1, 2, 7]}
    w.write([ok_line(T0 - 2)])
    states = [(w.tick(T0 + t) or {}).get("state") for t in range(0, 60, 5)]
    assert "failing" not in states, states
    assert calls == []
