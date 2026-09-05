"""Cutting one MOLA tile's planes down to what its feature's box keeps."""

from __future__ import annotations

from building.preprocessing.common.cut import taken
from building.preprocessing.common.models.cut import Cut
from building.preprocessing.mola.models.sample import MolaSample


def cut(sample: MolaSample, held: Cut) -> MolaSample:
    """Return one tile holding only the bins a cut keeps.

    A gridded tile is simple cylindrical, so the box is a rectangle on it and
    both planes are cut at once by a range of lines and a range of samples.

    Args:
        sample: The tile as it was read off disk.
        held: What the feature's box keeps of it.

    Returns:
        The tile cut to it, how fine its grid is unchanged.
    """
    lines, samples = held.bounds
    return MolaSample(
        identifier=sample.identifier,
        topography=taken(sample.topography, held.bounds),
        counts=taken(sample.counts, held.bounds),
        latitude=sample.latitude[lines],
        longitude=sample.longitude[samples],
        resolution=sample.resolution,
    )
