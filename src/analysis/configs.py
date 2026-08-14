"""Central configuration for the coverage analysis stage.

This module holds every tunable constant and imports nothing from the rest of
the stage, so it can be imported anywhere without creating a cycle.
"""

from __future__ import annotations

from common.configs import REPO_ROOT

SPEED_OF_LIGHT = 299_792_458.0

# IAU mean radius and gravitational parameter for Mars
MARS_RADIUS_M = 3_389_500.0
MARS_GM = 4.2828372e13

# SHARAD transmits 15-25 MHz; its centre sets the sounding wavelength
SHARAD_CENTRE_FREQUENCY_HZ = 20e6
SHARAD_WAVELENGTH_M = SPEED_OF_LIGHT / SHARAD_CENTRE_FREQUENCY_HZ

# MRO orbits at 255-320 km; a solve outside this band is unusable
SHARAD_MIN_ALTITUDE_M = 200e3
SHARAD_MAX_ALTITUDE_M = 400e3

# Median solved altitude, used only when no track in a feature solves
SHARAD_NOMINAL_ALTITUDE_M = 315e3

# Tracks are clipped to a dilated box so buffering still reaches the edge
LINE_CLIP_MARGIN_DEG = 2.0

LAEA_MIN_DENOMINATOR = 1e-12

# The union is kept per tile so each insert touches a small shape, not the
# whole accumulated one; tiles are disjoint so summing their areas is exact
UNION_TILES = 16

# How many observations a tile folds in before its union is rebuilt in one
# batch; a sequential pairwise union shreds its own boundary into slivers
UNION_CHUNK = 64

# A tile covered to within this share of what it could hold is treated as
# full, because an exact comparison between two separately computed areas
# almost never holds and leaves a finished tile grinding on
SATURATION_TOLERANCE = 1e-12

# Straight lon/lat edges curve once projected, so resample below this step
MAX_SEGMENT_DEG = 0.25

DATA_ROOT = REPO_ROOT / "data"
METADATA_ROOT = DATA_ROOT / "metadata"
ARTIFACTS_ROOT = DATA_ROOT / "artifacts"
COVERAGE_DIR = "coverage"
COVERAGE_ROOT = ARTIFACTS_ROOT / COVERAGE_DIR
GEOMETRY_DIR = "geometry"
GEOMETRY_ROOT = ARTIFACTS_ROOT / GEOMETRY_DIR

# Stamped into every cached projection. Bump it whenever the projection, the
# segment step or the swath model changes, so a cache built by the old rule is
# rebuilt instead of silently reused.
GEOMETRY_VERSION = b"1"
SUMMARY_NAME = "summary.parquet"
EVENTS_SUFFIX = ".events.parquet"
SET_SUMMARY_SUFFIX = ".summary.parquet"

# How many sets left without an artifact are named before the rest are counted
MISSING_SHOWN = 5

# The section of config.yaml this stage reads
CONFIG_SECTION = "coverage"

# The running union is the expensive half of the work, so it can be skipped
DEFAULT_CUMULATIVE_UNION = True

DEFAULT_WORKERS = 8
