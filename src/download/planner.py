"""Build the list of download jobs from a feature selection."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from download import configs
from download.models import DownloadPlan, Feature, InstrumentSet, Job
from download.selection import select_features
from download.storage.layout import product_file


def build_plan(
    features: Sequence[Feature],
    instrument_sets: Sequence[InstrumentSet],
    out_root: Path = configs.METADATA_ROOT,
    *,
    names: Sequence[str] | None = None,
    force: bool = False,
) -> DownloadPlan:
    """Select features and build the jobs still needed for a run.

    A job whose output file already exists is left out unless force is set, so
    interrupted runs resume where they stopped.

    Args:
        features: The full feature catalog.
        instrument_sets: The instrument sets to download for each feature.
        out_root: The metadata output root directory.
        names: Optional feature names to keep.
        force: When True, include jobs whose output file already exists.

    Returns:
        The plan describing the selection and the jobs to run.
    """
    usable, degenerate = select_features(features, names=names)

    # Assemble the jobs still needed, skipping existing output files unless forced
    jobs: list[Job] = []
    skipped_existing = 0
    for feature in usable:
        for instrument_set in instrument_sets:
            path = product_file(out_root, feature, instrument_set)
            if path.exists() and not force:
                skipped_existing += 1
                continue
            jobs.append(Job(feature, instrument_set, path))

    return DownloadPlan(
        jobs=tuple(jobs),
        feature_count=len(usable),
        instrument_set_count=len(instrument_sets),
        degenerate_features=len(degenerate),
        skipped_existing=skipped_existing,
    )
