"""Which observations are a look at the tile rather than a clip of its edge."""

from __future__ import annotations

import math

from models.results import Event
from survey.models.tiles import Tile


def least(
    admits: dict[str, float],
    iid: str,
    patch: Tile,
    cell_km2: float,
    *,
    linear: bool = False,
) -> float:
    """Work out the pixels one instrument has to land on one tile.

    Args:
        admits: The pixels each instrument has to land on a whole tile, by iid.
        iid: The instrument the observation belongs to.
        patch: The tile, holding its block of cells and the feature ground in it.
        cell_km2: How much ground one cell of the block covers.
        linear: Whether the instrument lays its pixels along a line, as a sounder does.

    Returns:
        The pixels it has to land on that tile, and nothing where it is named nowhere.
    """
    share = patch.area_km2 / (patch.cells * cell_km2)
    return admits.get(iid, 0.0) * (math.sqrt(share) if linear else share)


def landed(observation: Event, cells: int, cell_km2: float) -> float:
    """Work out the pixels one observation leaves on one tile.

    Args:
        observation: The observation, carrying its pixels and the ground it covers.
        cells: How many of the tile's cells its footprint fills.
        cell_km2: How much ground one of them covers.

    Returns:
        The pixels it leaves there, and nothing where it covers no ground to spread.
    """
    if not observation.own_km2 or observation.pixels is None:
        return 0.0
    return observation.pixels * cells * cell_km2 / observation.own_km2
