"""One feature, searched under one strategy."""

from __future__ import annotations

from dataclasses import dataclass

from analysis.selector.models.grid import Grid
from analysis.selector.models.strategy import Strategy
from analysis.selector.models.survey import Survey
from analysis.selector.models.track import Track


@dataclass(frozen=True, slots=True)
class Study:
    """What the search found over one feature.

    Attributes:
        strategy: What the feature was asked for.
        grid: The grid it was searched over.
        track: Its admissible observations on one time axis, or None where it
            holds nothing measurable.
        survey: The window it earned, or None where it earned none.
    """

    strategy: Strategy
    grid: Grid
    track: Track | None
    survey: Survey | None
