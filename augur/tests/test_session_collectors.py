"""Replay synthetic libproc / nettop fixtures through augur.collectors.sessions."""
import json
import os
import re
import subprocess

import pytest

from augur.collectors import sessions as S

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sessions")
T0 = 1793503000.0


def proc_start_str(epoch):
    import time
    return time.strftime("%a %b %e %H:%M:%S %Y", time.gmtime(epoch))


class FakeReaders(S.Readers):
    def __init__(self, procs, ru, nettop_texts=()):
        self.procs = procs            # pid -> [ppid, uid, start, comm, path, cmd, cwd]
        self.ru = ru                  # pid -> (cpu_s, runnable_s, fp, disk)
        self.net = list(nettop_texts)
        self.calls = {"pidpath": 0, "cmdline": 0, "nettop": []}
        self.seen = set()

    def uid(self):
        return 501

    def all_pids(self):
        return sorted(self.procs)

    def bsdinfo(self, pid):
        self.seen.add(pid)
        p = self.procs.get(pid)
        return (p[0], p[1], p[2], p[3]) if p else None

    def rusage(self, pid):
        return self.ru.get(pid)

    def pidpath(self, pid):
        self.calls["pidpath"] += 1
        return self.procs[pid][4]

    def cmdline(self, pid):
        self.calls["cmdline"] += 1
        return self.procs[pid][5]

    def cwd(self, pid):
        return self.procs[pid][6]

    def environ_value(self, pid, name):
        return ""

    def tree(self, pid, limit=None):
        out, todo = [], [pid]
        while todo:
            p = todo.pop()
            if p in out or p not in self.procs:
                continue
            out.append(p)
            todo.extend(q for q, v in self.procs.items() if v[0] == p and q != p)
        return out

    def nettop(self, pids, timeout=3.0):
        self.calls["nettop"].append(list(pids))
        nxt = self.net.pop(0)
        if isinstance(nxt, BaseException):
            raise nxt
        return nxt


class Ctx(object):
    def __init__(self, home, storage, lodestar, now, mono, shared):
        self.home, self.storage, self.lodestar = home, storage, lodestar
        self.now, self.mono = now, mono
        self.cadence = {"fast": 2, "agents": 5, "probes": 15, "counts": 60}
        self.state = {}
        self.shared = shared


class World(object):
    """A synthetic HOME with two repos, Claude session files, transcripts and SidePulse."""

    def __init__(self, tmp, lodestar=True, registry_text=None):
        self.tmp = str(tmp)
        self.home = os.path.join(self.tmp, "home")
        self.repo_a = os.path.join(self.tmp, "dev", "RepoA")
        self.repo_b = os.path.join(self.tmp, "dev", "loose_thing")
        self.lodestar = os.path.join(self.tmp, "dev", "Lodestar") if lodestar else None
        for r in (self.repo_a, self.repo_b) + ((self.lodestar,) if lodestar else ()):
            os.makedirs(os.path.join(r, ".git"))
        os.makedirs(os.path.join(self.repo_a, "src"))
        self.storage = os.path.join(self.tmp, "ClaudeWork", "augur")
        os.makedirs(self.storage)
        os.makedirs(os.path.join(self.home, ".claude", "sessions"))
        if lodestar:
            os.makedirs(os.path.join(self.lodestar, "sync"))
            text = registry_text if registry_text is not None else (
                "# reg\n\n| Name | Path | Machines | Id | State |\n|---|---|---|---|---|\n"
                "| RepoA | %s |  | repo-a |  |\n"
                "| Lodestar | %s | laptop | lodestar | active |\n"
                "| Old | %s/dev/Old |  | old | retired |\n" % (self.repo_a, self.lodestar, self.tmp))
            with open(os.path.join(self.lodestar, "sync", "registry.md"), "w") as fh:
                fh.write(text)
            with open(os.path.join(self.lodestar, "machines.md"), "w") as fh:
                fh.write("| Key | Role |\n|---|---|\n| test-key | laptop |\n")
        raw = json.load(open(os.path.join(FIX, "procs.json")))["procs"]
        self.procs = {}
        for k, v in raw.items():
            v = [x.format(home=self.home, repo_a=self.repo_a, repo_b=self.repo_b)
                 if isinstance(x, str) else x for x in v]
            self.procs[int(k)] = v
        self.shared = {}

    def session_file(self, pid, start, **extra):
        d = {"peerToken": "x", "procStart": proc_start_str(start), "pidDomain": "d"}
        d.update(extra)
        with open(os.path.join(self.home, ".claude", "sessions", "%d.json" % pid), "w") as fh:
            json.dump(d, fh)

    def sidepulse(self, slots):
        d = os.path.join(self.tmp, "ClaudeWork", "sidepulse")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "state.json"), "w") as fh:
            json.dump({"slots": {str(i): s for i, s in enumerate(slots)}}, fh)

    def transcripts(self, cwd, sid, agents=(), top_mtime=T0):
        pdir = os.path.join(self.home, ".claude", "projects", S.transcript_slug(cwd))
        os.makedirs(os.path.join(pdir, sid, "subagents"), exist_ok=True)
        top = os.path.join(pdir, sid + ".jsonl")
        open(top, "w").close()
        os.utime(top, (top_mtime, top_mtime))
        for name, mt in agents:
            # running = the last line is not a terminal end_turn; the fixture marks the older
            # one finished (R2: subagents are judged by their last line, not by mtime)
            p = os.path.join(pdir, sid, "subagents", name)
            stop = "tool_use" if mt >= T0 - 30 else "end_turn"
            with open(p, "w") as fh:
                fh.write(json.dumps({"type": "assistant", "message": {"stop_reason": stop}}) + "\n")
            os.utime(p, (mt, mt))
        return pdir

    def ctx(self, now, mono, state=None):
        c = Ctx(self.home, self.storage, self.lodestar, now, mono, self.shared)
        if state is not None:
            c.state = state
        return c


@pytest.fixture(autouse=True)
def machine_key(monkeypatch, tmp_path):
    monkeypatch.setenv("LODESTAR_MACHINE", "test-key")
    # RB-n13: SidePulse's dir comes from its own variable, never from AUGUR_HOME's parent
    monkeypatch.setenv("SIDEPULSE_STATE_DIR", os.path.join(str(tmp_path), "ClaudeWork", "sidepulse"))


def standard(tmp_path, **kw):
    w = World(tmp_path, **kw)
    w.session_file(101, 1793500000)
    w.session_file(201, 1793501000)
    w.transcripts(w.repo_a + "/src", "sid-a",
                  agents=[("agent-a1.jsonl", T0 - 5), ("agent-a2.jsonl", T0 - 100)])
    w.transcripts(w.repo_b, "sid-b", top_mtime=1793501500)
    w.sidepulse([{"pid": "101", "sid": "sid-a", "state": "working", "since": T0 - 60, "t": T0 - 1},
                 {"pid": "201", "sid": "sid-b", "state": "done", "since": T0 - 30, "t": T0 - 30}])
    return w


