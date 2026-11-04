"""Gaussian-mixture fitting: component count by BIC/AIC, and modes of the fit.

⚠ **This module answers a different question from the rest of the package.**

``n_components_bic`` estimates how many Gaussian *components* the data are best
described by.  That is the number the owner's examples were reaching for
("a Gaussian plus a broad level region -> modality 2"), and it is a perfectly
good number -- but it is not the number of visible peaks, and the two diverge
whenever components overlap.  It is reported under its own name, never folded
into the visible-mode estimate.

The one place the two meet is :func:`fit_gmm`'s ``modes``: once a mixture has
been fitted we have a closed-form density, so we can count *its* local maxima
exactly with the same machinery used for ground truth.  That turns the GMM into
a genuine visible-mode estimator -- and in practice a rather good one, because
the fit does the smoothing that a KDE bandwidth would otherwise have to.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.mixture import GaussianMixture

from ..distributions import Mixture, Normal
from ..modes import ModeSet, modes_of_mixture


@dataclass
class GMMResult:
    n_components_bic: int
    n_components_aic: int
    bic: dict[int, float]
    aic: dict[int, float]
    fitted: Mixture | None
    modes: ModeSet | None
    max_k: int
    notes: list[str] = field(default_factory=list)

    @property
    def mode_count(self) -> int | None:
        return None if self.modes is None else self.modes.count

    def __repr__(self) -> str:
        return (
            f"GMMResult(components_bic={self.n_components_bic}, "
            f"components_aic={self.n_components_aic}, modes_of_fit={self.mode_count})"
        )


def _to_mixture(gm: GaussianMixture) -> Mixture:
    means = gm.means_.ravel()
    sds = np.sqrt(gm.covariances_.reshape(means.size, -1)[:, 0])
    return Mixture([Normal(float(m), float(s)) for m, s in zip(means, sds)], gm.weights_.ravel())


def fit_gmm(
    samples: np.ndarray,
    max_k: int = 8,
    n_init: int = 5,
    random_state: int = 0,
    min_rel_prominence: float = 0.0,
) -> GMMResult:
    """Fit ``k = 1 .. max_k`` Gaussian mixtures and select by BIC and AIC."""
    x = np.asarray(samples, dtype=float)
    x = x[np.isfinite(x)][:, None]
    n = x.shape[0]
    notes: list[str] = []

    # Each component needs a mean, a variance and a weight; refuse to ask for
    # more components than the sample can conceivably support.
    k_cap = max(1, min(max_k, n // 5))
    if k_cap < max_k:
        notes.append(f"max_k reduced from {max_k} to {k_cap} for n={n}")

    var = float(np.var(x)) if n > 1 else 1.0
    reg = max(1e-10, 1e-6 * var)

    bic: dict[int, float] = {}
    aic: dict[int, float] = {}
    fits: dict[int, GaussianMixture] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        for k in range(1, k_cap + 1):
            gm = GaussianMixture(
                n_components=k,
                covariance_type="full",
                n_init=n_init,
                reg_covar=reg,
                random_state=random_state,
                max_iter=500,
            )
            try:
                gm.fit(x)
            except Exception as exc:  # pragma: no cover - defensive
                notes.append(f"k={k} failed: {exc}")
                continue
            bic[k] = float(gm.bic(x))
            aic[k] = float(gm.aic(x))
            fits[k] = gm

    if not bic:  # pragma: no cover - defensive
        return GMMResult(0, 0, {}, {}, None, None, k_cap, notes + ["all fits failed"])

    k_bic = min(bic, key=bic.get)
    k_aic = min(aic, key=aic.get)
    if k_bic == k_cap and k_cap == max_k:
        notes.append("BIC selected the largest k tried; the true count may be higher")

    mixture = _to_mixture(fits[k_bic])
    modes = modes_of_mixture(mixture, min_rel_prominence=min_rel_prominence)
    return GMMResult(k_bic, k_aic, bic, aic, mixture, modes, k_cap, notes)
