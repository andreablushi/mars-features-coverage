"""Central configuration for the coverage analysis stage."""

from __future__ import annotations

SPEED_OF_LIGHT = 299_792_458.0

# IAU mean radius and gravitational parameter for Mars
MARS_RADIUS_M = 3_389_500.0
MARS_GM = 4.2828372e13

# SHARAD transmits 15-25 MHz; its centre sets the sounding wavelength
SHARAD_CENTRE_FREQUENCY_HZ = 20e6
SHARAD_WAVELENGTH_M = SPEED_OF_LIGHT / SHARAD_CENTRE_FREQUENCY_HZ

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

# A SHARAD sounding is as wide as its swath and as long as the spacing between
# traces in a focused radargram, which ODE does not publish.
SHARAD_ALONG_TRACK_M = 460.0

# Ground pixel size for the sets ODE publishes no map scale for, in metres.
# CRISM's survey modes are binned about ten times coarser than its targeted one.
FALLBACK_PIXEL_M = {"MRO/CRISM/TRDR:[mh]sp*": 180.0}

# Straight lon/lat edges curve once projected, so resample below this step
MAX_SEGMENT_DEG = 0.25

# Segments per quarter circle when a track is buffered to its swath.
BUFFER_QUAD_SEGMENTS = 16

# Cells across a feature's grid scale with the cube root of its width, so a
# crater keeps sub-kilometre cells and a continent does not need millions.
# The factor puts a feature of a few tens of km at about 64 cells a side.
RASTER_CELL_FACTOR = 18.0
RASTER_CELL_EXPONENT = 1.0 / 3.0

# A footprint smaller than this share of one cell is given no cell at all,
# since a whole cell would credit it with ground it never reached
MIN_CELL_SHARE = 0.5
