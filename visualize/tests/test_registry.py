import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import route_renderer  # noqa: E402

SHAPES = {
    "network", "embedding", "vector_field", "scalar_field", "point_samples_3d", "geo_flow",
    "trajectories", "scalar_time_series", "hierarchy", "text_corpus", "none",
}
OUTPUTS = {
    "interactive_web", "interactive_native", "still", "hires_still", "vector_still", "video",
    "deterministic_video",
}
REQUIRED = {
    "id", "names", "status", "verified", "install", "adapter", "platform", "dims", "primitives",
    "data_shapes", "output_modes", "hidden_defaults", "hazards", "license",
}


TASKS = {
    "live_monitoring", "exploratory_drilldown", "many_series_comparison", "event_annotation",
    "distribution_over_time", "long_time_series",
}


def test_registry_entries_are_wellformed():
    entries = route_renderer.load_registry()
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids))
    for e in entries:
        assert REQUIRED <= set(e), (e["id"], REQUIRED - set(e))
        assert e["status"] in {"runs", "pending", "dead"}
        assert set(e["data_shapes"]) <= SHAPES, e["id"]
        assert set(e["data_shapes"].values()) <= {"P", "S", "E"}, e["id"]
        assert set(e["output_modes"]) <= OUTPUTS, e["id"]
        assert set(e.get("tasks", [])) <= TASKS, e["id"]


def test_routes_by_property():
    ids = [m["id"] for m in route_renderer.route(shape="point_samples_3d", min_fit="P")]
    assert ids == ["potree"]
    assert "webgl-wind" in [m["id"] for m in route_renderer.route(shape="vector_field", min_fit="P")]


def test_hierarchy_has_no_primary_renderer():
    assert route_renderer.route(shape="hierarchy", min_fit="P") == []


def test_dead_renderers_are_excluded_by_default():
    assert all(m["status"] != "dead" for m in route_renderer.route())


def test_modes_table_covers_every_gate():
    text = (REPO / "principles" / "modes.md").read_text()
    rows = set(re.findall(r"^\| (G\d+) ", text, re.MULTILINE))
    assert rows == {f"G{i}" for i in range(1, 14)}


def test_time_series_has_a_primary_and_tasks_narrow_it():
    primaries = [m["id"] for m in route_renderer.route(shape="scalar_time_series", min_fit="P")]
    assert "grafana" in primaries and "mpl-network-still" in primaries  # interactive and static stills
    ids = [m["id"] for m in route_renderer.route(shape="scalar_time_series", task="exploratory_drilldown")]
    assert ids == ["grafana", "victoriametrics"]
    assert route_renderer.route(shape="network", task="live_monitoring", min_fit="S") == []
