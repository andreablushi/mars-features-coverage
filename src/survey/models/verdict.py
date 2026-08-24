"""Whether one feature belongs in the dataset, and everything behind it."""

from __future__ import annotations

from dataclasses import dataclass

from survey.models.look import Look
from survey.models.survey import Survey


@dataclass(frozen=True, slots=True)
class Verdict:
    """What the dataset asked of one feature, and what the feature answered.

    Attributes:
        surveys: The window every tile that earned one was given, in the order
            the tiling lays the tiles out. A tile earns a window only when one
            worth keeping was found over it, so these are what the feature
            would put in a dataset.
        across: How many tiles the feature was cut into along each axis, which
            is how they are laid out.
        tiles: How many of those tiles hold any of the feature at all. The grid
            covers the box the feature was projected into, so a tile at a
            corner of it can hold no feature to survey and is no more a failure
            than it is a success.
        gridded: Whether any instrument set filled a cell of the feature at
            all, which is the one way a feature can fail before it is
            searched.
        turned_away: How many looks were too small for the tile they reached,
            counting one once per tile it was turned away from. A feature whose
            looks were all that small holds no window for a different reason
            than one no instrument ever visited.
        smallest: The smallest look each instrument set left inside a window,
            by set name, least ground first, so that whatever the windows are
            thinnest on comes first. Each is measured on the tile its window
            was found over, not over the whole feature. The ground it covers
            and the pixels it landed there are the two floors an observation is
            asked to clear, and one does not follow from the other: a pixel is
            a quarter of a metre across for HiRISE and more than a kilometre
            for SHARAD.
        refused: How many looks were too small to count inside the windows,
            counting an observation once per tile it reached.
        overlaps: How much ground in square kilometres is reached by as many
            instrument sets at once as the strategy makes demands, by that
            count. Empty when no tile earned a window, or when the feature
            holds too few sets to reach the count.
    """

    surveys: list[Survey]
    across: int
    tiles: int
    gridded: bool
    turned_away: int
    smallest: dict[str, Look]
    refused: int
    overlaps: dict[int, float]

    @property
    def taken(self) -> int:
        """Report how many observations the windows hold between them.

        Returns:
            How many the tiles keep in total, counting one once per tile whose
            window holds it, which is what the surveys already say.
        """
        return sum(len(survey.kept) for survey in self.surveys)

    @property
    def kept(self) -> bool:
        """Report whether the feature belongs in the dataset.

        Returns:
            True when any tile earned a window. Nothing else is asked here:
            the search gives a tile a window only when it is worth keeping, so
            a feature that left one anywhere has something to put in a dataset.
        """
        return bool(self.surveys)
