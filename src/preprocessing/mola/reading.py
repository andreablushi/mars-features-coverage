"""Reading one MOLA tile off disk, whole."""

from __future__ import annotations

from preprocessing.mola.loaders import geometry, grid
from preprocessing.mola.loaders.utils import naming
from preprocessing.mola.models.observation import MolaObservation, Plane


def read(identifier: str) -> MolaObservation:
    """Read every plane one tile was downloaded as into an observation.

    Args:
        identifier: The tile, whose files must already be in the cache that
            `download.fetch` puts them in.

    Returns:
        The observation, both planes loaded and each placed on the grid its own
        label projects it onto.

    Raises:
        FileNotFoundError: When either plane or its label is missing.
        KeyError: When a label names a sample type this cannot read.
        ValueError: When a label names a projection this cannot read.
    """
    planes = {}
    for kind in naming.KINDS:
        values, label = grid.load(identifier, kind)
        planes[kind] = Plane(kind, values, label, *geometry.load(label))
    return MolaObservation(identifier, planes)
