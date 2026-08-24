"""Which observations are a look at the tile rather than a clip of its edge."""

from __future__ import annotations

import math

from survey.models.tiles import Tile

# What an instrument the strategy says nothing about has to leave on a tile,
# which is a cell, so reaching the tile at all is the whole of what it is asked.
ANYTHING = 1


def least(admits: dict[str, int], iid: str, patch: Tile, cell_km2: float) -> int:
    """Work out the cells one instrument has to leave on one tile.

    The strategy names what a whole tile is asked for. A tile at the edge of a
    feature holds a corner of it rather than a whole block, and nothing can
    fill more of a tile than there is feature in it, so a tile holding less is
    asked for the same share of what it has. The share is rooted because a
    sounder's cells lie along a line, which shortens with the width of the
    ground rather than with the ground itself.

    Args:
        admits: The cells each instrument has to leave on a whole tile, by
            instrument id.
        iid: The instrument the observation belongs to.
        patch: The tile, holding its block of cells and the feature ground in
            it.
        cell_km2: How much ground one cell of the block covers.

    Returns:
        The cells it has to leave on that tile, never fewer than one.
    """
    whole = admits.get(iid, ANYTHING)
    share = patch.area_km2 / (patch.cells * cell_km2)
    return max(ANYTHING, round(whole * math.sqrt(share)))
