"""Command-line interface: ``modality <command>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from . import __version__
from .api import estimate_modality
from .testcases import all_cases, get_case


def load_samples(path: str | Path, column: int | str | None = None) -> np.ndarray:
    """Read 1-D samples from ``.npy``, ``.csv`` or whitespace-delimited text."""
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"no such file: {path}")

    if path.suffix.lower() == ".npy":
        arr = np.load(path)
    else:
        delim = "," if path.suffix.lower() == ".csv" else None
        try:
            arr = np.loadtxt(path, delimiter=delim)
        except ValueError:
            # Probably a header row; retry skipping it and resolve a named column.
            with path.open(encoding="utf-8") as fh:
                header = fh.readline().strip()
            names = [h.strip() for h in (header.split(",") if delim else header.split())]
            arr = np.loadtxt(path, delimiter=delim, skiprows=1)
            if isinstance(column, str):
                if column not in names:
                    raise SystemExit(
                        f"column {column!r} not in {names}"
                    ) from None
                column = names.index(column)

    arr = np.asarray(arr, dtype=float)
    if arr.ndim == 2:
        if column is None:
            if arr.shape[1] != 1:
                raise SystemExit(
                    f"{path} has {arr.shape[1]} columns; pick one with --column"
                )
            column = 0
        arr = arr[:, int(column)]
    arr = arr.ravel()
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        raise SystemExit(f"{path} contained no finite values")
    return arr


def _add_estimator_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--no-bootstrap", action="store_true",
                   help="skip Silverman's smoothed-bootstrap test (the slowest method)")
    p.add_argument("--max-components", type=int, default=8,
                   help="largest Gaussian mixture size the BIC search will try")
    p.add_argument("--min-prominence", type=float, default=0.0,
                   help="ignore modes whose prominence is below this fraction of the peak "
                        "density (0 = count every local maximum)")


def _analyze(x: np.ndarray, args) -> None:
    res = estimate_modality(
        x,
        max_components=args.max_components,
        min_rel_prominence=args.min_prominence,
        run_bootstrap=not args.no_bootstrap,
    )
    print(res.report())


# ---------------------------------------------------------------------------

def cmd_list_cases(args) -> int:
    print(f"{'case':24s} {'comp':>4s} {'modes':>5s} {'vis':>4s}  tags")
    print("-" * 78)
    for c in all_cases():
        mark = " *" if c.diverges else "  "
        print(
            f"{c.name:24s} {c.n_components:4d} {c.true_modes:5d} "
            f"{c.true_modes_visible:4d}{mark} {','.join(c.tags)}"
        )
    n_div = sum(c.diverges for c in all_cases())
    print(
        f"\n{len(all_cases())} cases; {n_div} marked * have a visible-mode count "
        "that differs from their component count."
    )
    return 0


def cmd_truth(args) -> int:
    c = get_case(args.case)
    print(c.summary())
    ms = c.mode_set
    print("\n  exact local maxima (location, height, prominence):")
    for loc, h, p in zip(ms.locations, ms.heights, ms.prominences):
        print(f"    x={loc:12.5g}  f={h:.6g}  prominence={p:.6g}")
    return 0


def cmd_case(args) -> int:
    c = get_case(args.case)
    x = c.sample(args.n, args.seed)
    print(f"case: {c.name}")
    print(f"  {c.description}")
    print(f"  {c.mixture.describe()}")
    print(f"  GROUND TRUTH: {c.n_components} components, {c.true_modes} visible modes")
    print()
    _analyze(x, args)
    return 0


def cmd_analyze(args) -> int:
    x = load_samples(args.path, args.column)
    print(f"loaded {x.size} samples from {args.path}\n")
    _analyze(x, args)
    return 0


def cmd_validate(args) -> int:
    from .validate import (
        DEFAULT_SAMPLE_SIZES,
        DEFAULT_SEEDS,
        divergence_report,
        run_validation,
        summarize,
        write_csv,
    )

    sizes = args.sizes or list(DEFAULT_SAMPLE_SIZES)
    seeds = list(range(args.seeds)) if args.seeds else list(DEFAULT_SEEDS)
    if args.quick:
        sizes, seeds = [200, 1000], [0, 1]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"running validation: {len(all_cases())} cases x {sizes} x {len(seeds)} seeds")
    rows = run_validation(
        sample_sizes=sizes, seeds=seeds, jobs=args.jobs,
        run_bootstrap=not args.no_bootstrap,
    )
    csv_path = write_csv(rows, out / "results.csv")
    summary = summarize(rows, sizes)
    (out / "summary.md").write_text(summary, encoding="utf-8")
    (out / "divergence.md").write_text(divergence_report(), encoding="utf-8")
    print(f"\nwrote {csv_path}")
    print(f"wrote {out / 'summary.md'}")
    print(f"wrote {out / 'divergence.md'}\n")
    print(summary.split("## Per-case detail")[0])
    return 0


def cmd_figures(args) -> int:
    from .plots import make_gallery

    paths = make_gallery(args.out, n=args.n, seed=args.seed, cases=args.cases or None)
    for p in paths:
        print(p)
    return 0


def cmd_catalogue_figure(args) -> int:
    from .plots import plot_catalogue_sample

    print(plot_catalogue_sample(args.out, n=args.n, seed=args.seed))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="modality",
        description="Estimate how multimodal a distribution is: the number of "
                    "local maxima of its density, reported separately from the "
                    "number of mixture components.",
    )
    p.add_argument("--version", action="version", version=f"modality {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("list-cases", help="list the built-in ground-truth distributions")
    q.set_defaults(func=cmd_list_cases)

    q = sub.add_parser("truth", help="print the analytic ground truth for one case")
    q.add_argument("case")
    q.set_defaults(func=cmd_truth)

    q = sub.add_parser("case", help="sample a built-in case and analyse it")
    q.add_argument("case")
    q.add_argument("-n", type=int, default=1000, help="sample size")
    q.add_argument("--seed", type=int, default=0)
    _add_estimator_args(q)
    q.set_defaults(func=cmd_case)

    q = sub.add_parser("analyze", help="analyse samples from a .npy/.csv/.txt file")
    q.add_argument("path")
    q.add_argument("--column", default=None,
                   help="column index or name, for multi-column files")
    _add_estimator_args(q)
    q.set_defaults(func=cmd_analyze)

    q = sub.add_parser("validate", help="run every estimator against every known case")
    q.add_argument("--out", default="results", help="output directory")
    q.add_argument("--jobs", type=int, default=1)
    q.add_argument("--sizes", type=int, nargs="+", default=None)
    q.add_argument("--seeds", type=int, default=None, help="number of seeds")
    q.add_argument("--quick", action="store_true", help="a fast, smaller sweep")
    q.add_argument("--no-bootstrap", action="store_true")
    q.set_defaults(func=cmd_validate)

    q = sub.add_parser("figures", help="save a gallery of example distributions")
    q.add_argument("--out", default="figures")
    q.add_argument("-n", type=int, default=2000)
    q.add_argument("--seed", type=int, default=0)
    q.add_argument("--cases", nargs="+", default=None)
    q.set_defaults(func=cmd_figures)

    q = sub.add_parser(
        "catalogue-figure",
        help="one page of representative ground-truth test distributions",
    )
    q.add_argument("--out", default="figures")
    q.add_argument("-n", type=int, default=2000)
    q.add_argument("--seed", type=int, default=0)
    q.set_defaults(func=cmd_catalogue_figure)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyError as exc:
        print(str(exc).strip('"'), file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
