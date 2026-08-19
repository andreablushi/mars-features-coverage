"""The ground under a feature, as ODE published it, for a look at the place."""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from html import escape

import httpx
import ipywidgets as widgets

from download import configs as download_configs
from models.results import Event, SetCoverage
from visualization import configs


def ground(coverage: Sequence[SetCoverage]) -> widgets.Widget:
    """Show the ground the feature sits on, drawn from the record itself.

    Args:
        coverage: The feature's instrument sets, at least one of them loaded.

    Returns:
        The ODE browse image of the observation reaching most of the feature,
        captioned with the product it came from, or a note in its place when
        ODE has no browse image to give.
    """
    event = _widest(coverage)
    picture = _fetch(event.pdsid) if event else None
    if picture is None:
        return _note("ODE published no browse image for this feature.")
    caption = f"{event.iid} {event.pt} {event.pdsid}, {event.t_start:%Y-%m-%d}"
    return widgets.VBox(
        [
            widgets.Image(
                value=picture,
                format="png",
                layout=widgets.Layout(height=configs.BASEMAP_HEIGHT, width="auto"),
            ),
            _note(caption),
        ]
    )


def _widest(coverage: Sequence[SetCoverage]) -> Event | None:
    """Return the observation reaching most of the feature.

    Args:
        coverage: The feature's instrument sets, in any order.

    Returns:
        The single observation covering the most ground inside the feature, or
        None when no set observed it.
    """
    events = [event for entry in coverage for event in entry.events]
    return max(events, key=lambda event: event.own_km2, default=None)


@lru_cache(maxsize=configs.BASEMAP_CACHE)
def _fetch(pdsid: str) -> bytes | None:
    """Fetch one product's browse image from ODE.

    Args:
        pdsid: The PDS product identifier ODE knows the observation by.

    Returns:
        The PNG bytes, or None when ODE is unreachable or publishes no browse
        image for the product.
    """
    try:
        response = httpx.get(
            download_configs.ODE_BASE_URL,
            params={
                "query": "browse",
                "target": download_configs.ODE_TARGET,
                "pdsid": pdsid,
            },
            timeout=configs.BASEMAP_TIMEOUT,
        )
    except httpx.HTTPError:
        return None
    kind = response.headers.get("content-type", "")
    if response.status_code != 200 or not kind.startswith("image/"):
        return None
    return response.content


def _note(text: str) -> widgets.HTML:
    """Set a line of grey small print under or in place of the picture.

    Args:
        text: The line to set.

    Returns:
        The rendered line.
    """
    return widgets.HTML(
        f"<div style='color: {configs.GREY}; font-family: sans-serif; "
        f"font-size: 11px;'>{escape(text)}</div>"
    )
