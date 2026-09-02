"""Reading one SHARAD observation off disk, whole."""

from __future__ import annotations

from building.preprocessing.common.pds import images, tables
from building.preprocessing.sharad import configs
from building.preprocessing.sharad.models.observation import SharadObservation


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
    # The echoes themselves, then the places they were sounded at.
    power, label = images.load_plane(
        configs.CACHE.files(
            identifier, configs.NAMING.product(identifier, configs.OBSERVATION)
        )[".img"]
    )
    geometry = configs.NAMING.product(identifier, configs.GEOMETRY)
    table, geometry_label = tables.load_table(
        configs.CACHE.files(identifier, geometry, configs.GEOMETRY)[".tab"]
    )
    return SharadObservation(identifier, power, label, table, geometry_label)
