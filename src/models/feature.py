"""The geological feature both stages are keyed by."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Feature:
    """A named geological feature with its bounding box.

    Attributes:
        name: The feature name as ODE spells it, for example "Gale".
        feature_class: The feature class, for example "Crater".
        min_lat: The southernmost planetocentric latitude in degrees.
        max_lat: The northernmost planetocentric latitude in degrees.
        west_lon: The westernmost longitude in degrees, 0 to 360.
        east_lon: The easternmost longitude in degrees, 0 to 360.
    """

    name: str
    feature_class: str
    min_lat: float
    max_lat: float
    west_lon: float
    east_lon: float

    @property
    def is_degenerate(self) -> bool:
        """Return whether the bounding box has no positive latitude span.

        ODE rejects any query whose minimum latitude is not strictly less than
        its maximum, so these are skipped before querying.

        Returns:
            True when the latitude span is zero or negative.
        """
        return self.min_lat >= self.max_lat
