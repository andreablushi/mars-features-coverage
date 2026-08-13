"""Central configuration for the coverage analysis stage.

This module holds every tunable constant and imports nothing from the rest of
the package, so it can be imported anywhere without creating a cycle.
"""

from __future__ import annotations

from pathlib import Path

SPEED_OF_LIGHT = 299_792_458.0

# IAU mean radius and gravitational parameter for Mars
MARS_RADIUS_M = 3_389_500.0
MARS_GM = 4.2828372e13

# SHARAD transmits 15-25 MHz; the centre frequency sets the sounding wavelength
SHARAD_CENTRE_FREQUENCY_HZ = 20e6
SHARAD_WAVELENGTH_M = SPEED_OF_LIGHT / SHARAD_CENTRE_FREQUENCY_HZ

# MRO flies a near-circular 255-320 km orbit; altitudes solved outside this
# band mean the track length or duration is unusable, so the run falls back to
# the median width of every track that did solve
SHARAD_MIN_ALTITUDE_M = 200e3
SHARAD_MAX_ALTITUDE_M = 400e3

# Median altitude solved across every SHARAD track in the archive, used only
# when a feature holds no track that solved at all
SHARAD_NOMINAL_ALTITUDE_M = 315e3

# Lines are clipped to a generously dilated box before projection, so a track
# buffered afterwards still covers the box edge
LINE_CLIP_MARGIN_DEG = 2.0

GRID_MAX_DIM = 2048
LAEA_MIN_DENOMINATOR = 1e-12

# An edge that is straight in lon/lat curves once projected, so every boundary
# is resampled below this angular step before being projected; without it a
# footprint clipped against the box cuts the corner off the box edge
MAX_SEGMENT_DEG = 0.25

DATA_ROOT = Path("data")
METADATA_ROOT = DATA_ROOT / "metadata"
ARTIFACTS_ROOT = Path("artifacts")
COVERAGE_DIR = "coverage"
COVERAGE_ROOT = ARTIFACTS_ROOT / COVERAGE_DIR
EVENTS_NAME = "events.parquet"
SUMMARY_NAME = "summary.parquet"

# Whole-planet basemaps cover every feature by construction, so they are
# computed but tagged for exclusion from default plots
GRIDDED_SETS = frozenset({("MGS", "MOLA", "MEGDR")})

ALL_SETS_LABEL = "ALL"

DEFAULT_WORKERS = 8
