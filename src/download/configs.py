"""Central configuration for the download pipeline."""

from __future__ import annotations

ODE_BASE_URL = "https://oderest.rsl.wustl.edu/live2/"
ODE_META_DB = "mars"
ODE_TARGET = "mars"

REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 5
BACKOFF_BASE = 0.5
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

PAGE_SIZE = 5000
PAGE_ORDER = "oba"

# A feature running through every longitude is asked for in two halves,
# because a box from a longitude back to itself has no width and ODE
# returns the no-count for it
LONGITUDE_HALVES = ((0.0, 180.0), (180.0, 360.0))

# Half the width of the box put around a point feature, in degrees of
# latitude. About 15 km on Mars, which holds a crater or a landing site
POINT_RADIUS_DEG = 0.25

# The point features worth sizing: a named position standing for something
# with a real edge, rather than for a diffuse classical albedo region
SIZED_POINT_CLASSES = frozenset({"Crater", "Rovers and Landers"})

# "f" keeps every product whose footprint intersects the feature box, even
# partly; "o" keeps only those fully inside, "b" compares bounding boxes,
# and "i" keeps only products containing the whole feature
DEFAULT_LOC = "f"
LOC_MODES = ("b", "f", "o", "i")

# The section of config.yaml this stage reads
CONFIG_SECTION = "download"

RETAINED_FIELDS = (
    "pdsid",
    "ihid",
    "iid",
    "pt",
    "UTC_start_time",
    "UTC_stop_time",
    "Minimum_latitude",
    "Maximum_latitude",
    "Westernmost_longitude",
    "Easternmost_longitude",
    "Footprint_C0_geometry",
    "Map_scale",
)
