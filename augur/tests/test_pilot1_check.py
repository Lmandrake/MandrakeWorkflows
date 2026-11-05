import json, os, subprocess, sys, time, importlib.util
import pytest

AUG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("pilot1_check", os.path.join(AUG, "bin", "pilot1_check.py"))
pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)
jsonschema = pytest.importorskip("jsonschema")
EXAMPLE = json.load(open(os.path.join(AUG, "schema", "example.json")))


def run(home, *args):
    env = dict(os.environ, AUGUR_HOME=str(home))
    r = subprocess.run([sys.executable, os.path.join(AUG, "bin", "pilot1_check.py"), *args],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout


def snap(t):
    s = json.loads(json.dumps(EXAMPLE)); s["written_at"] = t; s["valid_until"] = t + 10
    return s


def write_samples(home, n, mutate=None, now=None):
    now = now or time.time()
    d = home / "samples"; d.mkdir(parents=True, exist_ok=True)
    with open(d / "snap-2026-10-31.jsonl", "w") as f:
        for i in range(n):
            s = snap(now - (n - 1 - i) * 60)
            if mutate and i == n - 1:
                mutate(s)
            f.write(json.dumps(s) + "\n")


def test_validate_pass(tmp_path):
    write_samples(tmp_path, 30)
    code, out = run(tmp_path, "validate", "--since-hours", "0.5")
    assert code == 0, out


def test_validate_schema_fail(tmp_path):
    write_samples(tmp_path, 30, lambda s: s.pop("seq"))
    code, out = run(tmp_path, "validate", "--since-hours", "0.5")
    assert code == 1 and "failed=1" in out


def test_validate_privacy(tmp_path):
    write_samples(tmp_path, 30, lambda s: s["producer"].update(rev="/Users/x"))
    assert run(tmp_path, "validate", "--since-hours", "0.5")[0] == 1
    write_samples(tmp_path, 30, lambda s: s["producer"].update(rev="10.1.2.3"))
    assert run(tmp_path, "validate", "--since-hours", "0.5")[0] == 1
    write_samples(tmp_path, 30, lambda s: s["producer"].update(rev="a@b"))
    assert run(tmp_path, "validate", "--since-hours", "0.5")[0] == 1


def test_privacy_allows_session_id():
    assert pc.privacy_hits('{"id":"123@1793500000"}') == []
    assert pc.privacy_hits("1793500000.5") == []


def test_validate_no_data(tmp_path):
    assert run(tmp_path, "validate")[0] == 2


def cost_rows(home, verdicts):
    now = time.time()
    with open(home / "cost.jsonl", "w") as f:
        for i, v in enumerate(verdicts):
            f.write(json.dumps({"t": now - (len(verdicts) - i) * 60, "window": "1h", "verdict": v,
                                "collectors": {"fast": 0.1, "agents": 0.3}}) + "\n")


def test_cost_bar(tmp_path):
    cost_rows(tmp_path, ["pass"] * 22 + ["watch"] * 2)
    assert run(tmp_path, "cost")[0] == 0
    cost_rows(tmp_path, ["pass"] * 21 + ["watch"] * 3)
    code, out = run(tmp_path, "cost")
    assert code == 1 and "worst_collector=agents" in out
    cost_rows(tmp_path, ["pass"] * 10)
    assert run(tmp_path, "cost")[0] == 2


def audit(home, rows):
    with open(home / "audit.jsonl", "w") as f:
        for i, (ir, it, sr, st) in enumerate(rows):
            f.write(json.dumps({"t": time.time() - 100 + i, "pid": 5, "started_at": 1, "audit": {
                "iface_rx_bytes": ir, "iface_tx_bytes": it, "session_rx_bytes": sr,
                "session_tx_bytes": st, "iface_ticks": 1, "session_net_ticks": 1}}) + "\n")


def test_nettop(tmp_path):
    audit(tmp_path, [(0, 0, 0, 0), (1000, 500, 400, 100)])
    code, out = run(tmp_path, "nettop"); assert code == 0 and "ratio=0.333" in out
    audit(tmp_path, [(0, 0, 0, 0), (1000, 500, 1200, 10)])  # rx over, sum under
    assert run(tmp_path, "nettop")[0] == 1
    audit(tmp_path, [(0, 0, 0, 0), (1000, 500, 1000, 600)])  # sum over
    assert run(tmp_path, "nettop")[0] == 1
    audit(tmp_path, [(0, 0, 0, 0)])
    assert run(tmp_path, "nettop")[0] == 2


def test_pair_report(tmp_path):
    rows = []
    for i in range(20):
        rows.append({"procs_h": 3, "procs_a": 3, "cpu_h": 0.0, "cpu_a": 0.01, "dt": 1})
    p = tmp_path / "p.jsonl"; p.write_text("\n".join(map(json.dumps, rows)))
    code, out = run(tmp_path, "pair", "--report", str(p))
    assert code == 0 and "procs_exact=100.0%" in out and "cpu_within10_strict=0.0%" in out \
        and "cpu_within10_or_0.02cores=100.0%" in out
    rows[0]["procs_a"] = 5
    for r in rows[:5]:
        r["procs_a"] = 5
    p.write_text("\n".join(map(json.dumps, rows)))
    code, out = run(tmp_path, "pair", "--report", str(p))
    assert code == 1 and "procs_exact=75.0%" in out


def test_install_render_only(tmp_path):
    out = tmp_path / "x.plist"
    env = dict(os.environ, AUGUR_HOME=str(tmp_path / "ah"))
    r = subprocess.run([os.path.join(AUG, "bin", "install.sh"), "--render-only", str(out)],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    txt = out.read_text()
    assert "__" not in txt and str(tmp_path / "ah") in txt and "com.mandrake.augur" in txt
    assert subprocess.run(["plutil", "-lint", str(out)], capture_output=True).returncode == 0


def test_cost_settles_when_restarts_lost_hour_lines(tmp_path):
    """R1 finding 18: 21 pass lines over a fully elapsed 24 h (3 hour lines lost to restarts)
    must settle on a verdict, never stay pending; too little coverage fails, with the reason."""
    now = time.time()
    with open(tmp_path / "cost.jsonl", "w") as f:
        for i in range(21):
            f.write(json.dumps({"t": now - 23.5 * 3600 + i * 3600 * 1.1, "window": "1h",
                                "verdict": "pass", "collectors": {}}) + "\n")
    code, out = run(tmp_path, "cost", "--since-hours", "24")
    assert code == 0, out
    with open(tmp_path / "cost.jsonl", "w") as f:
        for i in range(12):
            f.write(json.dumps({"t": now - 23.5 * 3600 + i * 7000, "window": "1h",
                                "verdict": "pass", "collectors": {}}) + "\n")
    code, out = run(tmp_path, "cost", "--since-hours", "24")
    assert code == 1 and "coverage" in out


def gate_snap(vpn, age=0.0):
    s = snap(time.time() - age)
    s["machine"] = {} if vpn is None else {"vpn": dict(vpn, observed_at=time.time() - age,
                                                       valid_until=time.time() - age + 5)}
    return s


def test_load_test_gate_needs_onsite_network_and_no_vpn():
    """Load testing only on a trusted on-site network without the VPN; unknown = refuse."""
    ok = lambda v, **k: pc.load_test_allowed(gate_snap(v, **k))[0]  # noqa: E731
    assert ok({"state": "down", "on_site": True}) is True
    assert ok({"state": "up", "on_site": True}) is False
    assert ok({"state": "down", "on_site": False}) is False
    assert ok({"state": "down"}) is False                       # SSID unknown
    assert ok({"unknown": "read_failed"}) is False
    assert ok(None) is False                                    # no vpn signal at all
    assert ok({"state": "down", "on_site": True}, age=60) is False   # stale snapshot
    assert pc.load_test_allowed(None)[0] is False


def test_groundtruth_refuses_off_site(tmp_path):
    (tmp_path / "live").mkdir()
    (tmp_path / "live" / "snapshot.json").write_text(json.dumps(gate_snap({"state": "up", "on_site": False})))
    code, out = run(tmp_path, "groundtruth", "--root", "1")
    assert code == 2 and "refused" in out


# --------------------------------------------------------------------------- R5 RB4, RB-m9, RB-n15

def _slept(home, spans):
    with open(home / "audit.jsonl", "a") as f:
        for a, b in spans:
            f.write(json.dumps({"t": b, "event": "slept", "from": a, "to": b, "slept_s": b - a}) + "\n")


def test_rb4_validate_excuses_machine_sleep(tmp_path):
    now = time.time()
    # 60 min window: samples for minutes 0-19 and 40-59 (40 of 60 = 67 %), lid closed 20-40
    d = tmp_path / "samples"; d.mkdir()
    with open(d / "snap-2026-10-31.jsonl", "w") as f:
        for i in list(range(0, 20)) + list(range(40, 60)):
            f.write(json.dumps(snap(now - (59 - i) * 60)) + "\n")
    code, out = run(tmp_path, "validate", "--since-hours", "1")
    assert code == 1, out                                   # no sleep logged: real downtime
    _slept(tmp_path, [(now - 40 * 60 - 30, now - 19 * 60 - 30)])
    code, out = run(tmp_path, "validate", "--since-hours", "1")
    assert code == 0, out
    assert "slept_excused_min=" in out and "slept_excused_min=0" not in out


def test_rb4_cost_excuses_slept_hours(tmp_path):
    now = time.time()
    with open(tmp_path / "cost.jsonl", "w") as f:           # 18 pass lines over 24 h, 6 h asleep
        for i in range(18):
            f.write(json.dumps({"t": now - (23 - i) * 3600 + 1, "window": "1h", "verdict": "pass",
                                "collectors": {"fast": 0.1}}) + "\n")
    code, out = run(tmp_path, "cost")
    assert code != 0, out
    _slept(tmp_path, [(now - 6 * 3600, now)])
    code, out = run(tmp_path, "cost")
    assert code == 0 and "slept_excused_h=6.00" in out, out


def test_rbm9_validate_skips_lines_outside_the_window_without_parsing(tmp_path, monkeypatch):
    now = time.time()
    d = tmp_path / "samples"; d.mkdir()
    old = d / "snap-2026-01-01.jsonl"
    old.write_text("{not json at all\n" * 3)                # never parsed: older than the window
    os.utime(str(old), (now - 86400 * 3, now - 86400 * 3))
    with open(d / "snap-2026-10-31.jsonl", "w") as f:
        f.write("{\"written_at\": %f, broken\n" % (now - 86400 * 2))   # old line in a live file
        for i in range(30):
            f.write(json.dumps(snap(now - (29 - i) * 60)) + "\n")
    code, out = run(tmp_path, "validate", "--since-hours", "0.5")
    assert code == 0 and "validated=30 " in out, out


def test_rbn15_unwritable_storage_backs_off_in_process(tmp_path):
    sys.path.insert(0, AUG)
    from augur import main as amain
    waits, logs = [], []
    calls = {"n": 0}

    def build():
        calls["n"] += 1
        if calls["n"] < 4:
            raise OSError(30, "Read-only file system", "/Users/x/agent-storage/augur/live")
        return "core"
    assert amain.make_core(build, sleep=waits.append, log=logs.append) == "core"
    assert waits == [5.0, 15.0, 60.0] and len(logs) == 3
    assert all("errno 30" in m and "/Users/" not in m for m in logs)
    with pytest.raises(OSError):
        amain.make_core(lambda: (_ for _ in ()).throw(OSError(30, "ro")), sleep=waits.append,
                        log=logs.append, tries=2)


def test_n4_rendered_plist_sets_umask_077(tmp_path):
    import plistlib
    out = tmp_path / "x.plist"
    env = dict(os.environ, AUGUR_HOME=str(tmp_path / "ah"))
    r = subprocess.run([os.path.join(AUG, "bin", "install.sh"), "--render-only", str(out)],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert plistlib.loads(out.read_bytes())["Umask"] == 0o077


def test_rbn14_scheduled_check_stamps_in_utc(tmp_path):
    txt = open(os.path.join(AUG, "bin", "scheduled_check.sh")).read()
    assert 'date -u +%Y-%m-%dT%H%M%SZ' in txt
