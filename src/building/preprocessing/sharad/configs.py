"""Central configuration for reading a SHARAD radargram."""

from __future__ import annotations

import re

from building.preprocessing.common.disk.naming import Naming
from building.preprocessing.common.disk.product_cache import ProductCache
from utils.disk import paths

# The two products one track is published as.
OBSERVATION = "observation"
GEOMETRY = "geometry"
KINDS = (OBSERVATION, GEOMETRY)

# How ODE spells one product of a track, which writes its kind after the track
# the observation on its own ends at.
NAMING = Naming(
    re.compile(r"^(?P<track>s_\d+)(?:_(?P<marker>rgram|geom))?$"),
    identity="{track}",
    marks=("marker",),
    template="{track}_{marker}",
    fields={OBSERVATION: {"marker": "rgram"}, GEOMETRY: {"marker": "geom"}},
)

# Where the metadata download stage writes what it fetched from ODE.
METADATA_ROOT = paths.METADATA_ROOT

# Where each product of an observation is kept. The geometry is a table rather
# than an image, and sits in a subdirectory of its own.
CACHE = ProductCache(
    paths.SHARAD_ROOT,
    {OBSERVATION: (".lbl", ".img"), GEOMETRY: (".lbl", ".tab")},
    {GEOMETRY: "geom"},
)
