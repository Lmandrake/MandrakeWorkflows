"""A visual sanity-check gallery: true density, sample, KDE and detected modes."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from .api import estimate_modality  # noqa: E402
from .estimators.kde import BinnedKDE, stable_mode_count  # noqa: E402
from .testcases import get_case  # noqa: E402

# A spread that shows the interesting behaviour rather than only the easy wins.
GALLERY = (
    "u_gaussian",
    "g2_sep2",
    "g2_sep2.2",
    "g2_sep4",
    "gu_hidden",
    "gu_adjacent",
    "g2u_prior_hidden",
    "g3_wide",
    "g3_two_merge",
    "g2_spike_on_base",
    "g4_pairs",
    "mix_gauss_expon",
)


# A representative sample of the 44-case catalogue, grouped by the axis each
# row is there to exercise. Four rows x four cases; the rows, not the
# individual cases, are what makes this a sample rather than a highlight reel.
CATALOGUE_ROWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "One component\nthe floor",
        ("u_gaussian", "u_gamma", "u_studentt", "u_uniform"),
    ),
    (
        "Two Gaussians\nthrough the 2$\\sigma$ bifurcation",
        ("g2_sep1", "g2_sep2", "g2_sep2.2", "g2_sep4"),
    ),
    (
        "Components $\\neq$ peaks\nthe divergent cases",
        ("g2_spike_on_base", "gu_hidden", "g2u_prior_hidden", "g4_pairs"),
    ),
    (
        "More structure\nand mixed families",
        ("g3_wide", "g3_two_merge", "mix_gauss_expon", "g2u_prior_visible"),
    ),
)

# Categorical, two levels, colourblind-safe and distinguishable in grayscale by
# lightness. Never the only cue: every panel also states its counts in text.
_TRUE = "#1b3a6b"        # analytic density -- dark blue
_DIVERGE = "#b25a00"     # amber, for cases where component count != peak count
_SAMPLE = "0.86"         # the one visible draw


def plot_catalogue_sample(
    outdir: str | Path = "figures",
    n: int = 2000,
    seed: int = 0,
    rows: Sequence[tuple[str, Sequence[str]]] | None = None,
    filename: str = "catalogue_sample.png",
) -> Path:
    """One page of representative ground-truth distributions.

    Shows the *analytic* density -- the quantity the package is scored
    against -- with the single sampled draw behind it for scale, and the
    exact mode locations marked. No estimator output appears here; this is
    the test set, not the result.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = list(rows) if rows else list(CATALOGUE_ROWS)
    ncol = max(len(names) for _, names in rows)

    fig, axes = plt.subplots(
        len(rows), ncol, figsize=(3.45 * ncol, 2.62 * len(rows))
    )
    axes = np.atleast_2d(axes)

    for r, (row_label, names) in enumerate(rows):
        for c in range(ncol):
            ax = axes[r, c]
            if c >= len(names):
                ax.axis("off")
                continue
            _panel(ax, get_case(names[c]), n=n, seed=seed)
            if c == 0:
                ax.set_ylabel(row_label, fontsize=9, labelpad=8,
                              color="0.15", linespacing=1.4)

    fig.suptitle(
        "What Modality is scored against: a representative sample of the "
        "44-case ground-truth catalogue",
        fontsize=14, y=0.985,
    )
    fig.text(
        0.5, 0.952,
        "Each density is analytic, so its mode count is exact rather than "
        "estimated. Rows walk the axes the catalogue was built to exercise.",
        ha="center", fontsize=9.5, color="0.3",
    )

    handles = [
        Line2D([], [], color=_TRUE, lw=2.2, label="true density (analytic)"),
        Patch(facecolor=_SAMPLE, edgecolor="0.62",
              label=f"one sampled draw, n={n} (seed {seed})"),
        Line2D([], [], color=_TRUE, marker="v", ls="none", ms=8, mec="white",
               mew=0.8, label="exact mode, prominence $\\geq$1% of peak"),
        Line2D([], [], color=_TRUE, marker="v", ls="none", ms=8,
               mfc="white", mew=1.4, label="exact mode, shallower than that"),
        Patch(facecolor="white", edgecolor=_DIVERGE, lw=1.8,
              label="amber frame: components $\\neq$ peaks"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, 0.042))

    fig.text(
        0.5, 0.006,
        "Densities are exact closed-form pdfs; histograms are one simulated "
        "draw per panel. Vertical scale is independent per panel, so peak\n"
        "heights are not comparable across panels; the horizontal window holds "
        "essentially all the mass. Source: modality.testcases "
        "(`modality list-cases`).",
        ha="center", va="bottom", fontsize=8, color="0.38", linespacing=1.5,
    )

    fig.tight_layout(rect=(0.0, 0.082, 1.0, 0.945))
    p = outdir / filename
    fig.savefig(p, dpi=200, facecolor="white")
    plt.close(fig)
    return p


