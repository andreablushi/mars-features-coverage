"""Where every file the pipeline reads and writes belongs."""

from __future__ import annotations

from pathlib import Path

import configs
from models.feature import Feature
from models.instrument import InstrumentSet
from utils import slugify


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

    Args:
        root: The coverage artifacts root directory.
        source: The instrument set's metadata JSONL file.

    Returns:
        The path to the summary parquet file.
    """
    return _mirrored(root, source.parent) / f"{source.stem}{configs.SET_SUMMARY_SUFFIX}"


def catalog_summary_path(root: Path = configs.ARTIFACTS_ROOT) -> Path:
    """Return the file holding every feature's summary rows together.

    Args:
        root: The artifacts root directory.

    Returns:
        The path to the catalogue-wide summary parquet file.
    """
    return root / configs.SUMMARY_NAME


def features_path(cache_dir: Path = configs.CATALOG_ROOT) -> Path:
    """Return where the cached feature catalogue lives.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        The path to the features JSONL file, which need not exist.
    """
    return cache_dir / configs.FEATURES_CACHE_NAME


def instrument_sets_path(cache_dir: Path = configs.CATALOG_ROOT) -> Path:
    """Return where the cached instrument set catalogue lives.

    Args:
        cache_dir: Directory holding the cached catalogue files.

    Returns:
        The path to the instrument sets JSONL file, which need not exist.
    """
    return cache_dir / configs.INSTRUMENT_SETS_CACHE_NAME
