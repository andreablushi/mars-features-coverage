"""Central configuration for reading a MOLA gridded tile."""

from __future__ import annotations

from building.preprocessing.common.disk.product_cache import ProductCache
from utils.disk import paths

# Where both planes of a tile are kept, in the one directory of the tile.
CACHE = ProductCache(paths.MOLA_ROOT, {None: (".lbl", ".img")})

# How fine a grid to read, in pixels per degree. MEGDR publishes 4, 16, 32, 64
# and 128, and only 128 is finer than a kilometre.
RESOLUTION = 128
