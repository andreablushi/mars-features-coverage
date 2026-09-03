"""The search behind the panels on show, run once and shared."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from analysis.coverage.results import SetCoverage
from analysis.sampling import searching
from analysis.sampling.models.study import Study
from analysis.selector import configs as filtering
from analysis.selector.models.filter import Filter

Stretch = tuple[datetime, datetime]

# How many searches are kept, so every panel of a feature shares one.
STUDY_CACHE = 8


_found: dict[tuple, Study] = {}


def studied(
    coverage: Sequence[SetCoverage], criteria: Filter = filtering.FILTER
) -> Study:
    """Search one feature, running it only once however many panels ask.

    Args:
        coverage: The feature's instrument sets, in the order they are drawn.
        criteria: Which instruments a window has to hold, the written filter
            unless a panel asks for a reading of its own.

    Returns:
        What the search found over it.
    """
    # The relaxed reading of the filter is a search of its own, so it is keyed apart
    first = coverage[0].summary
    key = (
        criteria.unfloored,
        first.feature_class,
        first.feature_name,
        tuple(
            (
                instrument.summary.set_key,
                instrument.summary.n_obs,
                instrument.summary.t_last,
                instrument.summary.covered_km2,
                instrument.summary.mask_cells,
            )
            for instrument in coverage
        ),
    )
    if key not in _found:
        if len(_found) >= STUDY_CACHE:
            _found.clear()
        _found[key] = searching.study_feature(coverage, criteria)
    return _found[key]


def open_for(study: Study) -> list[Stretch]:
    """Return the stretch of time the feature's window is open over.

    Args:
        study: What the search found over one feature.

    Returns:
        The one stretch it earned, and nothing at all when it earned none.
    """
    if study.survey is None:
        return []
    return [(study.survey.start, study.survey.end)]
