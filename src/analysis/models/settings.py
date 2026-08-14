"""What one coverage run was asked to do, once every source has been read."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalysisSettings:
    """The settled choices for a run, whatever they were asked for through.

    Attributes:
        cumulative_union: Whether to accumulate the running union of covered
            ground. Turning it off leaves each observation's own area measured
            and the union columns empty, which is the whole of what the union
            costs.
        force: Whether to recompute instead of skipping finished sets.
        workers: How many sets to compute at once.
    """

    cumulative_union: bool
    force: bool
    workers: int
