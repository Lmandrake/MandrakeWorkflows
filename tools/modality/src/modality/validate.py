"""The validation harness: every estimator against every known-truth case.

Runs the whole catalogue at several sample sizes and several seeds, so the
report shows *variance*, not one lucky draw, and writes a CSV of every run plus
a markdown summary.

Two accuracy questions are scored separately, because the estimators answer
two different questions:

* against ``true_modes``      -- how many peaks does the density really have?
* against ``n_components``    -- how many pieces was it built from?

``gmm_bic`` is scored against the second and is *expected* to do badly against
the first; that expectation is itself one of the findings.
"""

from __future__ import annotations

import csv
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from .api import estimate_modality
from .testcases import TestCase, all_cases, get_case

DEFAULT_SAMPLE_SIZES: tuple[int, ...] = (50, 200, 1000, 10000)
DEFAULT_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)

# Methods that claim to count visible modes, scored against `true_modes`.
MODE_METHODS: tuple[str, ...] = (
    "kde_silverman",
    "kde_scott",
    "kde_stable",
    "silverman_boot",
    "gmm_modes",
)
# Methods that count components, scored against `n_components`.
COMPONENT_METHODS: tuple[str, ...] = ("gmm_bic", "gmm_aic")
# Binary unimodality check, scored separately.
BINARY_METHODS: tuple[str, ...] = ("dip",)

ALL_METHODS = MODE_METHODS + COMPONENT_METHODS + BINARY_METHODS


def _run_one(args: tuple[str, int, int, bool]) -> dict:
    name, n, seed, run_bootstrap = args
    case = get_case(name)
    x = case.sample(n, seed)
    res = estimate_modality(x, run_bootstrap=run_bootstrap, random_state=seed)
    row: dict = {
        "case": case.name,
        "tags": "|".join(case.tags),
        "n_components": case.n_components,
        "true_modes": case.true_modes,
        "true_modes_visible": case.true_modes_visible,
        "n": n,
        "seed": seed,
        "headline": res.visible_modes,
    }
    for m in ALL_METHODS:
        row[m] = res.value(m)
    return row


def run_validation(
    cases: Sequence[TestCase] | None = None,
    sample_sizes: Sequence[int] = DEFAULT_SAMPLE_SIZES,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    jobs: int = 1,
    run_bootstrap: bool = True,
    progress: bool = True,
) -> list[dict]:
    cases = list(cases) if cases is not None else all_cases()
    tasks = [
        (c.name, n, s, run_bootstrap)
        for c in cases
        for n in sample_sizes
        for s in seeds
    ]
    rows: list[dict] = []
    if jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            for i, row in enumerate(pool.map(_run_one, tasks, chunksize=4), 1):
                rows.append(row)
                if progress and i % 50 == 0:
                    print(f"  {i}/{len(tasks)} runs", flush=True)
    else:
        for i, t in enumerate(tasks, 1):
            rows.append(_run_one(t))
            if progress and i % 50 == 0:
                print(f"  {i}/{len(tasks)} runs", flush=True)
    return rows


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

@dataclass
class Score:
    method: str
    target: str
    exact: float
    within_one: float
    bias: float
    n: int

    def as_row(self) -> list[str]:
        return [
            self.method,
            self.target,
            f"{self.exact:.3f}",
            f"{self.within_one:.3f}",
            f"{self.bias:+.2f}",
            str(self.n),
        ]


def score_method(rows: Iterable[dict], method: str, target: str) -> Score:
    exact = within = total = 0
    errs: list[int] = []
    for r in rows:
        v = r.get(method)
        if v is None:
            continue
        t = r[target]
        total += 1
        exact += int(v == t)
        within += int(abs(v - t) <= 1)
        errs.append(v - t)
    if total == 0:
        return Score(method, target, 0.0, 0.0, 0.0, 0)
    return Score(method, target, exact / total, within / total, statistics.fmean(errs), total)


def _fmt_table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def _mode_of(values: Sequence[int | None]) -> str:
    vals = [v for v in values if v is not None]
    if not vals:
        return "-"
    c = Counter(vals)
    top, cnt = c.most_common(1)[0]
    return str(top) if cnt == len(vals) else f"{top}~"


