"""Kernel-density mode counting, with honest bandwidth handling.

The number of modes a KDE shows is a *function of the bandwidth*, not a
property of the sample: shrink the bandwidth and every sample becomes its own
mode; grow it and everything merges into one.  Any tool that reports "the"
number of KDE modes without saying which bandwidth it used is hiding the
biggest source of variance it has.  So this module offers three answers:

* ``modes_at(h)`` for a bandwidth you name (Silverman's and Scott's
  rules-of-thumb are provided),
* ``critical_bandwidth(k)`` -- Silverman's idea: the smallest bandwidth at
  which the KDE has at most ``k`` modes.  Mode count is monotone
  non-increasing in ``h`` for a Gaussian kernel, which makes this well defined
  and findable by bisection,
* ``stable_mode_count()`` -- scan a range of bandwidths and report the mode
  count that survives the widest interval of ``log h``.  This is the
  "most stable" estimate rather than one bandwidth-dependent number.

Implementation note: the KDE is evaluated by linear binning plus an FFT
convolution, so cost is independent of the sample size and a 60-bandwidth scan
is cheap.  The derivative is obtained by multiplying the same spectrum by
``i*w`` -- it is the *exact* derivative of the binned estimate, not a finite
difference, which is what lets modes be located by derivative zero-crossings
(see :func:`modality.modes.find_modes_from_grid`) instead of by comparing
neighbouring grid values.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..modes import ModeSet, find_modes_from_grid


def silverman_bandwidth(x: np.ndarray) -> float:
    """Silverman's robust rule of thumb: ``0.9 * min(s, IQR/1.349) * n^(-1/5)``."""
    x = np.asarray(x, dtype=float)
    n = x.size
    s = float(np.std(x, ddof=1)) if n > 1 else 1.0
    q75, q25 = np.percentile(x, [75, 25])
    iqr = float(q75 - q25)
    spread = min(s, iqr / 1.349) if iqr > 0 else s
    if spread <= 0:
        spread = s if s > 0 else 1.0
    return 0.9 * spread * n ** (-0.2)


def scott_bandwidth(x: np.ndarray) -> float:
    """Scott's rule: ``s * n^(-1/5)`` (the factor ``scipy``'s KDE calls 'scott')."""
    x = np.asarray(x, dtype=float)
    n = x.size
    s = float(np.std(x, ddof=1)) if n > 1 else 1.0
    if s <= 0:
        s = 1.0
    return s * n ** (-0.2)


