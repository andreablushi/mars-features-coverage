"""Turning a placement's degree offsets into metres on the feature's own frame."""

from __future__ import annotations

import numpy as np

from building.metadata.models.feature import FeatureFrame
from building.preprocessing.common.models.placement import Placement
from utils.geometry import geodesy

# How many samples of an axis to measure a ground sample size over. A grid is
# regular enough that a stride this long says the same as the whole axis.
MEASURED = 512


def metres(placement: Placement, frame: FeatureFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return how far east and north of the feature centre every sample sits.

    A separable placement is crossed to its full grid here, so a large raster is
    sliced before it is handed over rather than after.

    Args:
        placement: Where the samples sit, in degrees from the feature centre.
        frame: The feature's local frame, which the offsets are relative to.

    Returns:
        The eastings and northings in metres, shaped as the ground is.
    """
    north, east = placement.north, placement.east
    if placement.separable:
        north, east = north[:, np.newaxis], east[np.newaxis, :]
    return geodesy.laea_forward(
        frame.centre_lon + east,
        frame.centre_lat + north,
        frame.centre_lon,
        frame.centre_lat,
    )


def ground_sample_m(placement: Placement, frame: FeatureFrame) -> tuple[float, ...]:
    """Return how much ground one sample spans, along each of its ground axes.

    Measured off the placement rather than read out of a label, so one figure
    means the same for a map raster, a swath and a track alike.

    Args:
        placement: Where the samples sit, in degrees from the feature centre.
        frame: The feature's local frame, which the offsets are relative to.

    Returns:
        The median distance in metres between samples neighbouring along each
        ground axis, in the order those axes run. A map raster near a pole is
        far finer across than along, so one figure for both would say neither.
    """

    def stride(length: int, walked: bool) -> slice:
        """Return the samples of one axis to measure over.

        The frame is a feature's own, and an equal-area projection shortens a
        step the further it falls from that feature, so the samples nearest the
        middle are the ones that say what a sample spans.

        Args:
            length: How many samples the axis holds.
            walked: Whether this is the axis being measured along, rather than
                one held at a single sample while it is.

        Returns:
            The slice of it to measure, at most MEASURED samples long.
        """
        if not walked:
            return slice(length // 2, length // 2 + 1)
        kept = min(length, MEASURED)
        start = (length - kept) // 2
        return slice(start, start + kept)

    steps: list[float] = []
    for axis in range(placement.ground_axes):
        if placement.separable:
            thinned = Placement(
                placement.north[stride(placement.north.size, axis == 0)],
                placement.east[stride(placement.east.size, axis == 1)],
                True,
            )
        else:
            taken = tuple(
                stride(size, held == axis)
                for held, size in enumerate(placement.north.shape)
            )
            thinned = Placement(placement.north[taken], placement.east[taken], False)
        east, north = metres(thinned, frame)
        walk = np.hypot(np.diff(east, axis=axis), np.diff(north, axis=axis))
        steps.append(float(np.median(walk)))
    return tuple(steps)
