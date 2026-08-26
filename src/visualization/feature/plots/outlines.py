"""The footprints as ODE published them, read back off the downloaded metadata."""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

import numpy as np
from shapely import wkt as reading
from shapely.geometry.base import BaseGeometry

import utils.disk.paths as paths
from coverage.records import load_set
from coverage.results import SetCoverage
from models.instrument import InstrumentSet
from utils.disk.slugify import slugify

# How many features' footprints are kept, so a tile already read draws in memory
OUTLINE_CACHE = 4

Trace = tuple[np.ndarray, np.ndarray]


def read(coverage: Sequence[SetCoverage]) -> dict[str, BaseGeometry]:
    """Read the published footprint of every observation of one feature.

    Args:
        coverage: The feature's instrument sets, in any order.

    Returns:
        The footprint of each observation, by product id.
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
        The footprint of each of its observations, by product id.
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


def traced(shape: BaseGeometry) -> list[Trace]:
    """Trace one published footprint as the lines a panel can draw.

    Args:
        shape: The footprint as published.

    Returns:
        The longitudes and latitudes of each line it is drawn as.
    """
    drawn: list[Trace] = []
    for part in getattr(shape, "geoms", [shape]):
        ring = getattr(part, "exterior", None)
        line = ring if ring is not None else part
        coordinates = np.asarray(line.coords, dtype=float)
        if coordinates.shape[0] > 1:
            drawn.append((coordinates[:, 0], coordinates[:, 1]))
    return drawn