def ru_tick(cpu_scale):
    return {101: (10.0 * cpu_scale, 10.0 * cpu_scale, 400_000_000, 0),
            102: (1.0, 1.0, 1_000_000, 0),
            103: (2.0 * cpu_scale, 4.0 * cpu_scale, 50_000_000, 0),
            104: (0.1, 0.1, 500_000, 0),
            105: (0.2, 0.2, 2_000_000, 0),
            201: (5.0, 5.0, 300_000_000, 0),
            301: (1.0, 1.0, 100_000_000, 0)}


def run_sessions(w, readers, coll, state, now, mono):
    ctx = w.ctx(now, mono, state)
    return coll.collect(ctx)["sessions"], ctx


# --------------------------------------------------------------------------- sessions

def test_two_sessions_and_load(tmp_path):
    w = standard(tmp_path)
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    st = {}
    out, ctx = run_sessions(w, r, c, st, T0, 100.0)
    ids = [s["id"] for s in out]
    assert ids == ["101@1793500000", "201@1793501000"]          # 301 has no session file
    assert all(s["load"] == {"unknown": "warming_up"} for s in out)
    assert ctx.shared["agent_wait_s_per_s"] is None
    assert ctx.shared["session_trees"]["101@1793500000"] == [101, 102, 103, 104, 105]
    assert ctx.shared["session_ids_by_pid"] == {101: "101@1793500000", 201: "201@1793501000"}
    a, b = out
    assert (a["project"], a["project_key"], a["managed"]) == ("RepoA", "repo-a", True)
    assert (b["project"], b["project_key"], b["managed"]) == ("loose_thing", "loose_thing", False)
    r.ru = ru_tick(1.5)          # root +5 cpu +5 run; 103 +1 cpu +2 run over 5 s
    out, ctx = run_sessions(w, r, c, st, T0 + 5, 105.0)
    la = out[0]["load"]
    assert la["cpu_cores"] == pytest.approx(1.2)
    assert la["wait_s_per_s"] == pytest.approx(0.2)
    assert la["procs"] == 5 and la["mem_gb"] == pytest.approx(0.454)
    assert la["starved"] is False
    assert out[1]["load"]["cpu_cores"] == 0.0
    assert ctx.shared["agent_wait_s_per_s"] == pytest.approx(0.2)
    # pidpath read once per pid@start, cmdline only for zsh/bash/sh
    assert r.calls["pidpath"] == 2          # only the two candidate roots named by session files
    assert 301 not in r.seen and 900 not in r.seen   # pids outside the trees are never read
    assert r.calls["cmdline"] == 4          # + once per root with no entrypoint in its file (1.2 headless)


def test_reaped_children_cpu_counted_once(tmp_path):
    w = standard(tmp_path)
    ru = ru_tick(1.0)
    ru[101] = (10.0, 10.0, 400_000_000, 0, 0.0)
    r = FakeReaders(w.procs, ru)
    c = S.SessionsCollector(r)
    st = {}
    tree = lambda ctx: ctx.shared["session_trees"]["101@1793500000"]
    run_sessions(w, r, c, st, T0, 0.0)
    # a short-lived child never seen by any sweep: its 2 s land in the root's child time
    ru = dict(ru)
    ru[101] = (10.0, 10.0, 400_000_000, 0, 2.0)
    r.ru = ru
    out, _ = run_sessions(w, r, c, st, T0 + 5, 5.0)
    assert out[0]["load"]["cpu_cores"] == pytest.approx(0.4)
    # a child born this interval (seen once, 1 s own CPU so far) counts in full
    w.procs[106] = [101, 501, int(T0 + 7), "git", "/usr/bin/git", "git status", w.repo_a]
    ru = dict(ru)
    ru[106] = (1.0, 1.0, 1_000_000, 0, 0.0)
    r.ru = ru
    out, ctx = run_sessions(w, r, c, st, T0 + 10, 10.0)
    assert 106 in tree(ctx)
    assert out[0]["load"]["cpu_cores"] == pytest.approx(0.2)
    # it runs 0.5 s more, exits and is reaped: the root's child time rises by its total 1.5 s;
    # only the new 0.5 s may count (1.0 was already counted when it was seen)
    del w.procs[106]
    ru = dict(ru)
    del ru[106]
    ru[101] = (10.0, 10.0, 400_000_000, 0, 3.5)
    r.ru = ru
    out, ctx = run_sessions(w, r, c, st, T0 + 15, 15.0)
    assert 106 not in tree(ctx)
    assert out[0]["load"]["cpu_cores"] == pytest.approx(0.1)


def test_starved_needs_two_ticks(tmp_path):
    w = standard(tmp_path)
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    st = {}
    run_sessions(w, r, c, st, T0, 0.0)
    ru = ru_tick(1.0)
    for i, mono in enumerate((5.0, 10.0), 1):
        ru = dict(ru)
        ru[101] = (10.0, 10.0 + 5.0 * i, 400_000_000, 0)   # 1.0 s/s wait, no CPU
        r.ru = ru
        out, _ = run_sessions(w, r, c, st, T0 + mono, mono)
        assert out[0]["load"]["wait_s_per_s"] == pytest.approx(1.0)
        assert out[0]["load"]["starved"] is (i == 2)


def test_shell_and_subagent(tmp_path):
    w = standard(tmp_path)
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    t = out[0]["tasks"]
    assert (t["shells"], t["subagents"], t["total"], t["method"]) == (1, 1, 2, "tree+transcripts")
    assert out[1]["tasks"]["total"] == 0          # interactive zsh (105) is not a Bash-tool shell


def test_sessionid_fallback_newest_transcript(tmp_path):
    w = standard(tmp_path)
    os.remove(os.path.join(w.tmp, "ClaudeWork", "sidepulse", "state.json"))
    w.transcripts(w.repo_a + "/src", "sid-old", agents=[("agent-z.jsonl", T0 - 1)],
                  top_mtime=1793499000)                           # before the session started
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert out[0]["tasks"]["subagents"] == 1                      # sid-a, not sid-old


def test_pid_reuse_new_id_no_cpu(tmp_path):
    w = standard(tmp_path)
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    st = {}
    run_sessions(w, r, c, st, T0, 0.0)
    r.ru = ru_tick(1.0)
    run_sessions(w, r, c, st, T0 + 5, 5.0)
    # pid 201 dies; a new Claude takes pid 201 with a later start and a huge cumulative CPU
    w.procs[201] = [1, 501, 1793503004, "2.1.292", "/opt/x/claude/versions/2.1.300", "claude", w.repo_b]
    w.session_file(201, 1793503004)
    ru = ru_tick(1.0)
    ru[201] = (999.0, 999.0, 10_000_000, 0)
    r.ru = ru
    out, _ = run_sessions(w, r, c, st, T0 + 10, 10.0)
    b = out[1]
    assert b["id"] == "201@1793503004"
    assert b["load"] == {"unknown": "warming_up"}
    r.ru = dict(ru)
    out, _ = run_sessions(w, r, c, st, T0 + 15, 15.0)
    assert out[1]["load"]["cpu_cores"] == 0.0


