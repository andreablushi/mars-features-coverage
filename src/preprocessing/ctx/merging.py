"""Checking a scan fills the grid its label projects, and marking what it left."""

from __future__ import annotations

from preprocessing.common import grids
from preprocessing.ctx import configs, geometry
from preprocessing.ctx.models.observation import CtxObservation
from preprocessing.ctx.models.sample import CtxSample

# What the projection writes where the scan swept no ground.
BLANK = 0

# The corners a label claims, in the order `grids.bounds` reaches them.
CORNERS = (
    "MinimumLatitude",
    "MaximumLatitude",
    "MinimumLongitude",
    "MaximumLongitude",
)


def merge_geometry(observation: CtxObservation) -> CtxSample:
    """Place one scan on its grid and mark the pixels it never measured.

    ISIS writes the footprint that was asked for and then snaps the grid to
    whole pixels, so the two agree to under a pixel and never exactly.

    Args:
        observation: The observation, read but not yet placed.

    Returns:
        The sample, its grid checked against the corners its label claims.

    Raises:
        ValueError: When the image is not the shape its label promises, or
            falls further from those corners than a pixel or two.
    """
    if observation.image.shape != observation.shape:
        raise ValueError(
            f"{observation.identifier} holds a {observation.image.shape} image "
            f"where its label promises {observation.shape}."
        )
    step = geometry.pixel(observation.label)
    grids.check_bounds(
        grids.bounds(observation.latitude, observation.longitude, step),
        tuple(float(observation.label[key]) for key in CORNERS),
        step * configs.TOLERANCE_PIXELS,
        observation.identifier,
    )
    return CtxSample(
        observation.identifier,
        observation.image,
        observation.image == BLANK,
        observation.latitude,
        observation.longitude,
        step,
    )
