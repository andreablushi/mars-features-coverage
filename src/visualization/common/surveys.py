"""The search behind the panels on show, run once and shared."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from models.results import SetCoverage
from survey import strategies, studying
from survey.models.strategy import Strategy
from survey.models.study import Study
from survey.models.survey import Survey

Stretch = tuple[datetime, datetime]

# The strategy a picker opens on. The search is never configured with one, it
# is told, so the choice of what to show first belongs here.
DEFAULT_STRATEGY = "default"

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
        _found[key] = studying.study(coverage, strategy)
    return _found[key]


def opening() -> Strategy:
    """Return the strategy a picker opens on.

    Returns:
        The named one where it is still written, and otherwise the first of
        those that are.
    """
    if DEFAULT_STRATEGY in strategies.STRATEGIES:
        return strategies.STRATEGIES[DEFAULT_STRATEGY]
    return next(iter(strategies.STRATEGIES.values()))


def stretches(found: Sequence[Survey]) -> list[Stretch]:
    """Merge the windows the tiles earned into the time they are open over.

    Two tiles surveyed in the same season hold two windows over one stretch of
    time, and an observation taken then belongs to the dataset once, not
    twice.

    Args:
        found: The windows the tiles earned, in any order.

    Returns:
        The stretches of time at least one window is open over, earliest
        first, none of them touching another, and nothing at all when no tile
        earned a window.
    """
    if not found:
        return []
    ordered = sorted((survey.start, survey.end) for survey in found)
    merged: list[Stretch] = [ordered[0]]
    for opened, closed in ordered[1:]:
        held = merged[-1]
        if opened <= held[1]:
            merged[-1] = (held[0], max(held[1], closed))
        else:
            merged.append((opened, closed))
    return merged


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
