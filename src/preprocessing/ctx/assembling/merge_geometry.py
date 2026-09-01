"""Checking a scan fills the grid its label projects, and marking what it left."""

from __future__ import annotations

import numpy as np

from preprocessing.ctx import configs
from preprocessing.ctx.loaders import geometry
from preprocessing.ctx.models.observation import CtxObservation
from preprocessing.ctx.models.sample import CtxSample

# What the projection writes where the scan swept no ground.
BLANK = 0


def merge_geometry(observation: CtxObservation) -> CtxSample:
    """Place one scan on its grid and mark the pixels it never measured.

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
    _check_corners(observation, step)
    return CtxSample(
        observation.identifier,
        observation.image,
        observation.image == BLANK,
        observation.latitude,
        observation.longitude,
        step,
    )


def _check_corners(observation: CtxObservation, step: float) -> None:
    """Refuse a grid that falls far from the corners its label claims.

    ISIS writes the footprint that was asked for and then snaps the grid to
    whole pixels, so the two agree to under a pixel and never exactly.

    Args:
        observation: The observation to check.
        step: How many degrees one pixel spans.

    Returns:
        None.

    Raises:
        ValueError: When the grid covers something other than its label says.
    """
    half = step / 2.0
    reached = (
        float(observation.latitude.min()) - half,
        float(observation.latitude.max()) + half,
        float(observation.longitude.min()) - half,
        float(observation.longitude.max()) + half,
    )
    claimed = tuple(
        float(observation.label[key])
        for key in (
            "MinimumLatitude",
            "MaximumLatitude",
            "MinimumLongitude",
            "MaximumLongitude",
        )
    )
    if not np.allclose(reached, claimed, atol=step * configs.TOLERANCE_PIXELS):
        raise ValueError(
            f"{observation.identifier} reads over {reached}, where its label "
            f"claims {claimed}."
        )
