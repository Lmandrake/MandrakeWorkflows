#!/usr/bin/env python3
"""demo_feed.py - writes a changing, realistic Augur snapshot (augur/schema/snapshot.schema.json, version 1.1).

  demo_feed.py [--out PATH] [--period 2] [--seed 20261031] [--duration SEC] [--once]
               [--at T] [--speed X] [--scenario NAME] [--list-scenarios] [--print] [--check]

Sprites reads ONE input shape, Augur's snapshot; this stands in for Augur (producer.name "demo_feed").
--out defaults to $SPRITES_STATE, else ~/ClaudeWork/sprites/live/demo_snapshot.json (atomic replace; never Augur's own path).
--at T evaluates the simulation at sim-second T (deterministic: same seed+T => identical JSON, including written_at).
--speed X multiplies sim time (10 = fast churn). --scenario NAME freezes a named test state (see --list-scenarios);
default is the full cycling demo (sessions arrive/leave, state cycles, strain/VPN/memory episodes, omitted fields,
per-project burning counts, Lodestar closed phases). The schedule is generated up front from the seeded RNG over a
2 h loop, so state_at(t, seed) is a pure function. Pids are fake (90000+, checked not to exist).
Mapping: the internal simulation state is converted by to_augur(): level -> machine.strain (score = level/0.75),
absent strain -> no machine.bandwidth block, absent rx/tx -> session net {"unknown": "read_failed"}, valid_until =
written_at + 3 x period. --check validates the output (jsonschema if importable, else a structural check of required
keys); exits 1 on failure. producer.name "demo_feed" differs from the schema's const "augur" by design; the check
relaxes only that const.
"""
import argparse, copy, json, math, os, random, re, signal, sys, tempfile, time, zlib

EPOCH0 = 1793500000.0
HORIZON = 7200.0
PROJECTS = ["Lodestar", "SidePulse", "Granite", "ProjectCert", "ProjectDial", "Machinist", "Waypoint", "Augur"]
LODESTAR_CLOSED = [(600, 900), (1200, 1500)]     # per 1800 s: no Lodestar session; burning drops to 0 from 1260
LODESTAR_ZERO = (1260, 1500)


def nz(key, t, period):
    """Smooth deterministic noise in 0..1."""
    h = zlib.crc32(str(key).encode())
    a, b = (h & 0xFFFF) / 65535 * 6.283, (h >> 16) / 65535 * 6.283
    return 0.5 + 0.25 * math.sin(t / period * 6.283 + a) + 0.25 * math.sin(t / (period * 0.37) * 6.283 + b)


def fake_pid(n):
    pid = 90000 + n * 7
    while True:
        try:
            os.kill(pid, 0)
            pid += 1
        except ProcessLookupError:
            return pid
        except PermissionError:
            pid += 1


def gen_states(rng, t0, t1, managed):
    segs, t, st = [], t0, rng.choice(["working", "working", "idle"])
    while t < t1:
        d = {"working": rng.uniform(30, 120), "idle": rng.uniform(10, 60), "needs": rng.uniform(20, 120)}[st]
        segs.append((t, t + d, st))
        t += d
        st = "idle" if st in ("working", "needs") and rng.random() < .5 else (
            "needs" if st == "idle" and rng.random() < .1 else "working")
    return segs


def events(rng, gap, dur, **extra):
    out, t = [], rng.uniform(*gap)
    while t < HORIZON:
        d = rng.uniform(*dur)
        out.append(dict(t0=t, t1=t + d, **{k: (f() if callable(f) else f) for k, f in extra.items()}))
        t += d + rng.uniform(*gap)
    return out


