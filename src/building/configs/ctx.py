"""What a CTX scan is published as, and where it lands."""

from __future__ import annotations

import re

from building.common.naming import Naming
from building.common.product_cache import ProductCache
from building.metadata.models import observation as observation_axes
from utils.disk import paths

# The two products one scan is downloaded as, the pixels and what places them.
IMAGE = "image"
LABEL = "label"
KINDS = (IMAGE, LABEL)

# What each kind is suffixed with once it is on disk.
SUFFIXES = {IMAGE: ".tiff", LABEL: ".isis.hdr"}

# How a scan is named, for its mission phase, orbit, latitude and where it
# looked.
NAMING = Naming(
    re.compile(
        r"^(?P<scan>(?:[a-z]\d{2}|moi)_\d{6}_\d{4}_[a-z]{2}_\d{2}[ns]\d{3}[we])$"
    ),
    identity="{scan}",
)

# What each axis of the image holds, in the order it is stored.
AXES = (observation_axes.GROUND, observation_axes.GROUND)

# Where both products of a scan are kept. ASU names them after the scan itself,
# so the suffix is all that tells them apart.
CACHE = ProductCache(paths.CTX_ROOT, {None: tuple(SUFFIXES.values())})
