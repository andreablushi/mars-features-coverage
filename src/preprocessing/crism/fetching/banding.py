"""Putting the bands in wavelength order and saying which of them read ground.

Ported from the `band_select` reordering in crism_ml's `io.crism_to_mat` and
from its `preprocessing.BANDS` and `preprocessing.N_BANDS`.

Differs from crism_ml:
  - The band table is the one for multispectral survey mode, not crism_ml's
    hyperspectral `BANDS`. Its `band_select` of `np.r_[433:185:-1, 170:-1:68]`
    is hyperspectral only, and its second slice is empty, so it yields 248
    channels where the datasets it ships hold 350.
  - The table was taken from the mode's own wavelength file rather than copied.
    Measured against the wavelength file of crism_ml's own demo image, its
    hardcoded table sits one channel out: mean error 6.50 nm and worst 6.54 nm,
    falling to 0.09 nm once the slice is shifted by one.
  - Hardcoding is safe for this mode even though observations name different
    versions of the wavelength file. Both versions in circulation for MSP were
    compared band by band and hold identical centres, to 0.000 nm, and mark the
    same 60 columns live.
  - The reversal is the same idea as `band_select`, but the order was checked
    rather than assumed. MSP stores band 0 at 3925.39 nm and its last band at
    1022.75 nm, strictly decreasing.
  - Uncalibrated detector columns are new. MSP leaves four of its 64 columns
    without a wavelength, so only 60 carry data, and their spectra still read
    as ordinary numbers. crism_ml has no notion of a dead column and nothing in
    `filter_bad_pixels` finds them.
  - Spectral smile is left uncorrected, as in crism_ml. Across the live columns
    the band centres spread by 10.22 nm on average and 15.94 nm at worst, which
    is 28 per cent of an MSP channel against 162 per cent of a hyperspectral
    one, and a ratio taken down a detector column divides out what remains.
"""

from __future__ import annotations

import numpy as np

from preprocessing.crism import configs


def wavelengths() -> np.ndarray:
    """Return the band centres the cleaned cube is indexed by.

    Returns:
        The centres in nanometres, ascending, one per band the cube keeps.
    """
    return np.asarray(configs.WAVELENGTHS_NM, dtype=np.float64)


def ascending(cube: np.ndarray) -> np.ndarray:
    """Drop the uncalibrated bands and put the rest in wavelength order.

    Args:
        cube: The values as read, lines by samples by bands, in file order.

    Returns:
        The values with the uncalibrated bands gone and the band axis reversed,
        so band i sits at `wavelengths()[i]`.

    Raises:
        ValueError: When the cube holds a different number of bands than the
            band table accounts for.
    """
    expected = len(configs.WAVELENGTHS_NM) + len(configs.DEAD_BANDS)
    if cube.shape[-1] != expected:
        raise ValueError(f"Expected {expected} bands, found {cube.shape[-1]}.")
    kept = np.ones(cube.shape[-1], dtype=bool)
    kept[list(configs.DEAD_BANDS)] = False
    return cube[..., kept][..., ::-1]


def usable_columns(samples: int) -> np.ndarray:
    """Return which detector columns carry a wavelength calibration.

    Args:
        samples: How many columns the observation is wide.

    Returns:
        A boolean array over the columns, false where the column is dead.
    """
    live = np.ones(samples, dtype=bool)
    live[[column for column in configs.DEAD_COLUMNS if column < samples]] = False
    return live


def usable_bands(centres: np.ndarray) -> np.ndarray:
    """Return which bands read the ground rather than the air or the heat.

    Args:
        centres: The band centres in nanometres.

    Returns:
        A boolean array over the bands, false inside the opaque window and
        above the wavelength where the surface starts to glow.
    """
    opaque_from, opaque_to = configs.OPAQUE_NM
    opaque = (centres >= opaque_from) & (centres <= opaque_to)
    return ~opaque & (centres < configs.THERMAL_NM)


def channels(width_nm: float, spacing_nm: float) -> int:
    """Convert a filter width in nanometres to a whole number of channels.

    The result is forced odd so the window sits symmetrically on the channel it
    is filtering, and never narrower than a median can reject anything over.

    Args:
        width_nm: How wide the window should be in nanometres.
        spacing_nm: The gap between neighbouring band centres.

    Returns:
        The window width in channels.
    """
    wide = max(int(round(width_nm / spacing_nm)), configs.MIN_WINDOW_CHANNELS)
    return wide if wide % 2 else wide + 1
