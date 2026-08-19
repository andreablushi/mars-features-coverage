"""The stretch of time the figures are drawn over."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from models.results import Event


@dataclass(frozen=True, slots=True)
class Window:
    """The period the time axis is limited to.

    Nothing is recomputed for a window: it moves the viewport over the whole
    record, so a running curve keeps the level it had already reached when it
    enters the window rather than restarting inside it.

    Attributes:
        start: The earliest moment shown, or None to start at the record's own
            beginning.
        end: The latest moment shown, or None to end at the record's own end.
    """

    start: datetime | None = None
    end: datetime | None = None

    @classmethod
    def between(cls, start: date | None, end: date | None) -> Window:
        """Build a window from the two days a picker returns.

        Args:
            start: The first day to show, or None to leave that end open.
            end: The last day to show, whole, or None to leave that end open.

        Returns:
            The window in UTC, which is what the artifacts are timestamped in.
        """
        return cls(
            start=datetime.combine(start, time.min, UTC) if start else None,
            end=datetime.combine(end, time.max, UTC) if end else None,
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
