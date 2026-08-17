"""Where every file the pipeline reads and writes belongs."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import configs
from models.feature import Feature
from models.instrument import InstrumentSet
from models.job import CoverageOutcome
from storage.files import slugify


def metadata_file(root: Path, feature: Feature, instrument_set: InstrumentSet) -> Path:
    """Return the JSONL path for one feature and instrument set.

    Args:
        root: The metadata root directory.
        feature: The feature being stored.
        instrument_set: The instrument set being stored.

    Returns:
        The path to the JSONL output file.
    """
    directory = root / slugify(feature.feature_class) / slugify(feature.name)
    return directory / f"{instrument_set.slug}.jsonl"


def feature_artifacts_dir(root: Path, feature_class: str, name: str) -> Path:
    """Return where one feature's artifacts live, from its catalogue names.

    Reading starts from a name rather than from a metadata path, so this is the
    one place that turns a name back into the slugs the tree is keyed by.

    Args:
        root: The artifacts subtree the path is built under.
        feature_class: The feature class, such as Crater.
        name: The feature name as ODE spells it.

    Returns:
        The feature's directory under that root, which need not exist.
    """
    return root / slugify(feature_class) / slugify(name)


def _mirrored(root: Path, feature_dir: Path) -> Path:
    """Return the directory mirroring one feature's metadata under a root.

    Args:
        root: The artifacts subtree the path is built under.
        feature_dir: The feature's metadata directory.

    Returns:
        The matching path under the given root.
    """
    return root / feature_dir.parent.name / feature_dir.name


def events_path(root: Path, source: Path) -> Path:
    """Return the per-observation events file for one instrument set.

    Args:
        root: The coverage artifacts root directory.
        source: The instrument set's metadata JSONL file.

    Returns:
        The path to the events parquet file.
    """
    return _mirrored(root, source.parent) / f"{source.stem}{configs.EVENTS_SUFFIX}"


def set_summary_path(root: Path, source: Path) -> Path:
    """Return the summary file for one instrument set.

    It is written after the events, so its presence is what marks a set as
    fully computed when a later run decides what to skip.

    Args:
        root: The coverage artifacts root directory.
        source: The instrument set's metadata JSONL file.

    Returns:
        The path to the summary parquet file.
    """
    return _mirrored(root, source.parent) / f"{source.stem}{configs.SET_SUMMARY_SUFFIX}"


def geometry_path(root: Path, source: Path) -> Path:
    """Return the cached projected footprints for one instrument set.

    Args:
        root: The geometry cache root directory.
        source: The instrument set's metadata JSONL file.

    Returns:
        The path to the geometry cache parquet file.
    """
    return _mirrored(root, source.parent) / f"{source.stem}.parquet"


def catalog_summary_path(root: Path = configs.ARTIFACTS_ROOT) -> Path:
    """Return the file holding every feature's summary rows together.

    Args:
        root: The artifacts root directory.

    Returns:
        The path to the catalogue-wide summary parquet file.
    """
    return root / configs.SUMMARY_NAME


def has_metadata(
    feature_dir: Path, instrument_set: InstrumentSet, root: Path = configs.METADATA_ROOT
) -> bool:
    """Report whether one feature holds downloaded records for an instrument set.

    A set with records on disk but no artifact beside them was never computed,
    which is a different thing from a set that observed nothing, and the two
    are indistinguishable from the artifacts alone. The name is matched by
    prefix, so a set narrowed to one observing mode answers for its type.

    Args:
        feature_dir: The feature's artifacts directory, named by the same slugs
            the metadata tree uses.
        instrument_set: The instrument set to look for.
        root: The metadata root directory.

    Returns:
        True when a non-empty metadata file for that set exists.
    """
    directory = root / feature_dir.parent.name / feature_dir.name
    return any(
        path.stat().st_size > 0
        for path in directory.glob(f"{instrument_set.slug}*.jsonl")
    )


def discard_metadata(outcomes: Sequence[CoverageOutcome]) -> int:
    """Delete the metadata of every set whose coverage is now on disk.

    A set is only discarded once its summary exists, so a run that stopped part
    way never leaves an artifact without the metadata that produced it.

    Args:
        outcomes: Every finished coverage job.

    Returns:
        How many metadata files were removed.
    """
    removed = 0
    for outcome in outcomes:
        if not outcome.failed and outcome.job.summary_path.exists():
            outcome.job.source.unlink(missing_ok=True)
            removed += 1
    return removed


def find_sets(root: Path = configs.METADATA_ROOT) -> list[Path]:
    """Find every stored instrument set holding observations.

    The download stage writes a file for every query it makes, empty ones
    included, so a resumed download can tell what it already asked for. An
    empty file means the instrument never saw the feature.

    Args:
        root: The metadata root directory.

    Returns:
        The non-empty JSONL files, sorted, one per feature and instrument set.
    """
    return sorted(path for path in root.glob("*/*/*.jsonl") if path.stat().st_size > 0)