def test_sessions_dir_unlistable_falls_back_to_full_sweep(tmp_path):
    w = standard(tmp_path)
    import shutil
    shutil.rmtree(os.path.join(w.home, ".claude", "sessions"))
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert [s["pid"] for s in out] == [101, 201, 301]       # every root counts
    assert 900 in r.seen


def test_nested_root_stays_in_enclosing_tree(tmp_path):
    w = standard(tmp_path)
    w.procs[301][0] = 101                                    # a `claude -p` under session 101
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, ctx = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert [s["pid"] for s in out] == [101, 201]
    assert 301 in ctx.shared["session_trees"]["101@1793500000"]


def test_stale_session_file_rejected(tmp_path):
    w = standard(tmp_path)
    w.session_file(201, 1793400000)              # file belongs to a previous owner of pid 201
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert [s["pid"] for s in out] == [101]


def test_lodestar_absent_managed_false(tmp_path):
    w = standard(tmp_path, lodestar=False)
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert [s["managed"] for s in out] == [False, False]
    assert out[0]["project_key"] == "repoa"


def test_registry_unreadable_managed_absent(tmp_path):
    w = standard(tmp_path, registry_text="no table here, just prose\n")
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert all("managed" not in s for s in out)
    assert out[0]["project_key"] == "repoa"


def test_lodestar_session_key_and_machines_column(tmp_path, monkeypatch):
    w = standard(tmp_path)
    w.procs[201][6] = w.lodestar
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert (out[1]["project"], out[1]["project_key"], out[1]["managed"]) == ("Lodestar", "lodestar", True)
    monkeypatch.setenv("LODESTAR_MACHINE", "other-key")      # not a laptop: row not carried
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert (out[1]["project_key"], out[1]["managed"]) == ("lodestar", False)


# --------------------------------------------------------------------------- attention

def test_attention_slots_and_fallback(tmp_path):
    w = standard(tmp_path)
    w.shared["session_ids_by_pid"] = {101: "101@1793500000", 201: "201@1793501000"}
    a = S.AttentionCollector().collect(w.ctx(T0, 0.0))["sessions.attention"]
    assert a["101@1793500000"] == {"state": "working", "since": T0 - 60}
    assert a["201@1793501000"]["state"] == "stopped"
    a = S.AttentionCollector().collect(w.ctx(T0 + 3600, 0.0))["sessions.attention"]
    assert a["201@1793501000"]["state"] == "idle"
    # no slot: the session file status is the fallback; no status at all: absent
    w.sidepulse([])
    w.session_file(101, 1793500000, status="waiting", statusUpdatedAt=int(T0 * 1000))
    a = S.AttentionCollector().collect(w.ctx(T0, 0.0))["sessions.attention"]
    assert a == {"101@1793500000": {"state": "needs_you", "since": T0}}
    # state.json corrupt and no fallback: read_failed for that session
    with open(os.path.join(w.tmp, "ClaudeWork", "sidepulse", "state.json"), "w") as fh:
        fh.write("{nope")
    a = S.AttentionCollector().collect(w.ctx(T0, 0.0))["sessions.attention"]
    assert a["201@1793501000"] == {"unknown": "read_failed"}
    assert a["101@1793500000"]["state"] == "needs_you"


# --------------------------------------------------------------------------- session_net

def nettop_text(name):
    return open(os.path.join(FIX, name)).read()


def test_net_replay_loopback_and_close(tmp_path):
    w = standard(tmp_path)
    w.shared["session_trees"] = {"101@1793500000": [101, 102, 103, 104, 105], "201@1793501000": [201]}
    r = FakeReaders({}, {}, [(0, nettop_text("nettop_t0.txt")), (0, nettop_text("nettop_t1.txt"))])
    c = S.SessionNetCollector(r)
    st = {}
    assert c.collect(w.ctx(T0, 100.0, st)) == {"sessions.net": {"unknown": "warming_up"}}
    net = c.collect(w.ctx(T0 + 5, 105.0, st))["sessions.net"]
    a, b = net["101@1793500000"], net["201@1793501000"]
    # 50001 +625000 in / +1250000 out; loopback 50003 excluded; 50004 new = 0; 50002 closed
    assert a == {"rx_mbps": 1.0, "tx_mbps": 2.0, "flows": 3, "retx_pct": 0.08, "provisional": True}
    assert b == {"rx_mbps": 0.0, "tx_mbps": 0.0, "flows": 1, "provisional": True}   # no tcp out: no retx
    au = w.shared["audit"]
    assert (au["session_rx_bytes"], au["session_tx_bytes"], au["session_net_ticks"]) == (625000, 1250000, 1)
    assert r.calls["nettop"][0] == [101, 102, 103, 104, 105, 201]


def test_net_failures_and_off(tmp_path):
    w = standard(tmp_path)
    w.shared["session_trees"] = {"101@1": [101]}
    r = FakeReaders({}, {}, [subprocess.TimeoutExpired("nettop", 3), (64, "usage"), (0, "garbage")])
    c = S.SessionNetCollector(r)
    assert c.collect(w.ctx(T0, 0.0)) == {"sessions.net": {"unknown": "timeout"}}
    assert c.collect(w.ctx(T0, 0.0)) == {"sessions.net": {"unknown": "read_failed"}}
    assert c.collect(w.ctx(T0, 0.0)) == {"sessions.net": {"unknown": "read_failed"}}
    w.shared["session_trees"] = {}
    assert c.collect(w.ctx(T0, 0.0)) == {}


def test_parse_nettop_excludes_local_pairs():
    text = (",bytes_in,bytes_out,re-tx,\n2.1.292.7,0,0,0,\n"
            "tcp4 192.0.2.10:1<->192.0.2.10:2,5,5,0,\n"
            "tcp6 fe80::1%utun5.1<->fe80::2%utun5.2,5,5,0,\n"
            "tcp4 192.0.2.10:3<->198.51.100.1:443,5,5,0,\n")
    f = S.parse_nettop(text, {7})
    assert len(f) == 2 and all(v[0] == 7 for v in f.values())


# --------------------------------------------------------------------------- privacy

IPV4 = re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b")


def test_privacy_outputs_hold_no_paths_commands_or_addresses(tmp_path):
    w = standard(tmp_path)
    r = FakeReaders(w.procs, ru_tick(1.0),
                    [(0, nettop_text("nettop_t0.txt")), (0, nettop_text("nettop_t1.txt"))])
    cs = S.all_collectors(r)
    assert [(c.name, c.tier) for c in cs] == [("sessions", "agents"), ("attention", "fast"),
                                               ("session_net", "agents")]
    states = [{}, {}, {}]
    dumps = []
    for i, mono in enumerate((0.0, 5.0)):
        r.ru = ru_tick(1.0 + i)
        for c, st in zip(cs, states):
            dumps.append(json.dumps(c.collect(w.ctx(T0 + mono, mono, st))))
    blob = "\n".join(dumps)
    for bad in ("/Users/", w.tmp, "shell-snapshots", "sleep 99", "mcp_server", "sid-a", "@example"):
        assert bad not in blob, bad
    assert not IPV4.search(blob)
    assert "::1" not in blob and "<->" not in blob
    # the only '@' allowed is the pid@start id
    assert not re.search(r"[A-Za-z]@", blob)


