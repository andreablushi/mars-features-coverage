"""The weightings of the instruments a search can be run under, side by side."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from analysis.selector.models.strategy import Strategy

STRATEGIES_ROOT = Path(__file__).parent

# The strategies each one is built from, the furthest base first and itself last.
_CHAINS: dict[str, tuple[str, ...]] = {}


def load(root: Path = STRATEGIES_ROOT) -> dict[str, Strategy]:
    """Read every strategy the comparison can be run over.

    Args:
        root: The directory the strategies are written in, one file each.

    Returns:
        The strategies, by the name each file goes by.

    Raises:
        ValueError: When the directory holds no strategy, or one cannot be read.
    """
    written = {
        path.stem: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(root.glob("*.yaml"))
    }
    if not written:
        raise ValueError(f"{root} holds no strategy to search under")
    _CHAINS.clear()
    _CHAINS.update({name: _chain(name, written, root) for name in written})
    return {
        name: _strategy(name, _settled(name, written, root), root / f"{name}.yaml")
        for name in written
    }


def _chain(name: str, written: Mapping[str, Any], root: Path) -> tuple[str, ...]:
    """Walk the strategies one is written as a change to, itself last.

    Args:
        name: The strategy to walk from.
        written: What every file in the directory holds, by name.
        root: The directory they are written in, named when a base cannot be read.

    Returns:
        The names it is built from, the furthest base first and itself last.

    Raises:
        ValueError: When a base is not written, or the bases run in a circle.
    """
    held: list[str] = []
    seen = name
    while seen is not None:
        if seen in held:
            raise ValueError(f"{root}: `{name}` is written as a change to itself")
        if seen not in written:
            raise ValueError(f"{root}: `{name}` is a change to `{seen}`, unwritten")
        held.append(seen)
        spec = written[seen]
        seen = spec.get("base") if isinstance(spec, Mapping) else None
    return tuple(reversed(held))


def _settled(name: str, written: Mapping[str, Any], root: Path) -> Any:
    """Lay one strategy over the strategies it is written as a change to.

    Args:
        name: The strategy to settle.
        written: What every file in the directory holds, by name.
        root: The directory they are written in, named when a base cannot be read.

    Returns:
        Every setting it runs under, its own overriding the ones it changes.
    """
    spec: dict[str, Any] = {}
    for held in _chain(name, written, root):
        if not isinstance(written[held], Mapping):
            return written[held]
        spec.update(written[held])
    spec.pop("base", None)
    return spec


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
        The digest of its file and of every file it is written as a change to.
    """
    running = hashlib.sha256()
    for held in _CHAINS.get(name, (name,)):
        running.update((STRATEGIES_ROOT / f"{held}.yaml").read_bytes())
    return running.hexdigest()


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
