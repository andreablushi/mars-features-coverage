"""Central configuration for the stats and what they publish."""

from __future__ import annotations

# How far past the whole feature a share may read before it is thrown out.
SHARE_CEILING = 1.01

# How many features are held read at once, so every panel of one shares it.
FEATURE_CACHE = 8

# The layout of a published file, raised whenever what is written changes.
STATS_SHAPE = 2
