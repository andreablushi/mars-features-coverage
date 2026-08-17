"""Central configuration for the coverage analysis stage."""

from __future__ import annotations

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

# The union is kept per tile so each insert touches a small shape
MIN_UNION_TILES = 4
MAX_UNION_TILES = 32

# How many tiles of one feature are accumulated at once
UNION_THREADS = 4

# How many observations a tile folds in before its union is rebuilt in one
UNION_CHUNK = 64

# A tile covered to within this share of what it could hold
SATURATION_TOLERANCE = 1e-12

# Grid an overlay is snapped to when exact arithmetic cannot node it.
SNAP_GRID_M = 1e-6

# Straight lon/lat edges curve once projected, so resample below this step
MAX_SEGMENT_DEG = 0.25

# Segments per quarter circle when a track is buffered to its swath.
BUFFER_QUAD_SEGMENTS = 16


# Stamped into every cached projection.
GEOMETRY_VERSION = b"3"
