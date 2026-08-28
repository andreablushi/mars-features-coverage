"""What a tile was asked for, and the most it could ever answer with."""

from __future__ import annotations

from dataclasses import dataclass

from sampling.models.tiles import TileStats
from sampling.stats import tiles
from selector import relaxing
from selector.models.counter import Counter
from selector.models.track import Track
from utils.maths import ground
from visualization.common import surveys
from visualization.feature.picker import TileView


@dataclass(frozen=True, slots=True)
class Shortfall:
    """What one instrument is asked of a tile, and the most it brings there.

    Attributes:
        iid: The instrument.
        asked: The share of the tile it is asked to reach.
        windowed: The share it reaches in the best window, the ground bars lifted.
        whole: The share it reaches over the whole record, however long that runs.
        timeless: Whether the record answers for it rather than a window.
    """

    iid: str
    asked: float
    windowed: float
    whole: float
    timeless: bool


def best(chosen: TileView) -> list[Shortfall]:
    """Search one tile again with no ground asked, and read what it came back with.

    Args:
        chosen: The tile on show, and the strategy it was really searched under.

    Returns:
        What each instrument is asked and the most it brings, in the order the
        strategy names its constraints.
    """
    strategy = chosen.view.strategy
    study = surveys.studied(chosen.view.coverage, relaxing.unfloored(strategy))
    measured = {stats.tile: stats for stats in tiles.measured(study)}
    stats = measured.get(chosen.stats.tile)
    whole = _whole(chosen.track)
    return [
        Shortfall(
            iid=iid,
            asked=share,
            windowed=_reached(stats, iid),
            whole=whole.get(iid, 0.0),
            timeless=iid in strategy.timeless,
        )
        for constraint in strategy.constraints
        for iid, share in constraint.items()
    ]


def _whole(track: Track) -> dict[str, float]:
    """Read the most of a tile each instrument reaches over its whole record.

    Args:
        track: The tile's admissible observations on one time axis.

    Returns:
        The share each of them reaches, counting a cell once however often it flew.
    """
    counter = Counter.over(track, 0, len(track.observations) - 1)
    reached: dict[str, float] = {}
    for owner, iid in enumerate(track.iids):
        filled = ground.share(
            counter.cells_reached[owner], track.cell_km2, track.area_km2
        )
        reached[iid] = max(reached.get(iid, 0.0), filled)
    return reached


def _reached(stats: TileStats | None, iid: str) -> float:
    """Read what one instrument left on a tile the unfloored search kept.

    Args:
        stats: The tile as that search left it, or None when it kept none.
        iid: The instrument to read.

    Returns:
        The share of the tile it reaches there, and nought where it reaches none.
    """
    if stats is None or not stats.kept or not stats.area_km2:
        return 0.0
    reach = stats.reached.get(iid)
    return reach.km2 / stats.area_km2 if reach else 0.0