def build_schedule(seed):
    rng = random.Random(seed)
    sess, n = [], 0
    slots = [(PROJECTS, (250, 600), (3, 40))] * 4 + [(PROJECTS, (120, 300), (60, 240))] * 3
    for projs, life, gap in slots:
        t = -rng.uniform(0, 250)
        while t < HORIZON:
            n += 1
            e = t + rng.uniform(*life)
            sess.append(dict(n=n, project=rng.choice(projs), managed=True, t0=t, t1=e, states=gen_states(rng, t, e, True)))
            t = e + rng.uniform(*gap)
    t = -rng.uniform(0, 500)
    while t < HORIZON:
        n += 1
        e = t + rng.uniform(600, 1500)
        sess.append(dict(n=n, project=rng.choice(["ollama", "scratch"]), managed=False, t0=t, t1=e,
                         states=gen_states(rng, t, e, False)))
        t = e + rng.uniform(10, 60)
    for s in sess:
        s["pid"] = fake_pid(s["n"])
        s["cpu_scale"] = rng.uniform(.6, 1.2)
        s["mem0"] = rng.uniform(.3, 1.6)
    proj = {}
    for p in PROJECTS:
        t, b, steps = 0.0, rng.randint(0, 9), []
        while t < HORIZON + 300:
            b = max(0, min(14, b + rng.choice([-2, -1, -1, 0, 1, 1, 2])))
            if p == "Lodestar" and b == 0 and rng.random() < .7:
                b = 3
            r = rng.random()
            steps.append((t, b, r, rng.random()))
            t += rng.uniform(120, 300)
        proj[p] = steps
    ev = dict(
        mach=events(rng, (150, 400), (25, 40), peak=lambda: rng.choice([2, 2.5, 3]), thermal=lambda: rng.choice([0, 1, 1])),
        bw=events(rng, (200, 500), (25, 60), strain=lambda: rng.uniform(.6, .9)),
        vpn=events(rng, (400, 900), (15, 25)),
        mem=events(rng, (300, 700), (8, 20), lvl=lambda: rng.choice([1, 1, 2])),
        norx=events(rng, (200, 500), (30, 80), k=lambda: rng.random()),
        nostrain=events(rng, (500, 1000), (30, 90)),
        # drawn last so every earlier draw (and so the old schedule) is unchanged
        onsite=events(rng, (500, 1100), (150, 400)),
        api=events(rng, (250, 600), (25, 50), kind=lambda: rng.choice(["network", "network", "rate_limit", "server"])),
    )
    return dict(sess=sess, proj=proj, ev=ev)


_cache = {}


def active(evs, t):
    return next((e for e in evs if e["t0"] <= t < e["t1"]), None)


def burning_at(sched, p, t):
    m = t % 1800
    if p == "Lodestar":
        if LODESTAR_ZERO[0] <= m < LODESTAR_ZERO[1]:
            return 0, 0, 0, 0
    cur = [s for s in sched["proj"][p] if s[0] <= t][-1]
    b = cur[1]
    if p == "Lodestar" and any(a <= m < c for a, c in LODESTAR_CLOSED):
        b = max(b, 3)
    red = round(b * cur[2] * .5)
    ver = round((b - red) * cur[3] * .4)
    return b, red, b - red - ver, ver


def mk_proj(counts):
    return [dict(name=p, burning=b[0], burning_red=b[1], burning_amber=b[2], burning_verify=b[3]) for p, b in counts]


