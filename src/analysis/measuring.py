"""Computing one instrument set's coverage, start to finish."""

from __future__ import annotations

from analysis.coverage import events as coverage
from analysis.geometry import projection
from models.job import Job, Outcome
from storage import artifacts


def run_job(job: Job) -> Outcome:
    """Compute and write coverage for one feature and instrument set.

    Args:
        job: The instrument set to compute.

    Returns:
        The outcome, carrying the error when the job failed.
    """
    try:
        prepared = projection.load_projected(job)
        if prepared is None:
            return Outcome(job=job)
        loaded, region = prepared
        if not loaded.observations:
            return Outcome(job=job, discarded=loaded.discarded)
        rows, summary = coverage.measure_set(loaded, region)
        artifacts.write_coverage(job, rows, summary)
        return Outcome(job=job, events=len(rows), discarded=loaded.discarded)
    except Exception as exc:
        return Outcome(job=job, error=exc)
