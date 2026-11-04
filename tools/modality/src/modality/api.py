"""The public entry point: :func:`estimate_modality`.

    >>> from modality import estimate_modality
    >>> result = estimate_modality(samples)
    >>> result.visible_modes        # how many peaks the density appears to have
    >>> result.component_count      # how many mixture components BIC prefers
    >>> print(result.report())

``visible_modes`` and ``component_count`` are deliberately two fields.  They
answer different questions and they routinely disagree; see the README.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .estimators.dip import dip_test
from .estimators.gmm import fit_gmm
from .estimators.kde import (
    BinnedKDE,
    scott_bandwidth,
    silverman_bandwidth,
    silverman_sequential_modes,
    stable_mode_count,
)

# Estimated modes below this prominence (as a fraction of the peak density)
# are treated as estimator noise.  See estimate_modality's docstring for the
# sweep that chose the value.
DEFAULT_MIN_PROMINENCE = 0.02

# What each method is actually measuring.  Mixing these up is the single
# easiest way to get a confidently wrong answer out of this package.
VISIBLE_MODES = "visible_modes"
COMPONENT_COUNT = "component_count"
UNIMODALITY_TEST = "unimodality_test"


@dataclass
class MethodResult:
    name: str
    kind: str
    value: int | None
    detail: dict[str, Any] = field(default_factory=dict)
    note: str = ""

    def __repr__(self) -> str:
        return f"MethodResult({self.name}={self.value}, kind={self.kind})"


@dataclass
class ModalityResult:
    """What every estimator said, plus one headline number for each question."""

    n_samples: int
    visible_modes: int
    headline_method: str
    mode_locations: np.ndarray
    component_count: int | None
    methods: dict[str, MethodResult]
    notes: list[str] = field(default_factory=list)

    def value(self, method: str) -> int | None:
        m = self.methods.get(method)
        return None if m is None else m.value

    def report(self) -> str:
        lines = [
            f"n = {self.n_samples} samples",
            "",
            f"VISIBLE MODES (local maxima of the density): {self.visible_modes}",
            f"  headline method: {self.headline_method}",
        ]
        if self.mode_locations.size:
            locs = ", ".join(f"{v:.4g}" for v in self.mode_locations)
            lines.append(f"  estimated at: {locs}")
        if self.component_count is not None:
            lines += [
                "",
                f"MIXTURE COMPONENTS (BIC-selected Gaussian count): {self.component_count}",
                "  NOTE: a different question. Components that overlap enough merge",
                "  into fewer visible peaks than there are components.",
            ]
        lines += ["", "per-method breakdown:"]
        width = max(len(k) for k in self.methods) if self.methods else 10
        for name, m in self.methods.items():
            val = "n/a" if m.value is None else str(m.value)
            lines.append(f"  {name:<{width}}  {val:>4}   [{m.kind}] {m.note}")
        if self.notes:
            lines += ["", "notes:"]
            lines += [f"  - {n}" for n in self.notes]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"ModalityResult(visible_modes={self.visible_modes}, "
            f"component_count={self.component_count}, n={self.n_samples})"
        )


def _headline(methods: dict[str, MethodResult]) -> tuple[int, str, list[str]]:
    """Pick the visible-mode number to lead with.

    The rule was chosen by measurement, not taste: every candidate combination
    was scored against the 44-case catalogue at four sample sizes and five
    seeds (see the README's "How the headline rule was chosen").  The winner:

    ``min(kde_stable, gmm_modes)``, then bumped to 2 if the dip test rejects
    unimodality while the minimum came out at 1.

    Why it works.  The two mode counters fail in *opposite* directions and
    rarely at the same time -- the KDE invents ripples in flat regions, the
    GMM invents Gaussians to paper over non-Gaussian shape -- and both failures
    are over-counts, so the minimum cancels them.  The dip test is then the one
    safe correction: on this catalogue it misclassified a unimodal density as
    multimodal once in 340 runs (99.7% specificity), so "dip says multimodal"
    is close to proof that the answer is not 1, while "dip says unimodal" is
    weak evidence and is deliberately NOT used to push an answer down.
    """
    notes: list[str] = []
    stable = methods["kde_stable"].value or 1
    gmm = methods["gmm_modes"].value
    dip = methods.get("dip")

    value = stable if gmm is None else min(stable, gmm)
    why = "consensus"
    if gmm is not None and gmm != stable:
        notes.append(
            f"kde_stable said {stable} and gmm_modes said {gmm}; taking the "
            "lower, which is the more accurate choice on the validation set"
        )
    if dip is not None and dip.value == 2 and value == 1:
        value = 2
        notes.append(
            f"raised to 2: the dip test rejects unimodality (p={dip.detail['p_value']:.4f}) "
            "and is near-perfectly specific, so a single mode is not credible"
        )
    return value, why, notes


def estimate_modality(
    samples: np.ndarray,
    *,
    n_grid: int = 8192,
    max_components: int = 8,
    min_rel_prominence: float = DEFAULT_MIN_PROMINENCE,
    run_bootstrap: bool = True,
    n_boot: int = 200,
    random_state: int = 0,
) -> ModalityResult:
    """Estimate how multimodal a sample is.

    Parameters
    ----------
    samples
        1-D array of i.i.d. draws.
    min_rel_prominence
        Discard estimated modes whose topographic prominence is below this
        fraction of the peak density.  ``0`` counts every mathematical local
        maximum, which sounds purer but is measurably worse: a KDE puts
        hair-thin ripples on flat regions and in heavy tails, and they are all
        local maxima.  The default of 2% was picked by sweeping the catalogue
        (exact-match rate 0.743 at 0, 0.805 at 1%, 0.822 at 2%, 0.828 at 5%);
        2% takes nearly all of the gain while removing the least real
        structure.
    run_bootstrap
        Run Silverman's smoothed-bootstrap mode test (a calibrated sequential
        test).  It is the slowest method here but still fast; turn it off for
        tight loops.
    """
    x = np.asarray(samples, dtype=float).ravel()
    x = x[np.isfinite(x)]
    n = x.size
    notes: list[str] = []
    if n < 10:
        raise ValueError(f"need at least 10 finite samples, got {n}")
    if n < 50:
        notes.append("n < 50: every method here is unreliable at this sample size")

    methods: dict[str, MethodResult] = {}
    kde = BinnedKDE(x, n_grid=n_grid)

    # --- KDE at the two rules of thumb ----------------------------------
    h_sil = silverman_bandwidth(x)
    h_sco = scott_bandwidth(x)
    ms_sil = kde.modes_at(h_sil)
    ms_sco = kde.modes_at(h_sco)
    methods["kde_silverman"] = MethodResult(
        "kde_silverman", VISIBLE_MODES, ms_sil.count_at(min_rel_prominence),
        {"bandwidth": h_sil, "locations": ms_sil.locations},
        f"h={h_sil:.4g} (robust rule of thumb)",
    )
    methods["kde_scott"] = MethodResult(
        "kde_scott", VISIBLE_MODES, ms_sco.count_at(min_rel_prominence),
        {"bandwidth": h_sco, "locations": ms_sco.locations},
        f"h={h_sco:.4g}",
    )

    # --- KDE bandwidth-stability ----------------------------------------
    stable = stable_mode_count(kde, min_rel_prominence=min_rel_prominence)
    ms_stable = kde.modes_at(np.sqrt(stable.h_low * stable.h_high)).filtered(min_rel_prominence)
    methods["kde_stable"] = MethodResult(
        "kde_stable", VISIBLE_MODES, stable.count,
        {
            "h_low": stable.h_low,
            "h_high": stable.h_high,
            "log_span": stable.log_span,
            "plateaus": stable.plateaus,
            "locations": ms_stable.locations,
        },
        f"widest log-h plateau, h in [{stable.h_low:.3g}, {stable.h_high:.3g}]",
    )

    # --- Silverman critical bandwidth for unimodality --------------------
    h_crit1 = kde.critical_bandwidth(1, min_rel_prominence)
    methods["kde_critical_h1"] = MethodResult(
        "kde_critical_h1", VISIBLE_MODES, None,
        {"h_crit_1": h_crit1, "ratio_to_silverman": h_crit1 / h_sil if h_sil else None},
        f"smallest h giving 1 mode = {h_crit1:.4g} ({h_crit1 / h_sil:.2f}x Silverman)",
    )

    # --- Silverman smoothed bootstrap ------------------------------------
    if run_bootstrap:
        k_boot, pvals = silverman_sequential_modes(
            x, max_k=5, n_boot=n_boot, rng=random_state, n_grid=min(n_grid, 4096)
        )
        methods["silverman_boot"] = MethodResult(
            "silverman_boot", VISIBLE_MODES, k_boot,
            {"p_values": pvals},
            "sequential smoothed-bootstrap test, p=" + ", ".join(f"{p:.3f}" for p in pvals),
        )

    # --- dip test ---------------------------------------------------------
    dip = dip_test(x)
    if dip.available:
        methods["dip"] = MethodResult(
            "dip", UNIMODALITY_TEST, dip.modes_lower_bound,
            {"statistic": dip.statistic, "p_value": dip.p_value},
            f"p={dip.p_value:.4f}; 1 = unimodality not rejected, 2 = 'at least 2'",
        )
    else:
        notes.append(f"dip test unavailable: {dip.message}")

    # --- GMM ---------------------------------------------------------------
    gmm = fit_gmm(
        x, max_k=max_components, random_state=random_state,
        min_rel_prominence=min_rel_prominence,
    )
    methods["gmm_bic"] = MethodResult(
        "gmm_bic", COMPONENT_COUNT, gmm.n_components_bic, {"bic": gmm.bic},
        "components, NOT peaks",
    )
    methods["gmm_aic"] = MethodResult(
        "gmm_aic", COMPONENT_COUNT, gmm.n_components_aic, {"aic": gmm.aic},
        "components, NOT peaks",
    )
    methods["gmm_modes"] = MethodResult(
        "gmm_modes", VISIBLE_MODES, gmm.mode_count,
        {"locations": None if gmm.modes is None else gmm.modes.locations},
        "local maxima of the BIC-selected fitted mixture density",
    )
    notes.extend(gmm.notes)

    value, why, hnotes = _headline(methods)
    notes.extend(hnotes)

    # Report locations from whichever method actually produced the headline
    # count, so the positions and the number always agree.
    locs = None
    for src in ("kde_stable", "gmm_modes"):
        m = methods.get(src)
        if m is not None and m.value == value and m.detail.get("locations") is not None:
            locs = m.detail["locations"]
            break
    if locs is None:
        locs = np.empty(0)
        if value > 0:
            notes.append(
                "no single method produced exactly the headline count, so no mode "
                "locations are reported; see the per-method breakdown"
            )

    return ModalityResult(
        n_samples=n,
        visible_modes=value,
        headline_method=why,
        mode_locations=np.asarray(locs, dtype=float),
        component_count=gmm.n_components_bic,
        methods=methods,
        notes=notes,
    )
