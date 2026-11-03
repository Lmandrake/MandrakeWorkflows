"""Machine collectors driven by injected fake readers: no live syscalls."""
import types

from augur.collectors import machine as M

ETHER, UPRUN = 0x06, 0x1 | 0x40


def ctx(now=1000.0, mono=None, shared=None, home="/nonexistent"):
    return types.SimpleNamespace(now=now, mono=now if mono is None else mono, state={},
                                 shared={} if shared is None else shared, home=home,
                                 cadence={"fast": 2, "probes": 15})


def step(c, x, now):
    x.now = x.mono = now
    return c.collect(x)


def iface(ib, ob, typ=ETHER):
    return {"type": typ, "flags": UPRUN, "ibytes": ib, "obytes": ob}


def netc(seq_counters, seq_routes, ssid=None, links=None):
    it_c, it_r = iter(seq_counters), iter(seq_routes)
    return M.NetCollector({"if_counters": lambda: next(it_c), "default_routes": lambda: next(it_r),
                           "link_types": lambda: links or {"en0": "IEEE80211"},
                           "ssid": lambda path, now: ssid, "probe_ssid": lambda: "OnSiteWifi"})


# ---------------------------------------------------------------- cpu

def test_cpu_warming_then_value_then_reset():
    ticks = iter([(100, 50, 850, 0), (200, 100, 1700, 0), (10, 10, 10, 0)])
    c = M.CpuCollector({"cpu_ticks": lambda: next(ticks), "ncpu": lambda: 10})
    x = ctx()
    assert step(c, x, 1000)["machine.cpu"] == {"unknown": "warming_up"}
    v = step(c, x, 1002)["machine.cpu"]
    assert v == {"busy_pct": 15.0, "ncpu": 10, "cores_busy": 1.5}
    assert x.shared["cpu_busy_pct"] == 15.0
    assert step(c, x, 1004)["machine.cpu"] == {"unknown": "counter_reset"}


def test_cpu_read_failed():
    c = M.CpuCollector({"cpu_ticks": lambda: None})
    assert c.collect(ctx())["machine.cpu"] == {"unknown": "read_failed"}


# ---------------------------------------------------------------- memory

def test_memory_pressure_map_and_swap_rate():
    vms = iter([{"swapouts": 100, "avail_pct": 50.04}, {"swapouts": 110, "avail_pct": 49.0}])
    c = M.MemoryCollector({"vm_counters": lambda: next(vms), "mem_pressure": lambda: 2})
    x = ctx()
    first = step(c, x, 1000)["machine.memory"]
    assert first == {"pressure": 1, "available_pct": 50.0}            # no swap key on first tick
    assert step(c, x, 1002)["machine.memory"]["swap_out_per_s"] == 5.0
    assert x.shared["mem_pressure_raw"] == 2 and x.shared["mem_avail_pct"] == 49.0
    assert M.PRESSURE == {1: 0, 2: 1, 4: 2}


# ---------------------------------------------------------------- net / vpn

def test_net_warming_rates_and_audit():
    cs = [{"en0": iface(0, 0)}, {"en0": iface(1_000_000, 250_000)}]
    rs = [[("en0", "10.0.0.1", 0x3)]] * 2
    c, x = netc(cs, rs), ctx()
    assert step(c, x, 1000)["machine.net"] == {"unknown": "warming_up"}
    n = step(c, x, 1002)["machine.net"]
    assert n == {"rx_mbps": 4.0, "tx_mbps": 1.0, "link": "wifi"}
    assert x.shared["audit"] == {"iface_rx_bytes": 1_000_000, "iface_tx_bytes": 250_000, "iface_ticks": 1}


def test_net_counter_reset_and_iface_change():
    cs = [{"en0": iface(5000, 5000)}, {"en0": iface(10, 10)}, {"en0": iface(20, 20), "en7": iface(9, 9)},
          {"en0": iface(30, 30), "en7": iface(19, 19)}]
    rs = [[("en0", "g", 3)], [("en0", "g", 3)], [("en7", "g", 3)], [("en7", "g", 3)]]
    c, x = netc(cs, rs, links={"en7": "Ethernet"}), ctx()
    step(c, x, 1000)
    assert step(c, x, 1002)["machine.net"] == {"unknown": "counter_reset"}
    assert step(c, x, 1004)["machine.net"] == {"unknown": "counter_reset"}   # interface changed
    n = step(c, x, 1006)["machine.net"]
    assert n["link"] == "ethernet" and n["rx_mbps"] == 0.0
    assert x.shared["audit"]["iface_ticks"] == 1


def test_net_no_physical_route():
    cs = [{"lo0": {"type": 0x18, "flags": UPRUN, "ibytes": 1, "obytes": 1}}]
    c, x = netc(cs, [[]]), ctx()
    out = step(c, x, 1000)
    assert out["machine.net"] == {"link": "none"}
    assert out["machine.vpn"]["state"] == "down"
    assert "audit" not in x.shared


