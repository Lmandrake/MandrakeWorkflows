"""The analytic densities and derivatives must actually be right.

Everything downstream -- the ground truth, and therefore every accuracy number
in the validation report -- rests on these, so they are checked against scipy
and against high-accuracy numerical differentiation rather than trusted.
"""

import numpy as np
import pytest
from scipy.integrate import quad

from modality.distributions import (
    Beta,
    Exponential,
    Gamma,
    Mixture,
    Normal,
    StudentT,
    Uniform,
)

COMPONENTS = [
    Normal(0.0, 1.0),
    Normal(-3.5, 2.25),
    Uniform(-1.0, 4.0),
    Gamma(3.0, 1.5),
    Gamma(2.0, 0.5, loc=2.0),
    Beta(2.0, 5.0),
    Beta(3.0, 3.0, loc=-1.0, width=4.0),
    StudentT(3.0),
    StudentT(7.0, 2.0, 0.5),
    Exponential(2.0),
    Exponential(0.5, loc=1.0),
]


@pytest.mark.parametrize("comp", COMPONENTS, ids=lambda c: c.describe())
def test_pdf_matches_scipy(comp):
    lo, hi = comp.quantile_range(1e-4)
    x = np.linspace(lo, hi, 501)
    np.testing.assert_allclose(comp.pdf(x), comp.frozen().pdf(x), rtol=1e-10, atol=1e-12)


@pytest.mark.parametrize("comp", COMPONENTS, ids=lambda c: c.describe())
def test_dpdf_matches_numerical_derivative(comp):
    """Central differences on a wide interior stencil, away from any edge."""
    lo, hi = comp.quantile_range(1e-3)
    span = hi - lo
    x = np.linspace(lo + 0.05 * span, hi - 0.05 * span, 201)
    eps = 1e-6 * span
    num = (comp.pdf(x + eps) - comp.pdf(x - eps)) / (2 * eps)
    ana = comp.dpdf(x)
    scale = max(np.abs(ana).max(), 1e-12)
    np.testing.assert_allclose(ana, num, atol=1e-5 * scale, rtol=1e-4)


@pytest.mark.parametrize("comp", COMPONENTS, ids=lambda c: c.describe())
def test_pdf_integrates_to_one(comp):
    lo, hi = comp.quantile_range(1e-12)
    total, _ = quad(lambda t: float(comp.pdf(np.array([t]))[0]), lo, hi, limit=400)
    assert total == pytest.approx(1.0, abs=1e-6)


def test_mixture_pdf_and_dpdf_are_weighted_sums():
    m = Mixture([Normal(0, 1), Uniform(-2, 5), Gamma(3, 1)], [0.5, 0.2, 0.3])
    x = np.linspace(-6, 12, 401)
    expected = sum(w * c.pdf(x) for w, c in zip(m.weights, m.components))
    np.testing.assert_allclose(m.pdf(x), expected, rtol=1e-12)
    expected_d = sum(w * c.dpdf(x) for w, c in zip(m.weights, m.components))
    np.testing.assert_allclose(m.dpdf(x), expected_d, rtol=1e-12)


def test_mixture_integrates_to_one():
    m = Mixture([Normal(0, 1), Normal(6, 2), Uniform(-4, 10)], [0.4, 0.4, 0.2])
    lo, hi = m.effective_range(eps=1e-14)
    total, _ = quad(lambda t: float(m.pdf(np.array([t]))[0]), lo, hi, limit=600)
    assert total == pytest.approx(1.0, abs=1e-6)


def test_weights_are_normalised():
    m = Mixture([Normal(0, 1), Normal(5, 1)], [3.0, 1.0])
    np.testing.assert_allclose(m.weights, [0.75, 0.25])


def test_sampling_reproduces_moments():
    m = Mixture([Normal(0, 1), Normal(10, 1)], [0.5, 0.5])
    x = m.rvs(200_000, 12345)
    assert x.size == 200_000
    assert x.mean() == pytest.approx(5.0, abs=0.05)
    # variance of the mixture = E[var] + var[E] = 1 + 25
    assert x.var() == pytest.approx(26.0, rel=0.02)


def test_sampling_is_reproducible():
    m = Mixture([Normal(0, 1), Uniform(3, 4)], [0.6, 0.4])
    np.testing.assert_array_equal(m.rvs(500, 7), m.rvs(500, 7))
    assert not np.array_equal(m.rvs(500, 7), m.rvs(500, 8))


def test_breakpoints_are_collected_from_components():
    m = Mixture([Normal(0, 1), Uniform(-2, 5), Exponential(1, loc=3)])
    assert m.breakpoints == (-2.0, 3.0, 5.0)


def test_bad_mixtures_are_rejected():
    with pytest.raises(ValueError):
        Mixture([])
    with pytest.raises(ValueError):
        Mixture([Normal(0, 1)], [0.0])
    with pytest.raises(ValueError):
        Mixture([Normal(0, 1), Normal(1, 1)], [1.0])
    with pytest.raises(ValueError):
        Mixture([Normal(0, 1)], [-1.0])
