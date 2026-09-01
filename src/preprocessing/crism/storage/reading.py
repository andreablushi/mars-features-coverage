"""Reading one CRISM observation off disk."""

from __future__ import annotations

import numpy as np

from preprocessing.crism.calibration import bands_calibration, wavelengths
from preprocessing.crism.fetching import pds
from preprocessing.crism.models.observation import CrismObservation, Detector
from preprocessing.crism.storage import locations, naming


def read(identifier: str) -> CrismObservation:
    """Read every image one observation was downloaded as into an observation.

    Args:
        identifier: The observation, whose files must already be in the cache
            that `download.fetch` puts them in, the wavelength file each of its
            labels names included.

    Returns:
        The observation, both detectors and both geometries loaded, each cube
        ordered by the wavelength file its own label was calibrated against.

    Raises:
        FileNotFoundError: When any of the four images, their labels, or a
            wavelength file a label names is missing.
        ValueError: When a label names a band order this cannot read, or the
            wavelength file does not describe the cube beside it.
    """
    # Every product read so far, keyed by detector and by which kind it is.
    products: dict[tuple[str, bool], tuple[np.ndarray, dict[str, str]]] = {}
    for name in naming.DETECTORS:
        # The scan itself, then the geometry published beside it.
        for kind in naming.KINDS:
            # Where this product's image belongs in the cache.
            image = locations.files(identifier, name, kind)[".img"]

            # Loading the label text of the label beside the image.
            label = pds.load_label(image.with_suffix(".lbl"))

            # The values themselves, shaped by what the label said.
            cube = pds.build_cube(image, label)
            # Hold it until this detector's other half has been read as well.
            products[name, kind] = (cube, label)

    detectors = {}
    for name in naming.DETECTORS:
        cube, label = products[name, naming.OBSERVATION]
        # The wavelength file this half was calibrated against, and no other.
        record = locations.wavelength_file(naming.wavelength(label))[".img"]
        table = wavelengths.load(record)
        # Order the bands by wavelength and mark what was never calibrated.
        cube, table = bands_calibration.calibrate(cube, table)
        # Pair each detector's own cube with the geometry beside it.
        detectors[name] = Detector(
            name, cube, label, table, *products[name, naming.GEOMETRY]
        )
    return CrismObservation(identifier, detectors)
