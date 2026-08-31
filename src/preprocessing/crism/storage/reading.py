"""Reading one CRISM observation off disk."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from preprocessing.crism.calibration import bands_calibration
from preprocessing.crism.models.observation import CrismObservation, Detector
from preprocessing.crism.storage import locations, naming

# What a PDS sample type and width mean as a numpy dtype.
_DTYPES = {("PC_REAL", 32): "<f4", ("PC_REAL", 64): "<f8"}

# The two orders a CRISM image is written in.
_BIL = "LINE_INTERLEAVED"
_BSQ = "BAND_SEQUENTIAL"


def read(identifier: str) -> CrismObservation:
    """Read every image one observation was downloaded as into an observation.

    Args:
        identifier: The observation, whose files must already be in the cache
            that `download.fetch` puts them in.

    Returns:
        The observation, both detectors and both geometries loaded, each cube
        in the band order its file stores, which is long wavelength first.

    Raises:
        FileNotFoundError: When any of the four images or their labels is
            missing.
        ValueError: When the identifier is not one this can read, or a label
            names a band order this cannot read, or an image is shorter than
            its label says.
    """
    # Every product read so far, keyed by detector and by which kind it is.
    products: dict[tuple[str, bool], tuple[np.ndarray, dict[str, str]]] = {}
    for name in naming.DETECTORS:
        # The scan itself, then the geometry published beside it.
        for kind in naming.KINDS:
            # Where this product's image belongs in the cache.
            image = locations.files(identifier, name, kind)[".img"]

            # Loading the label text of the label beside the image.
            label = load_label(image.with_suffix(".lbl"))

            # The values themselves, shaped by what the label said.
            cube = build_cube(image, label)
            # Hold it until this detector's other half has been read as well.
            products[name, kind] = (cube, label)

    detectors = {}
    for name in naming.DETECTORS:
        cube, label = products[name, naming.OBSERVATION]
        # Order the bands by wavelength and mark what was never calibrated.
        cube, waves = bands_calibration.calibrate(cube, name)
        # Pair each detector's own cube with the geometry beside it.
        detectors[name] = Detector(
            name, cube, label, waves, *products[name, naming.GEOMETRY]
        )
    return CrismObservation(identifier, detectors)


def build_cube(image: Path, label: dict[str, str]) -> np.ndarray:
    """Read one image into an array indexed by line, sample and band.

    Args:
        image: The `.img` file holding the values.
        label: The parsed label describing it.

    Returns:
        The values as lines by samples by bands, in the band order the file
        stores them in, which is long wavelength first.

    Raises:
        ValueError: When the label names a band order this cannot read.
        KeyError: When it names a sample type this cannot read.
    """
    # How the image is shaped, ordered and written.
    lines, samples, bands, stored, dtype = load_layout(label)
    # How many values the cube holds, the trailing record excluded.
    wanted = lines * samples * bands
    # Read exactly those, so the table of detector rows is left alone.
    flat = np.fromfile(image, dtype=dtype, count=wanted)
    # BIL writes one line's bands together, so bands sit in the middle.
    if stored == _BIL:
        return flat.reshape(lines, bands, samples).transpose(0, 2, 1)
    # BSQ writes whole bands one after another, so bands come first.
    return flat.reshape(bands, lines, samples).transpose(1, 2, 0)


def load_layout(label: dict[str, str]) -> tuple[int, int, int, str, str]:
    """Read how one image is shaped and written from its label.

    Args:
        label: The parsed label.

    Returns:
        The lines, samples and bands it holds, the order its bands are written
        in, and the numpy dtype its samples are stored as.

    Raises:
        ValueError: When the label names a band order this cannot read.
        KeyError: When it names a sample type this cannot read.
    """
    # How many rows the scan holds, down track.
    lines = int(label["LINES"])
    # How many detector columns each row holds, across track.
    samples = int(label["LINE_SAMPLES"])
    # How many channels each pixel holds.
    bands = int(label["BANDS"])
    # The order bands are written in, BIL for a TRDR and BSQ for a DDR.
    stored = label.get("BAND_STORAGE_TYPE", _BIL)
    if stored not in (_BIL, _BSQ):
        raise ValueError(f"Cannot read a {stored} image.")
    # The sample type and its width, which together name a numpy dtype.
    dtype = _DTYPES[label["SAMPLE_TYPE"], int(label["SAMPLE_BITS"])]
    return lines, samples, bands, stored, dtype


def load_label(path: Path) -> dict[str, str]:
    """Read a PDS label into its keys and values.

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
