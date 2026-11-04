"""Analytic 1-D mixture distributions with exact densities and exact derivatives.

Every component here exposes three things the rest of the package relies on:

``pdf(x)``      the exact density,
``dpdf(x)``     the exact *analytic* first derivative of that density,
``breakpoints`` the x-values where the density is discontinuous or non-smooth.

Having ``dpdf`` in closed form is what lets :mod:`modality.modes` compute the
TRUE number of visible modes of a constructed distribution by root-finding on
the derivative, rather than by eyeballing a histogram.

The ``breakpoints`` are what make components with bounded support (uniform,
exponential, gamma, beta) safe to handle: a uniform slab creates a *jump* in
the mixture density, and a jump can itself be a visible mode (the top of a
step).  Any mode-counting scheme that only looks for ``f'(x) = 0`` misses those.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy import stats

_SQRT_2PI = math.sqrt(2.0 * math.pi)


class Component:
    """One component of a mixture.  Subclasses supply exact pdf / dpdf."""

    # --- to be provided by subclasses -----------------------------------
    def pdf(self, x):  # pragma: no cover - abstract
        raise NotImplementedError

    def dpdf(self, x):  # pragma: no cover - abstract
        raise NotImplementedError

    def frozen(self):  # pragma: no cover - abstract
        """A frozen ``scipy.stats`` distribution, used for sampling/quantiles."""
        raise NotImplementedError

    @property
    def support(self) -> tuple[float, float]:  # pragma: no cover - abstract
        raise NotImplementedError

    @property
    def breakpoints(self) -> tuple[float, ...]:
        """x-values where the density is discontinuous or has a kink."""
        return ()

    # --- shared ----------------------------------------------------------
    def rvs(self, size: int, rng: np.random.Generator) -> np.ndarray:
        return np.atleast_1d(self.frozen().rvs(size=size, random_state=rng)).astype(float)

    def quantile_range(self, eps: float = 1e-7) -> tuple[float, float]:
        """A finite interval holding all but ``2*eps`` of this component's mass."""
        d = self.frozen()
        return float(d.ppf(eps)), float(d.ppf(1.0 - eps))

    def describe(self) -> str:
        return repr(self)


@dataclass(frozen=True)
class Normal(Component):
    mu: float = 0.0
    sigma: float = 1.0

    def pdf(self, x):
        z = (np.asarray(x, dtype=float) - self.mu) / self.sigma
        return np.exp(-0.5 * z * z) / (self.sigma * _SQRT_2PI)

    def dpdf(self, x):
        x = np.asarray(x, dtype=float)
        z = (x - self.mu) / self.sigma
        return -(z / self.sigma) * self.pdf(x)

    def frozen(self):
        return stats.norm(loc=self.mu, scale=self.sigma)

    @property
    def support(self):
        return (-math.inf, math.inf)

    def describe(self):
        return f"Normal(mu={self.mu:g}, sigma={self.sigma:g})"


@dataclass(frozen=True)
class Uniform(Component):
    a: float = 0.0
    b: float = 1.0

    def pdf(self, x):
        x = np.asarray(x, dtype=float)
        h = 1.0 / (self.b - self.a)
        return np.where((x >= self.a) & (x <= self.b), h, 0.0)

    def dpdf(self, x):
        # Zero everywhere it is defined; the jumps at a and b are handled as
        # breakpoints rather than as derivative information.
        return np.zeros_like(np.asarray(x, dtype=float))

    def frozen(self):
        return stats.uniform(loc=self.a, scale=self.b - self.a)

    @property
    def support(self):
        return (self.a, self.b)

    @property
    def breakpoints(self):
        return (self.a, self.b)

    def describe(self):
        return f"Uniform(a={self.a:g}, b={self.b:g})"


