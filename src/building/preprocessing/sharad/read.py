"""Reading one SHARAD observation off disk and placing its traces."""

from __future__ import annotations

from building.preprocessing.common.pds import images, tables
from building.preprocessing.sharad import configs
from building.preprocessing.sharad.models.observation import SharadObservation
from building.preprocessing.sharad.models.sample import SharadSample


def read(identifier: str) -> SharadSample:
    """Read one radargram and join it to the geometry it was measured at.

    Args:
        identifier: The observation, whose files must already be in the cache
            that `download.fetch` puts them in.

    Returns:
        The sample holding only the traces the geometry places, in the order
        the radargram stores them.

    Raises:
        FileNotFoundError: When either product or its label is missing.
        KeyError: When a label names a sample type this cannot read.
        ValueError: When the geometry holds fewer rows than its label promises.
    """
    # The echoes themselves, then the places they were sounded at.
    power, label = images.load_plane(
        configs.CACHE.files(
            identifier,
            configs.NAMING.product(identifier, configs.OBSERVATION),
            configs.OBSERVATION,
        )[".img"]
    )
    geometry = configs.NAMING.product(identifier, configs.GEOMETRY)
    table, geometry_label = tables.load_table(
        configs.CACHE.files(identifier, geometry, configs.GEOMETRY)[".tab"]
    )
    observation = SharadObservation(identifier, power, label, table, geometry_label)

    # The geometry counts columns from one, and the radargram from zero.
    traces = observation.geometry[configs.COLUMN_FIELD].astype("i8") - 1
    return SharadSample(
        observation.identifier,
        observation.power[:, traces],
        observation.geometry,
        traces,
    )
