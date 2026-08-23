"""Whether one feature belongs in the dataset, and everything behind it."""

from __future__ import annotations

from dataclasses import dataclass

from models.results import Event
from survey import configs
from survey.models.survey import Survey


@dataclass(frozen=True, slots=True)
class Verdict:
    """What the dataset asked of one feature, and what the feature answered.

    Attributes:
        surveys: The window every tile that earned one was given, in the order
            the tiling lays the tiles out. A tile earns a window only when one
            worth keeping was found over it, so these are what the feature
            would put in a dataset.
        tiles: How many tiles the feature was cut into, which is what the ones
            it earned are counted against.
        gridded: Whether any instrument set filled a cell of the feature at
            all, which is the one way a feature can fail before it is
            searched.
        sounders_refused: How many sounder tracks were too small to count. A
            feature whose only tracks were that small holds no window for a
            different reason than one no sounder ever flew over.
        smallest: The smallest look each instrument set left inside a window,
            by set name, least ground first, so that whatever the windows are
            thinnest on comes first. The ground it covers and the pixels it
            landed there are the two floors an observation is asked to clear,
            and one does not follow from the other: a pixel is a quarter of a
            metre across for HiRISE and more than a kilometre for SHARAD.
        refused: How many looks were too small to count inside the windows.
        taken: How many were counted inside them.
        overlaps: How much ground in square kilometres is reached by at least
            that many instrument sets at once, by set count. Empty when no
            tile earned a window.
    """

    surveys: list[Survey]
    tiles: int
    gridded: bool
    sounders_refused: int
    smallest: dict[str, Event]
    refused: int
    taken: int
    overlaps: dict[int, float]

    @property
    def kept(self) -> bool:
        """Report whether the feature belongs in the dataset.

        Returns:
            True when tiles enough earned a window. Nothing else is asked
            here: the search gives a tile a window only when it is worth
            keeping, so counting the tiles that earned one is the whole
            judgment.
        """
        return len(self.surveys) >= configs.MIN_TILES
