"""Central configuration for the download pipeline.

This module holds every tunable constant and imports nothing from the rest of
the stage, so it can be imported anywhere without creating a cycle.
"""

from __future__ import annotations

from common.files import REPO_ROOT

ODE_BASE_URL = "https://oderest.rsl.wustl.edu/live2/"
ODE_META_DB = "mars"
ODE_TARGET = "mars"

REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 5
BACKOFF_BASE = 0.5
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

PAGE_SIZE = 5000
PAGE_ORDER = "oba"

# "f" keeps every product whose footprint intersects the feature box, even
# partly; "o" would keep only products falling entirely inside it
DEFAULT_LOC = "f"

DEFAULT_WORKERS = 4
MAX_WORKERS = 6

DATA_ROOT = REPO_ROOT / "data"
METADATA_ROOT = DATA_ROOT / "metadata"
CATALOG_ROOT = DATA_ROOT / "_catalog"
FEATURES_CACHE_NAME = "features.jsonl"
INSTRUMENT_SETS_CACHE_NAME = "instrument_sets.jsonl"

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

# Every default carries both a footprint and an acquisition time, which is
# what the coverage stage needs to place an observation on a time axis
DEFAULT_INSTRUMENT_SETS = (
    ("MRO", "CTX", "EDR"),
    ("MRO", "HIRISE", "RDRV11"),
    ("MRO", "CRISM", "MTRDR"),
    ("MRO", "CRISM", "TRDR"),
    ("MRO", "SHARAD", "RDR"),
)
