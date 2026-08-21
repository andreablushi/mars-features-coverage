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

# The global mosaic a feature is drawn on, served as WMS by the USGS.
BASEMAP_URL = "https://planetarymaps.usgs.gov/cgi-bin/mapserv"
BASEMAP_MAP = "/maps/mars/mars_simp_cyl.map"
BASEMAP_LAYER = "THEMIS"
BASEMAP_PIXELS = 700
BASEMAP_WIDTH = "300px"
BASEMAP_TIMEOUT = 30.0
BASEMAP_FAILED = "The basemap could not be fetched: {reason}"
BASEMAP_LOADING = "Fetching the basemap..."
BASEMAP_CACHE = 32

# How many times the feature's own width the view spans, and its floor.
BASEMAP_PADDING = 4.0
BASEMAP_MIN_SPAN_DEG = 0.5

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

# The running curve beside the totals, and how the width is split between them
CUMULATIVE_FIGURE_SIZE = (13, 5)
CUMULATIVE_WIDTH_RATIOS = [3, 1]

# The grid of candidate windows a feature's record is scored on.
WINDOW_COLUMNS = 240
WINDOW_WIDTHS = 64
WINDOW_MIN_DAYS = 1.0
WINDOW_MAX_DAYS = 687.0
WINDOW_FIGURE_SIZE = (12, 6)

# The window the search picked, marked at either end of the time panels.
# How many searches are kept, so every panel of a feature shares one.
CAMPAIGN_CACHE = 8
CAMPAIGN_LINE = "#1a1a1a"
CAMPAIGN_STYLE = (0, (6, 3))
CAMPAIGN_WIDTH = 0.8

# How a feature that belongs in the dataset is marked, and one that does not.
VERDICT_PASS = "#2e7d32"
VERDICT_FAIL = "#c62828"
VERDICT_KEPT = "In the dataset"
VERDICT_LEFT = "Left out of the dataset"

# How a window holding no sounder track is drawn, and how the counts are traced.
WINDOW_UNSOUNDED = "#d9d9d9"
WINDOW_CONTOUR = "#4d4d4d"

# The window the search picked, marked on the grid of candidates it was chosen from.
WINDOW_PICKED = "#d62728"
WINDOW_PICKED_EDGE = "#ffffff"
WINDOW_PICKED_SIZE = 6.0

# How hard the colours lean towards the low shares a short window reaches.
WINDOW_GAMMA = 0.5

# How the instrument count rings are drawn, the ring holding every one of them last.
WINDOW_RING = 0.7
WINDOW_RING_ALL = 1.5
WINDOW_TICKS = [
    (1.0, "1 day"),
    (7.0, "1 week"),
    (30.0, "1 month"),
    (91.0, "3 months"),
    (183.0, "6 months"),
    (365.0, "1 year"),
    (687.0, "1 Mars year"),
    (730.0, "2 years"),
    (1826.0, "5 years"),
    (3652.0, "10 years"),
    (7305.0, "20 years"),
]
