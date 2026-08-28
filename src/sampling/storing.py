"""What a sweep made of the dataset, written out so it need not be swept again."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import utils.disk.paths as paths
from sampling.models.aggregate import Aggregate
from sampling.models.dataset import ClassStats, DatasetStats
from sampling.models.spread import Spread
from selector import strategies
from utils.disk.files import atomic_path

# What separates the instruments naming one piece of shared ground in a key.
JOINED = "|"


def written(
    read: Mapping[str, DatasetStats],
    digests: Mapping[str, str],
    root: Path = paths.PREDICTIONS_ROOT,
) -> list[Path]:
    """Write out what every strategy made of the dataset, one file each.

    Args:
        read: The stats each strategy left, by strategy name.
        digests: The fingerprint to file each of them under, by strategy name.
        root: The directory to write them in, made when it is missing.

    Returns:
        The files written, in the order the strategies came in.
    """
    found: list[Path] = []
    for name, stats in read.items():
        held = stats.held
        path = root / f"{name}.json"
        written_out = (
            json.dumps(
                {
                    "strategy": stats.strategy,
                    "digest": digests[name],
                    "features": stats.features,
                    "classes": {
                        name: [held.selected, held.covered, held.days]
                        for name, held in stats.classes.items()
                    },
                    "iids": stats.iids,
                    "held": {
                        "searched": held.searched,
                        "kept": held.kept,
                        "area_km2": held.area_km2,
                        "kept_km2": held.kept_km2,
                        "days": _spread(held.days),
                        "geo_mean": _spread(held.geo_mean),
                        "reached": {
                            iid: _spread(measured)
                            for iid, measured in held.reached.items()
                        },
                        "landed": {
                            iid: _spread(measured)
                            for iid, measured in held.landed.items()
                        },
                        "per_look": held.per_look,
                        "pixel_km2": {
                            iid: _spread(measured)
                            for iid, measured in held.pixel_km2.items()
                        },
                        "overlaps": {
                            JOINED.join(names): km2
                            for names, km2 in held.overlaps.items()
                        },
                    },
                    "widths": _spread(stats.widths),
                    "offered": {
                        iid: _spread(measured)
                        for iid, measured in stats.offered.items()
                    },
                    "overlap": _spread(stats.overlap),
                },
                indent=1,
            )
            + "\n"
        )
        with atomic_path(path) as tmp:
            tmp.write_text(written_out, encoding="utf-8")
        found.append(path)
    return found


def loaded(
    root: Path = paths.PREDICTIONS_ROOT,
) -> dict[str, tuple[str, DatasetStats]]:
    """Read back what a previous run made of the dataset.

    Only the strategies written now are looked for. A file left behind by one
    since renamed or deleted names no strategy, so it is never opened. A file
    written before the stats took the shape they have now holds no reading of
    them either, so it is passed over and the strategy is swept again.

    Args:
        root: The directory the files were written in.

    Returns:
        The stats each strategy left and the digest it was filed under, by name.
    """
    found: dict[str, tuple[str, DatasetStats]] = {}
    for name in strategies.STRATEGIES:
        path = root / f"{name}.json"
        if not path.is_file():
            continue
        saved = json.loads(path.read_text(encoding="utf-8"))
        try:
            found[name] = (saved["digest"], _stats(saved))
        except KeyError:
            continue
    return found


def _stats(saved: Mapping[str, Any]) -> DatasetStats:
    """Read one strategy's stats back off what its file holds.

    Args:
        saved: What the file was written with.

    Returns:
        The stats that strategy left.

    Raises:
        KeyError: When it was written without something the stats are read from.
        TypeError: When something it holds is not the shape it is read as.
        ValueError: When a measurement it holds is not the numbers a spread is.
    """
    held = saved["held"]
    return DatasetStats(
        strategy=saved["strategy"],
        features=saved["features"],
        classes={
            name: ClassStats(int(selected), covered, days)
            for name, (selected, covered, days) in saved["classes"].items()
        },
        held=Aggregate(
            searched=held["searched"],
            kept=held["kept"],
            area_km2=held["area_km2"],
            kept_km2=held["kept_km2"],
            days=_read(held["days"]),
            geo_mean=_read(held["geo_mean"]),
            reached={iid: _read(measured) for iid, measured in held["reached"].items()},
            landed={iid: _read(measured) for iid, measured in held["landed"].items()},
            per_look=held["per_look"],
            pixel_km2={
                iid: _read(measured) for iid, measured in held["pixel_km2"].items()
            },
            overlaps={
                tuple(names.split(JOINED)): km2
                for names, km2 in held["overlaps"].items()
            },
        ),
        widths=_read(saved["widths"]),
        offered={iid: _read(measured) for iid, measured in saved["offered"].items()},
        overlap=_read(saved["overlap"]),
        iids=saved["iids"],
    )


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
