"""Reading one MOLA tile off disk and joining its planes onto one grid."""

from __future__ import annotations

from building.common.pds import images
from building.configs import mola as configs
from building.preprocessing.mola import projection
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
        planes[kind] = images.load_plane(
            configs.CACHE.files(identifier, product, kind)[".img"]
        )
    # Both planes are written on the one grid, so the height's places them all.
    height, label = planes[configs.TOPOGRAPHY]
    latitude, longitude = projection.load(label)
    return MolaSample(
        identifier,
        height,
        planes[configs.COUNTS][0],
        latitude,
        longitude,
        configs.resolution(identifier),
    )
