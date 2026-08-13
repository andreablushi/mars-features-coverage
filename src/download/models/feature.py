"""Geological feature model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    """A named geological feature with its bounding box.

    Attributes:
        name: The feature name (for example "Gale").
        feature_class: The feature class or type (for example "Crater").
        min_lat: Minimum planetocentric latitude in degrees.
        max_lat: Maximum planetocentric latitude in degrees.
        west_lon: Westernmost longitude in degrees, 0 to 360.
        east_lon: Easternmost longitude in degrees, 0 to 360.
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
        its maximum latitude, so degenerate features must be skipped before
        querying.

        Returns:
            True when the latitude span is zero or negative.
        """
        return self.min_lat >= self.max_lat
