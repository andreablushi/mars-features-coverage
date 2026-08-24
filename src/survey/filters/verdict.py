"""Asking a feature everything the dataset asks of it, a tile at a time."""

from __future__ import annotations

from collections.abc import Sequence

from models.results import Event, SetCoverage
from survey import algorithm
from survey.models import track as timeline
from survey.models.look import Look
from survey.models.strategy import Strategy
from survey.models.survey import Survey
from survey.models.track import Track
from survey.models.verdict import Verdict
from survey.utils import overlap, tiling

Found = list[tuple[Track, Survey]]


def assess(coverage: Sequence[SetCoverage], strategy: Strategy) -> Verdict:
    """Search every tile of a feature for the window a dataset would keep.

    Args:
        coverage: The feature's instrument sets, in any order.
        strategy: Which instruments a window has to hold and how much ground
            each of them has to reach.

    Returns:
        The verdict, holding the window every tile earned and every count
        behind them.
    """
    summary = coverage[0].summary
    if not summary.mask_cells:
        return _nothing()
    patchwork = tiling.split(
        summary.grid_side,
        summary.tiles_across,
        summary.cell_km2,
        summary.grid_mask,
    )
    tracks = timeline.build(coverage, patchwork, strategy.crossing_km)
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
        tiles=sum(1 for tile in patchwork.tiles if tile.area_km2),
        gridded=True,
        sounders_refused=_sounders(tracks),
        smallest=_smallest(found),
        refused=_refused(found),
        taken=sum(len(picked.kept) for _, picked in found),
        overlaps=_overlaps(found, len(strategy.demands)),
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
        tiles=0,
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


def _overlaps(found: Found, wanted: int) -> dict[int, float]:
    """Measure how much ground several instruments reach between them.

    How many are asked for is the strategy's own count of demands, since that
    is what the dataset wanted of the ground in the first place.

    Args:
        found: Every tile that earned a window, with the window it earned.
        wanted: How many sets have to reach a piece of ground for it to count.

    Returns:
        The ground in square kilometres reached by at least that many sets
        inside the windows, by that count, and nothing at all when no tile
        earned a window or the feature holds too few sets to reach it. The
        tiles are disjoint, so their ground adds up.
    """
    if not found or wanted > len(found[0][0].labels):
        return {}
    return {
        wanted: sum(
            overlap.ground(overlap.reached(track, picked), wanted, track.cell_km2)
            for track, picked in found
        )
    }


def _smallest(found: Found) -> dict[str, Look]:
    """Find the least an instrument's single observation covers in a window.

    An observation is judged on the tile it landed in, so it is measured there
    too: the ground it covers over the whole feature is a different number and
    would name a different observation as the thinnest.

    Args:
        found: Every tile that earned a window, with the window it earned.

    Returns:
        The smallest look each set left inside a window, by set name, least
        ground first, so that whatever the windows are thinnest on comes
        first.
    """
    least: dict[str, Look] = {}
    for track, picked in found:
        for index in picked.kept:
            observation = track.observations[index]
            label = track.labels[track.owners[index]]
            ground_km2 = len(track.cells[index]) * track.cell_km2
            held = least.get(label)
            if held is None or ground_km2 < held.ground_km2:
                least[label] = Look(
                    observation=observation,
                    ground_km2=ground_km2,
                    pixels=_landed(observation, ground_km2),
                )
    return dict(sorted(least.items(), key=lambda found: found[1].ground_km2))


def _landed(observation: Event, ground_km2: float) -> float | None:
    """Work out how many pixels an observation landed on one tile.

    A footprint's pixels are spread evenly over the ground it covers, so the
    share of them that fell on one tile is the share of its ground that did.

    Args:
        observation: The observation, carrying the pixels it landed on the
            whole feature.
        ground_km2: How much ground it covers inside the tile.

    Returns:
        The pixels it landed there, or None when none were counted for it.
    """
    if observation.pixels is None or not observation.own_km2:
        return None
    return observation.pixels * ground_km2 / observation.own_km2


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
