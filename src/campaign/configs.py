"""Central configuration for the best time window search."""

from __future__ import annotations

# A campaign is a stretch to observe in, not an era, so it never runs longer
# than one Mars year, which is every season the feature has.
MAX_SPAN_DAYS = 687.0

# How many rungs of ground the trade off curve is traced at. Coarser than
# this and the curve is too thin to find its bend in; finer buys nothing.
LEVELS = 48

# A share adds up cell by cell, so let a rung it lands a rounding under pass.
ROUNDING = 1e-9

# Seconds in a day, which is what every span is measured in.
DAY_SECONDS = 86400.0

# An observation clipping the edge of a feature reports the edge, not the
# feature. It has to bring ground enough to crop, and fill a cell of the
# feature's grid that is not the only one.
MIN_AREA_KM2 = 1.0
MIN_CELLS = 2

# A sounder reports a line, so it also has to cross this share of the feature
# rather than stopping just inside it.
MIN_CROSSING = 0.10

# What a feature has to hold before it is worth putting in a dataset at all.
MIN_SETS = 2

# Cells an observation has to bring a window that nothing before it brought.
MIN_GAIN_CELLS = 1
