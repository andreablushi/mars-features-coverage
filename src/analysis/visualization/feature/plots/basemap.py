"""The feature itself: the ground it covers, and what the search made of it."""

from __future__ import annotations

from html import escape

import ipywidgets as widgets
from matplotlib.colors import to_rgba
from matplotlib.patches import Patch

from analysis.stats.feature import reading
from analysis.stats.models.feature import FeatureLooks
from analysis.visualization.common import panels
from analysis.visualization.common.picker import Coverage
from analysis.visualization.feature.plots import mosaic, placing
from analysis.visualization.feature.plots.placing import Box, Placed

MAP_FIGURE_SIZE = (7.0, 6.0)

# How wide the report beside the map is set, so the map keeps the rest.
REPORT_WIDTH = "360px"

# How the feature is drawn, by what the search made of it.
FEATURE_FILL = 0.18
FEATURE_WIDTH = 1.4
FEATURE_COLOURS = (
    (True, panels.KEPT, "feature kept"),
    (False, panels.REFUSED, "feature refused"),
)


def plot(coverage: Coverage) -> widgets.Widget:
    """Show the ground the feature covers, marked by what the search made of it.

    Args:
        coverage: The feature on show, as the instrument sets it holds.

    Returns:
        The report beside the mosaic, or the grey panel when nothing is loaded.
    """
    if not coverage:
        return panels.unavailable()
    summary = coverage[0].summary
    looks = reading.read_feature(coverage)
    grid = placing.placed(
        summary.feature_class, summary.feature_name, summary.grid_side
    )
    if grid is None:
        return panels.unavailable(mosaic.BASEMAP_FAILED.format(reason=mosaic.NO_BOX))
    title = panels.title(coverage)
    box = grid.box()
    return widgets.HBox(
        [
            _report(coverage, looks, box),
            mosaic.fetched(box, lambda image: figure(grid, looks, box, image, title)),
        ],
        layout=widgets.Layout(
            align_items="flex-start", flex_flow="row nowrap", grid_gap="24px"
        ),
    )


def figure(
    grid: Placed, looks: FeatureLooks | None, box: Box, image: bytes, title: str
) -> widgets.Image:
    """Draw the mosaic with the feature laid over it.

    Args:
        grid: Where the feature's grid falls on the mosaic.
        looks: What the selection left on it, or None where it left nothing.
        box: The lon/lat box the crop covers.
        image: The crop as PNG bytes.
        title: The feature, for the line above the map.

    Returns:
        The figure as a widget.
    """
    drawn, axis = panels.board(MAP_FIGURE_SIZE)
    mosaic.draw(axis, box, image)
    # The feature is shaded and outlined by what the search made of it
    colour = panels.KEPT if looks and looks.window.kept else panels.REFUSED
    lon, lat = grid.outline()
    axis.fill(lon, lat, color=colour, alpha=FEATURE_FILL, zorder=2)
    axis.plot(lon, lat, color=colour, linewidth=FEATURE_WIDTH, zorder=3)
    axis.set_title(title, fontsize=12, loc="left")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.tick_params(labelsize=8)
    panels.key_below(
        drawn,
        [
            Patch(edgecolor=colour, facecolor=to_rgba(colour, FEATURE_FILL), label=said)
            for _, colour, said in FEATURE_COLOURS
        ],
    )
    return panels.rendered(drawn)


def _report(coverage: Coverage, looks: FeatureLooks | None, box: Box) -> widgets.HTML:
    """Report the feature's extent, its window, and what each set holds of it.

    Args:
        coverage: The feature on show, as the instrument sets it holds.
        looks: What the selection left on it, or None where it left nothing.
        box: The lon/lat box its grid falls in.

    Returns:
        The report.
    """
    window = looks.window if looks else None
    verdict = (
        f"{window.start:%Y-%m-%d} to {window.end:%Y-%m-%d}, {window.days:,.0f} days"
        if window and window.kept
        else "no window worth keeping"
    )
    summary = coverage[0].summary
    body = escape(
        "\n".join(
            f"{instrument.label:16s} {instrument.summary.n_obs:6,d} observations"
            f"{f'  ({instrument.reason})' if instrument.reason else ''}"
            for instrument in coverage
        )
    )
    return widgets.HTML(
        f"<b>{escape(panels.title(coverage))}</b><br>"
        f"{summary.feature_area_km2:,.1f} km2 bounding box, "
        f"{box.south:.3f} to {box.north:.3f} lat, "
        f"{box.west:.3f} to {box.east:.3f} lon<br>"
        f"{verdict}"
        f"<pre style='margin: 8px 0 0; line-height: 1.4'>{body}</pre>",
        layout=widgets.Layout(flex=f"0 0 {REPORT_WIDTH}"),
    )
