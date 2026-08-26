"""Reading every tile a search ran over, and what the instruments left on it."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

from models.results import Event
from prediction.models.tiles import Reach, TileStats
from survey.models.study import Study
from survey.models.survey import Survey
from survey.models.track import Track


def measured(study: Study) -> list[TileStats]:
    """Read every tile the search ran over.

    Args:
        study: What the search found over one feature.

    Returns:
        One entry per tile it ran over, in the order the patchwork lays them out.
    """
    return [
        _tile(study, track, picked)
        for track, picked in zip(study.tracks, study.surveys, strict=True)
    ]


def held(picked: Survey | None) -> tuple[int, ...]:
    """Name every observation the tile keeps, in time order.

    Args:
        picked: The window it earned, or None when it earned none.

    Returns:
        The window's own observations and what came from outside it, oldest first.
    """
    if picked is None:
        return ()
    return tuple(sorted(set(picked.kept) | set(picked.standing)))


def shared(overlaps: Mapping[tuple[str, ...], float]) -> dict[int, float]:
    """Add up the ground each number of instruments reaches at once.

    Args:
        overlaps: The ground each set of instruments reaches, counting a cell once.

    Returns:
        The ground in square kilometres, by how many instruments reach it, fewest first.
    """
    counted: dict[int, float] = {}
    for names, km2 in overlaps.items():
        counted[len(names)] = counted.get(len(names), 0.0) + km2
    return dict(sorted(counted.items()))


def instruments(study: Study) -> list[str]:
    """Name every instrument the searched tiles hold, in the order drawn.

    Args:
        study: What the search found over one feature.

    Returns:
        Each instrument once, in the order the coverage names its sets.
    """
    named = [iid for track in study.tracks for iid in track.iids]
    return list(dict.fromkeys(named))


def _tile(study: Study, track: Track, picked: Survey | None) -> TileStats:
    """Read one tile.

    Args:
        study: What the search found over the feature the tile belongs to.
        track: The tile's admissible observations on one time axis.
        picked: The window it earned, or None when it earned none.

    Returns:
        The tile.
    """
    row, column = divmod(track.tile, study.patchwork.across)
    kept = held(picked)
    # What each instrument left inside the window, and which of them each cell holds
    cells: dict[str, set[int]] = {}
    counted: dict[str, list[Event]] = {}
    here: list[set[str]] = [set() for _ in range(track.grid)] if kept else []
    for index in kept:
        iid = track.iids[track.owners[index]]
        cells.setdefault(iid, set()).update(track.cells[index])
        counted.setdefault(iid, []).append(track.observations[index])
        for cell in track.cells[index]:
            here[cell].add(iid)
    overlaps: dict[tuple[str, ...], float] = {}
    for reaching in here:
        if reaching:
            names = tuple(sorted(reaching))
            overlaps[names] = overlaps.get(names, 0.0) + track.cell_km2
    return TileStats(
        tile=track.tile,
        row=row,
        column=column,
        area_km2=track.area_km2,
        kept=picked is not None,
        start=picked.start if picked else None,
        end=picked.end if picked else None,
        days=picked.days if picked else 0.0,
        geo_mean=picked.geo_mean if picked else 0.0,
        taken=len(kept),
        dropped=picked.dropped if picked else 0,
        refused=sum(
            1
            for observation in track.refused
            if picked and picked.start <= observation.t_start <= picked.end
        ),
        turned_away=len(track.refused),
        offered=dict(Counter(track.iids[owner] for owner in track.owners)),
        reached={
            iid: Reach(
                km2=len(filled) * track.cell_km2,
                pixels=_landed(track, picked, iid),
                taken=len(counted[iid]),
            )
            for iid, filled in cells.items()
        },
        overlaps=dict(sorted(overlaps.items(), key=lambda ground: -ground[1])),
    )


def _landed(track: Track, picked: Survey, iid: str) -> float | None:
    """Add up the pixels one instrument landed on the tile inside its window.

    Args:
        track: The tile's admissible observations on one time axis.
        picked: The window they are counted inside.
        iid: The instrument to count.

    Returns:
        The pixels it landed there, or None when any of its observations carries none.
    """
    total = 0.0
    for index in held(picked):
        if track.iids[track.owners[index]] != iid:
            continue
        observation = track.observations[index]
        if observation.pixels is None or not observation.own_km2:
            return None
        ground_km2 = len(track.cells[index]) * track.cell_km2
        total += observation.pixels * ground_km2 / observation.own_km2
    return total
