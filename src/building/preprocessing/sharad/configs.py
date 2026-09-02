"""Central configuration for reading a SHARAD radargram."""

from __future__ import annotations

from building.preprocessing.common.disk.product_cache import ProductCache
from building.preprocessing.sharad import naming
from utils.disk import paths

# Where the metadata download stage writes what it fetched from ODE.
METADATA_ROOT = paths.METADATA_ROOT

# Where each product of an observation is kept. The geometry is a table rather
# than an image, and sits in a subdirectory of its own.
CACHE = ProductCache(
    paths.SHARAD_ROOT,
    {naming.OBSERVATION: (".lbl", ".img"), naming.GEOMETRY: (".lbl", ".tab")},
    {naming.GEOMETRY: "geom"},
)
