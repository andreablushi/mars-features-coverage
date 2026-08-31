"""Where the files of one CRISM observation are kept on disk.

An observation owns a directory named after it, holding both detectors of the
scan, with the geometry the two were published with in a subdirectory of its
own since it is a product apart.
"""

from __future__ import annotations

from pathlib import Path

from preprocessing.crism import configs
from preprocessing.crism.fetching import naming

# The two halves a product is downloaded as.
SUFFIXES = (".lbl", ".img")

# The subdirectory an observation keeps its geometry in.
GEOMETRY_DIR = "ddr"


def files(
    observation_id: str, detector: str, kind: str = naming.OBSERVATION
) -> dict[str, Path]:
    """Return where each half of one detector's product belongs.

    Args:
        observation_id: The observation.
        detector: Which detector, `l` or `s`.
        kind: Which product, `naming.OBSERVATION` or `naming.GEOMETRY`.

    Returns:
        The path for each suffix, keyed by suffix.
    """
    stem = naming.product(observation_id, detector, kind)
    place = configs.CACHE_ROOT / observation_id
    if kind == naming.GEOMETRY:
        place = place / GEOMETRY_DIR
    return {suffix: place / f"{stem}{suffix}" for suffix in SUFFIXES}


def labels(observation_id: str) -> dict[str, Path]:
    """Return where each detector's label belongs.

    Args:
        observation_id: The observation.

    Returns:
        The label path for each detector, keyed by detector.
    """
    return {
        detector: files(observation_id, detector)[".lbl"]
        for detector in naming.DETECTORS
    }
