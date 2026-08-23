"""The best time window with most observations across multiple instruments."""

from __future__ import annotations

from survey import configs
from survey.filters import redundancy
from survey.models.survey import Survey
from survey.models.track import Track
from survey.models.window import Window
from survey.utils import measuring
from utils.maths import quantities


def search(track: Track) -> Survey | None:
    """Run the search over a timeline that has already been built.

    Args:
        track: The feature's admissible observations on one time axis.

    Returns:
        The chosen window, or None when no window inside the allowed span holds
        a sounder track at all.
    """
    # Early out: no sounder track ever flew over the feature, so there is no window.
    if not any(track.sounder):
        return None
    times, owners = track.times, track.owners
    sounder, cells = track.sounder, track.cells
    frontier: list[Window] = []

    #
    for wanted in range(len(track.labels), 0, -1):
        frontier, seen = [], set()
        # Rungs climb towards what the whole record reaches rather than towards
        # one, so the curve is sampled evenly whatever the feature can offer.
        _, whole, _ = measuring.counted(track, 0, len(track.observations) - 1)
        ceiling = measuring.mean(whole, track.totals, wanted)
        for step in range(configs.LEVELS + 1):
            level = (
                ceiling * step / configs.LEVELS
            )  # the first rung asks for the instruments alone

            # 3. Slide a window along the axis: widen right, then tighten left.
            counts, reached, inside = measuring.opened(len(track.totals), track.grid)
            found: Window | None = None
            sounders, left = 0, 0
            for right in range(len(track.observations)):
                measuring.hold(counts, reached, inside, owners[right], cells[right])
                sounders += sounder[right]
                while (
                    sounders  # a survey without a sounder track is no survey
                    and measuring.instruments(inside) >= wanted
                    and measuring.mean(reached, track.totals, wanted)
                    >= level - configs.ROUNDING
                ):
                    days = times[right] - times[left]
                    scored = measuring.mean(reached, track.totals, wanted)
                    if found is None or (days, -scored) < (found.days, -found.reach):
                        found = Window(
                            left, right, days, scored, measuring.instruments(inside)
                        )
                    measuring.release(
                        counts, reached, inside, owners[left], cells[left]
                    )
                    sounders -= sounder[left]
                    left += 1

            if found is None or found.days > configs.MAX_SPAN_DAYS:
                break  # asking for more ground can only ever ask for more days
            found = found.widened(track, wanted)  # a tie in time is free
            if (found.first, found.last) not in seen:
                seen.add((found.first, found.last))
                frontier.append(found)
        if frontier:
            break  # this many instruments do fit, so stop settling for fewer
    if not frontier:
        return None

    # 4. The knee: rescale both axes to nought and one, then take the point
    #    sitting furthest above the diagonal joining the ends of the curve.
    cost = quantities.unit([span.days for span in frontier])
    gain = quantities.unit([span.reach for span in frontier])
    lift = [ground - days for days, ground in zip(cost, gain, strict=True)]
    turn = max(range(len(lift)), key=lift.__getitem__)
    # Nothing above the diagonal means ground is speeding up rather than
    # running out, so there is no knee to find and nothing to gain by stopping
    # early: take every day the cap allows.
    knee = lift[turn] > 0.0
    picked = frontier[turn] if knee else frontier[-1]

    return Survey(
        start=track.observations[picked.first].t_start,
        end=track.observations[picked.last].t_start,
        days=picked.days,
        reach=picked.reach,
        instruments=picked.instruments,
        observations=picked.last - picked.first + 1,
        core=redundancy.trimming(track, picked),
        knee=knee,
        shares=picked.shares(track),
        frontier=frontier,
    )
