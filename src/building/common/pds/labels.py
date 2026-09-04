"""Reading a PDS or ISIS label, and whatever it says about what sits beside it."""

from __future__ import annotations

from pathlib import Path

# The order a TRDR writes its bands in, against a DDR's band sequential.
BIL = "LINE_INTERLEAVED"

# What a PDS sample type and width mean as a numpy dtype.
_DTYPES = {
    ("PC_REAL", 32): "<f4",
    ("PC_REAL", 64): "<f8",
    ("MSB_INTEGER", 16): ">i2",
    ("UNSIGNED_INTEGER", 8): "u1",
}


def _value(text: str) -> str:
    """Return one label value, its quotes and its unit suffix stripped.

    Args:
        text: What the label writes after the equals sign.

    Returns:
        The value alone.
    """
    return text.strip().strip('"').split("<")[0].strip()


def load(path: Path) -> dict[str, str]:
    """Read a label into its keys and values.

    Args:
        path: The `.lbl` or `.hdr` file to read.

    Returns:
        The label, keyed as written, with quotes and unit suffixes stripped.
        Where a key is written more than once the first wins.
    """
    label: dict[str, str] = {}
    skipping = False
    for line in path.read_text(errors="replace").splitlines():
        if skipping:
            skipping = "}" not in line
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if value.startswith("{") and "}" not in value:
            skipping = True
            continue
        key = key.strip()
        if key and key not in label:
            label[key] = _value(value)
    return label


def layout(label: dict[str, str]) -> tuple[int, int, int, str, str]:
    """Read how one image is shaped and written from its label.

    Args:
        label: The parsed label.

    Returns:
        The lines, samples and bands it holds, the order its bands are written
        in, and the numpy dtype its samples are stored as.

    Raises:
        KeyError: When it names a sample type this cannot read.
    """
    # How many rows the image holds.
    lines = int(label["LINES"])
    # How many columns each row holds.
    samples = int(label["LINE_SAMPLES"])
    # How many channels each pixel holds, which a single band image omits.
    bands = int(label.get("BANDS", 1))
    # The order bands are written in, BIL for a TRDR and BSQ for a DDR.
    stored = label.get("BAND_STORAGE_TYPE", BIL)
    # The sample type and its width, which together name a numpy dtype.
    dtype = _DTYPES[label["SAMPLE_TYPE"], int(label["SAMPLE_BITS"])]
    return lines, samples, bands, stored, dtype


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
            inside[key] = _value(value)
    return found
