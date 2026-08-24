"""Which observations are a look at the tile rather than a clip of its edge."""

from __future__ import annotations

import math

from models.results import Event
from survey import configs
from survey.models.tiles import Tile


def crossing(crossing_km: float, patch: Tile, cell_km2: float) -> float:
    """Scale a strategy's crossing to the ground one tile really holds.

    A tile at the edge of a feature holds a corner of it rather than a whole
    block, and no line can run further than there is ground to run over. The
    strategy names what a whole tile is asked for, and a tile holding less of
    the feature is asked for the same share of what it has, so the bar stays
    the same demand everywhere rather than one no corner could ever clear.

    Args:
        crossing_km: How far a line has to run inside a whole tile.
        patch: The tile, holding its block of cells and the feature ground in
            it.
        cell_km2: How much ground one cell of the block covers.

    Returns:
        How far a line has to run inside that tile.
    """
    return crossing_km * math.sqrt(patch.area_km2 / (patch.cells * cell_km2))


def admissible(observation: Event, ground_km2: float, crossing_km: float) -> bool:
    """Report whether one observation says enough about a tile to be counted.

    Args:
        observation: The observation, which carries its swath width when it is
            a sounder track.
        ground_km2: The ground it lands inside the tile.
        crossing_km: How far a line has to run inside the tile, which only a
            sounder is measured against.

    Returns:
        True when the observation clears every floor asked of it.
    """
    # Under a minimum area
    if ground_km2 < configs.MIN_AREA_KM2:
        return False
    # Only SHARAD has a swath width, otherwise we are satisfied by this check
    if not observation.width_km:
        return True
    # The SHARAD line and not the width as to cross the tile
    crossed = ground_km2 / observation.width_km
    return crossed >= crossing_km
