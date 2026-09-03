"""Where a feature's grid falls back onto lon and lat."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from analysis.coverage.projection.geometry import footprints, geodesy
from analysis.models.feature import Feature

MIN_SPAN_DEG = 0.5
RING_SAMPLES = 17


@dataclass(frozen=True, slots=True)
class Box:
    """One lon/lat box, as a mosaic crop is asked for and drawn over.

    Attributes:
        west: Its western edge in degrees.
        south: Its southern edge in degrees.
        east: Its eastern edge in degrees.
        north: Its northern edge in degrees.
    """

    west: float
    south: float
    east: float
    north: float

    @property
    def extent(self) -> tuple[float, float, float, float]:
        """Return the box as an image extent."""
        return self.west, self.east, self.south, self.north

    @property
    def centre_lat(self) -> float:
        """Return the latitude the box is centred on."""
        return (self.south + self.north) / 2.0


class Placed:
    """Where one feature's grid falls on the mosaic, in lon and lat.

    Attributes:
        side: How many cells the grid holds along each axis.
    """

    def __init__(self, feature: Feature, side: int) -> None:
        """Project one feature and lay its grid back onto lon and lat."""
        region = footprints.feature_region(feature)
        west, south, east, north = region.shape.bounds
        self._centre = (region.centre_lon, region.centre_lat)
        self._west, self._south = west, south
        self._dx = (east - west) / side
        self._dy = (north - south) / side
        self.side = side

    def outline(self) -> tuple[np.ndarray, np.ndarray]:
        """Trace the whole feature as a closed lon/lat ring."""
        right = self._west + self.side * self._dx
        top = self._south + self.side * self._dy
        along = np.linspace(self._west, right, RING_SAMPLES)
        up = np.linspace(self._south, top, RING_SAMPLES)
        flat = np.full(RING_SAMPLES, 0.0)
        lon, lat = geodesy.laea_inverse(
            np.concatenate([along, flat + right, along[::-1], flat + self._west]),
            np.concatenate([flat + self._south, up, flat + top, up[::-1]]),
            *self._centre,
        )
        return self.around(lon), lat

    def around(self, lon: np.ndarray) -> np.ndarray:
        """Bring longitudes onto the same turn as the feature's own."""
        return self._centre[0] + geodesy.normalise_longitude(lon - self._centre[0])

    def box(self) -> Box:
        """Return the lon/lat box the whole grid falls in, held open to a minimum."""
        lon, lat = self.outline()
        centre_lat = float((lat.min() + lat.max()) / 2.0)
        south, north = _floored(float(lat.min()), float(lat.max()), MIN_SPAN_DEG)
        west, east = _floored(
            float(lon.min()),
            float(lon.max()),
            MIN_SPAN_DEG / geodesy.longitude_stretch(centre_lat),
        )
        return Box(west, south, east, north)


def _floored(low: float, high: float, minimum: float) -> tuple[float, float]:
    """Hold a side of a box open to a minimum width, about its middle."""
    if high - low >= minimum:
        return low, high
    centre = (low + high) / 2.0
    return centre - minimum / 2.0, centre + minimum / 2.0
