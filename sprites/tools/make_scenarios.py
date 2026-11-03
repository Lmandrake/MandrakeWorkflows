#!/usr/bin/env python3
"""Gallery scenarios: one indicator at a time, so each grid row shows a concept answering ONE datum.

  python3 tools/make_scenarios.py      # writes prototype/scenarios.js (window.VISITORS_SCENARIOS)

Stage for gallery cells is 640x400 with chrome=0 (no menu bar or dock); focus is null except g_needs.
`hud` names the values burned into the video so the viewer sees the data under the motion.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
HUE = 190
PROJECTS = [("Orchard", 286), ("ProjectCert", 211), ("ProjectDial", 93), ("Lodestar", 43), ("Granite", 164), ("SidePulse", 350)]


def S(cpu=0.05, mem=0.6, procs=2, state="idle", rx=0.05, tx=0.02):
    return {"cpu": cpu, "mem": mem, "procs": procs, "state": state, "rx": rx, "tx": tx}


def key(t, s, level=0.1, thermal=0, mempress=0, mbps=0.6, vpn="up", loss=0, focus=None, pair=("", ""), amt=0, bwstrain=0):
    return {"t": t, "s": s, "m": {"level": level, "thermal": thermal, "mempress": mempress},
            "net": {"mbps": mbps, "vpn": vpn, "loss": loss, "strain": bwstrain}, "focus": focus, "play": {"pair": list(pair), "amt": amt}}


def one(**k):
    return {"s0": S(**k)}


def many(n, **k):
    return {f"s{i}": S(**k) for i in range(n)}


def sess(n, hue=HUE):
    return [{"id": f"s{i}", "hue": (hue + i * 0) % 360, "name": f"s{i}", "iv": i} for i in range(n)]


def scenarios():
    out = {}
    def add(sid, title, dur, sessions, keys, hud):
        out[sid] = {"id": sid, "title": title, "seed": 777 + len(out), "duration": dur,
                    "sessions": sessions, "keys": keys, "hud": hud,
                    "labels": {"g_variants": "variant"}.get(sid)}
    add("g_idle", "Idle: one session resting", 12, sess(1),
        [key(0, one()), key(12, one())], ["state", "cpu"])
    add("g_cpu", "CPU: one session ramps to ~4 cores, then settles", 14, sess(1),
        [key(0, one(cpu=0.05, state="working")), key(2, one(cpu=0.05, state="working")),
         key(8, one(cpu=3.8, state="working")), key(11, one(cpu=3.8, state="working")),
         key(14, one(cpu=0.3, state="working"))], ["cpu"])
    add("g_mem", "Memory: footprint grows 0.3 to 2.5 GB", 13, sess(1),
        [key(0, one(cpu=0.5, mem=0.3, state="working")), key(2, one(cpu=0.5, mem=0.3, state="working")),
         key(10, one(cpu=0.5, mem=2.5, state="working")), key(13, one(cpu=0.5, mem=2.5, state="working"))], ["mem"])
    add("g_tasks", "Background tasks: 1 to 10, then back to 2", 14, sess(1),
        [key(0, one(cpu=0.6, procs=1, state="working")), key(2, one(cpu=0.6, procs=1, state="working")),
         key(8, one(cpu=0.6, procs=10, state="working")), key(11, one(cpu=0.6, procs=10, state="working")),
         key(13, one(cpu=0.6, procs=2, state="working")), key(14, one(cpu=0.6, procs=2, state="working"))], ["procs"])
    F = [16, 60, 300, 300]
    add("g_needs", "Needs you: session asks a question at 4 s, answered at 11 s (window on the left)", 14, sess(1),
        [key(0, one(), focus=F), key(4, one(), focus=F), key(4.05, one(state="needs"), focus=F),
         key(11, one(state="needs"), focus=F), key(11.05, one(), focus=F), key(14, one(), focus=F)], ["state"])
    w = dict(cpu=1.0, mem=0.8, procs=3, state="working")
    add("g_strain", "Machine strain: light to danger (CPU, heat, memory pressure), then recovery", 16, sess(3),
        [key(0, many(3, **w)), key(2, many(3, **w)), key(9, many(3, **w), level=3, thermal=2, mempress=2),
         key(12, many(3, **w), level=3, thermal=2, mempress=2), key(15, many(3, **w), level=0.1), key(16, many(3, **w))],
        ["level"])
    # Network, per session: download (rx) then upload (tx), then the link can't keep up (need > available).
    def nk(t, rx, tx, bs=0):
        return key(t, {"s0": S(cpu=0.8, mem=0.8, procs=3, state="working", rx=rx, tx=tx)}, mbps=rx + tx, bwstrain=bs)
    add("g_net", "Network: download rises (0-6 s), upload rises (6-11 s), then the link is too slow for the work (12-17 s)", 19, sess(1),
        [nk(0, 0.05, 0.02), nk(1, 0.05, 0.02), nk(4, 25, 0.3), nk(6, 25, 0.3), nk(9, 0.5, 12), nk(11, 0.5, 12),
         nk(12.5, 18, 6, 1), nk(16.5, 18, 6, 1), nk(18, 0.3, 0.1), nk(19, 0.3, 0.1)], ["rx", "tx", "bw"])
    add("g_vpn", "VPN lost at 3 s, back at 11 s (machine is NOT strained)", 15, sess(3),
        [key(0, many(3, **w), mbps=2), key(3, many(3, **w), mbps=2), key(3.05, many(3, **w), mbps=0, vpn="down", loss=100),
         key(11, many(3, **w), mbps=0, vpn="down", loss=100), key(11.05, many(3, **w), mbps=2), key(15, many(3, **w), mbps=2)],
        ["vpn", "level"])
    idle2 = many(2, cpu=0.02, mem=0.6)
    add("g_play", "Play: two idle sessions meet and dance (no data change)", 15, sess(2),
        [key(0, idle2, pair=("s0", "s1")), key(3, idle2, pair=("s0", "s1")), key(5, idle2, pair=("s0", "s1"), amt=1),
         key(11, idle2, pair=("s0", "s1"), amt=1), key(13, idle2, pair=("s0", "s1")), key(15, idle2, pair=("s0", "s1"))],
        ["play"])
    add("g_variants", "Individualizer: variants 0-7, all the SAME colour and the same load", 12, sess(8),
        [key(0, many(8, cpu=0.5, mem=0.7, procs=3, state="working")), key(12, many(8, cpu=0.5, mem=0.7, procs=3, state="working"))], [])
    ps = [{"id": f"s{i}", "hue": h, "name": n, "label": n, "iv": i} for i, (n, h) in enumerate(PROJECTS)]
    st = {"s0": S(3.2, 1.8, 8, "working", rx=22, tx=2), "s1": S(0.02, 0.5, 2), "s2": S(0.7, 0.9, 3, "working", rx=0.5, tx=9),
          "s3": S(0.4, 1.2, 4, "working", rx=3, tx=3), "s4": S(0.02, 0.6, 2, "needs"), "s5": S(0.02, 0.4, 1)}
    add("g_projects", "Your projects: real colours, one variant each (Orchard busy and downloading, ProjectDial uploading, Granite needs you)", 14, ps,
        [key(0, st, mbps=3), key(14, st, mbps=3)], [])
    add("g_cast", "Cast preview: one session, gently working (hue and variant set by URL)", 12, sess(1),
        [key(0, one(cpu=0.3, mem=0.8, procs=3, state="working")), key(6, one(cpu=1.2, mem=0.8, procs=4, state="working")),
         key(12, one(cpu=0.3, mem=0.8, procs=3, state="working"))], [])
    return out


def main():
    sc = scenarios()
    (HERE / "prototype/scenarios.js").write_text("/* generated by tools/make_scenarios.py; do not edit */\nwindow.VISITORS_SCENARIOS = "
                                              + json.dumps(sc, separators=(",", ":")) + ";\n")
    print(f"{len(sc)} scenarios -> prototype/scenarios.js")


if __name__ == "__main__":
    main()