def test_vpn_flap_moves_changed_at():
    up = [("utun4", "10.1.1.1", 3), ("en0", "192.168.1.1", 0x1000003)]
    down = [("en0", "192.168.1.1", 3)]
    cs = [{"en0": iface(i, i), "utun4": iface(i, i, 0x18)} for i in range(5)]
    c, x = netc(cs, [up, up, down, down, up]), ctx()
    v = [step(c, x, 1000 + 2 * i)["machine.vpn"] for i in range(5)]
    assert [e["state"] for e in v] == ["up", "up", "down", "down", "up"]
    assert v[0]["changed_at"] is None and v[1]["changed_at"] is None
    assert v[2]["changed_at"] == 1004 and v[3]["changed_at"] == 1004 and v[4]["changed_at"] == 1008
    assert all("on_site" not in e for e in v)                       # no ssid: key absent


def test_on_site_boolean_only():
    for ssid, want in (("OnSiteWifi", True), ("Home", False)):
        c = netc([{"en0": iface(0, 0)}], [[("en0", "g", 3)]], ssid=ssid)
        v = c.collect(ctx())["machine.vpn"]
        assert v["on_site"] is want and ssid not in repr(v)


def test_ssid_file_freshness(tmp_path):
    import json
    from augur.darwin import native
    p = tmp_path / "ssid.json"
    p.write_text(json.dumps({"at": 1000.0, "authorized": True, "ssid": "OnSiteWifi"}))
    assert native.ssid_from_file(str(p), now=1100.0) == "OnSiteWifi"
    assert native.ssid_from_file(str(p), now=1121.0) is None
    p.write_text(json.dumps({"at": 1000.0, "authorized": False, "ssid": "OnSiteWifi"}))
    assert native.ssid_from_file(str(p), now=1001.0) is None


# ---------------------------------------------------------------- thermal / power

def test_thermal_clamp_and_low_power_shared():
    c = M.ThermalCollector({"thermal": lambda: 4, "low_power": lambda: True})
    x = ctx()
    assert c.collect(x)["machine.thermal"] == {"state": 3, "low_power": True}
    assert x.shared["low_power"] is True and c.lpm_exempt


def test_power_absent_without_battery():
    x = ctx()
    assert M.PowerCollector({"power": lambda: {"present": False}}).collect(x) == {}
    assert x.shared["on_battery"] is None
    out = M.PowerCollector({"power": lambda: {"present": True, "on_battery": True, "battery_pct": 87.25}}).collect(x)
    assert out == {"machine.power": {"on_battery": True, "battery_pct": 87.2}} and x.shared["on_battery"] is True
    assert M.PowerCollector({"power": lambda: None}).collect(x)["machine.power"] == {"unknown": "read_failed"}


# ---------------------------------------------------------------- strain

def strain_run(busy_pct, stretch, n=12, wait=None):
    """n probes 15 s apart at a constant busy fraction (fake ticks) and stretch."""
    state = {"t": [0, 0, 0, 0]}

    def ticks():
        b = int(busy_pct * 10)
        state["t"] = [state["t"][0] + b, state["t"][1], state["t"][2] + 1000 - b, 0]
        return tuple(state["t"])
    c = M.StrainCollector({"cpu_ticks": ticks, "burst": lambda: stretch})
    x = ctx(shared={"agent_wait_s_per_s": wait, "mem_pressure_raw": 1, "mem_avail_pct": 60.0})
    outs = [step(c, x, 1000 + 15 * i)["machine.strain"] for i in range(n)]
    return outs


def test_strain_levels_and_score_monotone():
    light = strain_run(10, 1.0)[-1]
    assert light["level"] == "light" and 0 <= light["score"] < 1 and light["provisional"] is True
    assert "agent_wait_s_per_s" not in light or light["agent_wait_s_per_s"] is None
    med = strain_run(60, 1.0)[-1]
    full = strain_run(90, 1.0)[-1]
    delay_full = strain_run(10, 3.0)[-1]
    assert med["level"] == "medium" and 1 <= med["score"] < 2
    assert full["level"] == "full" and 2 <= full["score"] < 3
    assert delay_full["level"] == "full" and delay_full["delay_level"] == "full"
    danger = strain_run(99, 9.0, wait=2.0)[-1]
    assert danger["level"] == "danger" and danger["score"] == 4.0
    scores = [strain_run(b, 1.0)[-1]["score"] for b in (5, 20, 45, 70, 86, 95)]
    assert scores == sorted(scores), scores


def test_strain_score_bounds():
    assert M.strain_score("medium", "medium", "light", 40.0, 1.0) == 1.0
    assert M.strain_score("medium", "medium", "light", 84.99, 1.0) < 2.0
    assert M.strain_score("overload", "overload", "light", 100.0, 1.0) == 3.999
    assert M.strain_score(None, None, None, None, None) is None


