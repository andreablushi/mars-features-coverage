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

# The union is kept per sector so each insert touches a small shape. A sector
# is not a tile of the survey: it exists only to keep the union small.
MIN_UNION_SECTORS = 4
MAX_UNION_SECTORS = 32

# How many sectors of one feature are accumulated at once
UNION_THREADS = 4

# How many observations a sector folds in before its union is rebuilt in one
UNION_CHUNK = 64

# A sector covered to within this share of what it could hold
SATURATION_TOLERANCE = 1e-12

# Grid an overlay is snapped to when exact arithmetic cannot node it.
SNAP_GRID_M = 1e-6

# A SHARAD sounding is as wide as its swath and as long as the spacing between
# traces in a focused radargram, which ODE does not publish.
SHARAD_ALONG_TRACK_M = 460.0

# Ground pixel size for the sets ODE publishes no map scale for, in metres.
# CRISM's survey modes are binned about ten times coarser than its targeted one.
# CTX publishes one for all but a handful of its records, and theirs is the
# median of the 497,279 that do.
FALLBACK_PIXEL_M = {"MRO/CRISM/TRDR:msp*": 180.0, "MRO/CTX/EDR": 5.4}

# How wide one block of the measurement grid is, in kilometres. A CTX swath is
# some tens of kilometres across, so a tile this wide is a few images across:
# narrower, and a single image fills it and the share of it asked for stops
# meaning anything; wider, and one window stretches over ground nothing looked
# at together.
GRID_KM = 100

# How wide a cell of the grid of Mars is, in kilometres, on which the features
# are laid over one another so ground two of them share is counted once. It is
# finer than the smallest grid a feature is measured on.
OVERLAP_CELL_KM = 3.0

# Straight lon/lat edges curve once projected, so resample below this step
MAX_SEGMENT_DEG = 0.25

# Segments per quarter circle when a track is buffered to its swath.
BUFFER_QUAD_SEGMENTS = 16

# A footprint smaller than this share of one cell is given no cell at all,
# since a whole cell would credit it with ground it never reached
MIN_CELL_SHARE = 0.5
