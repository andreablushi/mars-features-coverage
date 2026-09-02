"""Central configuration for reading a MOLA gridded tile."""

from __future__ import annotations

import re

from building.preprocessing.common.disk.naming import Naming
from building.preprocessing.common.disk.product_cache import ProductCache
from utils.disk import paths

# The two planes of one tile that are read, the height and how it was measured.
TOPOGRAPHY = "topography"
COUNTS = "counts"
KINDS = (TOPOGRAPHY, COUNTS)

# How fine a grid each resolution letter stands for, in pixels per degree.
RESOLUTIONS = {"c": 4, "e": 16, "f": 32, "g": 64, "h": 128}

# How the archive spells one plane of a tile, named for the corner it starts at
# and how fine it is. Its kind is what drops the polar tiles.
NAMING = Naming(
    re.compile(r"^(?:meg(?P<marker>[tc]))?(?P<tile>\d{2}[ns]\d{3}(?P<step>[cefgh])b)$"),
    identity="{tile}",
    marks=("marker",),
    template="meg{marker}{tile}",
    fields={TOPOGRAPHY: {"marker": "t"}, COUNTS: {"marker": "c"}},
)

# Where both planes of a tile are kept, in the one directory of the tile.
CACHE = ProductCache(paths.MOLA_ROOT, {None: (".lbl", ".img")})

# How fine a grid to read, in pixels per degree. MEGDR publishes 4, 16, 32, 64
# and 128, and only 128 is finer than a kilometre.
RESOLUTION = 128


def resolution(tile: str) -> int:
    """Read how fine a grid one tile is written on.

    Args:
        tile: The tile, such as 00n180hb.

    Returns:
        The pixels per degree the tile holds.

    Raises:
        ValueError: When the tile is not one this can read.
    """
    parts = NAMING.parts(tile)
    if not parts:
        raise ValueError(f"{tile} is not a simple cylindrical MEGDR tile.")
    return RESOLUTIONS[parts["step"]]
