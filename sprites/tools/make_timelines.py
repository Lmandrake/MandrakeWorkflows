#!/usr/bin/env python3
"""Scripted data timelines for the Visitors trials, and the answer key they imply.

  python3 tools/make_timelines.py      # writes prototype/timelines.js

The data ARE the motion: each piece renders one of these timelines, so every comprehension question
has a scripted true answer. Value ranges are taken from real fixtures (fixtures/RANGES.md): per-session
cpu in cores (0-4), footprint in GB (0.2-2.5), procs 1-12; machine level 0 light .. 3 danger (continuous),
thermal 0-2, mempress 0-2; network Mbit/s, vpn up/down, path loss %.
Each brief has variants that permute WHO does what, so the owner cannot learn answers across pieces.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
HUES = {"blue": 215, "amber": 40, "green": 130, "pink": 320, "teal": 172}
FOCUS_L = [90, 110, 560, 430]
FOCUS_R = [640, 160, 540, 420]


def sess(ids):
    return [{"id": i, "hue": HUES[i], "name": i} for i in ids]


def S(cpu=0.05, mem=0.4, procs=2, state="idle"):
    return {"cpu": cpu, "mem": mem, "procs": procs, "state": state}


def key(t, s, level=0.2, thermal=0, mempress=0, mbps=0.8, vpn="up", loss=0, focus=FOCUS_L, play=None):
    return {"t": t, "s": s, "m": {"level": level, "thermal": thermal, "mempress": mempress},
            "net": {"mbps": mbps, "vpn": vpn, "loss": loss}, "focus": focus,
            "play": play or {"pair": ["", ""], "amt": 0}}


def brief_a(v):
    ids = ["blue", "amber", "green", "pink", "teal"]
    busy, big, tasks = (("amber", "teal", "pink"), ("green", "blue", "amber"), ("pink", "amber", "blue"))[v - 1]
    def at(phase):
        out = {}
        for i in ids:
            cpu = {"calm": 0.05, "burst": 0.6, "settle": 0.25}[phase]
            if i == busy: cpu = {"calm": 0.1, "burst": 3.6, "settle": 1.6}[phase]
            mem = 2.4 if i == big else 0.5 + 0.1 * ids.index(i)
            procs = 10 if i == tasks else 2 + ids.index(i) % 2
            st = "working" if phase != "calm" else "idle"
            out[i] = S(cpu, mem, procs, st)
        return out
    K = [key(0, at("calm")), key(5, at("calm")), key(7, at("burst"), level=0.6, mbps=4),
         key(20, at("burst"), level=0.7, mbps=5), key(20.4, at("burst"), level=0.7, mbps=5, focus=FOCUS_R),
         key(24, at("settle"), level=0.3, focus=FOCUS_R), key(36, at("settle"), level=0.3, focus=FOCUS_R)]
    return sess(ids), K, 36, {"busiest_cpu": busy, "largest_memory": big, "most_tasks": tasks}


def brief_b(v):
    ids = ["blue", "amber", "green", "pink"]
    onset = (12, 18)[v - 1]
    work = {i: S(0.8, 0.6 + 0.2 * n, 3, "working") for n, i in enumerate(ids)}
    hard = {i: S(2.2, 0.9 + 0.3 * n, 5, "working") for n, i in enumerate(ids)}
    K = [key(0, work, level=0.1), key(onset, work, level=0.1),
         key(onset + 6, hard, level=1.6, thermal=1, mempress=1, mbps=3),
         key(onset + 12, hard, level=3.0, thermal=2, mempress=2, mbps=3),
         key(onset + 16, hard, level=3.0, thermal=2, mempress=2, mbps=3, focus=FOCUS_R),
         key(onset + 22, work, level=0.2, thermal=1, focus=FOCUS_R), key(42, work, level=0.1, focus=FOCUS_R)]
    return sess(ids), K, 42, {"strain_onset_s": onset, "peak": "danger", "recovers": True}


def brief_c(v):
    ids = ["blue", "amber", "green", "pink"]
    work = {i: S(0.6, 0.7, 3, "working") for i in ids}
    hard = {i: S(2.4, 1.1, 6, "working") for i in ids}
    strain = [(8, 16), (24, 32), (10, 26)][v - 1]
    drop = [(24, 32), (8, 16), None][v - 1]   # v3: strain only, no drop (catch trial)
    K = []
    for t in sorted({0, *strain, *(drop or ()), strain[0] + 2, strain[1] - 1, 40}):
        in_s = strain[0] + 2 <= t <= strain[1] - 1
        in_d = bool(drop) and drop[0] <= t < drop[1]
        K.append(key(t, hard if in_s else work, level=2.7 if in_s else 0.3, thermal=1 if in_s else 0,
                     mbps=0 if in_d else 2.5, vpn="down" if in_d else "up", loss=100 if in_d else 0,
                     focus=FOCUS_L if t < 20 else FOCUS_R))
    return sess(ids), K, 40, {"strain_window_s": strain, "vpn_drop_window_s": drop,
                              "first_event": "strain" if not drop or strain[0] < drop[0] else "vpn",
                              "vpn_dropped": bool(drop)}


def brief_d(v):
    ids = ["blue", "amber", "green", "pink"]
    who, t0, decoy = (("amber", 14, "pink"), ("green", 20, "blue"))[v - 1]
    def at(needs, decoy_on):
        out = {}
        for i in ids:
            st = "needs" if (needs and i == who) else ("idle" if i == who else "working")
            cpu = 3.2 if (decoy_on and i == decoy) else (0.0 if st != "working" else 0.7)
            out[i] = S(cpu, 0.8, 3, st)
        return out
    dt = 8 if v == 1 else 6   # decoy CPU burst, well clear of the summons
    K = [key(0, at(False, False)), key(dt - 1, at(False, False)), key(dt, at(False, True), level=0.8),
         key(dt + 4, at(False, True), level=0.8), key(dt + 5, at(False, False)),
         key(t0 - 0.1, at(False, False)), key(t0, at(True, False)), key(30, at(True, False)),
         key(30.1, at(False, False)), key(40, at(False, False))]
    K.sort(key=lambda k: k["t"])
    return sess(ids), K, 40, {"needs_you": who, "needs_onset_s": t0, "needs_end_s": 30,
                              "decoy_cpu_burst": decoy, "decoy_window_s": [dt, dt + 5]}


def brief_e(v):
    ids = ["blue", "amber", "green", "pink"]
    pair, worker = ((["blue", "pink"], "green"), (["amber", "green"], "blue"))[v - 1]
    other = [i for i in ids if i not in pair and i != worker][0]
    def at(worker_on):
        out = {i: S(0.02, 0.5, 2, "idle") for i in ids}
        out[worker] = S(1.4 if worker_on else 0.03, 0.9, 4, "working" if worker_on else "idle")
        out[other] = S(0.02, 0.6, 2, "idle")
        return out
    p = lambda a: {"pair": pair, "amt": a}
    K = [key(0, at(True), play=p(0)), key(9, at(True), play=p(0)), key(12, at(True), play=p(1)),
         key(20, at(True), play=p(1)), key(20.3, at(False), play=p(1)),
         key(28, at(False), play=p(1)), key(31, at(False), play=p(0)), key(40, at(False), play=p(0))]
    return sess(ids), K, 40, {"play_pair": pair, "play_window_s": [10, 30], "data_change_during_play": True,
                              "who_stopped_working": worker, "stop_s": 20.3,
                              "play_pair_changed_state": False}


def brief_p(v):
    ids = ["blue", "amber", "green"]
    calm = {i: S(0.3, 0.8, 3, "working") for i in ids}
    K = [key(0, calm), key(14, calm)]
    return sess(ids), K, 14, {}


def main():
    tl, keyout = {}, {}
    for b, f, nv in [("a", brief_a, 3), ("b", brief_b, 2), ("c", brief_c, 3), ("d", brief_d, 2),
                     ("e", brief_e, 2), ("p", brief_p, 1)]:
        for v in range(1, nv + 1):
            sessions, keys, dur, ans = f(v)
            tid = f"{b}{v}"
            tl[tid] = {"id": tid, "seed": 20261031 + ord(b) * 10 + v, "duration": dur,
                       "sessions": sessions, "keys": keys}
            keyout[tid] = ans
    (HERE / "prototype/timelines.js").write_text(
        "/* generated by tools/make_timelines.py; do not edit */\nwindow.VISITORS_TIMELINES = "
        + json.dumps(tl, separators=(",", ":")) + ";\n")
    print(f"{len(tl)} timelines -> prototype/timelines.js (answer key: MandrakeWorkflows study)")


if __name__ == "__main__":
    main()
