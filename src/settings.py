"""Reading config.yaml and ranking it against the command line flags."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

import configs
from analysis import configs as analysis_configs
from download import configs as download_configs
from models.instrument import InstrumentSet
from models.settings import CoverageSettings, DownloadSettings, PipelineSettings


def _section(name: str, path: Path) -> dict[str, Any]:
    """Read one section of the config file.

    Args:
        name: The section to read, such as "download".
        path: The config file, which need not exist.

    Returns:
        The section's keys, empty when the file or the section is absent.

    Raises:
        ValueError: When the file or the section is not a mapping.
    """
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} should hold a mapping, found {type(loaded).__name__}")
    found = loaded.get(name)
    if found is None:
        return {}
    if not isinstance(found, dict):
        raise ValueError(f"{path}: `{name}` should hold a mapping of settings")
    return found


def _first(*candidates: Any) -> Any:
    """Return the first candidate that was actually given.

    Args:
        candidates: The sources in priority order, the flag first and the
            built-in default last.

    Returns:
        The first one that is not None.
    """
    return next(value for value in candidates if value is not None)


def _positive_int(value: Any, name: str) -> int:
    """Check that a setting is a count a run can be given.

    Args:
        value: The settled value.
        name: What to call it if it has to be rejected.

    Returns:
        The value unchanged.

    Raises:
        ValueError: When it is not a positive whole number.
    """
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} should be a positive whole number, found {value!r}")
    return value


def _boolean(value: Any, name: str) -> bool:
    """Check that a setting is a plain yes or no.

    Args:
        value: The settled value.
        name: What to call it if it has to be rejected.

    Returns:
        The value unchanged.

    Raises:
        ValueError: When it is not true or false.
    """
    if not isinstance(value, bool):
        raise ValueError(f"{name} should be true or false, found {value!r}")
    return value


def _instrument_set(key: Any) -> InstrumentSet:
    """Build one instrument set from an IHID/IID/PT triple.

    A product type holding several observing modes at once can be narrowed to
    one of them by following the triple with a colon and an ODE product id
    pattern, as in MRO/CRISM/TRDR:[mh]sp*.

    Args:
        key: The triple, as a string or as the three parts.

    Returns:
        The instrument set.

    Raises:
        ValueError: When the triple does not carry exactly three parts.
    """
    raw = key if isinstance(key, str) else "/".join(str(part) for part in key)
    return InstrumentSet.from_key(raw)


def _positive_float(value: Any, name: str) -> float:
    """Check that a setting is a distance a box can be grown by.

    Args:
        value: The settled value.
        name: What to call it if it has to be rejected.

    Returns:
        The value as a float.

    Raises:
        ValueError: When it is not a positive number.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} should be a positive number, found {value!r}")
    return float(value)


def download(
    args: argparse.Namespace, path: Path = configs.CONFIG_PATH
) -> DownloadSettings:
    """Settle what the download stage should do.

    There is no built-in list of instrument sets, so the config file or the
    command line has to name them; a run that asks for nothing is a mistake
    rather than a run of some default selection.

    Args:
        args: The parsed command line arguments.
        path: The config file, which need not exist.

    Returns:
        The settled choices for the stage.

    Raises:
        ValueError: When the config file holds a key it cannot honour, or no
            instrument set was named anywhere.
    """
    config = _section(download_configs.CONFIG_SECTION, path)
    keys = _first(args.instrument_set, config.get("instruments"), [])
    if not keys:
        raise ValueError(
            "no instrument sets requested: name them under `download.instruments` "
            f"in {path.name} or pass --instrument-set"
        )
    loc = str(_first(args.loc, config.get("loc"), download_configs.DEFAULT_LOC))
    if loc not in download_configs.LOC_MODES:
        raise ValueError(
            f"loc should be one of {download_configs.LOC_MODES}, found {loc!r}"
        )
    return DownloadSettings(
        instrument_sets=tuple(_instrument_set(key) for key in keys),
        loc=loc,
        point_radius_deg=_positive_float(
            _first(
                config.get("point_radius_deg"),
                download_configs.DEFAULT_POINT_RADIUS_DEG,
            ),
            "point_radius_deg",
        ),
        force=_boolean(_first(args.force, config.get("force"), False), "force"),
        workers=_positive_int(
            _first(
                args.download_workers,
                config.get("workers"),
                download_configs.DEFAULT_WORKERS,
            ),
            "workers",
        ),
    )


def coverage(
    args: argparse.Namespace, path: Path = configs.CONFIG_PATH
) -> CoverageSettings:
    """Settle what the coverage stage should do.

    Args:
        args: The parsed command line arguments.
        path: The config file, which need not exist.

    Returns:
        The settled choices for the stage.

    Raises:
        ValueError: When the config file holds a key it cannot honour.
    """
    config = _section(analysis_configs.CONFIG_SECTION, path)
    return CoverageSettings(
        cumulative_union=_boolean(
            _first(
                args.cumulative_union,
                config.get("cumulative_union"),
                analysis_configs.DEFAULT_CUMULATIVE_UNION,
            ),
            "cumulative_union",
        ),
        force=_boolean(_first(args.force, config.get("force"), False), "force"),
        workers=_positive_int(
            _first(
                args.coverage_workers,
                config.get("workers"),
                analysis_configs.DEFAULT_WORKERS,
            ),
            "workers",
        ),
    )


def pipeline(
    args: argparse.Namespace, path: Path = configs.CONFIG_PATH
) -> PipelineSettings:
    """Settle what the run as a whole should do.

    Args:
        args: The parsed command line arguments.
        path: The config file, which need not exist.

    Returns:
        The settled choices for the run.

    Raises:
        ValueError: When the config file holds a key it cannot honour.
    """
    config = _section(configs.CONFIG_SECTION, path)
    return PipelineSettings(
        keep_metadata=_boolean(
            _first(
                args.keep_metadata,
                config.get("keep_metadata"),
                configs.DEFAULT_KEEP_METADATA,
            ),
            "keep_metadata",
        ),
        coverage_only=_boolean(
            _first(
                args.coverage_only,
                config.get("coverage_only"),
                configs.DEFAULT_COVERAGE_ONLY,
            ),
            "coverage_only",
        ),
    )
