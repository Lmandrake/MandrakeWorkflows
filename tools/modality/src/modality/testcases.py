"""The ground-truth catalogue: realistic 1-D mixtures with known modality.

Each case records *two* truths, and keeping them apart is the whole point of
this package:

``n_components``
    how many pieces the distribution was built from.

``true_modes``
    how many local maxima its density actually has, computed analytically from
    the closed-form derivative (see :mod:`modality.modes`).

The catalogue deliberately walks the separation axis from "obviously two
peaks" through the bifurcation to "one peak made of two components", because
the interesting behaviour of every estimator lives in that transition, not at
the endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

from .distributions import (
    Beta,
    Exponential,
    Gamma,
    Mixture,
    Normal,
    StudentT,
    Uniform,
)
from .modes import ModeSet, modes_of_mixture

# A mode whose prominence is under this fraction of the peak density is a dip
# you would struggle to see in a plot; reported as a secondary truth column.
VISIBLE_PROMINENCE = 0.01


@dataclass
class TestCase:
    name: str
    mixture: Mixture
    description: str
    tags: tuple[str, ...] = ()

    @property
    def n_components(self) -> int:
        return self.mixture.n_components

    @cached_property
    def mode_set(self) -> ModeSet:
        return modes_of_mixture(self.mixture)

    @property
    def true_modes(self) -> int:
        """Exact number of local maxima of the density."""
        return self.mode_set.count

    @property
    def true_modes_visible(self) -> int:
        """Modes surviving a 1%-of-peak-height prominence filter."""
        return self.mode_set.count_at(VISIBLE_PROMINENCE)

    @property
    def diverges(self) -> bool:
        return self.true_modes != self.n_components

    def sample(self, n: int, seed: int = 0):
        return self.mixture.rvs(n, seed)

    def summary(self) -> str:
        return (
            f"{self.name}: components={self.n_components} "
            f"true_modes={self.true_modes} (visible={self.true_modes_visible})\n"
            f"  {self.description}\n  {self.mixture.describe()}"
        )


_CASES: dict[str, TestCase] = {}


def _add(name: str, mixture: Mixture, description: str, *tags: str) -> None:
    if name in _CASES:
        raise ValueError(f"duplicate test case {name!r}")
    _CASES[name] = TestCase(name, mixture, description, tuple(tags))


# ---------------------------------------------------------------------------
# 1 component -- the floor every estimator must not trip over
# ---------------------------------------------------------------------------
_add("u_gaussian", Mixture([Normal(0, 1)]), "A single standard Gaussian.", "unimodal")
_add("u_gamma", Mixture([Gamma(3, 1)]), "A single skewed Gamma(3,1).", "unimodal", "skew")
_add("u_beta", Mixture([Beta(2, 5)]), "A single Beta(2,5) on [0,1]: skewed, bounded.", "unimodal", "bounded")
_add("u_studentt", Mixture([StudentT(3)]), "A single Student-t with 3 df: heavy tails.", "unimodal", "heavy_tail")
_add("u_exponential", Mixture([Exponential(1)]), "A single Exponential: the mode is a boundary jump at 0.", "unimodal", "jump")
_add("u_uniform", Mixture([Uniform(0, 1)]), "A single Uniform: one flat-topped mode, not zero and not infinitely many.", "unimodal", "plateau")

# ---------------------------------------------------------------------------
# 2 Gaussians -- the separation sweep through the d = 2*sigma bifurcation
# ---------------------------------------------------------------------------
for _d in (1.0, 1.5, 2.0, 2.2, 2.5, 3.0, 4.0, 6.0):
    _add(
        f"g2_sep{_d:g}",
        Mixture([Normal(0, 1), Normal(_d, 1)], [0.5, 0.5]),
        f"Two equal unit Gaussians {_d:g} sigma apart. Equal-weight equal-variance "
        "Gaussians are bimodal iff the separation exceeds 2 sigma.",
        "two_gaussian",
        "separation_sweep",
    )

# ---------------------------------------------------------------------------
# 2 Gaussians -- unequal weights and unequal scales
# ---------------------------------------------------------------------------
_add("g2_w10_sep3", Mixture([Normal(0, 1), Normal(3, 1)], [0.9, 0.1]),
     "A dominant Gaussian with a 10% companion 3 sigma away.", "two_gaussian", "unequal_weight")
_add("g2_w25_sep3", Mixture([Normal(0, 1), Normal(3, 1)], [0.75, 0.25]),
     "A 3:1 weight split, 3 sigma apart.", "two_gaussian", "unequal_weight")
_add("g2_w05_sep5", Mixture([Normal(0, 1), Normal(5, 1)], [0.95, 0.05]),
     "A 5% satellite far out: a real but tiny second mode.", "two_gaussian", "unequal_weight")
_add("g2_var_sep3", Mixture([Normal(0, 1), Normal(3, 3)], [0.5, 0.5]),
     "A narrow and a broad Gaussian, centres 3 apart.", "two_gaussian", "unequal_variance")
_add("g2_spike_on_base", Mixture([Normal(0, 4), Normal(0, 0.4)], [0.7, 0.3]),
     "A narrow spike sitting exactly on top of a broad base: two components, "
     "one peak, and nothing about the sample can separate them by position.",
     "two_gaussian", "unequal_variance", "divergence")
_add("g2_bump_on_shoulder", Mixture([Normal(0, 4), Normal(4, 0.5)], [0.8, 0.2]),
     "A small sharp bump on the shoulder of a broad Gaussian.",
     "two_gaussian", "unequal_variance")

# ---------------------------------------------------------------------------
# Gaussian + uniform -- the owner's "Gaussian plus a broad level region"
# ---------------------------------------------------------------------------
_add("gu_hidden", Mixture([Normal(0, 1), Uniform(-6, 6)], [0.85, 0.15]),
     "A Gaussian over a broad low uniform slab. Two components; the slab is "
     "too low to make a second peak, so the density has ONE maximum.",
     "gauss_uniform", "divergence")
_add("gu_wide_low", Mixture([Normal(0, 1), Uniform(-10, 10)], [0.95, 0.05]),
     "The same idea pushed further: a 5% uniform pedestal, invisible as a mode.",
     "gauss_uniform", "divergence")
_add("gu_shoulder", Mixture([Normal(0, 1), Uniform(2, 8)], [0.6, 0.4]),
     "A uniform slab starting on the Gaussian's shoulder: the slab's left edge "
     "is a genuine second (flat-topped) mode.", "gauss_uniform")
_add("gu_adjacent", Mixture([Normal(0, 1), Uniform(4, 10)], [0.5, 0.5]),
     "A clearly separated Gaussian and uniform: two obvious modes, one of them "
     "a plateau rather than a peak.", "gauss_uniform")
_add("gu_tall_slab", Mixture([Normal(0, 3), Uniform(-1, 1)], [0.5, 0.5]),
     "A narrow tall uniform inside a broad Gaussian: one plateau mode.",
     "gauss_uniform", "plateau")

# ---------------------------------------------------------------------------
# Gamma + Gamma -- skewed, bounded-below families
# ---------------------------------------------------------------------------
_add("gam2_far", Mixture([Gamma(4, 1), Gamma(4, 1, loc=12)], [0.5, 0.5]),
     "Two well-separated Gamma(4,1) humps.", "two_gamma")
_add("gam2_close", Mixture([Gamma(4, 1), Gamma(4, 1, loc=3)], [0.5, 0.5]),
     "Two Gamma(4,1) humps only 3 apart: they merge.", "two_gamma")
_add("gam2_mid", Mixture([Gamma(4, 1), Gamma(4, 1, loc=6)], [0.5, 0.5]),
     "Two Gamma(4,1) humps 6 apart: borderline.", "two_gamma")
_add("gam2_skewpair", Mixture([Gamma(6, 0.5), Gamma(2, 2, loc=6)], [0.5, 0.5]),
     "A tight early Gamma and a broad late one.", "two_gamma", "skew")

# ---------------------------------------------------------------------------
# 3 components
# ---------------------------------------------------------------------------
_add("g3_wide", Mixture([Normal(0, 1), Normal(6, 1), Normal(12, 1)], [1 / 3, 1 / 3, 1 / 3]),
     "Three equal Gaussians 6 sigma apart: three obvious modes.", "three_gaussian")
_add("g3_mid", Mixture([Normal(0, 1), Normal(3, 1), Normal(6, 1)], [1 / 3, 1 / 3, 1 / 3]),
     "Three equal Gaussians 3 sigma apart: the pairwise gaps clear 2 sigma but "
     "the middle component is flanked on both sides.", "three_gaussian")
_add("g3_tight", Mixture([Normal(0, 1), Normal(1.5, 1), Normal(3, 1)], [1 / 3, 1 / 3, 1 / 3]),
     "Three equal Gaussians 1.5 sigma apart: fully merged into one hump.",
     "three_gaussian", "divergence")
_add("g3_two_merge", Mixture([Normal(0, 1), Normal(1.2, 1), Normal(8, 1)], [1 / 3, 1 / 3, 1 / 3]),
     "Two Gaussians merge into a single wide hump; a third sits far away. "
     "Three components, two visible modes.", "three_gaussian", "divergence")
_add("g3_uneven", Mixture([Normal(0, 1), Normal(4, 1), Normal(8, 1)], [0.5, 0.3, 0.2]),
     "Three Gaussians at 5:3:2 weights, well separated.", "three_gaussian", "unequal_weight")
_add("g3_unequal_var", Mixture([Normal(0, 0.5), Normal(4, 2), Normal(10, 0.7)], [0.3, 0.5, 0.2]),
     "Three Gaussians with quite different widths.", "three_gaussian", "unequal_variance")

# ---------------------------------------------------------------------------
# The owner's own examples: Gaussians plus a uniform "prior"
# ---------------------------------------------------------------------------
_add("g2u_prior_hidden", Mixture([Normal(0, 1), Normal(6, 1), Uniform(-8, 14)], [0.4, 0.4, 0.2]),
     "Two Gaussians plus a broad uniform prior. The owner's 'modality 3' example: "
     "three components, but the uniform only lifts the floor, so the density has "
     "TWO maxima.", "gauss_uniform", "three_component", "divergence")
_add("g2u_prior_visible", Mixture([Normal(0, 1), Normal(10, 1), Uniform(3.5, 6.5)], [0.35, 0.35, 0.3]),
     "Two Gaussians with a uniform slab between them. A surprise the analytic "
     "truth-finder caught and a histogram would not: the two Gaussian tails sum "
     "to a shape with a minimum inside the slab, so BOTH slab edges are local "
     "maxima and the density has FOUR of them from three components -- though "
     "only two clear a 1%-prominence filter.",
     "gauss_uniform", "three_component", "divergence")
_add("g2u_prior_flank", Mixture([Normal(0, 1), Normal(6, 1), Uniform(10, 14)], [0.35, 0.35, 0.3]),
     "Two Gaussians and a uniform slab off to one side, where only one tail "
     "leans on it: three components, three maxima, the third a plateau edge.",
     "gauss_uniform", "three_component")

# ---------------------------------------------------------------------------
# Mixed families
# ---------------------------------------------------------------------------
_add("mix_norm_t", Mixture([Normal(0, 1), StudentT(2, 0, 3)], [0.7, 0.3]),
     "A Gaussian core with a heavy-tailed Student-t halo: one mode, two "
     "components, and a shape no single Gaussian fits.", "mixed_family", "divergence")
_add("mix_gauss_expon", Mixture([Exponential(2), Normal(8, 1)], [0.4, 0.6]),
     "An exponential decay from zero plus a distant Gaussian: two modes, one of "
     "which is a boundary jump.", "mixed_family", "jump")
_add("mix_beta_gauss", Mixture([Beta(2, 2, 0, 4), Normal(7, 0.8)], [0.5, 0.5]),
     "A bounded Beta hump and a Gaussian.", "mixed_family", "bounded")
_add("mix_trimodal_asym", Mixture([Gamma(3, 1), Normal(9, 1), Normal(14, 0.6)], [0.4, 0.35, 0.25]),
     "Skewed, then two Gaussians: an asymmetric trimodal shape.", "mixed_family", "three_component")

# ---------------------------------------------------------------------------
# 4 components
# ---------------------------------------------------------------------------
_add("g4_wide", Mixture([Normal(0, 1), Normal(5, 1), Normal(10, 1), Normal(15, 1)], [0.25] * 4),
     "Four well-separated Gaussians.", "four_gaussian")
_add("g4_pairs", Mixture([Normal(0, 1), Normal(1, 1), Normal(9, 1), Normal(10, 1)], [0.25] * 4),
     "Two tight pairs far apart: four components, two visible modes.",
     "four_gaussian", "divergence")


# ---------------------------------------------------------------------------
# accessors
# ---------------------------------------------------------------------------

def all_cases() -> list[TestCase]:
    return list(_CASES.values())


def case_names() -> list[str]:
    return list(_CASES)


def get_case(name: str) -> TestCase:
    try:
        return _CASES[name]
    except KeyError:
        raise KeyError(
            f"unknown test case {name!r}; try one of: {', '.join(sorted(_CASES))}"
        ) from None


def cases_with_tag(tag: str) -> list[TestCase]:
    return [c for c in _CASES.values() if tag in c.tags]
