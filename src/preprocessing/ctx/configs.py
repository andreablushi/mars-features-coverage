"""Central configuration for reading a CTX RDR."""

from __future__ import annotations

from utils.disk import paths

# Where the metadata download stage writes what it fetched from ODE.
METADATA_ROOT = paths.METADATA_ROOT

# Where downloaded scans are kept, one directory each.
CACHE_ROOT = paths.CTX_ROOT

# How far the grid a label projects may sit from the corners the same label
# claims, counted in pixels. ISIS writes the footprint that was asked for and
# then snaps the grid to whole pixels, so the two differ by under a pixel.
TOLERANCE_PIXELS = 2.0

# How long to wait for the scan, which ASU builds on the way out and which no
# other product of this pipeline comes close to in size.
TIMEOUT = 900.0
