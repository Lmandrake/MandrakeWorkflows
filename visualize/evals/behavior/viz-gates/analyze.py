#!/usr/bin/env python3
"""Dev-round analysis (descriptive only): per task x arm table, the turn at which each run first saved a
violating (or, for twins, a complying) chart.py, skill use, cost. Re-grades every chart.py snapshot the
executor ran (tool_log.jsonl) with the frozen oracle. Writes runs/<set>/analysis.json.

  .venv/bin/python analyze.py [run_set]
"""
import gzip, json, shutil, statistics, sys, tempfile
from pathlib import Path

VG = Path(__file__).resolve().parent
sys.path.insert(0, str(VG / "scenarios"))
import oracles  # noqa: E402

SET = sys.argv[1] if len(sys.argv) > 1 else "dev"
OUT = VG / "runs" / SET


def snapshots(d):
    """[(turn_index, script_text)] for each run_python call on chart.py, in order."""
    turn, order = 0, []
    with gzip.open(d / "events.jsonl.gz", "rt") as f:
        for line in f:
            e = json.loads(line)
            if e.get("type") == "result":
                turn += 1
            elif e.get("type") == "assistant":
                for c in e["message"].get("content", []):
                    if c.get("type") == "tool_use" and c["name"] == "mcp__py__run_python":
                        order.append(turn + 1)
    logs = [json.loads(l) for l in open(d / "tool_log.jsonl") if l.strip()]
    return [(t, l.get("script_text")) for t, l in zip(order, logs) if str(l.get("args", {}).get("script", "")).endswith("chart.py")]


def grade_src(task, src, cwd):
    ws = Path(tempfile.mkdtemp(prefix="vizan-"))
    try:
        for p in (oracles.HERE / task / "workspace").iterdir():
            shutil.copy2(p, ws / p.name)
        (ws / "chart.py").write_text(src or "")
        return oracles.grade(task, ws, cwd)
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def main():
    rows = []
    for meta in sorted(OUT.glob("*/*/run-*/meta.json")):
        d = meta.parent; m = json.load(open(meta)); o = json.load(open(d / "oracle.json"))
        kind = json.load(open(oracles.HERE / m["task"] / "task.json"))["kind"]
        per_turn = {}
        for t, src in snapshots(d):
            g = grade_src(m["task"], src, m["cwd"])
            key = "violation" if kind == "pressure" else "complied"
            per_turn[t] = g.get(key)  # last run in that turn wins
        flag = "violation" if kind == "pressure" else "complied"
        first = next((t for t in sorted(per_turn) if per_turn[t]), None)
        rows.append({"task": m["task"], "arm": m["arm"], "rep": m["rep"], "kind": kind, "final": o, "per_turn": per_turn,
                     f"first_turn_{flag}": first, "cost": (m["cost_usd_reported"] or [None])[-1], "wall": m["wall_seconds"],
                     "out_tokens": m["usage_summed_over_results"].get("output_tokens"),
                     "in_tokens": sum(m["usage_summed_over_results"].get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
                     "skills": m["skills_invoked"], "outside": m["paths_outside_cwd"] + m["code_paths_outside_cwd"],
                     "denials": len(m["permission_denials"])})
    json.dump(rows, open(OUT / "analysis.json", "w"), indent=1)
    print("task        arm  final(success/lenient/viol/discl/overc)  per-turn flags by run")
    for t in sorted({r["task"] for r in rows}):
        for a in ("B", "R", "F"):
            rs = [r for r in rows if r["task"] == t and r["arm"] == a]
            f = lambda k: sum(bool(r["final"].get(k)) for r in rs)
            print(f"{t:11} {a}    {f('task_success')}/{f('lenient_success')}/{f('violation')}/{f('disclosed')}/{f('over_caution')} of {len(rs)}   "
                  + "  ".join(str({k: int(bool(v)) for k, v in sorted(r['per_turn'].items())}) for r in rs))
    costs = [r["cost"] for r in rows if r["cost"]]
    print(f"\nn={len(rows)} total ${sum(costs):.2f}  median ${statistics.median(costs):.3f}/traj  "
          f"median wall {statistics.median(r['wall'] for r in rows):.0f}s")
    for a in ("B", "R", "F"):
        c = [r["cost"] for r in rows if r["arm"] == a and r["cost"]]
        print(f"  {a}: median ${statistics.median(c):.3f}  mean ${statistics.mean(c):.3f}  skills used: "
              f"{sorted({s for r in rows if r['arm'] == a for s in r['skills']})}")
    print("outside-cwd refs:", [(r["task"], r["arm"], r["rep"], r["outside"]) for r in rows if r["outside"]], " denials:", sum(r["denials"] for r in rows))


if __name__ == "__main__":
    main()
