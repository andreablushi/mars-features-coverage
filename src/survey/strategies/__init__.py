"""The weightings of the instruments a search can be run under, side by side.

Every strategy is one YAML file beside this one, named after it, so a strategy
that loses the comparison is removed by deleting its file. Nothing here says
which one a run uses: a search is handed the strategy it runs under, never
configured with one.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from survey.models.strategy import Strategy

STRATEGIES_ROOT = Path(__file__).parent


def load(root: Path = STRATEGIES_ROOT) -> dict[str, Strategy]:
    """Read every strategy the comparison can be run over.

    Args:
        root: The directory the strategies are written in, one file each.

    Returns:
        The strategies, by the name each file goes by.

    Raises:
        ValueError: When the directory holds no strategy, or one of them is
            written in a way it cannot be read.
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
    demands = spec.get("demands")
    if isinstance(demands, str) or not isinstance(demands, Sequence) or not demands:
        raise ValueError(f"{path.name}: `{name}` needs a list of `demands`")
    for demand in demands:
        if not isinstance(demand, Mapping) or not demand:
            raise ValueError(
                f"{path.name}: `{name}` wants each demand as instrument to "
                f"share, found {demand!r}"
            )
    timeless = spec.get("timeless") or []
    if isinstance(timeless, str) or not isinstance(timeless, Sequence):
        raise ValueError(f"{path.name}: `{name}` wants `timeless` as a list")
    admits = spec.get("admits") or {}
    if not isinstance(admits, Mapping):
        raise ValueError(f"{path.name}: `{name}` wants `admits` as instrument to cells")
    return Strategy(
        name=name,
        demands=tuple(
            {
                str(iid): _number(name, "demands", share, path)
                for iid, share in demand.items()
            }
            for demand in demands
        ),
        admits={
            str(iid): int(_number(name, "admits", cells, path))
            for iid, cells in admits.items()
        },
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
