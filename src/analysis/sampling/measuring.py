"""Reading the feature a search ran over, and what the instruments left on it."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from analysis.sampling.models.feature import FeatureStats, InstrumentReach
from analysis.sampling.models.study import Study
from analysis.selector.models.survey import Survey
from analysis.selector.models.track import Track


def measured_feature(study: Study) -> FeatureStats | None:
    """Read the feature the search ran over.

    Args:
        study: What the search found over one feature.

    Returns:
        What it holds, or None where it held nothing to search at all.
    """
    track = study.track
    if track is None:
        return None
    survey = study.survey
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
    # A pixel is the same size whether or not its look was chosen, so every
    # observation offered to the feature is read and not only the ones kept
    pixel_km2: dict[str, float] = {}
    for index, owner in enumerate(track.owners):
        iid = track.iids[owner]
        observation = track.observations[index]
        if iid not in pixel_km2 and observation.pixels and observation.own_km2:
            pixel_km2[iid] = observation.own_km2 / observation.pixels
    return FeatureStats(
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
        pixel_km2=pixel_km2,
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


def kept_observations(survey: Survey | None) -> tuple[int, ...]:
    """Name every observation the feature keeps, in time order.

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


def instruments_searched(study: Study) -> list[str]:
    """Name every instrument the searched feature holds, in the order drawn.

    Args:
        study: What the search found over one feature.

    Returns:
        Each instrument once, in the order the coverage names its sets.
    """
    if study.track is None:
        return []
    return list(dict.fromkeys(study.track.iids))


def _pixels_landed(track: Track, kept: Sequence[int], iid: str) -> float | None:
    """Add up the pixels one instrument landed on the feature inside its window.

    Args:
        track: The feature's admissible observations on one time axis.
        kept: Where the observations it keeps sit on that axis.
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
