"""The feature itself: the ground it covers, cut into the tiles it is searched in."""

from __future__ import annotations

from html import escape

import ipywidgets as widgets
import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import to_rgba
from matplotlib.patches import Patch

from analysis.sampling import measuring
from analysis.sampling.models.study import Study
from analysis.utils.maths import quantities
from analysis.visualization.common import panels, surveys
from analysis.visualization.common.picker import View
from analysis.visualization.feature.plots import mosaic, placing
from analysis.visualization.feature.plots.placing import Box, Placed

MAP_FIGURE_SIZE = (7.0, 6.0)

# How wide the report beside the map is set, so the map keeps the rest.
REPORT_WIDTH = "360px"

# How a tile is drawn, by what the search made of it.
TILE_FILL = 0.18
TILE_WIDTH = 1.1
TILE_COLOURS = (
    (True, panels.KEPT, "tile kept"),
    (False, panels.REFUSED, "tile refused"),
)


def plot(view: View) -> widgets.Widget:
    """Show the ground the feature covers, cut into the tiles it is searched in.

    Args:
        view: The feature on show and the strategy it is judged under.

    Returns:
        The report beside the mosaic, or the grey panel when nothing is loaded.
    """
    if not view.coverage:
        return panels.unavailable()
    summary = view.coverage[0].summary
    study = surveys.studied(view.coverage, view.strategy)
    grid = placing.placed(
        summary.feature_class,
        summary.feature_name,
        summary.grid_side,
        study.grid.across or 1,
    )
    if grid is None:
        return panels.unavailable(mosaic.BASEMAP_FAILED.format(reason=mosaic.NO_BOX))
    title = panels.title(view.coverage)
    box = grid.box()
    return widgets.HBox(
        [
            _report(view, grid, box),
            mosaic.fetched(box, lambda image: figure(grid, study, box, image, title)),
        ],
        layout=widgets.Layout(
            align_items="flex-start", flex_flow="row nowrap", grid_gap="24px"
        ),
    )


def figure(
    grid: Placed, study: Study, box: Box, image: bytes, title: str
) -> widgets.Image:
    """Draw the mosaic with the feature's tiles laid over it.

    Args:
        grid: Where the feature's grid falls on the mosaic.
        study: What the search found over it.
        box: The lon/lat box the crop covers.
        image: The crop as PNG bytes.
        title: The feature, for the line above the map.

    Returns:
        The figure as a widget.
    """
    drawn, axis = panels.board(MAP_FIGURE_SIZE)
    mosaic.draw(axis, box, image)
    _tiles(axis, grid, study)
    axis.set_title(title, fontsize=12, loc="left")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.tick_params(labelsize=8)
    panels.key_below(
        drawn,
        [
            Patch(edgecolor=colour, facecolor=to_rgba(colour, TILE_FILL), label=said)
            for _, colour, said in TILE_COLOURS
        ],
    )
    return panels.rendered(drawn)


def _report(view: View, grid: Placed, box: Box) -> widgets.HTML:
    """Report the feature's extent, its tiling, and what each set holds of it.

    Args:
        view: The feature on show and the strategy it is judged under.
        grid: Where its grid falls on the mosaic.
        box: The lon/lat box that grid falls in.

    Returns:
        The report.
    """
    summary = view.coverage[0].summary
    body = escape(
        "\n".join(
            f"{instrument.label:16s} {instrument.summary.n_obs:6,d} observations"
            f"{f'  ({instrument.reason})' if instrument.reason else ''}"
            for instrument in view.coverage
        )
    )
    return widgets.HTML(
        f"<b>{escape(panels.title(view.coverage))}</b><br>"
        f"{summary.feature_area_km2:,.1f} km2 bounding box, "
        f"{box.south:.3f} to {box.north:.3f} lat, "
        f"{box.west:.3f} to {box.east:.3f} lon<br>"
        f"{escape(view.strategy.name)}: cut into {grid.across} by {grid.across} tiles "
        f"of about {quantities.area(view.strategy.tile_km**2)}"
        f"<pre style='margin: 8px 0 0; line-height: 1.4'>{body}</pre>",
        layout=widgets.Layout(flex=f"0 0 {REPORT_WIDTH}"),
    )


def _tiles(axis: Axes, grid: Placed, study: Study) -> None:
    """Shade and outline every tile, marked by what the search made of it.

    Args:
        axis: The panel to draw on.
        grid: Where the feature's grid falls on the mosaic.
        study: What the search found over it.

    Returns:
        None.
    """
    found = {stats.tile: stats.kept for stats in measuring.measured_tiles(study)}
    rings: dict[bool, list[np.ndarray]] = {True: [], False: []}
    for at, patch in enumerate(study.grid.tiles):
        if not patch.area_km2:
            continue
        row, column = divmod(at, study.grid.across)
        lon, lat = grid.tile(row, column)
        rings[found.get(at, False)].append(np.column_stack([lon, lat]))
    # Every tile is shaded before any is outlined, so no fill dims an edge
    for kept, colour, _ in TILE_COLOURS:
        if rings[kept]:
            axis.add_collection(
                PolyCollection(
                    rings[kept], facecolors=colour, alpha=TILE_FILL, linewidths=0
                ),
                autolim=False,
            )
    for kept, colour, _ in TILE_COLOURS:
        if rings[kept]:
            axis.add_collection(
                LineCollection(rings[kept], colors=colour, linewidths=TILE_WIDTH),
                autolim=False,
            )
