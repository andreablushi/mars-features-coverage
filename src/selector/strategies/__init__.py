"""The weightings of the instruments a search can be run under, side by side."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from selector.models.strategy import Strategy

# How wide a tile is when a strategy does not say, in kilometres.
TILE_KM = 100.0

# What an observation has to bring a window when a strategy does not say, in cells.
GAIN = 5

STRATEGIES_ROOT = Path(__file__).parent


def load(root: Path = STRATEGIES_ROOT) -> dict[str, Strategy]:
    """Read every strategy the comparison can be run over.

    Args:
        root: The directory the strategies are written in, one file each.

    Returns:
        The strategies, by the name each file goes by.

    Raises:
        ValueError: When the directory holds no strategy, or one cannot be read.
    """
    found = {
        path.stem: _strategy(
            path.stem, yaml.safe_load(path.read_text(encoding="utf-8")), path
        )
        for path in sorted(root.glob("*.yaml"))
    }
    if not found:
        raise ValueError(f"{root} holds no strategy to search under")
    return found


def _strategy(name: str, spec: Any, path: Path) -> Strategy:
    """Read one strategy from what the file writes under its name.

    Args:
        name: The name the strategy is written under, which is what it goes by.
        spec: What the file writes under it.
        path: The file, named when something in it cannot be read.

    Returns:
        The strategy.

    Raises:
        ValueError: When a setting is missing or is not what it has to be.
    """
    if not isinstance(spec, Mapping):
        raise ValueError(
            f"{path.name}: `{name}` should hold its settings, found {spec!r}"
        )
    constraints = spec.get("constraints")
    if (
        isinstance(constraints, str)
        or not isinstance(constraints, Sequence)
        or not constraints
    ):
        raise ValueError(f"{path.name}: `{name}` needs a list of `constraints`")
    for constraint in constraints:
        if not isinstance(constraint, Mapping) or not constraint:
            raise ValueError(
                f"{path.name}: `{name}` wants each constraint as instrument to "
                f"share, found {constraint!r}"
            )
    timeless = spec.get("timeless") or []
    if isinstance(timeless, str) or not isinstance(timeless, Sequence):
        raise ValueError(f"{path.name}: `{name}` wants `timeless` as a list")
    admits = spec.get("admits") or {}
    if not isinstance(admits, Mapping):
        raise ValueError(
            f"{path.name}: `{name}` wants `admits` as instrument to pixels"
        )
    return Strategy(
        name=name,
        constraints=tuple(
            {
                str(iid): _number(name, "constraints", share, path)
                for iid, share in constraint.items()
            }
            for constraint in constraints
        ),
        admits={
            str(iid): _number(name, "admits", pixels, path)
            for iid, pixels in admits.items()
        },
        tile_km=_number(name, "tile_km", spec.get("tile_km", TILE_KM), path),
        gain=int(_number(name, "gain", spec.get("gain", GAIN), path)),
        span_days=_number(name, "span_days", spec.get("span_days"), path),
        timeless=frozenset(str(iid) for iid in timeless),
    )


def _number(name: str, key: str, found: Any, path: Path) -> float:
    """Read one number a strategy is written with.

    Args:
        name: The strategy it belongs to.
        key: What the number is called.
        found: What the file writes for it.
        path: The file, named when the number cannot be read.

    Returns:
        The number.

    Raises:
        ValueError: When it is missing or is not a number at or above nought.
    """
    if isinstance(found, bool) or not isinstance(found, (int, float)) or found < 0.0:
        raise ValueError(
            f"{path.name}: `{name}` wants `{key}` as a number, found {found!r}"
        )
    return float(found)


STRATEGIES: dict[str, Strategy] = load()


def digest(name: str) -> str:
    """Fingerprint one strategy as it is written now.

    Args:
        name: The strategy's name, which is what its file is called.

    Returns:
        The digest of the file it is written in.
    """
    return hashlib.sha256((STRATEGIES_ROOT / f"{name}.yaml").read_bytes()).hexdigest()


def named(name: str) -> Strategy:
    """Return the strategy one name stands for.

    Args:
        name: The strategy's name, as the file writes it.

    Returns:
        The strategy.

    Raises:
        KeyError: When no strategy goes by that name.
    """
    if name not in STRATEGIES:
        raise KeyError(f"no strategy named {name!r}, try one of {sorted(STRATEGIES)}")
    return STRATEGIES[name]
