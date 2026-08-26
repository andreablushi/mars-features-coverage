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

    @property
    def gridded(self) -> bool:
        """Report whether any instrument set filled a cell of the feature.

        Returns:
            True when the feature was cut into tiles at all.
        """
        return bool(self.grid.tiles)

    @property
    def tiles(self) -> int:
        """Count the tiles holding any of the feature.

        Returns:
            How many of them a window could have been found over.
        """
        return sum(1 for tile in self.grid.tiles if tile.area_km2)

    @property
    def kept(self) -> list[tuple[Track, Survey]]:
        """Pair every tile that earned a window with the window it earned.

        Returns:
            The tiles that earned one, in the order the grid lays them out.
        """
        return [
            (track, picked)
            for track, picked in zip(self.tracks, self.surveys, strict=True)
            if picked is not None
        ]
