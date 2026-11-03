"""Machine-wide collectors (DESIGN.md sections 2-3): cpu, memory, net (+vpn), thermal, power,
strain and path. Stdlib only, no spawns. Every reader is injectable (all_collectors(readers=...))
so tests replay recorded tuples and dicts.

Shared keys written: cpu_busy_pct, mem_pressure_raw, mem_avail_pct, low_power, on_battery,
audit.iface_rx_bytes / iface_tx_bytes / iface_ticks. Read: agent_wait_s_per_s (sessions),
cpu_busy_pct / mem_* (strain's fallbacks).

The load ladder (LEVELS .. reason) is vendored verbatim from Lodestar load_levels.py; its state
lives in this collector's private ctx.state, never in Lodestar's levels-state.json.
"""

import json
import math
import os
import threading
import time

from augur.collectors.base import Collector
from augur.darwin import native

# load_levels.json @3f98c64b (identical at 098ae26c), minus bg_delay: Augur runs no compiled
# background probe in pilot 1, so background_level is never produced.
PARAMS = {
    "probe": {
        "burst_ms": 20.0,
        "burst_qos": "utility",
        "delay_window": 5,
        "gap_reset_s": 150.0,
        "corroborate_busy_pct": 90.0,
        "corroborate_agent_wait_s_per_s": 1.0
    },
    "cpu_busy": {
        "tau_s": 10.0,
        "enter": {
            "medium": 40.0,
            "full": 85.0,
            "overload": 97.0
        },
        "hysteresis": 5.0,
        "dwell_up_s": {
            "medium": 10,
            "full": 20,
            "overload": 60
        },
        "dwell_down_s": 30
    },
    "sched_delay": {
        "enter_x": {
            "medium": 1.5,
            "full": 2.5,
            "overload": 4.0,
            "danger": 8.0
        },
        "hysteresis_frac": 0.25,
        "needs_corroboration": [
            "overload",
            "danger"
        ],
        "dwell_up_s": {
            "medium": 5,
            "full": 5,
            "overload": 10,
            "danger": 10
        },
        "dwell_down_s": 10
    },
    "memory": {
        "avail_enter_pct": {
            "medium": 40.0,
            "full": 25.0,
            "overload": 12.0,
            "danger": 4.0
        },
        "hysteresis": 3.0,
        "pressure_overload": 2,
        "pressure_danger": 4,
        "dwell_up_s": {
            "medium": 30,
            "full": 30,
            "overload": 15,
            "danger": 5
        },
        "dwell_down_s": 60
    }
}

WALL_STEP_S = 10.0   # RB-m5: a wall step / sleep between two strain probes, beyond this
REV = "augur"   # update() stamps writer.rev; Augur drops the writer block


def load_params(path=None):
    """update()'s fallback when no params are passed; Augur always passes PARAMS."""
    return json.loads(json.dumps(PARAMS))


# from Lodestar bin/lib/load_levels.py@3f98c64b LEVELS
LEVELS = ["light", "medium", "full", "overload", "danger"]

# from Lodestar bin/lib/load_levels.py@3f98c64b RANK
RANK = {n: i for i, n in enumerate(LEVELS)}

# from Lodestar bin/lib/load_levels.py@3f98c64b worst
def worst(*names):
    names = [n for n in names if n in RANK]
    return max(names, key=RANK.get) if names else None

