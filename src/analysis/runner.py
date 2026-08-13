"""Run coverage computation across every downloaded feature.

Each feature is an independent CPU-bound job, so the work runs on a process
pool rather than the thread pool the download stage uses. A worker writes its
own parquet files and hands back only its summary rows, keeping the millions of
event rows a full catalogue produces out of the parent process entirely.
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from analysis import configs, coverage, layout, records, writer
from analysis.models import FeatureOutcome, ProgressEvent, RunSummary


def discover(root: Path = configs.METADATA_ROOT) -> list[Path]:
    """Find every feature directory holding downloaded metadata.

    Args:
        root: The metadata root directory.

    Returns:
        The feature directories, sorted, that hold at least one JSONL file.
    """
    return sorted(
        path for path in root.glob("*/*") if path.is_dir() and any(path.glob("*.jsonl"))
    )


def compute_feature(
    directory: Path, root: Path
) -> tuple[FeatureOutcome, list[dict[str, Any]]]:
    """Compute and write coverage for one feature directory.

    Args:
        directory: The feature directory holding one JSONL file per set.
        root: The coverage artifacts root directory.

    Returns:
        The outcome and the feature's summary rows.
    """
    box, observations = records.load_feature(directory)
    if box is None:
        return FeatureOutcome(label=directory.name), []
    events, summaries = coverage.compute(box, observations)
    if events:
        writer.write(
            events,
            writer.EVENTS_SCHEMA,
            layout.events_path(root, box.feature_class, box.name),
        )
    writer.write(
        summaries,
        writer.SUMMARY_SCHEMA,
        layout.summary_path(root, box.feature_class, box.name),
    )
    outcome = FeatureOutcome(
        label=f"{box.feature_class}/{box.name}",
        events=len(events),
        degenerate=bool(summaries) and summaries[0]["degenerate"],
    )
    return outcome, summaries


class CoverageRunner:
    """Computes coverage for many features on a bounded process pool.

    The runner never writes to the console. It yields a ProgressEvent as each
    feature finishes and exposes a RunSummary once the run is complete, leaving
    all rendering to the caller.
    """

    def __init__(
        self,
        *,
        workers: int = configs.DEFAULT_WORKERS,
        artifacts_root: Path = configs.ARTIFACTS_ROOT,
    ) -> None:
        """Create a runner.

        Args:
            workers: Requested worker count, at least one.
            artifacts_root: Where computed artifacts are written.

        Returns:
            None.
        """
        self._workers = max(1, workers)
        self._artifacts_root = artifacts_root
        self._coverage_root = artifacts_root / configs.COVERAGE_DIR
        self._summary = RunSummary(
            features=0, failed=0, degenerate=0, events=0, elapsed=0.0
        )

    @property
    def workers(self) -> int:
        """Return the effective worker count.

        Returns:
            The number of concurrent workers used.
        """
        return self._workers

    @property
    def summary(self) -> RunSummary:
        """Return the summary of the last run.

        Returns:
            The summary, zeroed until a run has finished.
        """
        return self._summary

    def run(self, directories: Sequence[Path]) -> Iterator[ProgressEvent]:
        """Compute every feature, yielding progress as each finishes.

        Args:
            directories: The feature directories to compute.

        Yields:
            One ProgressEvent per finished feature, in completion order.
        """
        started = time.monotonic()
        rows: list[dict[str, Any]] = []
        features = failed = degenerate = events = 0
        pool = ProcessPoolExecutor(max_workers=self._workers)
        try:
            futures = {
                pool.submit(compute_feature, directory, self._coverage_root): directory
                for directory in directories
            }
            for completed, future in enumerate(as_completed(futures), start=1):
                try:
                    outcome, summaries = future.result()
                    rows.extend(summaries)
                    features += 1
                    events += outcome.events
                    degenerate += outcome.degenerate
                except Exception as exc:
                    failed += 1
                    outcome = FeatureOutcome(label=futures[future].name, error=exc)
                yield ProgressEvent(completed=completed, outcome=outcome)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
            if rows:
                writer.write(
                    rows,
                    writer.SUMMARY_SCHEMA,
                    layout.catalog_summary_path(self._artifacts_root),
                )
            self._summary = RunSummary(
                features=features,
                failed=failed,
                degenerate=degenerate,
                events=events,
                elapsed=time.monotonic() - started,
            )
