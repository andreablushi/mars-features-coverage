"""Cutting one SHARAD track's traces down to what its feature's box keeps."""

from __future__ import annotations

from building.preprocessing.common.models.cut import Cut
from building.preprocessing.sharad.models.sample import SharadSample


def cut(sample: SharadSample, held: Cut) -> SharadSample:
    """Return one track holding only the traces a cut keeps.

    A sounder walks a line, so only the traces are cut and the delay each one
    was sounded over is left whole. The traces are the radargram's second axis,
    which is why it is not cut on its leading axes as a raster is.

    Args:
        sample: The radargram holding only the traces its geometry places.
        held: What the feature's box keeps of it.

    Returns:
        The track cut to it, its delay axis unchanged.
    """
    (traces,) = held.bounds
    return SharadSample(
        identifier=sample.identifier,
        power=sample.power[:, traces],
        geometry=sample.geometry[traces],
        traces=sample.traces[traces],
    )
