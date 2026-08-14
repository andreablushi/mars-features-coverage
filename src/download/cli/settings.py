"""Settling the download stage's choices from its section of the config file.

The ranking and the file reading live in `common.settings`. What is here is
only what the download stage alone knows: that an instrument set is a triple,
and that ODE understands two location modes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import settings
from common.configs import CONFIG_PATH
from download import configs
from download.models.instrument import InstrumentSet
from download.models.settings import DownloadSettings


def resolve(args: argparse.Namespace, path: Path = CONFIG_PATH) -> DownloadSettings:
    """Settle what a download run should do from its flags and the config file.

    Args:
        args: The parsed command line arguments.
        path: The config file, which need not exist.

    Returns:
        The settled choices for the run.

    Raises:
        ValueError: When the config file holds a key it cannot honour.
    """
    config = settings.section(configs.CONFIG_SECTION, path)
    workers = settings.first(
        args.workers, config.get("workers"), configs.DEFAULT_WORKERS
    )
    force = settings.first(args.force, config.get("force"), False)
    return DownloadSettings(
        instrument_sets=_instrument_sets(
            args.instrument_set, config.get("instruments")
        ),
        loc=_loc(args.loc, config.get("loc")),
        force=settings.boolean(force, "force"),
        workers=settings.positive_int(workers, "workers"),
    )


def _instrument_sets(
    flag: list[str] | None, configured: Any
) -> tuple[InstrumentSet, ...]:
    """Settle which instrument sets to download.

    Args:
        flag: The sets named on the command line, or None.
        configured: The sets named in the config file, or None.

    Returns:
        One instrument set per requested triple.

    Raises:
        ValueError: When a triple is malformed or the list is empty.
    """
    keys = settings.first(flag, configured, list(configs.DEFAULT_INSTRUMENT_SETS))
    if not keys:
        raise ValueError("no instrument sets requested")
    return tuple(_instrument_set(key) for key in keys)


def _instrument_set(key: Any) -> InstrumentSet:
    """Build one instrument set from an IHID/IID/PT triple.

    Args:
        key: The triple, as a string or as the three parts.

    Returns:
        The instrument set.

    Raises:
        ValueError: When the triple does not carry exactly three parts.
    """
    parts = key.split("/") if isinstance(key, str) else list(key)
    if len(parts) != 3 or not all(str(part).strip() for part in parts):
        raise ValueError(f"instrument set should be IHID/IID/PT, found {key!r}")
    return InstrumentSet(*(str(part).strip() for part in parts))


def _loc(flag: str | None, configured: Any) -> str:
    """Settle which products ODE returns for a feature box.

    Args:
        flag: The mode passed on the command line, or None.
        configured: The mode named in the config file, or None.

    Returns:
        The location mode.

    Raises:
        ValueError: When the mode is not one ODE understands.
    """
    loc = str(settings.first(flag, configured, configs.DEFAULT_LOC))
    if loc not in configs.LOC_MODES:
        raise ValueError(f"loc should be one of {configs.LOC_MODES}, found {loc!r}")
    return loc
