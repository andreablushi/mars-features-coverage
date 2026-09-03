"""What a feature was asked for, and the most it could ever answer with."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from analysis.sampling import measuring
from analysis.sampling.models.feature import FeatureStats
from analysis.selector.artifacts import filter_config as filtering
from analysis.selector.models.counter import Counter
from analysis.utils.maths import ground
from analysis.visualization.common import surveys
from analysis.visualization.common.picker import Coverage


@dataclass(frozen=True, slots=True)
class Shortfall:
    """What one instrument is asked of a feature, and the most it brings there.

    Attributes:
        iid: The instrument.
        asked: The share of the feature it is asked to reach.
        windowed: The share it reaches in the best window, the ground bars lifted.
        whole: The share it reaches over the whole record, however long that runs.
        timeless: Whether the record answers for it rather than a window.
    """

    iid: str
    asked: float
    windowed: float
    whole: float
    timeless: bool


def best(coverage: Coverage) -> list[Shortfall]:
    """Search a feature again with no ground asked, and read what it came back with.

    Args:
        coverage: The feature on show, as the instrument sets it holds.

    Returns:
        What each instrument is asked and the most it brings, in the order the
        filter names its constraints.
    """
    criteria = filtering.FILTER
    track = surveys.studied(coverage, criteria).track
    if track is None:
        return []
    # The filter read as asking for a look and no ground, so a feature the search
    # refused still shows the window it came closest with
    unfloored = dataclasses.replace(
        criteria,
        unfloored=True,
        constraints=tuple(
            dict.fromkeys(constraint, 0.0) for constraint in criteria.constraints
        ),
    )
    stats = measuring.measured_feature(surveys.studied(coverage, unfloored))
    # The most each instrument reaches, counting a cell once however often it flew
    counter = Counter.over(track, 0, len(track.observations) - 1)
    whole: dict[str, float] = {}
    for owner, iid in enumerate(track.iids):
        filled = ground.share(
            counter.cells_reached[owner], track.grid.cell_km2, track.grid.area_km2
        )
        whole[iid] = max(whole.get(iid, 0.0), filled)
    return [
        Shortfall(
            iid=iid,
            asked=share,
            windowed=_reached(stats, iid),
            whole=whole.get(iid, 0.0),
            timeless=iid in criteria.timeless,
        )
        for constraint in criteria.constraints
        for iid, share in constraint.items()
    ]


def _reached(stats: FeatureStats | None, iid: str) -> float:
    """Read what one instrument left on a feature the unfloored search kept.

    Args:
        stats: The feature as that search left it, or None when it kept none.
        iid: The instrument to read.

    Returns:
        The share of the feature it reaches there, and nought where it reaches none.
    """
    if stats is None or not stats.kept:
        return 0.0
    reach = stats.reached.get(iid)
    return reach.km2 / stats.area_km2 if reach else 0.0
