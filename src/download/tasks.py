"""Downloading one feature and instrument set's metadata."""

from __future__ import annotations

from download.api import products
from download.api.client import ODEClient
from models.job import DownloadJob, DownloadOutcome
from storage.disk import write_jsonl


def run_job(job: DownloadJob, client: ODEClient, loc: str) -> DownloadOutcome:
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
        return DownloadOutcome(job=job)
    except Exception as exc:
        return DownloadOutcome(job=job, error=exc)
