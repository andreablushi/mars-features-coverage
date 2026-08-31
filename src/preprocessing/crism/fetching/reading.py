"""Reading a CRISM product off disk from its PDS label.

Ported from crism_ml's `io._generate_envi_header`, `io.crism_to_mat` and
`io.load_image`.

Differs from crism_ml:
  - No `spectral` dependency and no generated `.hdr`. crism_ml writes an ENVI
    header out of the label and reopens it through `spectral`; the same label
    fields are read here and the array comes straight from `np.fromfile`.
    `spectral` is not a dependency of this project and adding it would put a
    raster library in the main group for the sake of three integers.
  - The interleave comes from the label. crism_ml's header writer hardcodes
    `interleave = bil`, which is right for a TRDR and silently wrong for the
    geometry file beside it, whose BAND_STORAGE_TYPE is BAND_SEQUENTIAL.
  - Keys are matched whole rather than by substring, and the first value wins.
    crism_ml tests `if "LINES" in line`, which also fires on any longer key
    that happens to contain it.
  - Only the image is read. A TRDR holds lines by bands records and then one
    more for the table of detector rows, so exactly lines by bands by samples
    values are taken and the trailing record is left alone.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# What a PDS sample type and width mean as a numpy dtype.
_DTYPES = {("PC_REAL", 32): "<f4", ("PC_REAL", 64): "<f8"}

_BIL = "LINE_INTERLEAVED"
_BSQ = "BAND_SEQUENTIAL"


def read_label(path: Path) -> dict[str, str]:
    """Read a PDS label into its keys and values.

    Values spanning several lines, such as the braced list of source products,
    are skipped: nothing here needs them. Where a key appears more than once,
    as RECORD_BYTES does when a label describes several files, the first value
    is kept, which is the one belonging to the image.

    Args:
        path: The `.lbl` file to read.

    Returns:
        The label, keyed as written, with quotes and unit suffixes stripped.
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
            label[key] = value.strip('"').split("<")[0].strip()
    return label


def shape_of(label: dict[str, str]) -> tuple[int, int, int]:
    """Return how many lines, samples and bands the image holds.

    Args:
        label: The parsed label.

    Returns:
        The lines, samples and bands, in that order.

    Raises:
        KeyError: When the label names none of them.
    """
    return (
        int(label["LINES"]),
        int(label["LINE_SAMPLES"]),
        int(label["BANDS"]),
    )


def dtype_of(label: dict[str, str]) -> str:
    """Return the numpy dtype the image is written in.

    Args:
        label: The parsed label.

    Returns:
        The dtype string, byte order included.

    Raises:
        ValueError: When the label names a sample type this cannot read.
    """
    sample = (label["SAMPLE_TYPE"], int(label["SAMPLE_BITS"]))
    if sample not in _DTYPES:
        raise ValueError(
            f"Cannot read samples of type {sample[0]} at {sample[1]} bits."
        )
    return _DTYPES[sample]


def read_cube(path: Path, label: dict[str, str]) -> np.ndarray:
    """Read an image into an array indexed by line, sample and band.

    Args:
        path: The `.img` file holding the values.
        label: The parsed label describing it.

    Returns:
        The values as lines by samples by bands, in the band order the file
        stores them in.

    Raises:
        ValueError: When the label names an interleave this cannot read, or the
            file is shorter than the label says.
    """
    lines, samples, bands = shape_of(label)
    stored = label.get("BAND_STORAGE_TYPE", _BIL)
    if stored not in (_BIL, _BSQ):
        raise ValueError(f"Cannot read a {stored} image.")

    wanted = lines * samples * bands
    flat = np.fromfile(path, dtype=dtype_of(label), count=wanted)
    if flat.size < wanted:
        raise ValueError(f"{path.name} holds {flat.size} values, not {wanted}.")

    if stored == _BIL:
        return flat.reshape(lines, bands, samples).transpose(0, 2, 1)
    return flat.reshape(bands, lines, samples).transpose(1, 2, 0)


def read(path: Path) -> tuple[np.ndarray, dict[str, str]]:
    """Read one product from either half of its pair.

    The image file is found beside the label under the same stem, rather than
    through the label's own pointer, which is written upper case while the
    archive stores the file lower case.

    Args:
        path: Either the `.lbl` or the `.img` of one product.

    Returns:
        The values as lines by samples by bands, and the parsed label.

    Raises:
        FileNotFoundError: When either half of the pair is missing.
    """
    label_path, image_path = path.with_suffix(".lbl"), path.with_suffix(".img")
    for needed in (label_path, image_path):
        if not needed.exists():
            raise FileNotFoundError(f"{needed} is missing.")
    label = read_label(label_path)
    return read_cube(image_path, label), label
