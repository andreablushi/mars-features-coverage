"""Reading the ASCII table a PDS label describes, column by column."""

from __future__ import annotations

from pathlib import Path

import numpy as np

# What a PDS column data type means as a numpy dtype, once its width is known.
_INTEGER = "ASCII_INTEGER"
_TIME = "TIME"

# How wide a UT instant is written, to the millisecond.
_TIME_UNIT = "ms"


def columns(path: Path) -> list[dict[str, str]]:
    """Read the COLUMN objects one table label names, in the order written.

    Args:
        path: The `.lbl` file describing the table.

    Returns:
        One dictionary per column, keyed as the label writes it, with quotes
        and unit suffixes stripped.
    """
    found: list[dict[str, str]] = []
    inside: dict[str, str] | None = None
    for line in path.read_text(errors="replace").splitlines():
        key, _, value = (part.strip() for part in line.partition("="))
        if key == "OBJECT" and value == "COLUMN":
            inside = {}
        elif key == "END_OBJECT" and value == "COLUMN" and inside is not None:
            found.append(inside)
            inside = None
        elif inside is not None and key:
            inside[key] = value.strip('"').split("<")[0].strip()
    return found


def build_table(table: Path, label: dict[str, str], fields: list[dict[str, str]]):
    """Read one fixed width ASCII table into a row per record.

    Args:
        table: The `.tab` file holding the records.
        label: The parsed label describing it.
        fields: The COLUMN objects, as `columns` returns them.

    Returns:
        A structured array of one row per record, its fields named as the label
        names them, integers read as integers, times as datetimes and the rest
        as floats.

    Raises:
        ValueError: When the file does not hold the records the label promises.
    """
    rows, width = int(label["ROWS"]), int(label["ROW_BYTES"])
    raw = np.fromfile(table, dtype="S1", count=rows * width)
    if raw.size < rows * width:
        raise ValueError(f"{table.name} holds fewer than the {rows} rows promised.")
    # One fixed width record per row, so a column is a slice of every one.
    records = raw.reshape(rows, width)
    built = {}
    for field in fields:
        # START_BYTE is written one based, and BYTES is the width that follows.
        start = int(field["START_BYTE"]) - 1
        cut = records[:, start : start + int(field["BYTES"])]
        text = np.char.strip(cut.view(f"S{cut.shape[1]}").reshape(rows))
        built[field["NAME"]] = _cast(text, field["DATA_TYPE"])
    return np.rec.fromarrays(list(built.values()), names=list(built))


def _cast(text: np.ndarray, kind: str) -> np.ndarray:
    """Read one column's text as the type its label names.

    Args:
        text: The column's values as written, one per record.
        kind: The PDS data type the label gives the column.

    Returns:
        The column as integers, datetimes, or floats.
    """
    if kind == _INTEGER:
        return text.astype("i8")
    if kind == _TIME:
        return text.astype(f"M8[{_TIME_UNIT}]")
    return text.astype("f8")
