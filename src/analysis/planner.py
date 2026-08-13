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
    *,
    force: bool = False,
) -> CoveragePlan:
    """Build the jobs still needed for a run.

    A feature whose summary already exists is left out unless force is set, so
    an interrupted run resumes where it stopped. The summary is written after
    the events and both are written atomically, so its presence means the
    feature finished rather than merely started.

    Args:
        sources: The feature metadata directories discovered on disk.
        coverage_root: The coverage artifacts root directory.
        force: When True, recompute features that are already done.

    Returns:
        The plan describing the discovery and the jobs to run.
    """
    jobs: list[CoverageJob] = []
    skipped_existing = 0
    for source in sources:
        summary = layout.summary_path(coverage_root, source)
        if summary.exists() and not force:
            skipped_existing += 1
            continue
        jobs.append(
            CoverageJob(
                source=source,
                events_path=layout.events_path(coverage_root, source),
                summary_path=summary,
            )
        )
    return CoveragePlan(
        jobs=tuple(jobs),
        feature_count=len(sources),
        skipped_existing=skipped_existing,
    )