class BinnedKDE:
    """A Gaussian KDE evaluated on a fixed grid by FFT, at any bandwidth."""

    def __init__(self, samples: np.ndarray, n_grid: int = 8192, expand: float = 0.3):
        x = np.asarray(samples, dtype=float)
        x = x[np.isfinite(x)]
        if x.size < 2:
            raise ValueError("need at least 2 finite samples")
        self.samples = x
        self.n = x.size

        lo, hi = float(x.min()), float(x.max())
        rng_width = hi - lo
        if rng_width <= 0:
            rng_width = max(abs(lo), 1.0)
        self.lo = lo - expand * rng_width
        self.hi = hi + expand * rng_width

        self.n_grid = int(n_grid)
        self.grid = np.linspace(self.lo, self.hi, self.n_grid)
        self.dx = float(self.grid[1] - self.grid[0])

        # --- linear (Wand) binning: each sample splits between its neighbours
        t = (x - self.lo) / self.dx
        i0 = np.floor(t).astype(int)
        frac = t - i0
        i0 = np.clip(i0, 0, self.n_grid - 2)
        counts = np.zeros(self.n_grid)
        np.add.at(counts, i0, 1.0 - frac)
        np.add.at(counts, i0 + 1, frac)
        self.counts = counts

        # --- zero-padded spectrum (padding prevents circular wrap-around)
        self._L = 2 * self.n_grid
        padded = np.zeros(self._L)
        padded[: self.n_grid] = counts
        self._spec = np.fft.rfft(padded)
        self._w = 2.0 * np.pi * np.fft.rfftfreq(self._L, d=self.dx)

    # --- evaluation ------------------------------------------------------
    def _transfer(self, h: float) -> np.ndarray:
        return np.exp(-0.5 * (self._w * h) ** 2)

    def density(self, h: float) -> np.ndarray:
        g = np.fft.irfft(self._spec * self._transfer(h), n=self._L)[: self.n_grid]
        return np.maximum(g / (self.n * self.dx), 0.0)

    def derivative(self, h: float) -> np.ndarray:
        spec = self._spec * (1j * self._w) * self._transfer(h)
        g = np.fft.irfft(spec, n=self._L)[: self.n_grid]
        return g / (self.n * self.dx)

    def exact_density(self, xq: np.ndarray, h: float) -> np.ndarray:
        """Direct O(n*m) Gaussian KDE -- reference implementation for tests."""
        xq = np.asarray(xq, dtype=float)
        z = (xq[:, None] - self.samples[None, :]) / h
        return np.exp(-0.5 * z * z).sum(axis=1) / (self.n * h * np.sqrt(2 * np.pi))

    # --- modes -----------------------------------------------------------
    def min_sane_bandwidth(self) -> float:
        """Below ~2 grid spacings the binned estimate stops being trustworthy."""
        return 2.0 * self.dx

    def modes_at(self, h: float) -> ModeSet:
        h = max(float(h), self.min_sane_bandwidth())
        return find_modes_from_grid(self.grid, self.density(h), self.derivative(h))

    def n_modes(self, h: float, min_rel_prominence: float = 0.0) -> int:
        return self.modes_at(h).count_at(min_rel_prominence)

    # --- bandwidth selection ---------------------------------------------
    def critical_bandwidth(
        self,
        k: int = 1,
        min_rel_prominence: float = 0.0,
        tol: float = 1e-3,
        max_iter: int = 60,
    ) -> float:
        """Smallest ``h`` whose KDE has at most ``k`` modes (Silverman, 1981)."""
        h_hi = silverman_bandwidth(self.samples)
        if h_hi <= 0:
            h_hi = self.dx * 10
        for _ in range(40):
            if self.n_modes(h_hi, min_rel_prominence) <= k:
                break
            h_hi *= 1.6
        else:  # pragma: no cover - defensive
            return h_hi
        h_lo = max(self.min_sane_bandwidth(), h_hi / 1000.0)
        if self.n_modes(h_lo, min_rel_prominence) <= k:
            return h_lo
        for _ in range(max_iter):
            if (h_hi - h_lo) / h_hi < tol:
                break
            mid = np.sqrt(h_lo * h_hi)
            if self.n_modes(mid, min_rel_prominence) <= k:
                h_hi = mid
            else:
                h_lo = mid
        return float(h_hi)

    # The scan window is anchored on the critical bandwidth for unimodality
    # rather than on a rule of thumb.  h_crit(1) is the point above which the
    # answer is trivially 1 forever, so anchoring there keeps the scan inside
    # the informative part of the staircase; anchoring on Silverman's rule
    # instead hands the count "1" an arbitrarily wide free plateau at the top
    # and costs about 12 accuracy points on the catalogue (0.62 vs 0.74).
    SCAN_LOWER_DIVISOR = 40.0
    SCAN_UPPER_FACTOR = 2.0
    SCAN_POINTS = 60

    def default_bandwidth_grid(self, min_rel_prominence: float = 0.0) -> np.ndarray:
        h_c = self.critical_bandwidth(1, min_rel_prominence)
        lo = max(h_c / self.SCAN_LOWER_DIVISOR, self.min_sane_bandwidth())
        hi = h_c * self.SCAN_UPPER_FACTOR
        if hi <= lo:  # pragma: no cover - degenerate samples
            hi = lo * 10
        return np.logspace(np.log10(lo), np.log10(hi), self.SCAN_POINTS)

    def bandwidth_scan(
        self,
        h_grid: np.ndarray | None = None,
        min_rel_prominence: float = 0.0,
    ) -> tuple[np.ndarray, np.ndarray]:
        if h_grid is None:
            h_grid = self.default_bandwidth_grid(min_rel_prominence)
        h_grid = np.asarray(h_grid, dtype=float)
        counts = np.array([self.n_modes(h, min_rel_prominence) for h in h_grid])
        return h_grid, counts


