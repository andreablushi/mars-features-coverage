"""The search behind the panels on show, run once and shared."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from coverage.results import SetCoverage
from sampling import searching
from sampling.models.study import Study
from selector import strategies
from selector.models.strategy import Strategy

Stretch = tuple[datetime, datetime]

# The strategy a picker opens on, since a search is told one and never holds one
DEFAULT_STRATEGY = "earth-year"

# How many searches are kept, so every panel of a feature shares one.
STUDY_CACHE = 8


_found: dict[tuple, Study] = {}


def studied(coverage: Sequence[SetCoverage], strategy: Strategy) -> Study:
    """Search one feature, running it only once however many panels ask.

    Args:
        coverage: The feature's instrument sets, in the order they are drawn.
        strategy: Which instruments a window has to hold.

    Returns:
        What the search found over every tile of it.
    """
    key = (strategy.name, _key(coverage))
    if key not in _found:
        if len(_found) >= STUDY_CACHE:
            _found.clear()
        _found[key] = searching.study_feature(coverage, strategy)
    return _found[key]


def opening() -> Strategy:
    """Return the strategy a picker opens on.

    Returns:
        The named one where it is still written, and otherwise the first written.
    """
    if DEFAULT_STRATEGY in strategies.STRATEGIES:
        return strategies.STRATEGIES[DEFAULT_STRATEGY]
    return next(iter(strategies.STRATEGIES.values()))


def _key(coverage: Sequence[SetCoverage]) -> tuple:
    """Name what a search was run over, so the same run is recognised.

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