def state_at(t, seed, wall0=None):
    wall0 = EPOCH0 if wall0 is None else wall0
    if (seed) not in _cache:
        _cache[seed] = build_schedule(seed)
    sched = _cache[seed]
    cyc, tt = divmod(t, HORIZON)
    ev = {k: active(v, tt) for k, v in sched["ev"].items()}
    m_ = tt % 1800
    closed = any(a <= m_ < b for a, b in LODESTAR_CLOSED)
    out, mbps = [], 0.0
    bw = ev["bw"]
    for s in sched["sess"]:
        if not (s["t0"] <= tt < s["t1"]) or (closed and s["project"] == "Lodestar"):
            continue
        seg = next(x for x in s["states"] if x[0] <= tt < x[1])
        st = seg[2]
        k = s["pid"]
        w, wi = nz(f"c{k}", tt, 25), nz(f"r{k}", tt, 40)
        if st == "working":
            cpu, lw, procs = (.4 + 3.1 * w) * s["cpu_scale"], .3 + .7 * wi, round(nz(f"p{k}", tt, 60) * 10)
        else:
            cpu, lw, procs = (.03 if st == "idle" else .02) + .01 * w, .08 * wi, round(nz(f"p{k}", tt, 90) * 3)
        if bw and st == "working" and k % 2 == 0:
            lw = .85 + .15 * wi
        rx = .02 * 1250 ** lw
        tx = max(.02, rx * (.15 + .4 * nz(f"t{k}", tt, 30)))
        mbps += rx + tx
        d = dict(id=f"{k}@{int(wall0 + s['t0'] + cyc * HORIZON)}", pid=k, project=s["project"], managed=s["managed"],
                 started_at=float(int(wall0 + s["t0"] + cyc * HORIZON)), since=round(wall0 + cyc * HORIZON + max(seg[0], s["t0"]), 1), cpu=round(max(.02, min(4, cpu)), 2),
                 mem=round(min(2.5, s["mem0"] + .5 * nz(f"m{k}", tt, 200) + (.3 if st == "working" else 0)), 2),
                 procs=int(min(10, procs)), state=st, rx=round(min(25, rx), 2), tx=round(min(25, tx), 2))
        nr = ev["norx"]
        if nr and (k % 5) == int(nr["k"] * 5):
            del d["rx"], d["tx"]
        out.append(d)
    out.sort(key=lambda d: d["started_at"])
    tc = sum(d["cpu"] for d in out)
    mc = ev["mach"]
    level = min(3, tc / 12 + .05 * nz("lv", tt, 50))
    thermal = 0
    if mc:
        ramp = min(1, (tt - mc["t0"]) / 8, (mc["t1"] - tt) / 8)
        level, thermal = max(level, mc["peak"] * max(0, ramp)), mc["thermal"]
    vpn_down = ev["vpn"] is not None
    # three-signal link (review R1 #12): on the on-site network in its own windows (so VPN down on site happens), API failures with a reason
    net = dict(mbps=round(mbps, 2), vpn="down" if vpn_down else "up", on_site=ev["onsite"] is not None, loss=0,
               api=("failing", ev["api"]["kind"]) if ev["api"] else ("ok", None))
    if not ev["nostrain"]:
        net["strain"] = round(bw["strain"] if bw else min(.5, mbps / 80), 2)
    if vpn_down and not ev["nostrain"]:
        net["loss"] = 1
    mem = ev["mem"]
    ids = {d["project"] for d in out}
    projects = mk_proj((p, burning_at(sched, p, tt)) for p in PROJECTS if p in ids or p == "Lodestar" or burning_at(sched, p, tt)[0] > 0)
    return dict(schema=1, t=wall0 + t, producer_hint="demo_feed", sessions=out,
                m=dict(level=round(level, 2), thermal=thermal, mempress=mem["lvl"] if mem else 0), net=net,
                projects=projects)


# ---- scenarios: fixed, deterministic ----
def S(proj, pid, state, managed=True, cpu=None, rx=None, tx=None, mem=1.0, procs=None):
    cpu = cpu if cpu is not None else {"working": 1.8, "idle": .03, "needs": .02}[state]
    rx = rx if rx is not None else {"working": 1.5, "idle": .02, "needs": .03}[state]
    tx = tx if tx is not None else rx * .3
    st0 = EPOCH0 - 3000 + pid % 100
    return dict(id=f"{pid}@{int(st0)}", pid=pid, project=proj, managed=managed, started_at=st0, since=EPOCH0 - 60, cpu=cpu, mem=mem,
                procs=procs if procs is not None else (3 if state == "working" else 0), state=state,
                rx=rx, tx=round(tx, 2))


