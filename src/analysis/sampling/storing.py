"""What a sweep made of the dataset, written out so it need not be swept again.

The keys below are the published format, not the field names the stats carry,
so a field may be renamed without every published file having to be swept again.
Only a change to what is written raises `configs.PREDICTION_SHAPE`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import utils.disk.paths as paths
from analysis.sampling import configs
from analysis.sampling.models.dataset import ClassStats, DatasetStats
from analysis.sampling.models.spread import Spread
from analysis.sampling.models.tiles import Aggregate
from analysis.selector import strategies
from utils.disk.files import atomic_path


def write_predictions(
    predicted: Mapping[str, DatasetStats],
    digests: Mapping[str, str],
    root: Path = paths.PREDICTIONS_ROOT,
) -> list[Path]:
    """Write out what every strategy made of the dataset, one file each.

    Args:
        predicted: The stats each strategy left, by strategy name.
        digests: The fingerprint to file each of them under, by strategy name.
        root: The directory to write them in, made when it is missing.

    Returns:
        The files written, in the order the strategies came in.
    """
    written: list[Path] = []
    for name, stats in predicted.items():
        path = root / f"{name}.json"
        with atomic_path(path) as tmp:
            tmp.write_text(
                json.dumps(_as_json(stats, digests[name]), indent=1) + "\n",
                encoding="utf-8",
            )
        written.append(path)
    return written


def read_predictions(
    root: Path = paths.PREDICTIONS_ROOT,
) -> dict[str, tuple[str, DatasetStats]]:
    """Read back what a previous run made of the dataset.

    Only the strategies written now are looked for. A file left behind by one
    since renamed or deleted names no strategy, so it is never opened. A file
    written under an older shape, or one nothing can be read from at all, is
    passed over, named on the way past, and the strategy is swept again.

    Args:
        root: The directory the files were written in.

    Returns:
        The stats each strategy left and the digest it was filed under, by name.
    """
    published: dict[str, tuple[str, DatasetStats]] = {}
    for name in strategies.STRATEGIES:
        path = root / f"{name}.json"
        if not path.is_file():
            continue
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            shape = saved.get("shape")
            if shape != configs.PREDICTION_SHAPE:
                raise ValueError(f"shape {shape!r}, not {configs.PREDICTION_SHAPE}")
            published[name] = (saved["digest"], _from_json(saved))
        except Exception as why:
            # A file that cannot be read leaves no answer but to sweep again
            print(
                f"{path.name} cannot be read back ({why}), so `{name}` is swept again"
            )
    return published


def _as_json(stats: DatasetStats, digest: str) -> dict[str, Any]:
    """Lay one strategy's stats out as the file holds them.

    Args:
        stats: What that strategy made of the dataset.
        digest: The fingerprint it is filed under.

    Returns:
        What the file is written from.
    """
    tiles = stats.tiles
    return {
        "strategy": stats.strategy,
        "shape": configs.PREDICTION_SHAPE,
        "digest": digest,
        "features": stats.features,
        "classes": {
            name: [held.selected, _spreads(held.taken)]
            for name, held in stats.classes.items()
        },
        "iids": stats.iids,
        "held": {
            "searched": tiles.searched,
            "kept": tiles.kept,
            "area_km2": tiles.area_km2,
            "kept_km2": tiles.kept_km2,
            "days": _spread(tiles.days),
            "geo_mean": _spread(tiles.geo_mean),
            "reached": _spreads(tiles.reached),
            "landed": _spreads(tiles.landed),
            "per_look": _spreads(tiles.pixels_per_look),
            "pixel_km2": _spreads(tiles.pixel_km2),
            "overlaps": {
                configs.INSTRUMENTS_JOINED.join(names): km2
                for names, km2 in tiles.overlaps.items()
            },
        },
        "widths": _spread(stats.widths),
        "offered": _spreads(stats.offered),
        "overlap": _spread(stats.overlap),
    }


def _from_json(saved: Mapping[str, Any]) -> DatasetStats:
    """Read one strategy's stats back off what its file holds.

    Args:
        saved: What the file was written with.

    Returns:
        The stats that strategy left.

    Raises:
        Exception: When anything it holds is not what the stats are read from.
            The caller checks the shape first and treats any failure here as a
            file it cannot read.
    """
    tiles = saved["held"]
    return DatasetStats(
        strategy=saved["strategy"],
        features=saved["features"],
        classes={
            name: ClassStats(int(selected), _spreads_back(taken))
            for name, (selected, taken) in saved["classes"].items()
        },
        tiles=Aggregate(
            searched=tiles["searched"],
            kept=tiles["kept"],
            area_km2=tiles["area_km2"],
            kept_km2=tiles["kept_km2"],
            days=_read(tiles["days"]),
            geo_mean=_read(tiles["geo_mean"]),
            reached=_spreads_back(tiles["reached"]),
            landed=_spreads_back(tiles["landed"]),
            pixels_per_look=_spreads_back(tiles["per_look"]),
            pixel_km2=_spreads_back(tiles["pixel_km2"]),
            overlaps={
                tuple(names.split(configs.INSTRUMENTS_JOINED)): km2
                for names, km2 in tiles["overlaps"].items()
            },
        ),
        widths=_read(saved["widths"]),
        offered=_spreads_back(saved["offered"]),
        overlap=_read(saved["overlap"]),
        iids=saved["iids"],
    )


def _spreads(measured: Mapping[str, Spread]) -> dict[str, list[float]]:
    """Write out one measurement per instrument.

    Args:
        measured: The measurement each instrument left, by instrument.

    Returns:
        The numbers each of them holds, by instrument.
    """
    return {iid: _spread(one) for iid, one in measured.items()}


def _spreads_back(saved: Mapping[str, Sequence[float]]) -> dict[str, Spread]:
    """Read one measurement per instrument back.

    Args:
        saved: The numbers each instrument's measurement was written as.

    Returns:
        The measurement each of them left, by instrument.
    """
    return {iid: _read(one) for iid, one in saved.items()}


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
