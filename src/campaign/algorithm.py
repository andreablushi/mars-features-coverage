"""The best time window with most observations across multiple instruments."""

from __future__ import annotations

from collections.abc import Sequence

from campaign import configs, curve, measuring, timeline
from campaign.reach import Reach
from campaign.results import Campaign, Span
from campaign.timeline import Filter
from models.results import SetCoverage


def find_best_time_window(
    coverage: Sequence[SetCoverage], visible: Filter | None = None
) -> Campaign | None:
    """Find the shortest window holding most of what every instrument saw.

    Two aims pull against each other: a window should be short, and it should
    hold most of the ground every instrument covered. Neither can be maximised
    without giving up the other, so nothing here is scored against a made up
    exchange rate between days and ground. The demand for ground is raised a
    rung at a time instead, the shortest window meeting each rung is found
    exactly, and the turn in the curve those windows trace is what gets picked.

    It runs in four steps, marked in the body below.

    1. Put every instrument's observations on one time axis, oldest first.
    2. Ask for all the instruments at once, and settle for fewer only when no
       window inside the allowed span holds that many at all.
    3. For each rung of ground, slide a window along the axis and keep the
       shortest one meeting it. Two facts make one pass enough. A window can
       always be pulled in to start and end on an observation without losing
       anything, so only those windows are worth looking at. And every demand
       only becomes easier to meet as a window grows, so once a window
       qualifies, the earliest observation it can start at never moves
       backwards again: the left edge sweeps forward exactly once.
    4. Pick the knee of the curve, the point past which more ground stops
       being worth the days it costs.

    Args:
        coverage: The feature's instrument sets, in any order.
        visible: A filter narrowing each set to the observations to consider,
            or None to search the whole record.

    Returns:
        The chosen window, or None when the feature was never sounded, or when
        no window inside the allowed span holds a sounder track at all.
    """
    # 1. One time axis, and nothing to choose from unless a sounder flew here.
    track = timeline.build(coverage, visible)
    if track is None or not any(track.sounder):
        return None
    times, owners = track.times, track.owners
    sounder, cells = track.sounder, track.cells

    frontier: list[Span] = []
    # 2. Every instrument first, dropping to fewer only when none of them fit.
    for wanted in range(track.sets, 0, -1):
        frontier, seen = [], set()
        for step in range(configs.LEVELS + 1):
            level = (
                step / configs.LEVELS
            )  # the first rung asks for the instruments alone

            # 3. Slide a window along the axis: widen right, then tighten left.
            held = Reach(track.totals, track.grid)
            found: Span | None = None
            sounders, left = 0, 0
            for right in range(track.size):
                held.hold(owners[right], cells[right])  # take the next one in
                sounders += sounder[right]
                while (
                    sounders  # a campaign without a sounder track is no campaign
                    and held.instruments >= wanted
                    and held.mean >= level - configs.ROUNDING
                ):
                    days = times[right] - times[left]
                    if found is None or (days, -held.mean) < (found.days, -found.reach):
                        found = Span(left, right, days, held.mean, held.instruments)
                    held.release(owners[left], cells[left])  # drop the oldest
                    sounders -= sounder[left]
                    left += 1

            if found is None or found.days > configs.MAX_SPAN_DAYS:
                break  # asking for more ground can only ever ask for more days
            found = measuring.widen(track, found)  # a tie in time is ground for free
            if (found.first, found.last) not in seen:
                seen.add((found.first, found.last))
                frontier.append(found)
        if frontier:
            break  # this many instruments do fit, so stop settling for fewer
    if not frontier:
        return None

    # 4. The knee: rescale both axes to nought and one, then take the point
    #    sitting furthest above the diagonal joining the ends of the curve.
    cost = curve.unit([span.days for span in frontier])
    gain = curve.unit([span.reach for span in frontier])
    turn = max(range(len(frontier)), key=lambda index: gain[index] - cost[index])
    picked = frontier[turn] if len(frontier) > 2 else frontier[-1]

    return Campaign(
        start=track.moments[picked.first],
        end=track.moments[picked.last],
        days=picked.days,
        reach=picked.reach,
        instruments=picked.instruments,
        observations=picked.last - picked.first + 1,
        shares=measuring.shares(track, picked),
        frontier=frontier,
    )
