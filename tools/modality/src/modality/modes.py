"""Counting the local maxima of a density.

This module holds the one definition the whole package is built on:

    The **modality** of a distribution is the number of distinct local maxima
    of its density function.

That is the classical statistical definition, and it is deliberately *not* the
number of mixture components -- see the README for why the two differ and why
this one is the estimable quantity.

Two entry points, both reducing to the same core:

``find_modes_analytic``
    Exact.  Used for ground truth (we built the distribution, so we have the
    closed-form derivative) and for the density of a *fitted* Gaussian mixture.
    Works by locating sign changes of ``f'`` and refining them with Brent's
    method, and by treating density jumps (uniform slabs, exponential edges) as
    first-class candidate modes -- the flat top of a step is a visible mode
    even though ``f'`` is never zero there.

``find_modes_from_grid``
    For a density known only on a grid together with its exact derivative on
    the same grid (this is how the FFT-based KDE reports itself).

Both return a :class:`ModeSet` carrying each mode's location, height and
*topographic prominence*, so a caller can discard numerically-real but visually
irrelevant ripples.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np
from scipy.optimize import brentq


@dataclass
class ModeSet:
    """Local maxima of a density, ordered by location."""

    locations: np.ndarray
    heights: np.ndarray
    prominences: np.ndarray
    max_height: float = 0.0
    notes: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        return int(self.locations.size)

    @property
    def count(self) -> int:
        return len(self)

    def filtered(self, min_rel_prominence: float) -> "ModeSet":
        """Drop modes whose prominence is below a fraction of the peak height."""
        if min_rel_prominence <= 0 or len(self) == 0:
            return self
        thr = min_rel_prominence * self.max_height
        keep = self.prominences >= thr
        if not keep.any():
            # A density always has at least one maximum; never filter to zero. Keep exactly
            # one: on a symmetric mixture the peaks tie, and `>= max` would keep them all.
            keep = np.zeros(len(self), dtype=bool)
            keep[int(np.argmax(self.heights))] = True
        return ModeSet(
            self.locations[keep],
            self.heights[keep],
            self.prominences[keep],
            self.max_height,
            list(self.notes),
        )

    def count_at(self, min_rel_prominence: float) -> int:
        return len(self.filtered(min_rel_prominence))

    def __repr__(self) -> str:
        locs = ", ".join(f"{v:.4g}" for v in self.locations)
        return f"ModeSet(count={len(self)}, at=[{locs}])"


# ---------------------------------------------------------------------------
# core: peaks of a value chain
# ---------------------------------------------------------------------------

def _chain_peaks(xs: np.ndarray, vs: np.ndarray, rtol: float = 1e-10) -> ModeSet:
    """Local maxima of a piecewise-monotone value chain.

    ``xs``/``vs`` describe the density as a sequence of knots between which it
    is monotone.  Adjacent entries may share an x (that is how a jump
    discontinuity is represented: the left limit and the right limit).
    Runs of equal values are merged into a single plateau, so a flat-topped
    uniform counts as one mode rather than thousands.
    """
    xs = np.asarray(xs, dtype=float)
    vs = np.asarray(vs, dtype=float)
    if vs.size == 0:
        return ModeSet(np.empty(0), np.empty(0), np.empty(0), 0.0)

    vmax = float(np.max(vs))
    atol = rtol * vmax if vmax > 0 else 0.0

    # --- merge plateaus --------------------------------------------------
    group_val: list[float] = []
    group_lo: list[int] = []
    group_hi: list[int] = []
    for i, v in enumerate(vs):
        if group_val and abs(v - group_val[-1]) <= atol:
            group_hi[-1] = i
            continue
        group_val.append(float(v))
        group_lo.append(i)
        group_hi.append(i)
    u = np.asarray(group_val)
    m = u.size
    if m < 3:
        return ModeSet(np.empty(0), np.empty(0), np.empty(0), vmax)

    peaks = [i for i in range(1, m - 1) if u[i] > u[i - 1] and u[i] > u[i + 1]]
    if not peaks:
        return ModeSet(np.empty(0), np.empty(0), np.empty(0), vmax)

    locs, heights, proms = [], [], []
    for i in peaks:
        h = u[i]
        # topographic prominence: descend either way to the lowest point
        # reached before rising to something at least as tall.
        left_min = h
        j = i - 1
        while j >= 0 and u[j] < h:
            left_min = min(left_min, u[j])
            j -= 1
        right_min = h
        j = i + 1
        while j < m and u[j] < h:
            right_min = min(right_min, u[j])
            j += 1
        proms.append(h - max(left_min, right_min))
        heights.append(h)
        # representative location: middle of the plateau
        lo_i, hi_i = group_lo[i], group_hi[i]
        locs.append(0.5 * (xs[lo_i] + xs[hi_i]))

    order = np.argsort(np.asarray(locs))
    return ModeSet(
        np.asarray(locs)[order],
        np.asarray(heights)[order],
        np.asarray(proms)[order],
        vmax,
    )


# ---------------------------------------------------------------------------
# analytic path
# ---------------------------------------------------------------------------

def _segment_extrema(
    dpdf: Callable[[np.ndarray], np.ndarray],
    pdf: Callable[[np.ndarray], np.ndarray],
    grid: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Interior critical points of a smooth segment, via derivative sign changes."""
    if grid.size < 3:
        return np.empty(0), np.empty(0)
    d = np.asarray(dpdf(grid), dtype=float)
    d = np.where(np.isfinite(d), d, 0.0)
    sign = np.sign(d)
    # Indices where the sign strictly flips between consecutive nonzero signs.
    idx = np.nonzero((sign[:-1] * sign[1:]) < 0)[0]
    roots = []
    for i in idx:
        a, b = grid[i], grid[i + 1]
        try:
            r = brentq(lambda t: float(dpdf(np.array([t]))[0]), a, b, xtol=1e-14, rtol=1e-13)
        except (ValueError, RuntimeError):  # pragma: no cover - defensive
            r = 0.5 * (a + b)
        roots.append(r)
    # Exact zeros of the derivative that sit on a grid node and flank a flip.
    zero_nodes = np.nonzero(sign == 0)[0]
    for i in zero_nodes:
        if 0 < i < grid.size - 1 and sign[i - 1] * sign[i + 1] < 0:
            roots.append(float(grid[i]))
    if not roots:
        return np.empty(0), np.empty(0)
    r = np.unique(np.asarray(roots, dtype=float))
    return r, np.asarray(pdf(r), dtype=float)


