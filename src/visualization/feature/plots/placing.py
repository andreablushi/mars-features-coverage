"""Where a feature's grid falls back onto lon and lat, tile by tile."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from coverage.geometry.region import FeatureRegion
from coverage.utils import geodesy
from metadata import catalog
from models.feature import Feature
from utils.disk.slugify import slugify

# The least ground a side of a box covers, however thin the block inside it is.
MIN_SPAN_DEG = 0.5

# How many points an edge is sampled at, since a straight line curves in lon/lat
RING_SAMPLES = 17

# The widest a grid may run in longitude and still crop to a lon/lat box.
HALF_TURN_DEG = 180.0


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
        """Return the box as an image extent.

        Returns:
            The west, east, south, and north edges.
        """
        return self.west, self.east, self.south, self.north

    @property
    def centre_lat(self) -> float:
        """Return the latitude the box is centred on.

        Returns:
            The latitude halfway up it, which its longitudes are stretched about.
        """
        return (self.south + self.north) / 2.0


class Placed:
    """Where one feature's grid falls on the mosaic, in lon and lat.

    Attributes:
        side: How many cells the grid holds along each axis.
        across: How many tiles the grid is cut into along each axis.
        wide: How many cells a tile holds along each axis.
    """

    def __init__(self, feature: Feature, side: int, across: int) -> None:
        """Project one feature and lay its grid back onto lon and lat.

        Args:
            feature: The catalogued feature, carrying the box the grid covers.
            side: How many cells the grid holds along each axis.
            across: How many tiles it is cut into along each axis.

        Returns:
            None.
        """
        region = FeatureRegion(feature)
        west, south, east, north = region.shape.bounds
        self._centre = (region.centre_lon, region.centre_lat)
        self._west, self._south = west, south
        self._dx = (east - west) / side
        self._dy = (north - south) / side
        self.side = side
        self.across = across
        self.wide = side // across if across else side

    def ring(
        self, column: int, row: int, columns: int, rows: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """Trace one block of cells as a closed lon/lat ring.

        Args:
            column: Its westernmost column of cells.
            row: Its southernmost row of cells.
            columns: How many columns it spans.
            rows: How many rows it spans.

        Returns:
            The ring longitudes and latitudes, closed back onto the first point.
        """
        left = self._west + column * self._dx
        right = self._west + (column + columns) * self._dx
        bottom = self._south + row * self._dy
        top = self._south + (row + rows) * self._dy
        along = np.linspace(left, right, RING_SAMPLES)
        up = np.linspace(bottom, top, RING_SAMPLES)
        flat = np.full(RING_SAMPLES, 0.0)
        lon, lat = geodesy.laea_inverse(
            np.concatenate([along, flat + right, along[::-1], flat + left]),
            np.concatenate([flat + bottom, up, flat + top, up[::-1]]),
            *self._centre,
        )
        return self.around(lon), lat

    def tile(self, row: int, column: int) -> tuple[np.ndarray, np.ndarray]:
        """Trace one tile of the feature as a closed lon/lat ring.

        Args:
            row: Its row, counting north from the south edge.
            column: Its column, counting east from the west edge.

        Returns:
            The ring longitudes and latitudes.
        """
        return self.ring(column * self.wide, row * self.wide, self.wide, self.wide)

    def around(self, lon: np.ndarray) -> np.ndarray:
        """Bring longitudes onto the same turn as the feature's own.

        Args:
            lon: The longitudes in degrees, however they are spelled.

        Returns:
            The same longitudes, kept contiguous around the projection centre.
        """
        return self._centre[0] + geodesy.normalise_longitude(lon - self._centre[0])

    def box(self) -> Box:
        """Return the lon/lat box the whole grid falls in.

        Returns:
            The box, held open to a minimum span so a thin feature still reads.
        """
        return _around(*self.ring(0, 0, self.side, self.side))

    def tile_box(self, row: int, column: int) -> Box:
        """Return the lon/lat box one tile falls in.

        Args:
            row: Its row, counting north from the south edge.
            column: Its column, counting east from the west edge.

        Returns:
            The box, held open to a minimum span.
        """
        return _around(*self.tile(row, column))


def placed(feature_class: str, name: str, side: int, across: int) -> Placed | None:
    """Lay one feature's grid back onto the mosaic.

    Args:
        feature_class: The feature class, such as Crater.
        name: The feature name as ODE spells it.
        side: How many cells the grid holds along each axis.
        across: How many tiles it is cut into along each axis.

    Returns:
        The placed grid, or None when it has no box or wraps the planet.
    """
    feature = _catalogue().get((slugify(feature_class), slugify(name)))
    if feature is None:
        return None
    grid = Placed(feature, side, across)
    # A feature wrapping the planet has no lon/lat box a plate carree crop can cover
    lon, _ = grid.ring(0, 0, grid.side, grid.side)
    return grid if lon.max() - lon.min() <= HALF_TURN_DEG else None


def _around(lon: np.ndarray, lat: np.ndarray) -> Box:
    """Return the lon/lat box holding one traced ring.

    Args:
        lon: The ring longitudes.
        lat: The ring latitudes.

    Returns:
        The box, held open to a minimum span so a thin block still reads.
    """
    centre_lat = float((lat.min() + lat.max()) / 2.0)
    south, north = _floored(float(lat.min()), float(lat.max()), MIN_SPAN_DEG)
    west, east = _floored(
        float(lon.min()),
        float(lon.max()),
        MIN_SPAN_DEG / geodesy.longitude_stretch(centre_lat),
    )
    return Box(west, south, east, north)


def _floored(low: float, high: float, minimum: float) -> tuple[float, float]:
    """Hold a side of a box open to a minimum width.

    Args:
        low: The lower bound in degrees.
        high: The upper bound in degrees.
        minimum: The least the side may span.

    Returns:
        The bounds, moved apart about their middle when they fall too close.
    """
    if high - low >= minimum:
        return low, high
    centre = (low + high) / 2.0
    return centre - minimum / 2.0, centre + minimum / 2.0


@lru_cache(maxsize=1)
def _catalogue() -> dict[tuple[str, str], Feature]:
    """Read the feature catalogue once, keyed by the slugs the trees use.

    Returns:
        Every catalogued feature, by class and name slug.
    """
    return {
        (slugify(feature.feature_class), slugify(feature.name)): feature
        for feature in catalog.read_features()
    }
