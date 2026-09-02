"""Central configuration for reading a MOLA gridded tile."""

from __future__ import annotations

from utils.disk import paths

# Where downloaded tiles are kept, one directory each.
CACHE_ROOT = paths.MOLA_ROOT

# How fine a grid to read, in pixels per degree. MEGDR publishes 4, 16, 32, 64
# and 128, and only 128 is finer than a kilometre.
RESOLUTION = 128
