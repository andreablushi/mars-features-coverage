"""Build the list of coverage jobs from what is on disk."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from analysis import configs
from analysis.loader import layout
from analysis.models.job import CoverageJob, CoveragePlan


def build_plan(
    sources: Sequence[Path],
    coverage_root: Path = configs.COVERAGE_ROOT,
    geometry_root: Path = configs.GEOMETRY_ROOT,
    *,
    force: bool = False,
) -> CoveragePlan:
    """Build the jobs still needed for a run.

    An instrument set whose summary already exists is left out unless force is
    set, so an interrupted run resumes where it stopped. That summary is
    written after the events and the union, and every output is written
    atomically, so its presence means the set finished rather than started.

    Args:
        sources: The instrument set metadata files discovered on disk.
        coverage_root: The coverage artifacts root directory.
        geometry_root: The projected geometry cache root directory.
        force: When True, recompute sets that are already done.

    Returns:
        The plan describing the discovery and the jobs to run.
    """
    jobs: list[CoverageJob] = []
    skipped_existing = 0
    for source in sources:
        if layout.set_summary_path(coverage_root, source).exists() and not force:
            skipped_existing += 1
            continue
        jobs.append(
            CoverageJob(
                source=source,
                events_path=layout.events_path(coverage_root, source),
                geometry_path=layout.geometry_path(geometry_root, source),
            )
        )
    return CoveragePlan(
        jobs=tuple(jobs),
        feature_count=len({source.parent for source in sources}),
        set_count=len(sources),
        skipped_existing=skipped_existing,
    )
