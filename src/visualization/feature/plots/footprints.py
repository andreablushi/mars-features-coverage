"""The tile on show, with a box round the ground every observation reached."""

from __future__ import annotations

import threading

import ipywidgets as widgets
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.lines import Line2D

from survey.models.track import Track
from visualization.common import panels, series
from visualization.feature import picker
from visualization.feature.picker import TileView
from visualization.feature.plots import basemap, overlay
from visualization.feature.plots.overlay import Box, Placed

MAP_FIGURE_SIZE = (7.0, 6.0)

# How the tile itself is drawn under the boxes.
TILE_EDGE = "#ffffff"
TILE_WIDTH = 1.4
BOX_WIDTH = 1.0
BOX_ALPHA = 0.85

_NO_WINDOW = "This tile holds no window worth keeping, so nothing is boxed."
_UNKNOWN = "the catalogue holds no box for this feature"


def plot(chosen: TileView | None) -> widgets.Widget:
    """Show the tile on show with the observations its window keeps boxed on it.

    Args:
        chosen: The tile on show, or None while none is picked.

    Returns:
        The map as a widget, or the grey panel when there is none to draw.
    """
    if chosen is None:
        return panels.unavailable(picker.NO_TILE)
    if chosen.survey is None:
        return panels.unavailable(_NO_WINDOW)
    summary = chosen.view.coverage[0].summary
    grid = overlay.placed(
        summary.feature_class,
        summary.feature_name,
        summary.grid_side,
        chosen.across,
    )
    if grid is None:
        return panels.unavailable(overlay.BASEMAP_FAILED.format(reason=_UNKNOWN))
    space = widgets.Box([_loading()])
    threading.Thread(target=_fill, args=(space, grid, chosen), daemon=True).start()
    return space


def _loading() -> widgets.HTML:
    """Set the note shown while the crop is fetched.

    Returns:
        The note.
    """
    return widgets.HTML(
        f"<div style='color: {panels.GREY}; font-family: sans-serif;"
        f" font-size: 12px; padding: 12px;'>{overlay.BASEMAP_LOADING}</div>"
    )


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


def _figure(grid: Placed, chosen: TileView, box: Box, image: bytes) -> widgets.Image:
    """Draw the tile's crop with one box per observation its window keeps.

    Args:
        grid: Where the feature's grid falls on the mosaic.
        chosen: The tile on show.
        box: The lon/lat box the crop covers.
        image: The crop as PNG bytes.

    Returns:
        The figure as a widget.
    """
    figure, axis = plt.subplots(figsize=MAP_FIGURE_SIZE)
    basemap.mosaic(axis, box, image)
    lon, lat = grid.tile(chosen.stats.row, chosen.stats.column)
    axis.plot(lon, lat, color=TILE_EDGE, linewidth=TILE_WIDTH)
    colours = _boxes(axis, grid, chosen)
    axis.set_title(f"{chosen.name}  -  what its window keeps", fontsize=12, loc="left")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.tick_params(labelsize=8)
    axis.legend(
        handles=[
            Line2D([], [], color=colour, linewidth=BOX_WIDTH, label=label)
            for label, colour in colours.items()
        ],
        fontsize=8,
        loc="upper left",
        bbox_to_anchor=(0.0, -0.08),
        ncols=3,
        frameon=False,
    )
    figure.tight_layout()
    return panels.rendered(figure)


def _boxes(axis: Axes, grid: Placed, chosen: TileView) -> dict[str, tuple]:
    """Box the ground every observation the window keeps reached on the tile.

    Args:
        axis: The panel to draw on.
        grid: Where the feature's grid falls on the mosaic.
        chosen: The tile on show.

    Returns:
        The colour each instrument set was drawn in, by set label, for the
        legend.
    """
    track, stats = chosen.track, chosen.stats
    colours = panels.colours(series.over_tile(track))
    drawn: dict[str, tuple] = {}
    for index in chosen.survey.kept:
        label = track.labels[track.owners[index]]
        lon, lat = grid.ring(*_cells(track, stats.row, stats.column, index, grid.wide))
        axis.plot(lon, lat, color=colours[label], linewidth=BOX_WIDTH, alpha=BOX_ALPHA)
        drawn[label] = colours[label]
    return drawn


def _cells(
    track: Track, row: int, column: int, index: int, wide: int
) -> tuple[int, int, int, int]:
    """Find the block of grid cells one observation's footprint reaches.

    Args:
        track: The tile's admissible observations on one time axis.
        row: The tile's row on the feature's grid.
        column: Its column on the feature's grid.
        index: Where the observation sits on the time axis.
        wide: How many cells a tile holds along each axis.

    Returns:
        The westernmost column, southernmost row, and how many columns and
        rows the footprint spans, on the feature's own grid.
    """
    rows = [cell // wide for cell in track.cells[index]]
    columns = [cell % wide for cell in track.cells[index]]
    west = column * wide + min(columns)
    south = row * wide + min(rows)
    return west, south, max(columns) - min(columns) + 1, max(rows) - min(rows) + 1
