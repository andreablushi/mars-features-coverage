"""Reading one MOLA tile off disk and joining its planes onto one grid."""

from __future__ import annotations

from building.preprocessing.common.pds import images
from building.preprocessing.mola import configs, geometry
from building.preprocessing.mola.models.observation import MolaObservation, Plane
from building.preprocessing.mola.models.sample import MolaSample


def read(identifier: str) -> MolaSample:
    """Read every plane one tile was downloaded as onto the grid they share.

    Args:
        identifier: The tile, whose files must already be in the cache that
            `download.fetch` puts them in.

    Returns:
        The sample, its two planes on the one grid their labels project them
        onto.

    Raises:
        FileNotFoundError: When either plane or its label is missing.
        KeyError: When a label names a sample type this cannot read.
        ValueError: When a label names a projection this cannot read.
    """
    planes = {}
    for kind in configs.KINDS:
        product = configs.NAMING.product(identifier, kind)
        values, label = images.load_plane(
            configs.CACHE.files(identifier, product, kind)[".img"]
        )
        planes[kind] = Plane(kind, values, label, *geometry.load(label))
    observation = MolaObservation(identifier, planes)
    height, shots = observation.topography, observation.counts
    return MolaSample(
        observation.identifier,
        height.values,
        shots.values,
        height.latitude,
        height.longitude,
        observation.resolution,
    )
