"""Central configuration for reading a SHARAD radargram."""

from __future__ import annotations

from utils.disk import paths

# Where the metadata download stage writes what it fetched from ODE.
METADATA_ROOT = paths.METADATA_ROOT

# Where downloaded radargrams are kept, one directory each.
CACHE_ROOT = paths.SHARAD_ROOT
