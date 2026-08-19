"""Central configuration for the download pipeline."""

from __future__ import annotations

ODE_BASE_URL = "https://oderest.rsl.wustl.edu/live2/"
ODE_META_DB = "mars"
ODE_TARGET = "mars"

REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 20
BACKOFF_BASE = 0.5
# Ceiling on one backoff sleep, so many retries stay minutes rather than days
BACKOFF_MAX = 30.0
RETRYABLE_STATUS = frozenset({403, 429, 500, 502, 503, 504})

PAGE_SIZE = 5000
PAGE_ORDER = "oba"

# A feature running through every longitude is asked for in two halves.
LONGITUDE_HALVES = ((0.0, 180.0), (180.0, 360.0))

# Half the width of the box put around a point feature (15Km in mars degrees)
POINT_RADIUS_DEG = 0.25

# The point features worth sizing: a landing site has no extent to lose.
SIZED_POINT_CLASSES = frozenset({"Rovers and Landers"})

# Localization modes for the products API
LOC_MODES = ("b", "f", "o", "i")

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
