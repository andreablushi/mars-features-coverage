"""Where the files of one MOLA tile are kept on disk."""

from __future__ import annotations

from pathlib import Path

from preprocessing.locations import product_files
from preprocessing.mola import configs
from preprocessing.mola.loaders.utils import naming

# The two halves each plane is downloaded as, the label and what it describes.
SUFFIXES = (".lbl", ".img")


def files(tile: str, kind: str = naming.TOPOGRAPHY) -> dict[str, Path]:
    """Return where each half of one plane belongs.

    Args:
        tile: The tile, such as 00n180hb.
        kind: Which plane, `naming.TOPOGRAPHY` or `naming.COUNTS`.

    Returns:
        The path for each suffix, keyed by suffix.

    Raises:
        KeyError: When the kind is neither of the two.
    """
    return product_files(configs.CACHE_ROOT, tile, naming.product(tile, kind), SUFFIXES)


def label(tile: str, kind: str = naming.TOPOGRAPHY) -> Path:
    """Return where one plane's label belongs.

    Args:
        tile: The tile, such as 00n180hb.
        kind: Which plane, `naming.TOPOGRAPHY` or `naming.COUNTS`.

    Returns:
        The label path.
    """
    return files(tile, kind)[".lbl"]
