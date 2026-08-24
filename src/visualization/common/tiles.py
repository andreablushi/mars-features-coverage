"""What one tile of a feature holds, read off the search that ran over it."""

from __future__ import annotations

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
        km2: The ground it reaches, counting a cell once however often it was
            revisited.
        pixels: The pixels it landed there, counting a revisit again, or None
            when any of its observations carries no pixel count.
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
        row: Which row of the grid it sits in, counting north from the south
            edge.
        column: Which column it sits in, counting east from the west edge.
        area_km2: How much of the feature it holds.
        kept: Whether it earned a window worth keeping.
        start: When the earliest observation in its window was taken, or None
            when it earned none.
        end: When the latest one was taken, or None when it earned none.
        days: How long its window lasts.
        reach: How much of the tile its window reaches, as the search scores
            it.
        taken: How many observations the window keeps.
        dropped: How many the window dropped as repeats of ground it held.
        refused: How many looks fell inside the window but were too small for
            the tile.
        turned_away: How many looks were too small for the tile at all.
        reached: What each instrument left inside the window, by instrument.
        overlaps: How much ground each set of instruments reaches between them,
            by the instruments really there, most ground first.
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
    reached: dict[str, Reach]
    overlaps: dict[tuple[str, ...], float]


def measured(study: Study) -> list[TileStats]:
    """Read every tile the search ran over.

    Args:
        study: What the search found over one feature.

    Returns:
        One entry per tile it ran over, in the order the patchwork lays them
        out.
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
        taken=len(picked.kept) if picked else 0,
        dropped=picked.dropped if picked else 0,
        refused=_refused(track, picked),
        turned_away=len(track.refused),
        reached=_reached(track, picked),
        overlaps=_overlaps(track, picked),
    )


def _refused(track: Track, picked: Survey | None) -> int:
    """Count the looks that fell inside a window but were too small to count.

    Args:
        track: The tile's admissible observations on one time axis.
        picked: The window they are counted inside, or None for no window.

    Returns:
        How many of them there were.
    """
    if picked is None:
        return 0
    return sum(
        1
        for observation in track.refused
        if picked.start <= observation.t_start <= picked.end
    )


def _reached(track: Track, picked: Survey | None) -> dict[str, Reach]:
    """Work out what each instrument left on the tile inside its window.

    Args:
        track: The tile's admissible observations on one time axis.
        picked: The window they are counted inside, or None for no window.

    Returns:
        What each instrument that appears in the window left, by instrument.
    """
    if picked is None:
        return {}
    cells: dict[str, set[int]] = {}
    counted: dict[str, list[Event]] = {}
    for index in picked.kept:
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

    A footprint's pixels are spread evenly over the ground it covers, so the
    share of them that fell on the tile is the share of its ground that did.

    Args:
        track: The tile's admissible observations on one time axis.
        picked: The window they are counted inside.
        iid: The instrument to count.

    Returns:
        The pixels it landed there, or None when any of its observations
        carries none.
    """
    total = 0.0
    for index in picked.kept:
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
        The ground in square kilometres, by the instruments that reach it,
        named in order and most ground first. A cell counts once, so the
        grounds do not overlap and add up to what the window covers.
    """
    if picked is None:
        return {}
    here: list[set[str]] = [set() for _ in range(track.grid)]
    for index in picked.kept:
        iid = track.iids[track.owners[index]]
        for cell in track.cells[index]:
            here[cell].add(iid)
    found: dict[tuple[str, ...], float] = {}
    for reaching in here:
        if reaching:
            names = tuple(sorted(reaching))
            found[names] = found.get(names, 0.0) + track.cell_km2
    return dict(sorted(found.items(), key=lambda ground: -ground[1]))


def instruments(study: Study) -> list[str]:
    """Name every instrument the searched tiles hold, in the order drawn.

    Args:
        study: What the search found over one feature.

    Returns:
        Each instrument once, in the order the coverage names its sets.
    """
    named = [iid for track in study.tracks for iid in track.iids]
    return list(dict.fromkeys(named))
