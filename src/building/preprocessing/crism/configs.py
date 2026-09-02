"""Central configuration for cleaning a CRISM multispectral survey observation."""

from __future__ import annotations

import re

from building.preprocessing.common.disk.naming import Naming
from building.preprocessing.common.disk.product_cache import ProductCache
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

# Where the metadata download stage writes what it fetched from ODE.
METADATA_ROOT = paths.METADATA_ROOT

# Where each product of an observation is kept, and what it is called there.
# The geometry sits in a subdirectory of its own, beside the scan it belongs to.
CACHE = ProductCache(paths.CRISM_ROOT, {None: (".lbl", ".img")}, {GEOMETRY: "ddr"})

# The directory every wavelength file is kept in, shared by every observation.
WAVELENGTH_DIR = "cdr"

# What a wavelength file writes where the detector was never calibrated.
UNCALIBRATED = 65535.0

# The wavelength window in nm each detector is trusted over, outside which the
# sensor edge sees almost no light and the reading is noise.
WINDOWS = {"l": (1020.0, 2650.0), "s": (400.0, 1060.0)}

# The range a brightness can take, its floor just below zero so noise there
# survives and only the impossible is refused.
BRIGHTNESS = (-0.05, 1.0)


# How wide in nm the moving median smoothing a column's spectrum reaches, fixed
# in nm so every downlink configuration means the same width.
STRIPE_WIDTH = 80.0

# How many deviations above its column's mean a band must sit to read as a
# spike, set per detector above the highest real absorption measured.
STRIPE_SIGMA = {"l": 7.5, "s": 4.7}

# Where the atmosphere absorbs inside each detector's window, in nm. Only the
# 2.0 um CO2 band costs less than it saves, the weaker ones sit on real features.
ATMOSPHERIC = {"l": ((1940.0, 2090.0),), "s": ()}

# The windows crism_ml despikes ratioed spectra with, in nm. The deviation is 20
# rather than 5, which keeps 99.7 per cent of a real one band absorption.
SPIKE_PASSES = ((72.0, 20.0), (46.0, 20.0), (20.0, 20.0))
