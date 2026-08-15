"""The geological feature both stages are keyed by."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

# A degree of longitude shrinks towards the poles, so a box of fixed ground
# width needs more of them; these stop the correction running away at the pole
_MIN_COSINE = 0.05
_MAX_LON_RADIUS_DEG = 180.0


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

        A feature with neither span is a named position rather than an area:
        the classical albedo names, the landing sites, and a few craters ODE
        records by centre alone. There is nothing to measure coverage against
        until one is given a size.

        Returns:
            True when the feature has neither a latitude nor a longitude span.
        """
        return not self.has_latitude_extent and not self.has_longitude_extent

    @property
    def circles_a_pole(self) -> bool:
        """Return whether the feature runs through every longitude.

        The catalogue writes a circumpolar feature with its west and east
        longitudes equal, because there is no meridian at which a ring around
        a pole starts or stops. Read as a box that is what it says, a zero
        width one, which is how the polar caps and Vastitas Borealis came to
        be queried for a strip of ground with no width and to measure nothing.

        Returns:
            True when the feature has a latitude span but no longitude one.
        """
        return self.has_latitude_extent and not self.has_longitude_extent

    def enlarged(self, radius_deg: float) -> Feature:
        """Return this feature grown to a box of the given half-width.

        Args:
            radius_deg: Half the width of the box to give it, in degrees of
                latitude, applied to longitude as the same ground distance.

        Returns:
            A copy carrying the widened box, clamped inside the poles.
        """
        stretch = max(math.cos(math.radians(self.centre_lat)), _MIN_COSINE)
        lon_radius = min(radius_deg / stretch, _MAX_LON_RADIUS_DEG)
        return replace(
            self,
            min_lat=max(-90.0, self.min_lat - radius_deg),
            max_lat=min(90.0, self.max_lat + radius_deg),
            west_lon=(self.west_lon - lon_radius) % 360.0,
            east_lon=(self.east_lon + lon_radius) % 360.0,
        )

    @property
    def centre_lat(self) -> float:
        """Return the latitude the feature's box is centred on.

        Returns:
            The midpoint of the latitude span in degrees.
        """
        return (self.min_lat + self.max_lat) / 2.0
