"""The best time window for the feature on show, found once and shared."""

from __future__ import annotations

from collections.abc import Sequence

from campaign import verdict
from campaign.results import Campaign
from campaign.verdict import Verdict
from models.results import SetCoverage
from visualization import configs
from visualization.selectors.window import Window

_found: dict[tuple, Verdict] = {}


def assessed(coverage: Sequence[SetCoverage], window: Window) -> Verdict:
    """Judge one feature, searching it only once however many panels ask.

    Every panel that marks the window or reads the verdict asks for the same
    search, and confirming a feature draws them all, so what it found is kept
    rather than repeated. What a feature is measured against decides it
    entirely: which sets are on show, and the date range they are limited to.

    Args:
        coverage: The feature's instrument sets, in the order they are drawn.
        window: The date range the panels are shown over.

    Returns:
        The verdict, holding the chosen window and every check behind it.
    """
    key = _key(coverage, window)
    if key not in _found:
        if len(_found) >= configs.CAMPAIGN_CACHE:
            _found.clear()
        _found[key] = verdict.assess(coverage, window.visible)
    return _found[key]


def picked(coverage: Sequence[SetCoverage], window: Window) -> Campaign | None:
    """Return the best window for one feature.

    Args:
        coverage: The feature's instrument sets, in the order they are drawn.
        window: The date range the panels are shown over.

    Returns:
        The chosen window, or None when the feature has none.
    """
    return assessed(coverage, window).campaign


def _key(coverage: Sequence[SetCoverage], window: Window) -> tuple:
    """Name what a search was run over, so the same run is recognised.

    The sets are named by what they measured and not by name alone, so a
    feature measured again by a later pipeline is searched again rather than
    answered from what the earlier one produced.

    Args:
        coverage: The feature's instrument sets, in the order they are drawn.
        window: The date range the panels are shown over.

    Returns:
        The feature, what each set holds, and the range, as one hashable value.
    """
    first = coverage[0].summary
    measured = tuple(
        (
            entry.summary.set_key,
            entry.summary.n_obs,
            entry.summary.t_last,
            entry.summary.covered_km2,
            entry.summary.mask_cells,
        )
        for entry in coverage
    )
    return (first.feature_class, first.feature_name, measured, window.start, window.end)