# from Lodestar bin/lib/load_levels.py@3f98c64b _ladder
def _ladder(st, key, value, enter, exit_of, dwell_up, dwell_down, now, qualifies=None):
    """Advance one signal's level. `value` higher = worse. `enter[L]` is the entry threshold for
    each level above light; `exit_of(L)` the lower threshold to leave L. A level is entered once
    the value has qualified for it continuously for dwell_up[L] s; left once it has stayed below
    the exit for dwell_down s (then drops to the level the value qualifies for)."""
    s = st.setdefault(key, {"level": "light", "since": now, "above": {}, "below": None})
    cur = s["level"]
    if value is None:
        return cur
    above = s["above"]
    for lvl in LEVELS[1:]:
        ok = lvl in enter and value >= enter[lvl] and (qualifies is None or qualifies(lvl))
        if ok:
            above.setdefault(lvl, now)
        else:
            above.pop(lvl, None)
    target = cur
    for lvl in reversed(LEVELS[1:]):
        if RANK[lvl] > RANK[cur] and lvl in above and now - above[lvl] >= dwell_up.get(lvl, 0):
            target = lvl
            break
    if target == cur and cur != "light":
        if value < exit_of(cur) or (qualifies is not None and not qualifies(cur)):
            if s["below"] is None:
                s["below"] = now
            if now - s["below"] >= dwell_down:
                target = max([l for l in LEVELS if l == "light" or (l in enter and value >= enter[l]
                              and (qualifies is None or qualifies(l)))] + ["light"], key=RANK.get)
                target = min(target, LEVELS[RANK[cur] - 1], key=RANK.get)
        else:
            s["below"] = None
    if target != cur:
        s.update(level=target, since=now, below=None)
    return target

# from Lodestar bin/lib/load_levels.py@3f98c64b new_state
def new_state():
    return {"cpu_ewma": None, "last_t": None, "ticks": None, "delays": [], "bg_delays": [], "levels": {}}

