"""The ODE browse image of one observation, for a look at the ground itself."""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

import httpx

from download import configs as download_configs
from models.results import Event, SetCoverage
from visualization import configs


def widest(coverage: Sequence[SetCoverage]) -> Event | None:
    """Return the observation reaching most of the feature.

    Args:
        coverage: The feature's instrument sets, in any order.

    Returns:
        The single observation covering the most ground inside the feature, or
        None when no set observed it.
    """
    events = [event for entry in coverage for event in entry.events]
    return max(events, key=lambda event: event.own_km2, default=None)


@lru_cache(maxsize=configs.BROWSE_CACHE)
def image(pdsid: str) -> bytes | None:
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
            timeout=configs.BROWSE_TIMEOUT,
        )
    except httpx.HTTPError:
        return None
    kind = response.headers.get("content-type", "")
    if response.status_code != 200 or not kind.startswith("image/"):
        return None
    return response.content
