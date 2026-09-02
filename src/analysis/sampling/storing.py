"""What a sweep made of the dataset, written out so it need not be swept again.

The keys below are the published format, not the field names the stats carry,
so a field may be renamed without the published file having to be swept again.
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
from analysis.sampling.models.feature import Aggregate
from analysis.sampling.models.spread import Spread
from utils.disk.files import atomic_path


def prediction_path(root: Path = paths.PREDICTIONS_ROOT) -> Path:
    """Return the file a sweep is published as.

    Args:
        root: The directory it is written in.

    Returns:
        The file, which need not exist.
    """
    return root / paths.PREDICTION_NAME


def write_prediction(
    predicted: DatasetStats, digest: str, root: Path = paths.PREDICTIONS_ROOT
) -> Path:
    """Write out what the filter made of the dataset.

    Args:
        predicted: The stats the sweep left.
        digest: The fingerprint of the filter it was swept under.
        root: The directory to write it in, made when it is missing.

    Returns:
        The file written.
    """
    path = prediction_path(root)
    with atomic_path(path) as tmp:
        tmp.write_text(
            json.dumps(_as_json(predicted, digest), indent=1) + "\n", encoding="utf-8"
        )
    return path


def read_prediction(
    root: Path = paths.PREDICTIONS_ROOT,
) -> tuple[str, DatasetStats] | None:
    """Read back what a previous run made of the dataset.

    A file written under an older shape, or one nothing can be read from at all,
    is passed over and named on the way past, so the sweep runs again.

    Args:
        root: The directory the file was written in.

    Returns:
        The digest it was filed under and the stats it holds, or None where
        there is nothing to read back.
    """
    path = prediction_path(root)
    if not path.is_file():
        return None
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        shape = saved.get("shape")
        if shape != configs.PREDICTION_SHAPE:
            raise ValueError(f"shape {shape!r}, not {configs.PREDICTION_SHAPE}")
        return (saved["digest"], _from_json(saved))
    except Exception as why:
        # A file that cannot be read leaves no answer but to sweep again
        print(f"{path.name} cannot be read back ({why}), so the sweep runs again")
        return None


def _as_json(stats: DatasetStats, digest: str) -> dict[str, Any]:
    """Lay the stats out as the file holds them.

    Args:
        stats: What the filter made of the dataset.
        digest: The fingerprint it is filed under.

    Returns:
        What the file is written from.
    """
    held = stats.held
    return {
        "shape": configs.PREDICTION_SHAPE,
        "digest": digest,
        "features": stats.features,
        "classes": {
            name: [held.selected, _spreads(held.taken)]
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
            "reached": _spreads(held.reached),
            "landed": _spreads(held.landed),
            "per_look": _spreads(held.pixels_per_look),
            "pixel_km2": _spreads(held.pixel_km2),
            "overlaps": {
                configs.INSTRUMENTS_JOINED.join(names): km2
                for names, km2 in held.overlaps.items()
            },
        },
        "widths": _spread(stats.widths),
        "offered": _spreads(stats.offered),
        "overlap": _spread(stats.overlap),
    }


def _from_json(saved: Mapping[str, Any]) -> DatasetStats:
    """Read the stats back off what the file holds.

    Args:
        saved: What the file was written with.

    Returns:
        The stats the sweep left.

    Raises:
        Exception: When anything it holds is not what the stats are read from.
            The caller checks the shape first and treats any failure here as a
            file it cannot read.
    """
    held = saved["held"]
    return DatasetStats(
        features=saved["features"],
        classes={
            name: ClassStats(int(selected), _spreads_back(taken))
            for name, (selected, taken) in saved["classes"].items()
        },
        held=Aggregate(
            searched=held["searched"],
            kept=held["kept"],
            area_km2=held["area_km2"],
            kept_km2=held["kept_km2"],
            days=_read(held["days"]),
            geo_mean=_read(held["geo_mean"]),
            reached=_spreads_back(held["reached"]),
            landed=_spreads_back(held["landed"]),
            pixels_per_look=_spreads_back(held["per_look"]),
            pixel_km2=_spreads_back(held["pixel_km2"]),
            overlaps={
                tuple(names.split(configs.INSTRUMENTS_JOINED)): km2
                for names, km2 in held["overlaps"].items()
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
        measured: The measurement read off many features.

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