def summarize(rows: Sequence[dict], sample_sizes: Sequence[int] = DEFAULT_SAMPLE_SIZES) -> str:
    out: list[str] = []
    out.append("# Validation results\n")
    n_cases = len({r["case"] for r in rows})
    out.append(
        f"{len(rows)} runs: {n_cases} ground-truth distributions x "
        f"{len(sample_sizes)} sample sizes x {len({r['seed'] for r in rows})} seeds.\n"
    )

    # --- headline accuracy ------------------------------------------------
    out.append("## Accuracy against the TRUE number of visible modes\n")
    out.append(
        "`exact` = fraction of runs matching the true local-maximum count; "
        "`+-1` = fraction within one; `bias` = mean signed error "
        "(positive = over-counting).\n"
    )
    body = [score_method(rows, m, "true_modes").as_row() for m in ("headline",) + MODE_METHODS]
    body += [score_method(rows, m, "true_modes").as_row() for m in COMPONENT_METHODS]
    out.append(_fmt_table(["method", "target", "exact", "+-1", "bias", "runs"], body))
    out.append("")

    out.append(
        "## Accuracy against the PROMINENT visible modes\n\n"
        "The same target, but ignoring maxima whose prominence is under 1% of "
        "the peak density -- dips too shallow to see in a plot.\n"
    )
    body = [
        score_method(rows, m, "true_modes_visible").as_row()
        for m in ("headline",) + MODE_METHODS
    ]
    out.append(_fmt_table(["method", "target", "exact", "+-1", "bias", "runs"], body))
    out.append("")

    out.append("## Accuracy against the number of MIXTURE COMPONENTS\n")
    body = [
        score_method(rows, m, "n_components").as_row()
        for m in COMPONENT_METHODS + MODE_METHODS
    ]
    out.append(_fmt_table(["method", "target", "exact", "+-1", "bias", "runs"], body))
    out.append("")

    # --- by sample size ----------------------------------------------------
    out.append("## Exact-match rate by sample size (target: true visible modes)\n")
    header = ["method"] + [f"n={n}" for n in sample_sizes]
    body = []
    for m in ("headline",) + MODE_METHODS:
        row = [m]
        for n in sample_sizes:
            sub = [r for r in rows if r["n"] == n]
            row.append(f"{score_method(sub, m, 'true_modes').exact:.3f}")
        body.append(row)
    out.append(_fmt_table(header, body))
    out.append("")

    # --- binary unimodality ------------------------------------------------
    dip_rows = [r for r in rows if r.get("dip") is not None]
    if dip_rows:
        tp = sum(1 for r in dip_rows if r["true_modes"] > 1 and r["dip"] == 2)
        fn = sum(1 for r in dip_rows if r["true_modes"] > 1 and r["dip"] == 1)
        tn = sum(1 for r in dip_rows if r["true_modes"] == 1 and r["dip"] == 1)
        fp = sum(1 for r in dip_rows if r["true_modes"] == 1 and r["dip"] == 2)
        out.append("## Dip test as a binary unimodal / multimodal classifier\n")
        out.append(
            _fmt_table(
                ["", "dip says unimodal", "dip says multimodal"],
                [
                    ["truly 1 mode", str(tn), str(fp)],
                    ["truly >1 mode", str(fn), str(tp)],
                ],
            )
        )
        sens = tp / (tp + fn) if tp + fn else 0.0
        spec = tn / (tn + fp) if tn + fp else 0.0
        out.append(
            f"\nSensitivity (multimodal correctly flagged): {sens:.3f}. "
            f"Specificity (unimodal correctly left alone): {spec:.3f}.\n"
        )

    # --- per-case ----------------------------------------------------------
    out.append("## Per-case detail\n")
    out.append(
        "`comp` = true component count, `modes` = true visible-mode count. "
        "Each estimator cell is the modal answer across seeds; a trailing `~` "
        "means the seeds disagreed.\n"
    )
    by_case: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_case[r["case"]].append(r)

    show = ("kde_stable", "silverman_boot", "gmm_modes", "gmm_bic", "dip")
    header = ["case", "comp", "modes", "n"] + list(show)
    body = []
    for case_name in sorted(by_case, key=lambda c: (get_case(c).n_components, c)):
        rs = by_case[case_name]
        c = get_case(case_name)
        for i, n in enumerate(sample_sizes):
            sub = [r for r in rs if r["n"] == n]
            if not sub:
                continue
            flag = " **" if c.diverges else ""
            body.append(
                [
                    (case_name + flag) if i == 0 else "",
                    str(c.n_components) if i == 0 else "",
                    str(c.true_modes) if i == 0 else "",
                    str(n),
                ]
                + [_mode_of([r[m] for r in sub]) for m in show]
            )
    out.append(_fmt_table(header, body))
    out.append("\n`**` marks a case where the component count and the visible-mode count disagree.\n")
    return "\n".join(out)


def write_csv(rows: Sequence[dict], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return path


def divergence_report(rows: Sequence[dict] | None = None) -> str:
    """A table of every case where components != visible modes."""
    out = ["# Where 'component count' and 'visible mode count' diverge\n"]
    body = []
    for c in all_cases():
        if not c.diverges:
            continue
        body.append([c.name, str(c.n_components), str(c.true_modes), c.description.replace("\n", " ")])
    out.append(_fmt_table(["case", "components", "visible modes", "why"], body))
    return "\n".join(out)
