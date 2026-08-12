"""Central configuration for the download pipeline.

This module holds every tunable constant and imports nothing from the rest of
the package, so it can be imported anywhere without creating a cycle.
"""

from __future__ import annotations

from pathlib import Path

ODE_BASE_URL = "https://oderest.rsl.wustl.edu/live2/"
ODE_META_DB = "mars"
ODE_TARGET = "mars"

REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 5
BACKOFF_BASE = 0.5
RETRYABLE_STATUS = frozenset({403, 429, 500, 502, 503, 504})

PAGE_SIZE = 5000
PAGE_ORDER = "oba"
DEFAULT_LOC = "o"
LOC_CHOICES = ("b", "f", "o", "i")

DEFAULT_WORKERS = 4
MAX_WORKERS = 6

DATA_ROOT = Path("data")
METADATA_ROOT = DATA_ROOT / "metadata"
CATALOG_ROOT = DATA_ROOT / "_catalog"
FEATURES_CACHE_NAME = "features.jsonl"
INSTRUMENT_SETS_CACHE_NAME = "instrument_sets.jsonl"

RETAINED_FIELDS = (
    "ode_id",
    "pdsid",
    "ihid",
    "iid",
    "pt",
    "Data_Set_Id",
    "UTC_start_time",
    "UTC_stop_time",
    "Observation_time",
    "Center_latitude",
    "Center_longitude",
    "Minimum_latitude",
    "Maximum_latitude",
    "Westernmost_longitude",
    "Easternmost_longitude",
    "Footprint_C0_geometry",
    "Emission_angle",
    "Incidence_angle",
    "Phase_angle",
    "Solar_longitude",
    "Map_scale",
    "Product_creation_time",
    "Start_orbit_number",
    "Stop_orbit_number",
)

DEFAULT_INSTRUMENT_SETS = (
    ("MRO", "CTX", "EDR"),
    ("MRO", "HIRISE", "RDRV11"),
    ("MRO", "HIRISE", "DTM"),
    ("MRO", "CRISM", "MTRDR"),
    ("MRO", "CRISM", "TRDR"),
    ("MRO", "SHARAD", "RDR"),
    ("MGS", "MOLA", "MEGDR"),
    ("MEX", "HRSC", "DTMRDR"),
)

TEST_FEATURE_NAMES = ("Gale", "Baetis Chasma", "Jezero")

TEST_INSTRUMENT_SETS = (
    ("MRO", "CTX", "EDR"),
    ("MRO", "CRISM", "MTRDR"),
)
