"""Reading config.yaml, which is the only place a run is configured from."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

import configs
from download import configs as download_configs
from models.instrument import InstrumentSet
from models.settings import DownloadSettings, PipelineSettings


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
        candidates: The sources in priority order, the file first and the
            built-in default last.

    Returns:
        The first one that is not None.
    """
    return next(value for value in candidates if value is not None)


def _names(value: Any) -> tuple[str, ...] | None:
    """Read the optional list of feature names a run is restricted to.

    Args:
        value: The configured value, absent for the whole catalogue.

    Returns:
        The names, or None when every feature is wanted.

    Raises:
        ValueError: When the value is not a list of names.
    """
    if value is None:
        return None
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ValueError(f"features should be a list of names, found {value!r}")
    return tuple(str(name).strip() for name in value if str(name).strip())


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


def download(path: Path = configs.CONFIG_PATH) -> DownloadSettings:
    """Settle what the download stage should do.

    There is no built-in list of instrument sets, so the config file has to
    name them; a run that asks for nothing is a mistake rather than a run of
    some default selection.

    Args:
        path: The config file, which need not exist.

    Returns:
        The settled choices for the stage.

    Raises:
        ValueError: When the config file holds a key it cannot honour, or no
            instrument set was named.
    """
    config = _section(download_configs.CONFIG_SECTION, path)
    keys = config.get("instruments") or []
    if not keys:
        raise ValueError(
            "no instrument sets requested: name them under `download.instruments` "
            f"in {path.name}"
        )
    loc = str(_first(config.get("loc"), download_configs.DEFAULT_LOC))
    if loc not in download_configs.LOC_MODES:
        raise ValueError(
            f"loc should be one of {download_configs.LOC_MODES}, found {loc!r}"
        )
    return DownloadSettings(
        instrument_sets=tuple(_instrument_set(key) for key in keys),
        feature_names=_names(config.get("features")),
        loc=loc,
    )


def pipeline(path: Path = configs.CONFIG_PATH) -> PipelineSettings:
    """Settle what the run as a whole should do.

    There is no built-in worker count, so the config file has to give one: how
    many jobs a machine should carry at once is a property of that machine, and
    a number picked here would be picked for a machine nobody has seen.

    Args:
        path: The config file, which need not exist.

    Returns:
        The settled choices for the run.

    Raises:
        ValueError: When the config file holds a key it cannot honour, or no
            worker count was given.
    """
    config = _section(configs.CONFIG_SECTION, path)
    workers = config.get("workers")
    if workers is None:
        raise ValueError(
            f"no worker count requested: set `pipeline.workers` in {path.name}"
        )
    return PipelineSettings(
        keep_metadata=_boolean(
            _first(config.get("keep_metadata"), configs.DEFAULT_KEEP_METADATA),
            "keep_metadata",
        ),
        force=_boolean(_first(config.get("force"), False), "force"),
        refresh_catalog=_boolean(
            _first(config.get("refresh_catalog"), configs.DEFAULT_REFRESH_CATALOG),
            "refresh_catalog",
        ),
        workers=_positive_int(workers, "workers"),
    )
