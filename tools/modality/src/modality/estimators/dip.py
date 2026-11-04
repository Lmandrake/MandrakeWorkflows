"""Hartigan & Hartigan's dip test -- a binary unimodal / not-unimodal check.

The dip statistic is the largest vertical distance between the empirical CDF
and the closest unimodal (concave-then-convex) CDF.  It answers only
"unimodal, yes or no": it never tells you *how many* modes there are, and it
is not a competitor to the KDE mode counters -- it is a cross-check with a
completely different failure mode, which is exactly what makes it useful here.

The heavy lifting is done by the well-vetted ``diptest`` package (a binding of
Hartigan's original Fortran, which is far better tested than a fresh
implementation would be).  If it is not installed the estimator reports
``available = False`` rather than silently substituting something else.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:  # pragma: no cover - import guard
    import diptest as _diptest

    _AVAILABLE = True
    _IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - import guard
    _diptest = None
    _AVAILABLE = False
    _IMPORT_ERROR = str(exc)


@dataclass
class DipResult:
    available: bool
    statistic: float | None
    p_value: float | None
    alpha: float
    message: str = ""

    @property
    def multimodal(self) -> bool | None:
        """True if unimodality is rejected, False if not, None if unavailable."""
        if not self.available or self.p_value is None:
            return None
        return bool(self.p_value < self.alpha)

    @property
    def modes_lower_bound(self) -> int | None:
        """1 if unimodality holds, 2 (i.e. "at least 2") if it is rejected."""
        m = self.multimodal
        if m is None:
            return None
        return 2 if m else 1

    def __repr__(self) -> str:
        if not self.available:
            return f"DipResult(unavailable: {self.message})"
        return f"DipResult(dip={self.statistic:.5f}, p={self.p_value:.4f}, multimodal={self.multimodal})"


def dip_test(samples: np.ndarray, alpha: float = 0.05) -> DipResult:
    """Run Hartigan's dip test on a 1-D sample."""
    if not _AVAILABLE:
        return DipResult(
            False,
            None,
            None,
            alpha,
            f"the 'diptest' package is not installed ({_IMPORT_ERROR}); "
            "install it with `pip install diptest`",
        )
    x = np.asarray(samples, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 4:
        return DipResult(False, None, None, alpha, "need at least 4 samples")
    stat, pval = _diptest.diptest(x)
    return DipResult(True, float(stat), float(pval), alpha)


def is_available() -> bool:
    return _AVAILABLE
