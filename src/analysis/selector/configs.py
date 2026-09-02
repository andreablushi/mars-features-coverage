"""Central configuration for the best time window search.

The thresholds below are the ones the search itself turns on. What each
instrument is asked for is written in `configs/filter.yaml` and read here, so
the search is configured from one place whether a number is written in code or
in the file.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

import utils.disk.paths as paths
from analysis.selector.models.filter import Filter

# How many days of waiting one more percentage point of ground is worth.
DAYS_PER_PERCENT = 10.0

# The cells an observation has to reach that no other observation of its own set
# already does, or the window is trimmed of it. At one only a full repeat is
# dropped, and every higher value drops a look that does add ground.
GAIN = 1

# Seconds in a day, which is what every span is measured in.
DAY_SECONDS = 86400.0


def load(path: Path = paths.FILTER_CONFIG_PATH) -> Filter:
    """Read what the instruments are asked for before a feature earns a place.

    Args:
        path: The filter config, which has to exist and carry every setting.

    Returns:
        The filter every search runs under.

    Raises:
        ValueError: When a setting is missing or is not what it has to be.
    """
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(spec, Mapping):
        raise ValueError(f"{path.name} should hold its settings, found {spec!r}")
    constraints = spec.get("constraints")
    if (
        isinstance(constraints, str)
        or not isinstance(constraints, Sequence)
        or not constraints
    ):
        raise ValueError(f"{path.name} needs a list of `constraints`")
    for constraint in constraints:
        if not isinstance(constraint, Mapping) or not constraint:
            raise ValueError(
                f"{path.name} wants each constraint as instrument to share, "
                f"found {constraint!r}"
            )
    timeless = spec.get("timeless") or []
    if isinstance(timeless, str) or not isinstance(timeless, Sequence):
        raise ValueError(f"{path.name} wants `timeless` as a list")
    admits = spec.get("admits") or {}
    if not isinstance(admits, Mapping):
        raise ValueError(f"{path.name} wants `admits` as instrument to pixels")
    return Filter(
        constraints=tuple(
            {
                str(iid): _number("constraints", share, path)
                for iid, share in constraint.items()
            }
            for constraint in constraints
        ),
        admits={
            str(iid): _number("admits", pixels, path) for iid, pixels in admits.items()
        },
        span_days=_number("span_days", spec.get("span_days"), path),
        timeless=frozenset(str(iid) for iid in timeless),
    )


def digest(path: Path = paths.FILTER_CONFIG_PATH) -> str:
    """Fingerprint the filter as it is written now.

    Args:
        path: The filter config.

    Returns:
        The digest of the file, so a published sweep of an edited one is never
        read back.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _number(key: str, found: Any, path: Path) -> float:
    """Read one number the filter is written with.

    Args:
        key: What the number is called.
        found: What the file writes for it.
        path: The file, named when the number cannot be read.

    Returns:
        The number.

    Raises:
        ValueError: When it is missing or is not a number at or above nought.
    """
    if isinstance(found, bool) or not isinstance(found, (int, float)) or found < 0.0:
        raise ValueError(f"{path.name} wants `{key}` as a number, found {found!r}")
    return float(found)


FILTER: Filter = load()