# from Lodestar bin/lib/load_levels.py@3f98c64b update
def update(state, reading, now=None, params=None):
    """Fold one reading into `state` (mutated) and return the public dict. Pure apart from the
    state argument: tests inject readings."""
    P = params or load_params()
    now = reading.get("t", time.time()) if now is None else now
    if state.get("last_t") is not None and now - state["last_t"] > P["probe"]["gap_reset_s"]:
        # sleep/wake or a stalled caller: forget pending evidence and the smoothing.
        state["cpu_ewma"], state["delays"], state["bg_delays"] = None, [], []
        for s in state["levels"].values():
            s["above"], s["below"] = {}, None
    dt = now - state["last_t"] if state.get("last_t") is not None else None
    state["last_t"] = now
    lv = state["levels"]

    c = P["cpu_busy"]
    busy = reading.get("busy_pct")
    if busy is not None:
        if state["cpu_ewma"] is None or dt is None:
            state["cpu_ewma"] = busy
        else:
            state["cpu_ewma"] += (1 - math.exp(-max(dt, 0) / c["tau_s"])) * (busy - state["cpu_ewma"])
    cpu = _ladder(lv, "cpu", state["cpu_ewma"], c["enter"], lambda l: c["enter"][l] - c["hysteresis"],
                  c["dwell_up_s"], c["dwell_down_s"], now)

    d = P["sched_delay"]
    st = reading.get("stretch")
    if st is not None:
        state["delays"] = (state["delays"] + [st])[-P["probe"]["delay_window"]:]
    delay_v = sorted(state["delays"])[len(state["delays"]) // 2] if state["delays"] else None
    wait = reading.get("agent_wait")
    corroborated = bool((busy is not None and busy >= P["probe"]["corroborate_busy_pct"])
                        or (wait is not None and wait >= P["probe"]["corroborate_agent_wait_s_per_s"]))
    delay = _ladder(lv, "delay", delay_v, d["enter_x"], lambda l: d["enter_x"][l] * (1 - d["hysteresis_frac"]),
                    d["dwell_up_s"], d["dwell_down_s"], now,
                    qualifies=lambda l: corroborated or l not in d["needs_corroboration"])

    m = P["memory"]
    avail = reading.get("mem_avail_pct")
    used_like = None if avail is None else 100.0 - avail
    enter_m = {k: 100.0 - v for k, v in m["avail_enter_pct"].items()}
    mem = _ladder(lv, "memory", used_like, enter_m, lambda l: enter_m[l] - m["hysteresis"],
                  m["dwell_up_s"], m["dwell_down_s"], now)
    pr = reading.get("pressure")
    if pr is not None and pr >= m["pressure_danger"]:
        mem = worst(mem, "danger")
    elif pr is not None and pr >= m["pressure_overload"]:
        mem = worst(mem, "overload")

    b = P.get("bg_delay")
    bg, bg_v = None, None
    if b:
        bx = reading.get("bg_stretch")
        rows = [r for r in state.get("bg_delays") or [] if now - r[0] <= b["max_age_s"]]
        if bx is not None:
            rows = (rows + [[now, bx]])[-b["window"]:]
        state["bg_delays"] = rows
        if rows:
            xs = sorted(r[1] for r in rows)
            bg_v = xs[len(xs) // 2]
            bg = _ladder(lv, "background", bg_v, b["enter_x"],
                         lambda l: b["enter_x"][l] * (1 - b["hysteresis_frac"]),
                         b["dwell_up_s"], b["dwell_down_s"], now)
        else:
            lv.pop("background", None)      # no fresh probe result: unknown, never a held level

    overall = worst(cpu, delay)
    since = {k: lv[k]["since"] for k in ("cpu", "delay", "memory", "background") if k in lv}
    since["overall"] = max(since[k] for k in ("cpu", "delay")
                           if k in since and lv[k]["level"] == overall) if overall else now
    readings = {"cpu_busy_pct": _r(state["cpu_ewma"]), "cpu_busy_raw_pct": _r(busy),
                "sched_delay_x": _r(delay_v, 1), "agent_wait_s_per_s": _r(wait, 2),
                "corroborated": corroborated,
                "agents_tracked": reading.get("agents_tracked"), "agents_matched": reading.get("agents_matched"),
                "bg_delay_x": _r(bg_v, 1), "bg_samples": len(state.get("bg_delays") or []),
                "mem_pressure": pr, "mem_avail_pct": _r(avail)}
    return {"cpu_level": cpu, "delay_level": delay, "memory_level": mem, "overall": overall,
            "background_level": bg,
            "readings": readings, "since": since, "at": now, "reason": reason(cpu, delay, mem, readings),
            "writer": {"pid": os.getpid(), "rev": REV}}

# from Lodestar bin/lib/load_levels.py@3f98c64b _r
def _r(v, nd=1):
    return None if v is None else round(v, nd)

# from Lodestar bin/lib/load_levels.py@3f98c64b reason
def reason(cpu, delay, mem, rd):
    """Plain words for a tile: 'CPU 86% busy, scheduling delay 3x normal'."""
    parts = []
    if rd.get("cpu_busy_pct") is not None:
        parts.append("CPU %d%% busy" % round(rd["cpu_busy_pct"]))
    x = rd.get("sched_delay_x")
    if x is not None:
        parts.append("scheduling delay normal" if x < 1.5 else "scheduling delay %.0fx normal" % x)
    return ", ".join(parts) or "not measured"


# ================================================================== Augur's own (not vendored)

def _rnd(v, nd):
    return None if v is None else round(float(v), nd)


def _default_readers():
    return {
        "cpu_ticks": native.cpu_ticks,
        "ncpu": os.cpu_count,
        "vm_counters": native.vm_counters,
        "mem_pressure": native.mem_pressure_level,
        "if_counters": native.if_counters,
        "default_routes": native.default_routes,
        "link_types": native.link_types,
        "ssid": lambda path, now: native.ssid_from_file(path, now=now),
        "probe_ssid": lambda: (os.environ.get("LODESTAR_NETWATCH_PROBE_SSID") or "").strip()
        or native.DEFAULT_PROBE_SSID,
        "thermal": native.thermal_state,
        "low_power": native.low_power_mode,
        "power": native.power_source,
        "burst": lambda: native.burst_stretch(PARAMS["probe"]["burst_ms"], PARAMS["probe"]["burst_qos"]),
        "ping_burst": native.ping_burst,
        "anchor": native.path_anchor,
        "set_qos": native.set_thread_qos,
        "clock": time.monotonic,
        "path_sync": False,       # tests: run the echo burst inline instead of on a thread
    }


def _tick_busy(prev, cur):
    """(busy_pct or None, reason or None) from two cumulative (user, system, idle, nice) tuples."""
    if prev is None:
        return None, "warming_up"
    d = [cur[i] - prev[i] for i in range(4)]
    if any(x < 0 for x in d):
        return None, "counter_reset"
    tot = sum(d)
    if tot <= 0:
        return None, "warming_up"
    return 100.0 * (tot - d[2]) / tot, None


class _Base(Collector):
    def __init__(self, readers=None):
        self.r = _default_readers()
        self.r.update(readers or {})


class CpuCollector(_Base):
    name, tier, signals = "cpu", "fast", ("machine.cpu",)

    def collect(self, ctx):
        t = self.r["cpu_ticks"]()
        if t is None:
            ctx.shared["cpu_busy_pct"] = None
            return {"machine.cpu": {"unknown": "read_failed"}}
        busy, why = _tick_busy(ctx.state.get("ticks"), t)
        ctx.state["ticks"] = tuple(t)
        ctx.shared["cpu_busy_pct"] = busy
        if why:
            return {"machine.cpu": {"unknown": why}}
        n = self.r["ncpu"]() or None
        return {"machine.cpu": {"busy_pct": _rnd(busy, 1), "ncpu": n,
                                "cores_busy": _rnd(busy * n / 100.0, 2) if n else None}}


PRESSURE = {1: 0, 2: 1, 4: 2}


class MemoryCollector(_Base):
    name, tier, signals = "memory", "fast", ("machine.memory",)

    def collect(self, ctx):
        vm = self.r["vm_counters"]()
        raw = self.r["mem_pressure"]()
        avail = vm.get("avail_pct") if vm else None
        ctx.shared["mem_pressure_raw"], ctx.shared["mem_avail_pct"] = raw, avail
        if vm is None and raw is None:
            return {"machine.memory": {"unknown": "read_failed"}}
        out = {"pressure": PRESSURE.get(raw), "available_pct": _rnd(avail, 1)}
        prev = ctx.state.get("swap")
        if vm is not None:
            if prev is not None and ctx.mono > prev[1] and vm["swapouts"] >= prev[0]:
                out["swap_out_per_s"] = _rnd((vm["swapouts"] - prev[0]) / (ctx.mono - prev[1]), 2)
            ctx.state["swap"] = (vm["swapouts"], ctx.mono)
        return {"machine.memory": out}


LINK_WORDS = {"IEEE80211": "wifi", "Ethernet": "ethernet"}


class NetCollector(_Base):
    """machine.net on the physical default-route interface and machine.vpn (a tunnel holds the
    primary default route). The SSID is read only to compute on_site and never leaves here."""
    name, tier, signals = "net", "fast", ("machine.net", "machine.vpn")

    def collect(self, ctx):
        st = ctx.state
        c = self.r["if_counters"]() or {}
        routes = self.r["default_routes"]() or []
        out = {"machine.vpn": self._vpn(ctx, routes)}
        if not c:
            st["prev"] = None
            out["machine.net"] = {"unknown": "read_failed"}
            return out
        phys = native.physical_for(c, routes) if routes else None
        if phys is None:
            st["prev"] = None
            out["machine.net"] = {"link": "none"}
            return out
        cur = (phys, c[phys]["ibytes"], c[phys]["obytes"], ctx.mono)
        prev, st["prev"] = st.get("prev"), cur
        if prev is None:
            out["machine.net"] = {"unknown": "warming_up"}
            return out
        dib, dob = native._d(cur[1], prev[1]), native._d(cur[2], prev[2])
        dt = cur[3] - prev[3]
        if prev[0] != phys or dib is None or dob is None:
            out["machine.net"] = {"unknown": "counter_reset"}
            return out
        if dt <= 0:
            out["machine.net"] = {"unknown": "warming_up"}
            return out
        a = ctx.shared.setdefault("audit", {})
        a["iface_rx_bytes"] = a.get("iface_rx_bytes", 0) + dib
        a["iface_tx_bytes"] = a.get("iface_tx_bytes", 0) + dob
        a["iface_ticks"] = a.get("iface_ticks", 0) + 1
        link = LINK_WORDS.get((self.r["link_types"]() or {}).get(phys), "other")
        out["machine.net"] = {"rx_mbps": _rnd(dib * 8 / dt / 1e6, 3), "tx_mbps": _rnd(dob * 8 / dt / 1e6, 3),
                              "link": link}
        return out

    def _vpn(self, ctx, routes):
        st = ctx.state
        primary = routes[0][0] if routes else None
        state = "up" if primary and native.is_tunnel(primary) else "down"
        if st.get("vpn") is not None and st["vpn"] != state:
            st["vpn_changed_at"] = ctx.now
        st["vpn"] = state
        v = {"state": state, "changed_at": st.get("vpn_changed_at")}
        ssid = self.r["ssid"](os.path.join(ctx.home, "dev", ".lodestar", "companion", "ssid.json"), ctx.now)
        if ssid is not None:
            v["on_site"] = ssid == self.r["probe_ssid"]()
        return v


class ThermalCollector(_Base):
    name, tier, signals, lpm_exempt = "thermal", "probes", ("machine.thermal",), True

    def collect(self, ctx):
        s, lp = self.r["thermal"](), self.r["low_power"]()
        ctx.shared["low_power"] = lp
        if s is None and lp is None:
            return {"machine.thermal": {"unknown": "read_failed"}}
        return {"machine.thermal": {"state": None if s is None else max(0, min(3, int(s))), "low_power": lp}}


class PowerCollector(_Base):
    name, tier, signals, lpm_exempt = "power", "probes", ("machine.power",), True

    def collect(self, ctx):
        p = self.r["power"]()
        if p is None:
            ctx.shared["on_battery"] = None
            return {"machine.power": {"unknown": "read_failed"}}
        if not p.get("present"):
            ctx.shared["on_battery"] = None
            return {}                          # no battery on this machine: the signal is absent
        ctx.shared["on_battery"] = p.get("on_battery")
        if p.get("on_battery") is None:
            return {"machine.power": {"unknown": "read_failed"}}   # never "on AC" by default
        return {"machine.power": {"on_battery": p.get("on_battery"), "battery_pct": _rnd(p.get("battery_pct"), 1)}}


def strain_score(level, cpu_level, delay_level, cpu_v, delay_v, params=PARAMS):
    """RANK[level] + the fraction of the way the input that set `level` has travelled from that
    level's entry threshold toward the next level's, clamped to [RANK, RANK + 0.999]; 4.0 at
    danger. Floors below the first threshold: cpu 0 %, delay 1.0x (served at once). cpu has no
    danger threshold, so its overload band runs to 100 %."""
    if level is None:
        return None
    r = RANK[level]
    if level == "danger":
        return 4.0
    c, d = params["cpu_busy"]["enter"], params["sched_delay"]["enter_x"]
    lv = LEVELS
    bands = []
    if cpu_level == level and cpu_v is not None:
        lo = 0.0 if level == "light" else c[level]
        hi = c.get(lv[r + 1], 100.0)
        bands.append((cpu_v, lo, hi))
    if delay_level == level and delay_v is not None:
        lo = 1.0 if level == "light" else d[level]
        bands.append((delay_v, lo, d[lv[r + 1]]))
    f = 0.0
    for v, lo, hi in bands:
        if hi > lo:
            f = max(f, (v - lo) / (hi - lo))
    return round(r + max(0.0, min(0.999, f)), 3)


def _other_threads_cpu(fn):
    """(fn(), CPU burnt by threads other than the caller while fn ran): process CPU delta minus
    the calling thread's own delta. The burst runs on a fresh thread the core cannot see."""
    import resource
    r0, t0 = resource.getrusage(resource.RUSAGE_SELF), time.thread_time()
    out = fn()
    r1, t1 = resource.getrusage(resource.RUSAGE_SELF), time.thread_time()
    proc = (r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime)
    return out, max(0.0, proc - (t1 - t0))


class StrainCollector(_Base):
    name, tier, signals = "strain", "probes", ("machine.strain",)
    _worker_cpu = 0.0

    def drain_worker_cpu(self):
        """Worker-thread CPU since the last call, for the core's per-line meter."""
        v, self._worker_cpu = self._worker_cpu, 0.0
        return v

    def collect(self, ctx):
        st = ctx.state
        ll = st.setdefault("ladder", new_state())
        stretch, wcpu = _other_threads_cpu(self.r["burst"])
        self._worker_cpu += wcpu
        t = self.r["cpu_ticks"]()
        busy, _why = _tick_busy(st.get("ticks"), t) if t is not None else (None, None)
        if t is not None:
            st["ticks"] = tuple(t)
        if busy is None:
            busy = ctx.shared.get("cpu_busy_pct")
        wait = ctx.shared.get("agent_wait_s_per_s")
        reading = {"t": ctx.mono, "busy_pct": busy, "stretch": stretch, "agent_wait": wait,
                   "pressure": ctx.shared.get("mem_pressure_raw"), "mem_avail_pct": ctx.shared.get("mem_avail_pct")}
        # RB-m5: the ladder's dwell runs on ctx.mono, so a wall-clock step cannot freeze it. A
        # wall step or a sleep (|d wall - d mono| > WALL_STEP_S; mono stops in sleep) resets the
        # pending evidence, as update()'s own gap_reset_s did for forward wall jumps.
        prev = st.get("clk")
        st["clk"] = (ctx.now, ctx.mono)
        if prev is not None and abs((ctx.now - prev[0]) - (ctx.mono - prev[1])) > WALL_STEP_S:
            ll["cpu_ewma"], ll["delays"], ll["bg_delays"] = None, [], []
            for s in ll["levels"].values():
                s["above"], s["below"] = {}, None
        out = update(ll, reading, now=ctx.mono, params=PARAMS)
        delays = ll["delays"]
        delay_v = sorted(delays)[len(delays) // 2] if delays else None
        if ll["cpu_ewma"] is None and delay_v is None:
            return {"machine.strain": {"unknown": "read_failed"}}
        lvl = out["overall"]
        return {"machine.strain": {
            "level": lvl, "cpu_level": out["cpu_level"], "delay_level": out["delay_level"],
            "memory_level": out["memory_level"],
            "score": strain_score(lvl, out["cpu_level"], out["delay_level"], ll["cpu_ewma"], delay_v),
            "sched_delay_x": _rnd(delay_v, 2), "agent_wait_s_per_s": _rnd(wait, 3),
            "provisional": True}}


class _PathWindow(object):
    """netwatch.Net's rolling echo window and its verdict, with the thresholds it uses."""
    PATH_EVERY_S = 10.0
    PATH_BURST = 4
    PATH_WINDOW = 12
    PATH_MIN_SAMPLES = 4
    PATH_MAX_AGE_S = 90.0
    PATH_BAD_MS, PATH_BAD_LOSS = 300.0, 5.0
    PATH_DEGRADED_MS, PATH_DEGRADED_LOSS = 150.0, 2.0

    def __init__(self):
        self.path = []

    # from Lodestar bin/lib/netwatch.py@51517eaa Net.path_state
    def path_state(self, now):
        """(level, why, median_ms, loss_pct, samples) from the rolling window; level is
        ok|degraded|bad|unknown. A stale window (sleep, probe dead) is dropped, not trusted."""
        w = self.path
        if w and now - w[-1][0] > self.PATH_MAX_AGE_S:
            self.path = w = []
        n = len(w)
        if n < self.PATH_MIN_SAMPLES:
            return "unknown", "path: %d echo%s so far" % (n, "" if n == 1 else "es"), None, None, n
        ok = sorted(ms for _t, ms in w if ms is not None)
        lost = n - len(ok)
        loss = round(100.0 * lost / n, 1)
        if not ok:
            return "bad", "no echo of %d answered" % n, None, 100.0, n
        m = len(ok)
        med = round(ok[m // 2] if m % 2 else (ok[m // 2 - 1] + ok[m // 2]) / 2.0, 1)
        # one lost echo in a window is not evidence of loss
        loss_ev = loss if lost >= 2 else 0.0
        if med >= self.PATH_BAD_MS or loss_ev >= self.PATH_BAD_LOSS:
            lv = "bad"
        elif med >= self.PATH_DEGRADED_MS or loss_ev >= self.PATH_DEGRADED_LOSS:
            lv = "degraded"
        else:
            lv = "ok"
        return lv, "median %.0f ms, %.0f%% loss over %d echoes" % (med, loss, n), med, loss, n

class PathCollector(_Base):
    """Unprivileged ICMP burst (4 echoes, 0.25 s apart) to the anchor, bound to the physical
    interface, on a daemon worker thread at UTILITY QoS: collect() only starts a burst and reads
    the window, it never waits on the network. The anchor address is never output."""
    name, tier, signals = "path", "probes", ("machine.path",)

    def __init__(self, readers=None):
        _Base.__init__(self, readers)
        self.w = _PathWindow()
        self.iface = None
        self.started = -1e9
        self.thread = None
        self.lock = threading.Lock()
        self._worker_cpu = 0.0

    def drain_worker_cpu(self):
        with self.lock:
            v, self._worker_cpu = self._worker_cpu, 0.0
        return v

    def collect(self, ctx):
        clock = self.r["clock"]
        c = self.r["if_counters"]() or {}
        routes = self.r["default_routes"]() or []
        phys = native.physical_for(c, routes) if routes and c else None
        with self.lock:
            if phys != self.iface:
                self.w.path, self.iface = [], phys
        if phys is None:
            return {"machine.path": {"unknown": "read_failed"}}
        self._start(clock(), phys)
        with self.lock:
            lv, _why, med, loss, _n = self.w.path_state(clock())
        if lv == "unknown":
            return {"machine.path": {"unknown": "warming_up"}}
        return {"machine.path": {"level": lv, "rtt_ms": _rnd(med, 1), "loss_pct": _rnd(loss, 1)}}

    def _start(self, now, phys):
        if now - self.started < self.w.PATH_EVERY_S:
            return
        if self.thread is not None and self.thread.is_alive():
            return
        self.started = now
        anchor = self.r["anchor"]()

        def work():
            t0 = time.thread_time()
            try:
                _work()
            finally:
                if not self.r["path_sync"]:      # inline (tests): the caller's thread_time has it
                    with self.lock:
                        self._worker_cpu += time.thread_time() - t0

        def _work():
            if not self.r["path_sync"]:
                try:
                    self.r["set_qos"]("utility")
                except Exception:  # noqa: BLE001 - QoS is best effort
                    pass
            try:
                res = self.r["ping_burst"](anchor, phys, count=self.w.PATH_BURST, gap=0.25)
            except Exception:  # noqa: BLE001 - a broken probe is no samples, never a crash
                return
            t = self.r["clock"]()
            with self.lock:
                if phys != self.iface:
                    return
                self.w.path = (self.w.path + [(t, r) for r in res])[-self.w.PATH_WINDOW:]
        if self.r["path_sync"]:
            work()
        else:
            self.thread = threading.Thread(target=work, name="augur-path", daemon=True)
            self.thread.start()


def all_collectors(readers=None):
    """Fresh instances of every machine collector, sharing one readers override dict."""
    return [CpuCollector(readers), MemoryCollector(readers), NetCollector(readers),
            ThermalCollector(readers), PowerCollector(readers), StrainCollector(readers),
            PathCollector(readers)]
