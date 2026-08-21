"""The best time window for the feature on show, found once and shared."""

from __future__ import annotations

from collections.abc import Sequence

from models.results import SetCoverage
from survey.filters import verdict
from survey.models.survey import Survey
from survey.models.verdict import Verdict

# How many searches are kept, so every panel of a feature shares one.
SURVEY_CACHE = 8


_found: dict[tuple, Verdict] = {}


def assessed(coverage: Sequence[SetCoverage]) -> Verdict:
    """Judge one feature, searching it only once however many panels ask.

    Every panel that marks the window or reads the verdict asks for the same
    search, and confirming a feature draws them all, so what it found is kept
    rather than repeated. What a feature is measured against decides it
    entirely, which is the sets on show and what each of them holds.

    Args:
        coverage: The feature's instrument sets, in the order they are drawn.

    Returns:
        The verdict, holding the chosen window and every check behind it.
    """
    key = _key(coverage)
    if key not in _found:
        if len(_found) >= SURVEY_CACHE:
            _found.clear()
        _found[key] = verdict.assess(coverage)
    return _found[key]


def picked(coverage: Sequence[SetCoverage]) -> Survey | None:
    """Return the best window for one feature.

    Args:
        coverage: The feature's instrument sets, in the order they are drawn.

    Returns:
        The chosen window, or None when the feature has none.
    """
    return assessed(coverage).survey


def _key(coverage: Sequence[SetCoverage]) -> tuple:
    """Name what a search was run over, so the same run is recognised.

    The sets are named by what they measured and not by name alone, so a
    feature measured again by a later pipeline is searched again rather than
    answered from what the earlier one produced.

    Args:
        coverage: The feature's instrument sets, in the order they are drawn.

    Returns:
        The feature and what each set holds, as one hashable value.
    """
    first = coverage[0].summary
    measured = tuple(
        (
            instrument.summary.set_key,
            instrument.summary.n_obs,
            instrument.summary.t_last,
            instrument.summary.covered_km2,
            instrument.summary.mask_cells,
        )
        for instrument in coverage
    )
    return (first.feature_class, first.feature_name, measured)