def test_slug_matches_claude_projects_dirs():
    assert S.transcript_slug("/Users/x/dev/Orchard_Mandrake") == "-Users-x-dev-Orchard-Mandrake"
    assert S.transcript_slug("/a/b.c") == "-a-b-c"


# --------------------------------------------------------------------------- subagents running (R2)

def _agent(sub, name, lines, age, now, depth=1):
    p = os.path.join(sub, name + ".jsonl")
    with open(p, "w") as fh:
        for d in lines:
            fh.write(json.dumps(d) + "\n")
    os.utime(p, (now - age, now - age))
    with open(os.path.join(sub, name + ".meta.json"), "w") as fh:
        json.dump({"agentType": "general-purpose", "spawnDepth": depth}, fh)


A_TOOL = {"type": "assistant", "agentId": "x", "message": {"stop_reason": "tool_use",
          "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "sleep 900"}}]}}
A_END = {"type": "assistant", "agentId": "x", "message": {"stop_reason": "end_turn",
         "content": [{"type": "text", "text": "done"}]}}
A_ERR = {"type": "assistant", "agentId": "x", "isApiErrorMessage": True, "error": "server_error",
         "message": {"stop_reason": "stop_sequence", "content": [{"type": "text", "text": "API Error"}]}}
ATTACH = {"type": "attachment", "agentId": "x", "attachment": {"type": "x"}}
USER = {"type": "user", "agentId": "x", "message": {"content": [{"type": "tool_result"}]}}


def test_subagents_running_by_last_line_not_mtime(tmp_path):
    """Truth: the harness's view, encoded in each file's last line (owner bug 2026-11-01: a
    subagent blocked on a long tool call wrote nothing for minutes and dropped out of the count)."""
    w = standard(tmp_path)
    sub = os.path.join(w.home, ".claude", "projects", S.transcript_slug(w.repo_a + "/src"), "sid-a", "subagents")
    for f in os.listdir(sub):
        os.remove(os.path.join(sub, f))
    _agent(sub, "agent-run1", [USER, A_TOOL], 600, T0)                 # blocked on a 10-min tool
    _agent(sub, "agent-run2", [A_TOOL, ATTACH], 120, T0)               # tool result pending
    _agent(sub, "agent-run3", [A_TOOL, USER], 2, T0, depth=2)          # nested, running
    _agent(sub, "agent-resumed", [A_TOOL, A_END, USER, A_TOOL], 50, T0)  # end_turn, then resumed
    _agent(sub, "agent-done", [A_TOOL, A_END], 5, T0)                  # just finished: not running
    _agent(sub, "agent-died", [ATTACH, A_ERR], 300, T0)                # ended on an API error
    _agent(sub, "agent-old", [A_TOOL], 25 * 3600, T0)                  # older than the session's day
    with open(os.path.join(sub, "agent-partial.jsonl"), "w") as fh:     # end_turn, then a half line
        fh.write(json.dumps(A_END) + "\n" + json.dumps(A_TOOL)[:30])
    os.utime(os.path.join(sub, "agent-partial.jsonl"), (T0 - 1, T0 - 1))
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert out[0]["tasks"]["subagents"] == 4


# --------------------------------------------------------------------------- background work (R2)

def test_background_work_counts(tmp_path):
    """Owner ruling 2026-11-01: dots = background work. Truth set by the fixture: which shells
    were launched with run_in_background (their task id is announced in a transcript), which
    process is an orphaned worker, which children are an MCP server and a foreground shell."""
    w = standard(tmp_path)
    pdir = os.path.join(w.home, ".claude", "projects", S.transcript_slug(w.repo_a + "/src"))
    sub = os.path.join(pdir, "sid-a", "subagents")
    for f in os.listdir(sub):
        os.remove(os.path.join(sub, f))
    _agent(sub, "agent-r", [USER, A_TOOL], 5, T0)                       # one live subagent
    with open(os.path.join(sub, "agent-r.jsonl"), "a") as fh:            # it launched bg shell b2
        fh.write(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result",
                 "content": "Command running in background with ID: b2bgsub. Output is being written to: x"}]}}) + "\n")
    os.utime(os.path.join(sub, "agent-r.jsonl"), (T0 - 5, T0 - 5))
    with open(os.path.join(pdir, "sid-a.jsonl"), "w") as fh:            # main launched bg shell b1
        fh.write(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result",
                 "content": "Command running in background with ID: b1bgmain. Output is being written to: x"}]}}) + "\n")
    sh = lambda pid, start: [101, 501, start, "zsh", "/bin/zsh",  # noqa: E731
                             "/bin/zsh -c source /h/.claude/shell-snapshots/s.sh && eval 'x'", w.repo_a]
    w.procs[102] = sh(102, int(T0 - 2))            # foreground tool shell, fresh (fixture 102 reused)
    w.procs[110] = sh(110, int(T0 - 9 * 3600))     # bg (cocaffeinate --lid), announced by main
    w.procs[111] = sh(111, int(T0 - 30))           # bg, announced by a subagent
    w.procs[112] = sh(112, int(T0 - 300))          # long FOREGROUND command: not background
    w.procs[113] = sh(113, int(T0 - 120))          # stdout unreadable: age fallback, counts
    w.procs[114] = sh(114, int(T0 - 10))           # stdout unreadable, young: does not count
    w.procs[120] = [101, 501, int(T0 - 3600), "python3.12", "/x/.venv/bin/python", "python mcp.py", w.repo_a]
    w.procs[121] = [101, 501, int(T0 - 60), "caffeinate", "/usr/bin/caffeinate", "caffeinate -i", w.repo_a]
    out_ids = {102: "bfgnow", 110: "b1bgmain", 111: "b2bgsub", 112: "bfglong", 115: "bunannounced"}
    w.procs[115] = sh(115, int(T0 - 900))          # never announced, but older than any fg call
    r = FakeReaders(w.procs, {p: (1.0, 1.0, 1000, 0, 0.0) for p in w.procs})
    r.stdout_path = lambda pid: ("/private/tmp/claude-503/x/sid/tasks/%s.output" % out_ids[pid]
                                 if pid in out_ids else "")
    c = S.SessionsCollector(r)
    st = {}
    run_sessions(w, r, c, st, T0, 0.0)
    # a worker double-forked out of foreground shell 112 is reparented to launchd: an orphan
    w.procs[130] = [112, 501, int(T0 - 200), "server", "/x/server", "server", w.repo_a]
    r.ru[130] = (1.0, 1.0, 1000, 0, 0.0)
    run_sessions(w, r, c, st, T0 + 5, 5.0)
    w.procs[130][0] = 1
    out, _ = run_sessions(w, r, c, st, T0 + 10, 10.0)
    t = out[0]["tasks"]
    assert (t["bg_shells"], t["subagents"], t["other"]) == (4, 1, 1), t
    assert t["total"] == 6
    assert "shells" in t                               # kept for readers (all tool shells)
    assert "b1bgmain" not in json.dumps(out)           # task ids stay in memory


