"""The mosaic under a feature, and where its grid falls back onto it."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import httpx
import numpy as np

from analysis.geometry.region import FeatureRegion
from analysis.utils import geodesy
from models.feature import Feature
from storage import catalog
from utils.disk.slugify import slugify

# The global mosaic a feature is drawn on, served as WMS by the USGS.
BASEMAP_URL = "https://planetarymaps.usgs.gov/cgi-bin/mapserv"
BASEMAP_MAP = "/maps/mars/mars_simp_cyl.map"
BASEMAP_LAYER = "THEMIS"
BASEMAP_PIXELS = 900
BASEMAP_TIMEOUT = 30.0
BASEMAP_FAILED = "The basemap could not be fetched: {reason}"
BASEMAP_LOADING = "Fetching the basemap..."
BASEMAP_CACHE = 32

# The least ground a side of the crop covers, however thin the box is.
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
    def bounds(self) -> tuple[float, float, float, float]:
        """Return the box as the service and the axes want it.

        Returns:
            The west, south, east, and north edges.
        """
        return self.west, self.south, self.east, self.north

    @property
    def extent(self) -> tuple[float, float, float, float]:
        """Return the box as an image extent.

        Returns:
            The west, east, south, and north edges.
        """
        return self.west, self.east, self.south, self.north


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
        x = np.concatenate([along, flat + right, along[::-1], flat + left])
        y = np.concatenate([flat + bottom, up, flat + top, up[::-1]])
        return self.lonlat(x, y)

    def tile(self, row: int, column: int) -> tuple[np.ndarray, np.ndarray]:
        """Trace one tile of the feature as a closed lon/lat ring.

        Args:
            row: Its row, counting north from the south edge.
            column: Its column, counting east from the west edge.

        Returns:
            The ring longitudes and latitudes.
        """
        return self.ring(column * self.wide, row * self.wide, self.wide, self.wide)

    def lonlat(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Turn projected metres back into lon and lat.

        Args:
            x: The eastings in metres.
            y: The northings in metres.

        Returns:
            The longitudes and latitudes in degrees, kept contiguous around the centre.
        """
        lon, lat = geodesy.laea_inverse(x, y, *self._centre)
        return self.around(lon), lat

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

    @property
    def drawable(self) -> bool:
        """Report whether the grid can be drawn on a plate carree mosaic.

        Returns:
            False for a feature wrapping the planet, whose grid has no box to crop to.
        """
        lon, _ = self.ring(0, 0, self.side, self.side)
        return bool(lon.max() - lon.min() <= HALF_TURN_DEG)

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
    return grid if grid.drawable else None


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


def _pixels(box: Box) -> tuple[int, int]:
    """Return the image size to ask for so the crop is not stretched.

    Args:
        box: The lon/lat box to draw.

    Returns:
        The width and height in pixels, neither below one.
    """
    tall = box.north - box.south
    wide = (box.east - box.west) * geodesy.longitude_stretch(
        (box.south + box.north) / 2.0
    )
    longest = max(wide, tall)
    return (
        max(1, round(BASEMAP_PIXELS * wide / longest)),
        max(1, round(BASEMAP_PIXELS * tall / longest)),
    )


def crop(box: Box) -> bytes:
    """Fetch the mosaic over one lon/lat box.

    Args:
        box: The box to draw.

    Returns:
        The image as PNG bytes.
    """
    return _fetch(box.bounds, _pixels(box))


@lru_cache(maxsize=BASEMAP_CACHE)
def _fetch(window: tuple[float, float, float, float], size: tuple[int, int]) -> bytes:
    """Fetch one basemap view.

    Args:
        window: The west, south, east, and north bounds to draw.
        size: The width and height to draw them at, in pixels.

    Returns:
        The image as PNG bytes.

    Raises:
        ValueError: When the service answers with anything but an image.
    """
    response = httpx.get(
        BASEMAP_URL,
        params={
            "map": BASEMAP_MAP,
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetMap",
            "LAYERS": BASEMAP_LAYER,
            "STYLES": "",
            "SRS": "EPSG:4326",
            "BBOX": ",".join(f"{bound:.4f}" for bound in window),
            "WIDTH": size[0],
            "HEIGHT": size[1],
            "FORMAT": "image/png",
        },
        timeout=BASEMAP_TIMEOUT,
        follow_redirects=True,
    )
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("image/"):
        raise ValueError(response.text.strip()[:200])
    return response.content


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
