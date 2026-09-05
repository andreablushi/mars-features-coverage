"""Cutting one CRISM observation's cube down to what its feature's box keeps."""

from __future__ import annotations

from building.preprocessing.common.cut import taken
from building.preprocessing.common.models.cut import Cut
from building.preprocessing.crism.models.sample import CrismSample


def cut(sample: CrismSample, held: Cut) -> CrismSample:
    """Return one observation holding only the pixels a cut keeps.

    A swath bends as the spacecraft flies, so the box is no rectangle on it and
    the cut is the rectangle bounding what it keeps. The wavelengths run along
    the columns, so they are cut by the column axis alone.

    Args:
        sample: The observation with its two detectors joined.
        held: What the feature's box keeps of it.

    Returns:
        The observation cut to it, its bands left whole.
    """
    columns = held.bounds[1]
    return CrismSample(
        identifier=sample.identifier,
        cube=taken(sample.cube, held.bounds),
        wavelengths=sample.wavelengths[columns],
        geometry=taken(sample.geometry, held.bounds),
        columns=sample.columns[columns],
    )
