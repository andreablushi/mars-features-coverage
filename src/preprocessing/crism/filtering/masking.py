"""Finding the voxels that hold no measurement, and the border they make.

Ported from crism_ml's `preprocessing.filter_bad_pixels` and
`preprocessing.crop_region`.

Differs from crism_ml:
  - The test is I/F outside [0, 1] rather than only above 1e3. I/F is a ratio
    against a white surface, so anything outside those bounds is impossible,
    and a hyperspectral label records the same two numbers for itself as
    MRO:IF_MIN_VALUE and MRO:IF_MAX_VALUE. crism_ml's `bad = (pixspec > 1e3) |
    ~np.isfinite(pixspec)` lets every negative through, and real products carry
    them: a value of -1374.5 was measured at band 1 of an ordinary frame.
  - Bad voxels become NaN and the mask is returned beside them. crism_ml writes
    `np.mean(pixspec[~bad])`, one number averaged over the whole cube, into
    every bad voxel. That is safe for a classifier handed the mask in the same
    breath, but in a stored dataset it is a plausible looking number with
    nothing behind it.
  - Uncalibrated detector columns are folded in, which crism_ml has no notion
    of, so a whole dead column is unusable even where its numbers look normal.
  - `crop_region` returns whether the border was clean instead of logging it.
    Nothing else in this repository logs from a library module.
"""

from __future__ import annotations

import numpy as np

from preprocessing.crism import configs


def flagged(cube: np.ndarray) -> np.ndarray:
    """Return which voxels hold no usable measurement.

    Args:
        cube: The spectra, lines by samples by bands.

    Returns:
        A boolean array shaped like the cube, true where the value is the fill
        value, is not finite, or falls outside the bounds I/F can take.
    """
    with np.errstate(invalid="ignore"):
        outside = (cube < configs.IF_MIN) | (cube > configs.IF_MAX)
    return outside | ~np.isfinite(cube) | (cube == configs.FILL)


def applied(cube: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Return a copy of the cube with the masked voxels made unreadable.

    Args:
        cube: The spectra, lines by samples by bands.
        mask: Which voxels hold no usable measurement.

    Returns:
        A copy holding NaN wherever the mask is true.
    """
    cleaned = cube.astype(np.float32, copy=True)
    cleaned[mask] = np.nan
    return cleaned


def unusable(mask: np.ndarray, columns: np.ndarray) -> np.ndarray:
    """Return which pixels cannot be read at all.

    This is crism_ml's `rem`: a pixel is unusable when any of its bands is,
    widened here to take in the columns the wavelength table never calibrated.

    Args:
        mask: Which voxels hold no usable measurement.
        columns: Which detector columns carry a wavelength calibration.

    Returns:
        A boolean array over lines and samples, true where the pixel is unusable.
    """
    return np.any(mask, axis=-1) | ~columns[np.newaxis, :]


def crop_region(rem: np.ndarray) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return the smallest rectangle holding every readable pixel.

    Args:
        rem: A boolean array over lines and samples, true where the pixel is
            unusable.

    Returns:
        The rectangle as ((first line, last line plus one), (first sample, last
        sample plus one)).

    Raises:
        ValueError: When no pixel in the image is readable.
    """
    rows, columns = np.nonzero(~rem)
    if not rows.size:
        raise ValueError("Every pixel of the image is unusable.")
    return (
        (int(rows.min()), int(rows.max()) + 1),
        (int(columns.min()), int(columns.max()) + 1),
    )


def border_clean(
    rem: np.ndarray, crop: tuple[tuple[int, int], tuple[int, int]]
) -> bool:
    """Say whether the unusable pixels are only a border round the crop.

    When they are not, the crop keeps unusable pixels inside it, which is worth
    knowing before the rectangle is trusted.

    Args:
        rem: A boolean array over lines and samples, true where the pixel is
            unusable.
        crop: The rectangle from `crop_region`.

    Returns:
        True when every unusable pixel lies outside the rectangle.
    """
    (top, bottom), (left, right) = crop
    border = np.ones(rem.shape, dtype=bool)
    border[top:bottom, left:right] = False
    return bool(np.array_equal(rem, border))