def test_announce_scan_is_incremental_and_complete_lines_only(tmp_path):
    p = str(tmp_path / "t.jsonl")
    c = S.SessionsCollector(FakeReaders({}, {}))
    with open(p, "w") as fh:
        fh.write('{"x":"Command running in background with ID: b1aaa. Output"}\n{"x":"Command running in background with ID: b2b')
    assert c._announced(p) == {"b1aaa"}
    with open(p, "a") as fh:
        fh.write('bb. more"}\n')
    assert c._announced(p) == {"b1aaa", "b2bbb"}
    with open(p, "w") as fh:                       # replaced: rescanned from the start
        fh.write('{"x":"moved to the background (ID: b3ccc)"}\n')
    assert c._announced(p) == {"b3ccc"}


def iso_utc(t):
    import datetime as _d
    return _d.datetime.fromtimestamp(t, _d.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def test_task_notification_ends_a_mid_stream_agent(tmp_path):
    """Bake-off instant 2 (CLAUDE_HUD_BAKEOFF.md): the agent's last line is mid-stream (no
    stop_reason) and young, and the parent transcript already holds its completion notice for
    that agent id. Truth (the harness): not running. A later line after the notice = resumed."""
    w = standard(tmp_path)
    pdir = os.path.join(w.home, ".claude", "projects", S.transcript_slug(w.repo_a + "/src"))
    sub = os.path.join(pdir, "sid-a", "subagents")
    for f in os.listdir(sub):
        os.remove(os.path.join(sub, f))
    stream = {"type": "assistant", "timestamp": iso_utc(T0 - 10),
              "message": {"stop_reason": None, "content": [{"type": "text"}]}}
    # R5-6: lines carry timestamps (as real ones do); a file with none reads unmeasured
    _agent(sub, "agent-a2d5cebcc98bd7be4", [A_TOOL, USER, stream], 1, T0)
    _agent(sub, "agent-aother", [A_TOOL], 1, T0)                 # a different agent: still running
    with open(os.path.join(pdir, "sid-a.jsonl"), "w") as fh:
        note = ("<task-notification>\n<task-id>a2d5cebcc98bd7be4</task-id>\n<tool-use-id>toolu_x"
                "</tool-use-id>\n<status>completed</status>\n</task-notification>")
        fh.write(json.dumps({"type": "queue-operation", "operation": "enqueue", "content": note,
                             "timestamp": iso_utc(T0 - 1)}) + "\n")
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    out, _ = run_sessions(w, r, c, {}, T0, 0.0)
    assert out[0]["tasks"]["subagents"] == 1
    p = os.path.join(sub, "agent-a2d5cebcc98bd7be4.jsonl")       # resumed after the notice
    with open(p, "a") as fh:
        fh.write(json.dumps(dict(USER, timestamp=iso_utc(T0 + 4))) + "\n")
    os.utime(p, (T0 + 4, T0 + 4))
    out, _ = run_sessions(w, r, c, {}, T0 + 5, 5.0)
    assert out[0]["tasks"]["subagents"] == 2
    # a fresh collector (Augur restarted) after the resume must also see it running
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0 + 6, 6.0)
    assert out[0]["tasks"]["subagents"] == 2


def test_notice_text_inside_a_tool_call_does_not_end_an_agent(tmp_path):
    """09:45 false positive: a Bash tool_use input (and its tool_result) quoting
    `<task-id>a...</task-id>` ended a live agent. Only the harness's own notification entries
    count: a queue-operation enqueue, a user line with origin.kind task-notification, or an
    attachment with commandMode task-notification. Shapes copied from this session's transcript."""
    w = standard(tmp_path)
    pdir = os.path.join(w.home, ".claude", "projects", S.transcript_slug(w.repo_a + "/src"))
    sub = os.path.join(pdir, "sid-a", "subagents")
    for f in os.listdir(sub):
        os.remove(os.path.join(sub, f))
    for aid in ("aaa1", "aaa2", "aaa3", "aaa4"):
        _agent(sub, "agent-" + aid, [dict(A_TOOL, timestamp=iso_utc(T0 - 100))], 1, T0)
    block = lambda aid: ("<task-notification>\n<task-id>%s</task-id>\n<tool-use-id>toolu_x</tool-use-id>\n"  # noqa: E731
                         "<status>completed</status>\n</task-notification>" % aid)
    lines = [
        # quoted in a tool call and its result: must NOT end aaa1
        {"type": "assistant", "message": {"role": "assistant", "stop_reason": "tool_use", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "grep '%s' f" % block("aaa1")}}]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "content": block("aaa1")}]}},
        {"type": "user", "message": {"role": "user", "content": "please look at " + block("aaa1")}},
        # the harness's real entries: end aaa2, aaa3, aaa4
        {"type": "queue-operation", "operation": "enqueue", "content": block("aaa2"),
         "timestamp": iso_utc(T0)},
        {"type": "user", "origin": {"kind": "task-notification", "producer": "session-task"},
         "message": {"role": "user", "content": block("aaa3")}, "timestamp": iso_utc(T0)},
        {"type": "attachment", "attachment": {"type": "queued_command", "commandMode": "task-notification",
                                              "prompt": block("aaa4"), "timestamp": iso_utc(T0)}},
    ]
    with open(os.path.join(pdir, "sid-a.jsonl"), "w") as fh:
        for d in lines:
            fh.write(json.dumps(d) + "\n")
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert out[0]["tasks"]["subagents"] == 1


