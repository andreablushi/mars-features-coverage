"""Central configuration for reading a CTX RDR."""

from __future__ import annotations

from utils.disk import paths

# Where the metadata download stage writes what it fetched from ODE.
METADATA_ROOT = paths.METADATA_ROOT

# Where downloaded scans are kept, one directory each.
CACHE_ROOT = paths.CTX_ROOT

# How long to wait for the scan, which ASU builds on the way out and which no
# other product of this pipeline comes close to in size.
TIMEOUT = 900.0