def _panel(ax, case, n: int, seed: int) -> None:
    """One ground-truth distribution: analytic density, draw, exact modes."""
    # eps=1e-4 rather than 1e-6: a Student-t's 1e-6 quantile is at +-107, which
    # would squash every other panel's shape into the axis.
    lo, hi = case.mixture.effective_range(eps=1e-4, pad=0.02)
    grid = np.linspace(lo, hi, 2000)
    truth = case.mixture.pdf(grid)

    x = case.sample(n, seed)
    ax.hist(x, bins=70, range=(lo, hi), density=True, color=_SAMPLE,
            edgecolor="0.62", linewidth=0.3, zorder=1)
    ax.fill_between(grid, truth, color=_TRUE, alpha=0.12, lw=0, zorder=2)
    ax.plot(grid, truth, color=_TRUE, lw=2.2, zorder=3, solid_capstyle="round")

    ms = case.mode_set
    prominent = set(case.mode_set.filtered(0.01).locations.tolist())
    # Markers float a little above their peak rather than sitting on the
    # curve, so they stay readable against the histogram behind them.
    lift = float(truth.max()) * 0.075
    for loc, height in zip(ms.locations, ms.heights):
        shallow = loc not in prominent
        ax.plot([loc], [height + lift], marker="v", ms=8.5, zorder=5,
                color=_TRUE, mfc="white" if shallow else _TRUE,
                mec=_TRUE if shallow else "white", mew=1.4 if shallow else 0.8)

    # The counts in words, so the amber frame is never the only cue.
    peaks = case.true_modes
    vis = case.true_modes_visible
    peak_txt = f"{peaks} peak" + ("" if peaks == 1 else "s")
    if vis != peaks:
        peak_txt += f" ({vis} prominent)"
    ax.set_title(case.name, fontsize=10.5, pad=12, color="0.1")
    ax.text(0.5, 1.012, f"{case.n_components} component"
            f"{'' if case.n_components == 1 else 's'}  →  {peak_txt}",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.6,
            color=_DIVERGE if case.diverges else "0.42",
            fontweight="bold" if case.diverges else "normal")

    if case.diverges:
        for side in ax.spines.values():
            side.set_color(_DIVERGE)
            side.set_linewidth(1.8)
    else:
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("0.7")

    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=8, colors="0.45", length=3)
    ax.margins(x=0)
    ax.set_ylim(0, float(truth.max()) * 1.26)


