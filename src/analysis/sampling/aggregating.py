"""Reading a run of tiles as one, whatever feature or dataset they belong to."""

from __future__ import annotations

from collections.abc import Sequence

from analysis.sampling import configs
from analysis.sampling.models.spread import Spread
from analysis.sampling.models.tiles import Aggregate, TileStats


def aggregate_tiles(searched: Sequence[TileStats], iids: Sequence[str]) -> Aggregate:
    """Read a run of tiles as one.

    Args:
        searched: The tiles the search ran over, in any order.
        iids: The instruments to report on, in the order to report them.

    Returns:
        What they hold between them, leaving out any tile reading more ground
        than it holds.
    """
    read = [tile for tile in searched if plausible(tile)]
    kept = [tile for tile in read if tile.kept]
    # The grounds of the kept tiles are disjoint, so their overlaps add up
    overlaps: dict[tuple[str, ...], float] = {}
    for tile in kept:
        for instrument_names, km2 in tile.overlaps.items():
            overlaps[instrument_names] = overlaps.get(instrument_names, 0.0) + km2
    return Aggregate(
        searched=len(read),
        kept=len(kept),
        area_km2=sum(tile.area_km2 for tile in read),
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
                [tile.pixel_km2[iid] for tile in read if iid in tile.pixel_km2]
            )
            for iid in iids
        },
        overlaps=dict(sorted(overlaps.items(), key=lambda ground: -ground[1])),
    )


def plausible(tile: TileStats) -> bool:
    """Say whether a tile reports no more ground than it holds.

    Args:
        tile: One tile the search ran over.

    Returns:
        Whether every share it reports sits inside the ceiling.
    """
    if not tile.area_km2:
        return True
    shares = [reach.km2 / tile.area_km2 for reach in tile.reached.values()]
    shares.append(sum(tile.overlaps.values()) / tile.area_km2)
    shares.append(tile.geo_mean)
    return max(shares) <= configs.SHARE_CEILING


def _pixels_landed(kept: Sequence[TileStats], iid: str) -> Spread:
    """Read how many pixels one instrument lands on a tile, tile by tile.

    Args:
        kept: The tiles that earned a window.
        iid: The instrument to read.

    Returns:
        The pixels it lands on a tile, leaving out a tile carrying no count.
    """
    landed: list[float] = []
    for tile in kept:
        reach = tile.reached.get(iid)
        if reach is None:
            landed.append(0.0)
        elif reach.pixels is not None:
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
        The pixels one of its observations landed, tile by tile, leaving out a
        tile carrying no pixel count.
    """
    per_look: list[float] = []
    for tile in kept:
        reach = tile.reached.get(iid)
        if reach is None or not reach.observations_taken or reach.pixels is None:
            continue
        per_look.append(reach.pixels / reach.observations_taken)
    return Spread.over(per_look)