def test_r3_2_scan_path_has_no_mmap_and_survives_truncation(tmp_path):
    """R3-2 / R4-12: never crash a real process to test this. (1) Structurally, the transcript
    scan path maps nothing. (2) A file truncated during the scan (simulated by a reader that
    returns short) ends the scan cleanly, and the next scan re-reads from the start."""
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(S))
    names = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    names |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    attrs = {n.value.id for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    assert "mmap" not in names and "mmap" not in attrs
    p = str(tmp_path / "t.jsonl")
    line = b'{"type":"queue-operation","operation":"enqueue","content":"x"}\n'
    with open(p, "wb") as fh:
        fh.write(line * 50000)
    seen = []

    class Short(object):
        """A file whose writer truncated it after the first read: later reads return b''."""
        def __init__(self, f):
            self.f, self.n = f, 0

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.f.close()

        def seek(self, *a):
            return self.f.seek(*a)

        def readinto(self, mv):
            self.n += 1
            return self.f.readinto(mv) if self.n == 1 else 0
    orig = S.open_regular                     # S1: the scanner opens through open_regular
    S.open_regular = lambda path: Short(orig(path)) if path == p else orig(path)
    try:
        off = S.SessionsCollector._scan_lines(p, 0, os.path.getsize(p), lambda b: seen.append(len(b)))
    finally:
        S.open_regular = orig
    assert 0 < off < os.path.getsize(p) and off % len(line) == 0   # stopped on a line boundary


def test_r4_2_malformed_notification_line_is_skipped_not_poisoning(tmp_path):
    w = standard(tmp_path)
    pdir = os.path.join(w.home, ".claude", "projects", S.transcript_slug(w.repo_a + "/src"))
    sub = os.path.join(pdir, "sid-a", "subagents")
    for f in os.listdir(sub):
        os.remove(os.path.join(sub, f))
    _agent(sub, "agent-ab1", [dict(A_TOOL, timestamp=iso_utc(T0 - 100))], 1, T0)
    _agent(sub, "agent-ab2", [dict(A_TOOL, timestamp=iso_utc(T0 - 100))], 1, T0)
    note = lambda aid: "<task-notification>\n<task-id>%s</task-id>\n<status>completed</status>" % aid  # noqa: E731
    with open(os.path.join(pdir, "sid-a.jsonl"), "w") as fh:
        fh.write(json.dumps({"type": "queue-operation", "operation": "enqueue", "content": note("ab1"),
                             "attachment": "not-an-object", "timestamp": iso_utc(T0)}) + "\n")
        fh.write(json.dumps({"type": "queue-operation", "operation": "enqueue", "content": note("ab2"),
                             "timestamp": iso_utc(T0)}) + "\n")
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    st = {}
    for t in (0, 5):
        out, ctx = run_sessions(w, r, c, st, T0 + t, float(t))
        assert "tasks" in out[0] and "load" in out[0]
        assert "101@1793500000" in ctx.shared["transcript_dirs"]
    assert out[0]["tasks"]["subagents"] == 0             # both notices read despite the odd shape
    # R5-5 (replaces the R4-2 rule): a timestampless notice after a timestamped one does not
    # poison the id; the newest timestamped notice (T0) is kept and ab1's last line (T0-100) is
    # older, so both stay ended
    with open(os.path.join(pdir, "sid-a.jsonl"), "a") as fh:
        fh.write(json.dumps({"type": "queue-operation", "operation": "enqueue",
                             "content": note("ab1")}) + "\n")
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0 + 10, 10.0)
    assert out[0]["tasks"]["subagents"] == 0


def test_r4_3_overlong_line_keeps_framing_and_size_bound(tmp_path):
    p = str(tmp_path / "t.jsonl")
    big = b"x" * (2 * S.SCAN_CHUNK + 17)
    note = (b'{"type":"queue-operation","operation":"enqueue","content":"<task-notification>\\n'
            b'<task-id>a1</task-id>"}')
    with open(p, "wb") as fh:
        fh.write(big)                                   # no newline yet: one huge partial line
    c = S.SessionsCollector(FakeReaders({}, {}))
    assert c._noticed(p) == {}
    with open(p, "ab") as fh:
        fh.write(note + b"\n")                          # the SAME physical line continues
    assert c._noticed(p) == {}                          # the suffix is not a record of its own
    with open(p, "ab") as fh:
        fh.write(note.replace(b'"}', b'","timestamp":"2026-11-01T10:00:00Z"}') + b"\n")
    assert set(c._noticed(p)) == {"a1"}                 # a real next line is still read
    size = os.path.getsize(p)
    with open(p, "ab") as fh:
        fh.write(b"y" * (3 * S.SCAN_CHUNK))
    got = S.SessionsCollector._scan_lines(p, 0, size, lambda b: None)
    assert got <= size                                  # never reads past `size`


def test_r4_9_resume_is_judged_by_content_not_mtime(tmp_path):
    w = standard(tmp_path)
    pdir = os.path.join(w.home, ".claude", "projects", S.transcript_slug(w.repo_a + "/src"))
    sub = os.path.join(pdir, "sid-a", "subagents")
    for f in os.listdir(sub):
        os.remove(os.path.join(sub, f))
    tool = lambda t: dict(A_TOOL, timestamp=iso_utc(t))  # noqa: E731
    _agent(sub, "agent-ac1", [tool(T0 - 100)], 1, T0)               # touched after its notice
    _agent(sub, "agent-ac2", [tool(T0 - 100), dict(USER, timestamp=iso_utc(T0 - 5))], 1, T0)  # resumed
    note = lambda aid: "<task-notification>\n<task-id>%s</task-id>\n<status>completed</status>" % aid  # noqa: E731
    with open(os.path.join(pdir, "sid-a.jsonl"), "w") as fh:
        for aid in ("ac1", "ac2"):
            fh.write(json.dumps({"type": "queue-operation", "operation": "enqueue", "content": note(aid),
                                 "timestamp": iso_utc(T0 - 50)}) + "\n")
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    assert out[0]["tasks"]["subagents"] == 1                         # ac2 only


# --------------------------------------------------------------------------- review R5

def _note_session(tmp_path, notes, agent_lines, age=1):
    """Session A with one agent a01 and completion notices for it at `notes` (None = a notice
    with no timestamp). Returns (world, main transcript, agent file)."""
    w = standard(tmp_path)
    pdir = os.path.join(w.home, ".claude", "projects", S.transcript_slug(w.repo_a + "/src"))
    sub = os.path.join(pdir, "sid-a", "subagents")
    for f in os.listdir(sub):
        os.remove(os.path.join(sub, f))
    _agent(sub, "agent-a01", agent_lines, age, T0)
    main = os.path.join(pdir, "sid-a.jsonl")
    with open(main, "w") as fh:
        for ts in notes:
            d = {"type": "queue-operation", "operation": "enqueue",
                 "content": "<task-notification>\n<task-id>a01</task-id>\n<status>completed</status>"}
            if ts is not None:
                d["timestamp"] = iso_utc(ts)
            fh.write(json.dumps(d) + "\n")
    return w, main, os.path.join(sub, "agent-a01.jsonl")


def _tool(t):
    return dict(A_TOOL, timestamp=iso_utc(t))


def _tasks_once(w, coll=None, state=None, now=T0, mono=0.0):
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, coll or S.SessionsCollector(r), {} if state is None else state, now, mono)
    return out[0]["tasks"]


@pytest.mark.parametrize("notes", [[None, T0 - 50], [T0 - 50, None]])
def test_r5_5_timestampless_notice_does_not_absorb(tmp_path, notes):
    """R5-5: a notice with no timestamp must not hide a timestamped one for the same id. Truth:
    the agent wrote a line at T0-5, after its newest timestamped notice (T0-50): 1 running."""
    w, _, _ = _note_session(tmp_path, notes, [_tool(T0 - 100), dict(USER, timestamp=iso_utc(T0 - 5))])
    assert _tasks_once(w).get("subagents") == 1


def test_r5_5_only_timestampless_notices_stay_unknown(tmp_path):
    w, _, _ = _note_session(tmp_path, [None], [_tool(T0 - 100), dict(USER, timestamp=iso_utc(T0 - 5))])
    assert _tasks_once(w) == {"unknown": "read_failed"}


def test_r5_6_resume_in_one_long_line_is_found(tmp_path):
    """R5-6 (G2b): resumed with one 20 KB tool_use line after the notice; the 8 KB tail holds a
    fragment only. Truth: 1 running (never 0)."""
    big = _tool(T0 - 5)
    big["message"] = dict(big["message"], content=[{"type": "tool_use", "name": "Bash",
                                                    "input": {"command": "x" * 20000}}])
    w, _, _ = _note_session(tmp_path, [T0 - 50], [_tool(T0 - 100), big])
    assert _tasks_once(w).get("subagents") == 1