def find_modes_analytic(
    pdf: Callable[[np.ndarray], np.ndarray],
    dpdf: Callable[[np.ndarray], np.ndarray],
    lo: float,
    hi: float,
    breakpoints: Sequence[float] = (),
    grid: np.ndarray | None = None,
    n_grid: int = 20001,
) -> ModeSet:
    """Exact local maxima of a density with a closed-form derivative.

    ``breakpoints`` are x-values where the density jumps or kinks; the domain
    is split there, each smooth piece is searched for ``f' = 0``, and the
    one-sided limits at every break are added to the chain so that a step top
    is counted as a mode.
    """
    if grid is None:
        grid = np.linspace(lo, hi, n_grid)
    grid = np.asarray(grid, dtype=float)
    grid = grid[(grid >= lo) & (grid <= hi)]

    knots = sorted({float(b) for b in breakpoints if lo < float(b) < hi})
    edges = [lo, *knots, hi]

    xs: list[float] = [lo]
    vs: list[float] = [0.0]  # padded window: the density is zero at the edges

    for s, e in zip(edges[:-1], edges[1:]):
        width = e - s
        if width <= 0:
            continue
        delta = min(1e-9 * max(abs(s), abs(e), 1.0), 1e-6 * width)
        s_in, e_in = s + delta, e - delta
        if e_in <= s_in:
            continue
        inner = grid[(grid > s_in) & (grid < e_in)]
        seg = np.unique(np.concatenate([[s_in], inner, [e_in]]))
        r, rv = _segment_extrema(dpdf, pdf, seg)
        xs.append(s_in)
        vs.append(float(pdf(np.array([s_in]))[0]))
        for xr, vr in zip(r, rv):
            xs.append(float(xr))
            vs.append(float(vr))
        xs.append(e_in)
        vs.append(float(pdf(np.array([e_in]))[0]))

    xs.append(hi)
    vs.append(0.0)
    return _chain_peaks(np.asarray(xs), np.asarray(vs))


def modes_of_mixture(mixture, min_rel_prominence: float = 0.0) -> ModeSet:
    """Exact modes of a :class:`modality.distributions.Mixture`."""
    lo, hi = mixture.effective_range()
    ms = find_modes_analytic(
        mixture.pdf,
        mixture.dpdf,
        lo,
        hi,
        breakpoints=mixture.breakpoints,
        grid=mixture.search_grid(),
    )
    return ms.filtered(min_rel_prominence)


# ---------------------------------------------------------------------------
# grid path
# ---------------------------------------------------------------------------

def find_modes_from_grid(x: np.ndarray, f: np.ndarray, df: np.ndarray) -> ModeSet:
    """Local maxima of a density sampled on a grid together with its derivative.

    Peaks are located by zero-crossings of ``df`` (linearly interpolated), not
    by comparing neighbouring values of ``f`` -- that removes the grid
    quantisation artefacts a naive ``f[i-1] < f[i] > f[i+1]`` test suffers from
    and gives sub-grid mode locations.
    """
    x = np.asarray(x, dtype=float)
    f = np.asarray(f, dtype=float)
    df = np.asarray(df, dtype=float)
    if x.size < 3:
        return ModeSet(np.empty(0), np.empty(0), np.empty(0), float(f.max() if f.size else 0.0))

    s = np.sign(df)
    idx = np.nonzero(s[:-1] * s[1:] < 0)[0]

    xs = [float(x[0])]
    vs = [float(f[0])]
    for i in idx:
        d0, d1 = df[i], df[i + 1]
        t = d0 / (d0 - d1) if (d0 - d1) != 0 else 0.5
        xr = float(x[i] + t * (x[i + 1] - x[i]))
        vr = float(f[i] + t * (f[i + 1] - f[i]))
        # quadratic touch-up of the height using the three surrounding samples
        j = i if abs(d0) < abs(d1) else i + 1
        if 0 < j < x.size - 1:
            y0, y1, y2 = f[j - 1], f[j], f[j + 1]
            denom = y0 - 2 * y1 + y2
            if denom != 0:
                shift = 0.5 * (y0 - y2) / denom
                if abs(shift) <= 1.0:
                    vr = max(vr, float(y1 - 0.25 * (y0 - y2) * shift))
        xs.append(xr)
        vs.append(vr)
    xs.append(float(x[-1]))
    vs.append(float(f[-1]))
    return _chain_peaks(np.asarray(xs), np.asarray(vs))
