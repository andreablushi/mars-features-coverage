"""Central configuration for the best time window search."""

from __future__ import annotations

# A campaign is a stretch to observe in, not an era, so it never runs longer.
MAX_SPAN_DAYS = 365.0

# How many rungs of ground the trade off curve is traced at. Coarser than
# this and the curve is too thin to find its bend in; finer buys nothing.
LEVELS = 48

# A share adds up cell by cell, so let a rung it lands a rounding under pass.
ROUNDING = 1e-9

# Seconds in a day, which is what every span is measured in.
DAY_SECONDS = 86400.0
