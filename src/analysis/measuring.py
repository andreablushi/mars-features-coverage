"""Computing one instrument set's coverage, start to finish."""

from __future__ import annotations

from analysis.coverage import events as coverage
from analysis.geometry import projection
from analysis.geometry.region import FeatureRegion
from models.feature import Feature
from models.job import Job, Outcome
from models.observation import LoadedSet, ProjectedObservation
from storage import caching, parquet, records
from storage.schemas import EVENTS, SUMMARY


def run_job(job: Job) -> Outcome:
    """Compute and write coverage for one feature and instrument set.

    Args:
        job: The instrument set to compute.

    Returns:
        The outcome, carrying the error when the job failed.
    """
    try:
        prepared = _projected_footprints(job)
        if prepared is None:
            return Outcome(job=job)
        loaded, region = prepared
        if not loaded.observations:
            return Outcome(job=job, discarded=loaded.discarded)
        rows, summary = coverage.measure_set(loaded, region)
        parquet.write(rows, EVENTS, job.events_path)
        parquet.write([summary], SUMMARY, job.summary_path)
        return Outcome(job=job, events=len(rows), discarded=loaded.discarded)
    except Exception as exc:
        return Outcome(job=job, error=exc)


def _projected_footprints(
    job: Job,
) -> tuple[LoadedSet[ProjectedObservation], FeatureRegion] | None:
    """Load the set's projected footprints, from the cache when it is valid.

    Args:
        job: The instrument set being computed.

    Returns:
        The projected set and the region it was measured against, or None when
        the set holds no records.
    """
    cached = caching.load(job.geometry_path, job.source)
    if cached is not None:
        return cached, _region(cached.feature)
    loaded = records.load_set(job.source)
    if loaded is None:
        return None
    region = _region(loaded.feature)
    projected, missed = projection.project(region, loaded.observations)
    if projected:
        caching.save(job.geometry_path, loaded.feature, loaded.set_key, projected)
    return (
        LoadedSet(
            feature=loaded.feature,
            set_key=loaded.set_key,
            observations=projected,
            discarded=loaded.discarded + missed,
        ),
        region,
    )


def _region(feature: Feature) -> FeatureRegion:
    """Project one feature's bounding box into equal-area metres.

    Args:
        feature: The feature to project.

    Returns:
        The projected region.
    """
    return FeatureRegion(
        feature.min_lat, feature.max_lat, feature.west_lon, feature.east_lon
    )
