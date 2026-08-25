"""The footprints as ODE published them, read back off the downloaded metadata."""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import lru_cache

import numpy as np
from shapely import affinity
from shapely import wkt as reading
from shapely.geometry.base import BaseGeometry

import utils.disk.paths as paths
from analysis import configs
from analysis.utils import geodesy
from models.instrument import InstrumentSet
from models.results import SetCoverage
from storage.records import load_set
from utils.disk.slugify import slugify

# How many features' footprints are kept, so a tile of one already read draws
# without touching the disk again.
OUTLINE_CACHE = 4

# How much ground a degree of latitude covers, in kilometres.
DEGREE_KM = math.radians(configs.MARS_RADIUS_M) / 1000.0

Trace = tuple[np.ndarray, np.ndarray]


def read(coverage: Sequence[SetCoverage]) -> dict[str, BaseGeometry]:
    """Read the published footprint of every observation of one feature.

    The coverage artifacts carry the cells a footprint fills and not its
    outline, so the outline is read back off the metadata the download left.

    Args:
        coverage: The feature's instrument sets, in any order.

    Returns:
        The footprint of each observation, by product id, and nothing at all
        for a set whose metadata is no longer on disk.
    """
    summary = coverage[0].summary
    found: dict[str, BaseGeometry] = {}
    for instrument in coverage:
        found.update(
            _published(
                summary.feature_class, summary.feature_name, instrument.summary.set_key
            )
        )
    return found


@lru_cache(maxsize=OUTLINE_CACHE)
def _published(feature_class: str, name: str, set_key: str) -> dict[str, BaseGeometry]:
    """Read one instrument set's published footprints.

    Args:
        feature_class: The feature class, such as Crater.
        name: The feature name as ODE spells it.
        set_key: The instrument set the records were asked for by.

    Returns:
        The footprint of each of its observations, by product id, and nothing
        at all when its metadata is no longer on disk.
    """
    path = (
        paths.METADATA_ROOT
        / slugify(feature_class)
        / slugify(name)
        / f"{InstrumentSet.from_key(set_key).slug}.jsonl"
    )
    if not path.exists() or not path.stat().st_size:
        return {}
    return {
        observation.pdsid: reading.loads(observation.wkt)
        for observation in load_set(path).observations
    }


def traced(shape: BaseGeometry, width_km: float | None = None) -> list[Trace]:
    """Trace one published footprint as the rings a panel can fill.

    A sounder publishes the ground track it flew and no width at all, so its
    track is widened to the swath the measurement read it at. Drawing the bare
    line instead would show no ground where the measurement counted a swath of
    it, and the map would disagree with every share it is put beside.

    Args:
        shape: The footprint as published.
        width_km: The swath the measurement widened the track to, or None for
            a footprint that came with area of its own.

    Returns:
        The longitudes and latitudes of each ring it is drawn as, and nothing
        at all for a footprint carrying no line, such as a bare point.
    """
    drawn: list[Trace] = []
    for part in getattr(shape, "geoms", [shape]):
        ring = getattr(part, "exterior", None)
        if ring is None and width_km:
            part = _widened(part, width_km)
            ring = getattr(part, "exterior", None)
        line = ring if ring is not None else part
        coordinates = np.asarray(line.coords, dtype=float)
        if coordinates.shape[0] > 1:
            drawn.append((coordinates[:, 0], coordinates[:, 1]))
    return drawn


def _widened(line: BaseGeometry, width_km: float) -> BaseGeometry:
    """Widen one ground track to the swath the measurement read it at.

    A degree of longitude covers less ground than a degree of latitude, so the
    track is stretched onto one scale before it is buffered and put back
    after, or the swath would come out wider than it is.

    Args:
        line: The track as published, in lon and lat degrees.
        width_km: How wide the swath is, in kilometres.

    Returns:
        The swath as a shape, or the track itself when it holds no point to
        widen.
    """
    coordinates = np.asarray(line.coords, dtype=float)
    if not coordinates.size:
        return line
    stretch = geodesy.longitude_stretch(float(coordinates[:, 1].mean()))
    flat = affinity.scale(line, xfact=stretch, yfact=1.0, origin=(0.0, 0.0))
    swathed = flat.buffer(width_km / 2.0 / DEGREE_KM)
    return affinity.scale(swathed, xfact=1.0 / stretch, yfact=1.0, origin=(0.0, 0.0))
