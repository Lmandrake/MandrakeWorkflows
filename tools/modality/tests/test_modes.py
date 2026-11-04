"""The ground-truth mode finder, checked against modes that are known in closed form."""

import numpy as np
import pytest

from modality.distributions import (
    Beta,
    Exponential,
    Gamma,
    Mixture,
    Normal,
    StudentT,
    Uniform,
)
from modality.modes import find_modes_from_grid, modes_of_mixture
from modality.testcases import all_cases


@pytest.mark.parametrize(
    "component, expected_mode",
    [
        (Normal(2.5, 1.3), 2.5),
        (StudentT(5.0, -1.0, 2.0), -1.0),
        (Gamma(4.0, 2.0), 6.0),               # mode = (k-1) * scale
        (Gamma(3.0, 1.0, loc=5.0), 7.0),      # ... shifted by loc
        (Beta(3.0, 7.0), 2.0 / 8.0),          # mode = (a-1)/(a+b-2)
        (Beta(4.0, 2.0, loc=1.0, width=6.0), 1.0 + 6.0 * (3.0 / 4.0)),
        (Exponential(2.0, loc=-1.0), -1.0),   # the mode is the boundary jump
    ],
)
def test_single_component_mode_location(component, expected_mode):
    ms = modes_of_mixture(Mixture([component]))
    assert ms.count == 1
    assert ms.locations[0] == pytest.approx(expected_mode, abs=2e-3)


def test_uniform_is_one_flat_mode_not_zero_and_not_many():
    ms = modes_of_mixture(Mixture([Uniform(-3, 7)]))
    assert ms.count == 1
    assert ms.locations[0] == pytest.approx(2.0, abs=1e-6)  # plateau centre


@pytest.mark.parametrize("d", [0.5, 1.0, 1.5, 1.9, 1.99, 2.0])
def test_equal_gaussians_are_unimodal_at_or_below_two_sigma(d):
    """Equal-weight equal-variance Gaussians are bimodal iff separation > 2 sigma."""
    m = Mixture([Normal(0, 1), Normal(d, 1)], [0.5, 0.5])
    assert modes_of_mixture(m).count == 1


@pytest.mark.parametrize("d", [2.01, 2.1, 2.5, 3.0, 5.0, 10.0])
def test_equal_gaussians_are_bimodal_above_two_sigma(d):
    m = Mixture([Normal(0, 1), Normal(d, 1)], [0.5, 0.5])
    ms = modes_of_mixture(m)
    assert ms.count == 2
    # symmetric about the midpoint
    assert ms.locations.mean() == pytest.approx(d / 2, abs=1e-4)


def test_scaling_the_axis_does_not_change_the_bifurcation():
    """The 2-sigma rule is scale free; the finder must be too."""
    for sigma in (0.01, 1.0, 100.0):
        below = Mixture([Normal(0, sigma), Normal(1.9 * sigma, sigma)], [0.5, 0.5])
        above = Mixture([Normal(0, sigma), Normal(2.2 * sigma, sigma)], [0.5, 0.5])
        assert modes_of_mixture(below).count == 1
        assert modes_of_mixture(above).count == 2


def test_a_low_wide_uniform_under_a_gaussian_adds_no_mode():
    m = Mixture([Normal(0, 1), Uniform(-6, 6)], [0.85, 0.15])
    assert m.n_components == 2
    assert modes_of_mixture(m).count == 1


def test_a_uniform_edge_can_itself_be_a_mode():
    """A step top is visible even though f' is never zero on it."""
    m = Mixture([Normal(0, 1), Uniform(4, 10)], [0.5, 0.5])
    ms = modes_of_mixture(m)
    assert ms.count == 2
    assert ms.locations[1] == pytest.approx(4.0, abs=1e-3)


def test_well_separated_gaussians_give_one_mode_each():
    for k in range(1, 6):
        m = Mixture([Normal(8.0 * i, 1.0) for i in range(k)])
        assert modes_of_mixture(m).count == k


def test_prominence_filter_drops_shallow_dips():
    m = Mixture([Normal(0, 1), Normal(2.05, 1)], [0.5, 0.5])
    ms = modes_of_mixture(m)
    assert ms.count == 2                      # mathematically two maxima
    assert ms.count_at(0.01) == 1             # but the dip is invisible


def test_grid_mode_finder_agrees_with_the_analytic_one():
    m = Mixture([Normal(0, 1), Normal(5, 1), Normal(11, 2)], [0.4, 0.3, 0.3])
    lo, hi = m.effective_range()
    x = np.linspace(lo, hi, 40001)
    grid_modes = find_modes_from_grid(x, m.pdf(x), m.dpdf(x))
    exact = modes_of_mixture(m)
    assert grid_modes.count == exact.count == 3
    np.testing.assert_allclose(grid_modes.locations, exact.locations, atol=1e-3)


def test_every_catalogue_case_has_at_least_one_mode():
    for c in all_cases():
        assert c.true_modes >= 1, c.name
        assert c.true_modes_visible >= 1, c.name
        assert c.true_modes_visible <= c.true_modes, c.name


def test_catalogue_truth_is_stable_across_grid_refinement():
    """A truth that moves when the grid changes is not a truth."""
    from modality.modes import find_modes_analytic

    for c in all_cases():
        lo, hi = c.mixture.effective_range()
        fine = find_modes_analytic(
            c.mixture.pdf, c.mixture.dpdf, lo, hi,
            breakpoints=c.mixture.breakpoints,
            grid=c.mixture.search_grid(n_global=60003, n_local=6001),
        )
        assert fine.count == c.true_modes, c.name
