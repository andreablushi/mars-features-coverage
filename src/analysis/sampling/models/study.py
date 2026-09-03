"""One feature, searched under the filter."""

from __future__ import annotations

from dataclasses import dataclass

from analysis.selector.models.filter import Filter
from analysis.selector.models.survey import Survey
from analysis.selector.models.track import Track


@dataclass(frozen=True, slots=True)
class Study:
    """What the search found over one feature.

    Attributes:
        criteria: What the feature was asked for.
        track: Its admissible observations on one time axis, or None where it
            holds nothing measurable.
        survey: The window it earned, or None where it earned none.
    """

    criteria: Filter
    track: Track | None
    survey: Survey | None
