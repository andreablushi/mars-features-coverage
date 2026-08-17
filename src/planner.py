"""Turning what a run could do into the jobs it still has to do."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from models.job import Job


def outstanding[T](
    candidates: Iterable[T],
    output_for: Callable[[T], Path],
    job_for: Callable[[T, Path], Job],
    *,
    force: bool,
) -> tuple[tuple[Job, ...], int]:
    """Build a job for every candidate whose output is not already on disk.

    Args:
        candidates: What the run could do, in the order to do it.
        output_for: The file whose presence marks a candidate as finished.
        job_for: Builds the job for a candidate and its output path.
        force: When True, include candidates that are already finished.

    Returns:
        The jobs to run, and how many candidates were skipped as finished.
    """
    jobs: list[Job] = []
    skipped = 0
    for candidate in candidates:
        output = output_for(candidate)
        if output.exists() and not force:
            skipped += 1
            continue
        jobs.append(job_for(candidate, output))
    return tuple(jobs), skipped