def test_r5_6_no_timestamp_anywhere_reads_unmeasured_not_ended(tmp_path):
    w, _, _ = _note_session(tmp_path, [T0 - 50], [A_TOOL, USER])
    assert _tasks_once(w) == {"unknown": "read_failed"}


def test_r5_6_failed_tail_read_is_never_cached(tmp_path, monkeypatch):
    """R5-6 (G2c): one EIO on the tail read. That tick is unmeasured (not 0); the next reads the
    truth (1) although the file did not change."""
    w, _, _ = _note_session(tmp_path, [T0 - 50], [_tool(T0 - 100), dict(USER, timestamp=iso_utc(T0 - 5))])
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    real = S._last_line_epoch

    def eio(*a, **k):
        raise OSError(5, "EIO")
    monkeypatch.setattr(S, "_last_line_epoch", eio)
    a = _tasks_once(w, c, {}, T0, 0.0)
    monkeypatch.setattr(S, "_last_line_epoch", real)
    b = _tasks_once(w, c, {}, T0 + 5, 5.0)
    assert a == {"unknown": "read_failed"}
    assert b.get("subagents") == 1


def test_r5_6_same_size_rewrite_is_reread(tmp_path):
    """The resume cache is keyed by (size, mtime, inode), not size: a same-size rewrite that adds
    a resume (T0-60 -> T0-5, same length) must be seen. Truth: 0, then 1."""
    lines = [_tool(T0 - 100), dict(USER, timestamp=iso_utc(T0 - 60))]
    w, _, ag = _note_session(tmp_path, [T0 - 50], lines)
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    assert _tasks_once(w, c, {}, T0, 0.0).get("subagents") == 0
    size = os.path.getsize(ag)
    with open(ag, "r+") as fh:
        fh.write(json.dumps(lines[0]) + "\n" + json.dumps(dict(USER, timestamp=iso_utc(T0 - 5))) + "\n")
    os.utime(ag, (T0 + 3, T0 + 3))
    assert os.path.getsize(ag) == size
    assert _tasks_once(w, c, {}, T0 + 5, 5.0).get("subagents") == 1


def test_r5_11_resume_cache_holds_across_sessions(tmp_path, monkeypatch):
    """R5-11: two sessions, one unchanged noticed agent each, 5 ticks: 2 tail reads, not 10."""
    w = standard(tmp_path)
    for repo, sid in ((w.repo_a + "/src", "sid-a"), (w.repo_b, "sid-b")):
        pdir = os.path.join(w.home, ".claude", "projects", S.transcript_slug(repo))
        sub = os.path.join(pdir, sid, "subagents")
        os.makedirs(sub, exist_ok=True)
        for f in os.listdir(sub):
            os.remove(os.path.join(sub, f))
        aid = "a0" + {"a": "1", "b": "2"}[sid[-1]]
        _agent(sub, "agent-" + aid, [_tool(T0 - 100)], 1, T0)
        note = "<task-notification>\n<task-id>%s</task-id>\n<status>completed</status>" % aid
        with open(os.path.join(pdir, sid + ".jsonl"), "a") as fh:
            fh.write(json.dumps({"type": "queue-operation", "operation": "enqueue", "content": note,
                                 "timestamp": iso_utc(T0 - 50)}) + "\n")
    calls = {"n": 0}
    real = S._last_line_epoch

    def counted(*a, **k):
        calls["n"] += 1
        return real(*a, **k)
    monkeypatch.setattr(S, "_last_line_epoch", counted)
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    for i in range(5):
        out, _ = run_sessions(w, r, c, {}, T0 + i, float(i))
    assert [s["tasks"].get("subagents") for s in out] == [0, 0]
    assert calls["n"] == 2


NOTE_LINE = (b'{"type":"queue-operation","operation":"enqueue","content":"<task-notification>'
             b'<task-id>a01</task-id>","timestamp":"2026-11-01T00:00:00Z"}\n')


def test_r5_4_skip_state_resets_on_same_size_rewrite(tmp_path):
    """R5-4 (G3): 2 MB with no newline (skip set), rewritten in place as 2 MB of newlines (same
    inode, same size), then a notice appended. Truth: the notice is there."""
    p = str(tmp_path / "t.jsonl")
    B = 2 * S.SCAN_CHUNK
    with open(p, "wb") as fh:
        fh.write(b"x" * B)
    c = S.SessionsCollector(FakeReaders({}, {}))
    assert c._noticed(p) == {}
    with open(p, "r+b") as fh:
        fh.write(b"\n" * B)
    c._noticed(p)
    with open(p, "ab") as fh:
        fh.write(NOTE_LINE)
    assert set(c._noticed(p)) == {"a01"}


def test_r5_4_announce_scan_resets_on_same_size_rewrite(tmp_path):
    p = str(tmp_path / "t.jsonl")
    B = 2 * S.SCAN_CHUNK
    with open(p, "wb") as fh:
        fh.write(b"x" * B)
    c = S.SessionsCollector(FakeReaders({}, {}))
    assert c._announced(p) == set()
    with open(p, "r+b") as fh:
        fh.write(b"\n" * B)
    with open(p, "ab") as fh:
        fh.write(b'{"t":"Command running in background with ID: b9zzz"}\n')
    assert c._announced(p) == {"b9zzz"}


class _NetClock(object):
    def __init__(self):
        self.t, self.m = T0, 1000.0

    def now(self):
        return self.t

    def mono(self):
        return self.m


class _ByteNettop(FakeReaders):
    """A nettop whose one flow carries `bytes` (the test integrates its rate per second)."""

    def __init__(self, clock):
        FakeReaders.__init__(self, {}, {})
        self.clock, self.bytes, self.execs = clock, 0.0, []

    def nettop(self, pids, timeout=3.0):
        self.execs.append(self.clock.m)
        b = int(self.bytes)
        return 0, (",bytes_in,bytes_out,re-tx,\n2.1.292.101,%d,%d,0,\n"
                   "tcp4 192.0.2.10:50001<->198.51.100.7:443,%d,%d,0,\n" % (b, b, b, b))


def test_r5_session_net_runs_every_30s_while_idle_15s_after_a_burst(tmp_path):
    """Agents-tier saving: one nettop exec per 30 s while every session read under 10 kbit/s on
    its last exec; back to 15 s as soon as one reads above."""
    from augur import core
    clk = _NetClock()
    burst = {"from": 1000.0 + 120, "to": 1000.0 + 135}
    rate = lambda m: 100_000.0 if burst["from"] < m <= burst["to"] else 100.0  # noqa: E731
    r = _ByteNettop(clk)
    net = S.SessionNetCollector(r)
    c = core.Core([net], str(tmp_path), home=str(tmp_path), clock=clk.now, mono=clk.mono, lodestar=None,
                  cpu_reader=lambda: (0.0, 0.0, 20 * 1000 * 1000))
    c.shared["session_trees"] = {"101@1793500000": [101]}
    for _ in range(200):
        c.tick()
        clk.t += 1.0
        clk.m += 1.0
        r.bytes += rate(clk.m)
    gaps = [b - a for a, b in zip(r.execs, r.execs[1:])]
    # 0: warming up (15); 15: idle -> 30, 45, 75, 105, 135 (sees the burst) -> 150 (idle) -> 30 s
    assert r.execs[:8] == [1000.0, 1015.0, 1045.0, 1075.0, 1105.0, 1135.0, 1150.0, 1180.0]
    assert set(gaps[6:]) == {30.0}
    v = c.signals["sessions.net"][1]["101@1793500000"]
    assert v["valid_until"] - v["observed_at"] == pytest.approx(core.STAMP_FACTOR * 30.0)


