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

    The strategy names what a whole tile is asked for. A tile at the edge of a
    feature holds a corner of it rather than a whole block, and nothing can
    land on more of a tile than there is feature in it, so a tile holding less
    is asked for the same share of what it has. An imager lays its pixels over
    ground, so its share falls with the ground; a sounder lays them along a
    line, which shortens with the width of the ground rather than with the
    ground itself, so its share is rooted.

    Args:
        admits: The pixels each instrument has to land on a whole tile, by
            instrument id.
        iid: The instrument the observation belongs to.
        patch: The tile, holding its block of cells and the feature ground in
            it.
        cell_km2: How much ground one cell of the block covers.
        linear: Whether the instrument lays its pixels along a line rather
            than over ground, as a sounder does.

    Returns:
        The pixels it has to land on that tile. An instrument the strategy
        names nowhere is asked for nothing, so it has only to reach the tile.
    """
    share = patch.area_km2 / (patch.cells * cell_km2)
    return admits.get(iid, 0.0) * (math.sqrt(share) if linear else share)


def landed(observation: Event, cells: int, cell_km2: float) -> float:
    """Work out the pixels one observation leaves on one tile.

    A footprint's pixels are spread evenly over the ground it covers, so the
    share of them that fell on the tile is the share of its ground that did.

    Args:
        observation: The observation, carrying the pixels it landed inside the
            feature and the ground it covers there.
        cells: How many of the tile's cells its footprint fills.
        cell_km2: How much ground one of them covers.

    Returns:
        The pixels it leaves there, and nothing at all when it covers no
        ground of the feature to spread them over.
    """
    if not observation.own_km2 or observation.pixels is None:
        return 0.0
    return observation.pixels * cells * cell_km2 / observation.own_km2
