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

# Stands in for a setting with no built-in default, which the file has to give
_REQUIRED = object()


def _setting(
    path: Path, section: str, key: str, kind: type, default: Any = _REQUIRED
) -> Any:
    """Read one setting from the config file and check the configuration is valid.

    Args:
        path: The config file, which need not exist.
        section: The section holding the setting, such as "download".
        key: The setting's name inside that section.
        kind: What the value has to be: bool for a flag, int for a count above
            zero, str for a spelling, or list for a sequence of them.
        default: What to settle on when the file gives nothing. A setting left
            without one has to be in the file.

    Returns:
        The configured value, or the default when the file gives none. A list
        comes back as a tuple of strings.

    Raises:
        ValueError: When the file is not a mapping of sections, the section is
            not a mapping of settings, a setting with no default is missing, or
            a value is not what its kind asks for.
    """
    found = None
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(
                f"{path} should hold a mapping, found {type(loaded).__name__}"
            )
        settings = loaded.get(section) or {}
        if not isinstance(settings, dict):
            raise ValueError(f"{path}: `{section}` should hold a mapping of settings")
        found = settings.get(key)

    if found is None or found == []:
        if default is _REQUIRED:
            raise ValueError(
                f"`{section}.{key}` has no built-in default: set it in {path.name}"
            )
        return default
    if kind is bool and not isinstance(found, bool):
        raise ValueError(f"`{section}.{key}` should be true or false, found {found!r}")
    if kind is int and (
        not isinstance(found, int) or isinstance(found, bool) or found < 1
    ):
        raise ValueError(
            f"`{section}.{key}` should be a positive whole number, found {found!r}"
        )
    if kind is list:
        if isinstance(found, str) or not isinstance(found, Sequence):
            raise ValueError(f"`{section}.{key}` should be a list, found {found!r}")
        return tuple(str(item).strip() for item in found)
    return str(found) if kind is str else found


def download(path: Path = configs.CONFIG_PATH) -> DownloadSettings:
    """Settle what the download stage should do.

    Args:
        path: The config file, which need not exist.

    Returns:
        The settled choices for the stage.

    Raises:
        ValueError: When the config file holds a key it cannot honour
    """
    section = download_configs.CONFIG_SECTION
    loc = _setting(path, section, "loc", str, download_configs.DEFAULT_LOC)
    if loc not in download_configs.LOC_MODES:
        raise ValueError(
            f"loc should be one of {download_configs.LOC_MODES}, found {loc!r}"
        )
    return DownloadSettings(
        instrument_sets=tuple(
            InstrumentSet.from_key(key)
            for key in _setting(path, section, "instruments", list)
        ),
        feature_names=_setting(path, section, "features", list, None),
        loc=loc,
    )


def pipeline(path: Path = configs.CONFIG_PATH) -> PipelineSettings:
    """Settle what the run as a whole should do.

    Args:
        path: The config file, which need not exist.

    Returns:
        The settled choices for the run.

    Raises:
        ValueError: When the config file holds a key it cannot honour.
    """
    section = configs.CONFIG_SECTION
    return PipelineSettings(
        keep_metadata=_setting(
            path, section, "keep_metadata", bool, configs.DEFAULT_KEEP_METADATA
        ),
        force=_setting(path, section, "force", bool, False),
        refresh_catalog=_setting(
            path, section, "refresh_catalog", bool, configs.DEFAULT_REFRESH_CATALOG
        ),
        workers=_setting(path, section, "workers", int),
    )
