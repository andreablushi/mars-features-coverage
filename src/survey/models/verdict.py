"""Whether one feature belongs in the dataset, and everything behind it."""

from __future__ import annotations

from dataclasses import dataclass

from survey.models.survey import Survey

Row = tuple[str, str, str, bool | None]


@dataclass(frozen=True, slots=True)
class Verdict:
    """What the dataset asked of one feature, and what the feature answered.

    Attributes:
        survey: The window the search picked, or None when it found none.
        checks: Everything asked of it, in the order they read. Each row is
            what was asked, what it holds, the least it could hold and still
            pass, and whether it passed, which is None on a row that is there
            to be read rather than to be met.
    """

    survey: Survey | None
    checks: list[Row]
