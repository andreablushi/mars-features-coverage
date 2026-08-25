"""What a sweep made of the dataset, written out so it need not be swept again."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import utils.disk.paths as paths
from prediction.models.aggregate import Aggregate
from prediction.models.spread import Spread
from prediction.stats.dataset import DatasetStats
from survey import strategies

# What separates the instruments naming one piece of shared ground in a key.
JOINED = "|"


def digest(name: str) -> str:
    """Fingerprint one strategy as it is written now.

    Args:
        name: The strategy's name, which is what its file is called.

    Returns:
        The digest of the file it is written in.
    """
    path = strategies.STRATEGIES_ROOT / f"{name}.yaml"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def written(
    read: Mapping[str, DatasetStats], root: Path = paths.PREDICTIONS_ROOT
) -> list[Path]:
    """Write out what every strategy made of the dataset, one file each.

    Args:
        read: The stats each strategy left, by strategy name.
        root: The directory to write them in, made when it is missing.

    Returns:
        The files written, in the order the strategies came in.
    """
    root.mkdir(parents=True, exist_ok=True)
    found: list[Path] = []
    for name, stats in read.items():
        held = stats.held
        path = root / f"{name}.json"
        path.write_text(
            json.dumps(
                {
                    "strategy": stats.strategy,
                    "digest": digest(name),
                    "features": stats.features,
                    "iids": stats.iids,
                    "held": {
                        "searched": held.searched,
                        "kept": held.kept,
                        "area_km2": held.area_km2,
                        "kept_km2": held.kept_km2,
                        "days": _spread(held.days),
                        "reach": _spread(held.reach),
                        "reached": {
                            iid: _spread(measured)
                            for iid, measured in held.reached.items()
                        },
                        "landed": {
                            iid: _spread(measured)
                            for iid, measured in held.landed.items()
                        },
                        "overlaps": {
                            JOINED.join(names): km2
                            for names, km2 in held.overlaps.items()
                        },
                    },
                    "sizes": _spread(stats.sizes),
                    "offered": {
                        iid: _spread(measured)
                        for iid, measured in stats.offered.items()
                    },
                    "shared": {
                        str(counted): _spread(measured)
                        for counted, measured in stats.shared.items()
                    },
                    "reaching": {
                        str(counted): tiles for counted, tiles in stats.reaching.items()
                    },
                    "covered": {
                        str(band): tiles for band, tiles in stats.covered.items()
                    },
                },
                indent=1,
            ),
            encoding="utf-8",
        )
        found.append(path)
    return found


def loaded(root: Path = paths.PREDICTIONS_ROOT) -> dict[str, DatasetStats]:
    """Read back what a previous run made of the dataset.

    Args:
        root: The directory the files were written in.

    Returns:
        The stats each strategy left, by name, leaving out any rewritten since.
    """
    found: dict[str, DatasetStats] = {}
    for path in sorted(root.glob("*.json")):
        saved = json.loads(path.read_text(encoding="utf-8"))
        name = saved["strategy"]
        if name not in strategies.STRATEGIES or saved["digest"] != digest(name):
            continue
        held = saved["held"]
        found[name] = DatasetStats(
            strategy=name,
            features=saved["features"],
            held=Aggregate(
                searched=held["searched"],
                kept=held["kept"],
                area_km2=held["area_km2"],
                kept_km2=held["kept_km2"],
                days=_read(held["days"]),
                reach=_read(held["reach"]),
                reached={
                    iid: _read(measured) for iid, measured in held["reached"].items()
                },
                landed={
                    iid: _read(measured) for iid, measured in held["landed"].items()
                },
                overlaps={
                    tuple(names.split(JOINED)): km2
                    for names, km2 in held["overlaps"].items()
                },
            ),
            sizes=_read(saved["sizes"]),
            offered={
                iid: _read(measured) for iid, measured in saved["offered"].items()
            },
            shared={
                int(counted): _read(measured)
                for counted, measured in saved["shared"].items()
            },
            reaching={
                int(counted): tiles for counted, tiles in saved["reaching"].items()
            },
            covered={float(band): tiles for band, tiles in saved["covered"].items()},
            iids=saved["iids"],
        )
    return found


def _spread(measured: Spread) -> list[float]:
    """Write one measurement out as the numbers it holds.

    Args:
        measured: The measurement read off many tiles.

    Returns:
        Its numbers, in the order the spread names them.
    """
    return [
        measured.mean,
        measured.middle,
        measured.deviation,
        measured.low,
        measured.high,
        measured.counted,
    ]


def _read(saved: Sequence[float]) -> Spread:
    """Read one measurement back off the numbers it was written as.

    Args:
        saved: Its numbers, in the order the spread names them.

    Returns:
        The measurement.
    """
    mean, middle, deviation, low, high, counted = saved
    return Spread(mean, middle, deviation, low, high, int(counted))
