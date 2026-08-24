"""Central configuration for the best time window search."""

from __future__ import annotations

# How many days of waiting one more percentage point of ground is worth.
DAYS_PER_PERCENT = 10.0

# Seconds in a day, which is what every span is measured in.
DAY_SECONDS = 86400.0

# Cells an observation has to bring a window that no other observation of its
# own set already reaches, or it is dropped as a repeat of ground it holds.
MIN_GAIN_CELLS = 5

# How many tiles a feature has to leave with a window before it is worth
# putting in a dataset at all. Nothing else is asked of the feature as a
# whole: what a window has to hold is asked of it tile by tile.
MIN_TILES = 1

# How many instruments the shared ground is read at, most first.
OVERLAP_SETS = (3, 2)
