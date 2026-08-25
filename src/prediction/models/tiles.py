"""What one tile of a feature holds, read off the search that ran over it."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from models.results import Event
from survey.models.study import Study
from survey.models.survey import Survey
from survey.models.track import Track


@dataclass(frozen=True, slots=True)
class Reach:
    """What one instrument left on one tile inside its window.

    Attributes:
        km2: The ground it reaches, counting a cell once however often it was revisited.
        pixels: The pixels it landed there, or None where any carries no count.
        taken: How many of its observations the window keeps.
    """

    km2: float
    pixels: float | None
    taken: int


@dataclass(frozen=True, slots=True)
class TileStats:
    """One tile of a feature, and what the search left on it.

    Attributes:
        tile: Which tile of the feature it is, as the patchwork numbers them.
        row: Which row of the grid it sits in, counting north from the south edge.
        column: Which column it sits in, counting east from the west edge.
        area_km2: How much of the feature it holds.
        kept: Whether it earned a window worth keeping.
        start: When the earliest observation in its window was taken, or None.
        end: When the latest one was taken, or None when it earned none.
        days: How long its window lasts.
        reach: How much of the tile its window reaches, as the search scores it.
        taken: How many observations the tile keeps, from the window and outside it.
        dropped: How many the window dropped as repeats of ground it held.
        refused: How many looks fell inside the window but were too small for the tile.
        turned_away: How many looks were too small for the tile at all.
        offered: How many observations of each instrument landed on the tile at all.
        reached: What each instrument left on the tile, by instrument.
        overlaps: The ground each set of instruments reaches, most ground first.
    """

    tile: int
    row: int
    column: int
    area_km2: float
    kept: bool
    start: datetime | None
    end: datetime | None
    days: float
    reach: float
    taken: int
    dropped: int
    refused: int
    turned_away: int
    offered: dict[str, int]
    reached: dict[str, Reach]
    overlaps: dict[tuple[str, ...], float]


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
    return TileStats(
        tile=track.tile,
        row=row,
        column=column,
        area_km2=track.area_km2,
        kept=picked is not None,
        start=picked.start if picked else None,
        end=picked.end if picked else None,
        days=picked.days if picked else 0.0,
        reach=picked.reach if picked else 0.0,
        taken=len(held(picked)),
        dropped=picked.dropped if picked else 0,
        refused=sum(
            1
            for observation in track.refused
            if picked and picked.start <= observation.t_start <= picked.end
        ),
        turned_away=len(track.refused),
        offered=dict(Counter(track.iids[owner] for owner in track.owners)),
        reached=_reached(track, picked),
        overlaps=_overlaps(track, picked),
    )


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


def _reached(track: Track, picked: Survey | None) -> dict[str, Reach]:
    """Work out what each instrument left on the tile inside its window.

    Args:
        track: The tile's admissible observations on one time axis.
        picked: The window they are counted inside, or None for no window.

    Returns:
        What each instrument that left anything on the tile left, by instrument.
    """
    if picked is None:
        return {}
    cells: dict[str, set[int]] = {}
    counted: dict[str, list[Event]] = {}
    for index in held(picked):
        iid = track.iids[track.owners[index]]
        cells.setdefault(iid, set()).update(track.cells[index])
        counted.setdefault(iid, []).append(track.observations[index])
    return {
        iid: Reach(
            km2=len(filled) * track.cell_km2,
            pixels=_landed(track, picked, iid),
            taken=len(counted[iid]),
        )
        for iid, filled in cells.items()
    }


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


def _overlaps(track: Track, picked: Survey | None) -> dict[tuple[str, ...], float]:
    """Work out how much ground each set of instruments reaches between them.

    Args:
        track: The tile's admissible observations on one time axis.
        picked: The window they are counted inside, or None for no window.

    Returns:
        The ground in square kilometres, by the instruments reaching it, most first.
    """
    if picked is None:
        return {}
    here: list[set[str]] = [set() for _ in range(track.grid)]
    for index in held(picked):
        iid = track.iids[track.owners[index]]
        for cell in track.cells[index]:
            here[cell].add(iid)
    found: dict[tuple[str, ...], float] = {}
    for reaching in here:
        if reaching:
            names = tuple(sorted(reaching))
            found[names] = found.get(names, 0.0) + track.cell_km2
    return dict(sorted(found.items(), key=lambda ground: -ground[1]))


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
