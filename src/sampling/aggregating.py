"""Reading a run of tiles as one, whatever feature or dataset they belong to."""

from __future__ import annotations

from collections.abc import Sequence

from sampling.models.spread import Spread
from sampling.models.tiles import Aggregate, TileStats


def aggregate_tiles(searched: Sequence[TileStats], iids: Sequence[str]) -> Aggregate:
    """Read a run of tiles as one.

    Args:
        searched: The tiles the search ran over, in any order.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What they hold between them.
    """
    kept = [tile for tile in searched if tile.kept]
    # The grounds of the kept tiles are disjoint, so their overlaps add up
    overlaps: dict[tuple[str, ...], float] = {}
    for tile in kept:
        for instrument_names, km2 in tile.overlaps.items():
            overlaps[instrument_names] = overlaps.get(instrument_names, 0.0) + km2
    return Aggregate(
        searched=len(searched),
        kept=len(kept),
        area_km2=sum(tile.area_km2 for tile in searched),
        kept_km2=sum(tile.area_km2 for tile in kept),
        days=Spread.over([tile.days for tile in kept]),
        geo_mean=Spread.over([tile.geo_mean for tile in kept]),
        reached={
            iid: Spread.over(
                [
                    tile.reached[iid].km2 / tile.area_km2
                    if iid in tile.reached
                    else 0.0
                    for tile in kept
                    if tile.area_km2
                ]
            )
            for iid in iids
        },
        landed={iid: _pixels_landed(kept, iid) for iid in iids},
        pixels_per_look={iid: _pixels_per_look(kept, iid) for iid in iids},
        # A pixel is the same size wherever it falls, so every searched tile says
        pixel_km2={
            iid: Spread.over(
                [tile.pixel_km2[iid] for tile in searched if iid in tile.pixel_km2]
            )
            for iid in iids
        },
        overlaps=dict(sorted(overlaps.items(), key=lambda ground: -ground[1])),
    )


def _pixels_landed(kept: Sequence[TileStats], iid: str) -> Spread:
    """Read how many pixels one instrument lands on a tile, tile by tile.

    Args:
        kept: The tiles that earned a window.
        iid: The instrument to read.

    Returns:
        The pixels it lands on a tile, and empty when any tile carries no count.
    """
    landed: list[float] = []
    for tile in kept:
        reach = tile.reached.get(iid)
        if reach is None:
            landed.append(0.0)
        elif reach.pixels is None:
            return Spread.over([])
        else:
            landed.append(reach.pixels)
    return Spread.over(landed)


def _pixels_per_look(kept: Sequence[TileStats], iid: str) -> Spread:
    """Read how many pixels one observation of an instrument lands on a tile.

    A tile the instrument took nothing on says nothing about what one of its
    looks is worth, so it is left out rather than counted as nought.

    Args:
        kept: The tiles that earned a window.
        iid: The instrument to read.

    Returns:
        The pixels one of its observations landed, tile by tile, and empty when
        any tile it worked carries no pixel count.
    """
    per_look: list[float] = []
    for tile in kept:
        reach = tile.reached.get(iid)
        if reach is None or not reach.observations_taken:
            continue
        if reach.pixels is None:
            return Spread.over([])
        per_look.append(reach.pixels / reach.observations_taken)
    return Spread.over(per_look)
