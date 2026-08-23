"""Central configuration for the best time window search."""

from __future__ import annotations

# A survey is a stretch to observe in, not an era, so it never runs longer
# than one Mars year, which is every season the feature has.
MAX_SPAN_DAYS = 687.0

# How many rungs of ground the trade off curve is traced at. Coarser than
# this and the curve is too thin to find its bend in; finer buys nothing.
LEVELS = 48

# A share adds up cell by cell, so let a rung it lands a rounding under pass.
ROUNDING = 1e-9

# Seconds in a day, which is what every span is measured in.
DAY_SECONDS = 86400.0

# How wide a tile of a feature is, in kilometres. A CTX swath is some tens of
# kilometres across, so a tile this wide is a few images across: narrower, and
# a single image fills it and the share of it asked for stops meaning
# anything; wider, and one window stretches over ground nothing looked at
# together, which is what the tiling is here to stop.
TILE_KM = 100.0

# An observation clipping the edge of a tile reports the edge, not the tile.
# It has to bring ground enough to crop.
MIN_AREA_KM2 = 1.0

# A sounder reports a line, so it also has to cross this share of the feature
# rather than stopping just inside it.
MIN_CROSSING = 0.10

# Which weighting of the instruments the search runs under, by the name the
# strategy's own file gives it. The others stay for the comparison.
STRATEGY = "imaged"

# Ground an observation has to bring a window that nothing before it brought.
MIN_GAIN_KM2 = 1.0

# How many tiles a feature has to leave with a window before it is worth
# putting in a dataset at all. Nothing else is asked of the feature as a
# whole: what a window has to hold is asked of it tile by tile.
MIN_TILES = 1

# How many instruments the shared ground is read at, most first.
OVERLAP_SETS = (3, 2)
