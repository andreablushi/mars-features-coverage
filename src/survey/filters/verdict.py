"""Asking a feature everything the dataset asks of it, a tile at a time."""

from __future__ import annotations

from collections.abc import Sequence

from models.results import Event, SetCoverage
from survey import algorithm, configs, strategies
from survey.models import track as timeline
from survey.models.strategy import Strategy
from survey.models.survey import Survey
from survey.models.track import Track
from survey.models.verdict import Verdict
from survey.utils import overlap, tiling

Found = list[tuple[Track, Survey]]


def assess(
    coverage: Sequence[SetCoverage], strategy: Strategy | None = None
) -> Verdict:
    """Search every tile of a feature for the window a dataset would keep.

    Args:
        coverage: The feature's instrument sets, in any order.
        strategy: Which instruments a window has to hold and how much ground
            each of them has to reach, or None for the configured one.

    Returns:
        The verdict, holding the window every tile earned and every count
        behind them.
    """
    strategy = strategy or strategies.named(configs.STRATEGY)
    summary = coverage[0].summary
    if not summary.mask_cells:
        return _nothing()
    patchwork = tiling.split(summary.grid_side, summary.tiles_across, summary.cell_km2)
    tracks = timeline.build(coverage, patchwork)
    if not tracks:
        return _nothing()
    found: Found = [
        (track, picked)
        for track in tracks
        if (picked := algorithm.search(track, strategy)) is not None
    ]
    return Verdict(
        surveys=[picked for _, picked in found],
        across=patchwork.across,
        gridded=True,
        sounders_refused=_sounders(tracks),
        smallest=_smallest(found),
        refused=_refused(found),
        taken=sum(picked.observations for _, picked in found),
        overlaps=_overlaps(found),
    )


def _nothing() -> Verdict:
    """Report a feature no instrument set ever filled a cell of.

    Returns:
        The verdict, which is the one a feature can reach before it is
        searched at all.
    """
    return Verdict(
        surveys=[],
        across=0,
        gridded=False,
        sounders_refused=0,
        smallest={},
        refused=0,
        taken=0,
        overlaps={},
    )


def _sounders(tracks: Sequence[Track]) -> int:
    """Count the sounder tracks that were too small to count.

    Args:
        tracks: The feature's tiles, each on its own time axis.

    Returns:
        How many of the looks left off the axes were sounder tracks, counting
        a track once per tile it was turned away from.
    """
    return sum(
        bool(observation.width_km) for track in tracks for observation in track.refused
    )


def _overlaps(found: Found) -> dict[int, float]:
    """Measure how much ground several instruments reach between them.

    Args:
        found: Every tile that earned a window, with the window it earned.

    Returns:
        The ground in square kilometres reached by at least that many sets
        inside the windows, by set count, counting only as many sets as the
        feature has, and nothing at all when no tile earned a window. The
        tiles are disjoint, so their ground adds up.
    """
    if not found:
        return {}
    sets = len(found[0][0].labels)
    return {
        wanted: sum(
            overlap.ground(overlap.reached(track, picked), wanted, track.cell_km2)
            for track, picked in found
        )
        for wanted in configs.OVERLAP_SETS
        if wanted <= sets
    }


def _smallest(found: Found) -> dict[str, Event]:
    """Find the least an instrument's single observation covers in a window.

    Args:
        found: Every tile that earned a window, with the window it earned.

    Returns:
        The smallest look each set left inside a window, by set name, least
        ground first, so that whatever the windows are thinnest on comes
        first.
    """
    least: dict[str, Event] = {}
    for track, picked in found:
        for owner, observation in zip(track.owners, track.observations, strict=True):
            if picked.start <= observation.t_start <= picked.end:
                label = track.labels[owner]
                held = least.get(label)
                if held is None or observation.own_km2 < held.own_km2:
                    least[label] = observation
    return dict(sorted(least.items(), key=lambda found: found[1].own_km2))


def _refused(found: Found) -> int:
    """Count what the windows turned away for being too small.

    Args:
        found: Every tile that earned a window, with the window it earned.

    Returns:
        How many looks were turned away over those stretches of time.
    """
    return sum(
        1
        for track, picked in found
        for observation in track.refused
        if picked.start <= observation.t_start <= picked.end
    )
