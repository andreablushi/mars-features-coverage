"""The stretch of time the figures are drawn over."""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from models.results import Event


@dataclass(frozen=True, slots=True)
class Window:
    """The period the time axis is limited to.

    Attributes:
        start: The earliest moment shown, or None to start at the record's own
            beginning.
        end: The latest moment shown, or None to end at the record's own end.
    """

    start: datetime | None = None
    end: datetime | None = None

    @classmethod
    def over_months(cls, start: date | None, end: date | None) -> Window:
        """Build a window from the two months a picker returns.

        Args:
            start: Any day in the first month to show, or None to leave that
                end open.
            end: Any day in the last month to show, or None to leave that end
                open.

        Returns:
            The window in UTC, which is what the artifacts are timestamped in.
        """
        return cls(
            start=datetime.combine(start.replace(day=1), time.min, UTC)
            if start
            else None,
            end=datetime.combine(_month_end(end), time.max, UTC) if end else None,
        )

    def visible(self, events: Sequence[Event]) -> list[Event]:
        """Keep only the observations the window shows.

        Args:
            events: The observations, in chronological order.

        Returns:
            Those falling inside the window, in the same order.
        """
        start = self.start or datetime.min.replace(tzinfo=UTC)
        end = self.end or datetime.max.replace(tzinfo=UTC)
        return [event for event in events if start <= event.t_start <= end]


def month_options(first: datetime, last: datetime) -> list[tuple[str, date]]:
    """List every month a period touches, as a dropdown shows them.

    Args:
        first: The earliest moment the period covers.
        last: The latest moment it covers.

    Returns:
        One label and first day per month, from the month holding first to the
        month holding last, in order.
    """
    cursor, stop = _first_of(first), _first_of(last)
    months = []
    while cursor <= stop:
        months.append((f"{cursor:%Y-%m}", cursor))
        cursor = _first_of_next(cursor)
    return months


def month_edges(first: datetime, last: datetime, step: int) -> list[datetime]:
    """Return bin edges every step months, covering a period whole.

    The last edge always sits past the end of the period, so the final bin is
    closed and the month holding last is counted in it.

    Args:
        first: The earliest moment the bins must cover.
        last: The latest moment they must cover.
        step: How many months one bin spans.

    Returns:
        The edges in UTC, in order, one more than there are bins.
    """
    cursor, stop = _first_of(first), _first_of(last)
    edges = []
    while cursor <= stop:
        edges.append(datetime.combine(cursor, time.min, UTC))
        for _ in range(step):
            cursor = _first_of_next(cursor)
    edges.append(datetime.combine(cursor, time.min, UTC))
    return edges


def _first_of(moment: datetime) -> date:
    """Return the first day of a moment's own month.

    Args:
        moment: The moment to place.

    Returns:
        The first day of the month it falls in.
    """
    return date(moment.year, moment.month, 1)


def _first_of_next(day: date) -> date:
    """Return the first day of the month after a day's own.

    Args:
        day: The day to step on from.

    Returns:
        The first day of the following month.
    """
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


def _month_end(day: date) -> date:
    """Return the last day of a day's own month.

    Args:
        day: Any day in the month.

    Returns:
        Its month's final day.
    """
    return day.replace(day=monthrange(day.year, day.month)[1])
