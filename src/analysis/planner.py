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
    set, so an interrupted run resumes where it stopped. The jobs that remain
    are ordered largest first, so the pool starts the long ones early.

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
    for source in _largest_first(sources):
        if _is_finished(source, coverage_root) and not force:
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
        source for source in sources if not _is_finished(source, coverage_root)
    )


def _is_finished(source: Path, coverage_root: Path) -> bool:
    """Report whether one instrument set has already been computed in full.

    The summary is written after the events and the union, and every output is
    written atomically, so its presence means the set finished rather than
    started.

    Args:
        source: The instrument set metadata file.
        coverage_root: The coverage artifacts root directory.

    Returns:
        True when the set's summary is already on disk.
    """
    return layout.set_summary_path(coverage_root, source).exists()


def _largest_first(sources: Sequence[Path]) -> list[Path]:
    """Order instrument sets so the biggest are handed out first.

    The sets differ in size by orders of magnitude, and in discovery order the
    pool can pick the largest up last and grind on it with every worker idle.

    Args:
        sources: The instrument set metadata files discovered on disk.

    Returns:
        The same files, largest first.
    """
    return sorted(sources, key=lambda source: -source.stat().st_size)
