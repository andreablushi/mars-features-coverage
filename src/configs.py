"""Where the project lives on disk, and what its files are called."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = REPO_ROOT / "config.yaml"

DATA_ROOT = REPO_ROOT / "data"
METADATA_ROOT = DATA_ROOT / "metadata"
CATALOG_ROOT = DATA_ROOT / "_catalog"
ARTIFACTS_ROOT = DATA_ROOT / "artifacts"
COVERAGE_ROOT = ARTIFACTS_ROOT / "coverage"
GEOMETRY_ROOT = ARTIFACTS_ROOT / "geometry"

FEATURES_CACHE_NAME = "features.jsonl"
INSTRUMENT_SETS_CACHE_NAME = "instrument_sets.jsonl"
SUMMARY_NAME = "summary.parquet"
EVENTS_SUFFIX = ".events.parquet"
SET_SUMMARY_SUFFIX = ".summary.parquet"
