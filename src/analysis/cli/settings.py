"""Settling the coverage stage's choices from its section of the config file.

The ranking and the file reading live in `common.settings`. Nothing here is
specific enough to need more than a type check, so this is only the mapping
from the stage's keys onto its settings.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from analysis import configs
from analysis.models.settings import AnalysisSettings
from common import settings
from common.configs import CONFIG_PATH


def resolve(args: argparse.Namespace, path: Path = CONFIG_PATH) -> AnalysisSettings:
    """Settle what a coverage run should do from its flags and the config file.

    Args:
        args: The parsed command line arguments.
        path: The config file, which need not exist.

    Returns:
        The settled choices for the run.

    Raises:
        ValueError: When the config file holds a key it cannot honour.
    """
    config = settings.section(configs.CONFIG_SECTION, path)
    union = settings.first(
        args.cumulative_union,
        config.get("cumulative_union"),
        configs.DEFAULT_CUMULATIVE_UNION,
    )
    force = settings.first(args.force, config.get("force"), False)
    workers = settings.first(
        args.workers, config.get("workers"), configs.DEFAULT_WORKERS
    )
    return AnalysisSettings(
        cumulative_union=settings.boolean(union, "cumulative_union"),
        force=settings.boolean(force, "force"),
        workers=settings.positive_int(workers, "workers"),
    )
