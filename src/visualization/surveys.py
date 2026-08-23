"""The best time window for the feature on show, found once and shared."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from models.results import SetCoverage
from survey import configs, strategies
from survey.filters import verdict
from survey.models.strategy import Strategy
from survey.models.survey import Survey
from survey.models.verdict import Verdict

Stretch = tuple[datetime, datetime]

# How many searches are kept, so every panel of a feature shares one. A
# feature is searched once per strategy the comparison draws, so the cache
# holds a few features over as many strategies as there are.
SURVEY_CACHE = 24


_found: dict[tuple, Verdict] = {}


def assessed(
    coverage: Sequence[SetCoverage], strategy: Strategy | None = None
) -> Verdict:
    """Judge one feature, searching it only once however many panels ask.

    Every panel that marks a window or reads the verdict asks for the same
    search, and confirming a feature draws them all, so what it found is kept
    rather than repeated. What a feature is measured against decides it
    entirely, which is the sets on show, what each of them holds, and what the
    strategy asks of them.

    Args:
        coverage: The feature's instrument sets, in the order they are drawn.
        strategy: Which instruments a window has to hold, or None for the
            configured one.

    Returns:
        The verdict, holding the window every tile earned and every check
        behind them.
    """
    strategy = strategy or strategies.named(configs.STRATEGY)
    key = (strategy.name, _key(coverage))
    if key not in _found:
        if len(_found) >= SURVEY_CACHE:
            _found.clear()
        _found[key] = verdict.assess(coverage, strategy)
    return _found[key]


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
