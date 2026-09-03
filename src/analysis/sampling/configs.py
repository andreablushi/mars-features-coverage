"""Central configuration for the sweep and what it publishes."""

from __future__ import annotations

# How far past the whole feature a share may read before it is thrown out.
SHARE_CEILING = 1.01

# What separates the instruments naming one piece of shared ground in a key.
INSTRUMENTS_JOINED = "|"

# The layout of a published file, raised whenever what is written changes.
PREDICTION_SHAPE = 6
