"""What a CRISM multispectral survey observation is published as, and where it lands."""

from __future__ import annotations

import re

from building.common.naming import Naming
from building.common.product_cache import ProductCache
from building.metadata.models import observation as observation_axes
from utils.disk import paths

# The two detectors of one scan, infrared and visible.
DETECTORS = ("l", "s")

# The two products one detector of a scan is published as.
OBSERVATION = "observation"
GEOMETRY = "geometry"
KINDS = (OBSERVATION, GEOMETRY)

# How ODE spells one detector of an observation, the detector and the kind
# written where the observation's own id carries neither.
NAMING = Naming(
    re.compile(r"^(?P<stem>\w+)_if(?P<code>\d+)(?P<detector>[ls]?)_(?P<level>trr\d+)$"),
    identity="{stem}_if{code}_{level}",
    marks=("detector",),
    template="{stem}_{marker}{code}{detector}_{level}",
    fields={
        OBSERVATION: {"marker": "if"},
        GEOMETRY: {"marker": "de", "level": "ddr1"},
    },
)

# What a label calls the wavelength file it was calibrated against.
WAVELENGTH_KEY = "MRO:WAVELENGTH_FILE_NAME"

# Where each product of an observation is kept, and what it is called there.
# The geometry sits in a subdirectory of its own, beside the scan it belongs to.
CACHE = ProductCache(paths.CRISM_ROOT, {None: (".lbl", ".img")}, {GEOMETRY: "ddr"})

# What each axis of the cube holds, in the order it is stored.
AXES = (observation_axes.GROUND, observation_axes.GROUND, observation_axes.WAVELENGTH)

# The directory every wavelength file is kept in, shared by every observation.
WAVELENGTH_DIR = "cdr"

# Which DDR backplane places a pixel. The other twelve are dropped: three carry
# the null sentinel in every pixel, four barely vary across a scan, and the rest
# are MOLA resampled onto this grid, which the MOLA tile itself holds better.
BACKPLANES = {"latitude": 3, "longitude": 4}
