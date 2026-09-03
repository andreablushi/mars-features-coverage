"""One feature as the selection left it, and what the instruments left on it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from analysis.selector.models.filter import Filter
from analysis.selector.models.selection import SelectedFeature
from analysis.selector.models.track import Track


@dataclass(frozen=True, slots=True)
class FeatureLooks:
    """One feature's timeline, the window it earned, and the looks it keeps.

    Attributes:
        criteria: The filter as it was read against the feature.
        track: Its admissible observations on one time axis.
        window: The window the selection gave it, or refused it.
        taken: Where the observations it keeps sit on that axis, oldest first.
    """

    criteria: Filter
    track: Track
    window: SelectedFeature
    taken: tuple[int, ...]

    @property
    def open_for(self) -> list[tuple[datetime, datetime]]:
        """Return the stretch of time the feature's window is open over.

        Returns:
            The one stretch it earned, and nothing at all when it earned none.
        """
        if not self.window.kept:
            return []
        return [(self.window.start, self.window.end)]


@dataclass(frozen=True, slots=True)
class InstrumentReach:
    """What one instrument left on one feature inside its window.

    Attributes:
        km2: The ground it reaches, counting a cell once however often it was revisited.
        pixels: The pixels it landed there, or None where any carries no count.
        observations_taken: How many of its observations the window keeps.
    """

    km2: float
    pixels: float | None
    observations_taken: int


@dataclass(frozen=True, slots=True)
class FeatureStats:
    """One feature, and what the looks it keeps left on it.

    Attributes:
        window: The window the selection gave it, carrying its class and name,
            how much ground it covers and how long its window runs.
        iids: The instruments it holds, in the order they are drawn.
        refused: How many looks fell inside the window but were too small for it.
        turned_away: How many looks were too small for the feature at all.
        offered: How many observations of each instrument landed on it at all.
        pixel_km2: The ground one pixel of each instrument covers, read off the
            observations offered to the feature rather than off the ones a window kept.
        reached: What each instrument left on it, by instrument.
        overlaps: The ground each set of instruments reaches, most ground first.
    """

    window: SelectedFeature
    iids: list[str]
    refused: int
    turned_away: int
    offered: dict[str, int]
    pixel_km2: dict[str, float]
    reached: dict[str, InstrumentReach]
    overlaps: dict[tuple[str, ...], float]
