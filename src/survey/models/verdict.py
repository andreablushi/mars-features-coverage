"""Whether one feature belongs in the dataset, and everything behind it."""

from __future__ import annotations

from dataclasses import dataclass

from models.results import Event
from survey.models.survey import Survey


@dataclass(frozen=True, slots=True)
class Verdict:
    """What the dataset asked of one feature, and what the feature answered.

    Attributes:
        survey: The window the search picked, or None when the feature holds
            no window worth keeping.
        gridded: Whether any instrument set filled a cell of the feature at
            all, which is the one way a feature can fail before it is searched.
        sounders_refused: How many sounder tracks were too small to count. A
            feature whose only tracks were that small has no window for a
            different reason than one no sounder ever flew over.
        smallest: The smallest observation each instrument set left in the
            window, by set name, least ground first, so that whatever the
            window is thinnest on comes first. The ground it covers and the
            pixels it landed there are the two floors an observation is
            asked to clear, and one does not follow from the other: a pixel
            is a quarter of a metre across for HiRISE and more than a
            kilometre for SHARAD. Empty when there is no window.
        refused: How many observations were too small to count, over the
            window when there is one and over the whole record when there is
            not.
        taken: How many were counted over that same stretch.
        overlaps: How much ground in square kilometres is reached by at least
            that many instrument sets at once, by set count. Empty when there
            is no window.
    """

    survey: Survey | None
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
            True when the search found a window, which it only ever does for a
            window the dataset would keep.
        """
        return self.survey is not None
