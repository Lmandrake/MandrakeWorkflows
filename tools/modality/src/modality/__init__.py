"""modality -- estimate how multimodal a distribution is.

The primary quantity is the **number of local maxima of the density** (the
classical statistical definition of modality).  The **number of mixture
components** is reported alongside it as a separate, clearly-labelled number,
because the two are different things and disagree more often than people
expect.
"""

from .api import (
    COMPONENT_COUNT,
    UNIMODALITY_TEST,
    VISIBLE_MODES,
    MethodResult,
    ModalityResult,
    estimate_modality,
)
from .distributions import (
    Beta,
    Component,
    Exponential,
    Gamma,
    Mixture,
    Normal,
    StudentT,
    Uniform,
)
from .modes import ModeSet, find_modes_analytic, find_modes_from_grid, modes_of_mixture
from .testcases import TestCase, all_cases, case_names, cases_with_tag, get_case

__version__ = "0.1.0"

__all__ = [
    "estimate_modality",
    "ModalityResult",
    "MethodResult",
    "VISIBLE_MODES",
    "COMPONENT_COUNT",
    "UNIMODALITY_TEST",
    "Mixture",
    "Component",
    "Normal",
    "Uniform",
    "Gamma",
    "Beta",
    "StudentT",
    "Exponential",
    "ModeSet",
    "modes_of_mixture",
    "find_modes_analytic",
    "find_modes_from_grid",
    "TestCase",
    "all_cases",
    "case_names",
    "get_case",
    "cases_with_tag",
    "__version__",
]
