"""Build the list of download jobs from a feature and instrument selection."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from download.models import DownloadPlan, Feature, InstrumentSet, Job
from download.storage.layout import product_file


def select_features(
    features: Sequence[Feature],
    *,
    names: Sequence[str] | None = None,
    classes: Sequence[str] | None = None,
) -> tuple[list[Feature], list[Feature]]:
    """Filter the catalog to the requested features and split off degenerate ones.

    Names take precedence over classes. Matching is case insensitive, and the
    catalog's own spelling is preserved for querying. When neither names nor
    classes are given, every feature is selected.

    Args:
        features: The full feature catalog.
        names: Optional feature names to keep.
        classes: Optional feature classes to keep.

    Returns:
        A pair (usable, degenerate) where degenerate features have a zero or
        negative latitude span and cannot be queried.
    """
    wanted_names = {name.strip().lower() for name in names} if names else None
    wanted_classes = {cls.strip().lower() for cls in classes} if classes else None
    selected: list[Feature] = []
    for feature in features:
        if wanted_names is not None:
            if feature.name.lower() not in wanted_names:
                continue
        elif wanted_classes is not None:
            if feature.feature_class.lower() not in wanted_classes:
                continue
        selected.append(feature)
    usable = [feature for feature in selected if not feature.is_degenerate]
    degenerate = [feature for feature in selected if feature.is_degenerate]
    return usable, degenerate


def build_plan(
    features: Sequence[Feature],
    instrument_sets: Sequence[InstrumentSet],
    out_root: Path,
    *,
    names: Sequence[str] | None = None,
    classes: Sequence[str] | None = None,
    force: bool = False,
) -> DownloadPlan:
    """Select features and build the jobs still needed for a run.

    A job whose output file already exists is left out unless force is set, so
    interrupted runs resume where they stopped.

    Args:
        features: The full feature catalog.
        instrument_sets: The instrument sets to download for each feature.
        out_root: The metadata root directory.
        names: Optional feature names to keep.
        classes: Optional feature classes to keep.
        force: When True, include jobs whose output file already exists.

    Returns:
        The plan describing the selection and the jobs to run.
    """
    usable, degenerate = select_features(features, names=names, classes=classes)
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
