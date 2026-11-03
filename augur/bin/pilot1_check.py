#!/usr/bin/env python3
"""Augur pilot 1 mechanical checks (DESIGN.md section 12). Run with /usr/bin/python3.
Exit 0 pass, 1 fail, 2 not enough data yet. stdlib + jsonschema only."""
import argparse, glob, json, math, os, re, signal, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(os.path.dirname(HERE), "schema", "snapshot.schema.json")
HOSTREC = "~/dev/.lodestar/companion/host-trace.json"
PASS, FAIL, PENDING = 0, 1, 2
MIN_COVERAGE = 20 / 24     # cost: hourly windows a fully elapsed check needs (R1 finding 18)
NAME = {0: "PASS", 1: "FAIL", 2: "PENDING"}


def home():
    h = os.environ.get("AUGUR_HOME")
    if h:
        return h
    helper = os.path.expanduser("~/dev/Lodestar/bin/lib/agent_storage.py")
    try:
        r = subprocess.run(["python3", helper], capture_output=True, text=True, timeout=20)
    except Exception as e:
        sys.exit(f"AUGUR_HOME unset and agent_storage.py failed: {e}")
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"AUGUR_HOME unset and agent_storage.py failed: {r.stderr.strip()[:200]}")
    return os.path.join(r.stdout.strip(), "augur")


def read_json(p):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


def jsonl(p):
    out = []
    try:
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
    except OSError:
        pass
    return out