def test_strain_first_tick_uses_shared_cpu():
    c = M.StrainCollector({"cpu_ticks": lambda: None, "burst": lambda: None})
    x = ctx(shared={"cpu_busy_pct": 50.0})
    assert step(c, x, 1000)["machine.strain"]["cpu_level"] == "light"     # dwell not yet met
    assert M.StrainCollector({"cpu_ticks": lambda: None, "burst": lambda: None}).collect(ctx())[
        "machine.strain"] == {"unknown": "read_failed"}


# ---------------------------------------------------------------- path

class Clock(object):
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


def pathc(bursts, clock, routes=None):
    it = iter(bursts)
    return M.PathCollector({"if_counters": lambda: {"en0": iface(0, 0)},
                            "default_routes": lambda: routes if routes is not None else [("en0", "g", 3)],
                            "ping_burst": lambda ip, ifn, count, gap: next(it), "anchor": lambda: "192.0.2.1",
                            "clock": clock, "path_sync": True})


def test_path_warming_then_ok_window_and_stale():
    clk = Clock(0.0)
    p = pathc([[10.0, None, 12.0], [11.0, 13.0, 9.0, 10.0]] + [[20.0] * 4] * 5, clk)
    assert p.collect(ctx())["machine.path"] == {"unknown": "warming_up"}   # 3 echoes < 4
    clk.t = 15.0
    v = p.collect(ctx())["machine.path"]
    assert v["level"] == "ok" and v["loss_pct"] == 14.3                   # one loss: not evidence
    assert "192.0.2.1" not in repr(v)
    for i in range(3):
        clk.t += 15.0
        v = p.collect(ctx())["machine.path"]
    assert len(p.w.path) == 12
    clk.t += 200.0                                                         # stale window dropped
    p.r["ping_burst"] = lambda *a, **k: []
    assert p.collect(ctx())["machine.path"] == {"unknown": "warming_up"}


def test_path_levels():
    clk = Clock(0.0)
    p = pathc([[200.0] * 4], clk)
    assert p.collect(ctx())["machine.path"]["level"] == "degraded"
    clk2 = Clock(0.0)
    p2 = pathc([[20.0, None, None, 20.0]], clk2)
    v = p2.collect(ctx())["machine.path"]
    assert v["level"] == "bad" and v["loss_pct"] == 50.0
    clk3 = Clock(0.0)
    p3 = pathc([[None] * 4], clk3)
    assert p3.collect(ctx())["machine.path"] == {"level": "bad", "rtt_ms": None, "loss_pct": 100.0}


def test_path_no_physical_route():
    p = pathc([], Clock(), routes=[])
    assert p.collect(ctx())["machine.path"] == {"unknown": "read_failed"}


def test_all_collectors_contract():
    cs = M.all_collectors()
    names = [c.name for c in cs]
    assert names == ["cpu", "memory", "net", "thermal", "power", "strain", "path"]
    for c in cs:
        assert c.tier in ("fast", "probes") and c.signals
    assert {c.name for c in cs if c.lpm_exempt} == {"thermal", "power"}


# ---------------------------------------------------------------- review R5

def test_r5_n12_32bit_tick_wrap_reads_counter_reset_once():
    """RB-n12: the idle counter wraps at 2**32. Truth: one counter_reset tick, then a real value
    (d = 100, 50, 800, 0 -> 150 / 950 busy), never a negative reading."""
    ticks = iter([(100, 50, 2 ** 32 - 500, 0), (200, 100, 300, 0), (300, 150, 1100, 0)])
    c = M.CpuCollector({"cpu_ticks": lambda: next(ticks), "ncpu": lambda: 10})
    x = ctx()
    assert step(c, x, 1000)["machine.cpu"] == {"unknown": "warming_up"}
    assert step(c, x, 1002)["machine.cpu"] == {"unknown": "counter_reset"}
    v = step(c, x, 1004)["machine.cpu"]
    assert v["busy_pct"] == round(100.0 * 150 / 950, 1) and v["busy_pct"] >= 0


def test_r5_m5_strain_climbs_after_a_backwards_wall_step():
    """RB-m5: 99 % busy throughout; the wall clock steps back 1 h after 30 s while the monotonic
    clock runs on. Truth: overload qualifies continuously, so its 60 s dwell is met by 30 + 60 s
    after the step at the latest (evidence may restart at the step) -> overload by then."""
    state = {"t": [0, 0, 0, 0]}

    def ticks():
        state["t"] = [state["t"][0] + 990, state["t"][1], state["t"][2] + 10, 0]
        return tuple(state["t"])
    c = M.StrainCollector({"cpu_ticks": ticks, "burst": lambda: 1.0})
    x = ctx(shared={"mem_pressure_raw": 1, "mem_avail_pct": 60.0})
    levels = []
    for i in range(16):
        mono = 1000.0 + 15 * i
        x.mono = mono
        x.now = mono if i < 3 else mono - 3600.0
        levels.append(c.collect(x)["machine.strain"]["level"])
    # step after i=2 (t=30); overload by mono 1030 + 15 + 60 + 15 (one tick of grid) = i == 8
    assert levels[8:] == ["overload"] * 8, levels
