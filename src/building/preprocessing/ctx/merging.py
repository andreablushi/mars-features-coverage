"""Placing a scan on the grid its label projects, and marking what it left."""

from __future__ import annotations

from building.preprocessing.ctx import geometry
from building.preprocessing.ctx.models.observation import CtxObservation
from building.preprocessing.ctx.models.sample import CtxSample

# What the projection writes where the scan swept no ground.
BLANK = 0


def merge_geometry(observation: CtxObservation) -> CtxSample:
    """Place one scan on its grid and mark the pixels it never measured.

    Args:
        observation: The observation, read but not yet placed.

    Returns:
        The sample, its image on the grid its label projects it onto.
    """
    return CtxSample(
        observation.identifier,
        observation.image,
        observation.image == BLANK,
        observation.latitude,
        observation.longitude,
        geometry.pixel(observation.label),
    )
