"""Central configuration for the best time window search."""

from __future__ import annotations

# Mars Year as a maximum span of time windows
MAX_SPAN_DAYS = 687.0

# How many rungs of ground the trade off curve is traced at. Coarser than
# this and the curve is too thin to find its bend in; finer buys nothing.
LEVELS = 48

# How close a cell count has to be to a level of ground to be considered.
ROUNDING = 1e-9

# Seconds in a day, which is what every span is measured in.
DAY_SECONDS = 86400.0

# An observation clipping the edge of a tile reports the edge, not the tile.
# It has to bring ground enough to crop.
MIN_AREA_KM2 = 1.0

# Which weighting of the instruments the search runs under, by the name the
# strategy's own file gives it. The others stay for the comparison.
STRATEGY = "imaged"

# Cells an observation has to bring a window that no other observation of its
# own set already reaches, or it is dropped as a repeat of ground it holds.
MIN_GAIN_CELLS = 5

# How many tiles a feature has to leave with a window before it is worth
# putting in a dataset at all. Nothing else is asked of the feature as a
# whole: what a window has to hold is asked of it tile by tile.
MIN_TILES = 1

# How many instruments the shared ground is read at, most first.
OVERLAP_SETS = (3, 2)
