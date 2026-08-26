"""Reading config.yaml, which is the only place a run is configured from."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

import utils.disk.paths as paths
from metadata import configs as download_configs
from models.instrument import InstrumentSet
from models.settings import Settings


def _setting(
    config: Mapping[str, Any], key: str, kind: type, *, required: bool = True
) -> Any:
    """Read one setting from the config file and check the value is valid.

    Args:
        config: The settings the config file holds, keyed by name.
        key: The setting's name.
        kind: What the value has to be: bool, int above zero, str, or list.
        required: Whether the file has to give the setting.

    Returns:
        The configured value, or None when an optional setting is absent.

    Raises:
        ValueError: When a setting is missing, or is not what its kind asks for.
    """
    found = config.get(key)
    if found is None or found == []:
        if required:
            raise ValueError(f"`{key}` is not set in {paths.CONFIG_PATH.name}")
        return None
    if kind is bool and not isinstance(found, bool):
        raise ValueError(f"`{key}` should be true or false, found {found!r}")
    if kind is int and (
        not isinstance(found, int) or isinstance(found, bool) or found < 1
    ):
        raise ValueError(f"`{key}` should be a positive whole number, found {found!r}")
    if kind is list:
        if isinstance(found, str) or not isinstance(found, Sequence):
            raise ValueError(f"`{key}` should be a list, found {found!r}")
        return tuple(str(item).strip() for item in found)
    return str(found) if kind is str else found


def load(path: Path = paths.CONFIG_PATH) -> Settings:
    """Settle what a run should do, reading the config file once.

    Args:
        path: The config file, which has to exist and carry every setting.

    Returns:
        The settled choices for the run.

    Raises:
        ValueError: When the file holds no mapping of settings, or one it cannot honour.
    """
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise ValueError(f"{path} should hold a mapping, found {type(config).__name__}")
    loc = _setting(config, "loc", str)
    if loc not in download_configs.LOC_MODES:
        raise ValueError(
            f"loc should be one of {download_configs.LOC_MODES}, found {loc!r}"
        )
    plotted = _setting(config, "plot_instruments", list, required=False)
    return Settings(
        grid_km=_setting(config, "grid_km", int),
        grid_cells=_setting(config, "grid_cells", int),
        instrument_sets=tuple(
            InstrumentSet.from_key(key) for key in _setting(config, "instruments", list)
        ),
        plot_instrument_sets=tuple(InstrumentSet.from_key(key) for key in plotted)
        if plotted
        else None,
        loc=loc,
        keep_metadata=_setting(config, "keep_metadata", bool),
        force=_setting(config, "force", bool),
        refresh_catalog=_setting(config, "refresh_catalog", bool),
        workers=_setting(config, "workers", int),
    )
