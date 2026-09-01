"""Placing each radargram column at the point its geometry names."""

from __future__ import annotations

import numpy as np

from preprocessing.sharad.models.observation import SharadObservation
from preprocessing.sharad.models.sample import SharadSample

# The field the geometry names each radargram column in, counted from one.
COLUMN_FIELD = "RADARGRAM COLUMN"


def merge_geometry(observation: SharadObservation) -> SharadSample:
    """Join one radargram to the geometry of the columns it was measured at.

    Args:
        observation: The observation, read but not yet joined.

    Returns:
        The sample holding only the traces the geometry places, in the order
        the radargram stores them.

    Raises:
        ValueError: When the geometry places a column the radargram does not
            hold, or names the same column twice.
    """
    # The geometry counts columns from one, and the radargram from zero.
    traces = observation.geometry[COLUMN_FIELD].astype("i8") - 1
    if traces.min() < 0 or traces.max() >= observation.traces:
        raise ValueError(
            f"{observation.identifier} is placed at columns 1 to "
            f"{traces.max() + 1}, outside its {observation.traces} traces."
        )
    if np.unique(traces).size != traces.size:
        raise ValueError(f"{observation.identifier} places a column twice.")
    # Read the geometry in the order the radargram stores its columns.
    order = np.argsort(traces)
    return SharadSample(
        observation.identifier,
        observation.power[:, traces[order]],
        observation.geometry[order],
        traces[order],
    )
