"""The geological feature both stages are keyed by."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

# A degree of longitude shrinks towards the poles, so a box of fixed ground
_MIN_COSINE = 0.05


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
    def has_latitude_extent(self) -> bool:
        """Return whether the catalogue gives the feature a latitude span.

        Returns:
            True when the maximum latitude is strictly the larger.
        """
        return self.max_lat > self.min_lat

    @property
    def has_longitude_extent(self) -> bool:
        """Return whether the catalogue bounds the feature in longitude.

        Returns:
            True when the west and east longitudes differ.
        """
        return self.west_lon != self.east_lon

    @property
    def is_point(self) -> bool:
        """Return whether the catalogue gives the feature no extent at all.

        Returns:
            True when the feature has neither a latitude nor a longitude span.
        """
        return not self.has_latitude_extent and not self.has_longitude_extent

    @property
    def circles_a_pole(self) -> bool:
        """Return whether the feature runs through every longitude.

        Returns:
            True when the feature has a latitude span but no longitude one.
        """
        return self.has_latitude_extent and not self.has_longitude_extent

    def enlarged(self, radius_deg: float) -> Feature:
        """Return this feature grown to a box of the given half-width.

        Args:
            radius_deg: Half the width of the box to give it, in degrees of latitude.

        Returns:
            A copy carrying the widened box, clamped inside the poles.
        """
        centre_lat = (self.min_lat + self.max_lat) / 2.0
        stretch = max(math.cos(math.radians(centre_lat)), _MIN_COSINE)
        lon_radius = radius_deg / stretch
        return replace(
            self,
            min_lat=max(-90.0, self.min_lat - radius_deg),
            max_lat=min(90.0, self.max_lat + radius_deg),
            west_lon=(self.west_lon - lon_radius) % 360.0,
            east_lon=(self.east_lon + lon_radius) % 360.0,
        )
