"""Central configuration for the interactive layer.

Every size, colour and standing message the widgets and figures use, so a
change to how the notebook looks is made in one place rather than hunted for
across the plots.
"""

from __future__ import annotations

GREY = "#8a8a8a"

NOTHING_TO_SHOW = "Confirm a feature with local data above to fill this in."
NO_UNION = (
    "This feature was computed without the cumulative union, so there is no "
    "running coverage to draw. Recompute it with --cumulative-union."
)

# The feature class the picker opens on
DEFAULT_CLASS = "Crater"
NO_DATA_SUFFIX = "  (no data)"
DROPDOWN_WIDTH = "340px"

# One stacked panel per instrument set, so the height is per panel
FIGURE_WIDTH = 11
PANEL_HEIGHT = 2.5

# The running curve beside the totals, and how the width is split between them
CUMULATIVE_FIGURE_SIZE = (13, 5)
CUMULATIVE_WIDTH_RATIOS = [3, 1]

# The USGS Mars basemap the notebook pulls a context image from. The image is
# fetched when the panel is drawn and kept in memory, never written to disk.
BASEMAP_URL = "https://planetarymaps.usgs.gov/cgi-bin/mapserv"
BASEMAP_MAP = "/maps/mars/mars_simp_cyl.map"
BASEMAP_LAYER = "MDIM21_color"
BASEMAP_PIXELS = 520
BASEMAP_TIMEOUT = 20.0

# How many feature widths the view spans, and the floor for a tiny feature
BASEMAP_PADDING = 3.0
BASEMAP_MIN_SPAN_DEG = 0.15

BASEMAP_FAILED = "The basemap image could not be fetched: {reason}"
