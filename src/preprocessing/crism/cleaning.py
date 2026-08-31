"""Running the cleaning steps over one observation, in order.

The order is the one crism_ml's `train.run_on_images` uses: read, flag the
voxels that hold no measurement, take out the faults a whole detector column
shares, then take out the spikes left in single channels.

Differs from crism_ml:
  - It stops before the bland pixel scoring, the classification and everything
    downstream of them, which are the classifier and not the cleaning.
  - `run_on_images` removes spikes after the ratio, because the ratio always
    runs there. Here the ratio is optional, so spike removal runs on the
    unratioed cube. `ratioing` is applied afterwards by whoever wants it.
  - Each step is kept rather than overwritten, so what a step changed can be
    read off against the step before it.
  - Every stage carries the mask of its own cube rather than the one taken at
    the start, which makes a step that introduces new unreadable voxels visible
    instead of silent.
"""

from __future__ import annotations

from pathlib import Path

from preprocessing.crism import banding, configs, despiking, masking, reading
from preprocessing.crism.models.stage import Stage
from preprocessing.crism.models.strip import Strip


def load(path: Path) -> Strip:
    """Read one observation and work out how to index it.

    Args:
        path: Either the `.lbl` or the `.img` of the observation.

    Returns:
        The observation, its bands in wavelength order and its unusable voxels,
        columns and bands marked.
    """
    cube, label = reading.read(path)
    ordered = banding.ascending(cube)
    centres = banding.wavelengths()
    return Strip(
        product_id=label.get("PRODUCT_ID", path.stem).lower(),
        cube=ordered,
        wavelengths=centres,
        columns=banding.usable_columns(ordered.shape[1]),
        bands=banding.usable_bands(centres),
        mask=masking.flagged(ordered),
        label=label,
    )


def stages(strip: Strip) -> list[Stage]:
    """Run the cleaning and keep what every step left behind.

    Args:
        strip: The observation as loaded.

    Returns:
        The stages in the order they ran, starting with the cube as read.
    """
    spacing = strip.spacing_nm
    kept = [Stage("as read", strip.cube, masking.flagged(strip.cube))]

    masked = masking.applied(strip.cube, strip.mask)
    kept.append(Stage("bad values masked", masked, masking.flagged(masked)))

    destriped = despiking.remove_column_spikes(
        masked, configs.COLUMN_WINDOW_NM, configs.COLUMN_SIGMA, spacing
    )
    kept.append(Stage("column faults removed", destriped, masking.flagged(destriped)))

    despiked = despiking.remove_spikes(destriped, configs.SPIKE_PASSES_NM, spacing)
    kept.append(Stage("spikes removed", despiked, masking.flagged(despiked)))

    return kept


def clean(strip: Strip) -> Strip:
    """Run the cleaning and keep only what it ended with.

    Args:
        strip: The observation as loaded.

    Returns:
        The observation with its cube cleaned and its mask brought up to date.
    """
    last = stages(strip)[-1]
    return Strip(
        product_id=strip.product_id,
        cube=last.cube,
        wavelengths=strip.wavelengths,
        columns=strip.columns,
        bands=strip.bands,
        mask=last.mask,
        label=strip.label,
    )