@dataclass(frozen=True)
class Gamma(Component):
    shape: float = 2.0
    scale: float = 1.0
    loc: float = 0.0

    def pdf(self, x):
        x = np.asarray(x, dtype=float)
        z = (x - self.loc) / self.scale
        out = np.zeros_like(z)
        ok = z > 0
        zk = z[ok]
        log_p = (self.shape - 1.0) * np.log(zk) - zk - math.lgamma(self.shape) - math.log(self.scale)
        out[ok] = np.exp(log_p)
        return out

    def dpdf(self, x):
        x = np.asarray(x, dtype=float)
        z = (x - self.loc) / self.scale
        out = np.zeros_like(z)
        ok = z > 0
        p = self.pdf(x)
        out[ok] = p[ok] * ((self.shape - 1.0) / z[ok] - 1.0) / self.scale
        return out

    def frozen(self):
        return stats.gamma(self.shape, loc=self.loc, scale=self.scale)

    @property
    def support(self):
        return (self.loc, math.inf)

    @property
    def breakpoints(self):
        return (self.loc,)

    def describe(self):
        return f"Gamma(shape={self.shape:g}, scale={self.scale:g}, loc={self.loc:g})"


@dataclass(frozen=True)
class Beta(Component):
    a: float = 2.0
    b: float = 2.0
    loc: float = 0.0
    width: float = 1.0

    def pdf(self, x):
        x = np.asarray(x, dtype=float)
        z = (x - self.loc) / self.width
        out = np.zeros_like(z)
        ok = (z > 0) & (z < 1)
        zk = z[ok]
        log_p = (
            (self.a - 1.0) * np.log(zk)
            + (self.b - 1.0) * np.log1p(-zk)
            - (math.lgamma(self.a) + math.lgamma(self.b) - math.lgamma(self.a + self.b))
            - math.log(self.width)
        )
        out[ok] = np.exp(log_p)
        return out

    def dpdf(self, x):
        x = np.asarray(x, dtype=float)
        z = (x - self.loc) / self.width
        out = np.zeros_like(z)
        ok = (z > 0) & (z < 1)
        p = self.pdf(x)
        zk = z[ok]
        out[ok] = p[ok] * ((self.a - 1.0) / zk - (self.b - 1.0) / (1.0 - zk)) / self.width
        return out

    def frozen(self):
        return stats.beta(self.a, self.b, loc=self.loc, scale=self.width)

    @property
    def support(self):
        return (self.loc, self.loc + self.width)

    @property
    def breakpoints(self):
        return (self.loc, self.loc + self.width)

    def describe(self):
        return f"Beta(a={self.a:g}, b={self.b:g}, loc={self.loc:g}, width={self.width:g})"


@dataclass(frozen=True)
class StudentT(Component):
    df: float = 3.0
    loc: float = 0.0
    scale: float = 1.0

    def pdf(self, x):
        x = np.asarray(x, dtype=float)
        z = (x - self.loc) / self.scale
        nu = self.df
        log_c = (
            math.lgamma((nu + 1.0) / 2.0)
            - math.lgamma(nu / 2.0)
            - 0.5 * math.log(nu * math.pi)
            - math.log(self.scale)
        )
        return np.exp(log_c - ((nu + 1.0) / 2.0) * np.log1p(z * z / nu))

    def dpdf(self, x):
        x = np.asarray(x, dtype=float)
        z = (x - self.loc) / self.scale
        nu = self.df
        return self.pdf(x) * (-(nu + 1.0) * z / (nu + z * z)) / self.scale

    def frozen(self):
        return stats.t(self.df, loc=self.loc, scale=self.scale)

    @property
    def support(self):
        return (-math.inf, math.inf)

    def describe(self):
        return f"StudentT(df={self.df:g}, loc={self.loc:g}, scale={self.scale:g})"


