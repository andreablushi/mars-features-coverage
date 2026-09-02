"""Central configuration for reading a CTX RDR."""

from __future__ import annotations

import re

from building.preprocessing.common.disk.naming import Naming
from building.preprocessing.common.disk.product_cache import ProductCache
from utils.disk import paths

# The two products one scan is downloaded as, the pixels and what places them.
IMAGE = "image"
LABEL = "label"
KINDS = (IMAGE, LABEL)

# What each kind is suffixed with once it is on disk.
SUFFIXES = {IMAGE: ".tiff", LABEL: ".isis.hdr"}

# Which ASU directory each kind is kept in, and what it is called there.
DIRECTORIES = {IMAGE: "prj_full", LABEL: "stage"}
REMOTE_SUFFIXES = {IMAGE: ".tiff", LABEL: ".scyl.isis.hdr"}

# How a scan is named, for its mission phase, orbit, latitude and where it
# looked. Every phase is a letter and two digits, apart from orbit insertion.
# ASU names both products after the scan itself, so there is no product to
# write and no kind written into the id.
NAMING = Naming(
    re.compile(
        r"^(?P<scan>(?:[a-z]\d{2}|moi)_\d{6}_\d{4}_[a-z]{2}_\d{2}[ns]\d{3}[we])$"
    ),
    identity="{scan}",
)

# The PDS volume a scan was archived on, which its download path runs through.
VOLUME = re.compile(r"/(?P<volume>mrox_\d+)/")

# Where the metadata download stage writes what it fetched from ODE.
METADATA_ROOT = paths.METADATA_ROOT

# Where both products of a scan are kept. ASU names them after the scan itself,
# so the suffix is all that tells them apart.
CACHE = ProductCache(paths.CTX_ROOT, {None: tuple(SUFFIXES.values())})

# How long to wait for the scan, which ASU builds on the way out and which no
# other product of this pipeline comes close to in size.
TIMEOUT = 900.0
