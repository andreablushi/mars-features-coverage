"""Reading one CRISM observation off disk, whole."""

from __future__ import annotations

from preprocessing.crism.fetching import bands_calibration
from preprocessing.crism.loaders import geometry, observation, wavelengths
from preprocessing.crism.loaders.utils import locations, naming
from preprocessing.crism.models.observation import CrismObservation, Detector


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
    detectors = {}
    for name in naming.DETECTORS:
        # The scan itself, then the geometry published beside it.
        cube, label = observation.load(identifier, name)
        # The wavelength file this half was calibrated against, and no other.
        record = locations.wavelength_file(naming.wavelength(label))[".img"]
        # Order the bands by wavelength and mark what was never calibrated.
        cube, table = bands_calibration.calibrate(cube, wavelengths.load(record))
        # Pair each detector's own cube with the geometry beside it.
        detectors[name] = Detector(
            name, cube, label, table, *geometry.load(identifier, name)
        )
    return CrismObservation(identifier, detectors)
