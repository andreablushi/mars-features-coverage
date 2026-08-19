"""Central configuration for the interactive layer."""

from __future__ import annotations

GREY = "#8a8a8a"

# The feature class the picker opens on
DEFAULT_CLASS = "Crater"
NO_DATA_SUFFIX = "  (no data)"
DROPDOWN_WIDTH = "340px"
MONTH_DROPDOWN_WIDTH = "190px"

# The blank first month, which leaves that end of the range open.
OPEN_END_LABEL = ""

# How an instrument set with nothing to draw is drawn anyway.
UNOBSERVED_LINESTYLE = (0, (1, 3))

# Instruments whose whole planet coverage would flatten every other panel.
FULL_PLANET_INSTRUMENTS = ("MOLA",)

# One stacked panel per instrument set, so the height is per panel
FIGURE_WIDTH = 11
PANEL_HEIGHT = 2.5

# The running curve beside the totals, and how the width is split between them
CUMULATIVE_FIGURE_SIZE = (13, 5)
CUMULATIVE_WIDTH_RATIOS = [3, 1]
