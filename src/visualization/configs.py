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

# The ODE browse image beside the overview, and how many are kept in memory.
BROWSE_TIMEOUT = 15.0
BROWSE_CACHE = 64
BROWSE_HEIGHT = "260px"

# How an instrument set with nothing to draw is drawn anyway.
UNOBSERVED_LINESTYLE = (0, (1, 3))

# One stacked panel per instrument set, so the height is per panel
FIGURE_WIDTH = 11
PANEL_HEIGHT = 2.5

# How many months one density column covers, however long the range is.
DENSITY_BIN_MONTHS = 1
DENSITY_ROW_HEIGHT = 0.5
DENSITY_COLORMAP = "YlGnBu"
DENSITY_EMPTY = "#ffffff"
DENSITY_ROW_EDGE = "#cccccc"

# The mean of the sets' records over time, with the weakest set filled under it
AVAILABILITY_FIGURE_SIZE = (11, 3.4)
AVAILABILITY_COLOUR = "#2c7fb8"
AVAILABILITY_MEAN_ALPHA = 0.35
AVAILABILITY_FLOOR_ALPHA = 0.85

# The running curve beside the totals, and how the width is split between them
CUMULATIVE_FIGURE_SIZE = (13, 5)
CUMULATIVE_WIDTH_RATIOS = [3, 1]
