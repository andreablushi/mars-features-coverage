"""Central configuration for cleaning a CRISM multispectral survey observation."""

from __future__ import annotations

from utils.disk import paths

# Where the metadata download stage writes what it fetched from ODE.
METADATA_ROOT = paths.METADATA_ROOT

# Where downloaded observations are kept, one directory each.
CACHE_ROOT = paths.CRISM_ROOT
