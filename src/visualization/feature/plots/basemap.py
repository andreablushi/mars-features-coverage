"""The feature itself: the ground it covers, cut into the tiles it is searched in."""

from __future__ import annotations

import io
import threading
from html import escape

import ipywidgets as widgets
import numpy as np
from matplotlib import image as reading
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.patches import Patch

from analysis.utils import geodesy
from survey.models.study import Study
from utils.maths import quantities
from visualization.common import panels, surveys, tiles
from visualization.common.picker import View
from visualization.feature.plots import overlay
from visualization.feature.plots.overlay import Box, Placed

MAP_FIGURE_SIZE = (7.0, 6.0)
MAP_PLACEHOLDER = "320px"

# How wide the report beside the map is set, so the map keeps the rest.
REPORT_WIDTH = "360px"

# How a tile is drawn, by what the search made of it.
TILE_KEPT = "#2e7d32"
TILE_REFUSED = "#c62828"
TILE_REFUSED_FILL = 0.18
TILE_WIDTH = 1.1

_UNKNOWN = "this feature has no lon/lat box to crop the mosaic to"
_LEGEND = (
    (TILE_KEPT, "tile kept"),
    (TILE_REFUSED, "tile refused"),
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
    grid = overlay.placed(
        summary.feature_class,
        summary.feature_name,
        summary.grid_side,
        study.patchwork.across or 1,
    )
    if grid is None:
        return panels.unavailable(overlay.BASEMAP_FAILED.format(reason=_UNKNOWN))
    return widgets.HBox(
        [_report(view, grid, study), _view(grid, study, panels.title(view.coverage))],
        layout=widgets.Layout(
            align_items="flex-start", flex_flow="row nowrap", grid_gap="24px"
        ),
    )


def _report(view: View, grid: Placed, study: Study) -> widgets.HTML:
    """Report the feature's extent, its tiling, and what each set holds of it.

    Args:
        view: The feature on show and the strategy it is judged under.
        grid: Where its grid falls on the mosaic.
        study: What the search found over it.

    Returns:
        The report.
    """
    summary = view.coverage[0].summary
    box = grid.box()
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


def _view(grid: Placed, study: Study, title: str) -> widgets.Widget:
    """Claim the space the mosaic goes in and fetch it off the redraw.

    Args:
        grid: Where the feature's grid falls on the mosaic.
        study: What the search found over it.
        title: The feature, for the line above the map.

    Returns:
        A box holding the loading note, which the fetch replaces.
    """
    box = widgets.Box([_placeholder(overlay.BASEMAP_LOADING)])
    threading.Thread(target=_fill, args=(box, grid, study, title), daemon=True).start()
    return box


def _fill(space: widgets.Box, grid: Placed, study: Study, title: str) -> None:
    """Put the fetched map in the space claimed for it.

    Args:
        space: The claimed space, already on screen.
        grid: Where the feature's grid falls on the mosaic.
        study: What the search found over it.
        title: The feature, for the line above the map.

    Returns:
        None.
    """
    box = grid.box()
    try:
        image = overlay.crop(box)
    except Exception as exc:
        space.children = (_placeholder(overlay.BASEMAP_FAILED.format(reason=exc)),)
        return
    space.children = (_figure(grid, study, box, image, title),)


def _figure(
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
    figure, axis = panels.board(MAP_FIGURE_SIZE)
    mosaic(axis, box, image)
    _tiles(axis, grid, study)
    axis.set_title(title, fontsize=12, loc="left")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.tick_params(labelsize=8)
    panels.key_below(
        figure,
        [
            Patch(edgecolor=colour, facecolor="none", label=said)
            for colour, said in _LEGEND
        ],
    )
    return panels.rendered(figure)


def mosaic(axis: Axes, box: Box, image: bytes) -> None:
    """Draw one mosaic crop onto an axis in lon and lat.

    Args:
        axis: The panel to draw on.
        box: The lon/lat box the crop covers.
        image: The crop as PNG bytes.

    Returns:
        None.
    """
    axis.imshow(
        reading.imread(io.BytesIO(image), format="png"),
        extent=box.extent,
        origin="upper",
        cmap="gray",
    )
    axis.set_aspect(1.0 / geodesy.longitude_stretch((box.south + box.north) / 2.0))
    axis.set_xlim(box.west, box.east)
    axis.set_ylim(box.south, box.north)
    # A footprint reaching well past the crop is cut to it rather than framed
    axis.autoscale(False)


def _tiles(axis: Axes, grid: Placed, study: Study) -> None:
    """Outline every tile of the feature, marked by what the search made of it.

    Args:
        axis: The panel to draw on.
        grid: Where the feature's grid falls on the mosaic.
        study: What the search found over it.

    Returns:
        None.
    """
    found = {stats.tile: stats.kept for stats in tiles.measured(study)}
    rings: dict[bool, list[np.ndarray]] = {True: [], False: []}
    for at, patch in enumerate(study.patchwork.tiles):
        if not patch.area_km2:
            continue
        row, column = divmod(at, study.patchwork.across)
        lon, lat = grid.tile(row, column)
        rings[found.get(at, False)].append(np.column_stack([lon, lat]))
    _outline(axis, rings[True], TILE_KEPT)
    _outline(axis, rings[False], TILE_REFUSED)
    if rings[False]:
        axis.add_collection(
            PolyCollection(
                rings[False],
                facecolors=TILE_REFUSED,
                alpha=TILE_REFUSED_FILL,
                linewidths=0,
            ),
            autolim=False,
        )


def _outline(axis: Axes, rings: list[np.ndarray], colour: str) -> None:
    """Draw one batch of tile outlines in the colour their verdict earned.

    Args:
        axis: The panel to draw on.
        rings: Each tile's ring, as its lon/lat points.
        colour: The colour to draw them in.

    Returns:
        None.
    """
    if not rings:
        return
    axis.add_collection(
        LineCollection(rings, colors=colour, linewidths=TILE_WIDTH), autolim=False
    )


def _placeholder(text: str) -> widgets.HTML:
    """Set a note in the space the map will fill.

    Args:
        text: The line to set.

    Returns:
        The note, squared off to the space the map is fitted into.
    """
    return widgets.HTML(
        f"<div style='width: {MAP_PLACEHOLDER};"
        f" height: {MAP_PLACEHOLDER};"
        f" display: flex; align-items: center; justify-content: center;"
        f" box-sizing: border-box; padding: 10px; text-align: center;"
        f" background: #f2f2f2; border: 1px solid #d8d8d8; border-radius: 4px;"
        f" color: {panels.GREY}; font-family: sans-serif; font-size: 12px;'>"
        f"{escape(text)}</div>"
    )