def P(*items):
    return mk_proj((n, (b, b // 3, b - b // 3, 0)) for n, b in items)


def scen(sessions, m=(0, 0, 0), net=None, projects=None):
    """net: vpn "up"/"down"/None (None = no vpn block), on_site, api (state, error_kind) or None (no api block)."""
    net = dict(dict(vpn="up", on_site=False, loss=0, strain=.05, api=("ok", None)), **(net or {}))
    ss = sessions
    net["mbps"] = round(sum(s.get("rx", 0) + s.get("tx", 0) for s in ss), 2)
    return lambda t, wall0: dict(schema=1, t=wall0 + t, producer_hint="demo_feed", sessions=ss,
                                 m=dict(level=m[0], thermal=m[1], mempress=m[2]), net=net, projects=projects or [])


def base(extra=()):
    return [S("SidePulse", 90011, "working"), S("Granite", 90012, "idle"), S("Waypoint", 90013, "idle"),
            S("scratch", 90014, "idle", managed=False)] + list(extra)


SCENARIOS = {
    "calm": ("4 sessions, all idle or light, no strain", scen([S("SidePulse", 90011, "idle"), S("Granite", 90012, "idle"),
             S("Waypoint", 90013, "idle"), S("ollama", 90014, "idle", managed=False)], projects=P(("Granite", 2)))),
    "busy": ("7 sessions all working hard, high rx/tx", scen([S(p, 90020 + i, "working", cpu=2.5 + i * .2, rx=8 + i, procs=6)
            for i, p in enumerate(PROJECTS[:6])] + [S("ollama", 90030, "working", False, cpu=3.4, rx=4)],
            m=(1, 0, 0), net=dict(strain=.35), projects=P(("Lodestar", 5), ("SidePulse", 3)))),
    "needs": ("one session needs you, others work/idle", scen(base([S("Lodestar", 90015, "needs")]), projects=P(("Lodestar", 4)))),
    "strain": ("machine strain: level 3, thermal 1, memory pressure 1", scen(base(), m=(3, 1, 1))),
    "vpn_down": ("VPN down, off site, API ok: AT RISK (beacon, no huddle)", scen(base(), net=dict(vpn="down", loss=1))),
    "lost": ("VPN down, off site, API unreachable: LOST (huddle and searchlight)",
             scen(base(), net=dict(vpn="down", loss=1, api=("failing", "network")))),
    "api_network": ("VPN up, on site, API unreachable: LOST", scen(base(), net=dict(on_site=True, api=("failing", "network")))),
    "api_ratelimit": ("VPN up, API rate-limited: link OK (the provider's problem)", scen(base(), net=dict(api=("failing", "rate_limit")))),
    "onsite_vpn_down": ("VPN down but on the on-site network, API ok: link OK", scen(base(), net=dict(vpn="down", on_site=True))),
    "link_unknown": ("no VPN and no API reading: no link cue", scen(base(), net=dict(vpn=None, api=None))),
    "bw_jam": ("bandwidth jam: strain .85, heavy rx/tx", scen([S("SidePulse", 90011, "working", rx=22, tx=6),
              S("ProjectDial", 90012, "working", rx=18, tx=4), S("Granite", 90013, "idle")], net=dict(strain=.85, loss=1))),
    "churn": ("8 sessions, mixed states (look for arrivals/leaves with --speed in the default demo)",
              scen([S(p, 90040 + i, ["working", "idle", "needs", "working"][i % 4]) for i, p in enumerate(PROJECTS)])),
    "lodestar_closed": ("no Lodestar session, Lodestar burning 6 (ghost)", scen(base(), projects=P(("Lodestar", 6), ("Granite", 2)))),
    "lodestar_closed_quiet": ("no Lodestar session, Lodestar burning 0 (ghost fading)", scen(base(), projects=P(("Lodestar", 0), ("Granite", 2)))),
    "ghosts": ("3 projects with burning and no session", scen(base(), projects=P(("ProjectCert", 5), ("ProjectDial", 9), ("Machinist", 2)))),
    "twin": ("SidePulse has two sessions and burning 7", scen(base([S("SidePulse", 90016, "working")]), projects=P(("SidePulse", 7)))),
    "unmanaged": ("only unmanaged sessions plus one managed", scen([S("ollama", 90011, "working", False), S("scratch", 90012, "idle", False),
                 S("Augur", 90013, "idle")])),
}


MACHINE = "mt-AAAAAA"
LEVELS = ["light", "medium", "full", "overload", "danger"]
NCPU = 10


def _stamp(obs, cad, **kw):
    return dict(observed_at=round(obs, 1), valid_until=round(obs + 2.5 * cad, 1), **kw)


def _key(name):
    return re.sub(r"[^a-z0-9._-]", "-", name.lower()).lstrip("-._") or "x"


def to_augur(d, seq, period, started_at, pid):
    """Convert the internal simulation dict to the augur.snapshot shape."""
    w = d["t"]
    cad = dict(fast=period, agents=max(period, 5), probes=max(period, 15), counts=60)
    m, net, ss = d["m"], d["net"], d["sessions"]
    cores = round(sum(s["cpu"] for s in ss), 2)
    busy = round(min(100.0, max(cores / NCPU * 100, m["level"] / 3 * 95)), 1)
    score = round(min(4.0, m["level"] / 0.75), 2)
    li = min(4, int(score))
    rx = round(sum(s.get("rx", 0) for s in ss) or net["mbps"] * .78, 2)
    tx = round(sum(s.get("tx", 0) for s in ss) or net["mbps"] * .22, 2)
    loss = 3.0 if net["loss"] else 0.0
    mach = dict(
        cpu=_stamp(w, cad["fast"], busy_pct=busy, cores_busy=round(busy * NCPU / 100, 2), ncpu=NCPU),
        memory=_stamp(w, cad["fast"], pressure=m["mempress"], available_pct=[45.2, 18.0, 6.0][m["mempress"]], swap_out_per_s=0.0),
        thermal=_stamp(w - 5, cad["agents"], state=m["thermal"], low_power=False),
        strain=_stamp(w, cad["fast"], level=LEVELS[li], score=score),
        net=_stamp(w, cad["fast"], rx_mbps=rx, tx_mbps=tx, link="wifi"),
        path=_stamp(w - 10, cad["probes"], level="bad" if loss else "ok", rtt_ms=14.3 if not loss else 90.0, loss_pct=loss),
    )
    if net.get("vpn"):
        mach["vpn"] = _stamp(w, cad["fast"], state=net["vpn"], on_site=bool(net["on_site"]))
    if net.get("api"):
        st, kind = net["api"]
        mach["api"] = _stamp(w - .5, cad["agents"], state=st, failing_sessions=1 if st == "failing" else 0,
                             **({"error_kind": kind, "last_error_at": round(w - 3, 1)} if st == "failing" else {"last_ok_at": round(w - 1, 1)}))
    if "strain" in net:
        mach["bandwidth"] = _stamp(w, cad["probes"], strain=net["strain"], basis="sendq", provisional=True)
    sess = []
    for s in ss:
        st = {"needs": "needs_you"}.get(s["state"], s["state"])
        if st == "idle" and s["pid"] % 3 == 0:
            st = "stopped"
        e = dict(id=s["id"], pid=s["pid"], started_at=s["started_at"], project=s["project"], project_key=_key(s["project"]),
                 managed=s["managed"],
                 attention=_stamp(w - .8, cad["agents"], state=st, since=s["since"]),
                 load=_stamp(w - 2.5, cad["agents"], cpu_cores=s["cpu"], mem_gb=s["mem"], procs=max(1, s["procs"])),
                 tasks=_stamp(w - 2.5, cad["agents"], total=max(0, s["procs"] - 1), background=max(0, s["procs"] - 1)))
        e["net"] = _stamp(w - 2.5, cad["agents"], rx_mbps=s["rx"], tx_mbps=s["tx"]) if "rx" in s else \
            _stamp(w - 2.5, cad["agents"], unknown="read_failed")
        sess.append(e)
    cnt = {p["name"]: p for p in d["projects"]}
    nsess, managed = {}, {}
    for s in ss:
        nsess[s["project"]] = nsess.get(s["project"], 0) + 1
        managed[s["project"]] = s["managed"]
    names = list(dict.fromkeys(["Lodestar"] + list(nsess) + list(cnt)))
    projects = []
    for n in names:
        if n != "Lodestar" and n in nsess and not managed[n]:
            projects.append(dict(key=_key(n), name=n, kind="unmanaged", sessions=nsess[n]))
            continue
        c = cnt.get(n, dict(burning=0, burning_red=0, burning_amber=0, burning_verify=0))
        h = zlib.crc32(n.encode())
        tk = 2 + h % 20
        counts = _stamp(w - 40, cad["counts"], burning=c["burning"], burning_red=c["burning_red"], burning_amber=c["burning_amber"],
                        burning_verify=c["burning_verify"], open=c["burning"] + tk + h % 5, waiting=h % 4,
                        basis="waiting=tickets-only", tickets_open=tk)
        projects.append(dict(key=_key(n), name=n, kind="lodestar" if n == "Lodestar" else "managed",
                             sessions=nsess.get(n, 0), counts=counts))
    return dict(schema="augur.snapshot", version="1.1",
                producer=dict(name="demo_feed", rev="demo", pid=pid, platform="darwin", machine=MACHINE, started_at=started_at),
                written_at=round(w, 1), valid_until=round(w + 3 * period + .5, 1), seq=seq, cadence_s=cad,
                machine=mach, sessions=sess, projects=projects)


SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "augur", "schema", "snapshot.schema.json")


def check(data):
    """Return a list of problems (empty = valid)."""
    schema = json.load(open(SCHEMA_PATH))
    try:
        import jsonschema
    except ImportError:
        jsonschema = None
    if jsonschema:
        sc = copy.deepcopy(schema)
        sc["properties"]["producer"]["properties"]["name"] = {"type": "string"}
        v = jsonschema.Draft202012Validator(sc)
        return [f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in v.iter_errors(data)]
    errs = [f"missing {k}" for k in schema["required"] if k not in data]
    errs += [f"producer missing {k}" for k in schema["properties"]["producer"]["required"] if k not in data.get("producer", {})]
    stamped = [(f"machine.{k}", v) for k, v in data.get("machine", {}).items()]
    for i, s in enumerate(data.get("sessions", [])):
        errs += [f"session {i} missing {k}" for k in schema["$defs"]["session"]["required"] if k not in s]
        if not re.fullmatch(r"[0-9]+@[0-9]+", str(s.get("id"))):
            errs.append(f"session {i} bad id")
        stamped += [(f"session {i}.{k}", s[k]) for k in ("attention", "load", "tasks", "net") if k in s]
    for i, p in enumerate(data.get("projects", [])):
        errs += [f"project {i} missing {k}" for k in schema["$defs"]["project"]["required"] if k not in p]
        if "counts" in p:
            stamped.append((f"project {i}.counts", p["counts"]))
    errs += [f"{n} missing observed_at/valid_until" for n, b in stamped if "observed_at" not in b or "valid_until" not in b]
    return errs


def snapshot(a, t, wall0, seq=0, started_at=None):
    d = SCENARIOS[a.scenario][1](t, wall0) if a.scenario else state_at(t, a.seed, wall0)
    return to_augur(d, seq, a.period, wall0 if started_at is None else started_at, 90000 if a.at is not None else os.getpid())


def write(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".snap.")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.environ.get("SPRITES_STATE") or "~/ClaudeWork/sprites/live/demo_snapshot.json")
    ap.add_argument("--period", type=float, default=2)
    ap.add_argument("--seed", type=int, default=20261031)
    ap.add_argument("--duration", type=float)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--at", type=float)
    ap.add_argument("--speed", type=float, default=1)
    ap.add_argument("--scenario", choices=sorted(SCENARIOS))
    ap.add_argument("--list-scenarios", action="store_true")
    ap.add_argument("--print", dest="pr", action="store_true")
    ap.add_argument("--check", action="store_true", help="validate each snapshot against the schema; exit 1 on failure")
    a = ap.parse_args()
    if a.list_scenarios:
        for k, (d, _) in SCENARIOS.items():
            print(f"{k:22s} {d}")
        return
    out = os.path.expanduser(a.out)
    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, lambda *_: sys.exit(0))
    start, seq = time.time(), 0
    while True:
        if a.at is not None:
            data = snapshot(a, a.at, EPOCH0, int(a.at / a.period))
        else:
            simt = (time.time() - start) * a.speed
            data = snapshot(a, simt, time.time() - simt, seq, start)
            seq += 1
        if a.check:
            errs = check(data)
            if errs:
                print("CHECK FAILED:\n  " + "\n  ".join(errs), file=sys.stderr)
                sys.exit(1)
            print("check ok", file=sys.stderr)
        if a.pr:
            print(json.dumps(data))
        else:
            write(out, data)
        if a.once or a.at is not None or (a.duration and time.time() - start >= a.duration):
            return
        time.sleep(a.period)


if __name__ == "__main__":
    main()
