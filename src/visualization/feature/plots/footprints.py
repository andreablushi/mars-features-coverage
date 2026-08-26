"""The tile on show, with the footprint of every observation it keeps."""

from __future__ import annotations

import threading

import ipywidgets as widgets
from matplotlib.axes import Axes
from matplotlib.lines import Line2D

from sampling.stats import tiles
from visualization.common import panels, series
from visualization.feature import picker
from visualization.feature.picker import TileView
from visualization.feature.plots import basemap, outlines, overlay
from visualization.feature.plots.overlay import Box, Placed

MAP_FIGURE_SIZE = (9.0, 6.0)

# How the tile itself is drawn under the footprints.
TILE_EDGE = "#ffffff"
TILE_WIDTH = 1.4
TRACE_WIDTH = 1.2
TRACE_ALPHA = 0.85

# How the note is written over a tile with nothing to trace on it.
NOTE_COLOUR = "#ffffff"
NOTE_SIZE = 11

_UNKNOWN = "this feature has no lon/lat box to crop the mosaic to"
_NOTHING = "No footprints available"


def plot(chosen: TileView | None) -> widgets.Widget:
    """Show the tile with the footprint of every observation it keeps.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The map as a widget, or the grey panel when there is nothing to crop to.
    """
    if chosen is None:
        return panels.unavailable(picker.NO_TILE)
    summary = chosen.view.coverage[0].summary
    grid = overlay.placed(
        summary.feature_class,
        summary.feature_name,
        summary.grid_side,
        chosen.across,
    )
    if grid is None:
        return panels.unavailable(overlay.BASEMAP_FAILED.format(reason=_UNKNOWN))
    note = (
        f"<div style='color: {panels.GREY}; font-family: sans-serif;"
        f" font-size: 12px; padding: 12px;'>{overlay.BASEMAP_LOADING}</div>"
    )
    space = widgets.Box([widgets.HTML(note)])
    threading.Thread(target=_fill, args=(space, grid, chosen), daemon=True).start()
    return space


def _fill(space: widgets.Box, grid: Placed, chosen: TileView) -> None:
    """Put the fetched map in the space claimed for it.

    Args:
        space: The claimed space, already on screen.
        grid: Where the feature's grid falls on the mosaic.
        chosen: The tile on show.

    Returns:
        None.
    """
    stats = chosen.stats
    box = grid.tile_box(stats.row, stats.column)
    try:
        image = overlay.crop(box)
    except Exception as exc:
        space.children = (
            panels.unavailable(overlay.BASEMAP_FAILED.format(reason=exc)),
        )
        return
    space.children = (_figure(grid, chosen, box, image),)


def _figure(grid: Placed, chosen: TileView, box: Box, image: bytes) -> widgets.Widget:
    """Draw the tile's crop with the footprints its window keeps traced on it.

    Args:
        grid: Where the feature's grid falls on the mosaic.
        chosen: The tile on show.
        box: The lon/lat box the crop covers.
        image: The crop as PNG bytes.

    Returns:
        The figure as a widget, carrying the crop alone where there is nothing to trace.
    """
    shapes = outlines.read(chosen.view.coverage)
    figure, axis = panels.board(MAP_FIGURE_SIZE)
    basemap.mosaic(axis, box, image)
    lon, lat = grid.tile(chosen.stats.row, chosen.stats.column)
    axis.plot(lon, lat, color=TILE_EDGE, linewidth=TILE_WIDTH)
    colours = _traces(axis, grid, chosen, shapes)
    if not colours:
        axis.text(
            0.5,
            0.5,
            _NOTHING,
            transform=axis.transAxes,
            ha="center",
            va="center",
            color=NOTE_COLOUR,
            fontsize=NOTE_SIZE,
        )
    axis.set_title(chosen.name, fontsize=12, loc="left")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.tick_params(labelsize=8)
    panels.key_beside(
        figure,
        [
            Line2D([], [], color=colour, linewidth=TRACE_WIDTH, label=label)
            for label, colour in colours.items()
        ],
    )
    return panels.rendered(figure)


def _traces(
    axis: Axes, grid: Placed, chosen: TileView, shapes: dict
) -> dict[str, tuple]:
    """Trace the footprint of every observation the tile keeps.

    Args:
        axis: The panel to draw on.
        grid: Where the feature's grid falls on the mosaic.
        chosen: The tile on show.
        shapes: The published footprint of each observation, by product id.

    Returns:
        The colour each instrument set was drawn in, by set label.
    """
    track = chosen.track
    colours = panels.colours(series.over_tile(track))
    drawn: dict[str, tuple] = {}
    for index in tiles.held(chosen.survey):
        shape = shapes.get(track.observations[index].pdsid)
        if shape is None:
            continue
        label = track.labels[track.owners[index]]
        for lon, lat in outlines.traced(shape):
            axis.plot(
                grid.around(lon),
                lat,
                color=colours[label],
                linewidth=TRACE_WIDTH,
                alpha=TRACE_ALPHA,
            )
            drawn[label] = colours[label]
    return drawn
