"""Central configuration for reading a CTX RDR."""

from __future__ import annotations

from building.preprocessing.common.disk.product_cache import ProductCache
from building.preprocessing.ctx import naming
from utils.disk import paths

# Where the metadata download stage writes what it fetched from ODE.
METADATA_ROOT = paths.METADATA_ROOT

# Where both products of a scan are kept. ASU names them after the scan itself,
# so the suffix is all that tells them apart.
CACHE = ProductCache(paths.CTX_ROOT, {None: tuple(naming.SUFFIXES.values())})

# How long to wait for the scan, which ASU builds on the way out and which no
# other product of this pipeline comes close to in size.
TIMEOUT = 900.0
