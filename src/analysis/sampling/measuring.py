"""Reading the feature a search ran over, and what the instruments left on it."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from analysis.sampling.models.feature import FeatureStats, InstrumentReach
from analysis.selector import selecting
from analysis.selector.models.selection import SelectedFeature
from analysis.selector.models.survey import Study
from analysis.selector.models.track import Track


def measured_feature(study: Study) -> FeatureStats | None:
    """Read the feature a search of its own ran over.

    Args:
        study: What the search found over one feature.

    Returns:
        What it holds, or None where it held nothing to search at all.
    """
    if study.track is None:
        return None
    survey = study.survey
    return measured_looks(
        study.track, selecting.selected_feature(study), survey.taken if survey else ()
    )


def measured_looks(
    track: Track, window: SelectedFeature, taken: Sequence[int]
) -> FeatureStats:
    """Read what the instruments left on one feature, given the looks it keeps.

    Args:
        track: The feature's admissible observations on one time axis.
        window: The window it earned, or did not, as the selection reads it.
        taken: Where the observations it keeps sit on that axis, oldest first.

    Returns:
        What it holds.
    """
    # What each instrument left inside the window, and which of them each cell holds
    cells_by_iid: dict[str, set[int]] = {}
    observations_by_iid: dict[str, int] = {}
    iids_by_cell: dict[int, set[str]] = {}
    for index in taken:
        iid = track.iids[track.owners[index]]
        cells_by_iid.setdefault(iid, set()).update(track.cells[index])
        observations_by_iid[iid] = observations_by_iid.get(iid, 0) + 1
        for cell in track.cells[index].tolist():
            iids_by_cell.setdefault(cell, set()).add(iid)
    overlaps: dict[tuple[str, ...], float] = {}
    for cell in sorted(iids_by_cell):
        instrument_names = tuple(sorted(iids_by_cell[cell]))
        overlaps[instrument_names] = (
            overlaps.get(instrument_names, 0.0) + track.grid.cell_km2
        )
    # A pixel is the same size whether or not its look was chosen, so every
    # observation offered to the feature is read and not only the ones kept
    pixel_km2: dict[str, float] = {}
    for index, owner in enumerate(track.owners):
        iid = track.iids[owner]
        observation = track.observations[index]
        if iid not in pixel_km2 and observation.pixels and observation.own_km2:
            pixel_km2[iid] = observation.own_km2 / observation.pixels
    # What the window was offered, against what it kept of it
    held = sum(
        1 for index in range(len(track.observations)) if _inside(track, window, index)
    )
    kept = sum(1 for index in taken if _inside(track, window, index))
    return FeatureStats(
        area_km2=track.grid.area_km2,
        kept=window.kept,
        start=window.start,
        end=window.end,
        days=window.days,
        geo_mean=window.geo_mean,
        taken=len(taken),
        dropped=held - kept,
        refused=sum(
            1
            for observation, _, _ in track.refused
            if window.kept and window.start <= observation.t_start <= window.end
        ),
        turned_away=len(track.refused),
        offered=dict(Counter(track.iids[owner] for owner in track.owners)),
        pixel_km2=pixel_km2,
        reached={
            iid: InstrumentReach(
                km2=len(cells_reached) * track.grid.cell_km2,
                pixels=_pixels_landed(track, taken, iid),
                observations_taken=observations_by_iid[iid],
            )
            for iid, cells_reached in cells_by_iid.items()
        },
        overlaps=dict(sorted(overlaps.items(), key=lambda ground: -ground[1])),
    )


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


def instruments_searched(track: Track) -> list[str]:
    """Name every instrument the searched feature holds, in the order drawn.

    Args:
        track: The feature's admissible observations on one time axis.

    Returns:
        Each instrument once, in the order the coverage names its sets.
    """
    return list(dict.fromkeys(track.iids))


def _inside(track: Track, window: SelectedFeature, index: int) -> bool:
    """Say whether one observation was taken while the window was open.

    Args:
        track: The feature's admissible observations on one time axis.
        window: The window it earned, or did not, as the selection reads it.
        index: Where the observation sits on that axis.

    Returns:
        Whether the window holds it, and False where the feature earned none.
    """
    if not window.kept:
        return False
    return window.start <= track.observations[index].t_start <= window.end


def _pixels_landed(track: Track, taken: Sequence[int], iid: str) -> float | None:
    """Add up the pixels one instrument landed on the feature inside its window.

    Args:
        track: The feature's admissible observations on one time axis.
        taken: Where the observations it keeps sit on that axis.
        iid: The instrument to count.

    Returns:
        The pixels it landed there, or None when any of its observations carries none.
    """
    total = 0.0
    for index in taken:
        if track.iids[track.owners[index]] != iid:
            continue
        observation = track.observations[index]
        if observation.pixels is None or not observation.own_km2:
            return None
        ground_km2 = len(track.cells[index]) * track.grid.cell_km2
        total += observation.pixels * ground_km2 / observation.own_km2
    return total
