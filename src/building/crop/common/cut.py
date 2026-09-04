"""Working out what one feature's box keeps of an observation placed against it."""

from __future__ import annotations

import numpy as np

from building.crop.common.models.cut import Box, Cut
from building.geometry.common.models.placement import Placement
from building.metadata.models.feature import FeatureFrame
from utils.geometry import geodesy

# The whole turn, which a longitude offset is measured round.
TURN = 360.0


def cut(placement: Placement, frame: FeatureFrame) -> Cut | None:
    """Return what one feature's box keeps of an observation placed against it.

    Args:
        placement: Where the observation's samples sit, in degrees from the
            feature centre.
        frame: The feature's local frame, carrying the box the catalogue gives
            it, which is read as the same degrees from that centre.

    Returns:
        The cut, or None where the observation reaches none of the box at all.
    """
    box = Box(
        south=frame.min_lat - frame.centre_lat,
        north=frame.max_lat - frame.centre_lat,
        west=geodesy.normalise_longitude(frame.west_lon - frame.centre_lon),
        span=geodesy.longitude_span(frame.west_lon, frame.east_lon),
    )
    if placement.separable:
        # The box is a rectangle on a grid whose axes run north and east, so
        # each axis is asked on its own and what they keep is exactly the box.
        lines = np.flatnonzero(_upward(placement.north, box))
        # An axis counts from its own first longitude, and a box running over
        # the meridian keeps two ends of it that are one strip of ground, so
        # ordering by how far east each lies is what joins those ends back up.
        reach = _eastward(placement.east, box)
        held = np.flatnonzero(reach <= box.span)
        samples = held[np.argsort(reach[held], kind="stable")]
        if not lines.size or not samples.size:
            return None
        return Cut((lines, samples), None)
    inside = _upward(placement.north, box) & (
        _eastward(placement.east, box) <= box.span
    )
    if not inside.any():
        return None
    where = np.argwhere(inside)
    bounds = tuple(
        np.arange(int(low), int(high) + 1)
        for low, high in zip(where.min(axis=0), where.max(axis=0), strict=True)
    )
    kept = taken(inside, bounds)
    return Cut(bounds, None if kept.all() else kept)


def taken(array: np.ndarray, bounds: tuple[np.ndarray, ...]) -> np.ndarray:
    """Return the part of one array a cut's bounds keep of its leading axes.

    Args:
        array: The array to cut, whose leading axes are the ground's.
        bounds: The samples to keep of each of those axes.

    Returns:
        The part that is left, every axis past the ground's kept whole.
    """
    return array[np.ix_(*bounds)] if len(bounds) > 1 else array[bounds[0]]


def cut_placement(placement: Placement, held: Cut) -> Placement:
    """Return where the samples one cut keeps sit.

    Args:
        placement: The placement the cut was worked out against.
        held: What the feature's box keeps of it.

    Returns:
        The placement of the samples that are left, held the same way.
    """
    if placement.separable:
        lines, samples = held.bounds
        return Placement(placement.north[lines], placement.east[samples], True)
    return Placement(
        taken(placement.north, held.bounds), taken(placement.east, held.bounds), False
    )


def _upward(north: np.ndarray, box: Box) -> np.ndarray:
    """Return which northward offsets fall between the box's two latitudes.

    Args:
        north: The northward offsets to test, in degrees.
        box: The feature's extent.

    Returns:
        True where an offset falls in it, shaped as the offsets are.
    """
    return (north >= box.south) & (north <= box.north)


def _eastward(east: np.ndarray, box: Box) -> np.ndarray:
    """Return how far east of the box's western edge each offset lies.

    Args:
        east: The eastward offsets to test, in degrees.
        box: The feature's extent.

    Returns:
        The distance east of that edge in degrees, from 0 up to a whole turn,
        so the meridian the box may run over is no edge at all.
    """
    return (east - box.west) % TURN
