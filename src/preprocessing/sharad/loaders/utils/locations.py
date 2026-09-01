"""Where the files of one SHARAD observation are kept on disk."""

from __future__ import annotations

from pathlib import Path

from preprocessing.sharad import configs
from preprocessing.sharad.loaders.utils import naming

# The two halves each product is downloaded as, the label and what it describes.
SUFFIXES = {
    naming.OBSERVATION: (".lbl", ".img"),
    naming.GEOMETRY: (".lbl", ".tab"),
}

# The subdirectory an observation keeps its geometry in.
GEOMETRY_DIR = "geom"


def files(observation_id: str, kind: str = naming.OBSERVATION) -> dict[str, Path]:
    """Return where each half of one product belongs.

    Args:
        observation_id: The observation.
        kind: Which product, `naming.OBSERVATION` or `naming.GEOMETRY`.

    Returns:
        The path for each suffix, keyed by suffix.

    Raises:
        KeyError: When the kind is neither of the two.
    """
    stem = naming.product(observation_id, kind)
    place = configs.CACHE_ROOT / observation_id
    if kind == naming.GEOMETRY:
        place = place / GEOMETRY_DIR
    return {suffix: place / f"{stem}{suffix}" for suffix in SUFFIXES[kind]}


def label(observation_id: str, kind: str = naming.OBSERVATION) -> Path:
    """Return where one product's label belongs.

    Args:
        observation_id: The observation.
        kind: Which product, `naming.OBSERVATION` or `naming.GEOMETRY`.

    Returns:
        The label path.
    """
    return files(observation_id, kind)[".lbl"]
