"""One instrument set's finished coverage, as it is read back off disk."""

from __future__ import annotations

from dataclasses import dataclass

from analysis.models.results import Event, Summary


@dataclass(frozen=True, slots=True)
class SetCoverage:
    """What one instrument set covered of one feature.

    Attributes:
        events: The set's observations in chronological order.
        summary: The single row describing the set as a whole.
    """

    events: list[Event]
    summary: Summary

    @property
    def label(self) -> str:
        """Return the short readable name for the instrument set.

        Returns:
            The instrument and product type, such as "CTX EDR".
        """
        return f"{self.summary.iid} {self.summary.pt}"
