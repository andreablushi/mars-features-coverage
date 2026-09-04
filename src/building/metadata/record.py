"""Building what one stored observation is, from the placement it was stored with."""

from __future__ import annotations

from datetime import datetime

from building.geometry.common import project
from building.geometry.common.models.placement import Placement
from building.metadata.models.feature import FeatureFrame
from building.metadata.models.observation import ObservationRecord


def observation_record(
    frame: FeatureFrame,
    instrument: str,
    identifier: str,
    axes: tuple[str, ...],
    shape: tuple[int, ...],
    placement: Placement,
    t_start: datetime | None = None,
    t_end: datetime | None = None,
    altitude: tuple[float, float] | None = None,
) -> ObservationRecord:
    """Return the record one stored observation is read back through.

    Args:
        frame: The local frame of the feature it was kept for.
        instrument: The instrument that took it, as ODE names it.
        identifier: What that instrument was asked for.
        axes: What each axis of the value array holds, in its own order.
        shape: The value array's shape, in that same order.
        placement: Where its samples sit, which the sample size is measured off.
        t_start: When it started, or None where the archive publishes no time.
        t_end: When it ended, or None for the same reason.
        altitude: How low and how high the spacecraft was, for a sounder whose
            delay axis is read through it, and None for every other instrument.

    Returns:
        The record, its ground sample measured rather than claimed.
    """
    low, high = altitude if altitude else (None, None)
    return ObservationRecord(
        feature_class=frame.feature_class,
        feature_name=frame.feature_name,
        instrument=instrument,
        identifier=identifier,
        axes=axes,
        shape=shape,
        ground_sample_m=project.ground_sample_m(placement, frame),
        separable=placement.separable,
        t_start=t_start,
        t_end=t_end,
        altitude_min_m=low,
        altitude_max_m=high,
    )