def plot_case(case_name: str, n: int = 2000, seed: int = 0, ax=None):
    case = get_case(case_name)
    x = case.sample(n, seed)
    res = estimate_modality(x, run_bootstrap=False)

    lo, hi = case.mixture.effective_range(eps=1e-6, pad=0.02)
    grid = np.linspace(lo, hi, 2000)
    truth = case.mixture.pdf(grid)

    kde = BinnedKDE(x)
    stable = stable_mode_count(kde)
    h = float(np.sqrt(stable.h_low * stable.h_high))
    kde_curve = np.interp(grid, kde.grid, kde.density(h))

    own_ax = ax is None
    if own_ax:
        _, ax = plt.subplots(figsize=(7.2, 4.2))

    ax.hist(x, bins=min(80, max(15, n // 25)), range=(lo, hi), density=True,
            color="0.85", edgecolor="0.7", linewidth=0.4, label=f"sample (n={n})")
    ax.plot(grid, truth, color="#1b3a6b", lw=2.0, label="true density")
    ax.plot(grid, kde_curve, color="#c2571a", lw=1.6, ls="--",
            label=f"KDE (h={h:.3g})")

    ms = case.mode_set
    for i, loc in enumerate(ms.locations):
        ax.axvline(loc, color="#1b3a6b", lw=1.0, alpha=0.45, ls=":",
                   label="true mode" if i == 0 else None)
    est = res.mode_locations
    if est.size:
        ax.plot(est, np.interp(est, grid, kde_curve), "v", color="#c2571a",
                ms=9, mec="white", mew=0.8, label="detected mode", zorder=5)

    ok = "OK" if res.visible_modes == case.true_modes else "MISS"
    ax.set_title(
        f"{case.name}  |  truth: {case.n_components} components, "
        f"{case.true_modes} modes  |  estimate: {res.visible_modes} modes "
        f"({ok}), BIC components {res.component_count}",
        fontsize=9.5,
    )
    ax.set_xlabel("x")
    ax.set_ylabel("density")
    ax.legend(fontsize=7.5, framealpha=0.9)
    ax.margins(x=0)
    return ax


def make_gallery(
    outdir: str | Path = "figures",
    n: int = 2000,
    seed: int = 0,
    cases: Sequence[str] | None = None,
) -> list[Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    names = list(cases) if cases else list(GALLERY)

    paths: list[Path] = []
    for name in names:
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        plot_case(name, n=n, seed=seed, ax=ax)
        fig.tight_layout()
        p = outdir / f"{name}.png"
        fig.savefig(p, dpi=130)
        plt.close(fig)
        paths.append(p)

    paths.append(make_bandwidth_figure(outdir, n=n, seed=seed))
    paths.append(make_contact_sheet(outdir, names, n=n, seed=seed))
    return paths


def make_bandwidth_figure(
    outdir: str | Path = "figures",
    cases: Sequence[str] = ("u_gaussian", "g2_sep2.2", "g3_wide", "gu_hidden"),
    n: int = 2000,
    seed: int = 0,
) -> Path:
    """Mode count versus bandwidth -- why "the" KDE mode count is not a number."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for name in cases:
        case = get_case(name)
        kde = BinnedKDE(case.sample(n, seed))
        h, counts = kde.bandwidth_scan()
        st = stable_mode_count(kde)
        (line,) = ax.step(h / st.h_high, counts, where="post", lw=1.8,
                          label=f"{name} (true {case.true_modes}, stable {st.count})")
        ax.axhline(case.true_modes, color=line.get_color(), lw=0.6, alpha=0.35, ls=":")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_yticks([1, 2, 3, 5, 10, 20])
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlabel("bandwidth, relative to the top of the chosen plateau")
    ax.set_ylabel("number of KDE modes")
    ax.set_title("Mode count is a staircase in bandwidth; the widest tread is the estimate",
                 fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    p = outdir / "bandwidth_staircase.png"
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def make_contact_sheet(
    outdir: str | Path,
    names: Sequence[str],
    n: int = 2000,
    seed: int = 0,
) -> Path:
    outdir = Path(outdir)
    ncol = 3
    nrow = (len(names) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(6.0 * ncol, 3.4 * nrow))
    for ax, name in zip(np.ravel(axes), names):
        plot_case(name, n=n, seed=seed, ax=ax)
        ax.legend().set_visible(False)
    for ax in np.ravel(axes)[len(names):]:
        ax.axis("off")
    fig.tight_layout()
    p = outdir / "contact_sheet.png"
    fig.savefig(p, dpi=100)
    plt.close(fig)
    return p
