"""The mosaic under a feature: fetching one crop of it, and drawing it."""

from __future__ import annotations

import io
import threading
from collections.abc import Callable
from functools import lru_cache
from html import escape

import httpx
import ipywidgets as widgets
from matplotlib import image as reading
from matplotlib.axes import Axes

from coverage.utils import geodesy
from visualization.common import panels
from visualization.feature.plots.placing import Box

# The global mosaic a feature is drawn on, served as WMS by the USGS.
BASEMAP_URL = "https://planetarymaps.usgs.gov/cgi-bin/mapserv"
BASEMAP_MAP = "/maps/mars/mars_simp_cyl.map"
BASEMAP_LAYER = "THEMIS"
BASEMAP_PIXELS = 900
BASEMAP_TIMEOUT = 30.0
BASEMAP_FAILED = "The basemap could not be fetched: {reason}"
BASEMAP_LOADING = "Fetching the basemap..."
BASEMAP_CACHE = 32

# How large the note standing in for the map is drawn while it is fetched.
PLACEHOLDER = "320px"

NO_BOX = "this feature has no lon/lat box to crop the mosaic to"


def fetched(box: Box, draw: Callable[[bytes], widgets.Widget]) -> widgets.Box:
    """Claim the space one crop goes in and fill it off the thread that fetches it.

    Args:
        box: The lon/lat box to crop the mosaic to.
        draw: What to draw once the crop arrives, given it as PNG bytes.

    Returns:
        A box holding the loading note, which the fetch replaces.
    """
    space = widgets.Box([_note(BASEMAP_LOADING)])

    def fill() -> None:
        """Crop the mosaic and put what it draws in the claimed space."""
        try:
            image = crop(box)
        except Exception as exc:
            space.children = (panels.unavailable(BASEMAP_FAILED.format(reason=exc)),)
            return
        space.children = (draw(image),)

    threading.Thread(target=fill, daemon=True).start()
    return space


def draw(axis: Axes, box: Box, image: bytes) -> None:
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
    axis.set_aspect(1.0 / geodesy.longitude_stretch(box.centre_lat))
    axis.set_xlim(box.west, box.east)
    axis.set_ylim(box.south, box.north)
    # A footprint reaching well past the crop is cut to it rather than framed
    axis.autoscale(False)


def crop(box: Box) -> bytes:
    """Fetch the mosaic over one lon/lat box.

    Args:
        box: The box to draw.

    Returns:
        The image as PNG bytes.
    """
    tall = box.north - box.south
    wide = (box.east - box.west) * geodesy.longitude_stretch(box.centre_lat)
    longest = max(wide, tall)
    return _fetch(
        box,
        (
            max(1, round(BASEMAP_PIXELS * wide / longest)),
            max(1, round(BASEMAP_PIXELS * tall / longest)),
        ),
    )


@lru_cache(maxsize=BASEMAP_CACHE)
def _fetch(box: Box, size: tuple[int, int]) -> bytes:
    """Fetch one basemap view.

    Args:
        box: The lon/lat box to draw.
        size: The width and height to draw them at, in pixels.

    Returns:
        The image as PNG bytes.

    Raises:
        ValueError: When the service answers with anything but an image.
    """
    response = httpx.get(
        BASEMAP_URL,
        params={
            "map": BASEMAP_MAP,
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetMap",
            "LAYERS": BASEMAP_LAYER,
            "STYLES": "",
            "SRS": "EPSG:4326",
            "BBOX": ",".join(
                f"{bound:.4f}" for bound in (box.west, box.south, box.east, box.north)
            ),
            "WIDTH": size[0],
            "HEIGHT": size[1],
            "FORMAT": "image/png",
        },
        timeout=BASEMAP_TIMEOUT,
        follow_redirects=True,
    )
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("image/"):
        raise ValueError(response.text.strip()[:200])
    return response.content


def _note(text: str) -> widgets.HTML:
    """Set a note in the space the map will fill.

    Args:
        text: The line to set.

    Returns:
        The note, squared off to the space the map is fitted into.
    """
    return widgets.HTML(
        f"<div style='width: {PLACEHOLDER}; height: {PLACEHOLDER};"
        f" display: flex; align-items: center; justify-content: center;"
        f" box-sizing: border-box; padding: 10px; text-align: center;"
        f" background: #f2f2f2; border: 1px solid #d8d8d8; border-radius: 4px;"
        f" color: {panels.GREY}; font-family: sans-serif; font-size: 12px;'>"
        f"{escape(text)}</div>"
    )
