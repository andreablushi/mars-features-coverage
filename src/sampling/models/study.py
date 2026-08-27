"""Every tile of one feature, searched under one strategy."""

from __future__ import annotations

from dataclasses import dataclass

from selector.models.strategy import Strategy
from selector.models.survey import Survey
from selector.models.tiles import Grid
from selector.models.track import Track


@dataclass(frozen=True, slots=True)
class Study:
    """What the search found over one feature, tile by tile.

    Attributes:
        strategy: What the tiles were asked for.
        grid: The feature cut into tiles, each placed on the grid.
        tracks: The tiles holding anything measurable, each on its own time axis.
        surveys: The window each of those tiles earned, or None where it earned none.
    """

    strategy: Strategy
    grid: Grid
    tracks: list[Track]
    surveys: list[Survey | None]
