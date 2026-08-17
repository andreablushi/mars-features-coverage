"""Build the list of coverage jobs from what is on disk."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import configs
from models.job import CoverageJob, CoveragePlan
from storage import paths


def build_plan(
    sources: Sequence[Path],
    coverage_root: Path = configs.COVERAGE_ROOT,
    geometry_root: Path = configs.GEOMETRY_ROOT,
    *,
    force: bool = False,
) -> CoveragePlan:
    """Build the jobs still needed for a run.

    An instrument set whose summary already exists is left out unless force is
    set, so an interrupted run resumes where it stopped. The jobs that remain
    are ordered largest first, so the pool starts the long ones early: the sets
    differ in size by orders of magnitude, and in discovery order the pool can
    pick the largest up last and grind on it with every worker idle.

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
    for source in sorted(sources, key=lambda path: -path.stat().st_size):
        summary_path = paths.set_summary_path(coverage_root, source)
        if summary_path.exists() and not force:
            skipped_existing += 1
            continue
        jobs.append(
            CoverageJob(
                source=source,
                events_path=paths.events_path(coverage_root, source),
                summary_path=summary_path,
                geometry_path=paths.geometry_path(geometry_root, source),
            )
        )
    return CoveragePlan(
        jobs=tuple(jobs),
        feature_count=len({source.parent for source in sources}),
        set_count=len(sources),
        skipped_existing=skipped_existing,
    )


def unfinished(
    sources: Sequence[Path], coverage_root: Path = configs.COVERAGE_ROOT
) -> tuple[Path, ...]:
    """Return the instrument sets that still have no coverage artifact.

    An interrupted run leaves nothing behind saying so, so the gaps are read
    back off disk. A set whose records are all unusable is in here too.

    Args:
        sources: The instrument set metadata files discovered on disk.
        coverage_root: The coverage artifacts root directory.

    Returns:
        The metadata files with no summary beside them, in discovery order.
    """
    return tuple(
        source
        for source in sources
        if not paths.set_summary_path(coverage_root, source).exists()
    )
