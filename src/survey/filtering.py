"""Which observations are a look at the feature rather than a clip of its edge."""

from __future__ import annotations

from collections.abc import Sequence

from models.results import Event
from survey import configs


def admissible(event: Event, cells: Sequence[int], width_km: float) -> bool:
    """Report whether one observation says enough about a feature to be counted.

    A footprint that grazes a feature reports the edge it clipped rather than
    the feature, and there are two ways to be that small. Both are asked for.

    The ground it lands inside the feature has to be enough to crop something
    out of, which is a square kilometre. Measuring the crop in ground rather
    than in the instrument's own pixels is what lets one floor serve every
    instrument, since a pixel runs from a quarter of a metre across for HiRISE
    to a radar trace covering more than a square kilometre for SHARAD.

    It also has to fill more than a single cell of the feature's grid. That is
    the half of the rule that knows how big the feature is: the grid follows
    the cube root of the feature's width, so two cells is a tenth of a percent
    of a small crater and a hundredth of that of a continent. Ground alone
    cannot tell a sounder crossing a small crater from one clipping the corner
    of a large one, because both land about the same square kilometres inside.
    Cells can.

    A sounder is asked for one more thing, since neither floor can tell a track
    that crosses a feature from one that enters it and stops. Both land about
    the same ground inside, and both fill about as many cells, because a line
    fills few of them whatever it does. So a track has to run at least a tenth
    of the feature's width, which is the length it covers rather than the
    ground it covers.

    Args:
        event: The observation, carrying the ground it landed in the feature.
        cells: The feature's cells its footprint fills.
        width_km: How wide the feature is, which only a sounder is measured
            against.

    Returns:
        True when the observation clears every floor asked of it.
    """
    if len(cells) < configs.MIN_CELLS:
        return False
    if event.own_km2 < configs.MIN_AREA_KM2:
        return False
    return not event.width_km or _crosses(event, width_km)


def _crosses(event: Event, width_km: float) -> bool:
    """Report whether a sounder track runs far enough across the feature.

    The ground a track lays inside the feature is its length there times the
    swath it sounds, so dividing the one by the other gives back the length,
    with no track geometry to carry around.

    Args:
        event: The track, carrying the ground it laid and the swath it sounds.
        width_km: How wide the feature is.

    Returns:
        True when it ran at least the required share of that width.
    """
    crossed = event.own_km2 / event.width_km
    return crossed >= configs.MIN_CROSSING * width_km
