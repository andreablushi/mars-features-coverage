"""Reading every tile a search ran over, and what the instruments left on it."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from analysis.sampling.models.study import Study
from analysis.sampling.models.tiles import InstrumentReach, TileStats
from analysis.selector.models.survey import Survey
from analysis.selector.models.track import Track


def measured_tiles(study: Study) -> list[TileStats]:
    """Read every tile the search ran over.

    Args:
        study: What the search found over one feature.

    Returns:
        One entry per tile it ran over, in the order the grid lays them out.
    """
    return [
        _tile(study, track, survey)
        for track, survey in zip(study.tracks, study.surveys, strict=True)
    ]


def kept_observations(survey: Survey | None) -> tuple[int, ...]:
    """Name every observation the tile keeps, in time order.

    Args:
        survey: The window it earned, or None when it earned none.

    Returns:
        The window's own observations and what came from outside it, oldest first.
    """
    if survey is None:
        return ()
    return tuple(sorted(set(survey.kept) | set(survey.standing)))


def ground_by_instrument_count(
    overlaps: Mapping[tuple[str, ...], float],
) -> dict[int, float]:
    """Add up the ground each number of instruments reaches at once.

    Args:
        overlaps: The ground each set of instruments reaches, counting a cell once.

    Returns:
        The ground in square kilometres, by how many instruments reach it, fewest first.
    """
    summed: dict[int, float] = {}
    for instrument_names, km2 in overlaps.items():
        summed[len(instrument_names)] = summed.get(len(instrument_names), 0.0) + km2
    return dict(sorted(summed.items()))


def tiles_holding_feature(study: Study) -> int:
    """Count the tiles holding any of the feature.

    Args:
        study: What the search found over one feature.

    Returns:
        How many of them a window could have been found over.
    """
    return sum(1 for tile in study.grid.tiles if tile.area_km2)


def instruments_searched(study: Study) -> list[str]:
    """Name every instrument the searched tiles hold, in the order drawn.

    Args:
        study: What the search found over one feature.

    Returns:
        Each instrument once, in the order the coverage names its sets.
    """
    every_iid = [iid for track in study.tracks for iid in track.iids]
    return list(dict.fromkeys(every_iid))


def _tile(study: Study, track: Track, survey: Survey | None) -> TileStats:
    """Read one tile.

    Args:
        study: What the search found over the feature the tile belongs to.
        track: The tile's admissible observations on one time axis.
        survey: The window it earned, or None when it earned none.

    Returns:
        The tile.
    """
    row, column = divmod(track.tile, study.grid.across)
    kept = kept_observations(survey)
    # What each instrument left inside the window, and which of them each cell holds
    cells_by_iid: dict[str, set[int]] = {}
    observations_by_iid: dict[str, int] = {}
    iids_by_cell: dict[int, set[str]] = {}
    for index in kept:
        iid = track.iids[track.owners[index]]
        cells_by_iid.setdefault(iid, set()).update(track.cells[index])
        observations_by_iid[iid] = observations_by_iid.get(iid, 0) + 1
        for cell in track.cells[index].tolist():
            iids_by_cell.setdefault(cell, set()).add(iid)
    overlaps: dict[tuple[str, ...], float] = {}
    for cell in sorted(iids_by_cell):
        instrument_names = tuple(sorted(iids_by_cell[cell]))
        overlaps[instrument_names] = (
            overlaps.get(instrument_names, 0.0) + track.cell_km2
        )
    return TileStats(
        tile=track.tile,
        row=row,
        column=column,
        area_km2=track.area_km2,
        kept=survey is not None,
        start=survey.start if survey else None,
        end=survey.end if survey else None,
        days=survey.days if survey else 0.0,
        geo_mean=survey.geo_mean if survey else 0.0,
        taken=len(kept),
        dropped=survey.dropped if survey else 0,
        refused=sum(
            1
            for observation, _, _ in track.refused
            if survey and survey.start <= observation.t_start <= survey.end
        ),
        turned_away=len(track.refused),
        offered=dict(Counter(track.iids[owner] for owner in track.owners)),
        pixel_km2=_ground_one_pixel_covers(track),
        reached={
            iid: InstrumentReach(
                km2=len(cells_reached) * track.cell_km2,
                pixels=_pixels_landed(track, kept, iid),
                observations_taken=observations_by_iid[iid],
            )
            for iid, cells_reached in cells_by_iid.items()
        },
        overlaps=dict(sorted(overlaps.items(), key=lambda ground: -ground[1])),
    )


def _pixels_landed(track: Track, kept: Sequence[int], iid: str) -> float | None:
    """Add up the pixels one instrument landed on the tile inside its window.

    Args:
        track: The tile's admissible observations on one time axis.
        kept: Where the observations the tile keeps sit on that axis.
        iid: The instrument to count.

    Returns:
        The pixels it landed there, or None when any of its observations carries none.
    """
    total = 0.0
    for index in kept:
        if track.iids[track.owners[index]] != iid:
            continue
        observation = track.observations[index]
        if observation.pixels is None or not observation.own_km2:
            return None
        ground_km2 = len(track.cells[index]) * track.cell_km2
        total += observation.pixels * ground_km2 / observation.own_km2
    return total


def _ground_one_pixel_covers(track: Track) -> dict[str, float]:
    """Read the ground one pixel of each instrument covers, off its observations.

    Every observation offered to the tile is read, not only the ones a window
    kept, since a pixel is the same size whether or not its look was chosen.

    Args:
        track: The tile's admissible observations on one time axis.

    Returns:
        The ground one pixel covers, by instrument, leaving out any instrument
        none of whose observations says.
    """
    found: dict[str, float] = {}
    for index, owner in enumerate(track.owners):
        iid = track.iids[owner]
        if iid in found:
            continue
        observation = track.observations[index]
        if observation.pixels and observation.own_km2:
            found[iid] = observation.own_km2 / observation.pixels
    return found
