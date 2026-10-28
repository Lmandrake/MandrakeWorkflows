#!/usr/bin/env python3
"""Resolve capability properties to renderer ids, using registry/renderers.yaml.

Skills ask for a capability by property and never by toolkit name (decision D6). This
script is the one place where properties become names:

    python3 tools/route_renderer.py --shape point_samples_3d --output still
    python3 tools/route_renderer.py --shape network --primitive links --dims 2d --fit P
    python3 tools/route_renderer.py --shape scalar_time_series --task live_monitoring

Each match prints its fit, status, licence, how it makes the requested output, and the
hidden defaults that must be bound or switched off before the render is honest. With no
match it says so: a data shape with no primary renderer is routed to the CLEAR family.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "registry" / "renderers.yaml"
FIT_RANK = {"P": 0, "S": 1, "E": 2}


def load_registry(path: Path = REGISTRY) -> list[dict]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment problem, not logic
        raise SystemExit(
            "PyYAML is needed to read the renderer registry: `python3 -m pip install pyyaml`"
        ) from exc
    return yaml.safe_load(path.read_text())["renderers"]


def renderer_names(path: Path = REGISTRY) -> set[str]:
    """Every string a skill must not contain: ids plus their listed names."""
    names: set[str] = set()
    for entry in load_registry(path):
        names.add(entry["id"])
        names.update(entry.get("names", []))
    return names


def route(
    shape: str | None = None,
    primitive: str | None = None,
    output: str | None = None,
    dims: str | None = None,
    min_fit: str = "S",
    include_dead: bool = False,
    task: str | None = None,
    registry: list[dict] | None = None,
) -> list[dict]:
    """Renderers matching every given property, best fit first."""
    entries = registry if registry is not None else load_registry()
    limit = FIT_RANK[min_fit]
    matches = []
    for entry in entries:
        if entry["status"] == "dead" and not include_dead:
            continue
        fit = None
        if shape:
            fit = entry.get("data_shapes", {}).get(shape)
            if fit is None or FIT_RANK[fit] > limit:
                continue
        if primitive and primitive not in entry.get("primitives", []):
            continue
        if dims and dims not in entry.get("dims", []):
            continue
        if output and not entry.get("output_modes", {}).get(output):
            continue
        if task and task not in entry.get("tasks", []):
            continue
        matches.append({**entry, "fit": fit})
    matches.sort(key=lambda e: (FIT_RANK.get(e["fit"] or "S", 1), e["status"] != "runs", e["id"]))
    return matches


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shape", help="data shape, e.g. network, point_samples_3d, vector_field")
    parser.add_argument("--primitive", help="mark primitive, e.g. points, links, particles")
    parser.add_argument("--output", help="output mode, e.g. interactive_web, hires_still, deterministic_video")
    parser.add_argument("--dims", choices=["2d", "3d"])
    parser.add_argument("--fit", default="S", choices=["P", "S", "E"], help="weakest fit to accept (default S)")
    parser.add_argument("--task", help="reader task, e.g. live_monitoring, exploratory_drilldown, distribution_over_time")
    parser.add_argument("--include-dead", action="store_true")
    args = parser.parse_args(argv[1:])

    matches = route(args.shape, args.primitive, args.output, args.dims, args.fit, args.include_dead, args.task)
    if not matches:
        print("no renderer has this capability; route the piece to the CLEAR family")
        return 1
    for m in matches:
        how = m["output_modes"].get(args.output) if args.output else None
        print(f"{m['id']:18} fit={m['fit'] or '-'} status={m['status']} licence={m['license']}")
        if how:
            print(f"{'':18} {args.output}: {how}")
        for hidden in m.get("hidden_defaults", []):
            print(f"{'':18} bind or switch off: {hidden}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
