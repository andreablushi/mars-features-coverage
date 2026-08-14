"""Computing one instrument set's coverage, start to finish."""

from __future__ import annotations

from analysis import configs
from analysis.coverage import events as coverage
from analysis.geometry import projection
from analysis.geometry.region import FeatureRegion
from models.feature import Feature
from models.job import CoverageJob, CoverageOutcome
from models.observation import ProjectedObservation
from storage import geometry, parquet, records
from storage.schemas import EVENTS, SUMMARY


def run_job(
    job: CoverageJob, cumulative_union: bool = configs.DEFAULT_CUMULATIVE_UNION
) -> CoverageOutcome:
    """Compute and write coverage for one feature and instrument set.

    The events are written before the summary, so a summary on disk means the
    whole set finished and a later run can skip it.

    Args:
        job: The instrument set to compute.
        cumulative_union: Whether to accumulate the running union.

    Returns:
        The outcome, carrying the error when the job failed.
    """
    try:
        prepared = _projected_footprints(job)
        if prepared is None:
            return CoverageOutcome(job=job)
        feature, region, projected, discarded = prepared
        if not projected:
            return CoverageOutcome(job=job, discarded=discarded)
        rows, summary = coverage.measure_set(
            feature, region, projected, cumulative_union=cumulative_union
        )
        parquet.write(rows, EVENTS, job.events_path)
        parquet.write([summary], SUMMARY, job.summary_path)
        return CoverageOutcome(job=job, events=len(rows), discarded=discarded)
    except Exception as exc:
        return CoverageOutcome(job=job, error=exc)


def _projected_footprints(
    job: CoverageJob,
) -> tuple[Feature, FeatureRegion, list[ProjectedObservation], int] | None:
    """Load the set's projected footprints, from the cache when it is valid.

    A cache hit reports no discards. Only a set that yielded something is ever
    cached, so the sets whose discards matter are always read afresh.

    Args:
        job: The instrument set being computed.

    Returns:
        The feature, its projected region, the projected observations, and how
        many records were discarded, or None when the set holds no records.
    """
    cached = geometry.load(job.geometry_path, job.source)
    if cached is not None:
        feature, projected = cached
        return feature, _region(feature), projected, 0
    loaded = records.load_set(job.source)
    if loaded is None:
        return None
    feature, observations, discarded = loaded
    region = _region(feature)
    projected, missed = projection.project(region, observations)
    if projected:
        geometry.save(job.geometry_path, feature, projected)
    return feature, region, projected, discarded + missed


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
