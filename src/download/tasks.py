"""Downloading one feature and instrument set's metadata."""

from __future__ import annotations

from download.api import products
from download.api.client import ODEClient
from models.job import Job, Outcome
from storage.disk import write_jsonl


def run_job(job: Job, client: ODEClient, loc: str) -> Outcome:
    """Download one instrument set's metadata and write it out.

    An output file is always written, empty included, so a later run can skip
    it. Nothing is written when the job fails.

    Args:
        job: The feature and instrument set to download.
        client: The shared ODE client.
        loc: Which products a feature box returns.

    Returns:
        The outcome, carrying the error when the job failed.
    """
    try:
        records = products.fetch_products(client, job.feature, job.instrument_set, loc)
        write_jsonl(job.output_path, records)
        return Outcome(job=job)
    except Exception as exc:
        return Outcome(job=job, error=exc)