@dataclass(frozen=True)
class Exponential(Component):
    scale: float = 1.0
    loc: float = 0.0

    def pdf(self, x):
        x = np.asarray(x, dtype=float)
        z = (x - self.loc) / self.scale
        return np.where(z >= 0, np.exp(-np.clip(z, 0, None)) / self.scale, 0.0)

    def dpdf(self, x):
        x = np.asarray(x, dtype=float)
        z = (x - self.loc) / self.scale
        return np.where(z > 0, -self.pdf(x) / self.scale, 0.0)

    def frozen(self):
        return stats.expon(loc=self.loc, scale=self.scale)

    @property
    def support(self):
        return (self.loc, math.inf)

    @property
    def breakpoints(self):
        return (self.loc,)

    def describe(self):
        return f"Exponential(scale={self.scale:g}, loc={self.loc:g})"


class Mixture:
    """A weighted mixture of :class:`Component` objects.

    ``pdf`` and ``dpdf`` are the exact weighted sums, so the mixture is itself
    an analytically differentiable density.  ``n_components`` is the *raw
    component count* -- deliberately kept separate from the number of visible
    modes, which is computed in :mod:`modality.modes`.
    """

    def __init__(self, components: Sequence[Component], weights: Sequence[float] | None = None):
        if not components:
            raise ValueError("a mixture needs at least one component")
        self.components = list(components)
        if weights is None:
            weights = [1.0] * len(self.components)
        w = np.asarray(weights, dtype=float)
        if w.shape != (len(self.components),):
            raise ValueError("weights must match components")
        if np.any(w < 0):
            raise ValueError("weights must be non-negative")
        total = w.sum()
        if total <= 0:
            raise ValueError("weights must sum to a positive number")
        self.weights = w / total

    # --- density ---------------------------------------------------------
    def pdf(self, x) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        out = np.zeros(x.shape, dtype=float)
        for w, c in zip(self.weights, self.components):
            out += w * c.pdf(x)
        return out

    def dpdf(self, x) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        out = np.zeros(x.shape, dtype=float)
        for w, c in zip(self.weights, self.components):
            out += w * c.dpdf(x)
        return out

    # --- structure -------------------------------------------------------
    @property
    def n_components(self) -> int:
        return len(self.components)

    @property
    def breakpoints(self) -> tuple[float, ...]:
        pts: set[float] = set()
        for c in self.components:
            pts.update(float(p) for p in c.breakpoints)
        return tuple(sorted(pts))

    def effective_range(self, eps: float = 1e-9, pad: float = 0.05) -> tuple[float, float]:
        """A finite window that contains essentially all of the mass, padded."""
        los, his = [], []
        for c in self.components:
            lo, hi = c.quantile_range(eps)
            los.append(lo)
            his.append(hi)
        lo, hi = min(los), max(his)
        width = hi - lo
        if width <= 0:
            width = 1.0
        return lo - pad * width, hi + pad * width

    def search_grid(self, n_global: int = 20001, n_local: int = 2001) -> np.ndarray:
        """A grid dense enough to resolve every component's own scale.

        A single uniform grid over the whole range can step straight over a
        narrow component sitting in a wide mixture, so the global grid is
        unioned with a local grid around each component.
        """
        lo, hi = self.effective_range()
        grids = [np.linspace(lo, hi, n_global)]
        for c in self.components:
            clo, chi = c.quantile_range(1e-6)
            clo = max(clo, lo)
            chi = min(chi, hi)
            if chi > clo:
                grids.append(np.linspace(clo, chi, n_local))
        g = np.unique(np.concatenate(grids))
        return g[(g >= lo) & (g <= hi)]

    # --- sampling --------------------------------------------------------
    def rvs(self, size: int, rng: np.random.Generator | int | None = None) -> np.ndarray:
        if not isinstance(rng, np.random.Generator):
            rng = np.random.default_rng(rng)
        counts = rng.multinomial(size, self.weights)
        parts = [c.rvs(int(k), rng) for c, k in zip(self.components, counts) if k > 0]
        out = np.concatenate(parts) if parts else np.empty(0)
        rng.shuffle(out)
        return out

    def describe(self) -> str:
        bits = [
            f"{w:.3f} * {c.describe()}" for w, c in zip(self.weights, self.components)
        ]
        return " + ".join(bits)

    def __repr__(self) -> str:
        return f"Mixture({self.describe()})"