# ---------------------------------------------------------------- machine sleep (RB4)
def slept_spans(home_, since, now):
    """[(from, to)] wall spans the producer logged as system sleep (audit.jsonl event "slept"),
    clipped to [since, now] and merged. Asleep, Augur writes nothing: that is the machine's
    state, not producer downtime, so the checks excuse it and say how much they excused."""
    out = []
    for r in jsonl(os.path.join(home_, "audit.jsonl")):
        if r.get("event") != "slept":
            continue
        try:
            a, b = max(float(r["from"]), since), min(float(r["to"]), now)
        except (KeyError, TypeError, ValueError):
            continue
        if b > a:
            out.append((a, b))
    out.sort()
    merged = []
    for a, b in out:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def slept_minutes(spans):
    """Minute indexes (epoch // 60) lying wholly inside a sleep span."""
    out = set()
    for a, b in spans:
        out.update(range(int(math.ceil(a / 60.0)), int(b // 60)))
    return out


# ---------------------------------------------------------------- validate
SID = re.compile(r"\d+@\d+")
WRITTEN_AT = re.compile(r'"written_at":\s*(-?[0-9.]+(?:[eE][-+]?[0-9]+)?)')
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")


def privacy_hits(text):
    hits = []
    if "/Users/" in text:
        hits.append("/Users/")
    if IPV4.search(text):
        hits.append("ipv4")
    if "@" in SID.sub("", text):
        hits.append("@")
    return hits


def validator():
    import jsonschema
    schema = read_json(SCHEMA)
    return jsonschema.Draft202012Validator(schema)


def cmd_validate(a):
    home_ = home()
    now = time.time()
    since = now - a.since_hours * 3600
    v = validator()
    n = failed = 0
    errs, priv = [], []
    minutes = set()

    def check(text, label):
        nonlocal n, failed
        try:
            d = json.loads(text)
        except ValueError as e:
            n += 1; failed += 1
            errs.append(f"{label}: not JSON ({e})"); return None
        n += 1
        es = sorted(v.iter_errors(d), key=lambda e: list(e.path))
        if es:
            failed += 1
            errs.append(f"{label}: {es[0].message[:120]} at /{'/'.join(map(str, es[0].path))}")
        for h in privacy_hits(text):
            priv.append(f"{label}: {h}")
        return d

    for p in sorted(glob.glob(os.path.join(home_, "samples", "snap-*.jsonl"))):
        try:
            if os.path.getmtime(p) < since:   # RB-m9: last appended before the window: skip unread
                continue
        except OSError:
            continue
        with open(p) as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                m = WRITTEN_AT.search(line)       # RB-m9: filter on time BEFORE the full parse
                try:
                    w = float(m.group(1)) if m else now
                except ValueError:
                    w = now
                if w < since:
                    continue
                d = check(line, f"{os.path.basename(p)}:{i}")
                if d is not None:
                    minutes.add(int(w // 60))
    live = os.path.join(home_, "live", "snapshot.json")
    if os.path.exists(live):
        with open(live) as f:
            check(f.read(), "live/snapshot.json")
    nsamples = len(minutes)
    if not minutes:
        print(f"validate: no samples in the last {a.since_hours} h under {home_}/samples")
        return PENDING
    first_min = min(minutes)
    excused = {m for m in slept_minutes(slept_spans(home_, since, now))
               if m not in minutes and first_min <= m <= int(now // 60)}
    span_min = (now - since) / 60.0
    covered_span = (int(now // 60) - first_min + 1)
    window_min = min(span_min, covered_span) - len(excused)
    coverage = nsamples / max(1.0, window_min)
    print(f"validate: validated={n} failed={failed} minutes_present={nsamples} "
          f"window_min={window_min:.0f} coverage={coverage:.3f} privacy_hits={len(priv)} "
          f"slept_excused_min={len(excused)}")
    for e in errs[:3]:
        print("  error:", e)
    for e in priv[:3]:
        print("  privacy:", e)
    if failed or priv:
        return FAIL
    if covered_span + len(excused) < 0.95 * span_min:
        print(f"  pending: samples span only {covered_span} of {span_min:.0f} minutes")
        return FAIL if coverage < 0.95 else PENDING
    return PASS if coverage >= 0.95 else FAIL


# ---------------------------------------------------------------- cost
def cmd_cost(a):
    home_ = home()
    now = time.time()
    since = now - a.since_hours * 3600
    rows = jsonl(os.path.join(home_, "cost.jsonl"))
    h1 = [r for r in rows if r.get("window") == "1h" and r.get("t", 0) >= since]
    m10 = [r for r in rows if r.get("window") == "10m"]
    if m10:
        print("latest 10m:", json.dumps(m10[-1], sort_keys=True))
    if not h1:
        print("cost: no 1h windows yet")
        return PENDING
    c = {"pass": 0, "watch": 0, "fail": 0}
    worst = (None, -1.0)
    for r in h1:
        c[r.get("verdict")] = c.get(r.get("verdict"), 0) + 1
        for k, val in (r.get("collectors") or {}).items():
            if isinstance(val, (int, float)) and val > worst[1]:
                worst = (k, val)
    n = len(h1)
    # RB4: hours the machine slept are not hours the producer could log; excuse them
    slept_h = sum(b - a for a, b in slept_spans(home_, since, now)) / 3600.0
    hours = max(1.0, a.since_hours - slept_h)
    need = 22 if hours >= 24 else max(1, round(22 / 24 * hours))
    print(f"cost: windows={n} pass={c['pass']} watch={c['watch']} fail={c['fail']} "
          f"worst_collector={worst[0]}({worst[1]:.3f}%)  bar: pass>=22 of 24 "
          f"slept_excused_h={slept_h:.2f}")
    if c["pass"] >= need:
        return PASS
    if n - c["pass"] > hours - need or n >= hours:
        return FAIL
    # R1 finding 18: restarts lose hour lines, so a fully elapsed window may never reach `need`
    # lines. Once the pilot has run the whole window (its first line is within an hour of the
    # window's start), judge the windows there are: coverage >= MIN_COVERAGE of the hours, and
    # the same pass fraction (22/24) of those windows. Settles; never pending forever.
    first = min((r.get("t", now) for r in rows), default=now)
    if first <= since + 3600:
        min_n = math.ceil(MIN_COVERAGE * hours)
        if n < min_n:
            print(f"  fail: coverage {n} of {hours:.1f} awake hourly windows < {min_n} ({MIN_COVERAGE:.0%})")
            return FAIL
        want = math.ceil(n * need / hours)
        print(f"  judged on {n} available windows (coverage {n / hours:.0%}): need {want} pass")
        return PASS if c["pass"] >= want else FAIL
    return PENDING


# ---------------------------------------------------------------- stale / off
def read_snap(home_):
    return read_json(os.path.join(home_, "live", "snapshot.json"))


def cmd_stale(a):
    home_ = home()
    s = read_snap(home_)
    if not s:
        print("stale: no readable snapshot"); return PENDING
    pid = s["producer"]["pid"]
    try:
        os.kill(pid, 0)
        comm = subprocess.run(["ps", "-o", "comm=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    except OSError as e:
        print(f"stale: producer pid {pid} not alive ({e})"); return FAIL
    if "python" not in os.path.basename(comm).lower() and "py" != os.path.basename(comm):
        print(f"stale: pid {pid} executable is {comm!r}, not python; refusing"); return FAIL
    t0 = time.time()
    os.kill(pid, signal.SIGSTOP)
    measured = None
    fresh = False
    try:
        while time.time() - t0 < 30:
            time.sleep(0.25)
            d = read_snap(home_)
            if d and time.time() > d["valid_until"]:
                measured = time.time() - t0
                break
    finally:
        os.kill(pid, signal.SIGCONT)
    t1 = time.time()
    while time.time() - t1 < 20:
        d = read_snap(home_)
        if d and d["valid_until"] > time.time() and d["written_at"] > t0:
            fresh = True; break
        time.sleep(0.25)
    print(f"stale: seconds_until_stale={measured if measured is None else round(measured, 2)} "
          f"bar<=10 refreshed_after_cont={fresh}")
    return PASS if (measured is not None and measured <= 10 and fresh) else FAIL


def cmd_off(a):
    home_ = home()
    flag = os.path.join(home_, "off")
    os.makedirs(home_, exist_ok=True)
    t0 = time.time()
    t_on = t_back = None
    open(flag, "a").close()
    try:
        while time.time() - t0 < 20:
            d = read_snap(home_)
            if d and d.get("off") is True:
                t_on = time.time() - t0; break
            time.sleep(0.25)
    finally:
        try:
            os.remove(flag)
        except OSError:
            pass
    t1 = time.time()
    while time.time() - t1 < 20:
        d = read_snap(home_)
        if d and not d.get("off"):
            t_back = time.time() - t1; break
        time.sleep(0.25)
    f = lambda x: None if x is None else round(x, 2)
    print(f"off: seconds_until_off={f(t_on)} (bar<=5) seconds_until_back={f(t_back)}")
    return PASS if (t_on is not None and t_on <= 5 and t_back is not None) else FAIL


# ---------------------------------------------------------------- pair
def within(a, h, rel=0.10, floor=0.0):
    return abs(a - h) <= max(rel * abs(h), floor)


def pair_report(path):
    rows = jsonl(path)
    n = len(rows)
    if n == 0:
        print("pair: no pairs"); return PENDING
    pe = sum(r["procs_a"] == r["procs_h"] for r in rows)
    p10 = sum(within(r["procs_a"], r["procs_h"]) for r in rows)
    cs = sum(within(r["cpu_a"], r["cpu_h"]) for r in rows)
    cf = sum(within(r["cpu_a"], r["cpu_h"], floor=0.02) for r in rows)
    pct = lambda k: 100.0 * k / n
    mean_dt = sum(abs(r.get("dt", 0)) for r in rows) / n
    print(f"pair: pairs={n} procs_exact={pct(pe):.1f}% procs_within10={pct(p10):.1f}% "
          f"cpu_within10_strict={pct(cs):.1f}% cpu_within10_or_0.02cores={pct(cf):.1f}% "
          f"mean|dt|={mean_dt:.1f}s  bar>=95%")
    print("pair note: hostrec cpu is over its 10 s tick, Augur's over its 5 s tick; windows differ, "
          "so residual disagreement at load is expected. Bar applies to procs_within10 and cpu with floor.")
    return PASS if (pct(p10) >= 95 and pct(cf) >= 95) else FAIL


def cmd_pair(a):
    home_ = home()
    out = a.out or os.path.join(home_, "pair-hostrec.jsonl")
    if a.report:
        return pair_report(a.report)
    end = time.time() + a.minutes * 60
    last_gen = None
    while time.time() < end:
        h = read_json(HOSTREC)
        s = read_snap(home_)
        if h and s and h.get("generated") != last_gen:
            last_gen = h.get("generated")
            now = time.time()
            by_pid = {x.get("pid"): x for x in s.get("sessions", [])}
            with open(out, "a") as f:
                for r in h.get("sessions", []):
                    x = by_pid.get(r.get("pid"))
                    if not x:
                        continue
                    ld = x.get("load") or {}
                    if "unknown" in ld or now > ld.get("valid_until", 0):
                        continue
                    if None in (r.get("procs"), r.get("cpu"), ld.get("procs"), ld.get("cpu_cores")):
                        continue
                    f.write(json.dumps({
                        "t": now, "pid": r["pid"], "hostrec_generated": h["generated"],
                        "dt": ld.get("observed_at", now) - h["generated"],
                        "procs_h": r["procs"], "procs_a": ld["procs"],
                        "cpu_h": r["cpu"], "cpu_a": ld["cpu_cores"],
                        "fp_h_gb": (r.get("fp") or 0) / 1e9, "mem_a_gb": ld.get("mem_gb")}) + "\n")
        time.sleep(10)
    return pair_report(out)


# ---------------------------------------------------------------- nettop
def nettop_eval(rows, since=None):
    """rows: audit lines. Returns (code, text)."""
    rows = [r for r in rows if isinstance(r.get("audit"), dict)]
    if since is not None:
        rows = [r for r in rows if r.get("t", 0) >= since]
    if not rows:
        return PENDING, "nettop: no audit lines"
    keys = ["iface_rx_bytes", "iface_tx_bytes", "session_rx_bytes", "session_tx_bytes"]
    # counters are cumulative per producer run: sum (last - first) over every run (pid, started_at)
    runs = {}
    for r in rows:
        runs.setdefault((r.get("pid"), r.get("started_at")), []).append(r)
    d = {k: 0 for k in keys}
    for seg in runs.values():
        if len(seg) < 2:
            continue
        for k in keys:
            d[k] += seg[-1]["audit"].get(k, 0) - seg[0]["audit"].get(k, 0)
    irx, itx, srx, stx = (d[k] for k in keys)
    isum, ssum = irx + itx, srx + stx
    if isum <= 0:
        return PENDING, f"nettop: interface bytes delta is {isum}; not enough traffic yet"
    bad = ssum > isum or srx > irx or stx > itx
    return (FAIL if bad else PASS), (
        f"nettop: session={ssum} iface={isum} ratio={ssum / isum:.3f} "
        f"rx_ratio={srx / irx if irx else 0:.3f} tx_ratio={stx / itx if itx else 0:.3f} "
        f"falsifier(session>iface)={'TRIPPED' if bad else 'not tripped'}")


def cmd_nettop(a):
    rows = jsonl(os.path.join(home(), "audit.jsonl"))
    since = time.time() - a.since_hours * 3600 if a.since_hours else None
    code, text = nettop_eval(rows, since)
    print(text)
    return code


# ---------------------------------------------------------------- groundtruth (a load test)
GT_DIR = os.path.join(os.path.expanduser("~"), "ClaudeWork", "augur", "scratch", "groundtruth")


def load_test_allowed(snap, now=None):
    """(allowed, why). Load testing ONLY on a trusted on-site network without the VPN. Read
    from Augur's own live machine.vpn: on_site true AND state "down", from a snapshot that is not
    stale. Anything else, unknown included, refuses."""
    now = time.time() if now is None else now
    if not snap:
        return False, "no readable snapshot"
    if now > snap.get("valid_until", 0):
        return False, "snapshot is stale (producer not running?)"
    v = (snap.get("machine") or {}).get("vpn")
    if not v or "unknown" in v or now > v.get("valid_until", 0):
        return False, "machine.vpn is absent, unknown or stale"
    if v.get("on_site") is not True:
        return False, "not on the on-site network (on_site=%s)" % v.get("on_site")
    if v.get("state") != "down":
        return False, "VPN state is %r" % v.get("state")
    return True, "on the on-site network, VPN down"


def cmd_groundtruth(a):
    """The controlled busy-loop check (PILOT1.md): refuses unless load_test_allowed."""
    ok, why = load_test_allowed(read_snap(home()))
    if not ok:
        print(f"groundtruth: refused: {why}. Load testing runs only on the on-site network without the VPN.")
        return PENDING
    print(f"groundtruth: allowed ({why}); running {GT_DIR}/gt.py against root {a.root}")
    r = subprocess.run(["/usr/bin/nice", "-n", "10", sys.executable, os.path.join(GT_DIR, "gt.py"),
                        str(a.root), a.tag])
    if r.returncode:
        return FAIL
    r = subprocess.run([sys.executable, os.path.join(GT_DIR, "analyze.py"), a.tag])
    return FAIL if r.returncode else PASS


# ---------------------------------------------------------------- all
def cmd_all(a):
    results = []
    for name, fn in (("validate", cmd_validate), ("cost", cmd_cost), ("nettop", cmd_nettop)):
        print(f"--- {name}")
        results.append((name, fn(a)))
    print("\n### Pilot 1 mechanical checks\n")
    for name, c in results:
        print(f"- {name}: {NAME[c]}")
    print("- stale / off / pair: run separately (intrusive)")
    codes = [c for _, c in results]
    return FAIL if FAIL in codes else (PENDING if PENDING in codes else PASS)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pilot1_check")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, hours=24.0):
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        if hours is not None:
            p.add_argument("--since-hours", type=float, default=hours)
        return p
    add("validate", cmd_validate)
    add("cost", cmd_cost)
    add("stale", cmd_stale, None)
    add("off", cmd_off, None)
    add("nettop", cmd_nettop, 0)
    add("all", cmd_all)
    p = add("groundtruth", cmd_groundtruth, None)
    p.add_argument("--root", type=int, required=True, help="pid of the session root to load")
    p.add_argument("--tag", default="run3")
    p = add("pair", cmd_pair, None)
    p.add_argument("--minutes", type=float, default=10)
    p.add_argument("--out")
    p.add_argument("--report")
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
