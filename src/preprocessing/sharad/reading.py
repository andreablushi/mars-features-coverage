"""Reading one SHARAD observation off disk, whole."""

from __future__ import annotations

from preprocessing.sharad.loaders import geometry, radargram
from preprocessing.sharad.models.observation import SharadObservation


def read(identifier: str) -> SharadObservation:
    """Read the radargram and the geometry one observation was published as.

    Args:
        identifier: The observation, whose files must already be in the cache
            that `download.fetch` puts them in.

    Returns:
        The observation, its radargram and its geometry loaded.

    Raises:
        FileNotFoundError: When either product or its label is missing.
        KeyError: When a label names a sample type this cannot read.
        ValueError: When the geometry holds fewer rows than its label promises.
    """
    power, label = radargram.load(identifier)
    table, geometry_label = geometry.load(identifier)
    return SharadObservation(identifier, power, label, table, geometry_label)
