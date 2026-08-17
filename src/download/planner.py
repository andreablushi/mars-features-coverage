"""Build the list of download jobs from a feature selection."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import configs
from download.selection.features import select_features
from models.feature import Feature
from models.instrument import InstrumentSet
from models.job import Job, Plan
from storage import paths


def build_plan(
    features: Sequence[Feature],
    instrument_sets: Sequence[InstrumentSet],
    out_root: Path = configs.METADATA_ROOT,
    *,
    names: Sequence[str] | None = None,
    force: bool = False,
) -> Plan:
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
    usable, sizeless = select_features(features, names=names)

    jobs: list[Job] = []
    skipped_existing = 0
    for feature in usable:
        for instrument_set in instrument_sets:
            path = paths.metadata_file(out_root, feature, instrument_set)
            if path.exists() and not force:
                skipped_existing += 1
                continue
            jobs.append(
                Job(
                    feature=feature,
                    instrument_set=instrument_set,
                    output_path=path,
                )
            )

    return Plan(
        jobs=tuple(jobs),
        feature_count=len(usable),
        set_count=len(instrument_sets),
        skipped_existing=skipped_existing,
        sizeless_features=tuple(feature.name for feature in sizeless),
    )