def test_s1_fifo_agent_file_never_blocks(tmp_path):
    """S1: a FIFO (and a symlink to one) named agent-*.jsonl is skipped. Truth: the one regular
    running agent counts, 1. open_regular refuses a FIFO without blocking (O_NONBLOCK)."""
    w = standard(tmp_path)
    pdir = os.path.join(w.home, ".claude", "projects", S.transcript_slug(w.repo_a + "/src"))
    sub = os.path.join(pdir, "sid-a", "subagents")
    for f in os.listdir(sub):
        os.remove(os.path.join(sub, f))
    _agent(sub, "agent-a01", [A_TOOL], 1, T0)
    fifo = os.path.join(str(tmp_path), "fifo")
    os.mkfifo(fifo)
    os.symlink(fifo, os.path.join(sub, "agent-alink.jsonl"))
    with pytest.raises(OSError):
        S.open_regular(fifo)
    with pytest.raises(OSError):
        S.open_regular(os.path.join(sub, "agent-alink.jsonl"))
    assert _tasks_once(w).get("subagents") == 1


def test_s4_session_outside_a_repo_publishes_unknown(tmp_path):
    """S4: cwd with no git toplevel and no registry row: project 'unknown', never the folder name."""
    w = standard(tmp_path)
    loose = os.path.join(w.tmp, "Personal", "citations")
    os.makedirs(loose)
    w.procs[201][6] = loose
    r = FakeReaders(w.procs, ru_tick(1.0))
    out, _ = run_sessions(w, r, S.SessionsCollector(r), {}, T0, 0.0)
    b = [s for s in out if s["pid"] == 201][0]
    assert (b["project"], b["project_key"]) == ("unknown", "unknown")
    assert "citations" not in json.dumps(out)


def test_rb_m9_caches_pruned_to_live_transcripts(tmp_path):
    """RB-m9: once a transcript is no longer read, its _notices/_bg_ids/_sub_state/_last_t
    entries go. Truth: after the agent file is deleted, no cache holds its path."""
    w, main, ag = _note_session(tmp_path, [T0 - 50], [_tool(T0 - 100)])
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    _tasks_once(w, c, {}, T0, 0.0)
    assert ag in c._sub_state and ag in c._last_t
    os.remove(ag)
    c._sub_state["/gone/agent-x.jsonl"] = c._notices["/gone/t.jsonl"] = c._bg_ids["/gone/t.jsonl"] = 1
    _tasks_once(w, c, {}, T0 + 5, 5.0)
    for cache in (c._sub_state, c._last_t, c._notices, c._bg_ids):
        assert not [k for k in cache if k == ag or k.startswith("/gone/")]
    assert main in c._notices                       # a live transcript keeps its offset


def test_rb_n13_sidepulse_dir_is_read_from_the_environment(tmp_path, monkeypatch):
    """RB-n13: AUGUR_HOME (ctx.storage) outside the storage root; SidePulse's state is still
    found through SIDEPULSE_STATE_DIR, then AGENT_STORAGE_ROOT. Truth: the slot written there."""
    w = standard(tmp_path)
    elsewhere = os.path.join(w.tmp, "elsewhere", "augur")
    os.makedirs(elsewhere)
    w.storage = elsewhere
    r = FakeReaders(w.procs, ru_tick(1.0))
    ctx = w.ctx(T0, 0.0)
    assert S.read_sidepulse(ctx)[0] == "ok" and 101 in S.read_sidepulse(ctx)[1]
    monkeypatch.delenv("SIDEPULSE_STATE_DIR")
    monkeypatch.setenv("AGENT_STORAGE_ROOT", os.path.join(w.tmp, "ClaudeWork"))
    assert 101 in S.read_sidepulse(ctx)[1]


def test_rb_m6_transcript_pick_is_cached_by_directory_mtime(tmp_path, monkeypatch):
    """RB-m6: a session with no SidePulse slot lists its project dir once, then only when the
    directory's mtime moves. Truth: 3 ticks, unchanged dir -> 1 listing; a new transcript -> 2."""
    w = standard(tmp_path)
    w.sidepulse([])
    calls = {"n": 0}
    real = os.scandir
    pdir_b = os.path.join(w.home, ".claude", "projects", S.transcript_slug(w.repo_b))

    def counted(p):
        if p == pdir_b:
            calls["n"] += 1
        return real(p)
    monkeypatch.setattr(S.os, "scandir", counted)
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    for i in range(3):
        run_sessions(w, r, c, {}, T0 + i, float(i))
    assert calls["n"] == 1
    open(os.path.join(pdir_b, "sid-new.jsonl"), "w").close()
    os.utime(pdir_b, (T0 + 9, T0 + 9))
    run_sessions(w, r, c, {}, T0 + 10, 10.0)
    assert calls["n"] == 2


def test_rb_m7_first_read_is_spread_under_a_byte_budget(tmp_path, monkeypatch):
    """RB-m7: a 7 MB main transcript (short lines), its agent's notice in the last line, first
    read by a fresh collector with a 3 MB budget. Truth: no tick scans more than the budget; the
    count reads warming_up (never a guessed 1) until both scanners (notices, then background
    launches, which share the budget) reach the end: 2 x 7.34 MB over 3 MB a tick = tick 5, then 0."""
    w, main, _ = _note_session(tmp_path, [], [_tool(T0 - 100)])
    line = b'{"type":"user","pad":"' + b"y" * 1000 + b'"}\n'
    with open(main, "wb") as fh:
        fh.write(line * (7 * 1024 * 1024 // len(line)))
        fh.write(json.dumps({"type": "queue-operation", "operation": "enqueue", "timestamp": iso_utc(T0 - 50),
                             "content": "<task-notification>\n<task-id>a01</task-id>"}).encode() + b"\n")
    monkeypatch.setattr(S, "SCAN_BUDGET", 3 * 1024 * 1024)
    scanned = []
    real = S.SessionsCollector._scan_lines.__func__

    def counted(cls, path, start, size, on_line, state=None):
        off = real(cls, path, start, size, on_line, state)
        scanned.append(off - start)
        return off
    monkeypatch.setattr(S.SessionsCollector, "_scan_lines", classmethod(counted))
    r = FakeReaders(w.procs, ru_tick(1.0))
    c = S.SessionsCollector(r)
    got = []
    for i in range(6):
        n0 = len(scanned)
        got.append(_tasks_once(w, c, {}, T0 + i, float(i)).get("subagents", "warming_up"))
        assert sum(scanned[n0:]) <= 3 * 1024 * 1024
    assert got == ["warming_up"] * 4 + [0, 0]