@dataclass
class StableModeEstimate:
    count: int
    h_low: float
    h_high: float
    log_span: float
    h_grid: np.ndarray
    counts: np.ndarray

    @property
    def plateaus(self) -> dict[int, float]:
        out: dict[int, float] = {}
        logh = np.log(self.h_grid)
        for c in np.unique(self.counts):
            mask = self.counts == c
            out[int(c)] = float(logh[mask].max() - logh[mask].min())
        return out


def stable_mode_count(
    kde: BinnedKDE,
    min_rel_prominence: float = 0.0,
    h_grid: np.ndarray | None = None,
) -> StableModeEstimate:
    """The mode count that survives the widest span of ``log h``.

    Mode count falls monotonically as the bandwidth grows, so the scan is a
    staircase; the widest tread is the count the data supports most robustly.
    Ties go to the smaller count (the more conservative claim).
    """
    h_grid, counts = kde.bandwidth_scan(h_grid, min_rel_prominence)
    logh = np.log(h_grid)

    best_count, best_span, best_lo, best_hi = 1, -1.0, h_grid[0], h_grid[-1]
    # Longest *contiguous* run for each count, measured in log-bandwidth.
    i = 0
    while i < counts.size:
        j = i
        while j + 1 < counts.size and counts[j + 1] == counts[i]:
            j += 1
        span = logh[j] - logh[i]
        c = int(counts[i])
        if span > best_span or (span == best_span and c < best_count):
            best_span, best_count = span, c
            best_lo, best_hi = float(h_grid[i]), float(h_grid[j])
        i = j + 1

    return StableModeEstimate(best_count, best_lo, best_hi, float(best_span), h_grid, counts)


def silverman_bootstrap_test(
    samples: np.ndarray,
    k: int = 1,
    n_boot: int = 200,
    alpha: float = 0.05,
    rng: np.random.Generator | int | None = 0,
    n_grid: int = 4096,
    min_rel_prominence: float = 0.0,
) -> tuple[float, float]:
    """Silverman's smoothed-bootstrap test of "at most k modes".

    Returns ``(p_value, critical_bandwidth)``.  Under H0 the data are
    resampled from the KDE at the critical bandwidth for ``k`` modes (with the
    variance correction of Silverman 1981), and the p-value is the fraction of
    resamples showing *more* than ``k`` modes.  A small p-value is evidence
    against "at most k modes".
    """
    if not isinstance(rng, np.random.Generator):
        rng = np.random.default_rng(rng)
    x = np.asarray(samples, dtype=float)
    n = x.size
    base = BinnedKDE(x, n_grid=n_grid)
    h_c = base.critical_bandwidth(k, min_rel_prominence)

    xbar = x.mean()
    s2 = float(np.var(x, ddof=1))
    scale = 1.0 / np.sqrt(1.0 + h_c * h_c / s2) if s2 > 0 else 1.0

    exceed = 0
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        eps = rng.standard_normal(n)
        y = xbar + scale * (x[idx] - xbar + h_c * eps)
        try:
            bk = BinnedKDE(y, n_grid=n_grid)
        except ValueError:  # pragma: no cover - defensive
            continue
        if bk.n_modes(h_c, min_rel_prominence) > k:
            exceed += 1
    return exceed / max(n_boot, 1), float(h_c)


def silverman_sequential_modes(
    samples: np.ndarray,
    max_k: int = 5,
    n_boot: int = 200,
    alpha: float = 0.05,
    rng: np.random.Generator | int | None = 0,
    n_grid: int = 4096,
) -> tuple[int, list[float]]:
    """Test k = 1, 2, ... and stop at the first k that is not rejected."""
    pvals: list[float] = []
    for k in range(1, max_k + 1):
        p, _ = silverman_bootstrap_test(samples, k=k, n_boot=n_boot, rng=rng, n_grid=n_grid)
        pvals.append(p)
        if p > alpha:
            return k, pvals
    return max_k, pvals
