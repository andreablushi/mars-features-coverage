"""Central configuration for the sweep and what it publishes."""

from __future__ import annotations

# How far past the whole tile a share may read before the tile is thrown out.
SHARE_CEILING = 1.01

# How many processes a sweep searches on when the caller names no number.
DEFAULT_WORKERS = 8

# What separates the instruments naming one piece of shared ground in a key.
INSTRUMENTS_JOINED = "|"

# The layout of a published file, raised whenever what is written changes.
PREDICTION_SHAPE = 3
